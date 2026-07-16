# irodb/core.py - Complete Fixed Version
import os
import struct
import pickle
import json
from typing import Any, Dict, List, Optional, Union, Tuple
from datetime import datetime
import hashlib

from .constants import *
from .exceptions import *

class HashManager:
    """Manages hash operations"""
    
    def __init__(self, db):
        self.db = db
        self.hash_indexes = {}
    
    def calculate_hash(self, data: Any) -> str:
        """Calculate SHA-256 hash of data"""
        try:
            if isinstance(data, (dict, list)):
                data = json.dumps(data, sort_keys=True).encode()
            elif isinstance(data, str):
                data = data.encode('utf-8')
            elif isinstance(data, (int, float, bool)):
                data = str(data).encode('utf-8')
            elif not isinstance(data, bytes):
                data = str(data).encode('utf-8')
            
            return hashlib.sha256(data).hexdigest()
        except Exception as e:
            raise HashError(f"Failed to calculate hash: {e}")
    
    def calculate_row_hash(self, row: Dict[str, Any]) -> str:
        """Calculate hash for a row"""
        row_copy = {k: v for k, v in row.items() if k not in ['id', 'hash', '_metadata']}
        return self.calculate_hash(row_copy)
    
    def find_by_hash(self, table_name: str, hash_value: str,
                    exact_match: bool = True) -> List[Dict[str, Any]]:
        """Find rows by hash"""
        table_info = self.db.tables.get(table_name)
        if not table_info:
            return []
        
        # Use hash index if available
        if exact_match and table_info.get('enable_hash_index', False):
            hash_page = table_info.get('hash_index_page')
            if hash_page:
                try:
                    hash_index = pickle.loads(self.db._read_page(hash_page))
                    if hash_value in hash_index:
                        row_ids = hash_index[hash_value]
                        return self._get_rows_by_ids(table_name, row_ids)
                except:
                    pass
                return []
        
        # Fallback to full scan
        try:
            table_data = pickle.loads(self.db._read_page(table_info['page']))
            results = []
            
            for row in table_data['rows']:
                row_hash = row.get('hash', '')
                if exact_match:
                    if row_hash == hash_value:
                        results.append(row.copy())
                else:
                    if row_hash.startswith(hash_value):
                        results.append(row.copy())
            
            return results
        except:
            return []
    
    def _get_rows_by_ids(self, table_name: str, row_ids: List[int]) -> List[Dict[str, Any]]:
        """Get rows by IDs"""
        try:
            table_data = pickle.loads(self.db._read_page(self.db.tables[table_name]['page']))
            id_set = set(row_ids)
            return [row.copy() for row in table_data['rows'] if row['id'] in id_set]
        except:
            return []
    
    def find_by_hashed_value(self, table_name: str, value: Any) -> List[Dict[str, Any]]:
        """Find rows by hashing a value"""
        hash_val = self.calculate_hash(value)
        return self.find_by_hash(table_name, hash_val)
    
    def find_by_hash_and_column(self, table_name: str, hash_value: str,
                               column: str, value: Any) -> List[Dict[str, Any]]:
        """Find by hash and column filter"""
        rows = self.find_by_hash(table_name, hash_value)
        return [row for row in rows if row.get(column) == value]
    
    def verify_hash_integrity(self, table_name: str) -> Dict[str, Any]:
        """Verify all hashes in a table"""
        table_info = self.db.tables.get(table_name)
        if not table_info:
            raise ValueError(f"Table {table_name} does not exist")
        
        try:
            table_data = pickle.loads(self.db._read_page(table_info['page']))
        except:
            return {'error': 'Failed to read table data'}
        
        results = {
            'total_rows': len(table_data['rows']),
            'valid_hashes': 0,
            'invalid_hashes': 0,
            'corrupted_rows': [],
            'verified_at': datetime.now().isoformat()
        }
        
        for row in table_data['rows']:
            stored_hash = row.get('hash', '')
            computed_hash = self.calculate_row_hash(row)
            
            if stored_hash == computed_hash:
                results['valid_hashes'] += 1
            else:
                results['invalid_hashes'] += 1
                results['corrupted_rows'].append({
                    'id': row['id'],
                    'stored_hash': stored_hash,
                    'computed_hash': computed_hash
                })
        
        return results
    
    def get_hash_statistics(self, table_name: str) -> Dict[str, Any]:
        """Get hash statistics"""
        table_info = self.db.tables.get(table_name)
        if not table_info:
            raise ValueError(f"Table {table_name} does not exist")
        
        try:
            table_data = pickle.loads(self.db._read_page(table_info['page']))
        except:
            return {'error': 'Failed to read table data'}
        
        hash_distribution = {}
        for row in table_data['rows']:
            hash_val = row.get('hash', '')
            if hash_val:
                if hash_val not in hash_distribution:
                    hash_distribution[hash_val] = []
                hash_distribution[hash_val].append(row['id'])
        
        duplicate_hashes = {k: v for k, v in hash_distribution.items() if len(v) > 1}
        
        return {
            'total_rows': len(table_data['rows']),
            'unique_hashes': len(hash_distribution),
            'duplicate_hash_count': len(duplicate_hashes),
            'duplicate_hashes': duplicate_hashes,
            'hash_collision_rate': (len(table_data['rows']) - len(hash_distribution)) / max(len(table_data['rows']), 1)
        }

