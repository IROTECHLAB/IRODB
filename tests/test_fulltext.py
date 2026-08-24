import tempfile
import unittest

from irodb import IRODB
from irodb.feature_fulltext import FullTextSearch


class FullTextBinaryPersistenceTests(unittest.TestCase):
    def test_integer_document_ids_use_safe_posting_lists(self):
        with tempfile.TemporaryDirectory() as directory:
            path = f"{directory}/fulltext.irodb"
            db = IRODB(path)
            db.create_table("products", {"name": str, "description": str})
            db.insert("products", {"name": "Phone", "description": "Fast mobile device"})
            db.insert("products", {"name": "Case", "description": "Protective mobile accessory"})

            fulltext = FullTextSearch(db)
            index_name = fulltext.create_fulltext_index(
                "products", ["name", "description"], "products_ft"
            )

            self.assertEqual(index_name, "products_ft")
            self.assertEqual(len(fulltext.search("products", "mobile")), 2)
            self.assertTrue(all(isinstance(key, str) for key in fulltext.indexes[index_name]["inverted_index"]))
            self.assertTrue(
                all(
                    isinstance(pair, list) and isinstance(pair[0], int)
                    for postings in fulltext.indexes[index_name]["inverted_index"].values()
                    for pair in [[doc_id, score] for doc_id, score in postings.items()]
                )
            )
            db.close()


if __name__ == "__main__":
    unittest.main()
