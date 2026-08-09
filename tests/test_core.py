#!/usr/bin/env python3
"""
Core Test Suite for IRODB
Tests all core functionality including database creation, CRUD operations,
hash features, and advanced operations.
"""

import unittest
import os
import tempfile
import sys
import pickle
import json
import shutil
from datetime import datetime
from typing import Dict, Any, List

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from irodb import IRODB
from irodb.exceptions import *
from irodb.hash_system import HashManager
from irodb.utils import DatabaseUtils


class TestDatabaseCreation(unittest.TestCase):
    """Test database creation and initialization"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test.irodb')
    
    def tearDown(self):
        try:
            if os.path.exists(self.db_path):
                os.remove(self.db_path)
        except:
            pass
        try:
            shutil.rmtree(self.temp_dir)
        except:
            pass
    
    def test_create_new_database(self):
        """Test creating a new database"""
        db = IRODB(self.db_path, auto_create=True)
        self.assertTrue(os.path.exists(self.db_path))
        self.assertEqual(len(db.tables), 0)
        db.close()
    
    def test_open_existing_database(self):
        """Test opening an existing database"""
        # Create database first
        db1 = IRODB(self.db_path, auto_create=True)
        db1.create_table("test", {"name": str})
        db1.close()
        
        # Open existing
        db2 = IRODB(self.db_path, auto_create=False)
        self.assertIn("test", db2.tables)
        db2.close()
    
    def test_database_with_custom_path(self):
        """Test creating database with custom path"""
        custom_path = os.path.join(self.temp_dir, "custom", "db.irodb")
        db = IRODB(custom_path, auto_create=True)
        self.assertTrue(os.path.exists(custom_path))
        db.close()
    
    def test_database_header_validation(self):
        """Test database header validation"""
        db = IRODB(self.db_path, auto_create=True)
        db.close()
        
        # Corrupt the file
        with open(self.db_path, 'rb+') as f:
            f.seek(0)
            f.write(b'INVALID')
        
        # Should handle corruption gracefully
        db2 = IRODB(self.db_path, auto_create=True)
        self.assertTrue(os.path.exists(self.db_path))
        db2.close()
    
    def test_auto_create_enabled(self):
        """Test auto_create parameter"""
        # Should create database if auto_create=True
        db1 = IRODB(os.path.join(self.temp_dir, "auto.irodb"), auto_create=True)
        self.assertTrue(os.path.exists(db1.db_path))
        db1.close()
        
        # Should raise error if auto_create=False and file doesn't exist
        non_existent = os.path.join(self.temp_dir, "missing.irodb")
        with self.assertRaises(DatabaseError):
            db2 = IRODB(non_existent, auto_create=False)


class TestTableOperations(unittest.TestCase):
    """Test table creation and management"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test.irodb')
        self.db = IRODB(self.db_path, auto_create=True)
    
    def tearDown(self):
        self.db.close()
        try:
            shutil.rmtree(self.temp_dir)
        except:
            pass
    
    def test_create_simple_table(self):
        """Test creating a simple table"""
        self.db.create_table("users", {"name": str, "age": int})
        self.assertIn("users", self.db.tables)
        self.assertEqual(len(self.db.tables["users"]["schema"]), 2)
        self.assertEqual(self.db.tables["users"]["schema"]["name"], str)
        self.assertEqual(self.db.tables["users"]["schema"]["age"], int)
    
    def test_create_table_with_all_types(self):
        """Test creating table with all data types"""
        self.db.create_table("all_types", {
            "string_field": str,
            "int_field": int,
            "float_field": float,
            "bool_field": bool,
            "bytes_field": bytes,
            "list_field": list,
            "dict_field": dict
        })
        self.assertIn("all_types", self.db.tables)
        schema = self.db.tables["all_types"]["schema"]
        self.assertEqual(schema["string_field"], str)
        self.assertEqual(schema["int_field"], int)
        self.assertEqual(schema["float_field"], float)
        self.assertEqual(schema["bool_field"], bool)
    
    def test_create_table_with_hash_index(self):
        """Test creating table with hash index"""
        self.db.create_table("hashed", {"name": str}, enable_hash_index=True)
        self.assertTrue(self.db.tables["hashed"]["enable_hash_index"])
        self.assertIsNotNone(self.db.tables["hashed"]["hash_index_page"])
    
    def test_create_duplicate_table(self):
        """Test creating duplicate table"""
        self.db.create_table("test", {"name": str})
        with self.assertRaises(TableError):
            self.db.create_table("test", {"name": str})
    
    def test_get_table_info(self):
        """Test getting table information"""
        self.db.create_table("users", {"name": str, "age": int})
        table_info = self.db.tables["users"]
        self.assertIn("schema", table_info)
        self.assertIn("page", table_info)
        self.assertIn("created_at", table_info)
        self.assertTrue(isinstance(table_info["created_at"], str))
    
    def test_multiple_tables_creation(self):
        """Test creating multiple tables"""
        tables = ["users", "products", "orders", "customers"]
        for table in tables:
            self.db.create_table(table, {"id": int, "name": str})
        
        for table in tables:
            self.assertIn(table, self.db.tables)
        self.assertEqual(len(self.db.tables), len(tables))


