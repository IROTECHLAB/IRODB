#!/usr/bin/env python3
"""
IRODB Complete Example Usage
Demonstrates all features: Core CRUD, Full-Text Search, SQL, Validation, Hash, and CLI
"""

import os
import sys
import json
import time
from datetime import datetime
from typing import Dict, Any, List

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from irodb import IRODB, FullTextSearch, SQLParser, DataValidator
from irodb.exceptions import *

# ============================================================================
# CONFIGURATION
# ============================================================================

DB_PATH = "example_db.irodb"
JSON_EXPORT_PATH = "example_export.json"
BACKUP_PATH = "example_backup.irodb"

# ============================================================================
# DATA DEFINITIONS
# ============================================================================

PRODUCT_DATA = [
    {
        "name": "MacBook Pro 16",
        "price": 2499.99,
        "category": "electronics",
        "description": "Apple MacBook Pro with M3 Max chip, 16-inch display, 36GB RAM",
        "email": "macbook@apple.com",
        "stock": 10,
        "rating": 4.9
    },
    {
        "name": "Dell XPS 15",
        "price": 1899.99,
        "category": "electronics",
        "description": "Dell XPS 15 with Intel i9, 32GB RAM, 1TB SSD, 4K display",
        "email": "xps@dell.com",
        "stock": 15,
        "rating": 4.7
    },
    {
        "name": "Python Crash Course",
        "price": 39.99,
        "category": "books",
        "description": "A hands-on, project-based introduction to Python programming",
        "email": "python@nostarch.com",
        "stock": 50,
        "rating": 4.8
    },
    {
        "name": "Data Science Handbook",
        "price": 59.99,
        "category": "books",
        "description": "Comprehensive guide to data science with Python and machine learning",
        "email": "ds@oreilly.com",
        "stock": 30,
        "rating": 4.6
    },
    {
        "name": "Nike Running Shoes",
        "price": 89.99,
        "category": "clothing",
        "description": "Professional running shoes with advanced cushioning technology",
        "email": "shoes@nike.com",
        "stock": 25,
        "rating": 4.5
    },
    {
        "name": "Levi's Jeans",
        "price": 69.99,
        "category": "clothing",
        "description": "Classic Levi's 501 denim jeans, premium quality",
        "email": "jeans@levi.com",
        "stock": 40,
        "rating": 4.3
    }
]

EMPLOYEE_DATA = [
    {"name": "Alice Johnson", "department": "Engineering", "salary": 85000, "email": "alice@company.com", "position": "Senior Developer"},
    {"name": "Bob Smith", "department": "Sales", "salary": 65000, "email": "bob@company.com", "position": "Sales Manager"},
    {"name": "Charlie Brown", "department": "Engineering", "salary": 95000, "email": "charlie@company.com", "position": "Tech Lead"},
    {"name": "David Wilson", "department": "Sales", "salary": 58000, "email": "david@company.com", "position": "Sales Representative"},
    {"name": "Eve Davis", "department": "Engineering", "salary": 78000, "email": "eve@company.com", "position": "Software Engineer"},
    {"name": "Frank Miller", "department": "Marketing", "salary": 72000, "email": "frank@company.com", "position": "Marketing Director"},
    {"name": "Grace Lee", "department": "Marketing", "salary": 68000, "email": "grace@company.com", "position": "Marketing Specialist"}
]

CUSTOMER_DATA = [
    {"name": "John Doe", "email": "john@example.com", "age": 30, "city": "New York", "active": True},
    {"name": "Jane Smith", "email": "jane@example.com", "age": 25, "city": "London", "active": True},
    {"name": "Bob Johnson", "email": "bob@example.com", "age": 35, "city": "Tokyo", "active": False},
    {"name": "Alice Williams", "email": "alice@example.com", "age": 28, "city": "Paris", "active": True},
    {"name": "Charlie Davis", "email": "charlie@example.com", "age": 40, "city": "Berlin", "active": False}
]

# ============================================================================
# SECTION 1: DATABASE SETUP
# ============================================================================