class IRODB:
    """Main database class"""
    
    def __init__(self, db_path: str, auto_create: bool = True):
        self.db_path = db_path
        self.tables = {}
        self.page_cache = {}
        self.hash_manager = HashManager(self)
        
        if not os.path.exists(db_path):
            if auto_create:
                self._create_empty_db()
            else:
                raise DatabaseError(f"Database not found: {db_path}")
        else:
            self._load_metadata()
    
    def _create_empty_db(self):
        """Create new database file"""
        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        
        with open(self.db_path, 'wb') as f:
            # Write header
            f.write(MAGIC_HEADER)
            f.write(struct.pack('<H', VERSION))
            f.write(struct.pack('<Q', 0))  # Page count
            f.write(struct.pack('<Q', 0))  # Checksum
            f.write(struct.pack('<Q', 1))  # Next page
            f.write(b'\x00' * (PAGE_SIZE - 31))
            
            # Create metadata page
            metadata = {
                'tables': {},
                'indexes': {},
                'hash_indexes': {},
                'next_page': 2,
                'created_at': datetime.now().isoformat(),
                'version': VERSION
            }
            self._write_page(1, pickle.dumps(metadata))
        
        # Load the metadata
        self._load_metadata()
    
    def _load_metadata(self):
        """Load metadata from database"""
        try:
            with open(self.db_path, 'rb') as f:
                header = f.read(5)
                if header != MAGIC_HEADER:
                    # Try to create new database if corrupted
                    self._create_empty_db()
                    return
                
                version = struct.unpack('<H', f.read(2))[0]
                if version != VERSION:
                    raise DatabaseError(f"Unsupported version: {version}")
                
                metadata = pickle.loads(self._read_page(1))
                self.tables = metadata.get('tables', {})
        except Exception as e:
            # If loading fails, recreate the database
            self._create_empty_db()
    
    def _read_page(self, page_num: int) -> bytes:
        """Read a page from disk"""
        if page_num in self.page_cache:
            return self.page_cache[page_num]
        
        try:
            with open(self.db_path, 'rb') as f:
                f.seek(page_num * PAGE_SIZE)
                data = f.read(PAGE_SIZE)
                if not data:
                    raise PageError(f"Page {page_num} not found")
                self.page_cache[page_num] = data
                return data
        except Exception as e:
            raise PageError(f"Failed to read page {page_num}: {e}")
    
    def _write_page(self, page_num: int, data: bytes):
        """Write a page to disk"""
        try:
            if len(data) < PAGE_SIZE:
                data += b'\x00' * (PAGE_SIZE - len(data))
            elif len(data) > PAGE_SIZE:
                data = data[:PAGE_SIZE]
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
            
            with open(self.db_path, 'r+b') as f:
                f.seek(page_num * PAGE_SIZE)
                f.write(data)
            
            self.page_cache[page_num] = data
        except Exception as e:
            raise PageError(f"Failed to write page {page_num}: {e}")
    
    def _get_next_page(self) -> int:
        """Get next available page"""
        max_page = 1
        for table in self.tables.values():
            # Get table page
            page = table.get('page', 0)
            if page and page > max_page:
                max_page = page
            
            # Get hash index page
            hash_page = table.get('hash_index_page')
            if hash_page and hash_page > max_page:
                max_page = hash_page
        
        return max_page + 1
    
    def _save_metadata(self):
        """Save metadata to page 1"""
        metadata = {
            'tables': self.tables,
            'indexes': {},
            'hash_indexes': self.hash_manager.hash_indexes,
            'next_page': self._get_next_page(),
            'created_at': datetime.now().isoformat(),
            'version': VERSION
        }
        self._write_page(1, pickle.dumps(metadata))
    
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
        self._write_page(table_data['page'], pickle.dumps(page_data))
        
        if enable_hash_index:
            self._write_page(table_data['hash_index_page'], pickle.dumps({}))
        
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
            if not isinstance(data[field], field_type):
                raise TypeError(f"Field {field} must be of type {field_type.__name__}")
        
        # Load table data
        table_data = pickle.loads(self._read_page(table_info['page']))
        
        # Assign row ID
        row_id = table_data['auto_increment'] + 1
        table_data['auto_increment'] = row_id
        
        # Create row with hash
        row = {'id': row_id, **data}
        row_hash = self.hash_manager.calculate_row_hash(row)
        row['hash'] = row_hash
        
        # Add row
        table_data['rows'].append(row)
        table_info['rows'] = table_data['rows']
        
        # Update hash index
        if table_info.get('enable_hash_index', False):
            hash_page = table_info.get('hash_index_page')
            if hash_page:
                try:
                    hash_index = pickle.loads(self._read_page(hash_page))
                    if row_hash not in hash_index:
                        hash_index[row_hash] = []
                    if row_id not in hash_index[row_hash]:
                        hash_index[row_hash].append(row_id)
                    self._write_page(hash_page, pickle.dumps(hash_index))
                except:
                    pass
        
        # Save
        self._write_page(table_info['page'], pickle.dumps(table_data))
        self._save_metadata()
        
        return (row_id, row_hash) if return_hash else row_id
    
    def select(self, table_name: str, conditions: Optional[Dict[str, Any]] = None,
              use_hash: bool = False, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Select rows"""
        if table_name not in self.tables:
            raise TableError(f"Table {table_name} does not exist")
        
        if use_hash and conditions and 'hash' in conditions:
            return self.hash_manager.find_by_hash(table_name, conditions['hash'])
        
        table_data = pickle.loads(self._read_page(self.tables[table_name]['page']))
        rows = table_data['rows']
        
        if not conditions:
            return rows[:limit] if limit else rows.copy()
        
        results = []
        for row in rows:
            if all(row.get(k) == v for k, v in conditions.items()):
                results.append(row.copy())
                if limit and len(results) >= limit:
                    break
        
        return results
    
    def update(self, table_name: str, conditions: Dict[str, Any],
              updates: Dict[str, Any]) -> int:
        """Update rows"""
        if table_name not in self.tables:
            raise TableError(f"Table {table_name} does not exist")
        
        table_info = self.tables[table_name]
        schema = table_info['schema']
        table_data = pickle.loads(self._read_page(table_info['page']))
        
        # Validate updates
        for field in updates:
            if field not in schema:
                raise ValueError(f"Invalid field: {field}")
        
        updated_count = 0
        for row in table_data['rows']:
            if all(row.get(k) == v for k, v in conditions.items()):
                # Update fields
                for key, value in updates.items():
                    row[key] = value
                
                # Recalculate hash
                old_hash = row['hash']
                new_hash = self.hash_manager.calculate_row_hash(row)
                row['hash'] = new_hash
                
                # Update hash index
                if table_info.get('enable_hash_index', False):
                    hash_page = table_info.get('hash_index_page')
                    if hash_page:
                        try:
                            hash_index = pickle.loads(self._read_page(hash_page))
                            
                            # Remove from old hash
                            if old_hash in hash_index:
                                hash_index[old_hash] = [id for id in hash_index[old_hash] if id != row['id']]
                                if not hash_index[old_hash]:
                                    del hash_index[old_hash]
                            
                            # Add to new hash
                            if new_hash not in hash_index:
                                hash_index[new_hash] = []
                            if row['id'] not in hash_index[new_hash]:
                                hash_index[new_hash].append(row['id'])
                            
                            self._write_page(hash_page, pickle.dumps(hash_index))
                        except:
                            pass
                
                updated_count += 1
        
        if updated_count > 0:
            self._write_page(table_info['page'], pickle.dumps(table_data))
            self._save_metadata()
        
        return updated_count
    
    def delete(self, table_name: str, conditions: Dict[str, Any]) -> int:
        """Delete rows"""
        if table_name not in self.tables:
            raise TableError(f"Table {table_name} does not exist")
        
        table_info = self.tables[table_name]
        table_data = pickle.loads(self._read_page(table_info['page']))
        
        deleted_count = 0
        remaining_rows = []
        
        for row in table_data['rows']:
            if all(row.get(k) == v for k, v in conditions.items()):
                # Update hash index
                if table_info.get('enable_hash_index', False):
                    hash_page = table_info.get('hash_index_page')
                    if hash_page:
                        try:
                            hash_index = pickle.loads(self._read_page(hash_page))
                            if row['hash'] in hash_index:
                                hash_index[row['hash']] = [id for id in hash_index[row['hash']] if id != row['id']]
                                if not hash_index[row['hash']]:
                                    del hash_index[row['hash']]
                                self._write_page(hash_page, pickle.dumps(hash_index))
                        except:
                            pass
                deleted_count += 1
            else:
                remaining_rows.append(row)
        
        if deleted_count > 0:
            table_data['rows'] = remaining_rows
            self._write_page(table_info['page'], pickle.dumps(table_data))
            self._save_metadata()
        
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
            table_data = pickle.loads(self._read_page(table_info['page']))
            self._write_page(table_info['page'], pickle.dumps(table_data))
        
        self.page_cache.clear()
    
    def close(self):
        """Close database"""
        self.page_cache.clear()
        self._save_metadata()