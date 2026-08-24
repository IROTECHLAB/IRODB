import tempfile
import unittest
from pathlib import Path

from irodb import IRODB


class TestBulkInsert(unittest.TestCase):
    def test_bulk_insert_is_durable_and_indexed(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "bulk.irodb"
            db = IRODB(str(path))
            db.create_table("events", {"name": str, "value": int}, enable_hash_index=True)
            ids = db.bulk_insert("events", [{"name": f"event-{i}", "value": i} for i in range(100)])
            self.assertEqual(ids, list(range(1, 101)))
            self.assertEqual(len(db.select("events")), 100)
            db.close()

            reopened = IRODB(str(path), auto_create=False)
            self.assertEqual(len(reopened.select("events")), 100)
            reopened.close()

    def test_bulk_insert_validates_before_writing(self):
        with tempfile.TemporaryDirectory() as td:
            db = IRODB(str(Path(td) / "bulk.irodb"))
            db.create_table("items", {"name": str, "value": int})
            with self.assertRaises(TypeError):
                db.bulk_insert("items", [{"name": "ok", "value": 1}, {"name": "bad", "value": "wrong"}])
            self.assertEqual(db.select("items"), [])
            db.close()


if __name__ == "__main__":
    unittest.main()
