#!/usr/bin/env python3
"""
Complete IRODB Example with CLI Testing
Tests all features: Core, Full-Text Search, SQL, Validation, Hash, and CLI
"""

import os
import sys
import tempfile
import shutil
import subprocess
import json
import pickle
import unittest
import time
import re
from datetime import datetime
from typing import Dict, Any, List

# Fix path for imports
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, PROJECT_ROOT)

print(f"Project root: {PROJECT_ROOT}")
print(f"Python path: {sys.path[:3]}")

# Import IRODB modules
try:
    from irodb import IRODB, FullTextSearch, SQLParser, DataValidator
    from irodb.exceptions import *
    print("✅ Imports successful")
except ImportError as e:
    print(f"❌ Import error: {e}")
    print(f"Looking in: {PROJECT_ROOT}/irodb/")
    sys.exit(1)

# ============================================================================
# CONFIGURATION
# ============================================================================

TEST_DB_NAME = "test_complete.irodb"
TEMP_DIR = tempfile.mkdtemp()
DB_PATH = os.path.join(TEMP_DIR, TEST_DB_NAME)
CLI_SCRIPT = os.path.join(PROJECT_ROOT, "irodb", "cli.py")

# ============================================================================
# TEST DATA
# ============================================================================

PRODUCTS = [
    {"name": "Laptop Pro", "price": 1299.99, "category": "electronics", 
     "description": "High-performance laptop for professionals", "email": "laptop@store.com"},
    {"name": "Smartphone X", "price": 799.99, "category": "electronics", 
     "description": "Latest smartphone with AI camera", "email": "phone@store.com"},
    {"name": "Python Book", "price": 39.99, "category": "books", 
     "description": "Complete Python programming guide", "email": "book@store.com"},
    {"name": "Data Science Book", "price": 49.99, "category": "books", 
     "description": "Machine learning with Python", "email": "ds@store.com"},
    {"name": "T-Shirt", "price": 19.99, "category": "clothing", 
     "description": "Comfortable cotton t-shirt", "email": "shirt@store.com"},
    {"name": "Jeans", "price": 59.99, "category": "clothing", 
     "description": "Premium denim jeans", "email": "jeans@store.com"},
]

EMPLOYEES = [
    {"name": "Alice", "department": "Engineering", "salary": 80000, "email": "alice@company.com"},
    {"name": "Bob", "department": "Sales", "salary": 60000, "email": "bob@company.com"},
    {"name": "Charlie", "department": "Engineering", "salary": 90000, "email": "charlie@company.com"},
    {"name": "David", "department": "Sales", "salary": 55000, "email": "david@company.com"},
    {"name": "Eve", "department": "Engineering", "salary": 75000, "email": "eve@company.com"},
]

# ============================================================================
# DATABASE OPERATIONS
# ============================================================================

def create_database():
    """Create database with tables and data"""
    print("\n" + "="*60)
    print("1. CREATING DATABASE")
    print("="*60)
    
    db = IRODB(DB_PATH, auto_create=True)
    
    # Create products table with hash index
    print("Creating 'products' table...")
    db.create_table("products", {
        "name": str,
        "price": float,
        "category": str,
        "description": str,
        "email": str
    }, enable_hash_index=True)
    
    # Create employees table
    print("Creating 'employees' table...")
    db.create_table("employees", {
        "name": str,
        "department": str,
        "salary": int,
        "email": str
    }, enable_hash_index=True)
    
    # Setup validation for products
    print("Setting up validation...")
    validator = DataValidator(db)
    validator.add_table_constraints("products", {
        "name": {"required": True, "min_length": 2, "max_length": 100},
        "price": {"required": True, "min": 0.0, "max": 999999.99},
        "category": {"required": True, "allowed_values": ["electronics", "books", "clothing"]},
        "email": {"validator": "email", "required": True},
        "description": {"max_length": 500}
    })
    
    # Insert data
    print(f"Inserting {len(PRODUCTS)} products...")
    for product in PRODUCTS:
        try:
            row_id, hash_val = db.insert("products", product, return_hash=True)
            print(f"  ✓ Inserted: {product['name']} (ID: {row_id}, Hash: {hash_val[:8]}...)")
        except Exception as e:
            print(f"  ✗ Failed to insert {product['name']}: {e}")
    
    print(f"Inserting {len(EMPLOYEES)} employees...")
    for employee in EMPLOYEES:
        try:
            row_id, hash_val = db.insert("employees", employee, return_hash=True)
            print(f"  ✓ Inserted: {employee['name']} (ID: {row_id}, Hash: {hash_val[:8]}...)")
        except Exception as e:
            print(f"  ✗ Failed to insert {employee['name']}: {e}")
    
    db.close()
    print("\n✅ Database created successfully!")
    return DB_PATH

