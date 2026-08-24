"""SQL-like IRODB queries."""
from irodb import IRODB, SQLParser


def main() -> None:
    db = IRODB("sql-example.irodb")
    sql = SQLParser(db)
    try:
        if "products" not in db.tables:
            sql.execute("CREATE TABLE products (name TEXT, price FLOAT, category TEXT)")
            sql.execute("INSERT INTO products (name, price, category) VALUES ('Laptop', 1200, 'electronics')")
            sql.execute("INSERT INTO products (name, price, category) VALUES ('Book', 25, 'education')")
        print(sql.execute("SELECT * FROM products WHERE price > 100 ORDER BY price DESC"))
        print(sql.execute("SELECT category, COUNT(*) FROM products GROUP BY category"))
        sql.execute("UPDATE products SET price = 1100 WHERE name = 'Laptop'")
        sql.execute("DELETE FROM products WHERE price < 30")
    finally:
        db.close()


if __name__ == "__main__":
    main()
