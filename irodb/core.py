"""
Core database implementation for IRODB
"""

import os
import struct
import tempfile
from . import binary_codec as codec
from .encryption import derive_key, encrypt_page, decrypt_page, SALT_SIZE
from . import wal
from typing import Any, Dict, List, Optional, Union, Tuple
from datetime import datetime
import hashlib
from contextlib import contextmanager

from .constants import *
from .exceptions import *
from .hash_system import HashManager

class IRODB:
    """Main database class"""
    
    def __init__(self, db_path: str, auto_create: bool = True, encryption_key=None):
        self.db_path = db_path
        self._wal_path = wal.wal_path(db_path)
        self._encryption_secret = encryption_key
        self._encryption_key = None
        self._encrypted = False
        self._salt = b""
        self.tables = {}
        self.page_cache = {}
        self.hash_manager = HashManager(self)
        self.metadata = {}
        self.constraints = {}
        self._batch_depth = 0
        self._pending_pages = {}
        
        if not os.path.exists(db_path):
            if auto_create:
                self._create_empty_db()
            else:
                raise DatabaseError(f"Database not found: {db_path}")
        else:
            wal.recover(self.db_path, PAGE_SIZE)
            self._load_metadata()
    
    def _create_empty_db(self):
        """Create new database file, optionally encrypted from the first page."""
        self._encrypted = self._encryption_secret is not None
        self._salt = os.urandom(SALT_SIZE) if self._encrypted else b"\x00" * SALT_SIZE
        self._encryption_key = (derive_key(self._encryption_secret, self._salt)
                               if self._encrypted else None)
        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        
        with open(self.db_path, 'wb') as f:
            # Write header
            f.write(MAGIC_HEADER)
            f.write(struct.pack('<H', VERSION))
            f.write(struct.pack('<Q', 0))  # Page count
            f.write(struct.pack('<Q', 0))  # Checksum
            f.write(struct.pack('<Q', 1))  # Next page
            f.write(b'\x01' if self._encrypted else b'\x00')
            f.write(self._salt)
            f.write(b'\x00' * (PAGE_SIZE - 48))
            
            # Create metadata page
            metadata = {
                'tables': {},
                'indexes': {},
                'hash_indexes': {},
                'next_page': 2,
                'created_at': datetime.now().isoformat(),
                'version': VERSION,
                'constraints': {}
            }
            self._write_page(1, codec.dumps(metadata))
        
        # Load the metadata
        self._load_metadata()
    
    def _load_metadata(self):
        """Load metadata from database"""
        try:
            with open(self.db_path, 'rb') as f:
                header = f.read(5)
                if header != MAGIC_HEADER:
                    self._create_empty_db()
                    return
                
                version = struct.unpack('<H', f.read(2))[0]
                if version != VERSION:
                    raise DatabaseError(f"Unsupported version: {version}")
                f.read(24)  # page count, header checksum, and next-page fields
                flags = f.read(1)
                self._encrypted = flags == b'\x01'
                self._salt = f.read(SALT_SIZE)
                if self._encrypted:
                    if self._encryption_secret is None:
                        raise DatabaseError("Database is encrypted; provide encryption_key")
                    self._encryption_key = derive_key(self._encryption_secret, self._salt)
                metadata = codec.loads(self._read_page(1))
                self.tables = metadata.get('tables', {})
                self.metadata = metadata
                self.constraints = metadata.get('constraints', {})
        except DatabaseError:
            raise
        except Exception as e:
            if self._encrypted:
                raise DatabaseError(f"Encrypted database metadata is corrupt: {e}") from e
            self._create_empty_db()
    
    def _read_page(self, page_num: int) -> bytes:
        """Read a page from disk"""
        if page_num in self.page_cache:
            return self.page_cache[page_num]
        
        try:
            with open(self.db_path, 'rb') as f:
                f.seek(page_num * PAGE_SIZE)
                data = f.read(PAGE_SIZE)
                if self._encrypted and page_num > 0:
                    data = decrypt_page(data, self._encryption_key, page_num, VERSION)
                if len(data) == 0:
                    # Page doesn't exist, return empty page
                    data = b'\x00' * PAGE_SIZE
                self.page_cache[page_num] = data
                return data
        except Exception as e:
            if self._encrypted:
                raise PageError(f"Failed to authenticate/read page {page_num}: {e}") from e
            return b'\x00' * PAGE_SIZE
    
    def _write_page(self, page_num: int, data: bytes):
        """Write one page through the durable batched commit path."""
        self._write_pages({page_num: data})

    @contextmanager
    def batch(self):
        """Coalesce writes into one durable WAL/database commit.

        Use this for many ordinary insert/update/delete calls when the caller
        wants one commit boundary. Data is staged in memory until the context
        exits successfully; an exception discards staged pages and invalidates
        the cache. A successful exit performs the normal WAL fsync and database
        fsync exactly once.
        """
        self._batch_depth += 1
        try:
            yield self
        except Exception:
            self._batch_depth = max(0, self._batch_depth - 1)
            if self._batch_depth == 0:
                self._pending_pages.clear()
                self.page_cache.clear()
            raise
        else:
            self._batch_depth -= 1
            if self._batch_depth == 0 and self._pending_pages:
                pages = self._pending_pages
                self._pending_pages = {}
                self._write_pages(pages)

    def _write_pages(self, pages: Dict[int, bytes]):
        """Durably commit several plaintext pages with one WAL and file sync."""
        if not pages:
            return
        if self._batch_depth:
            self._pending_pages.update(pages)
            self.page_cache.update(pages)
            return
        try:
            prepared = []
            plaintext_pages = {}
            for page_num, plaintext in pages.items():
                plaintext_pages[page_num] = plaintext
                data = plaintext
                if self._encrypted and page_num > 0:
                    data = encrypt_page(plaintext, self._encryption_key, page_num, VERSION)
                if len(data) > PAGE_SIZE:
                    raise PageError(f"Page {page_num} exceeds the fixed page size")
                prepared.append((page_num, data.ljust(PAGE_SIZE, b'\x00')))

            os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
            wal.append_records(self._wal_path, prepared)
            if os.path.exists(self.db_path):
                with open(self.db_path, 'r+b') as stream:
                    for page_num, data in prepared:
                        stream.seek(page_num * PAGE_SIZE)
                        stream.write(data)
                    stream.flush()
                    os.fsync(stream.fileno())
            else:
                with open(self.db_path, 'wb') as stream:
                    stream.write(MAGIC_HEADER)
                    stream.write(struct.pack('<H', VERSION))
                    stream.write(struct.pack('<Q', 0))
                    stream.write(struct.pack('<Q', 0))
                    stream.write(struct.pack('<Q', 1))
                    stream.write(b'\\x01' if self._encrypted else b'\\x00')
                    stream.write(self._salt)
                    stream.write(b'\\x00' * (PAGE_SIZE - 48))
                    for page_num, data in prepared:
                        stream.seek(page_num * PAGE_SIZE)
                        stream.write(data)
                    stream.flush()
                    os.fsync(stream.fileno())
            self.page_cache.update(plaintext_pages)
            wal.clear(self._wal_path)
        except Exception as exc:
            raise PageError(f"Failed to write pages {sorted(pages)}: {exc}") from exc
    
    def _get_next_page(self) -> int:
        """Get next available page"""
        max_page = 1
        for table in self.tables.values():
            page = table.get('page', 0)
            if page and page > max_page:
                max_page = page
            
            hash_page = table.get('hash_index_page')
            if hash_page and hash_page > max_page:
                max_page = hash_page
        
        # Check if we have any pages stored
        if hasattr(self, 'metadata') and self.metadata:
            next_page = self.metadata.get('next_page', max_page + 1)
            return max(next_page, max_page + 1)
        
        return max_page + 1
    
    def _metadata_dict(self):
        return {
            'tables': self.tables,
            'indexes': {},
            'hash_indexes': self.hash_manager.hash_indexes,
            'next_page': self._get_next_page(),
            'created_at': datetime.now().isoformat(),
            'version': VERSION,
            'constraints': getattr(self, 'constraints', {})
        }

    def _save_metadata(self):
        """Save metadata to page 1."""
        metadata = self._metadata_dict()
        self._write_page(1, codec.dumps(metadata))
        self.metadata = metadata
    
    def create_table(self, table_name: str, schema: Dict[str, type],
                    enable_hash_index: bool = False):
        """Create a new table"""
        if table_name in self.tables:
            raise TableError(f"Table {table_name} already exists")
        
        table_data = {
            'schema': schema,
            'rows': [],
            'page': self._get_next_page(),
            'enable_hash_index': enable_hash_index,
            'hash_index_page': self._get_next_page() + 1 if enable_hash_index else None,
            'created_at': datetime.now().isoformat()
        }
        
        self.tables[table_name] = table_data
        
        # Create table page
        page_data = {
            'rows': [],
            'auto_increment': 0,
            'hash_index': {} if enable_hash_index else None
        }
        self._write_page(table_data['page'], codec.dumps(page_data))
        
        if enable_hash_index:
            self._write_page(table_data['hash_index_page'], codec.dumps({}))
        
        self._save_metadata()
        return table_data
    
    def insert(self, table_name: str, data: Dict[str, Any],
              return_hash: bool = False) -> Union[int, Tuple[int, str]]:
        """Insert a row"""
        if table_name not in self.tables:
            raise TableError(f"Table {table_name} does not exist")
        
        table_info = self.tables[table_name]
        schema = table_info['schema']
        
        # Validate data
        for field, field_type in schema.items():
            if field not in data:
                raise ValueError(f"Missing field: {field}")
            if data[field] is not None and not isinstance(data[field], field_type):
                raise TypeError(f"Field {field} must be of type {field_type.__name__}")
        
        # Load table data
        try:
            page_data = self._read_page(table_info['page'])
            table_data = codec.loads(page_data)
        except Exception as exc:
            raise CorruptedError(f"Table page for {table_name} is corrupt: {exc}") from exc
        
        # Enforce application-level constraints before assigning or committing
        # the row. DataValidator is imported lazily to avoid an import cycle.
        from .feature_validation import DataValidator
        DataValidator(self).check_constraints_on_insert(table_name, data)

        # Assign row ID
        row_id = table_data.get('auto_increment', 0) + 1
        table_data['auto_increment'] = row_id
        
        # Create row with hash
        row = {'id': row_id, **data}
        row_hash = self.hash_manager.calculate_row_hash(row)
        row['hash'] = row_hash
        
        # Add row
        if 'rows' not in table_data:
            table_data['rows'] = []
        table_data['rows'].append(row)
        
        # Prepare all changed pages and commit them together.
        pages = {table_info['page']: codec.dumps(table_data)}
        if table_info.get('enable_hash_index', False):
            hash_page = table_info.get('hash_index_page')
            if hash_page:
                try:
                    hash_data = self._read_page(hash_page)
                    hash_index = codec.loads(hash_data) if hash_data and len(hash_data) > 0 else {}
                    if row_hash not in hash_index:
                        hash_index[row_hash] = []
                    if row_id not in hash_index[row_hash]:
                        hash_index[row_hash].append(row_id)
                    pages[hash_page] = codec.dumps(hash_index)
                except Exception as exc:
                    raise CorruptedError(f"Hash index for {table_name} is corrupt: {exc}") from exc

        metadata = self._metadata_dict()
        pages[1] = codec.dumps(metadata)
        self._write_pages(pages)
        self.metadata = metadata
        
        return (row_id, row_hash) if return_hash else row_id

    def bulk_insert(self, table_name: str, rows: List[Dict[str, Any]],
                    return_hashes: bool = False):
        """Insert many rows with one durable WAL/page commit.

        This is the preferred path for imports and ingestion workloads. It keeps
        the same schema and hash validation as insert(), while reducing repeated
        page serialization, WAL opens, and fsync calls.
        """
        if table_name not in self.tables:
            raise TableError(f"Table {table_name} does not exist")
        if not isinstance(rows, list):
            raise TypeError("rows must be a list of dictionaries")
        if not rows:
            return []

        table_info = self.tables[table_name]
        schema = table_info['schema']
        try:
            table_data = codec.loads(self._read_page(table_info['page']))
        except Exception as exc:
            raise CorruptedError(f"Table page for {table_name} is corrupt: {exc}") from exc

        next_id = table_data.get('auto_increment', 0)
        added = []
        for data in rows:
            if not isinstance(data, dict):
                raise TypeError("every bulk_insert row must be a dictionary")
            for field, field_type in schema.items():
                if field not in data:
                    raise ValueError(f"Missing field: {field}")
                if data[field] is not None and not isinstance(data[field], field_type):
                    raise TypeError(f"Field {field} must be of type {field_type.__name__}")
            from .feature_validation import DataValidator
            DataValidator(self).check_constraints_on_insert(table_name, data)
            # Also reject duplicate unique values within the same bulk batch.
            for previous in added:
                previous_row = previous[2]
                for field, constraint in self.constraints.get(table_name, {}).items():
                    if constraint.get('unique') and field in data and field in previous_row and data[field] == previous_row[field]:
                        raise ConstraintError(
                            f"Unique constraint violation: '{field}' must be unique, '{data[field]}' appears more than once in the batch"
                        )
            next_id += 1
            row = {'id': next_id, **data}
            row_hash = self.hash_manager.calculate_row_hash(row)
            row['hash'] = row_hash
            table_data.setdefault('rows', []).append(row)
            added.append((next_id, row_hash, row))
        table_data['auto_increment'] = next_id

        pages = {table_info['page']: codec.dumps(table_data)}
        if table_info.get('enable_hash_index', False):
            hash_page = table_info.get('hash_index_page')
            if hash_page:
                try:
                    hash_data = self._read_page(hash_page)
                    hash_index = codec.loads(hash_data) if hash_data and len(hash_data) > 0 else {}
                    for row_id, row_hash, _ in added:
                        hash_index.setdefault(row_hash, []).append(row_id)
                    pages[hash_page] = codec.dumps(hash_index)
                except Exception as exc:
                    raise CorruptedError(f"Hash index for {table_name} is corrupt: {exc}") from exc

        metadata = self._metadata_dict()
        pages[1] = codec.dumps(metadata)
        self._write_pages(pages)
        self.metadata = metadata
        return ([(row_id, row_hash) for row_id, row_hash, _ in added]
                if return_hashes else [row_id for row_id, _, _ in added])
    
    @staticmethod
    def _matches_condition(actual: Any, expected: Any) -> bool:
        if isinstance(expected, dict):
            for operator, target in expected.items():
                if operator == "$gt" and not (actual is not None and actual > target): return False
                if operator == "$gte" and not (actual is not None and actual >= target): return False
                if operator == "$lt" and not (actual is not None and actual < target): return False
                if operator == "$lte" and not (actual is not None and actual <= target): return False
                if operator == "$ne" and actual == target: return False
                if operator == "$in" and actual not in target: return False
                if operator == "$contains" and target not in actual: return False
            return True
        return actual == expected

    def select(self, table_name: str, conditions: Optional[Dict[str, Any]] = None,
              use_hash: bool = False, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Select rows"""
        if table_name not in self.tables:
            raise TableError(f"Table {table_name} does not exist")
        
        if use_hash and conditions and 'hash' in conditions:
            return self.hash_manager.find_by_hash(table_name, conditions['hash'])
        
        try:
            page_data = self._read_page(self.tables[table_name]['page'])
            table_data = codec.loads(page_data)
        except Exception as exc:
            raise CorruptedError(f"Table page for {table_name} is corrupt: {exc}") from exc
        
        rows = table_data.get('rows', [])
        
        if not conditions:
            return rows[:limit] if limit else rows.copy()
        
        results = []
        for row in rows:
            if all(self._matches_condition(row.get(k), v) for k, v in conditions.items()):
                results.append(row.copy())
                if limit and len(results) >= limit:
                    break
        
        return results
    
    def update(self, table_name: str, conditions: Dict[str, Any],
              updates: Dict[str, Any]) -> int:
        """Update matching rows and commit table/index changes once."""
        if table_name not in self.tables:
            raise TableError(f"Table {table_name} does not exist")

        table_info = self.tables[table_name]
        schema = table_info['schema']
        try:
            table_data = codec.loads(self._read_page(table_info['page']))
        except Exception as exc:
            raise CorruptedError(f"Table page for {table_name} is corrupt: {exc}") from exc

        for field, value in updates.items():
            if field not in schema:
                raise ValueError(f"Invalid field: {field}")
            if value is not None and not isinstance(value, schema[field]):
                raise TypeError(f"Field {field} must be of type {schema[field].__name__}")

        hash_index = None
        hash_page = None
        if table_info.get('enable_hash_index', False) and table_info.get('hash_index_page'):
            hash_page = table_info['hash_index_page']
            try:
                hash_index = codec.loads(self._read_page(hash_page))
            except Exception as exc:
                raise CorruptedError(f"Hash index for {table_name} is corrupt: {exc}") from exc

        updated_count = 0
        for row in table_data.get('rows', []):
            if not all(self._matches_condition(row.get(k), v) for k, v in conditions.items()):
                continue
            candidate = dict(row)
            candidate.update(updates)
            from .feature_validation import DataValidator
            DataValidator(self).check_constraints_on_update(table_name, candidate, row.get('id'))
            old_hash = row.get('hash', '')
            row.update(updates)
            new_hash = self.hash_manager.calculate_row_hash(row)
            row['hash'] = new_hash
            if hash_index is not None:
                if old_hash in hash_index:
                    hash_index[old_hash] = [rid for rid in hash_index[old_hash] if rid != row['id']]
                    if not hash_index[old_hash]:
                        del hash_index[old_hash]
                hash_index.setdefault(new_hash, [])
                if row['id'] not in hash_index[new_hash]:
                    hash_index[new_hash].append(row['id'])
            updated_count += 1

        if updated_count:
            pages = {table_info['page']: codec.dumps(table_data), 1: codec.dumps(self._metadata_dict())}
            if hash_index is not None:
                pages[hash_page] = codec.dumps(hash_index)
            self._write_pages(pages)
            self.metadata = self._metadata_dict()
        return updated_count
    
    def delete(self, table_name: str, conditions: Dict[str, Any]) -> int:
        """Delete matching rows and commit table/index changes once."""
        if table_name not in self.tables:
            raise TableError(f"Table {table_name} does not exist")

        table_info = self.tables[table_name]
        try:
            table_data = codec.loads(self._read_page(table_info['page']))
        except Exception as exc:
            raise CorruptedError(f"Table page for {table_name} is corrupt: {exc}") from exc

        hash_index = None
        hash_page = None
        if table_info.get('enable_hash_index', False) and table_info.get('hash_index_page'):
            hash_page = table_info['hash_index_page']
            try:
                hash_index = codec.loads(self._read_page(hash_page))
            except Exception as exc:
                raise CorruptedError(f"Hash index for {table_name} is corrupt: {exc}") from exc

        remaining_rows = []
        deleted_count = 0
        for row in table_data.get('rows', []):
            if all(self._matches_condition(row.get(k), v) for k, v in conditions.items()):
                deleted_count += 1
                if hash_index is not None and row.get('hash') in hash_index:
                    hash_index[row['hash']] = [rid for rid in hash_index[row['hash']] if rid != row['id']]
                    if not hash_index[row['hash']]:
                        del hash_index[row['hash']]
            else:
                remaining_rows.append(row)

        if deleted_count:
            table_data['rows'] = remaining_rows
            pages = {table_info['page']: codec.dumps(table_data), 1: codec.dumps(self._metadata_dict())}
            if hash_index is not None:
                pages[hash_page] = codec.dumps(hash_index)
            self._write_pages(pages)
            self.metadata = self._metadata_dict()
        return deleted_count
    
    def find_by_hash(self, table_name: str, hash_value: str) -> List[Dict[str, Any]]:
        """Find rows by hash"""
        return self.hash_manager.find_by_hash(table_name, hash_value)
    
    def find_by_hashed_value(self, table_name: str, value: Any) -> List[Dict[str, Any]]:
        """Find rows by hashed value"""
        return self.hash_manager.find_by_hashed_value(table_name, value)
    
    def verify_hash_integrity(self, table_name: str) -> Dict[str, Any]:
        """Verify hash integrity"""
        return self.hash_manager.verify_hash_integrity(table_name)
    
    def get_hash_statistics(self, table_name: str) -> Dict[str, Any]:
        """Get hash statistics"""
        return self.hash_manager.get_hash_statistics(table_name)
    
    def vacuum(self):
        """Optimize database"""
        for table_name, table_info in self.tables.items():
            try:
                page_data = self._read_page(table_info['page'])
                table_data = codec.loads(page_data)
                self._write_page(table_info['page'], codec.dumps(table_data))
            except Exception as exc:
                raise CorruptedError(f"Table page for {table_name} is corrupt: {exc}") from exc
        
        self.page_cache.clear()
    
    def query(self, query_text: str, params=None):
        """Execute an injection-safe IRODB Query statement."""
        from .feature_query import IRODBQuery
        return IRODBQuery(self).execute(query_text, params)

    def rekey(self, new_encryption_key, progress_callback=None):
        """Change the passphrase of an encrypted database atomically.

        Pages are processed one at a time, so memory usage is bounded by the
        fixed page size. The original file remains unchanged until the complete
        replacement has been validated and atomically installed.
        """
        if not self._encrypted:
            raise DatabaseError("Re-key requires an existing encrypted database")
        if new_encryption_key is None:
            raise ValueError("new encryption key is required")
        new_salt = os.urandom(SALT_SIZE)
        new_key = derive_key(new_encryption_key, new_salt)
        total_pages = os.path.getsize(self.db_path) // PAGE_SIZE
        if total_pages < 2:
            raise DatabaseError("Encrypted database has no metadata page")

        temp_fd, temp_path = tempfile.mkstemp(prefix=".irodb-rekey-", suffix=".tmp", dir=os.path.dirname(os.path.abspath(self.db_path)))
        os.close(temp_fd)
        try:
            with open(self.db_path, "rb") as source, open(temp_path, "w+b") as target:
                header = (MAGIC_HEADER + struct.pack('<H', VERSION) + struct.pack('<Q', total_pages - 1)
                          + struct.pack('<Q', 0) + struct.pack('<Q', self._get_next_page())
                          + b'\x01' + new_salt)
                target.write(header.ljust(PAGE_SIZE, b'\x00'))
                for page_number in range(1, total_pages):
                    source.seek(page_number * PAGE_SIZE)
                    encrypted_page = source.read(PAGE_SIZE)
                    plaintext = decrypt_page(encrypted_page, self._encryption_key, page_number, VERSION)
                    replacement = encrypt_page(plaintext, new_key, page_number, VERSION)
                    if len(replacement) > PAGE_SIZE:
                        raise PageError(f"Re-keyed page {page_number} exceeds the fixed page size")
                    target.seek(page_number * PAGE_SIZE)
                    target.write(replacement.ljust(PAGE_SIZE, b'\x00'))
                    if progress_callback:
                        progress_callback(page_number, total_pages - 1)
                target.flush()
                os.fsync(target.fileno())

            # Validate the complete replacement before changing the original.
            check = IRODB(temp_path, auto_create=False, encryption_key=new_encryption_key)
            check.close()
            os.replace(temp_path, self.db_path)
            try:
                directory_fd = os.open(os.path.dirname(os.path.abspath(self.db_path)), os.O_DIRECTORY)
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
            except OSError:
                pass
            self._encryption_secret = new_encryption_key
            self._salt = new_salt
            self._encryption_key = new_key
            self.page_cache.clear()
            self._load_metadata()
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def close(self):
        """Close database"""
        self.page_cache.clear()
        self._save_metadata()