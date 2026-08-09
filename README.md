# IRODB - Lightweight Database Engine

[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![PyPI version](https://img.shields.io/pypi/v/irotechlab-irodb.svg)](https://pypi.org/project/irotechlab-irodb/)
[![PyPI downloads](https://img.shields.io/pypi/dm/irotechlab-irodb.svg)](https://pypi.org/project/irotechlab-irodb/)

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
- **🔍 Full-Text Search**: Google-like search with TF-IDF ranking
- **📝 SQL-like Queries**: Familiar SQL syntax for database operations
- **✅ Data Validation**: Built-in validators for email, phone, URL, and more

## 📦 Installation

### From PyPI (Recommended)

```bash
pip install irotechlab-irodb
```

### From Source

```bash
# Clone the repository
git clone https://github.com/IROTECHLAB/irodb.git

# Navigate to the directory
cd irodb

# Install in development mode
pip install -e .
```

## 🚀 Quick Start

```python
from irodb import IRODB

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

## 📚 Documentation

### Database Operations

#### Creating a Database

```python
from irodb import IRODB

# Auto-create if doesn't exist
db = IRODB('data.irodb', auto_create=True)

# Open existing database
db = IRODB('data.irodb', auto_create=False)
```

#### Table Management

```python
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

### CRUD Operations

**Insert Data**

```python
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

```python
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

```python
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

### Full-Text Search

```python
from irodb import FullTextSearch

# Create full-text index
fulltext = FullTextSearch(db)
fulltext.create_fulltext_index("products", ["name", "description"], "products_ft")

# Search with ranking
results = fulltext.search("products", "laptop professional", limit=5)
for result in results:
    print(f"{result['name']} (Score: {result['_score']:.2f})")

# Field boosting
results = fulltext.search("products", "python book", 
                         boost={'name': 2.0, 'description': 1.0})
```

### SQL-like Queries

```python
from irodb import SQLParser

sql = SQLParser(db)

# SELECT with conditions
results = sql.execute("SELECT * FROM products WHERE category = 'electronics'")

# SELECT with ORDER BY and LIMIT
results = sql.execute("SELECT name, price FROM products WHERE price > 500 ORDER BY price DESC LIMIT 10")

# GROUP BY with aggregation
results = sql.execute("SELECT category, COUNT(*) as count FROM products GROUP BY category")

# INSERT
sql.execute("INSERT INTO products (name, price, category) VALUES ('Tablet', 299.99, 'electronics')")

# UPDATE
sql.execute("UPDATE products SET price = 249.99 WHERE name = 'Tablet'")

# DELETE
sql.execute("DELETE FROM products WHERE name = 'Tablet'")
```

### Data Validation

```python
from irodb import DataValidator

validator = DataValidator(db)

# Add constraints
validator.add_table_constraints("products", {
    "name": {"required": True, "min_length": 2, "max_length": 100},
    "price": {"required": True, "min": 0.0, "max": 999999.99},
    "category": {"required": True, "allowed_values": ["electronics", "books", "clothing"]},
    "email": {"validator": "email", "required": True},
    "sku": {"unique": True, "pattern": r'^[A-Z]{3}-\d{4}$'}
})

# Validate before insert
try:
    validator.check_constraints_on_insert("products", product_data)
    db.insert("products", product_data)
except ValidationError as e:
    print(f"Validation failed: {e}")
```

### Hash Features

#### Hash Generation

```python
# Insert with hash generation
row_id, row_hash = db.insert('users', {
    'name': 'Alice',
    'age': 30,
    'email': 'alice@example.com'
}, return_hash=True)

print(f"Record hash: {row_hash}")
```

#### Find by Hash

```python
# Find records by exact hash
results = db.find_by_hash('users', row_hash)

# Find records by hashed value
results = db.find_by_hashed_value('users', 'Alice')
```

#### Hash Integrity Verification

```python
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

```python
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

```python
# Optimize database by removing deleted records
db.vacuum()
```

#### Database Info

```python
# Get database information
info = {
    'tables': len(db.tables),
    'rows': sum(len(pickle.loads(db._read_page(t['page']))['rows']) 
               for t in db.tables.values())
}
print(info)
```

## 🏗️ Project Structure

```
irodb/
├── README.md
├── setup.py
├── pyproject.toml
├── LICENSE
├── .gitignore
├── irodb/
│   ├── __init__.py          # Package initialization
│   ├── core.py              # Core database engine
│   ├── constants.py         # Constants and configuration
│   ├── exceptions.py        # Custom exceptions
│   ├── hash_system.py       # Hash-based features
│   ├── index.py             # Indexing system
│   ├── transaction.py       # Transaction management
│   ├── utils.py             # Utility functions
│   ├── feature_fulltext.py  # Full-text search engine
│   ├── feature_sql.py       # SQL-like query parser
│   ├── feature_validation.py # Data validation system
│   └── cli.py              # Command-line interface
├── tests/
│   ├── test_core.py
│   └── test-all.py
└── examples/
    └── complete_example.py
```

### Module Descriptions

| Module | Description |
|--------|------|-------------|
| **core.py** | Main database engine with CRUD operations |
| **hash_system.py** | SHA-256 hashing and integrity verification |
| **utils.py** | Helper functions and utilities |
| **transaction.py** | ACID transaction support |
| **index.py** | Indexing and fast lookups |
| **feature_fulltext.py** | Full-text search with TF-IDF ranking |
| **feature_sql.py** | SQL-like query parser and executor |
| **feature_validation.py** | Data validation and constraints |
| **constants.py**  | Configuration constants |
| **exceptions.py** | Custom exception classes |
| **cli.py** | Command-line interface |

## 🧪 Running Tests

```bash
# Run all tests
python tests/test_core.py

# Run complete test suite
python tests/test-all.py

# Run specific test class
python -m unittest tests.test_core.TestCRUDOperations

# Run with coverage (if coverage installed)
coverage run -m unittest discover tests
coverage report -m
```

## 📝 Examples

### Complete Example with All Features

```python
from irodb import IRODB, FullTextSearch, SQLParser, DataValidator

# Initialize database
db = IRODB('complete_example.irodb', auto_create=True)

# Create table
db.create_table('products', {
    'name': str,
    'price': float,
    'category': str,
    'description': str,
    'email': str
}, enable_hash_index=True)

# Setup validation
validator = DataValidator(db)
validator.add_table_constraints("products", {
    "name": {"required": True, "min_length": 2},
    "price": {"required": True, "min": 0},
    "category": {"required": True, "allowed_values": ["electronics", "books", "clothing"]},
    "email": {"validator": "email", "required": True}
})

# Insert data
db.insert("products", {
    "name": "Laptop Pro",
    "price": 1299.99,
    "category": "electronics",
    "description": "High-performance laptop",
    "email": "laptop@store.com"
})

# Full-text search
fulltext = FullTextSearch(db)
fulltext.create_fulltext_index("products", ["name", "description"], "products_ft")
results = fulltext.search("products", "laptop high-performance")
print(f"Search results: {len(results)}")

# SQL query
sql = SQLParser(db)
results = sql.execute("SELECT name, price FROM products WHERE category = 'electronics'")
print(f"SQL results: {len(results)}")

# Hash integrity
integrity = db.verify_hash_integrity("products")
print(f"Hash integrity: {integrity['valid_hashes']}/{integrity['total_rows']}")

db.close()
```

### CLI Usage

```bash
# Show database info
irodb data.irodb --info

# Execute SQL query
irodb data.irodb --query "SELECT * FROM products WHERE price > 100"

# Export to JSON
irodb data.irodb --export data.json

# Backup database
irodb data.irodb --backup backup.irodb

# Interactive mode
irodb data.irodb --interactive
```

## ⚠️ Error Handling

### Common Exceptions

```python
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

try:
    db.insert('products', invalid_data)
except ValidationError as e:
    print(f"Validation failed: {e}")
except ConstraintError as e:
    print(f"Constraint violation: {e}")
```

## 🔧 Configuration

### Database Settings

```python
# Database options
db = IRODB(
    'data.irodb',
    auto_create=True,
    page_size=4096  # Custom page size
)
```

## 🤝 Contributing

IRODB is an open-source project and contributions are welcome! Whether you want to report a bug, suggest a feature, or submit a pull request, we appreciate your help.

### How to Contribute

1. **Fork the repository** on GitHub
2. **Create a feature branch**:
   ```git checkout -b feature/amazing-feature```
3. **Commit your changes**:
   ```git commit -m 'Add amazing feature'```
4. **Push to the branch**:
   ```git push origin feature/amazing-feature```
5. **Open a Pull Request**

### Development Setup

```bash
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

## 📞 Contact & Support

### Found a Bug or Have a Question?

If you find any issues or have questions, feel free to reach out:

- **📱 Instagram**: [@ironmanyt00](https://instagram.com/ironmanyt00)
- **🐦 Twitter (X)**: [@irotechlab](https://twitter.com/irotechlab)
- **📨 Telegram**: [@ironmanhindigaming](https://t.me/ironmanhindigaming)
- **📧 Telegram Channel**: [@irotechcoders](https://t.me/irotechcoders)
- **🐙 GitHub**: [IROTECHLAB/irodb](https://github.com/IROTECHLAB/irodb)

### Issues and Pull Requests

- **Report Issues**: [GitHub Issues](https://github.com/IROTECHLAB/irodb/issues)
- **Submit PRs**: [GitHub Pull Requests](https://github.com/IROTECHLAB/irodb/pulls)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👥 Authors

- **IROTECHLAB** - *Initial work* - [GitHub](https://github.com/IROTECHLAB)

## 🙏 Acknowledgments

- Built with Python's built-in libraries
- Inspired by simplicity and data integrity
- Community contributions welcome

## 📦 PyPI Package Information

- **Package Name**: `irotechlab-irodb`
- **Total Downloads**: Growing daily
- **PyPI Link**: [https://pypi.org/project/irotechlab-irodb/](https://pypi.org/project/irotechlab-irodb/)

### Install from PyPI

```bash
pip install irotechlab-irodb
```

### Upgrade

```bash
pip install --upgrade irotechlab-irodb
```

### Verify Installation

```bash
python -c "import irodb; print(irodb.__version__)"
```
---

Made with ❤️ by **IROTECHLAB**

[![Star on GitHub](https://img.shields.io/github/stars/IROTECHLAB/irodb.svg)](https://github.com/IROTECHLAB/irodb)
[![Fork on GitHub](https://img.shields.io/github/forks/IROTECHLAB/irodb.svg)](https://github.com/IROTECHLAB/irodb)
[![Issues](https://img.shields.io/github/issues/IROTECHLAB/irodb.svg)](https://github.com/IROTECHLAB/irodb/issues)
