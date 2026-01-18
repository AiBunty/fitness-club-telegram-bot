"""
Migration: Add payment_method and amount_paid to shake_purchases table
Run this to update shake credit purchases to support payment method selection and partial payments
"""

import psycopg2
from src.config import DATABASE_CONFIG

def migrate():
    """Add payment columns to shake_purchases"""
    conn = None
    try:
        conn = psycopg2.connect(**DATABASE_CONFIG)
        cursor = conn.cursor()
        
        print("🔄 Starting migration: Add payment_method to shake_purchases...")
        
        # Check if columns already exist
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'shake_purchases' 
            AND column_name IN ('payment_method', 'amount_paid')
        """)
        existing_columns = [row[0] for row in cursor.fetchall()]
        
        if 'payment_method' not in existing_columns:
            print("  Adding payment_method column...")
            cursor.execute("""
                ALTER TABLE shake_purchases 
                ADD COLUMN payment_method VARCHAR(10) DEFAULT 'unknown'
            """)
            print("  ✅ payment_method column added")
        else:
            print("  ℹ️  payment_method column already exists")
        
        if 'amount_paid' not in existing_columns:
            print("  Adding amount_paid column...")
            cursor.execute("""
                ALTER TABLE shake_purchases 
                ADD COLUMN amount_paid DECIMAL(10,2) DEFAULT 0.00
            """)
            print("  ✅ amount_paid column added")
        else:
            print("  ℹ️  amount_paid column already exists")
        
        conn.commit()
        print("✅ Migration completed successfully!")
        
        # Show current schema
        cursor.execute("""
            SELECT column_name, data_type, column_default
            FROM information_schema.columns 
            WHERE table_name = 'shake_purchases'
            ORDER BY ordinal_position
        """)
        
        print("\n📋 Current shake_purchases schema:")
        for row in cursor.fetchall():
            print(f"   {row[0]:20s} {row[1]:15s} (default: {row[2]})")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            cursor.close()
            conn.close()

if __name__ == "__main__":
    migrate()