def setup_database():
    """Initialize database with tables and constraints"""
    print("\n" + "="*70)
    print("SECTION 1: DATABASE SETUP")
    print("="*70)
    
    # Create database
    print(f"\n📁 Creating database: {DB_PATH}")
    db = IRODB(DB_PATH, auto_create=True)
    
    # Create tables
    print("\n📊 Creating tables...")
    
    # Products table
    db.create_table("products", {
        "name": str,
        "price": float,
        "category": str,
        "description": str,
        "email": str,
        "stock": int,
        "rating": float
    }, enable_hash_index=True)
    print("  ✓ 'products' table created with hash index")
    
    # Employees table
    db.create_table("employees", {
        "name": str,
        "department": str,
        "salary": int,
        "email": str,
        "position": str
    }, enable_hash_index=True)
    print("  ✓ 'employees' table created with hash index")
    
    # Customers table
    db.create_table("customers", {
        "name": str,
        "email": str,
        "age": int,
        "city": str,
        "active": bool
    }, enable_hash_index=True)
    print("  ✓ 'customers' table created with hash index")
    
    # Setup validation for products
    print("\n🔒 Setting up validation constraints...")
    validator = DataValidator(db)
    validator.add_table_constraints("products", {
        "name": {"required": True, "min_length": 3, "max_length": 100},
        "price": {"required": True, "min": 0.01, "max": 99999.99},
        "category": {"required": True, "allowed_values": ["electronics", "books", "clothing"]},
        "email": {"validator": "email", "required": True},
        "description": {"max_length": 500},
        "stock": {"required": True, "min": 0},
        "rating": {"min": 0, "max": 5}
    })
    print("  ✓ Product validation constraints added")
    
    validator.add_table_constraints("customers", {
        "name": {"required": True, "min_length": 2},
        "email": {"validator": "email", "required": True, "unique": True},
        "age": {"required": True, "min": 18, "max": 120},
        "city": {"required": True},
        "active": {"required": True}
    })
    print("  ✓ Customer validation constraints added")
    
    db.close()
    print("\n✅ Database setup complete!")
    return DB_PATH

# ============================================================================
# SECTION 2: DATA INSERTION
# ============================================================================

def insert_data():
    """Insert sample data into tables"""
    print("\n" + "="*70)
    print("SECTION 2: DATA INSERTION")
    print("="*70)
    
    db = IRODB(DB_PATH, auto_create=False)
    
    # Insert products
    print("\n📦 Inserting products...")
    for product in PRODUCT_DATA:
        try:
            row_id, hash_val = db.insert("products", product, return_hash=True)
            print(f"  ✓ {product['name']} (ID: {row_id}, Hash: {hash_val[:8]}...)")
        except Exception as e:
            print(f"  ✗ Failed to insert {product['name']}: {e}")
    
    # Insert employees
    print("\n👔 Inserting employees...")
    for employee in EMPLOYEE_DATA:
        try:
            row_id, hash_val = db.insert("employees", employee, return_hash=True)
            print(f"  ✓ {employee['name']} (ID: {row_id}, Dept: {employee['department']})")
        except Exception as e:
            print(f"  ✗ Failed to insert {employee['name']}: {e}")
    
    # Insert customers
    print("\n👤 Inserting customers...")
    for customer in CUSTOMER_DATA:
        try:
            row_id, hash_val = db.insert("customers", customer, return_hash=True)
            print(f"  ✓ {customer['name']} (ID: {row_id}, City: {customer['city']})")
        except Exception as e:
            print(f"  ✗ Failed to insert {customer['name']}: {e}")
    
    db.close()
    print("\n✅ Data insertion complete!")

# ============================================================================
# SECTION 3: CRUD OPERATIONS
# ============================================================================

def demonstrate_crud():
    """Demonstrate CRUD operations"""
    print("\n" + "="*70)
    print("SECTION 3: CRUD OPERATIONS")
    print("="*70)
    
    db = IRODB(DB_PATH, auto_create=False)
    
    # CREATE
    print("\n📝 CREATE - Insert new product:")
    new_product = {
        "name": "Samsung Galaxy S24",
        "price": 999.99,
        "category": "electronics",
        "description": "Samsung Galaxy S24 with AI features",
        "email": "galaxy@samsung.com",
        "stock": 20,
        "rating": 4.8
    }
    product_id = db.insert("products", new_product)
    print(f"  ✓ Inserted product with ID: {product_id}")
    
    # READ
    print("\n📖 READ - Select product by name:")
    results = db.select("products", {"name": "Samsung Galaxy S24"})
    for row in results:
        print(f"  - Found: {row['name']} (Price: ${row['price']}, Stock: {row['stock']})")
    
    # UPDATE
    print("\n✏️ UPDATE - Update product price:")
    updated = db.update("products", {"name": "Samsung Galaxy S24"}, {"price": 899.99})
    print(f"  ✓ Updated {updated} row(s)")
    
    # Verify update
    results = db.select("products", {"name": "Samsung Galaxy S24"})
    for row in results:
        print(f"  - New price: ${row['price']}")
    
    # DELETE
    print("\n🗑️ DELETE - Delete product:")
    deleted = db.delete("products", {"name": "Samsung Galaxy S24"})
    print(f"  ✓ Deleted {deleted} row(s)")
    
    # Verify delete
    results = db.select("products", {"name": "Samsung Galaxy S24"})
    print(f"  - Remaining rows: {len(results)}")
    
    db.close()
    print("\n✅ CRUD operations complete!")

