# Migrating IRODB from 0.2.0 to 0.3.0

## Scope

This guide documents the upgrade from the published `irotechlab-irodb` **0.2.0** package to **0.3.0**. The 0.2.0 source and metadata were used as the baseline for the compatibility comparison. See the package history at [1].

## What changed in 0.3.0

IRODB 0.3.0 is a substantial storage and safety release. Version 0.2.0 stored database pages with Python pickle and performed direct page writes. Version 0.3.0 writes a strict custom binary format, adds optional authenticated encryption, adds a write-ahead log, introduces the injection-safe IRODB Query interface, improves indexing and validation behavior, and provides mobile-oriented batch operations.

| Area | 0.2.0 | 0.3.0 |
| --- | --- | --- |
| Page serialization | Python `pickle` | Compact IRB2 custom binary format |
| Legacy reading | Pickle pages only | Reads IRB1 and writes IRB2 |
| Deserialization safety | Pickle can execute unsafe objects if untrusted data is opened | Strict allowlisted type markers, size/count/depth limits, no object imports |
| Encryption | None | Optional AES-GCM authenticated page encryption |
| Preferred crypto backend | None | PyCryptodome; optional `cryptography` compatibility backend |
| Crash safety | Direct writes without WAL replay | CRC-checked WAL with fsync and startup replay |
| Query interface | SQL-like `SQLParser` | Injection-safe `IRODBQuery`; legacy SQL parser retained for compatibility |
| Integrity | Row hashes and indexes existed but used pickle/JSON internals | Custom-binary row/index persistence, authenticated encrypted pages, explicit corruption errors |
| Constraints | Constraint engine existed but normal CRUD did not consistently invoke it | Unique and validation constraints are enforced by normal insert/update paths |
| Full-text persistence | Integer-key postings could conflict with strict storage | Safe list-record postings preserve integer document IDs |
| Throughput | Per-row direct writes | `bulk_insert()` and `db.batch()` reduce WAL/fsync overhead |
| CLI | Database operations and legacy query flow | Version reporting, IRODB Query, re-keying, key environment variables, friendly errors |
| Python package version | 0.2.0 | 0.3.0 |

## Installation

Upgrade the package in a clean environment:

```bash
python -m pip install --upgrade irotechlab-irodb
```

The normal installation includes the no-Rust AES-GCM backend:

```text
pycryptodome>=3.20
```

The optional legacy backend can be installed when an environment already standardizes on the `cryptography` package:

```bash
python -m pip install 'irotechlab-irodb[legacy-crypto]'
```

Verify the installed release:

```bash
irodb --version
# irodb 0.3.0
```

## Database-file migration

Do not open an old pickle database with an untrusted or partially upgraded program. Make a byte-for-byte backup first:

```bash
cp old_database.irodb old_database.irodb.v0.2-backup
```

The 0.3.0 reader is intended to preserve compatibility with legacy IRB1 custom-binary pages, but the published 0.2.0 database implementation used pickle pages. For pickle-backed databases, use an application-level export/import migration rather than treating the old file as a directly readable 0.3.0 database.

A safe migration pattern is:

```python
from irodb import IRODB

old_db = open_legacy_database_with_your_0_2_application("old_database.irodb")
new_db = IRODB("new_database.irodb")

for table_name, table_info in old_db.tables.items():
    schema = table_info["schema"]
    new_db.create_table(table_name, schema, enable_hash_index=True)
    rows = old_db.select(table_name)
    clean_rows = [
        {key: value for key, value in row.items() if key not in {"id", "hash", "_metadata"}}
        for row in rows
    ]
    if clean_rows:
        new_db.bulk_insert(table_name, clean_rows)

new_db.close()
old_db.close()
```

The exact legacy-open call depends on the 0.2.0 application API and any local changes. Never use `pickle.loads()` on a database received from an untrusted party. If a legacy database cannot be exported safely, preserve the backup and inspect it in an isolated environment.

## Enabling encryption

Encryption is optional. New encrypted databases use AES-GCM and keep the key outside the database file:

```python
from irodb import IRODB

db = IRODB("private.irodb", encryption_key="use-a-long-secret-passphrase")
db.create_table("notes", {"body": str})
db.insert("notes", {"body": "private text"})
db.close()
```

The same key is required to reopen the database. A lost key cannot be recovered from the database file. For production, read the key from a secret manager or protected environment rather than committing it to source code.

## Query migration

The recommended 0.3.0 interface is the fixed-grammar, parameterized IRODB Query language:

```python
rows = db.query(
    "IRODB GET users WHERE age >= :minimum ORDER age DESC LIMIT 10",
    {"minimum": 18},
)
```

Do not build query text by concatenating user input. Pass values through the parameter mapping. The legacy `SQLParser` remains available for compatibility, but new code should use `IRODBQuery` or `db.query()`.

## Performance migration

Code that inserts many records should use `bulk_insert()` rather than calling `insert()` thousands of times:

```python
db.bulk_insert("events", event_rows)
```

When ordinary CRUD calls must be grouped into one durable commit boundary, use:

```python
with db.batch():
    for event in event_rows:
        db.insert("events", event)
```

A single operation outside a batch provides immediate durability for that operation. A batch provides one durable commit at successful exit, so an application must choose the boundary deliberately. Batching is particularly important on mobile filesystems where repeated fsync calls can be expensive.

## Constraint and index behavior

Declare a unique field through the validation API and normal inserts will reject duplicates:

```python
from irodb.feature_validation import DataValidator

DataValidator(db).add_table_constraints(
    "users", {"email": {"unique": True}}
)
```

Full-text indexes keep fast in-memory dictionaries but persist postings as safe list records so integer document IDs are supported by IRB2 without allowing non-string binary dictionary keys.

## Recovery and operational checklist

Before upgrading a production database, stop writers, copy the database and adjacent WAL file, and test the copy. Keep the encryption key separately. After migration, verify row counts, sample records, unique constraints, full-text searches, and `verify_hash_integrity()` results. Keep the 0.2.0 backup until the new database has passed application-level acceptance tests.