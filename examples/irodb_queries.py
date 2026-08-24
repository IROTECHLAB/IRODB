"""The injection-safe IRODB Query language."""
from irodb import IRODB


def main() -> None:
    db = IRODB("irodb-query-example.irodb")
    try:
        if "users" not in db.tables:
            db.query("IRODB CREATE users SCHEMA name:text, age:int")
        db.query(
            "IRODB INSERT users VALUES name=:name, age=:age",
            {"name": "Alice' OR 1=1 --", "age": 30},
        )
        rows = db.query(
            "IRODB GET users WHERE age >= :minimum ORDER age DESC LIMIT 10",
            {"minimum": 18},
        )
        print(rows)
    finally:
        db.close()


if __name__ == "__main__":
    main()