# ============================================================================
# SECTION 4: FULL-TEXT SEARCH
# ============================================================================

def demonstrate_fulltext_search():
    """Demonstrate full-text search"""
    print("\n" + "="*70)
    print("SECTION 4: FULL-TEXT SEARCH")
    print("="*70)
    
    db = IRODB(DB_PATH, auto_create=False)
    fulltext = FullTextSearch(db)
    
    # Create full-text index
    print("\n🔍 Creating full-text index...")
    try:
        index_name = fulltext.create_fulltext_index("products", ["name", "description"], "products_ft")
        print(f"  ✓ Index created: {index_name}")
    except Exception as e:
        print(f"  ✗ Failed to create index: {e}")
        db.close()
        return
    
    # Search examples
    searches = [
        "laptop computer",
        "python programming",
        "running shoes",
        "machine learning data science"
    ]
    
    print("\n🔎 Full-text search results:")
    for query in searches:
        print(f"\n  Query: '{query}'")
        results = fulltext.search("products", query, limit=3)
        if results:
            for i, result in enumerate(results, 1):
                score = result.get('_score', 0)
                print(f"    {i}. {result['name']} (Score: {score:.3f})")
        else:
            print("    No results found")
    
    # Get index statistics
    print("\n📊 Index statistics:")
    stats = fulltext.get_index_statistics("products_ft")
    print(f"  - Unique terms: {stats['unique_terms']}")
    print(f"  - Total occurrences: {stats['total_term_occurrences']}")
    print(f"  - Top terms: {stats['top_terms'][:5]}")
    
    db.close()
    print("\n✅ Full-text search complete!")

# ============================================================================
# SECTION 5: SQL QUERIES
# ============================================================================

def demonstrate_sql():
    """Demonstrate SQL-like queries"""
    print("\n" + "="*70)
    print("SECTION 5: SQL-LIKE QUERIES")
    print("="*70)
    
    db = IRODB(DB_PATH, auto_create=False)
    sql = SQLParser(db)
    
    queries = [
        ("SELECT * FROM products WHERE category = 'electronics'", "Electronics products"),
        ("SELECT name, price FROM products WHERE price > 500 ORDER BY price DESC", "Expensive products"),
        ("SELECT name, salary, department FROM employees WHERE department = 'Engineering'", "Engineering employees"),
        ("SELECT name, age, city FROM customers WHERE active = true", "Active customers"),
        ("SELECT category, AVG(price) as avg_price FROM products GROUP BY category", "Average price by category"),
    ]
    
    print("\n📋 SQL Query results:")
    for query, description in queries:
        print(f"\n  {description}:")
        print(f"  Query: {query}")
        try:
            results = sql.execute(query)
            if isinstance(results, list):
                if results:
                    for i, row in enumerate(results[:5], 1):
                        print(f"    {i}. {row}")
                    if len(results) > 5:
                        print(f"    ... and {len(results) - 5} more")
                else:
                    print("    No results")
            else:
                print(f"    Result: {results}")
        except Exception as e:
            print(f"    ✗ Query failed: {e}")
    
    db.close()
    print("\n✅ SQL queries complete!")

# ============================================================================
# SECTION 6: HASH FEATURES
# ============================================================================

