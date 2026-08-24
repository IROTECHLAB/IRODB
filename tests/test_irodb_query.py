import tempfile
import unittest
from pathlib import Path

from irodb import IRODB, IRODBQuery
from irodb.exceptions import SQLError


class TestIRODBQuery(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = IRODB(str(Path(self.tmp.name) / "query.irodb"))
        self.query = IRODBQuery(self.db)
        self.query.execute("IRODB CREATE users SCHEMA name:text, age:int")

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def test_create_insert_get_update_delete(self):
        self.query.execute("IRODB INSERT users VALUES name=:name, age=:age", {"name": "Alice", "age": 30})
        rows = self.query.execute("IRODB GET users WHERE age >= :minimum ORDER age DESC LIMIT 5", {"minimum": 18})
        self.assertEqual(rows[0]["name"], "Alice")
        self.assertEqual(self.query.execute("IRODB UPDATE users SET age=:age WHERE name=:name", {"age": 31, "name": "Alice"}), 1)
        self.assertEqual(self.query.execute("IRODB DELETE users WHERE name=:name", {"name": "Alice"}), 1)
        self.assertEqual(self.query.execute("IRODB GET users"), [])

    def test_special_values_are_data_not_code(self):
        payload = "Alice' OR 1=1 --"
        self.query.execute("IRODB INSERT users VALUES name=:name, age=:age", {"name": payload, "age": 20})
        rows = self.query.execute("IRODB GET users WHERE name=:name", {"name": payload})
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name"], payload)

    def test_sql_injection_shaped_text_is_rejected(self):
        with self.assertRaises(SQLError):
            self.query.execute("IRODB GET users WHERE name = 'Alice' OR 1=1")
        with self.assertRaises(SQLError):
            self.query.execute("IRODB INSERT users VALUES name=:missing, age=20")
        with self.assertRaises(SQLError):
            self.query.execute("GET users")


if __name__ == "__main__":
    unittest.main()