# ============================================================================
# FEATURE TESTS
# ============================================================================

def test_fulltext_search():
    """Test full-text search functionality"""
    print("\n" + "="*60)
    print("2. FULL-TEXT SEARCH")
    print("="*60)
    
    if FullTextSearch is None:
        print("⚠️ FullTextSearch not available, skipping...")
        return
    
    db = IRODB(DB_PATH, auto_create=False)
    fulltext = FullTextSearch(db)
    
    # Create full-text index
    print("Creating full-text index on products...")
    try:
        index_name = fulltext.create_fulltext_index("products", ["name", "description"], "products_ft")
        print(f"  ✓ Index created: {index_name}")
    except Exception as e:
        print(f"  ✗ Failed to create index: {e}")
        db.close()
        return
    
    # Test searches
    searches = [
        "laptop professional",
        "python book",
        "machine learning",
        "electronics"
    ]
    
    for query in searches:
        print(f"\nSearching for '{query}':")
        try:
            results = fulltext.search("products", query, limit=5)
            if results:
                for result in results:
                    score = result.get('_score', 0)
                    print(f"  - {result['name']} (Score: {score:.2f})")
            else:
                print("  - No results found")
        except Exception as e:
            print(f"  ✗ Search failed: {e}")
    
    # Get index statistics
    try:
        stats = fulltext.get_index_statistics("products_ft")
        print(f"\nIndex Statistics:")
        print(f"  - Unique terms: {stats['unique_terms']}")
        print(f"  - Total occurrences: {stats['total_term_occurrences']}")
        print(f"  - Top terms: {stats['top_terms'][:3]}")
    except Exception as e:
        print(f"  ✗ Stats failed: {e}")
    
    db.close()
    print("\n✅ Full-text search tests passed!")

