#!/usr/bin/env python3
"""
Basic usage examples for IRODB
"""

from irodb import IRODB

def main():
    # Create database
    db = IRODB("example.irodb")
    
    # Create table
    db.create_table("products", {
        "name": str,
        "price": float,
        "category": str
    }, enable_hash_index=True)
    
    # Insert products
    products = [
        {"name": "Laptop", "price": 999.99, "category": "Electronics"},
        {"name": "Phone", "price": 599.99, "category": "Electronics"},
        {"name": "Book", "price": 29.99, "category": "Books"}
    ]
    
    for product in products:
        _, hash_val = db.insert("products", product, return_hash=True)
        print(f"Inserted: {product['name']} - Hash: {hash_val[:8]}...")
    
    # Query products
    electronics = db.select("products", {"category": "Electronics"})
    print(f"\nElectronics: {len(electronics)} found")
    
    # Update product
    db.update("products", {"name": "Laptop"}, {"price": 899.99})
    
    # Verify integrity
    integrity = db.verify_hash_integrity("products")
    print(f"\nIntegrity: {integrity['valid_hashes']}/{integrity['total_rows']} valid")
    
    db.close()

if __name__ == "__main__":
    main()