class TestCRUDOperations(unittest.TestCase):
    """Test basic CRUD operations"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test.irodb')
        self.db = IRODB(self.db_path, auto_create=True)
        self.db.create_table("users", {
            "name": str,
            "age": int,
            "email": str,
            "active": bool
        })
    
    def tearDown(self):
        self.db.close()
        try:
            shutil.rmtree(self.temp_dir)
        except:
            pass
    
    def test_insert_single_row(self):
        """Test inserting a single row"""
        row_id = self.db.insert("users", {
            "name": "Alice",
            "age": 30,
            "email": "alice@example.com",
            "active": True
        })
        self.assertEqual(row_id, 1)
        
        # Verify
        results = self.db.select("users")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "Alice")
        self.assertEqual(results[0]["age"], 30)
    
    def test_insert_multiple_rows(self):
        """Test inserting multiple rows"""
        users = [
            {"name": "Alice", "age": 30, "email": "alice@ex.com", "active": True},
            {"name": "Bob", "age": 25, "email": "bob@ex.com", "active": False},
            {"name": "Charlie", "age": 35, "email": "charlie@ex.com", "active": True}
        ]
        
        for user in users:
            self.db.insert("users", user)
        
        results = self.db.select("users")
        self.assertEqual(len(results), 3)
    
    def test_insert_missing_field(self):
        """Test inserting with missing field"""
        with self.assertRaises(ValueError):
            self.db.insert("users", {"name": "Alice", "age": 30})
    
    def test_insert_wrong_type(self):
        """Test inserting with wrong type"""
        with self.assertRaises(TypeError):
            self.db.insert("users", {
                "name": "Alice",
                "age": "30",  # Should be int
                "email": "alice@ex.com",
                "active": True
            })
    
    def test_insert_none_value(self):
        """Test inserting with None value"""
        row_id = self.db.insert("users", {
            "name": "Alice",
            "age": 30,
            "email": None,
            "active": True
        })
        self.assertEqual(row_id, 1)
        results = self.db.select("users", {"name": "Alice"})
        self.assertIsNone(results[0]["email"])
    
    def test_select_all(self):
        """Test selecting all rows"""
        self.db.insert("users", {"name": "Alice", "age": 30, "email": "a@ex.com", "active": True})
        self.db.insert("users", {"name": "Bob", "age": 25, "email": "b@ex.com", "active": False})
        
        results = self.db.select("users")
        self.assertEqual(len(results), 2)
    
    def test_select_with_conditions(self):
        """Test selecting with conditions"""
        self.db.insert("users", {"name": "Alice", "age": 30, "email": "a@ex.com", "active": True})
        self.db.insert("users", {"name": "Bob", "age": 25, "email": "b@ex.com", "active": False})
        self.db.insert("users", {"name": "Alice", "age": 25, "email": "a2@ex.com", "active": True})
        
        results = self.db.select("users", {"name": "Alice"})
        self.assertEqual(len(results), 2)
        
        results = self.db.select("users", {"name": "Alice", "age": 30})
        self.assertEqual(len(results), 1)
    
    def test_select_with_limit(self):
        """Test selecting with limit"""
        for i in range(10):
            self.db.insert("users", {
                "name": f"User{i}",
                "age": 20 + i,
                "email": f"user{i}@ex.com",
                "active": True
            })
        
        results = self.db.select("users", limit=5)
        self.assertEqual(len(results), 5)
    
    def test_select_non_existent_conditions(self):
        """Test selecting with non-existent conditions"""
        self.db.insert("users", {"name": "Alice", "age": 30, "email": "a@ex.com", "active": True})
        results = self.db.select("users", {"name": "NonExistent"})
        self.assertEqual(len(results), 0)
    
    def test_update_single_row(self):
        """Test updating a single row"""
        self.db.insert("users", {"name": "Alice", "age": 30, "email": "a@ex.com", "active": True})
        
        updated = self.db.update("users", {"name": "Alice"}, {"age": 31})
        self.assertEqual(updated, 1)
        
        results = self.db.select("users", {"name": "Alice"})
        self.assertEqual(results[0]["age"], 31)
    
    def test_update_multiple_rows(self):
        """Test updating multiple rows"""
        self.db.insert("users", {"name": "Alice", "age": 30, "email": "a@ex.com", "active": True})
        self.db.insert("users", {"name": "Bob", "age": 30, "email": "b@ex.com", "active": True})
        
        updated = self.db.update("users", {"age": 30}, {"active": False})
        self.assertEqual(updated, 2)
        
        results = self.db.select("users", {"active": False})
        self.assertEqual(len(results), 2)
    
    def test_update_multiple_fields(self):
        """Test updating multiple fields at once"""
        self.db.insert("users", {"name": "Alice", "age": 30, "email": "a@ex.com", "active": True})
        
        updated = self.db.update("users", {"name": "Alice"}, {
            "age": 31,
            "email": "new@ex.com",
            "active": False
        })
        self.assertEqual(updated, 1)
        
        results = self.db.select("users", {"name": "Alice"})
        self.assertEqual(results[0]["age"], 31)
        self.assertEqual(results[0]["email"], "new@ex.com")
        self.assertEqual(results[0]["active"], False)
    
    def test_update_nonexistent_row(self):
        """Test updating nonexistent row"""
        updated = self.db.update("users", {"name": "Nonexistent"}, {"age": 99})
        self.assertEqual(updated, 0)
    
    def test_delete_single_row(self):
        """Test deleting a single row"""
        self.db.insert("users", {"name": "Alice", "age": 30, "email": "a@ex.com", "active": True})
        self.db.insert("users", {"name": "Bob", "age": 25, "email": "b@ex.com", "active": True})
        
        deleted = self.db.delete("users", {"name": "Alice"})
        self.assertEqual(deleted, 1)
        
        results = self.db.select("users")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "Bob")
    
    def test_delete_multiple_rows(self):
        """Test deleting multiple rows"""
        self.db.insert("users", {"name": "Alice", "age": 30, "email": "a@ex.com", "active": True})
        self.db.insert("users", {"name": "Bob", "age": 25, "email": "b@ex.com", "active": True})
        self.db.insert("users", {"name": "Charlie", "age": 30, "email": "c@ex.com", "active": True})
        
        deleted = self.db.delete("users", {"age": 30})
        self.assertEqual(deleted, 2)
        
        results = self.db.select("users")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "Bob")
    
    def test_delete_all_rows(self):
        """Test deleting all rows"""
        self.db.insert("users", {"name": "Alice", "age": 30, "email": "a@ex.com", "active": True})
        self.db.insert("users", {"name": "Bob", "age": 25, "email": "b@ex.com", "active": True})
        
        deleted = self.db.delete("users", {})
        self.assertEqual(deleted, 2)
        
        results = self.db.select("users")
        self.assertEqual(len(results), 0)


class TestHashFeatures(unittest.TestCase):
    """Test hash-based features"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test_hash.irodb')
        self.db = IRODB(self.db_path, auto_create=True)
        self.db.create_table("users", {
            "name": str,
            "age": int,
            "email": str
        }, enable_hash_index=True)
    
    def tearDown(self):
        self.db.close()
        try:
            shutil.rmtree(self.temp_dir)
        except:
            pass
    
    def test_insert_with_hash_generation(self):
        """Test hash generation on insert"""
        row_id, row_hash = self.db.insert("users", {
            "name": "Alice",
            "age": 30,
            "email": "alice@example.com"
        }, return_hash=True)
        
        self.assertEqual(row_id, 1)
        self.assertIsNotNone(row_hash)
        self.assertEqual(len(row_hash), 64)  # SHA-256 hex length
        
        # Verify hash is stored
        results = self.db.select("users", {"name": "Alice"})
        self.assertEqual(results[0]["hash"], row_hash)
    
    def test_find_by_hash_exact(self):
        """Test finding by exact hash"""
        _, row_hash = self.db.insert("users", {
            "name": "Alice",
            "age": 30,
            "email": "alice@example.com"
        }, return_hash=True)
        
        results = self.db.find_by_hash("users", row_hash)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "Alice")
    
    def test_find_by_hash_with_duplicates(self):
        """Test finding by hash with duplicate data"""
        # Insert duplicate data (should have same hash)
        self.db.insert("users", {"name": "Alice", "age": 30, "email": "alice@ex.com"})
        self.db.insert("users", {"name": "Alice", "age": 30, "email": "alice@ex.com"})
        
        # Get hash of first row
        results = self.db.select("users", limit=1)
        hash_val = results[0]["hash"]
        
        # Find by hash
        found = self.db.find_by_hash("users", hash_val)
        self.assertEqual(len(found), 2)  # Should find both
    
    def test_find_by_hashed_value(self):
        """Test finding by hashed value"""
        self.db.insert("users", {"name": "Alice", "age": 30, "email": "alice@ex.com"})
        self.db.insert("users", {"name": "Bob", "age": 25, "email": "bob@ex.com"})
        
        results = self.db.find_by_hashed_value("users", "Alice")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "Alice")
    
    def test_hash_integrity_verification(self):
        """Test hash integrity verification"""
        self.db.insert("users", {"name": "Alice", "age": 30, "email": "alice@ex.com"})
        self.db.insert("users", {"name": "Bob", "age": 25, "email": "bob@ex.com"})
        
        integrity = self.db.verify_hash_integrity("users")
        self.assertEqual(integrity["total_rows"], 2)
        self.assertEqual(integrity["valid_hashes"], 2)
        self.assertEqual(integrity["invalid_hashes"], 0)
        self.assertEqual(len(integrity["corrupted_rows"]), 0)
    
    def test_hash_statistics(self):
        """Test hash statistics"""
        self.db.insert("users", {"name": "Alice", "age": 30, "email": "alice@ex.com"})
        self.db.insert("users", {"name": "Bob", "age": 25, "email": "bob@ex.com"})
        self.db.insert("users", {"name": "Alice", "age": 30, "email": "alice2@ex.com"})
        
        stats = self.db.get_hash_statistics("users")
        self.assertEqual(stats["total_rows"], 3)
        self.assertEqual(stats["unique_hashes"], 3)  # Different emails = different hashes
    
    def test_hash_update_on_data_change(self):
        """Test hash updates when data changes"""
        _, old_hash = self.db.insert("users", {
            "name": "Alice",
            "age": 30,
            "email": "alice@ex.com"
        }, return_hash=True)
        
        # Update data
        self.db.update("users", {"name": "Alice"}, {"age": 31})
        
        # Get new hash
        results = self.db.select("users", {"name": "Alice"})
        new_hash = results[0]["hash"]
        
        self.assertNotEqual(old_hash, new_hash)
    
    def test_hash_integrity_after_update(self):
        """Test hash integrity after updates"""
        self.db.insert("users", {"name": "Alice", "age": 30, "email": "alice@ex.com"})
        self.db.update("users", {"name": "Alice"}, {"age": 31})
        
        integrity = self.db.verify_hash_integrity("users")
        self.assertEqual(integrity["valid_hashes"], 1)
        self.assertEqual(integrity["invalid_hashes"], 0)
    
    def test_hash_delete_cleanup(self):
        """Test hash index cleanup on delete"""
        self.db.insert("users", {"name": "Alice", "age": 30, "email": "alice@ex.com"})
        self.db.insert("users", {"name": "Bob", "age": 25, "email": "bob@ex.com"})
        
        # Delete Alice
        self.db.delete("users", {"name": "Alice"})
        
        # Verify hash index is cleaned up
        results = self.db.select("users")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "Bob")