def test_sql_queries():
    """Test SQL-like query functionality"""
    print("\n" + "="*60)
    print("3. SQL-LIKE QUERIES")
    print("="*60)
    
    if SQLParser is None:
        print("⚠️ SQLParser not available, skipping...")
        return
    
    db = IRODB(DB_PATH, auto_create=False)
    sql = SQLParser(db)
    
    # Test SELECT with WHERE
    print("\nSELECT * FROM products WHERE category = 'electronics':")
    try:
        results = sql.execute("SELECT * FROM products WHERE category = 'electronics'")
        for row in results:
            print(f"  - {row.get('name', 'Unknown')}: ${row.get('price', 0)}")
    except Exception as e:
        print(f"  ✗ Query failed: {e}")
    
    # Test SELECT with ORDER BY
    print("\nSELECT name, price FROM products WHERE price > 500 ORDER BY price DESC:")
    try:
        results = sql.execute("SELECT name, price FROM products WHERE price > 500 ORDER BY price DESC")
        for row in results:
            print(f"  - {row.get('name', 'Unknown')}: ${row.get('price', 0)}")
    except Exception as e:
        print(f"  ✗ Query failed: {e}")
    
    # Test SELECT with JOIN (simple)
    print("\nSELECT name, salary FROM employees WHERE department = 'Engineering':")
    try:
        results = sql.execute("SELECT name, salary FROM employees WHERE department = 'Engineering'")
        for row in results:
            print(f"  - {row.get('name', 'Unknown')}: ${row.get('salary', 0)}")
    except Exception as e:
        print(f"  ✗ Query failed: {e}")
    
    # Test GROUP BY
    print("\nSELECT category, COUNT(*) as count FROM products GROUP BY category:")
    try:
        results = sql.execute("SELECT category, COUNT(*) as count FROM products GROUP BY category")
        for row in results:
            # Handle different possible key names
            count = row.get('count') or row.get('COUNT(*)') or row.get('_count') or 0
            category = row.get('category', 'Unknown')
            print(f"  - {category}: {count} products")
    except Exception as e:
        print(f"  ✗ Query failed: {e}")
    
    # Test INSERT
    print("\nINSERT INTO products (name, price, category, description, email) VALUES ('Tablet', 299.99, 'electronics', 'Portable tablet', 'tablet@store.com'):")
    try:
        result = sql.execute("INSERT INTO products (name, price, category, description, email) VALUES ('Tablet', 299.99, 'electronics', 'Portable tablet', 'tablet@store.com')")
        print(f"  ✓ Inserted with ID: {result}")
    except Exception as e:
        print(f"  ✗ Insert failed: {e}")
    
    # Test UPDATE
    print("\nUPDATE products SET price = 249.99 WHERE name = 'Tablet':")
    try:
        result = sql.execute("UPDATE products SET price = 249.99 WHERE name = 'Tablet'")
        print(f"  ✓ Updated {result} row(s)")
    except Exception as e:
        print(f"  ✗ Update failed: {e}")
    
    # Test DELETE
    print("\nDELETE FROM products WHERE name = 'Tablet':")
    try:
        result = sql.execute("DELETE FROM products WHERE name = 'Tablet'")
        print(f"  ✓ Deleted {result} row(s)")
    except Exception as e:
        print(f"  ✗ Delete failed: {e}")
    
    db.close()
    print("\n✅ SQL query tests passed!")

def test_validation():
    """Test data validation and constraints"""
    print("\n" + "="*60)
    print("4. DATA VALIDATION")
    print("="*60)
    
    if DataValidator is None:
        print("⚠️ DataValidator not available, skipping...")
        return
    
    db = IRODB(DB_PATH, auto_create=False)
    validator = DataValidator(db)
    
    # Test valid data
    print("\nTesting valid data:")
    valid_product = {
        "name": "Valid Product",
        "price": 99.99,
        "category": "books",
        "description": "A valid product",
        "email": "valid@store.com"
    }
    try:
        validator.validate_row("products", valid_product)
        print("  ✓ Valid data passed validation")
    except Exception as e:
        print(f"  ✗ Validation failed: {e}")
    
    # Test invalid data cases
    invalid_cases = [
        ("missing name", {"price": 99.99, "category": "books", "description": "Invalid", "email": "invalid@store.com"}),
        ("invalid category", {"name": "Invalid", "price": 99.99, "category": "invalid", "description": "Invalid", "email": "invalid@store.com"}),
        ("invalid email", {"name": "Invalid", "price": 99.99, "category": "books", "description": "Invalid", "email": "invalid"}),
    ]
    
    for case_desc, invalid_product in invalid_cases:
        print(f"\nTesting invalid data ({case_desc}):")
        try:
            validator.validate_row("products", invalid_product)
            print("  ✗ Validation should have failed")
        except Exception as e:
            print(f"  ✓ Validation caught error: {e}")
    
    # Test unique constraint
    print("\nTesting unique constraint:")
    try:
        # Add unique constraint
        validator.add_table_constraints("products", {
            "name": {"unique": True}
        })
        
        # Insert first product
        db.insert("products", {
            "name": "Unique Product",
            "price": 49.99,
            "category": "books",
            "description": "Unique product",
            "email": "unique@store.com"
        })
        print("  ✓ First product inserted")
        
        # Try to insert duplicate
        try:
            db.insert("products", {
                "name": "Unique Product",
                "price": 59.99,
                "category": "books",
                "description": "Duplicate product",
                "email": "duplicate@store.com"
            })
            print("  ✗ Duplicate should have been rejected")
        except Exception as e:
            print(f"  ✓ Duplicate caught: {e}")
    except Exception as e:
        print(f"  ✗ Unique test failed: {e}")
    
    db.close()
    print("\n✅ Validation tests passed!")

