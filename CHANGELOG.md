# Changelog

All notable changes to IRODB are documented here. This project follows a practical semantic-versioning style: storage-format changes, security changes, and public API changes are called out explicitly.

## [0.3.0] — 2026-08-25

### Highlights

IRODB 0.3.0 replaces unsafe pickle-backed persistence with the IRB2 custom binary format, adds optional AES-GCM encryption, introduces WAL-based crash recovery, and improves CRUD performance for mobile and low-RAM environments. It also adds the injection-safe IRODB Query language and a version-reporting CLI command.

### Added

- Added the **IRB2 custom binary codec** with compact varint lengths and counts.
- Added strict type allowlisting at the parsing boundary. Supported values are decoded into ordinary Python values without importing or instantiating arbitrary classes.
- Added limits for encoded size, collection counts, nesting depth, and malformed/truncated payloads.
- Added IRB1 compatibility reading where applicable, with IRB2 used for new and rewritten data.
- Added optional page-level **AES-GCM authenticated encryption**.
- Added PyCryptodome as the preferred AES-GCM backend because it does not require Rust during installation.
- Added an optional `cryptography` backend for environments that already use that package.
- Added authenticated-data binding for page number and database format version.
- Added a write-ahead log with checksums, durable append behavior, recovery replay, and stale-record cleanup.
- Added `bulk_insert()` for efficient insertion of many rows.
- Added the `batch()` context manager for grouping related writes into one commit boundary.
- Added the parameterized **IRODB Query** interface, including `GET`, predicates, ordering, limits, and named parameters such as `:minimum`.
- Added `irodb --version` and package version reporting for `0.3.0`.
- Added the CLI re-key operation for changing the passphrase of an existing encrypted database.
- Added examples for encryption, re-keying, WAL recovery, binary storage, IRODB Query, bulk operations, and mobile-oriented workloads.
- Added expanded tests for malformed binary payloads, encryption failures, tampering, WAL recovery, constraints, query parameters, CLI behavior, and performance-sensitive CRUD paths.

### Changed

- Changed persistent table, metadata, index, and hash-index serialization from Python pickle to IRB2.
- Changed database reads and writes to use explicit codec errors instead of silently accepting arbitrary serialized objects.
- Changed the normal encryption dependency to PyCryptodome, avoiding the Rust build requirement that can affect older Python and Android/Termux environments.
- Changed update and delete to mutate the table and hash index in one pass, avoiding repeated index page rewrites and synchronization calls.
- Changed bulk and batch writes to reduce repeated page serialization, WAL records, and filesystem synchronization overhead.
- Changed full-text postings to a binary-safe list representation so integer document identifiers are valid under the strict codec.
- Changed query recommendations from SQL-like strings to the simpler IRODB Query grammar. The older SQL feature remains available for compatibility.
- Changed operational errors to use clearer, user-facing database, codec, encryption, and WAL messages.
- Changed package metadata to require Python `>=3.7` and report version `0.3.0`.

### Security

- Removed pickle from the database persistence path. Pickle remains unsuitable for opening untrusted database content because deserialization can execute attacker-controlled behavior.
- Removed JSON from the internal persistence path. JSON export/import remains an explicit interoperability feature rather than the database storage format.
- Added authenticated encryption so modified ciphertext or authentication data fails verification instead of being accepted as valid plaintext.
- Added strict binary decoding rules to reject unknown type markers, invalid lengths, excessive nesting, oversized collections, and trailing or truncated data according to codec policy.
- Added encryption-key separation from the database file. A lost encryption key cannot be reconstructed from the database.
- Added re-keying through page-by-page authenticated decryption and re-encryption, with temporary output and replacement safeguards intended to reduce data-loss risk.
- Added parameter binding in IRODB Query so user values are parsed as values rather than interpreted as query syntax.

### Fixed

- Fixed unique-constraint enforcement so duplicate values are rejected on normal insert paths and are not bypassed by optimized writes.
- Fixed grouped `AVG()` aggregation so each group receives its own aggregate rather than the aggregate of the entire result set.
- Fixed full-text index creation for postings whose dictionary keys are integer identifiers.
- Fixed hash-index maintenance during multi-row updates and deletes.
- Fixed metadata and page handling around WAL-backed commits and recovery.
- Fixed CLI version invocation so `irodb --version` does not require a database path.

### Performance

The principal mobile optimization was eliminating one index-page rewrite and durability synchronization per changed row. In the validated 1,000-row workload, the optimized paths reduced update and delete time from approximately 6.088 seconds and 55.716 seconds, respectively, to approximately 0.016 seconds and 0.012 seconds in the development benchmark environment. Actual mobile performance depends on storage hardware, encryption, filesystem behavior, and Python runtime.

| Workload | Previous observed result | 0.3.0 optimized result |
| --- | ---: | ---: |
| Insert 1,000 rows | 1.747 s | approximately 0.050 s with bulk path |
| Update 100 rows | 6.088 s | approximately 0.016 s |
| Delete 1,000 rows | 55.716 s | approximately 0.012 s |
| Select 1,000 rows | 0.140 s | read path retained |

These figures are benchmark observations, not performance guarantees.

### Compatibility and migration

Version 0.3.0 should be treated as a storage migration release when upgrading from the published 0.2.0 line. Create a backup before opening or converting any existing database. Pickle-backed 0.2.0 files should be exported through the old application and imported into a newly created 0.3.0 database; do not manually call `pickle.loads()` on untrusted files. See [`MIGRATION_0.2.0_TO_0.3.0.md`](MIGRATION_0.2.0_TO_0.3.0.md).

The public PyPI index exposes `0.1.0`, `0.2.0`, and `0.3.0`. This changelog uses the published `0.2.0` package as the direct baseline for this migration.

### Documentation

- Reworked the README for public users, including installation, examples, encryption, queries, recovery, and mobile guidance.
- Added architecture, audit, production-readiness, performance, codec, and cryptography backend reports.
- Added project branding assets, including the IRODB banner and mark.

## [0.2.0] — previous line

The 0.2.0 release used page-based storage and exposed table, index, validation, full-text, transaction, utility, and SQL-like features. Its published implementation serialized database pages with Python pickle and used JSON in hash-related and interoperability paths. It did not provide the IRB2 codec, AES-GCM page encryption, WAL replay, the IRODB Query grammar, or the optimized one-pass update/delete paths introduced in 0.3.0.
