#!/usr/bin/env python3
"""
Migration: Add Payment Support to Subscriptions
- Add payment_method column to subscription_requests
- Create subscription_payments table for revenue tracking
- Create subscription_upi_codes table for UPI QR storage
"""

import sys
import os
from src.database.connection import DatabaseConnection

def run_migration():
    """Execute database migration"""
    db = DatabaseConnection()
    conn = db.get_connection()
    cursor = None
    try:
        cursor = conn.cursor()
        
        print("Running subscription payment migration...")
        
        # 1. Add payment_method column to subscription_requests if not exists
        print("✓ Adding payment_method to subscription_requests...")
        try:
            cursor.execute("""
                ALTER TABLE subscription_requests
                ADD COLUMN payment_method VARCHAR(20) DEFAULT 'pending'
            """)
            print("  ✓ payment_method column added")
        except Exception as e:
            if "already exists" in str(e):
                print("  ✓ payment_method column already exists")
            else:
                print(f"  ✗ Error: {e}")
        
        # 2. Create subscription_payments table
        print("✓ Creating subscription_payments table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subscription_payments (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(user_id),
                request_id INT REFERENCES subscription_requests(id),
                amount DECIMAL(10, 2) NOT NULL,
                payment_method VARCHAR(20) NOT NULL,
                reference TEXT,
                status VARCHAR(20) DEFAULT 'completed',
                paid_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        print("  ✓ subscription_payments table created")
        
        # 3. Create subscription_upi_codes table for UPI QR codes
        print("✓ Creating subscription_upi_codes table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subscription_upi_codes (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(user_id),
                request_id INT NOT NULL REFERENCES subscription_requests(id),
                upi_string VARCHAR(500) NOT NULL,
                qr_code_file TEXT,
                amount DECIMAL(10, 2) NOT NULL,
                status VARCHAR(20) DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                verified_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        print("  ✓ subscription_upi_codes table created")
        
        # 4. Add indexes for better performance
        print("✓ Creating indexes...")
        try:
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_subscription_payments_user ON subscription_payments(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_subscription_payments_date ON subscription_payments(paid_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_subscription_payments_method ON subscription_payments(payment_method)")
            print("  ✓ Indexes created")
        except Exception as e:
            print(f"  ⚠ Index creation warning: {e}")
        
        # Commit changes
        conn.commit()
        print("\n✅ Migration completed successfully!")
        
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if cursor:
            cursor.close()

if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