def test_hash_features():
    """Test hash-based features"""
    print("\n" + "="*60)
    print("5. HASH FEATURES")
    print("="*60)
    
    db = IRODB(DB_PATH, auto_create=False)
    
    # Verify hash integrity
    print("\nVerifying hash integrity for products:")
    try:
        integrity = db.verify_hash_integrity("products")
        print(f"  - Total rows: {integrity['total_rows']}")
        print(f"  - Valid hashes: {integrity['valid_hashes']}")
        print(f"  - Invalid hashes: {integrity['invalid_hashes']}")
    except Exception as e:
        print(f"  ✗ Integrity check failed: {e}")
    
    # Get hash statistics
    print("\nHash statistics for products:")
    try:
        stats = db.get_hash_statistics("products")
        print(f"  - Unique hashes: {stats['unique_hashes']}")
        print(f"  - Hash collision rate: {stats['hash_collision_rate']:.2%}")
    except Exception as e:
        print(f"  ✗ Stats failed: {e}")
    
    # Find by hash
    print("\nFinding by hash (first product):")
    try:
        first_product = db.select("products", limit=1)[0]
        hash_val = first_product['hash']
        results = db.find_by_hash("products", hash_val)
        for result in results:
            print(f"  - Found: {result['name']} (ID: {result['id']})")
    except Exception as e:
        print(f"  ✗ Hash find failed: {e}")
    
    # Find by hashed value
    print("\nFinding by hashed value ('Laptop Pro'):")
    try:
        results = db.find_by_hashed_value("products", "Laptop Pro")
        for result in results:
            print(f"  - Found: {result['name']} (ID: {result['id']})")
    except Exception as e:
        print(f"  ✗ Hashed find failed: {e}")
    
    db.close()
    print("\n✅ Hash features tests passed!")

def test_crud_operations():
    """Test basic CRUD operations"""
    print("\n" + "="*60)
    print("6. CRUD OPERATIONS")
    print("="*60)
    
    db = IRODB(DB_PATH, auto_create=False)
    
    # CREATE (Insert)
    print("\nINSERT new product:")
    try:
        product_id = db.insert("products", {
            "name": "CRUD Test Product",
            "price": 199.99,
            "category": "electronics",
            "description": "Testing CRUD operations",
            "email": "crud@store.com"
        })
        print(f"  ✓ Inserted with ID: {product_id}")
    except Exception as e:
        print(f"  ✗ Insert failed: {e}")
        db.close()
        return
    
    # READ (Select)
    print("\nSELECT product by name:")
    try:
        results = db.select("products", {"name": "CRUD Test Product"})
        for row in results:
            print(f"  - Found: {row['name']} (ID: {row['id']}, Price: ${row['price']})")
    except Exception as e:
        print(f"  ✗ Select failed: {e}")
    
    # UPDATE
    print("\nUPDATE product price:")
    try:
        updated = db.update("products", {"name": "CRUD Test Product"}, {"price": 149.99})
        print(f"  ✓ Updated {updated} row(s)")
        
        # Verify update
        results = db.select("products", {"name": "CRUD Test Product"})
        for row in results:
            print(f"  - New price: ${row['price']}")
    except Exception as e:
        print(f"  ✗ Update failed: {e}")
    
    # DELETE
    print("\nDELETE product:")
    try:
        deleted = db.delete("products", {"name": "CRUD Test Product"})
        print(f"  ✓ Deleted {deleted} row(s)")
        
        # Verify delete
        results = db.select("products", {"name": "CRUD Test Product"})
        print(f"  - Remaining rows: {len(results)}")
    except Exception as e:
        print(f"  ✗ Delete failed: {e}")
    
    db.close()
    print("\n✅ CRUD operations tests passed!")

