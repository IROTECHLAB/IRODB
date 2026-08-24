"""Controlled compact binary serialization for IRODB pages.

IRB2 uses varint lengths/counts and a bytearray encoder to reduce framing and
allocation overhead. The decoder accepts only a closed set of primitive types,
never imports classes, never evaluates input, and enforces resource limits.
IRB1 remains readable for existing databases and is rewritten as IRB2 on save.
"""
from __future__ import annotations

import math
import struct
from datetime import datetime
from typing import Any

MAGIC = b"IRB2"
LEGACY_MAGIC = b"IRB1"
MAX_PAYLOAD = 8 * 1024 * 1024
MAX_BLOB = 4 * 1024 * 1024
MAX_NESTING = 128
MAX_ITEMS = 1_000_000

_ALLOWED_TYPES = (str, int, float, bool, bytes, dict, list, tuple)
_TYPE_TO_CODE = {str: 1, int: 2, float: 3, bool: 4, bytes: 5, dict: 6, list: 7, tuple: 8}
_CODE_TO_TYPE = {code: value for value, code in _TYPE_TO_CODE.items()}


def _put_varint(buffer: bytearray, value: int) -> None:
    if value < 0:
        raise ValueError("negative binary length")
    while value >= 0x80:
        buffer.append((value & 0x7F) | 0x80)
        value >>= 7
    buffer.append(value)


def _get_varint(data, offset: int, end: int):
    value = 0
    shift = 0
    while offset < end and shift <= 63:
        byte = data[offset]
        offset += 1
        value |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return value, offset
        shift += 7
    raise ValueError("invalid or oversized binary varint")


class _Encoder:
    def __init__(self):
        self.buffer = bytearray()
        self.items = 0

    def encode(self, value: Any, depth: int = 0) -> None:
        if depth > MAX_NESTING:
            raise ValueError("IRODB binary nesting depth exceeds the safety limit")
        self.items += 1
        if self.items > MAX_ITEMS:
            raise ValueError("IRODB binary item count exceeds the safety limit")
        if value is None:
            self.buffer.extend(b"N")
        elif value is False:
            self.buffer.extend(b"F")
        elif value is True:
            self.buffer.extend(b"T")
        elif isinstance(value, int) and not isinstance(value, bool):
            try:
                self.buffer.extend(b"I" + struct.pack("<q", value))
            except struct.error as exc:
                raise ValueError("IRODB integers must fit in signed 64 bits") from exc
        elif isinstance(value, float):
            if not math.isfinite(value):
                raise ValueError("IRODB binary floats must be finite")
            self.buffer.extend(b"D" + struct.pack("<d", value))
        elif isinstance(value, str):
            self._blob(b"S", value.encode("utf-8"))
        elif isinstance(value, bytes):
            self._blob(b"B", value)
        elif isinstance(value, datetime):
            self._blob(b"Z", value.isoformat().encode("utf-8"))
        elif isinstance(value, type):
            code = _TYPE_TO_CODE.get(value)
            if code is None:
                raise TypeError(f"unsupported IRODB schema type: {value!r}")
            self.buffer.extend(b"Y")
            self.buffer.append(code)
        elif isinstance(value, list):
            self._sequence(b"L", value, depth)
        elif isinstance(value, tuple):
            self._sequence(b"U", value, depth)
        elif isinstance(value, dict):
            if len(value) > MAX_ITEMS:
                raise ValueError("IRODB binary mapping is too large")
            if not all(isinstance(key, str) for key in value):
                raise TypeError("IRODB binary dictionaries require string keys")
            self.buffer.extend(b"M")
            _put_varint(self.buffer, len(value))
            for key in sorted(value):
                self.encode(key, depth + 1)
                self.encode(value[key], depth + 1)
        else:
            raise TypeError(f"unsupported IRODB value type: {type(value).__name__}")
        if len(self.buffer) > MAX_PAYLOAD:
            raise ValueError("IRODB binary payload exceeds the safety limit")

    def _blob(self, tag: bytes, value: bytes) -> None:
        if len(value) > MAX_BLOB:
            raise ValueError("IRODB binary blob exceeds the safety limit")
        self.buffer.extend(tag)
        _put_varint(self.buffer, len(value))
        self.buffer.extend(value)

    def _sequence(self, tag: bytes, values, depth: int) -> None:
        if len(values) > MAX_ITEMS:
            raise ValueError("IRODB binary sequence is too large")
        self.buffer.extend(tag)
        _put_varint(self.buffer, len(values))
        for item in values:
            self.encode(item, depth + 1)


