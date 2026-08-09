"""
Core database implementation for IRODB
"""

import os
import struct
import pickle
import json
from typing import Any, Dict, List, Optional, Union, Tuple
from datetime import datetime
import hashlib

from .constants import *
from .exceptions import *
from .hash_system import HashManager

class IRODB:
    """Main database class"""
    
    def __init__(self, db_path: str, auto_create: bool = True):
        self.db_path = db_path
        self.tables = {}
        self.page_cache = {}
        self.hash_manager = HashManager(self)
        self.metadata = {}
        self.constraints = {}
        
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
                'version': VERSION,
                'constraints': {}
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
                    self._create_empty_db()
                    return
                
                version = struct.unpack('<H', f.read(2))[0]
                if version != VERSION:
                    raise DatabaseError(f"Unsupported version: {version}")
                
                metadata = pickle.loads(self._read_page(1))
                self.tables = metadata.get('tables', {})
                self.metadata = metadata
                self.constraints = metadata.get('constraints', {})
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
                if len(data) == 0:
                    # Page doesn't exist, return empty page
                    data = b'\x00' * PAGE_SIZE
                self.page_cache[page_num] = data
                return data
        except Exception as e:
            # Return empty page on error
            return b'\x00' * PAGE_SIZE
    
    def _write_page(self, page_num: int, data: bytes):
        """Write a page to disk"""
        try:
            if len(data) < PAGE_SIZE:
                data = data.ljust(PAGE_SIZE, b'\x00')
            elif len(data) > PAGE_SIZE:
                data = data[:PAGE_SIZE]
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
            
            # Open in correct mode
            if os.path.exists(self.db_path):
                with open(self.db_path, 'r+b') as f:
                    f.seek(page_num * PAGE_SIZE)
                    f.write(data)
            else:
                with open(self.db_path, 'wb') as f:
                    # Write header first
                    f.write(MAGIC_HEADER)
                    f.write(struct.pack('<H', VERSION))
                    f.write(struct.pack('<Q', 0))
                    f.write(struct.pack('<Q', 0))
                    f.write(struct.pack('<Q', 1))
                    f.write(b'\x00' * (PAGE_SIZE - 31))
                    
                    # Then seek to page position
                    f.seek(page_num * PAGE_SIZE)
                    f.write(data)
            
            self.page_cache[page_num] = data
        except Exception as e:
            raise PageError(f"Failed to write page {page_num}: {e}")
    
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
    
    def _save_metadata(self):
        """Save metadata to page 1"""
        metadata = {
            'tables': self.tables,
            'indexes': {},
            'hash_indexes': self.hash_manager.hash_indexes,
            'next_page': self._get_next_page(),
            'created_at': datetime.now().isoformat(),
            'version': VERSION,
            'constraints': getattr(self, 'constraints', {})
        }
        self._write_page(1, pickle.dumps(metadata))
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
        try:
            page_data = self._read_page(table_info['page'])
            table_data = pickle.loads(page_data)
        except:
            table_data = {'rows': [], 'auto_increment': 0}
        
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
        
        # Update hash index
        if table_info.get('enable_hash_index', False):
            hash_page = table_info.get('hash_index_page')
            if hash_page:
                try:
                    hash_data = self._read_page(hash_page)
                    hash_index = pickle.loads(hash_data) if hash_data and len(hash_data) > 0 else {}
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
        
        try:
            page_data = self._read_page(self.tables[table_name]['page'])
            table_data = pickle.loads(page_data)
        except:
            return []
        
        rows = table_data.get('rows', [])
        
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
        
        try:
            page_data = self._read_page(table_info['page'])
            table_data = pickle.loads(page_data)
        except:
            return 0
        
        # Validate updates
        for field in updates:
            if field not in schema:
                raise ValueError(f"Invalid field: {field}")
        
        updated_count = 0
        for row in table_data.get('rows', []):
            if all(row.get(k) == v for k, v in conditions.items()):
                # Update fields
                for key, value in updates.items():
                    row[key] = value
                
                # Recalculate hash
                old_hash = row.get('hash', '')
                new_hash = self.hash_manager.calculate_row_hash(row)
                row['hash'] = new_hash
                
                # Update hash index
                if table_info.get('enable_hash_index', False):
                    hash_page = table_info.get('hash_index_page')
                    if hash_page:
                        try:
                            hash_data = self._read_page(hash_page)
                            hash_index = pickle.loads(hash_data) if hash_data and len(hash_data) > 0 else {}
                            
                            if old_hash in hash_index:
                                hash_index[old_hash] = [id for id in hash_index[old_hash] if id != row['id']]
                                if not hash_index[old_hash]:
                                    del hash_index[old_hash]
                            
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
        
        try:
            page_data = self._read_page(table_info['page'])
            table_data = pickle.loads(page_data)
        except:
            return 0
        
        deleted_count = 0
        remaining_rows = []
        
        for row in table_data.get('rows', []):
            if all(row.get(k) == v for k, v in conditions.items()):
                # Update hash index
                if table_info.get('enable_hash_index', False):
                    hash_page = table_info.get('hash_index_page')
                    if hash_page:
                        try:
                            hash_data = self._read_page(hash_page)
                            hash_index = pickle.loads(hash_data) if hash_data and len(hash_data) > 0 else {}
                            if row.get('hash') in hash_index:
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
            try:
                page_data = self._read_page(table_info['page'])
                table_data = pickle.loads(page_data)
                self._write_page(table_info['page'], pickle.dumps(table_data))
            except:
                pass
        
        self.page_cache.clear()
    
    def close(self):
        """Close database"""
        self.page_cache.clear()
        self._save_metadata()