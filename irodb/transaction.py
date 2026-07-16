"""
Transaction management for IRODB
"""

import pickle
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid

from .exceptions import TransactionError

class Transaction:
    """Represents a database transaction"""
    
    def __init__(self, transaction_id: str):
        self.id = transaction_id
        self.operations = []
        self.status = 'pending'
        self.created_at = datetime.now()
        self.committed_at = None
        self.rolled_back_at = None
    
    def add_operation(self, operation_type: str, table: str, data: Dict[str, Any]):
        """Add an operation to the transaction"""
        self.operations.append({
            'type': operation_type,
            'table': table,
            'data': data,
            'timestamp': datetime.now().isoformat()
        })
    
    def commit(self):
        """Commit the transaction"""
        self.status = 'committed'
        self.committed_at = datetime.now()
    
    def rollback(self):
        """Rollback the transaction"""
        self.status = 'rolled_back'
        self.rolled_back_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert transaction to dict"""
        return {
            'id': self.id,
            'operations': self.operations,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'committed_at': self.committed_at.isoformat() if self.committed_at else None,
            'rolled_back_at': self.rolled_back_at.isoformat() if self.rolled_back_at else None
        }

class TransactionManager:
    """Manages database transactions"""
    
    def __init__(self, db):
        self.db = db
        self.current_transaction = None
        self.transaction_history = []
    
    def begin(self) -> Transaction:
        """Begin a new transaction"""
        if self.current_transaction:
            raise TransactionError("Transaction already in progress")
        
        transaction_id = str(uuid.uuid4())
        self.current_transaction = Transaction(transaction_id)
        return self.current_transaction
    
    def commit(self):
        """Commit current transaction"""
        if not self.current_transaction:
            raise TransactionError("No transaction in progress")
        
        # Apply all operations
        for op in self.current_transaction.operations:
            if op['type'] == 'INSERT':
                self.db.insert(op['table'], op['data'])
            elif op['type'] == 'UPDATE':
                self.db.update(op['table'], op['data']['conditions'], op['data']['updates'])
            elif op['type'] == 'DELETE':
                self.db.delete(op['table'], op['data']['conditions'])
        
        self.current_transaction.commit()
        self.transaction_history.append(self.current_transaction.to_dict())
        self.db._save_metadata()
        self.current_transaction = None
    
    def rollback(self):
        """Rollback current transaction"""
        if not self.current_transaction:
            raise TransactionError("No transaction in progress")
        
        self.current_transaction.rollback()
        self.transaction_history.append(self.current_transaction.to_dict())
        self.current_transaction = None
    
    def get_transactions(self) -> List[Dict[str, Any]]:
        """Get transaction history"""
        return self.transaction_history
    
    def rollback_to(self, transaction_id: str):
        """Rollback to a specific transaction"""
        # Find transaction index
        idx = -1
        for i, txn in enumerate(self.transaction_history):
            if txn['id'] == transaction_id:
                idx = i
                break
        
        if idx == -1:
            raise TransactionError(f"Transaction {transaction_id} not found")
        
        # Mark subsequent transactions as rolled back
        for txn in self.transaction_history[idx:]:
            txn['status'] = 'rolled_back'
            txn['rolled_back_at'] = datetime.now().isoformat()
        
        self.db._save_metadata()