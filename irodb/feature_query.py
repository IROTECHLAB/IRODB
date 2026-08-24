"""Simple, parameterized IRODB Query language.

The grammar is intentionally not SQL. Queries are parsed into a small set of
operations and values are either typed literals or separately supplied params.
No query fragment is evaluated as Python code or concatenated into executable SQL.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from .exceptions import SQLError

_IDENTIFIER = r"[A-Za-z_]\w*"
_TYPES = {"text": str, "string": str, "int": int, "integer": int, "float": float, "number": float, "bool": bool, "boolean": bool}
_OPERATORS = {"=": None, "!=": "$ne", "<>": "$ne", ">": "$gt", ">=": "$gte", "<": "$lt", "<=": "$lte"}


class IRODBQuery:
    """Execute the safe IRODB Query language."""

    def __init__(self, db):
        self.db = db

    def execute(self, query: str, params: Optional[Dict[str, Any]] = None):
        if not isinstance(query, str) or not query.strip():
            raise SQLError("IRODB Query cannot be empty")
        params = params or {}
        text = query.strip()
        if not re.match(r"^IRODB\s+", text, re.IGNORECASE):
            raise SQLError("IRODB Query must start with 'IRODB'")
        body = re.sub(r"^IRODB\s+", "", text, count=1, flags=re.IGNORECASE).strip()
        command = body.split(None, 1)[0].upper() if body else ""
        try:
            if command == "GET":
                return self._get(body, params)
            if command == "INSERT":
                return self._insert(body, params)
            if command == "UPDATE":
                return self._update(body, params)
            if command == "DELETE":
                return self._delete(body, params)
            if command == "CREATE":
                return self._create(body)
            if command == "DROP":
                return self._drop(body)
            raise SQLError(f"Unknown IRODB Query command: {command or '<empty>'}")
        except SQLError:
            raise
        except Exception as exc:
            raise SQLError(f"IRODB Query failed: {exc}") from exc

    def _get(self, body: str, params: Dict[str, Any]):
        match = re.match(
            rf"^GET\s+({_IDENTIFIER})(?:\s+WHERE\s+(.+?))?(?:\s+ORDER\s+({_IDENTIFIER})(?:\s+(ASC|DESC))?)?(?:\s+LIMIT\s+(\d+))?$",
            body, re.IGNORECASE,
        )
        if not match:
            raise SQLError("Use: IRODB GET table [WHERE field = :value] [ORDER field ASC|DESC] [LIMIT n]")
        table, where, order_field, direction, limit = match.groups()
        rows = self.db.select(table, self._conditions(where, params) if where else None)
        if order_field:
            rows.sort(key=lambda row: (row.get(order_field) is None, row.get(order_field)), reverse=(direction or "ASC").upper() == "DESC")
        return rows[: int(limit)] if limit else rows

    def _insert(self, body: str, params: Dict[str, Any]) -> int:
        match = re.match(rf"^INSERT\s+({_IDENTIFIER})\s+VALUES\s+(.+)$", body, re.IGNORECASE)
        if not match:
            raise SQLError("Use: IRODB INSERT table VALUES field=:value, other=:value")
        table, assignments = match.groups()
        return self.db.insert(table, self._assignments(assignments, params))

    def _update(self, body: str, params: Dict[str, Any]) -> int:
        match = re.match(rf"^UPDATE\s+({_IDENTIFIER})\s+SET\s+(.+?)(?:\s+WHERE\s+(.+))?$", body, re.IGNORECASE)
        if not match:
            raise SQLError("Use: IRODB UPDATE table SET field=:value WHERE field=:value")
        table, assignments, where = match.groups()
        return self.db.update(table, self._conditions(where, params) if where else {}, self._assignments(assignments, params))

    def _delete(self, body: str, params: Dict[str, Any]) -> int:
        match = re.match(rf"^DELETE\s+({_IDENTIFIER})(?:\s+WHERE\s+(.+))?$", body, re.IGNORECASE)
        if not match:
            raise SQLError("Use: IRODB DELETE table WHERE field=:value")
        table, where = match.groups()
        if not where:
            raise SQLError("DELETE requires a WHERE clause for safety")
        return self.db.delete(table, self._conditions(where, params))

    def _create(self, body: str):
        match = re.match(rf"^CREATE\s+({_IDENTIFIER})\s+SCHEMA\s+(.+)$", body, re.IGNORECASE)
        if not match:
            raise SQLError("Use: IRODB CREATE table SCHEMA name:text, age:int")
        table, schema_text = match.groups()
        schema = {}
        for item in self._split(schema_text):
            parts = item.split(":", 1)
            if len(parts) != 2 or not re.fullmatch(_IDENTIFIER, parts[0].strip()):
                raise SQLError(f"Invalid schema field: {item}")
            type_name = parts[1].strip().lower()
            if type_name not in _TYPES:
                raise SQLError(f"Unsupported IRODB type: {type_name}")
            schema[parts[0].strip()] = _TYPES[type_name]
        return self.db.create_table(table, schema, enable_hash_index=True)

    def _drop(self, body: str):
        match = re.fullmatch(rf"DROP\s+({_IDENTIFIER})", body, re.IGNORECASE)
        if not match:
            raise SQLError("Use: IRODB DROP table")
        table = match.group(1)
        if table not in self.db.tables:
            raise SQLError(f"Table {table} does not exist")
        del self.db.tables[table]
        self.db._save_metadata()
        return {"dropped": table}

    def _conditions(self, text: str, params: Dict[str, Any]) -> Dict[str, Any]:
        result = {}
        for clause in re.split(r"\s+AND\s+", text.strip(), flags=re.IGNORECASE):
            match = re.fullmatch(rf"({_IDENTIFIER})\s*(>=|<=|!=|<>|=|>|<)\s*(.+)", clause.strip())
            if not match:
                raise SQLError(f"Invalid condition: {clause}")
            field, operator, raw_value = match.groups()
            value = self._value(raw_value.strip(), params)
            mapped = _OPERATORS[operator]
            result[field] = value if mapped is None else {mapped: value}
        return result

    def _assignments(self, text: str, params: Dict[str, Any]) -> Dict[str, Any]:
        result = {}
        for item in self._split(text):
            match = re.fullmatch(rf"({_IDENTIFIER})\s*=\s*(.+)", item.strip())
            if not match:
                raise SQLError(f"Invalid assignment: {item}")
            result[match.group(1)] = self._value(match.group(2).strip(), params)
        return result

    @staticmethod
    def _split(text: str) -> List[str]:
        result, current, quote = [], [], None
        for char in text:
            if char in "'\"":
                quote = None if quote == char else (char if quote is None else quote)
            if char == "," and quote is None:
                result.append("".join(current).strip())
                current = []
            else:
                current.append(char)
        if current:
            result.append("".join(current).strip())
        return result

    @staticmethod
    def _value(raw: str, params: Dict[str, Any]) -> Any:
        if raw.startswith(":"):
            name = raw[1:]
            if not re.fullmatch(_IDENTIFIER, name) or name not in params:
                raise SQLError(f"Missing query parameter: {name}")
            return params[name]
        if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "'\"":
            return raw[1:-1]
        if raw.upper() == "NULL": return None
        if raw.upper() == "TRUE": return True
        if raw.upper() == "FALSE": return False
        try:
            return float(raw) if "." in raw else int(raw)
        except ValueError:
            raise SQLError("Values must be literals or named parameters such as :value")
