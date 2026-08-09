#!/usr/bin/env python3
"""
Command-line interface for IRODB
"""

import sys
import os
import argparse
import json
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from irodb.core import IRODB
except ImportError:
    from core import IRODB

try:
    from irodb.feature_sql import SQLParser
except ImportError:
    from feature_sql import SQLParser

try:
    from irodb.feature_validation import DataValidator
except ImportError:
    from feature_validation import DataValidator

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description='IRODB - Database CLI')
    parser.add_argument('db_path', help='Path to database file')
    parser.add_argument('--query', '-q', help='Execute SQL query')
    parser.add_argument('--interactive', '-i', action='store_true', help='Interactive mode')
    parser.add_argument('--create', action='store_true', help='Create database if not exists')
    parser.add_argument('--info', action='store_true', help='Show database info')
    parser.add_argument('--export', help='Export to JSON')
    parser.add_argument('--import-file', dest='import_path', help='Import from JSON')
    parser.add_argument('--backup', help='Backup database')
    parser.add_argument('--restore', help='Restore from backup')
    
    args = parser.parse_args()
    
    try:
        db = IRODB(args.db_path, auto_create=args.create)
        sql_parser = SQLParser(db)
        
        if args.info:
            show_info(db)
        elif args.query:
            result = sql_parser.execute(args.query)
            print(json.dumps(result, indent=2, default=str))
        elif args.interactive:
            interactive_mode(db, sql_parser)
        elif args.export:
            export_data(db, args.export)
        elif args.import_path:
            import_data(db, args.import_path)
        elif args.backup:
            backup_db(db, args.backup)
        elif args.restore:
            restore_db(db, args.restore)
        else:
            parser.print_help()
        
        db.close()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

def show_info(db):
    """Show database information"""
    info = {
        'path': db.db_path,
        'size': os.path.getsize(db.db_path),
        'tables': list(db.tables.keys()),
        'table_count': len(db.tables)
    }
    print(json.dumps(info, indent=2))

def interactive_mode(db, sql_parser):
    """Interactive mode"""
    print("IRODB Interactive Mode (type 'exit' to quit)")
    print("Enter SQL queries:")
    
    while True:
        try:
            query = input("irodb> ").strip()
            if query.lower() in ('exit', 'quit'):
                break
            if not query:
                continue
            
            result = sql_parser.execute(query)
            if isinstance(result, list):
                print(f"Found {len(result)} rows:")
                for row in result[:10]:
                    print(f"  {row}")
                if len(result) > 10:
                    print(f"  ... and {len(result) - 10} more")
            else:
                print(f"Result: {result}")
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}")

def export_data(db, export_path):
    """Export database to JSON"""
    try:
        from irodb.utils import DatabaseUtils
    except ImportError:
        from utils import DatabaseUtils
    utils = DatabaseUtils(db)
    result = utils.export_to_json(export_path)
    print(f"Exported to {export_path}")

def import_data(db, import_path):
    """Import from JSON"""
    try:
        from irodb.utils import DatabaseUtils
    except ImportError:
        from utils import DatabaseUtils
    utils = DatabaseUtils(db)
    result = utils.import_from_json(import_path)
    print(f"Imported {result['imported_tables']} tables from {import_path}")

def backup_db(db, backup_path):
    """Backup database"""
    try:
        from irodb.utils import DatabaseUtils
    except ImportError:
        from utils import DatabaseUtils
    utils = DatabaseUtils(db)
    result = utils.backup(backup_path)
    print(f"Backup created at {backup_path}")

def restore_db(db, restore_path):
    """Restore from backup"""
    try:
        from irodb.utils import DatabaseUtils
    except ImportError:
        from utils import DatabaseUtils
    utils = DatabaseUtils(db)
    result = utils.restore(restore_path)
    print(f"Restored from {restore_path}")

if __name__ == '__main__':
    main()