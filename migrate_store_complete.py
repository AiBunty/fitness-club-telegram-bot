#!/usr/bin/env python3
"""
Migration: Add complete store_products table and related tables
Adds all necessary columns for e-commerce store system
"""

from src.database.connection import execute_query
import logging

logger = logging.getLogger(__name__)

def migrate_store_products():
    """Create store_products table with all required columns"""
    
    # Create store_products table
    create_products_query = """
    CREATE TABLE IF NOT EXISTS store_products (
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
    """
    
    # Create store_orders table
    create_orders_query = """
    CREATE TABLE IF NOT EXISTS store_orders (
        order_id SERIAL PRIMARY KEY,
        user_id BIGINT NOT NULL,
        order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        total_amount DECIMAL(10, 2) NOT NULL,
        payment_method VARCHAR(50),
        order_status VARCHAR(50) DEFAULT 'PENDING',
        delivery_address TEXT,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
    );
    """
    
    # Create store_order_items table
    create_order_items_query = """
    CREATE TABLE IF NOT EXISTS store_order_items (
        order_item_id SERIAL PRIMARY KEY,
        order_id INT NOT NULL,
        product_id INT NOT NULL,
        quantity INT NOT NULL,
        unit_price DECIMAL(10, 2) NOT NULL,
        discount_percent DECIMAL(5, 2) DEFAULT 0,
        item_total DECIMAL(10, 2) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (order_id) REFERENCES store_orders(order_id) ON DELETE CASCADE,
        FOREIGN KEY (product_id) REFERENCES store_products(product_id) ON DELETE RESTRICT
    );
    """
    
    # Create indexes
    create_indexes_query = """
    CREATE INDEX IF NOT EXISTS idx_store_products_category ON store_products(category);
    CREATE INDEX IF NOT EXISTS idx_store_products_status ON store_products(status);
    CREATE INDEX IF NOT EXISTS idx_store_orders_user ON store_orders(user_id);
    CREATE INDEX IF NOT EXISTS idx_store_order_items_order ON store_order_items(order_id);
    """
    
    try:
        # Execute table creation queries
        print("Creating store_products table...")
        execute_query(create_products_query)
        print("[OK] store_products table created")
        
        print("Creating store_orders table...")
        execute_query(create_orders_query)
        print("[OK] store_orders table created")
        
        print("Creating store_order_items table...")
        execute_query(create_order_items_query)
        print("[OK] store_order_items table created")
        
        print("Creating indexes...")
        execute_query(create_indexes_query)
        print("[OK] Indexes created")
        
        print("\n[SUCCESS] Store migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"[ERROR] Migration failed: {e}")
        return False

if __name__ == "__main__":
    migrate_store_products()
