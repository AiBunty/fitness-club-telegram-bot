#!/usr/bin/env python3
"""
Migration: Add store management tables
- store_products: Catalog of products
- store_orders: Orders placed by users
- store_order_items: Line items in orders
- store_order_payments: Payment log
"""

import sys
import logging
from src.database.connection import get_db_cursor

logger = logging.getLogger(__name__)


def migrate():
    """Create store tables"""
    try:
        with get_db_cursor(commit=True) as cursor:
            # Products table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS store_products (
                    product_id SERIAL PRIMARY KEY,
                    product_code VARCHAR(50) NOT NULL UNIQUE,
                    category VARCHAR(100) NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    price DECIMAL(10,2) NOT NULL,
                    discount_percent DECIMAL(5,2) DEFAULT 0,
                    stock INT DEFAULT 0,
                    status VARCHAR(20) DEFAULT 'ACTIVE',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

            # Orders table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS store_orders (
                    order_id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    total_amount DECIMAL(10,2) NOT NULL,
                    balance DECIMAL(10,2),
                    payment_method VARCHAR(50) DEFAULT 'FULL',
                    payment_status VARCHAR(50) DEFAULT 'OPEN',
                    notes TEXT,
                    closed_by BIGINT,
                    closed_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                );
                """
            )

            # Order items table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS store_order_items (
                    order_item_id SERIAL PRIMARY KEY,
                    order_id INT NOT NULL,
                    product_id INT NOT NULL,
                    quantity INT NOT NULL,
                    unit_price DECIMAL(10,2) NOT NULL,
                    line_total DECIMAL(10,2) NOT NULL,
                    FOREIGN KEY (order_id) REFERENCES store_orders(order_id) ON DELETE CASCADE,
                    FOREIGN KEY (product_id) REFERENCES store_products(product_id) ON DELETE RESTRICT
                );
                """
            )

            # Order payments log
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS store_order_payments (
                    payment_id SERIAL PRIMARY KEY,
                    order_id INT NOT NULL,
                    amount DECIMAL(10,2) NOT NULL,
                    payment_method VARCHAR(50),
                    admin_confirmed BOOLEAN DEFAULT FALSE,
                    admin_id BIGINT,
                    reference VARCHAR(255),
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (order_id) REFERENCES store_orders(order_id) ON DELETE CASCADE
                );
                """
            )

            # Create indexes
            # Ensure product_code column exists for older partial runs
            cursor.execute("ALTER TABLE store_products ADD COLUMN IF NOT EXISTS product_code VARCHAR(50);")
            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_store_products_code ON store_products(product_code);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_store_products_category ON store_products(category);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_store_orders_user ON store_orders(user_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_store_orders_status ON store_orders(payment_status);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_store_order_items_order ON store_order_items(order_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_store_order_payments_order ON store_order_payments(order_id);")

        print("Migration successful: store tables created")
        return True
    except Exception as e:
        logger.exception("Store migration failed")
        print(f"Migration failed: {e}")
        return False


if __name__ == "__main__":
    success = migrate()
    sys.exit(0 if success else 1)