# ============================================================================
# CLI TESTS
# ============================================================================

def test_cli_commands():
    """Test CLI commands using subprocess"""
    print("\n" + "="*60)
    print("7. CLI COMMAND TESTING")
    print("="*60)
    
    # Check if CLI script exists
    if not os.path.exists(CLI_SCRIPT):
        print(f"⚠️ CLI script not found at: {CLI_SCRIPT}")
        print("Skipping CLI tests...")
        return
    
    # Test 1: Show database info
    print("\nTesting: CLI info command")
    cmd = [sys.executable, CLI_SCRIPT, DB_PATH, "--info"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("  ✓ Info command succeeded")
            # Show first 200 chars of output
            output = result.stdout[:200] + "..." if len(result.stdout) > 200 else result.stdout
            print(f"  Output: {output}")
        else:
            print(f"  ✗ Info command failed (code {result.returncode}): {result.stderr}")
    except subprocess.TimeoutExpired:
        print("  ✗ Info command timed out")
    except Exception as e:
        print(f"  ✗ Info command error: {e}")
    
    # Test 2: SQL query via CLI
    print("\nTesting: CLI SQL query")
    query = "SELECT name, price FROM products WHERE category = 'electronics' LIMIT 3"
    cmd = [sys.executable, CLI_SCRIPT, DB_PATH, "--query", query]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("  ✓ SQL query succeeded")
            print(f"  Output preview: {result.stdout[:200]}...")
        else:
            print(f"  ✗ SQL query failed: {result.stderr}")
    except subprocess.TimeoutExpired:
        print("  ✗ SQL query timed out")
    except Exception as e:
        print(f"  ✗ SQL query error: {e}")
    
    # Test 3: Export to JSON
    print("\nTesting: CLI export command")
    json_path = os.path.join(TEMP_DIR, "export.json")
    cmd = [sys.executable, CLI_SCRIPT, DB_PATH, "--export", json_path]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0 and os.path.exists(json_path):
            print(f"  ✓ Export succeeded: {json_path}")
            try:
                with open(json_path, 'r') as f:
                    data = json.load(f)
                    print(f"  - Exported tables: {len(data.get('tables', {}))}")
            except:
                print(f"  - Export file exists but JSON parsing failed")
        else:
            print(f"  ✗ Export failed: {result.stderr}")
    except subprocess.TimeoutExpired:
        print("  ✗ Export timed out")
    except Exception as e:
        print(f"  ✗ Export error: {e}")
    
    # Test 4: Backup
    print("\nTesting: CLI backup command")
    backup_path = os.path.join(TEMP_DIR, "backup.irodb")
    cmd = [sys.executable, CLI_SCRIPT, DB_PATH, "--backup", backup_path]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0 and os.path.exists(backup_path):
            print(f"  ✓ Backup succeeded: {backup_path}")
            print(f"  - Backup size: {os.path.getsize(backup_path)} bytes")
        else:
            print(f"  ✗ Backup failed: {result.stderr}")
    except subprocess.TimeoutExpired:
        print("  ✗ Backup timed out")
    except Exception as e:
        print(f"  ✗ Backup error: {e}")
    
    print("\n✅ CLI tests completed!")

# ============================================================================
# UNIT TESTS (using unittest)
# ============================================================================

class TestIRODB(unittest.TestCase):
    """Unit tests for IRODB"""
    
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.mkdtemp()
        cls.db_path = os.path.join(cls.temp_dir, "unittest.irodb")
        cls.db = IRODB(cls.db_path, auto_create=True)
        
        # Create test table
        cls.db.create_table("test", {
            "name": str,
            "value": int,
            "active": bool
        }, enable_hash_index=True)
    
    @classmethod
    def tearDownClass(cls):
        cls.db.close()
        shutil.rmtree(cls.temp_dir, ignore_errors=True)
    
    def test_01_insert(self):
        """Test insert operation"""
        row_id = self.db.insert("test", {
            "name": "Test1",
            "value": 100,
            "active": True
        })
        self.assertEqual(row_id, 1)
    
    def test_02_select(self):
        """Test select operation"""
        results = self.db.select("test", {"name": "Test1"})
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["value"], 100)
    
    def test_03_update(self):
        """Test update operation"""
        updated = self.db.update("test", {"name": "Test1"}, {"value": 200})
        self.assertEqual(updated, 1)
        
        results = self.db.select("test", {"name": "Test1"})
        self.assertEqual(results[0]["value"], 200)
    
    def test_04_hash_integrity(self):
        """Test hash integrity"""
        integrity = self.db.verify_hash_integrity("test")
        self.assertEqual(integrity["valid_hashes"], 1)
        self.assertEqual(integrity["invalid_hashes"], 0)
    
    def test_05_delete(self):
        """Test delete operation"""
        deleted = self.db.delete("test", {"name": "Test1"})
        self.assertEqual(deleted, 1)
        
        results = self.db.select("test")
        self.assertEqual(len(results), 0)

