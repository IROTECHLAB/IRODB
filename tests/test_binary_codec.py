import struct
import unittest
from datetime import datetime

from irodb import binary_codec as codec


class TestBinaryCodec(unittest.TestCase):
    def test_round_trip_supported_values(self):
        value = {
            "none": None,
            "bool": True,
            "int": 42,
            "float": 3.5,
            "text": "hello",
            "bytes": b"data",
            "date": datetime(2024, 1, 2, 3, 4, 5),
            "types": [str, int, float, bool, bytes, dict, list, tuple],
            "nested": [1, {"x": (2, 3)}],
        }
        self.assertEqual(codec.loads(codec.dumps(value)), value)

    def test_unsupported_values_are_blocked_at_serialization(self):
        with self.assertRaises(TypeError):
            codec.dumps(object())
        with self.assertRaises(TypeError):
            codec.dumps({1: "not a string key"})
        with self.assertRaises(TypeError):
            codec.dumps({"schema": object})

    def test_malicious_type_marker_is_rejected(self):
        payload = b"IRB2" + struct.pack("<I", 2) + b"Y\xff"
        with self.assertRaises(ValueError):
            codec.loads(payload)

    def test_resource_limits_are_enforced(self):
        with self.assertRaises(ValueError):
            codec.dumps([0] * (codec.MAX_ITEMS + 1))
        oversized = b"IRB2" + struct.pack("<I", codec.MAX_PAYLOAD + 1)
        with self.assertRaises(ValueError):
            codec.loads(oversized)

    def test_irb2_is_compact_for_small_records(self):
        encoded = codec.dumps({"name": "Alice", "age": 30})
        self.assertEqual(encoded[:4], b"IRB2")
        self.assertLess(len(encoded), 64)

    def test_legacy_irb1_is_still_readable(self):
        body = b"M" + struct.pack("<Q", 1) + b"S" + struct.pack("<Q", 3) + b"key" + b"I" + struct.pack("<q", 7)
        payload = b"IRB1" + struct.pack("<Q", len(body)) + body
        self.assertEqual(codec.loads(payload), {"key": 7})


if __name__ == "__main__":
    unittest.main()
