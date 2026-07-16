"""
IRODB - A Python database library with .irodb format and hash-based indexing
"""

from .core import IRODB
from .hash_system import HashManager
from .index import IndexManager
from .transaction import TransactionManager
from .utils import DatabaseUtils
from .exceptions import IRODBError, HashError, IntegrityError
from .constants import VERSION, PAGE_SIZE, MAGIC_HEADER

__version__ = "1.0.0"
__all__ = [
    'IRODB',
    'HashManager',
    'IndexManager',
    'TransactionManager',
    'DatabaseUtils',
    'IRODBError',
    'HashError',
    'IntegrityError',
    'VERSION',
    'PAGE_SIZE',
    'MAGIC_HEADER'
]
