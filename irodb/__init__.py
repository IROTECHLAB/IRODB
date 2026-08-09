"""
IRODB - A Python database library with .irodb format and hash-based indexing
"""

from .core import IRODB
from .hash_system import HashManager
from .index import IndexManager
from .transaction import TransactionManager
from .utils import DatabaseUtils
from .exceptions import (
    IRODBError, 
    HashError, 
    IntegrityError, 
    DatabaseError,
    TableError,
    IndexError,
    TransactionError,
    PageError,
    PermissionError,
    CorruptedError,
    NotFoundError,
    DuplicateError,
    SearchError,
    ValidationError,
    ConstraintError,
    SQLError
)
from .constants import VERSION, PAGE_SIZE, MAGIC_HEADER

# Import features
try:
    from .feature_fulltext import FullTextSearch
except ImportError:
    FullTextSearch = None

try:
    from .feature_sql import SQLParser
except ImportError:
    SQLParser = None

try:
    from .feature_validation import DataValidator
except ImportError:
    DataValidator = None

__version__ = "0.2.0"
__all__ = [
    'IRODB',
    'HashManager',
    'IndexManager',
    'TransactionManager',
    'DatabaseUtils',
    'FullTextSearch',
    'SQLParser',
    'DataValidator',
    'IRODBError',
    'HashError',
    'IntegrityError',
    'DatabaseError',
    'TableError',
    'IndexError',
    'TransactionError',
    'PageError',
    'PermissionError',
    'CorruptedError',
    'NotFoundError',
    'DuplicateError',
    'SearchError',
    'ValidationError',
    'ConstraintError',
    'SQLError',
    'VERSION',
    'PAGE_SIZE',
    'MAGIC_HEADER'
]