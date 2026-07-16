# IRODB - Lightweight Database Engine

[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## 📋 Overview

IRODB is a lightweight, file-based database engine for Python applications. It provides a simple yet powerful interface for storing and retrieving structured data with built-in support for data integrity through cryptographic hashing.

### ✨ Key Features

- **🔐 Data Integrity**: SHA-256 hashing for all records
- **📁 File-Based Storage**: No external dependencies or servers needed
- **🔍 Flexible Querying**: Query by any field with multiple conditions
- **⚡ Hash Indexing**: Fast lookups using hash-based indexes
- **🔄 ACID Operations**: Atomic operations with rollback capabilities
- **📊 Schema Validation**: Enforce data types and required fields
- **🛠️ Multi-Table Support**: Create and manage multiple tables
- **🧹 Vacuum Operation**: Optimize database size and performance
- **🔧 Cross-Platform**: Works on Windows, Linux, and macOS

## 🚀 Quick Start

```
from irodb.core import IRODB

# Create or open a database
db = IRODB('my_database.irodb', auto_create=True)

# Create a table with schema
db.create_table('users', {
    'name': str,
    'age': int,
    'email': str,
    'active': bool
}, enable_hash_index=True)

# Insert data
db.insert('users', {
    'name': 'Alice',
    'age': 30,
    'email': 'alice@example.com',
    'active': True
})

# Query data
results = db.select('users', {'name': 'Alice'})
print(results)

# Update data
db.update('users', {'name': 'Alice'}, {'age': 31})

# Delete data
db.delete('users', {'active': False})

# Close database
db.close()
```

## 📦 Installation

### From Source

```
# Clone the repository
git clone https://github.com/IROTECHLAB/irodb.git

# Navigate to the directory
cd irodb

# Install in development mode
pip install -e .
```

### Using pip

```
pip install irotechlab_irodb
```

## 📚 Documentation

### Database Operations

#### Creating a Database

```
from irodb.core import IRODB

# Auto-create if doesn't exist
db = IRODB('data.irodb', auto_create=True)

# Open existing database
db = IRODB('data.irodb', auto_create=False)
```

#### Table Management

```
# Create a table with schema
db.create_table('products', {
    'name': str,
    'price': float,
    'quantity': int,
    'available': bool
})

# Create table with hash index
db.create_table('users', {
    'username': str,
    'email': str
}, enable_hash_index=True)

# List all tables
print(db.tables.keys())
```

#### CRUD Operations

**Insert Data**

```
# Insert single record
row_id = db.insert('users', {
    'name': 'Bob',
    'age': 25,
    'email': 'bob@example.com',
    'active': True
})

# Insert with hash return
row_id, row_hash = db.insert('users', {
    'name': 'Charlie',
    'age': 35,
    'email': 'charlie@example.com',
    'active': False
}, return_hash=True)
```

**Select/Query Data**

```
# Select all records
all_users = db.select('users')

# Select with conditions
active_users = db.select('users', {'active': True})

# Select with limit
first_10 = db.select('users', limit=10)

# Complex conditions
results = db.select('users', {'age': 30, 'active': True})
```

**Update Data**

```
# Update single record
updated = db.update('users', {'name': 'Bob'}, {'age': 26})

# Update multiple records
updated = db.update('users', {'active': True}, {'status': 'active'})
```

**Delete Data**

```
# Delete single record
deleted = db.delete('users', {'name': 'Bob'})

# Delete multiple records
deleted = db.delete('users', {'active': False})
```

### Hash Features

#### Hash Generation

```
# Insert with hash generation
row_id, row_hash = db.insert('users', {
    'name': 'Alice',
    'age': 30,
    'email': 'alice@example.com'
}, return_hash=True)

print(f"Record hash: {row_hash}")
```

#### Find by Hash

```
# Find records by exact hash
results = db.find_by_hash('users', row_hash)

# Find records by hashed value
results = db.find_by_hashed_value('users', 'Alice')
```

#### Hash Integrity Verification

```
# Verify hash integrity of a table
integrity = db.verify_hash_integrity('users')
print(f"Total rows: {integrity['total_rows']}")
print(f"Valid hashes: {integrity['valid_hashes']}")
print(f"Invalid hashes: {integrity['invalid_hashes']}")

# Get hash statistics
stats = db.get_hash_statistics('users')
print(f"Unique hashes: {stats['unique_hashes']}")
```

### Advanced Features

#### Multiple Tables

```
# Create multiple tables
db.create_table('users', {'name': str, 'age': int})
db.create_table('products', {'name': str, 'price': float})
db.create_table('orders', {'user_id': int, 'product_id': int})

# Work with multiple tables
db.insert('users', {'name': 'Alice', 'age': 30})
db.insert('products', {'name': 'Laptop', 'price': 999.99})
db.insert('orders', {'user_id': 1, 'product_id': 1})
```

#### Vacuum Operation

```
# Optimize database by removing deleted records
db.vacuum()
```

#### Database Info

```
# Get database information
info = {
    'tables': len(db.tables),
    'rows': sum(len(pickle.loads(db._read_page(t['page']))['rows']) 
               for t in db.tables.values())
}
print(info)
```

## 🏗️ Project Structure

Based on the actual file structure:

```
irodb/
├── README.md
├── setup.py
├── LICENSE
├── .gitignore
├── irodb/
│   ├── __init__.py          # Package initialization
│   ├── core.py              # Core database engine (19.51KB)
│   ├── constants.py         # Constants and configuration (1.09KB)
│   ├── exceptions.py        # Custom exceptions (909.00B)
│   ├── hash_system.py       # Hash-based features (8.49KB)
│   ├── index.py             # Indexing system (3.56KB)
│   ├── transaction.py       # Transaction management (3.99KB)
│   └── utils.py             # Utility functions (4.67KB)
├── tests/
│   ├── __init__.py
│   └── test_core.py
└── examples/
    └── basic_usage.py
```

### Module Descriptions

| Module | Size | Description |
|--------|------|-------------|
| **core.py** | 19.51KB | Main database engine with CRUD operations |
| **hash_system.py** | 8.49KB | SHA-256 hashing and integrity verification |
| **utils.py** | 4.67KB | Helper functions and utilities |
| **transaction.py** | 3.99KB | ACID transaction support |
| **index.py** | 3.56KB | Indexing and fast lookups |
| **constants.py** | 1.09KB | Configuration constants |
| **exceptions.py** | 909B | Custom exception classes |
| **__init__.py** | 617B | Package exports |

## 🧪 Running Tests

```
# Run all tests
python tests/test_core.py

# Run specific test class
python -m unittest tests.test_core.TestCRUDOperations

# Run with coverage (if coverage installed)
coverage run -m unittest discover tests
coverage report -m
```

## 📝 Examples

### Basic Usage Example

```
from irodb.core import IRODB

# Initialize database
db = IRODB('example.irodb', auto_create=True)

# Create table
db.create_table('employees', {
    'name': str,
    'department': str,
    'salary': int,
    'active': bool
}, enable_hash_index=True)

# Insert sample data
employees = [
    {'name': 'Alice', 'department': 'Engineering', 'salary': 80000, 'active': True},
    {'name': 'Bob', 'department': 'Sales', 'salary': 60000, 'active': True},
    {'name': 'Charlie', 'department': 'Engineering', 'salary': 90000, 'active': False}
]

for emp in employees:
    db.insert('employees', emp)

# Query active engineers
active_engineers = db.select('employees', {
    'department': 'Engineering',
    'active': True
})

print(f"Active engineers: {len(active_engineers)}")

# Update employee salary
db.update('employees', {'name': 'Alice'}, {'salary': 85000})

# Verify hash integrity
integrity = db.verify_hash_integrity('employees')
print(f"Hash integrity: {integrity['valid_hashes']}/{integrity['total_rows']}")

# Close database
db.close()
```

### Hash Demo Example

```
from irodb.core import IRODB

# Create database with hash indexing
db = IRODB('hash_demo.irodb', auto_create=True)

db.create_table('documents', {
    'title': str,
    'content': str,
    'author': str
}, enable_hash_index=True)

# Insert documents with hash
doc_id, doc_hash = db.insert('documents', {
    'title': 'Introduction',
    'content': 'This is the first document.',
    'author': 'John Doe'
}, return_hash=True)

print(f"Document hash: {doc_hash}")

# Find document by hash
found = db.find_by_hash('documents', doc_hash)
print(f"Found: {found[0]['title']}")

# Check integrity
integrity = db.verify_hash_integrity('documents')
print(f"Integrity check: {integrity}")

db.close()
```

### Transaction Example

```
from irodb.core import IRODB
from irodb.transaction import Transaction

db = IRODB('data.irodb', auto_create=True)

# Start a transaction
with Transaction(db) as tx:
    tx.insert('users', {'name': 'Alice', 'age': 30})
    tx.insert('users', {'name': 'Bob', 'age': 25})
    # Auto-commit on exit

# Manual transaction
tx = Transaction(db)
try:
    tx.insert('users', {'name': 'Charlie', 'age': 35})
    tx.commit()
except Exception as e:
    tx.rollback()
    print(f"Transaction failed: {e}")
```

### Test Suite Example

```
# tests/test_core.py
import unittest
import os
import tempfile
import sys
import pickle

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from irodb.core import IRODB
from irodb.exceptions import *

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
            os.rmdir(self.temp_dir)
        except:
            pass
    
    def test_create_new_database(self):
        """Test creating a new database"""
        db = IRODB(self.db_path, auto_create=True)
        self.assertTrue(os.path.exists(self.db_path))
        self.assertEqual(len(db.tables), 0)
        db.close()

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
            os.remove(self.db_path)
        except:
            pass
        try:
            os.rmdir(self.temp_dir)
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
            os.remove(self.db_path)
        except:
            pass
        try:
            os.rmdir(self.temp_dir)
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

if __name__ == "__main__":
    unittest.main()
```

## ⚠️ Error Handling

### Common Exceptions

```
from irodb.exceptions import *

try:
    db.insert('users', {'name': 'Alice'})  # Missing required fields
except ValueError as e:
    print(f"Validation error: {e}")

try:
    db.select('nonexistent_table')
except TableError as e:
    print(f"Table error: {e}")

try:
    db.insert('users', {'name': 'Alice', 'age': 'thirty'})  # Wrong type
except TypeError as e:
    print(f"Type error: {e}")
```

## 🔧 Configuration

### Database Settings

```
# Database options
db = IRODB(
    'data.irodb',
    auto_create=True,
    page_size=4096,  # Custom page size
    hash_algorithm='sha256'  # Hash algorithm
)
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup

```
# Clone your fork
git clone https://github.com/IROTECHLAB/irodb.git

# Install development dependencies
pip install -e .[dev]

# Run tests
pytest tests/

# Check code style
black irodb/
flake8 irodb/
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👥 Authors

- **IROTECHLAB** - *Initial work* - [GitHub](https://github.com/IROTECHLAB)

## 🙏 Acknowledgments

- Built with Python's built-in libraries
- Inspired by simplicity and data integrity
- Community contributions welcome

## 📞 Contact

- **Telegram Channel**: [@irotechcoders](https://t.me/irotechcoders)
- **Author**: [@ironmanhindigaming](https://t.me/ironmanhindigaming)
- **GitHub**: [IROTECHLAB/irodb](https://github.com/IROTECHLAB/irodb)

## 🔮 Roadmap

- [ ] SQL-like query support
- [ ] Encryption at rest
- [ ] Replication support
- [ ] Backup and restore utilities
- [ ] Web admin interface
- [ ] Migration tools
- [ ] Performance optimizations

---

Made with ❤️ by **IROTECHLAB**