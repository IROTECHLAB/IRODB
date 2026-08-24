import os
import tempfile
import unittest
from pathlib import Path

from irodb import IRODB, SQLParser
from irodb import wal
from irodb.exceptions import SQLError, DatabaseError


class TestWALAndSQL(unittest.TestCase):
    def test_wal_replays_complete_page(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "wal.irodb"
            db = IRODB(str(path))
            db.create_table("items", {"name": str, "price": int})
            db.insert("items", {"name": "book", "price": 20})
            db.close()
            with open(path, "rb") as stream:
                stream.seek(1024 * 1024)
                page = stream.read(1024 * 1024)

            wal.append_record(str(path) + ".wal", 1, page)
            with open(path, "r+b") as stream:
                stream.seek(1024 * 1024)
                stream.write(b"damaged")
            reopened = IRODB(str(path), auto_create=False)
            self.assertIn("items", reopened.tables)
            self.assertEqual(len(reopened.select("items")), 1)
            reopened.close()
            self.assertFalse(os.path.exists(str(path) + ".wal"))

    def test_sql_comparisons_and_friendly_errors(self):
        with tempfile.TemporaryDirectory() as td:
            db = IRODB(str(Path(td) / "sql.irodb"))
            db.create_table("items", {"name": str, "price": int})
            db.insert("items", {"name": "book", "price": 20})
            db.insert("items", {"name": "laptop", "price": 1200})
            sql = SQLParser(db)
            rows = sql.execute("SELECT * FROM items WHERE price > 100 ORDER BY price DESC")
            self.assertEqual([row["name"] for row in rows], ["laptop"])
            with self.assertRaises(SQLError) as error:
                sql.execute("SELECT * FROM missing")
            self.assertIn("does not exist", str(error.exception))
            db.close()

    def test_encrypted_wrong_key_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "secure.irodb"
            db = IRODB(str(path), encryption_key="strong test key")
            db.create_table("secrets", {"value": str})
            db.insert("secrets", {"value": "hidden"})
            db.close()
            with self.assertRaises(DatabaseError):
                IRODB(str(path), auto_create=False, encryption_key="wrong key")


if __name__ == "__main__":
    unittest.main()
