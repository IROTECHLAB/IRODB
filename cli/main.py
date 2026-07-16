#!/usr/bin/env python3
"""
Command-line interface for IRODB
"""

import sys
import os
import json
import argparse
from pathlib import Path

from irodb import IRODB
from irodb.exceptions import IRODBError

class IRODBCLI:
    """Command-line interface for IRODB"""
    
    def __init__(self):
        self.db = None
        self.current_db = None
    
    def run(self):
        parser = argparse.ArgumentParser(description='IRODB Command Line Interface')
        subparsers = parser.add_subparsers(dest='command', help='Command to execute')
        
        # Install command
        subparsers.add_parser('install', help='Install IRODB')
        
        # Create database command
        create_parser = subparsers.add_parser('create', help='Create a new database')
        create_parser.add_argument('name', help='Database name')
        
        # Open database command
        open_parser = subparsers.add_parser('open', help='Open a database')
        open_parser.add_argument('name', help='Database name')
        
        # Table commands
        table_parser = subparsers.add_parser('table', help='Table operations')
        table_subparsers = table_parser.add_subparsers(dest='table_command')
        
        # Create table
        create_table = table_subparsers.add_parser('create', help='Create a table')
        create_table.add_argument('table', help='Table name')
        create_table.add_argument('--schema', help='Schema as JSON string', required=True)
        create_table.add_argument('--hash-index', action='store_true', help='Enable hash index')
        
        # Insert command
        insert_parser = subparsers.add_parser('insert', help='Insert data')
        insert_parser.add_argument('table', help='Table name')
        insert_parser.add_argument('--data', help='Data as JSON string', required=True)
        
        # Select command
        select_parser = subparsers.add_parser('select', help='Select data')
        select_parser.add_argument('table', help='Table name')
        select_parser.add_argument('--where', help='Conditions as JSON string')
        select_parser.add_argument('--hash', help='Search by hash')
        select_parser.add_argument('--limit', type=int, help='Limit results')
        
        # Update command
        update_parser = subparsers.add_parser('update', help='Update data')
        update_parser.add_argument('table', help='Table name')
        update_parser.add_argument('--where', help='Conditions as JSON string', required=True)
        update_parser.add_argument('--set', help='Updates as JSON string', required=True)
        
        # Delete command
        delete_parser = subparsers.add_parser('delete', help='Delete data')
        delete_parser.add_argument('table', help='Table name')
        delete_parser.add_argument('--where', help='Conditions as JSON string', required=True)
        
        # Hash commands
        hash_parser = subparsers.add_parser('hash', help='Hash operations')
        hash_subparsers = hash_parser.add_subparsers(dest='hash_command')
        
        # Verify hash
        verify_hash = hash_subparsers.add_parser('verify', help='Verify hash integrity')
        verify_hash.add_argument('table', help='Table name')
        
        # Repair hash index
        repair_hash = hash_subparsers.add_parser('repair', help='Repair hash index')
        repair_hash.add_argument('table', help='Table name')
        
        # Hash statistics
        stats_hash = hash_subparsers.add_parser('stats', help='Hash statistics')
        stats_hash.add_argument('table', help='Table name')
        
        # Import/Export
        import_parser = subparsers.add_parser('import', help='Import from JSON')
        import_parser.add_argument('json_file', help='JSON file path')
        
        export_parser = subparsers.add_parser('export', help='Export to JSON')
        export_parser.add_argument('json_file', help='JSON file path')
        
        # Info command
        subparsers.add_parser('info', help='Database information')
        
        # Backup command
        backup_parser = subparsers.add_parser('backup', help='Backup database')
        backup_parser.add_argument('backup_path', help='Backup file path')
        
        # Close command
        subparsers.add_parser('close', help='Close database')
        
        args = parser.parse_args()
        
        if args.command == 'install':
            self.install()
        elif args.command == 'create':
            self.create_database(args.name)
        elif args.command == 'open':
            self.open_database(args.name)
        elif args.command == 'table':
            self.handle_table(args)
        elif args.command == 'insert':
            self.insert(args)
        elif args.command == 'select':
            self.select(args)
        elif args.command == 'update':
            self.update(args)
        elif args.command == 'delete':
            self.delete(args)
        elif args.command == 'hash':
            self.handle_hash(args)
        elif args.command == 'import':
            self.import_db(args)
        elif args.command == 'export':
            self.export_db(args)
        elif args.command == 'info':
            self.info()
        elif args.command == 'backup':
            self.backup(args)
        elif args.command == 'close':
            self.close()
        else:
            parser.print_help()
    
    def install(self):
        from irodb.core import DatabaseSetup
        DatabaseSetup.install()
    
    def create_database(self, name: str):
        from irodb.core import DatabaseSetup
        if not name.endswith('.irodb'):
            name += '.irodb'
        
        db = DatabaseSetup.create_database(name)
        self.db = db
        self.current_db = name
        print(f"Database created: {db.db_path}")
    
    def open_database(self, name: str):
        if not name.endswith('.irodb'):
            name += '.irodb'
        
        db_path = os.path.expanduser(f"~/.irodb/{name}")
        if not os.path.exists(db_path):
            print(f"Database not found: {db_path}")
            return
        
        self.db = IRODB(db_path)
        self.current_db = name
        print(f"Database opened: {db_path}")
    
    def handle_table(self, args):
        if not self.db:
            print("No database open")
            return
        
        if args.table_command == 'create':
            schema = json.loads(args.schema)
            self.db.create_table(args.table, schema, args.hash_index)
            print(f"Table {args.table} created")
        else:
            print(f"Unknown table command: {args.table_command}")
    
    def insert(self, args):
        if not self.db:
            print("No database open")
            return
        
        data = json.loads(args.data)
        row_id, row_hash = self.db.insert(args.table, data, return_hash=True)
        print(f"Inserted row ID: {row_id}, Hash: {row_hash}")
    
    def select(self, args):
        if not self.db:
            print("No database open")
            return
        
        if args.hash:
            results = self.db.hash_manager.find_by_hash(args.table, args.hash)
        elif args.where:
            conditions = json.loads(args.where)
            results = self.db.select(args.table, conditions, limit=args.limit)
        else:
            results = self.db.select(args.table, limit=args.limit)
        
        print(json.dumps(results, indent=2, default=str))
    
    def update(self, args):
        if not self.db:
            print("No database open")
            return
        
        conditions = json.loads(args.where)
        updates = json.loads(args.set)
        count = self.db.update(args.table, conditions, updates)
        print(f"Updated {count} rows")
    
    def delete(self, args):
        if not self.db:
            print("No database open")
            return
        
        conditions = json.loads(args.where)
        count = self.db.delete(args.table, conditions)
        print(f"Deleted {count} rows")
    
    def handle_hash(self, args):
        if not self.db:
            print("No database open")
            return
        
        if args.hash_command == 'verify':
            results = self.db.hash_manager.verify_hash_integrity(args.table)
            print(json.dumps(results, indent=2))
        elif args.hash_command == 'repair':
            results = self.db.hash_manager.repair_hash_index(args.table)
            print(f"Hash index repaired: {json.dumps(results)}")
        elif args.hash_command == 'stats':
            results = self.db.hash_manager.get_hash_statistics(args.table)
            print(json.dumps(results, indent=2))
    
    def import_db(self, args):
        if not self.db:
            print("No database open")
            return
        
        results = self.db.utils.import_from_json(args.json_file)
        print(f"Imported: {json.dumps(results)}")
    
    def export_db(self, args):
        if not self.db:
            print("No database open")
            return
        
        results = self.db.utils.export_to_json(args.json_file)
        print(f"Exported: {json.dumps(results)}")
    
    def info(self):
        if not self.db:
            print("No database open")
            return
        
        info = self.db.utils.get_database_info()
        print(json.dumps(info, indent=2))
    
    def backup(self, args):
        if not self.db:
            print("No database open")
            return
        
        results = self.db.utils.backup(args.backup_path)
        print(f"Backup created: {json.dumps(results)}")
    
    def close(self):
        if self.db:
            self.db.close()
            self.db = None
            self.current_db = None
            print("Database closed")
        else:
            print("No database open")

def main():
    cli = IRODBCLI()
    try:
        cli.run()
    except IRODBError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()