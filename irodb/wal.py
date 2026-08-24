"""Pure-Python write-ahead logging for fixed-size IRODB pages."""
from __future__ import annotations

import os
import struct
import zlib

from .exceptions import DatabaseError

MAGIC = b"WAL1"
HEADER = struct.Struct("<4sQQI")


def wal_path(db_path: str) -> str:
    return db_path + ".wal"


def append_records(path: str, records) -> None:
    """Append and durably synchronize several page records in one syscall group."""
    with open(path, "ab") as stream:
        for page_number, page_data in records:
            checksum = zlib.crc32(page_data) & 0xFFFFFFFF
            stream.write(HEADER.pack(MAGIC, page_number, len(page_data), checksum))
            stream.write(page_data)
        stream.flush()
        os.fsync(stream.fileno())


def append_record(path: str, page_number: int, page_data: bytes) -> None:
    append_records(path, [(page_number, page_data)])


def recover(db_path: str, page_size: int) -> int:
    """Replay complete WAL records and remove the log.

    Returns the number of replayed pages. Incomplete final records are discarded;
    complete records with invalid CRCs raise DatabaseError.
    """
    path = wal_path(db_path)
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return 0
    with open(path, "rb") as stream:
        raw = stream.read()
    offset = 0
    records = []
    while offset + HEADER.size <= len(raw):
        magic, page_number, size, checksum = HEADER.unpack_from(raw, offset)
        if magic != MAGIC or size != page_size:
            raise DatabaseError("WAL is corrupt; database recovery was stopped safely")
        data_start = offset + HEADER.size
        data_end = data_start + size
        if data_end > len(raw):
            break
        page_data = raw[data_start:data_end]
        if zlib.crc32(page_data) & 0xFFFFFFFF != checksum:
            raise DatabaseError("WAL checksum failed; database recovery was stopped safely")
        records.append((page_number, page_data))
        offset = data_end
    with open(db_path, "r+b") as database:
        for page_number, page_data in records:
            database.seek(page_number * page_size)
            database.write(page_data)
        database.flush()
        os.fsync(database.fileno())
    os.remove(path)
    return len(records)


def clear(path: str) -> None:
    try:
        os.remove(path)
    except FileNotFoundError:
        pass
