import tempfile
import unittest

from irodb import IRODB


class BatchWriteTests(unittest.TestCase):
    def test_batch_coalesces_and_reopens_encrypted_data(self):
        with tempfile.TemporaryDirectory() as directory:
            path = f"{directory}/batch.irodb"
            db = IRODB(path, encryption_key="batch-secret")
            db.create_table("events", {"value": int})
            with db.batch():
                for value in range(100):
                    db.insert("events", {"value": value})
            self.assertEqual(len(db.select("events")), 100)
            db.close()

            reopened = IRODB(path, encryption_key="batch-secret")
            self.assertEqual(len(reopened.select("events")), 100)
            reopened.close()

    def test_failed_batch_does_not_commit_staged_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            db = IRODB(f"{directory}/batch.irodb")
            db.create_table("events", {"value": int})
            with self.assertRaises(ValueError):
                with db.batch():
                    db.insert("events", {"value": 1})
                    db.insert("events", {"wrong": 2})
            self.assertEqual(db.select("events"), [])
            db.close()


if __name__ == "__main__":
    unittest.main()
