# irodb/exceptions.py
class IRODBError(Exception):
    """Base exception for IRODB"""
    pass

class DatabaseError(IRODBError):
    """Database operation error"""
    pass

class TableError(IRODBError):
    """Table operation error"""
    pass

class IndexError(IRODBError):
    """Index operation error"""
    pass

class HashError(IRODBError):
    """Hash operation error"""
    pass

class IntegrityError(IRODBError):
    """Data integrity error"""
    pass

class TransactionError(IRODBError):
    """Transaction error"""
    pass

class PageError(IRODBError):
    """Page operation error"""
    pass

class PermissionError(IRODBError):
    """Permission error"""
    pass

class CorruptedError(IRODBError):
    """Corrupted database error"""
    pass

class NotFoundError(IRODBError):
    """Record not found error"""
    pass

class DuplicateError(IRODBError):
    """Duplicate record error"""
    pass