def dumps(value: Any) -> bytes:
    encoder = _Encoder()
    encoder.encode(value)
    body = bytes(encoder.buffer)
    return MAGIC + struct.pack("<I", len(body)) + body


def loads(data: bytes) -> Any:
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise TypeError("binary data required")
    raw = memoryview(data)
    if len(raw) < 8:
        raise ValueError("invalid IRODB binary payload")
    if raw[:4].tobytes() == LEGACY_MAGIC:
        return _loads_legacy(raw)
    if raw[:4].tobytes() != MAGIC:
        raise ValueError("invalid IRODB binary payload")
    size = struct.unpack_from("<I", raw, 4)[0]
    if size > MAX_PAYLOAD:
        raise ValueError("IRODB binary payload exceeds the safety limit")
    body_start = 8
    body_end = body_start + size
    if body_end > len(raw) or (body_end < len(raw) and any(raw[body_end:])):
        raise ValueError("truncated or unexpected IRODB binary payload")
    value, offset = _decode(raw, body_start, body_end)
    if offset != body_end:
        raise ValueError("invalid IRODB binary payload")
    return value


def _read_blob(data, offset: int, end: int):
    size, offset = _get_varint(data, offset, end)
    if size > MAX_BLOB or offset + size > end:
        raise ValueError("truncated or oversized binary value")
    next_offset = offset + size
    return data[offset:next_offset].tobytes(), next_offset


def _decode(data, offset: int, end: int, depth: int = 0):
    if depth > MAX_NESTING:
        raise ValueError("IRODB binary nesting depth exceeds the safety limit")
    if offset >= end:
        raise ValueError("truncated binary value")
    tag = data[offset]
    offset += 1
    if tag == ord("N"):
        return None, offset
    if tag == ord("F"):
        return False, offset
    if tag == ord("T"):
        return True, offset
    if tag == ord("I"):
        if offset + 8 > end:
            raise ValueError("truncated integer")
        return struct.unpack_from("<q", data, offset)[0], offset + 8
    if tag == ord("D"):
        if offset + 8 > end:
            raise ValueError("truncated float")
        value = struct.unpack_from("<d", data, offset)[0]
        if not math.isfinite(value):
            raise ValueError("non-finite binary float is not allowed")
        return value, offset + 8
    if tag in (ord("S"), ord("B"), ord("Z")):
        blob, offset = _read_blob(data, offset, end)
        if tag == ord("S"):
            return blob.decode("utf-8"), offset
        if tag == ord("B"):
            return blob, offset
        return datetime.fromisoformat(blob.decode("utf-8")), offset
    if tag == ord("Y"):
        if offset >= end:
            raise ValueError("truncated type marker")
        code = data[offset]
        if code not in _CODE_TO_TYPE:
            raise ValueError("unsupported or malicious schema type marker")
        return _CODE_TO_TYPE[code], offset + 1
    if tag in (ord("L"), ord("U")):
        count, offset = _get_varint(data, offset, end)
        if count > MAX_ITEMS:
            raise ValueError("IRODB binary sequence is too large")
        values = []
        for _ in range(count):
            item, offset = _decode(data, offset, end, depth + 1)
            values.append(item)
        return (values if tag == ord("L") else tuple(values)), offset
    if tag == ord("M"):
        count, offset = _get_varint(data, offset, end)
        if count > MAX_ITEMS:
            raise ValueError("IRODB binary mapping is too large")
        result = {}
        for _ in range(count):
            key, offset = _decode(data, offset, end, depth + 1)
            value, offset = _decode(data, offset, end, depth + 1)
            if not isinstance(key, str):
                raise ValueError("non-string binary mapping key")
            result[key] = value
        return result, offset
    raise ValueError(f"unknown IRODB binary tag: {bytes([tag])!r}")


