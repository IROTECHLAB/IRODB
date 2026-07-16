"""
Utility functions for IRODB
"""

import os
import shutil
import json
from typing import Any, Dict, List
from datetime import datetime

from .exceptions import DatabaseError

class DatabaseUtils:
    """Utility functions for database operations"""
    
    def __init__(self, db):
        self.db = db
    
    def backup(self, backup_path: str):
        """Create a backup of the database"""
        try:
            shutil.copy2(self.db.db_path, backup_path)
            return {
                'backup_path': backup_path,
                'timestamp': datetime.now().isoformat(),
                'size': os.path.getsize(backup_path)
            }
        except Exception as e:
            raise DatabaseError(f"Backup failed: {e}")
    
    def restore(self, backup_path: str):
        """Restore from backup"""
        if not os.path.exists(backup_path):
            raise DatabaseError(f"Backup not found: {backup_path}")
        
        try:
            shutil.copy2(backup_path, self.db.db_path)
            self.db.close()
            self.db._initialize_db()
            return {
                'restored_from': backup_path,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            raise DatabaseError(f"Restore failed: {e}")
    
    def export_to_json(self, json_path: str):
        """Export database to JSON"""
        data = {
            'metadata': {
                'exported_at': datetime.now().isoformat(),
                'version': '1.0'
            },
            'tables': {}
        }
        
        for table_name, table_info in self.db.tables.items():
            table_data = pickle.loads(self.db._read_page(table_info['page']))
            data['tables'][table_name] = {
                'schema': {k: str(v.__name__) for k, v in table_info['schema'].items()},
                'rows': table_data['rows'],
                'hash_index_enabled': table_info.get('enable_hash_index', False)
            }
        
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        return {'exported_to': json_path, 'tables': len(data['tables'])}
    
    def import_from_json(self, json_path: str):
        """Import database from JSON"""
        if not os.path.exists(json_path):
            raise DatabaseError(f"JSON file not found: {json_path}")
        
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        for table_name, table_data in data['tables'].items():
            # Create table
            schema = {}
            for field_name, field_type in table_data['schema'].items():
                if field_type == 'str':
                    schema[field_name] = str
                elif field_type == 'int':
                    schema[field_name] = int
                elif field_type == 'float':
                    schema[field_name] = float
                elif field_type == 'bool':
                    schema[field_name] = bool
                else:
                    schema[field_name] = str
            
            self.db.create_table(
                table_name, 
                schema, 
                enable_hash_index=table_data.get('hash_index_enabled', False)
            )
            
            # Insert rows
            for row in table_data['rows']:
                row_data = {k: v for k, v in row.items() if k not in ['id', 'hash']}
                self.db.insert(table_name, row_data)
        
        return {'imported_tables': len(data['tables'])}
    
    def get_table_size(self, table_name: str) -> Dict[str, Any]:
        """Get table size information"""
        if table_name not in self.db.tables:
            raise ValueError(f"Table {table_name} does not exist")
        
        table_info = self.db.tables[table_name]
        table_data = pickle.loads(self.db._read_page(table_info['page']))
        
        return {
            'table_name': table_name,
            'row_count': len(table_data['rows']),
            'page_count': 1 + (1 if table_info.get('enable_hash_index', False) else 0),
            'estimated_size_bytes': len(pickle.dumps(table_data)),
            'hash_index_enabled': table_info.get('enable_hash_index', False)
        }
    
    def get_database_info(self) -> Dict[str, Any]:
        """Get database information"""
        return {
            'path': self.db.db_path,
            'file_size_bytes': os.path.getsize(self.db.db_path),
            'tables_count': len(self.db.tables),
            'tables': list(self.db.tables.keys()),
            'total_rows': sum(len(pickle.loads(self.db._read_page(t['page']))['rows']) 
                            for t in self.db.tables.values()),
            'page_cache_size': len(self.db.page_cache)
        }