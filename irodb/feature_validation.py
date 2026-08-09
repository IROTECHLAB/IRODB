"""
Data Validation & Constraints System for IRODB
"""

import re
import pickle
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime

from .exceptions import ValidationError, ConstraintError

class DataValidator:
    """Data validation and constraints enforcement"""
    
    def __init__(self, db):
        self.db = db
        self.validators = {}
        self.constraints = {}
        self._builtin_validators = {
            'email': self._validate_email,
            'phone': self._validate_phone,
            'url': self._validate_url,
            'ip': self._validate_ip,
            'date': self._validate_date,
            'datetime': self._validate_datetime,
            'credit_card': self._validate_credit_card
        }
        
        # Load constraints from database if available
        if hasattr(db, 'constraints'):
            self.constraints = db.constraints
    
    def add_validator(self, validator_name: str, 
                      validator_fn: Callable[[Any], bool],
                      error_message: str = None):
        """Add a custom validator"""
        self.validators[validator_name] = {
            'function': validator_fn,
            'error_message': error_message or f"Validation failed for {validator_name}"
        }
    
    def add_table_constraints(self, table_name: str, constraints: Dict[str, Any]):
        """Add constraints to a table"""
        if table_name not in self.db.tables:
            raise ValidationError(f"Table {table_name} does not exist")
        
        if table_name not in self.constraints:
            self.constraints[table_name] = {}
        
        self.constraints[table_name].update(constraints)
        
        # Save to database
        if hasattr(self.db, 'constraints'):
            self.db.constraints = self.constraints
            self.db._save_metadata()
    
    def validate_row(self, table_name: str, row: Dict[str, Any]) -> bool:
        """Validate a row against constraints"""
        if table_name not in self.constraints:
            return True
        
        table_constraints = self.constraints.get(table_name, {})
        
        for field, constraint in table_constraints.items():
            value = row.get(field)
            
            # Check required
            if constraint.get('required', False) and (value is None or value == ''):
                raise ValidationError(f"Field '{field}' is required")
            
            # Skip validation if value is None and not required
            if value is None:
                continue
            
            # Check type
            if 'type' in constraint:
                expected_type = constraint['type']
                if not isinstance(value, expected_type):
                    raise ValidationError(
                        f"Field '{field}' must be of type {expected_type.__name__}, got {type(value).__name__}"
                    )
            
            # Check min/max for numbers
            if isinstance(value, (int, float)):
                if 'min' in constraint and value < constraint['min']:
                    raise ValidationError(
                        f"Field '{field}' must be >= {constraint['min']}, got {value}"
                    )
                if 'max' in constraint and value > constraint['max']:
                    raise ValidationError(
                        f"Field '{field}' must be <= {constraint['max']}, got {value}"
                    )
            
            # Check length for strings
            if isinstance(value, str):
                if 'min_length' in constraint and len(value) < constraint['min_length']:
                    raise ValidationError(
                        f"Field '{field}' must be at least {constraint['min_length']} characters, got {len(value)}"
                    )
                if 'max_length' in constraint and len(value) > constraint['max_length']:
                    raise ValidationError(
                        f"Field '{field}' must be at most {constraint['max_length']} characters, got {len(value)}"
                    )
            
            # Check pattern for strings
            if 'pattern' in constraint and isinstance(value, str):
                if not re.match(constraint['pattern'], value):
                    raise ValidationError(
                        f"Field '{field}' does not match required pattern: {constraint['pattern']}"
                    )
            
            # Check built-in validator
            if 'validator' in constraint:
                validator_name = constraint['validator']
                if validator_name in self._builtin_validators:
                    if not self._builtin_validators[validator_name](value):
                        raise ValidationError(
                            f"Field '{field}' is not a valid {validator_name}"
                        )
                elif validator_name in self.validators:
                    if not self.validators[validator_name]['function'](value):
                        raise ValidationError(
                            self.validators[validator_name]['error_message']
                        )
                else:
                    raise ValidationError(f"Unknown validator: {validator_name}")
            
            # Check allowed values
            if 'allowed_values' in constraint:
                if value not in constraint['allowed_values']:
                    raise ValidationError(
                        f"Field '{field}' must be one of {constraint['allowed_values']}, got {value}"
                    )
            
            # Check custom validator
            if 'custom_validator' in constraint and callable(constraint['custom_validator']):
                if not constraint['custom_validator'](value):
                    raise ValidationError(
                        f"Field '{field}' failed custom validation"
                    )
        
        return True
    
    def enforce_unique(self, table_name: str, row: Dict[str, Any],
                       exclude_id: int = None) -> bool:
        """Enforce unique constraints"""
        if table_name not in self.constraints:
            return True
        
        table_constraints = self.constraints.get(table_name, {})
        unique_fields = []
        
        for field, constraint in table_constraints.items():
            if constraint.get('unique', False):
                unique_fields.append(field)
        
        if not unique_fields:
            return True
        
        # Check for duplicates
        try:
            page_data = self.db._read_page(self.db.tables[table_name]['page'])
            table_data = pickle.loads(page_data)
        except:
            return True
        
        for existing_row in table_data.get('rows', []):
            # Skip the row being updated
            if exclude_id is not None and existing_row.get('id') == exclude_id:
                continue
            
            for field in unique_fields:
                if field in row and field in existing_row:
                    if row[field] == existing_row[field]:
                        raise ConstraintError(
                            f"Unique constraint violation: '{field}' must be unique, '{row[field]}' already exists"
                        )
        
        return True
    
    def enforce_foreign_key(self, table_name: str, row: Dict[str, Any],
                           exclude_id: int = None) -> bool:
        """Enforce foreign key constraints"""
        if table_name not in self.constraints:
            return True
        
        table_constraints = self.constraints.get(table_name, {})
        
        for field, constraint in table_constraints.items():
            if 'foreign_key' in constraint:
                fk_info = constraint['foreign_key']
                fk_table = fk_info['table']
                fk_field = fk_info['field']
                
                if fk_table not in self.db.tables:
                    raise ConstraintError(f"Foreign key table '{fk_table}' does not exist")
                
                if field not in row or row[field] is None:
                    if constraint.get('required', False):
                        raise ConstraintError(f"Foreign key field '{field}' is required")
                    continue
                
                # Check if referenced value exists
                try:
                    fk_data = pickle.loads(self.db._read_page(self.db.tables[fk_table]['page']))
                    exists = any(existing_row.get(fk_field) == row[field] for existing_row in fk_data.get('rows', []))
                except:
                    exists = False
                
                if not exists:
                    raise ConstraintError(
                        f"Foreign key violation: '{row[field]}' does not exist in {fk_table}.{fk_field}"
                    )
        
        return True
    
    def check_constraints_on_insert(self, table_name: str, row: Dict[str, Any]) -> bool:
        """Check all constraints before insert"""
        self.validate_row(table_name, row)
        self.enforce_unique(table_name, row)
        self.enforce_foreign_key(table_name, row)
        return True
    
    def check_constraints_on_update(self, table_name: str, row: Dict[str, Any], 
                                    row_id: int) -> bool:
        """Check all constraints before update"""
        self.validate_row(table_name, row)
        self.enforce_unique(table_name, row, exclude_id=row_id)
        return True
    
    def _save_constraints(self):
        """Save constraints to database"""
        if hasattr(self.db, 'constraints'):
            self.db.constraints = self.constraints
            self.db._save_metadata()
    
    def _validate_email(self, value: str) -> bool:
        """Validate email format"""
        if not value:
            return False
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, str(value)))
    
    def _validate_phone(self, value: str) -> bool:
        """Validate phone number"""
        if not value:
            return False
        pattern = r'^[\+\d\s\-\(\)]{7,20}$'
        return bool(re.match(pattern, str(value)))
    
    def _validate_url(self, value: str) -> bool:
        """Validate URL"""
        if not value:
            return False
        pattern = r'^https?://[^\s]+$'
        return bool(re.match(pattern, str(value)))
    
    def _validate_ip(self, value: str) -> bool:
        """Validate IP address"""
        if not value:
            return False
        pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if not re.match(pattern, str(value)):
            return False
        parts = value.split('.')
        return all(0 <= int(p) <= 255 for p in parts)
    
    def _validate_date(self, value: str) -> bool:
        """Validate date format (YYYY-MM-DD)"""
        if not value:
            return False
        try:
            datetime.strptime(str(value), '%Y-%m-%d')
            return True
        except ValueError:
            return False
    
    def _validate_datetime(self, value: str) -> bool:
        """Validate datetime format (YYYY-MM-DD HH:MM:SS)"""
        if not value:
            return False
        try:
            datetime.strptime(str(value), '%Y-%m-%d %H:%M:%S')
            return True
        except ValueError:
            return False
    
    def _validate_credit_card(self, value: str) -> bool:
        """Validate credit card number (Luhn algorithm)"""
        if not value:
            return False
        digits = re.sub(r'\D', '', str(value))
        if not digits or len(digits) < 13:
            return False
        
        total = 0
        reverse_digits = digits[::-1]
        for i, digit in enumerate(reverse_digits):
            n = int(digit)
            if i % 2 == 1:
                n *= 2
                if n > 9:
                    n -= 9
            total += n
        
        return total % 10 == 0