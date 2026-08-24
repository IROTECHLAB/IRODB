#!/usr/bin/env python3
"""
Command-line interface for IRODB
"""

import sys
import os
import argparse
import json
from datetime import datetime
from irodb.constants import VERSION
from irodb import __version__
from irodb.exceptions import IRODBError, SQLError, DatabaseError, PageError

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
    from irodb.feature_query import IRODBQuery
except ImportError:
    from feature_query import IRODBQuery

try:
    from irodb.feature_validation import DataValidator
except ImportError:
    from feature_validation import DataValidator

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description='IRODB - Database CLI')
    parser.add_argument('--version', action='version', version=f'irodb {__version__}')
    parser.add_argument('db_path', nargs='?', help='Path to database file')
    parser.add_argument('--query', '-q', '--irodb-query', dest='irodb_query', help='Execute an injection-safe IRODB Query')
    parser.add_argument('--interactive', '-i', action='store_true', help='Interactive mode')
    parser.add_argument('--create', action='store_true', help='Create database if not exists')
    parser.add_argument('--info', action='store_true', help='Show database info')
    parser.add_argument('--export', help='Export to JSON')
    parser.add_argument('--import-file', dest='import_path', help='Import from JSON')
    parser.add_argument('--backup', help='Backup database')
    parser.add_argument('--restore', help='Restore from backup')
    parser.add_argument('--table', help='Table for a row operation')
    parser.add_argument('--insert-json', dest='insert_json', help='Insert one row from a JSON object')
    parser.add_argument('--update-json', dest='update_json', help='Update fields from a JSON object')
    parser.add_argument('--where-json', dest='where_json', help='Row conditions for update/delete')
    parser.add_argument('--delete', action='store_true', help='Delete rows matching --where-json')
    parser.add_argument('--select', action='store_true', help='Select rows, optionally filtered by --where-json')
    parser.add_argument('--dump-binary', action='store_true', help='Print a safe structural summary without decoding raw bytes')
    parser.add_argument('--key-env', default='IRODB_KEY', help='Environment variable containing the current database encryption passphrase')
    parser.add_argument('--rekey', action='store_true', help='Change the passphrase of an existing encrypted database')
    parser.add_argument('--new-key-env', default='IRODB_NEW_KEY', help='Environment variable containing the replacement passphrase for --rekey')
    
    args = parser.parse_args()
    
    if not args.db_path:
        parser.error('db_path is required unless --version is used')

    try:
        encryption_key = os.environ.get(args.key_env)
        db = IRODB(args.db_path, auto_create=args.create, encryption_key=encryption_key)
        sql_parser = SQLParser(db)
        irodb_query = IRODBQuery(db)
        
        if args.rekey:
            if args.create:
                raise ValueError('--rekey cannot be combined with --create')
            new_key = os.environ.get(args.new_key_env)
            if not new_key:
                raise ValueError(f"Set {args.new_key_env} to the replacement encryption passphrase")
            def progress(current, total):
                print(f"\rRe-keying pages: {current}/{total}", end='', file=sys.stderr, flush=True)
            db.rekey(new_key, progress_callback=progress)
            print()
            print("Re-key completed successfully.")
        elif args.info:
            show_info(db)
        elif args.irodb_query:
            statement = args.irodb_query.strip()
            legacy_sql = statement.upper().startswith((
                "SELECT ", "INSERT ", "UPDATE ", "DELETE ",
                "CREATE TABLE ", "DROP TABLE ",
            ))
            result = sql_parser.execute(statement) if legacy_sql else irodb_query.execute(statement)
            print(json.dumps(result, indent=2, default=str))
        elif args.interactive:
            interactive_mode(db, irodb_query)
        elif args.export:
            export_data(db, args.export)
        elif args.import_path:
            import_data(db, args.import_path)
        elif args.backup:
            backup_db(db, args.backup)
        elif args.restore:
            restore_db(db, args.restore)
        elif args.insert_json:
            require_table(args.table)
            row = json.loads(args.insert_json)
            print(json.dumps({'id': db.insert(args.table, row)}, indent=2))
        elif args.update_json:
            require_table(args.table)
            where = json.loads(args.where_json or '{}')
            updates = json.loads(args.update_json)
            print(json.dumps({'updated': db.update(args.table, where, updates)}, indent=2))
        elif args.delete:
            require_table(args.table)
            where = json.loads(args.where_json or '{}')
            print(json.dumps({'deleted': db.delete(args.table, where)}, indent=2))
        elif args.select:
            require_table(args.table)
            where = json.loads(args.where_json) if args.where_json else None
            print(json.dumps(db.select(args.table, where), indent=2, default=str))
        elif args.dump_binary:
            print(json.dumps({'path': db.db_path, 'format': 'IRODB custom binary', 'version': VERSION, 'tables': list(db.tables)}, indent=2))
        else:
            parser.print_help()
        
        db.close()
    except SQLError as e:
        print(f"SQL error: {e}. Check the statement syntax, table name, and column names.", file=sys.stderr)
        sys.exit(2)
    except (DatabaseError, PageError) as e:
        print(f"Database error: {e}. Check the key, file permissions, WAL, or database backup.", file=sys.stderr)
        sys.exit(3)
    except IRODBError as e:
        print(f"IRODB error: {e}", file=sys.stderr)
        sys.exit(1)
    except (ValueError, KeyError, TypeError) as e:
        print(f"Input error: {e}", file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)

def require_table(table):
    if not table:
        raise ValueError('--table is required for this operation')


def show_info(db):
    """Show database information"""
    info = {
        'path': db.db_path,
        'size': os.path.getsize(db.db_path),
        'tables': list(db.tables.keys()),
        'table_count': len(db.tables)
    }
    print(json.dumps(info, indent=2))

def interactive_mode(db, query_engine):
    """Interactive mode"""
    print("IRODB Interactive Mode (type 'exit' to quit)")
    print("Enter IRODB Queries:")
    
    while True:
        try:
            query = input("irodb> ").strip()
            if query.lower() in ('exit', 'quit'):
                break
            if not query:
                continue
            
            result = query_engine.execute(query)
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