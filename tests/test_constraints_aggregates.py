import tempfile
import unittest

from irodb import IRODB, SQLParser
from irodb.exceptions import ConstraintError
from irodb.feature_validation import DataValidator


class ConstraintAndAggregateTests(unittest.TestCase):
    def test_unique_constraint_is_enforced_by_normal_insert(self):
        with tempfile.TemporaryDirectory() as directory:
            db = IRODB(f"{directory}/constraints.irodb")
            db.create_table("users", {"name": str, "email": str})
            DataValidator(db).add_table_constraints(
                "users", {"email": {"unique": True}}
            )
            db.insert("users", {"name": "A", "email": "a@example.com"})
            with self.assertRaises(ConstraintError):
                db.insert("users", {"name": "B", "email": "a@example.com"})
            self.assertEqual(len(db.select("users")), 1)
            db.close()

    def test_grouped_avg_uses_each_group(self):
        with tempfile.TemporaryDirectory() as directory:
            db = IRODB(f"{directory}/aggregates.irodb")
            db.create_table("products", {"category": str, "price": float})
            db.bulk_insert("products", [
                {"category": "electronics", "price": 100.0},
                {"category": "electronics", "price": 300.0},
                {"category": "books", "price": 20.0},
                {"category": "books", "price": 40.0},
            ])
            result = SQLParser(db).execute(
                "SELECT category, AVG(price) as avg_price FROM products GROUP BY category"
            )
            averages = {row["category"]: row["AVG(price) as avg_price"] for row in result}
            self.assertEqual(averages, {"electronics": 200.0, "books": 30.0})
            db.close()


if __name__ == "__main__":
    unittest.main()
