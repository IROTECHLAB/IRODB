"""
SQL-like Query Language for IRODB
"""

import re
import json
from typing import List, Dict, Any, Optional, Union, Tuple
from datetime import datetime

from .exceptions import SQLError, IRODBError

class SQLParser:
    """SQL-like query parser and executor"""
    
    def __init__(self, db):
        self.db = db
        self._keywords = {
            'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP',
            'ALTER', 'FROM', 'WHERE', 'SET', 'VALUES', 'INTO', 'JOIN',
            'ON', 'AND', 'OR', 'NOT', 'LIKE', 'IN', 'BETWEEN', 'IS',
            'NULL', 'ORDER', 'BY', 'GROUP', 'HAVING', 'LIMIT', 'OFFSET'
        }
    
    def execute(self, query: str) -> Union[List[Dict], int, Dict]:
        """Execute a SQL-like query"""
        query = query.strip()
        
        try:
            if query.upper().startswith('SELECT'):
                return self._parse_select(query)
            elif query.upper().startswith('INSERT'):
                return self._parse_insert(query)
            elif query.upper().startswith('UPDATE'):
                return self._parse_update(query)
            elif query.upper().startswith('DELETE'):
                return self._parse_delete(query)
            elif query.upper().startswith('CREATE'):
                return self._parse_create(query)
            elif query.upper().startswith('DROP'):
                return self._parse_drop(query)
            else:
                raise SQLError(f"Unsupported SQL statement: {query[:50]}...")
        except SQLError:
            raise
        except IRODBError as e:
            raise SQLError(str(e)) from e
        except Exception as e:
            raise SQLError(f"Unexpected SQL error: {e}") from e
    
    def _parse_select(self, query: str) -> List[Dict[str, Any]]:
        """Parse SELECT query"""
        # Extract components
        select_pattern = r'SELECT\s+(.*?)\s+FROM\s+(\w+)(?:\s+(.*))?'
        match = re.match(select_pattern, query, re.IGNORECASE)
        
        if not match:
            raise SQLError("Invalid SELECT syntax")
        
        columns_str = match.group(1)
        table_name = match.group(2)
        rest = match.group(3) or ''
        
        # Parse columns
        if columns_str.strip() == '*':
            columns = None
        else:
            columns = [col.strip() for col in columns_str.split(',')]
        
        # Parse WHERE clause
        conditions = {}
        where_clause = None
        order_by = None
        group_by = None
        having = None
        limit = None
        offset = 0
        
        # Parse WHERE
        where_match = re.search(r'WHERE\s+(.+?)(?:\s+(ORDER|GROUP|LIMIT|HAVING)|$)', rest, re.IGNORECASE)
        if where_match:
            where_clause = where_match.group(1).strip()
            rest = rest.replace(where_match.group(0), '').strip()
        
        # Parse ORDER BY
        order_match = re.search(r'ORDER\s+BY\s+(.+?)(?:\s+(LIMIT|GROUP|HAVING)|$)', rest, re.IGNORECASE)
        if order_match:
            order_by = order_match.group(1).strip()
            rest = rest.replace(order_match.group(0), '').strip()
        
        # Parse LIMIT
        limit_match = re.search(r'LIMIT\s+(\d+)(?:\s+OFFSET\s+(\d+))?', rest, re.IGNORECASE)
        if limit_match:
            limit = int(limit_match.group(1))
            if limit_match.group(2):
                offset = int(limit_match.group(2))
            rest = rest.replace(limit_match.group(0), '').strip()
        
        # Parse GROUP BY
        group_match = re.search(r'GROUP\s+BY\s+(.+?)(?:\s+(HAVING|LIMIT)\b|$)', rest, re.IGNORECASE)
        if group_match:
            group_by = group_match.group(1).strip()
            rest = rest.replace(group_match.group(0), '').strip()
        
        # Parse HAVING
        having_match = re.search(r'HAVING\s+(.+?)(?:\s+(LIMIT)\b|$)', rest, re.IGNORECASE)
        if having_match:
            having = having_match.group(1).strip()
        
        # Execute query
        rows = self.db.select(table_name)
        
        # Apply WHERE conditions
        if where_clause:
            conditions = self._parse_conditions(where_clause)
            rows = self._apply_conditions(rows, conditions)
        
        # Apply GROUP BY
        if group_by:
            rows = self._apply_group_by(rows, group_by, having)
        
        # Apply ORDER BY
        if order_by:
            rows = self._apply_order_by(rows, order_by)
        
        # Apply LIMIT and OFFSET
        if limit is not None:
            rows = rows[offset:offset + limit]
        
        # Select columns
        if columns:
            result = []
            for row in rows:
                selected_row = {}
                for col in columns:
                    if col.lower() == 'count(*)':
                        selected_row['count(*)'] = len(row.get('_rows', rows))
                    elif col in row:
                        selected_row[col] = row[col]
                    else:
                        # Handle aggregation functions
                        if '(' in col and ')' in col:
                            selected_row[col] = self._apply_aggregation(row.get('_rows', rows), col)
                result.append(selected_row)
            return result
        
        return rows
    
    def _parse_insert(self, query: str) -> int:
        """Parse INSERT query"""
        pattern = r'INSERT\s+INTO\s+(\w+)\s*\((.*?)\)\s+VALUES\s*\((.*?)\)'
        match = re.match(pattern, query, re.IGNORECASE | re.DOTALL)
        
        if not match:
            raise SQLError("Invalid INSERT syntax")
        
        table_name = match.group(1)
        columns = [col.strip() for col in match.group(2).split(',') if col.strip()]
        values = [val.strip() for val in match.group(3).split(',') if val.strip()]
        
        if len(columns) != len(values):
            raise SQLError("Number of columns must match number of values")
        
        data = {}
        for col, val in zip(columns, values):
            parsed = self._parse_literal(val)
            schema_type = self.db.tables.get(table_name, {}).get('schema', {}).get(col)
            if schema_type is float and isinstance(parsed, int) and not isinstance(parsed, bool):
                parsed = float(parsed)
            data[col] = parsed
        
        return self.db.insert(table_name, data)
    
    def _parse_update(self, query: str) -> int:
        """Parse UPDATE query"""
        pattern = r'UPDATE\s+(\w+)\s+SET\s+(.+?)(?:\s+WHERE\s+(.+))?$'
        match = re.match(pattern, query, re.IGNORECASE | re.DOTALL)
        
        if not match:
            raise SQLError("Invalid UPDATE syntax")
        
        table_name = match.group(1)
        set_clause = match.group(2)
        where_clause = match.group(3) if match.group(3) else None
        
        # Parse SET clause
        updates = {}
        for assignment in set_clause.split(','):
            key, val = assignment.split('=', 1)
            key = key.strip()
            parsed = self._parse_literal(val.strip())
            schema_type = self.db.tables.get(table_name, {}).get('schema', {}).get(key)
            if schema_type is float and isinstance(parsed, int) and not isinstance(parsed, bool):
                parsed = float(parsed)
            updates[key] = parsed
        
        # Parse WHERE conditions
        conditions = self._parse_conditions(where_clause) if where_clause else {}
        
        return self.db.update(table_name, conditions, updates)
    
    def _parse_delete(self, query: str) -> int:
        """Parse DELETE query"""
        pattern = r'DELETE\s+FROM\s+(\w+)(?:\s+WHERE\s+(.+))?$'
        match = re.match(pattern, query, re.IGNORECASE)
        
        if not match:
            raise SQLError("Invalid DELETE syntax")
        
        table_name = match.group(1)
        where_clause = match.group(2) if match.group(2) else None
        
        conditions = self._parse_conditions(where_clause) if where_clause else {}
        
        return self.db.delete(table_name, conditions)
    
    def _parse_create(self, query: str) -> Dict[str, Any]:
        """Parse CREATE TABLE query"""
        pattern = r'CREATE\s+TABLE\s+(\w+)\s*\((.*?)\)'
        match = re.match(pattern, query, re.IGNORECASE | re.DOTALL)
        
        if not match:
            raise SQLError("Invalid CREATE TABLE syntax")
        
        table_name = match.group(1)
        columns_str = match.group(2)
        
        schema = {}
        
        for column_def in columns_str.split(','):
            parts = column_def.strip().split()
            if not parts:
                continue
            
            col_name = parts[0]
            col_type = parts[1] if len(parts) > 1 else 'text'
            
            # Map SQL types to Python types
            type_map = {
                'text': str, 'string': str, 'varchar': str,
                'int': int, 'integer': int, 'number': int,
                'float': float, 'real': float,
                'bool': bool, 'boolean': bool,
                'date': str, 'datetime': str
            }
            
            schema[col_name] = type_map.get(col_type.lower(), str)
        
        self.db.create_table(table_name, schema, enable_hash_index=True)
        return {'table': table_name, 'schema': schema}
    
    def _parse_drop(self, query: str) -> Dict[str, str]:
        """Parse DROP TABLE query"""
        pattern = r'DROP\s+TABLE\s+(\w+)'
        match = re.search(pattern, query, re.IGNORECASE)
        
        if not match:
            raise SQLError("Invalid DROP TABLE syntax")
        
        table_name = match.group(1)
        del self.db.tables[table_name]
        self.db._save_metadata()
        
        return {'dropped': table_name}
    
    def _parse_conditions(self, where_clause: str) -> Dict[str, Any]:
        """Parse WHERE conditions into dict"""
        conditions = {}
        
        # Handle conjunctions before individual comparisons.
        if re.search(r'\s+AND\s+', where_clause, re.IGNORECASE):
            for clause in re.split(r'\s+AND\s+', where_clause, flags=re.IGNORECASE):
                conditions.update(self._parse_conditions(clause))
            return conditions
        if re.search(r'\s+OR\s+', where_clause, re.IGNORECASE):
            return {'$or': [self._parse_conditions(clause) for clause in re.split(r'\s+OR\s+', where_clause, flags=re.IGNORECASE)]}

        # Handle equality and comparison operators.
        comparison = re.match(r'^([A-Za-z_]\w*)\s*(>=|<=|<>|!=|=|>|<)\s*(.*?)\s*$', where_clause)
        if comparison:
            field, operator, literal = comparison.groups()
            operator_map = {'=': None, '>': 'gt', '>=': 'gte', '<': 'lt', '<=': 'lte', '!=': 'ne', '<>': 'ne'}
            parsed = self._parse_literal(literal)
            conditions[field] = parsed if operator_map[operator] is None else {operator_map[operator]: parsed}
            return conditions
        
        # Handle LIKE
        like_match = re.search(r'(\w+)\s+LIKE\s+[\'"]([^\'"]+)[\'"]', where_clause, re.IGNORECASE)
        if like_match:
            field = like_match.group(1)
            pattern = like_match.group(2)
            conditions[field] = {'like': pattern}
            return conditions
        
        # Handle IN
        in_match = re.search(r'(\w+)\s+IN\s*\(([^)]+)\)', where_clause, re.IGNORECASE)
        if in_match:
            field = in_match.group(1)
            values = [self._parse_literal(v.strip()) for v in in_match.group(2).split(',')]
            conditions[field] = {'in': values}
            return conditions
        
        # Handle IS NULL
        null_match = re.search(r'(\w+)\s+IS\s+NULL', where_clause, re.IGNORECASE)
        if null_match:
            conditions[null_match.group(1)] = {'is_null': True}
            return conditions
        

        
        # Default: return as is
        return conditions
    
    def _parse_literal(self, value: str) -> Any:
        """Parse literal values"""
        value = value.strip()
        
        # Remove quotes
        if value.startswith("'") and value.endswith("'"):
            return value[1:-1]
        if value.startswith('"') and value.endswith('"'):
            return value[1:-1]
        
        # Handle NULL
        if value.upper() == 'NULL':
            return None
        
        # Handle booleans
        if value.upper() == 'TRUE':
            return True
        if value.upper() == 'FALSE':
            return False
        
        # Handle numbers
        try:
            if '.' in value:
                return float(value)
            return int(value)
        except ValueError:
            return value
    
    def _apply_conditions(self, rows: List[Dict], conditions: Dict) -> List[Dict]:
        """Apply conditions to rows"""
        result = []
        
        for row in rows:
            if self._row_matches_conditions(row, conditions):
                result.append(row)
        
        return result
    
    def _row_matches_conditions(self, row: Dict, conditions: Dict) -> bool:
        """Check if row matches conditions"""
        for key, value in conditions.items():
            if key == '$or':
                # OR conditions
                if not any(self._row_matches_conditions(row, cond) for cond in value):
                    return False
                continue
            
            if key not in row:
                return False
            
            if isinstance(value, dict):
                if 'like' in value:
                    # LIKE condition
                    pattern = value['like'].replace('%', '.*')
                    if not re.match(pattern, str(row[key]), re.IGNORECASE):
                        return False
                elif 'in' in value:
                    # IN condition
                    if row[key] not in value['in']:
                        return False
                elif 'is_null' in value:
                    # IS NULL condition
                    if row[key] is not None:
                        return False
                else:
                    for operator, target in value.items():
                        try:
                            if operator == 'gt' and not row[key] > target: return False
                            if operator == 'gte' and not row[key] >= target: return False
                            if operator == 'lt' and not row[key] < target: return False
                            if operator == 'lte' and not row[key] <= target: return False
                            if operator == 'ne' and row[key] == target: return False
                        except TypeError:
                            return False
            else:
                # Equality condition
                if row[key] != value:
                    return False
        
        return True
    
    def _apply_order_by(self, rows: List[Dict], order_by: str) -> List[Dict]:
        """Apply ORDER BY clause"""
        parts = order_by.split()
        field = parts[0]
        direction = 'ASC' if len(parts) < 2 else parts[1].upper()
        
        reverse = direction == 'DESC'
        
        return sorted(rows, key=lambda x: x.get(field, ''), reverse=reverse)
    
    def _apply_group_by(self, rows: List[Dict], group_by: str, having: str = None) -> List[Dict]:
        """Apply GROUP BY clause"""
        groups = {}
        
        for row in rows:
            key = row.get(group_by)
            if key not in groups:
                groups[key] = []
            groups[key].append(row)
        
        result = []
        for key, group_rows in groups.items():
            group_result = {group_by: key}
            group_result['_count'] = len(group_rows)
            group_result['_rows'] = group_rows
            result.append(group_result)
        
        if having:
            having_conditions = self._parse_conditions(having)
            result = self._apply_conditions(result, having_conditions)
        
        return result
    
    def _apply_aggregation(self, rows: List[Dict], expr: str) -> Any:
        """Apply aggregation function"""
        pattern = r'(\w+)\((.+?)\)'
        match = re.match(pattern, expr, re.IGNORECASE)
        
        if not match:
            return None
        
        func = match.group(1).upper()
        field = match.group(2).strip()
        
        if field == '*':
            values = [row for row in rows]
        else:
            values = [row.get(field) for row in rows if field in row]
        
        if not values:
            return None
        
        if func == 'COUNT':
            return len(values)
        elif func == 'SUM':
            return sum(v for v in values if isinstance(v, (int, float)))
        elif func == 'AVG':
            nums = [v for v in values if isinstance(v, (int, float))]
            return sum(nums) / len(nums) if nums else 0
        elif func == 'MAX':
            return max(values)
        elif func == 'MIN':
            return min(values)
        
        return None