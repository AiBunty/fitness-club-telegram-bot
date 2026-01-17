"""
Migration: Add payment/subscription columns and fee_payments table
Enables user subscription management with admin approval workflow
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.database.connection import execute_query

def create_payment_system():
    """Create payment system tables and columns"""
    
    print("Step 1: Adding payment columns to users table...")
    alter_users_sql = """
    -- Add payment/subscription columns to users table
    DO $$ 
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                      WHERE table_name='users' AND column_name='fee_status') THEN
            ALTER TABLE users ADD COLUMN fee_status VARCHAR(20) DEFAULT 'unpaid';
        END IF;
        
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                      WHERE table_name='users' AND column_name='fee_paid_date') THEN
            ALTER TABLE users ADD COLUMN fee_paid_date DATE;
        END IF;
        
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                      WHERE table_name='users' AND column_name='fee_expiry_date') THEN
            ALTER TABLE users ADD COLUMN fee_expiry_date DATE;
        END IF;
    END $$;
    """
    
    try:
        execute_query(alter_users_sql)
        print("✅ Payment columns added to users table!")
    except Exception as e:
        print(f"⚠️ Note: {e}")
    
    print("\nStep 2: Creating fee_payments table...")
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS fee_payments (
        payment_id SERIAL PRIMARY KEY,
        user_id BIGINT NOT NULL,
        amount DECIMAL(10, 2) NOT NULL,
        payment_method VARCHAR(50) DEFAULT 'manual',
        status VARCHAR(20) DEFAULT 'pending',
        duration_days INTEGER DEFAULT 30,
        notes TEXT,
        approved_by BIGINT,
        approved_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT NOW(),
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
    );
    
    -- Create indexes for performance
    CREATE INDEX IF NOT EXISTS idx_fee_payments_user_id ON fee_payments(user_id);
    CREATE INDEX IF NOT EXISTS idx_fee_payments_status ON fee_payments(status);
    CREATE INDEX IF NOT EXISTS idx_fee_payments_created_at ON fee_payments(created_at);
    """
    
    try:
        execute_query(create_table_sql)
        print("✅ fee_payments table created successfully!")
        print("✅ Indexes created successfully!")
    except Exception as e:
        print(f"❌ Error creating fee_payments table: {e}")
        return False
    
    print("\nStep 3: Creating payment_requests table for admin approval workflow...")
    create_requests_table_sql = """
    CREATE TABLE IF NOT EXISTS payment_requests (
        request_id SERIAL PRIMARY KEY,
        user_id BIGINT NOT NULL,
        amount DECIMAL(10, 2),
        payment_proof_url TEXT,
        notes TEXT,
        status VARCHAR(20) DEFAULT 'pending',
        requested_at TIMESTAMP DEFAULT NOW(),
        reviewed_by BIGINT,
        reviewed_at TIMESTAMP,
        rejection_reason TEXT,
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
    );
    
    -- Create indexes
    CREATE INDEX IF NOT EXISTS idx_payment_requests_user_id ON payment_requests(user_id);
    CREATE INDEX IF NOT EXISTS idx_payment_requests_status ON payment_requests(status);
    CREATE INDEX IF NOT EXISTS idx_payment_requests_requested_at ON payment_requests(requested_at);
    """
    
    try:
        execute_query(create_requests_table_sql)
        print("✅ payment_requests table created successfully!")
        print("✅ Indexes created successfully!")
    except Exception as e:
        print(f"❌ Error creating payment_requests table: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("PAYMENT SYSTEM MIGRATION")
    print("=" * 60)
    print("\nThis will create:")
    print("1. Payment columns in users table")
    print("2. fee_payments table for payment history")
    print("3. payment_requests table for admin approval workflow")
    print("\n" + "=" * 60 + "\n")
    
    success = create_payment_system()
    
    if success:
        print("\n" + "=" * 60)
        print("✅ MIGRATION COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("\nPayment system is now ready!")
        print("\nFeatures enabled:")
        print("- User subscription management")
        print("- Payment request workflow")
        print("- Admin approval system")
        print("- Payment history tracking")
    else:
        print("\n" + "=" * 60)
        print("❌ MIGRATION FAILED!")
        print("=" * 60)
        sys.exit(1)
