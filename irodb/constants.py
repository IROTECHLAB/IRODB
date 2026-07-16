"""
Constants used throughout the IRODB system
"""

# Database format constants
MAGIC_HEADER = b'IRODB'
VERSION = 1
PAGE_SIZE = 4096
MAX_PAGES = 2**32 - 1
MAX_TABLES = 1000
MAX_INDEXES = 100

# Hash constants
HASH_ALGORITHM = 'sha256'
HASH_SIZE = 64  # SHA-256 hex length
SALT_SIZE = 16

# File extensions
DB_EXTENSION = '.irodb'
INDEX_EXTENSION = '.idx'
LOG_EXTENSION = '.log'
TEMP_EXTENSION = '.tmp'

# Operation types
OP_INSERT = 'INSERT'
OP_UPDATE = 'UPDATE'
OP_DELETE = 'DELETE'
OP_CREATE_TABLE = 'CREATE_TABLE'
OP_DROP_TABLE = 'DROP_TABLE'

# Index types
INDEX_BTREE = 'btree'
INDEX_HASH = 'hash'
INDEX_BITMAP = 'bitmap'

# Error codes
ERR_SUCCESS = 0
ERR_GENERAL = 1
ERR_NOT_FOUND = 2
ERR_DUPLICATE = 3
ERR_CORRUPTED = 4
ERR_PERMISSION = 5
ERR_IO = 6

# Default paths
DEFAULT_DB_DIR = '~/.irodb'
DEFAULT_CONFIG_FILE = 'config.json'
DEFAULT_LOG_FILE = 'irodb.log'

# Metadata keys
METADATA_TABLES = 'tables'
METADATA_INDEXES = 'indexes'
METADATA_HASH_INDEXES = 'hash_indexes'
METADATA_NEXT_PAGE = 'next_page'
METADATA_CREATED_AT = 'created_at'
METADATA_VERSION = 'version'
METADATA_TRANSACTIONS = 'transactions'