def demonstrate_hash_features():
    """Demonstrate hash-based features"""
    print("\n" + "="*70)
    print("SECTION 6: HASH FEATURES")
    print("="*70)
    
    db = IRODB(DB_PATH, auto_create=False)
    
    # Verify hash integrity
    print("\n🔐 Hash integrity verification:")
    for table in ["products", "employees", "customers"]:
        integrity = db.verify_hash_integrity(table)
        print(f"  {table}: {integrity['valid_hashes']}/{integrity['total_rows']} valid")
    
    # Get hash statistics
    print("\n📊 Hash statistics:")
    for table in ["products", "employees", "customers"]:
        stats = db.get_hash_statistics(table)
        print(f"  {table}: {stats['unique_hashes']} unique hashes, collision rate: {stats['hash_collision_rate']:.2%}")
    
    # Find by hash
    print("\n🔎 Finding by hash:")
    first_product = db.select("products", limit=1)[0]
    hash_val = first_product['hash']
    print(f"  Searching for hash of '{first_product['name']}'...")
    results = db.find_by_hash("products", hash_val)
    for result in results:
        print(f"  ✓ Found: {result['name']} (ID: {result['id']})")
    
    # Find by hashed value
    print("\n🔎 Finding by hashed value:")
    search_value = "MacBook Pro 16"
    results = db.find_by_hashed_value("products", search_value)
    for result in results:
        print(f"  ✓ Found: {result['name']} (ID: {result['id']})")
    
    db.close()
    print("\n✅ Hash features complete!")

# ============================================================================
# SECTION 7: VALIDATION
# ============================================================================

def demonstrate_validation():
    """Demonstrate validation and constraints"""
    print("\n" + "="*70)
    print("SECTION 7: DATA VALIDATION")
    print("="*70)
    
    db = IRODB(DB_PATH, auto_create=False)
    validator = DataValidator(db)
    
    # Test valid data
    print("\n✅ Testing valid data:")
    valid_product = {
        "name": "Valid Product",
        "price": 99.99,
        "category": "books",
        "description": "A valid product description",
        "email": "valid@store.com",
        "stock": 10,
        "rating": 4.5
    }
    try:
        validator.validate_row("products", valid_product)
        print("  ✓ Valid product passed validation")
    except Exception as e:
        print(f"  ✗ Validation failed: {e}")
    
    # Test invalid data
    print("\n❌ Testing invalid data:")
    invalid_cases = [
        ("Missing name", {"price": 99.99, "category": "books", "description": "Invalid", "email": "invalid@store.com", "stock": 10, "rating": 4.5}),
        ("Invalid category", {"name": "Invalid", "price": 99.99, "category": "invalid", "description": "Invalid", "email": "invalid@store.com", "stock": 10, "rating": 4.5}),
        ("Invalid email", {"name": "Invalid", "price": 99.99, "category": "books", "description": "Invalid", "email": "invalid", "stock": 10, "rating": 4.5}),
        ("Negative price", {"name": "Invalid", "price": -10.0, "category": "books", "description": "Invalid", "email": "invalid@store.com", "stock": 10, "rating": 4.5}),
        ("Stock negative", {"name": "Invalid", "price": 99.99, "category": "books", "description": "Invalid", "email": "invalid@store.com", "stock": -5, "rating": 4.5}),
    ]
    
    for case_desc, invalid_data in invalid_cases:
        try:
            validator.validate_row("products", invalid_data)
            print(f"  ✗ {case_desc}: Validation should have failed")
        except Exception as e:
            print(f"  ✓ {case_desc}: Caught error: {e}")
    
    # Test unique constraint
    print("\n🔒 Testing unique constraint:")
    try:
        # Try to insert customer with duplicate email
        duplicate_customer = {
            "name": "Duplicate User",
            "email": "john@example.com",  # Already exists in CUSTOMER_DATA
            "age": 25,
            "city": "Test City",
            "active": True
        }
        db.insert("customers", duplicate_customer)
        print("  ✗ Duplicate email should have been rejected")
    except Exception as e:
        print(f"  ✓ Duplicate caught: {e}")
    
    db.close()
    print("\n✅ Validation complete!")

# ============================================================================
# SECTION 8: UTILITY OPERATIONS
# ============================================================================

def demonstrate_utilities():
    """Demonstrate utility operations"""
    print("\n" + "="*70)
    print("SECTION 8: UTILITY OPERATIONS")
    print("="*70)
    
    from irodb.utils import DatabaseUtils
    
    db = IRODB(DB_PATH, auto_create=False)
    utils = DatabaseUtils(db)
    
    # Get database info
    print("\n📊 Database information:")
    info = utils.get_database_info()
    print(f"  - Database size: {info['file_size_bytes']} bytes")
    print(f"  - Tables: {info['tables']}")
    print(f"  - Total rows: {info['total_rows']}")
    
    # Get table sizes
    print("\n📏 Table sizes:")
    for table in info['tables']:
        size_info = utils.get_table_size(table)
        print(f"  - {table}: {size_info['row_count']} rows, {size_info['estimated_size_bytes']} bytes")
    
    # Export to JSON
    print(f"\n💾 Exporting to {JSON_EXPORT_PATH}...")
    result = utils.export_to_json(JSON_EXPORT_PATH)
    print(f"  ✓ Exported {result['tables']} tables")
    
    # Backup
    print(f"\n💾 Creating backup at {BACKUP_PATH}...")
    result = utils.backup(BACKUP_PATH)
    print(f"  ✓ Backup created: {result['size']} bytes")
    
    db.close()
    print("\n✅ Utilities complete!")