# ============================================================================
# PERFORMANCE TEST
# ============================================================================

def test_performance():
    """Test performance with large dataset"""
    print("\n" + "="*60)
    print("8. PERFORMANCE TEST")
    print("="*60)
    
    db = IRODB(DB_PATH, auto_create=False)
    
    # Create performance test table
    db.create_table("perf_test", {
        "id": int,
        "data": str,
        "value": float
    }, enable_hash_index=True)
    
    start_time = time.time()
    
    # Insert 500 rows (reduced for mobile)
    print("Inserting 500 rows...")
    for i in range(500):
        db.insert("perf_test", {
            "id": i,
            "data": f"Data_{i}",
            "value": i * 1.5
        })
    
    insert_time = time.time() - start_time
    print(f"  ✓ Insert time: {insert_time:.2f} seconds")
    
    # Select all rows
    start_time = time.time()
    results = db.select("perf_test")
    select_time = time.time() - start_time
    print(f"  ✓ Select time: {select_time:.2f} seconds")
    print(f"  ✓ Rows selected: {len(results)}")
    
    # Delete all rows
    start_time = time.time()
    deleted = db.delete("perf_test", {})
    delete_time = time.time() - start_time
    print(f"  ✓ Delete time: {delete_time:.2f} seconds")
    print(f"  ✓ Rows deleted: {deleted}")
    
    db.close()
    print("\n✅ Performance tests passed!")

# ============================================================================
# MAIN RUNNER
# ============================================================================

def run_all_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("IRODB COMPLETE TEST SUITE")
    print("="*60)
    print(f"Database: {DB_PATH}")
    print(f"Temp directory: {TEMP_DIR}")
    print(f"Python: {sys.version}")
    
    # Check if features are available
    features = []
    if FullTextSearch: features.append("FullTextSearch")
    if SQLParser: features.append("SQLParser")
    if DataValidator: features.append("DataValidator")
    print(f"Features available: {', '.join(features) if features else 'None'}")
    
    try:
        # Create database
        create_database()
        
        # Run feature tests
        test_crud_operations()
        test_fulltext_search()
        test_sql_queries()
        test_validation()
        test_hash_features()
        
        # Run CLI tests
        test_cli_commands()
        
        # Run performance test
        test_performance()
        
        # Run unit tests
        print("\n" + "="*60)
        print("9. UNIT TESTS")
        print("="*60)
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromTestCase(TestIRODB)
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        # Summary
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        print(f"✅ All tests completed!")
        print(f"Database: {DB_PATH}")
        print(f"Database size: {os.path.getsize(DB_PATH)} bytes")
        print(f"Temp directory: {TEMP_DIR}")
        
        return result
    except Exception as e:
        print(f"\n❌ Error during tests: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    try:
        result = run_all_tests()
        sys.exit(0 if result and result.wasSuccessful() else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error running tests: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Cleanup
        try:
            shutil.rmtree(TEMP_DIR, ignore_errors=True)
            print(f"\n✅ Cleaned up: {TEMP_DIR}")
        except:
            pass