def _loads_legacy(raw) -> Any:
    if len(raw) < 12:
        raise ValueError("invalid legacy IRODB binary payload")
    size = struct.unpack_from("<Q", raw, 4)[0]
    if size > MAX_PAYLOAD or size > len(raw) - 12:
        raise ValueError("invalid legacy IRODB binary length")
    body_start = 12
    body_end = body_start + size
    if body_end < len(raw) and any(raw[body_end:]):
        raise ValueError("unexpected legacy binary data")
    value, offset = _decode_legacy(raw, body_start, body_end)
    if offset != body_end:
        raise ValueError("invalid legacy IRODB binary payload")
    return value


def _legacy_blob(data, offset: int, end: int):
    if offset + 8 > end:
        raise ValueError("truncated legacy binary value")
    size = struct.unpack_from("<Q", data, offset)[0]
    offset += 8
    if size > MAX_BLOB or offset + size > end:
        raise ValueError("oversized legacy binary value")
    return data[offset:offset + size].tobytes(), offset + size


def _decode_legacy(data, offset: int, end: int, depth: int = 0):
    if depth > MAX_NESTING or offset >= end:
        raise ValueError("invalid legacy binary nesting or truncation")
    tag = data[offset].to_bytes(1, "little")
    offset += 1
    if tag == b"N": return None, offset
    if tag == b"F": return False, offset
    if tag == b"T": return True, offset
    if tag == b"I":
        if offset + 8 > end: raise ValueError("truncated legacy integer")
        return struct.unpack_from("<q", data, offset)[0], offset + 8
    if tag == b"D":
        if offset + 8 > end: raise ValueError("truncated legacy float")
        value = struct.unpack_from("<d", data, offset)[0]
        if not math.isfinite(value): raise ValueError("non-finite legacy float")
        return value, offset + 8
    if tag in (b"S", b"B", b"Z", b"Y"):
        blob, offset = _legacy_blob(data, offset, end)
        if tag == b"S": return blob.decode("utf-8"), offset
        if tag == b"B": return blob, offset
        if tag == b"Z": return datetime.fromisoformat(blob.decode()), offset
        module, name = blob.split(b"\0", 1)
        if module != b"builtins": raise ValueError("unsupported legacy schema type marker")
        allowed = {b"str": str, b"int": int, b"float": float, b"bool": bool, b"bytes": bytes, b"dict": dict, b"list": list}
        if name not in allowed: raise ValueError("unsupported legacy schema type marker")
        return allowed[name], offset
    if tag in (b"L", b"U"):
        if offset + 8 > end: raise ValueError("truncated legacy sequence")
        count = struct.unpack_from("<Q", data, offset)[0]
        offset += 8
        if count > MAX_ITEMS: raise ValueError("legacy sequence is too large")
        values = []
        for _ in range(count):
            item, offset = _decode_legacy(data, offset, end, depth + 1)
            values.append(item)
        return (values if tag == b"L" else tuple(values)), offset
    if tag == b"M":
        if offset + 8 > end: raise ValueError("truncated legacy mapping")
        count = struct.unpack_from("<Q", data, offset)[0]
        offset += 8
        if count > MAX_ITEMS: raise ValueError("legacy mapping is too large")
        result = {}
        for _ in range(count):
            key, offset = _decode_legacy(data, offset, end, depth + 1)
            value, offset = _decode_legacy(data, offset, end, depth + 1)
            if not isinstance(key, str): raise ValueError("non-string legacy mapping key")
            result[key] = value
        return result, offset
    raise ValueError(f"unknown legacy IRODB binary tag: {tag!r}")
