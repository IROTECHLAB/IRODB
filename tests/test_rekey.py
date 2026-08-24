import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from irodb import IRODB
from irodb.exceptions import DatabaseError, CorruptedError


class TestRekey(unittest.TestCase):
    def test_rekey_preserves_data_and_changes_key(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "private.irodb"
            old_key = "old-passphrase-for-tests"
            new_key = "new-passphrase-for-tests"
            db = IRODB(str(path), encryption_key=old_key)
            db.create_table("notes", {"title": str, "body": str})
            db.bulk_insert("notes", [{"title": f"n-{i}", "body": "secret"} for i in range(20)])
            progress = []
            db.rekey(new_key, progress_callback=lambda current, total: progress.append((current, total)))
            self.assertTrue(progress)
            self.assertEqual(progress[-1][0], progress[-1][1])
            self.assertEqual(len(db.select("notes")), 20)
            db.close()

            with self.assertRaises(DatabaseError):
                IRODB(str(path), auto_create=False, encryption_key=old_key)
            reopened = IRODB(str(path), auto_create=False, encryption_key=new_key)
            self.assertEqual(len(reopened.select("notes")), 20)
            reopened.close()

    def test_rekey_failure_does_not_replace_original(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "private.irodb"
            key = "old-passphrase-for-tests"
            db = IRODB(str(path), encryption_key=key)
            db.create_table("notes", {"body": str})
            db.insert("notes", {"body": "keep"})
            db.close()
            with open(path, "r+b") as stream:
                stream.seek(2 * 1024 * 1024 + 64)
                byte = stream.read(1)
                stream.seek(2 * 1024 * 1024 + 64)
                stream.write(bytes([byte[0] ^ 0xFF]))
            damaged = IRODB(str(path), auto_create=False, encryption_key=key)
            with self.assertRaises(Exception):
                damaged.rekey("new-passphrase-for-tests")
            damaged.close()
            self.assertFalse(list(Path(td).glob(".irodb-rekey-*.tmp")))

    def test_unencrypted_database_cannot_be_rekeyed(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "plain.irodb"
            db = IRODB(str(path))
            with self.assertRaises(DatabaseError):
                db.rekey("new-passphrase-for-tests")
            db.close()

    def test_cli_rekey_uses_environment_keys(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "cli.irodb"
            db = IRODB(str(path), encryption_key="old-passphrase-for-tests")
            db.create_table("notes", {"body": str})
            db.insert("notes", {"body": "cli secret"})
            db.close()
            env = os.environ.copy()
            env["IRODB_KEY"] = "old-passphrase-for-tests"
            env["IRODB_NEW_KEY"] = "new-passphrase-for-tests"
            result = subprocess.run([sys.executable, "-m", "irodb.cli", str(path), "--rekey"], cwd=Path(__file__).parent.parent, env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            reopened = IRODB(str(path), auto_create=False, encryption_key="new-passphrase-for-tests")
            self.assertEqual(reopened.select("notes")[0]["body"], "cli secret")
            reopened.close()


if __name__ == "__main__":
    unittest.main()
