"""
Index management for IRODB
"""

import pickle
import json
from typing import Any, Dict, List, Optional
from collections import defaultdict

from .exceptions import IndexError

class IndexManager:
    """Manages database indexes"""
    
    def __init__(self, db):
        self.db = db
        self.indexes = {}
    
    def create_index(self, table_name: str, column: str, index_name: str,
                    index_type: str = 'btree'):
        """Create an index on a column"""
        if table_name not in self.db.tables:
            raise IndexError(f"Table {table_name} does not exist")
        
        if index_name in self.indexes:
            raise IndexError(f"Index {index_name} already exists")
        
        table_info = self.db.tables[table_name]
        table_data = pickle.loads(self.db._read_page(table_info['page']))
        
        # Build index
        index_data = {}
        for row in table_data['rows']:
            if column in row:
                value = row[column]
                if value not in index_data:
                    index_data[value] = []
                index_data[value].append(row['id'])
        
        self.indexes[index_name] = {
            'table': table_name,
            'column': column,
            'type': index_type,
            'data': index_data,
            'page': self.db._get_next_page()
        }
        
        # Store index data
        self.db._write_page(self.indexes[index_name]['page'], pickle.dumps(index_data))
        self.db._save_metadata()
    
    def drop_index(self, index_name: str):
        """Drop an index"""
        if index_name not in self.indexes:
            raise IndexError(f"Index {index_name} does not exist")
        
        del self.indexes[index_name]
        self.db._save_metadata()
    
    def find_by_index(self, index_name: str, value: Any) -> List[Dict[str, Any]]:
        """Find rows using an index"""
        if index_name not in self.indexes:
            raise IndexError(f"Index {index_name} does not exist")
        
        index_info = self.indexes[index_name]
        table_name = index_info['table']
        
        if table_name not in self.db.tables:
            raise IndexError(f"Table {table_name} does not exist")
        
        # Load index data
        index_data = pickle.loads(self.db._read_page(index_info['page']))
        
        if value not in index_data:
            return []
        
        row_ids = index_data[value]
        return self._get_rows_by_ids(table_name, row_ids)
    
    def _get_rows_by_ids(self, table_name: str, row_ids: List[int]) -> List[Dict[str, Any]]:
        """Get rows by IDs"""
        table_data = pickle.loads(self.db._read_page(self.db.tables[table_name]['page']))
        id_set = set(row_ids)
        return [row.copy() for row in table_data['rows'] if row['id'] in id_set]
    
    def index_statistics(self, index_name: str) -> Dict[str, Any]:
        """Get statistics for an index"""
        if index_name not in self.indexes:
            raise IndexError(f"Index {index_name} does not exist")
        
        index_info = self.indexes[index_name]
        index_data = pickle.loads(self.db._read_page(index_info['page']))
        
        unique_values = len(index_data)
        total_entries = sum(len(ids) for ids in index_data.values())
        
        return {
            'name': index_name,
            'table': index_info['table'],
            'column': index_info['column'],
            'type': index_info['type'],
            'unique_values': unique_values,
            'total_entries': total_entries,
            'size': len(pickle.dumps(index_data))
        }