"""Basic IRODB usage."""
from irodb import IRODB


def main() -> None:
    db = IRODB("example.irodb")
    try:
        if "users" not in db.tables:
            db.create_table("users", {"name": str, "age": int, "email": str}, enable_hash_index=True)
        db.insert("users", {"name": "Alice", "age": 30, "email": "alice@example.com"})
        print("All users:", db.select("users"))
        print("Adults:", db.select("users", {"age": {"$gte": 18}}))
        db.update("users", {"name": "Alice"}, {"age": 31})
        print("Updated:", db.select("users", {"name": "Alice"}))
    finally:
        db.close()


if __name__ == "__main__":
    main()
