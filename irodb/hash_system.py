"""
Hash management system for IRODB
"""

import hashlib
import json
import pickle
from typing import Any, Dict, List, Optional, Union
from datetime import datetime

from .constants import HASH_ALGORITHM
from .exceptions import HashError, IntegrityError

class HashManager:
    """Manages hash operations for the database"""
    
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
                hash_index = pickle.loads(self.db._read_page(hash_page))
                if hash_value in hash_index:
                    row_ids = hash_index[hash_value]
                    return self._get_rows_by_ids(table_name, row_ids)
                return []
        
        # Fallback to full scan
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
    
    def _get_rows_by_ids(self, table_name: str, row_ids: List[int]) -> List[Dict[str, Any]]:
        """Get rows by IDs"""
        table_data = pickle.loads(self.db._read_page(self.db.tables[table_name]['page']))
        id_set = set(row_ids)
        return [row.copy() for row in table_data['rows'] if row['id'] in id_set]
    
    def find_by_hashed_value(self, table_name: str, value: Any) -> List[Dict[str, Any]]:
        """Find rows by hashing a value"""
        hash_val = self.calculate_hash(value)
        return self.find_by_hash(table_name, hash_val)
    
    def find_by_hash_and_column(self, table_name: str, hash_value: str,
                               column: str, value: Any) -> List[Dict[str, Any]]:
        """Find by hash and column filter"""
        rows = self.find_by_hash(table_name, hash_value)
        return [row for row in rows if row.get(column) == value]
    
    def update_hash_index(self, table_name: str, hash_value: str,
                         row_id: int, operation: str):
        """Update hash index"""
        table_info = self.db.tables.get(table_name)
        if not table_info or not table_info.get('enable_hash_index', False):
            return
        
        hash_page = table_info.get('hash_index_page')
        if not hash_page:
            return
        
        hash_index = pickle.loads(self.db._read_page(hash_page))
        
        if operation == 'insert':
            if hash_value not in hash_index:
                hash_index[hash_value] = []
            if row_id not in hash_index[hash_value]:
                hash_index[hash_value].append(row_id)
        elif operation == 'delete':
            if hash_value in hash_index:
                hash_index[hash_value] = [id for id in hash_index[hash_value] if id != row_id]
                if not hash_index[hash_value]:
                    del hash_index[hash_value]
        elif operation == 'update':
            # Handle update (remove old, add new)
            pass
        
        self.db._write_page(hash_page, pickle.dumps(hash_index))
    
    def verify_hash_integrity(self, table_name: str) -> Dict[str, Any]:
        """Verify all hashes in a table"""
        table_info = self.db.tables.get(table_name)
        if not table_info:
            raise ValueError(f"Table {table_name} does not exist")
        
        table_data = pickle.loads(self.db._read_page(table_info['page']))
        
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
                    'computed_hash': computed_hash,
                    'data': row
                })
        
        return results
    
    def repair_hash_index(self, table_name: str):
        """Repair corrupted hash index"""
        table_info = self.db.tables.get(table_name)
        if not table_info:
            raise ValueError(f"Table {table_name} does not exist")
        
        table_data = pickle.loads(self.db._read_page(table_info['page']))
        
        # Rebuild hash index
        hash_index = {}
        for row in table_data['rows']:
            hash_val = row.get('hash', self.calculate_row_hash(row))
            row['hash'] = hash_val  # Ensure hash is set
            
            if hash_val not in hash_index:
                hash_index[hash_val] = []
            if row['id'] not in hash_index[hash_val]:
                hash_index[hash_val].append(row['id'])
        
        # Save updated data
        self.db._write_page(table_info['page'], pickle.dumps(table_data))
        
        # Save hash index
        if table_info.get('hash_index_page'):
            self.db._write_page(table_info['hash_index_page'], pickle.dumps(hash_index))
        
        return {'repaired_rows': len(table_data['rows']), 'unique_hashes': len(hash_index)}
    
    def get_hash_statistics(self, table_name: str) -> Dict[str, Any]:
        """Get hash statistics"""
        table_info = self.db.tables.get(table_name)
        if not table_info:
            raise ValueError(f"Table {table_name} does not exist")
        
        table_data = pickle.loads(self.db._read_page(table_info['page']))
        
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
    
    def compare_hashes(self, table_name: str, row_id: int) -> bool:
        """Compare stored hash with computed hash for a specific row"""
        table_info = self.db.tables.get(table_name)
        if not table_info:
            raise ValueError(f"Table {table_name} does not exist")
        
        table_data = pickle.loads(self.db._read_page(table_info['page']))
        
        for row in table_data['rows']:
            if row['id'] == row_id:
                stored_hash = row.get('hash', '')
                computed_hash = self.calculate_row_hash(row)
                return stored_hash == computed_hash
        
        return False