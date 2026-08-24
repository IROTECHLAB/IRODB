import os
import struct
import tempfile
import unittest
from pathlib import Path

from irodb import IRODB, IRODBQuery, binary_codec, wal
from irodb.constants import PAGE_SIZE
from irodb.exceptions import CorruptedError, DatabaseError, PageError, SQLError


class TestSecurityHardening(unittest.TestCase):
    def test_binary_decoder_rejects_malformed_payloads(self):
        malformed = [
            b"bad",
            b"IRB1" + struct.pack("<Q", 10) + b"N",
            b"IRB1" + struct.pack("<Q", 1) + b"?",
            b"IRB1" + struct.pack("<Q", 9) + b"S" + struct.pack("<Q", 999),
        ]
        for payload in malformed:
            with self.assertRaises((ValueError, UnicodeError)):
                binary_codec.loads(payload)
        with self.assertRaises(TypeError):
            binary_codec.dumps({1: "not allowed"})

    def test_plaintext_table_tampering_is_reported(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "tampered.irodb"
            db = IRODB(str(path))
            db.create_table("items", {"value": str})
            db.insert("items", {"value": "original"})
            db.close()
            with open(path, "r+b") as stream:
                stream.seek(PAGE_SIZE * 2)
                stream.write(b"tampered page")
            reopened = IRODB(str(path), auto_create=False)
            with self.assertRaises(CorruptedError):
                reopened.select("items")
            reopened.close()

    def test_encrypted_page_tampering_is_authenticated(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "encrypted.irodb"
            key = "security-test-passphrase"
            db = IRODB(str(path), encryption_key=key)
            db.create_table("items", {"value": str})
            db.insert("items", {"value": "original"})
            db.close()
            with open(path, "r+b") as stream:
                stream.seek(PAGE_SIZE * 2 + 64)
                byte = stream.read(1)
                stream.seek(PAGE_SIZE * 2 + 64)
                stream.write(bytes([byte[0] ^ 0xFF]))
            reopened = IRODB(str(path), auto_create=False, encryption_key=key)
            with self.assertRaises(CorruptedError):
                reopened.select("items")
            reopened.close()

    def test_wal_checksum_and_incomplete_tail(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "wal.irodb"
            db = IRODB(str(path))
            db.close()
            page = b"\x00" * PAGE_SIZE
            wal_path = str(path) + ".wal"
            wal.append_record(wal_path, 1, page)
            with open(wal_path, "r+b") as stream:
                stream.seek(0)
                stream.write(b"BAD!")
            with self.assertRaises(DatabaseError):
                IRODB(str(path), auto_create=False)

            os.remove(wal_path)
            with open(wal_path, "wb") as stream:
                stream.write(wal.HEADER.pack(wal.MAGIC, 1, PAGE_SIZE, 0)[:10])
            self.assertEqual(wal.recover(str(path), PAGE_SIZE), 0)
            self.assertFalse(os.path.exists(wal_path))

    def test_query_injection_payload_is_data_and_fragments_are_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            db = IRODB(str(Path(td) / "query.irodb"))
            query = IRODBQuery(db)
            query.execute("IRODB CREATE users SCHEMA name:text")
            payload = "x' OR 1=1 --"
            query.execute("IRODB INSERT users VALUES name=:name", {"name": payload})
            self.assertEqual(query.execute("IRODB GET users WHERE name=:name", {"name": payload})[0]["name"], payload)
            with self.assertRaises(SQLError):
                query.execute("IRODB GET users WHERE name='x' OR 1=1")
            db.close()


if __name__ == "__main__":
    unittest.main()