class TestAdvancedFeatures(unittest.TestCase):
    """Test advanced database features"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test_advanced.irodb')
        self.db = IRODB(self.db_path, auto_create=True)
    
    def tearDown(self):
        self.db.close()
        try:
            shutil.rmtree(self.temp_dir)
        except:
            pass
    
    def test_multiple_tables(self):
        """Test working with multiple tables"""
        self.db.create_table("users", {"name": str, "age": int})
        self.db.create_table("products", {"name": str, "price": float})
        self.db.create_table("orders", {"user_id": int, "product_id": int})
        
        self.assertEqual(len(self.db.tables), 3)
        
        # Insert into all tables
        self.db.insert("users", {"name": "Alice", "age": 30})
        self.db.insert("products", {"name": "Laptop", "price": 999.99})
        self.db.insert("orders", {"user_id": 1, "product_id": 1})
        
        self.assertEqual(len(self.db.select("users")), 1)
        self.assertEqual(len(self.db.select("products")), 1)
        self.assertEqual(len(self.db.select("orders")), 1)
    
    def test_vacuum_operation(self):
        """Test vacuum operation"""
        self.db.create_table("test", {"name": str, "value": int})
        
        # Insert many rows
        for i in range(100):
            self.db.insert("test", {"name": f"item{i}", "value": i})
        
        # Delete half
        for i in range(50):
            self.db.delete("test", {"name": f"item{i}"})
        
        # Vacuum should work without errors
        self.db.vacuum()
        
        # Verify remaining rows
        results = self.db.select("test")
        self.assertEqual(len(results), 50)
    
    def test_database_info(self):
        """Test getting database information"""
        self.db.create_table("users", {"name": str, "age": int})
        self.db.insert("users", {"name": "Alice", "age": 30})
        self.db.insert("users", {"name": "Bob", "age": 25})
        
        # Access database info
        info = {
            'tables': len(self.db.tables),
            'rows': sum(len(pickle.loads(self.db._read_page(t['page']))['rows']) 
                       for t in self.db.tables.values())
        }
        
        self.assertEqual(info['tables'], 1)
        self.assertEqual(info['rows'], 2)
    
    def test_large_data_insertion(self):
        """Test inserting large amounts of data"""
        self.db.create_table("large", {"id": int, "data": str})
        
        # Insert 500 rows (reduced for test speed)
        for i in range(500):
            self.db.insert("large", {"id": i, "data": f"Data_{i}"})
        
        results = self.db.select("large")
        self.assertEqual(len(results), 500)
    
    def test_complex_queries(self):
        """Test complex query patterns"""
        self.db.create_table("employees", {
            "name": str,
            "department": str,
            "salary": int,
            "active": bool
        })
        
        employees = [
            {"name": "Alice", "department": "Engineering", "salary": 80000, "active": True},
            {"name": "Bob", "department": "Sales", "salary": 60000, "active": True},
            {"name": "Charlie", "department": "Engineering", "salary": 90000, "active": False},
            {"name": "David", "department": "Sales", "salary": 55000, "active": True},
            {"name": "Eve", "department": "Engineering", "salary": 75000, "active": True}
        ]
        
        for emp in employees:
            self.db.insert("employees", emp)
        
        # Query: Active engineers
        results = self.db.select("employees", {"department": "Engineering", "active": True})
        self.assertEqual(len(results), 2)
        
        # Query: All sales
        results = self.db.select("employees", {"department": "Sales"})
        self.assertEqual(len(results), 2)
        
        # Query: High salary
        results = self.db.select("employees", {"salary": {"$gt": 70000}})
        self.assertEqual(len(results), 3)
    
    def test_unicode_and_special_chars(self):
        """Test handling of unicode and special characters"""
        self.db.create_table("test", {"text": str})
        
        test_strings = [
            "Hello 世界",
            "Emoji: 🎉🔥🚀",
            "Special: !@#$%^&*()",
            "Üñìçødë",
            "Japanese: こんにちは"
        ]
        
        for text in test_strings:
            self.db.insert("test", {"text": text})
        
        results = self.db.select("test")
        self.assertEqual(len(results), len(test_strings))
        for i, result in enumerate(results):
            self.assertEqual(result["text"], test_strings[i])


class TestErrorHandling(unittest.TestCase):
    """Test error handling"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test_errors.irodb')
        self.db = IRODB(self.db_path, auto_create=True)
        self.db.create_table("test", {"name": str, "age": int})
    
    def tearDown(self):
        self.db.close()
        try:
            shutil.rmtree(self.temp_dir)
        except:
            pass
    
    def test_unknown_table(self):
        """Test operations on unknown table"""
        with self.assertRaises(TableError):
            self.db.select("unknown")
        
        with self.assertRaises(TableError):
            self.db.insert("unknown", {"name": "test"})
        
        with self.assertRaises(TableError):
            self.db.update("unknown", {"name": "test"}, {"age": 1})
        
        with self.assertRaises(TableError):
            self.db.delete("unknown", {"name": "test"})
    
    def test_invalid_schema_field(self):
        """Test invalid schema field"""
        with self.assertRaises(ValueError):
            self.db.insert("test", {"name": "Alice"})  # Missing age
    
    def test_invalid_data_type(self):
        """Test invalid data type"""
        with self.assertRaises(TypeError):
            self.db.insert("test", {"name": "Alice", "age": "thirty"})  # Should be int
    
    def test_update_invalid_field(self):
        """Test updating invalid field"""
        self.db.insert("test", {"name": "Alice", "age": 30})
        with self.assertRaises(ValueError):
            self.db.update("test", {"name": "Alice"}, {"invalid_field": "value"})
    
    def test_update_non_existent_condition(self):
        """Test updating with non-existent condition"""
        result = self.db.update("test", {"name": "NonExistent"}, {"age": 99})
        self.assertEqual(result, 0)
    
    def test_delete_non_existent_condition(self):
        """Test deleting with non-existent condition"""
        result = self.db.delete("test", {"name": "NonExistent"})
        self.assertEqual(result, 0)
    
    def test_db_path_permission_error(self):
        """Test permission error handling"""
        # Create a file that can't be written to (read-only directory)
        read_only_dir = os.path.join(self.temp_dir, "readonly")
        os.makedirs(read_only_dir, exist_ok=True)
        os.chmod(read_only_dir, 0o444)  # Read-only
        
        db_path = os.path.join(read_only_dir, "test.irodb")
        with self.assertRaises(Exception):
            db = IRODB(db_path, auto_create=True)
            db.close()


