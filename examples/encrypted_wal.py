"""Encrypted IRODB database with WAL-backed page commits."""
from irodb import IRODB


KEY = "replace-this-with-a-long-secret-passphrase"


def main() -> None:
    db = IRODB("secure.irodb", encryption_key=KEY)
    try:
        if "notes" not in db.tables:
            db.create_table("notes", {"title": str, "body": str})
        db.insert("notes", {"title": "Recovery", "body": "Pages are authenticated and WAL-backed."})
        print(db.select("notes"))
    finally:
        db.close()

    reopened = IRODB("secure.irodb", auto_create=False, encryption_key=KEY)
    try:
        print("Recovered rows:", reopened.select("notes"))
    finally:
        reopened.close()


if __name__ == "__main__":
    main()
