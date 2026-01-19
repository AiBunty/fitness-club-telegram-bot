#!/usr/bin/env python3
"""
Migration: Recreate store_products table with proper schema
"""

from src.database.connection import execute_query

def migrate():
    try:
        # Drop old table if it exists
        print("Dropping old store_products table...")
        execute_query("DROP TABLE IF EXISTS store_products CASCADE;")
        print("[OK] Old table dropped")
        
        # Recreate with correct schema
        print("Creating store_products table...")
        execute_query("""
        CREATE TABLE store_products (
            product_id SERIAL PRIMARY KEY,
            product_code VARCHAR(50) UNIQUE NOT NULL,
            category VARCHAR(100) NOT NULL,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            price DECIMAL(10, 2) NOT NULL,
            discount_percent DECIMAL(5, 2) DEFAULT 0,
            stock INT DEFAULT 0,
            status VARCHAR(50) DEFAULT 'ACTIVE',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        print("[OK] store_products table created with all columns")
        
        # Create indexes
        print("Creating indexes...")
        execute_query("CREATE INDEX idx_store_products_category ON store_products(category);")
        execute_query("CREATE INDEX idx_store_products_status ON store_products(status);")
        print("[OK] Indexes created")
        
        print("\n[SUCCESS] Store products table recreated successfully!")
        return True
        
    except Exception as e:
        print(f"[ERROR] {e}")
        return False

if __name__ == "__main__":
    migrate()