class TestDatabaseUtils(unittest.TestCase):
    """Test utility functions"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test_utils.irodb')
        self.db = IRODB(self.db_path, auto_create=True)
        self.db.create_table("users", {"name": str, "age": int})
        self.db.insert("users", {"name": "Alice", "age": 30})
        self.db.insert("users", {"name": "Bob", "age": 25})
        self.utils = DatabaseUtils(self.db)
    
    def tearDown(self):
        self.db.close()
        try:
            shutil.rmtree(self.temp_dir)
        except:
            pass
    
    def test_backup(self):
        """Test backup functionality"""
        backup_path = os.path.join(self.temp_dir, "backup.irodb")
        result = self.utils.backup(backup_path)
        self.assertTrue(os.path.exists(backup_path))
        self.assertEqual(result["backup_path"], backup_path)
        self.assertIn("timestamp", result)
        self.assertIn("size", result)
    
    def test_export_to_json(self):
        """Test export to JSON"""
        json_path = os.path.join(self.temp_dir, "export.json")
        result = self.utils.export_to_json(json_path)
        self.assertTrue(os.path.exists(json_path))
        self.assertEqual(result["tables"], 1)
        
        # Verify JSON content
        with open(json_path, 'r') as f:
            data = json.load(f)
        self.assertIn("tables", data)
        self.assertIn("users", data["tables"])
        self.assertEqual(len(data["tables"]["users"]["rows"]), 2)
    
    def test_get_table_size(self):
        """Test getting table size"""
        size_info = self.utils.get_table_size("users")
        self.assertEqual(size_info["table_name"], "users")
        self.assertEqual(size_info["row_count"], 2)
        self.assertIn("estimated_size_bytes", size_info)
        self.assertFalse(size_info["hash_index_enabled"])
    
    def test_get_database_info(self):
        """Test getting database info"""
        info = self.utils.get_database_info()
        self.assertEqual(info["path"], self.db_path)
        self.assertEqual(info["tables_count"], 1)
        self.assertEqual(info["tables"], ["users"])
        self.assertEqual(info["total_rows"], 2)
        self.assertIn("file_size_bytes", info)


def run_tests():
    """Run all tests with detailed output"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestDatabaseCreation))
    suite.addTests(loader.loadTestsFromTestCase(TestTableOperations))
    suite.addTests(loader.loadTestsFromTestCase(TestCRUDOperations))
    suite.addTests(loader.loadTestsFromTestCase(TestHashFeatures))
    suite.addTests(loader.loadTestsFromTestCase(TestAdvancedFeatures))
    suite.addTests(loader.loadTestsFromTestCase(TestErrorHandling))
    suite.addTests(loader.loadTestsFromTestCase(TestDatabaseUtils))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success: {result.wasSuccessful()}")
    
    if result.failures:
        print("\nFAILURES:")
        for failure in result.failures:
            print(f"\n{failure[0]}")
            print(failure[1])
    
    if result.errors:
        print("\nERRORS:")
        for error in result.errors:
            print(f"\n{error[0]}")
            print(error[1])
    
    return result


if __name__ == "__main__":
    result = run_tests()
    sys.exit(0 if result.wasSuccessful() else 1)