# ============================================================================
# SECTION 9: PERFORMANCE TEST
# ============================================================================

def demonstrate_performance():
    """Demonstrate performance"""
    print("\n" + "="*70)
    print("SECTION 9: PERFORMANCE TEST")
    print("="*70)
    
    db = IRODB(DB_PATH, auto_create=False)
    
    # Create performance test table
    db.create_table("perf_test", {
        "id": int,
        "data": str,
        "value": float,
        "timestamp": str
    }, enable_hash_index=True)
    
    # Insert performance test
    print("\n⚡ Performance test:")
    
    # Insert 1000 rows
    start_time = time.time()
    print("  Inserting 1000 rows...")
    for i in range(1000):
        db.insert("perf_test", {
            "id": i,
            "data": f"Performance test data {i}",
            "value": i * 1.23456789,
            "timestamp": datetime.now().isoformat()
        })
    insert_time = time.time() - start_time
    print(f"  ✓ Insert time: {insert_time:.3f} seconds ({1000/insert_time:.1f} rows/sec)")
    
    # Select all rows
    start_time = time.time()
    results = db.select("perf_test")
    select_time = time.time() - start_time
    print(f"  ✓ Select {len(results)} rows: {select_time:.3f} seconds")
    
    # Select with condition
    start_time = time.time()
    results = db.select("perf_test", {"id": 500})
    select_time = time.time() - start_time
    print(f"  ✓ Select with condition: {select_time:.3f} seconds")
    
    # Update rows
    start_time = time.time()
    updated = db.update("perf_test", {"id": {"$lt": 100}}, {"value": 999.99})
    update_time = time.time() - start_time
    print(f"  ✓ Updated {updated} rows: {update_time:.3f} seconds")
    
    # Delete all rows
    start_time = time.time()
    deleted = db.delete("perf_test", {})
    delete_time = time.time() - start_time
    print(f"  ✓ Deleted {deleted} rows: {delete_time:.3f} seconds")
    
    db.close()
    print("\n✅ Performance test complete!")

# ============================================================================
# SECTION 10: CLEANUP
# ============================================================================

def cleanup():
    """Clean up example files"""
    print("\n" + "="*70)
    print("SECTION 10: CLEANUP")
    print("="*70)
    
    files_to_clean = [DB_PATH, JSON_EXPORT_PATH, BACKUP_PATH]
    
    for file_path in files_to_clean:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"  ✓ Removed: {file_path}")
            except Exception as e:
                print(f"  ✗ Failed to remove {file_path}: {e}")
        else:
            print(f"  - File not found: {file_path}")
    
    print("\n✅ Cleanup complete!")

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main execution function"""
    print("="*70)
    print("IRODB COMPLETE EXAMPLE USAGE")
    print("="*70)
    print(f"Python: {sys.version}")
    print(f"Database: {DB_PATH}")
    
    try:
        # Run all sections
        setup_database()
        insert_data()
        demonstrate_crud()
        demonstrate_fulltext_search()
        demonstrate_sql()
        demonstrate_hash_features()
        demonstrate_validation()
        demonstrate_utilities()
        demonstrate_performance()
        
        # Summary
        print("\n" + "="*70)
        print("EXECUTION SUMMARY")
        print("="*70)
        print("✅ All demonstrations completed successfully!")
        print(f"📁 Database: {DB_PATH}")
        print(f"💾 Export: {JSON_EXPORT_PATH}")
        print(f"💾 Backup: {BACKUP_PATH}")
        
        # Ask for cleanup
        print("\n" + "="*70)
        response = input("🗑️  Clean up all files? (y/n): ").strip().lower()
        if response in ('y', 'yes'):
            cleanup()
        else:
            print("  ℹ️  Files kept for inspection")
            
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n" + "="*70)
        print("END OF EXAMPLE")
        print("="*70)

if __name__ == "__main__":
    main()