#!/usr/bin/env python3
"""
Direct MySQL validation without bot imports
"""
import os
import sys
import mysql.connector

# Database credentials
DB_HOST = 'mysql.gb.stackcp.com'
DB_PORT = 42152
DB_NAME = 'FItnessBot-313935eecd'
DB_USER = 'FItnessBot-313935eecd'
DB_PASS = 'Zebra@789'

def connect_db():
    return mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME
    )

def run_validation():
    """Validate schema migration success"""
    try:
        conn = connect_db()
        cursor = conn.cursor(dictionary=True)
        
        print("\n" + "="*80)
        print("VALIDATION: Schema Migration Success Check")
        print("="*80)
        
        # Check 1: accounts_receivable table exists and has correct columns
        print("\n✓ Checking accounts_receivable table...")
        cursor.execute("DESCRIBE accounts_receivable")
        ar_cols = {row['Field']: row['Type'] for row in cursor.fetchall()}
        
        required_ar_cols = [
            'receivable_id', 'user_id', 'receivable_type', 'source_id',
            'bill_amount', 'discount_amount', 'final_amount', 'status',
            'due_date', 'created_at', 'updated_at'
        ]
        
        missing = [c for c in required_ar_cols if c not in ar_cols]
        if missing:
            print(f"  ✗ FAILED: Missing columns in accounts_receivable: {missing}")
            return False
        print(f"  ✓ All required columns present: {len(ar_cols)} columns")
        
        # Check 2: ar_transactions table exists and has correct columns
        print("\n✓ Checking ar_transactions table...")
        cursor.execute("DESCRIBE ar_transactions")
        art_cols = {row['Field']: row['Type'] for row in cursor.fetchall()}
        
        required_art_cols = [
            'transaction_id', 'receivable_id', 'method', 'amount',
            'reference', 'created_by', 'created_at'
        ]
        
        missing = [c for c in required_art_cols if c not in art_cols]
        if missing:
            print(f"  ✗ FAILED: Missing columns in ar_transactions: {missing}")
            return False
        print(f"  ✓ All required columns present: {len(art_cols)} columns")
        
        # Check 3: subscription_requests has correct schema
        print("\n✓ Checking subscription_requests table...")
        cursor.execute("DESCRIBE subscription_requests")
        sr_cols = {row['Field']: row['Type'] for row in cursor.fetchall()}
        
        required_sr_cols = ['id', 'user_id', 'plan_id', 'amount', 'status', 'requested_at']
        missing = [c for c in required_sr_cols if c not in sr_cols]
        if missing:
            print(f"  ✗ FAILED: Missing columns in subscription_requests: {missing}")
            return False
        print(f"  ✓ All required columns present: {len(sr_cols)} columns")
        
        # Check 4: subscriptions table has grace_period_end
        print("\n✓ Checking subscriptions table...")
        cursor.execute("DESCRIBE subscriptions")
        sub_cols = {row['Field']: row['Type'] for row in cursor.fetchall()}
        
        if 'grace_period_end' not in sub_cols:
            print(f"  ✗ FAILED: Missing grace_period_end in subscriptions")
            return False
        print(f"  ✓ All required columns present: {len(sub_cols)} columns")
        
        # Check 5: Foreign keys exist
        print("\n✓ Checking foreign key constraints...")
        cursor.execute("""
            SELECT CONSTRAINT_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
            WHERE TABLE_NAME IN ('accounts_receivable', 'ar_transactions')
            AND TABLE_SCHEMA = %s
        """, (DB_NAME,))
        
        fks = cursor.fetchall()
        if len(fks) < 2:
            print(f"  ⚠ Warning: Expected at least 2 FKs, found {len(fks)}")
        else:
            print(f"  ✓ Foreign keys configured: {len(fks)} constraints")
        
        # Check 6: Verify empty tables (fresh schema)
        print("\n✓ Checking table status...")
        cursor.execute("SELECT COUNT(*) as count FROM accounts_receivable")
        ar_count = cursor.fetchone()['count']
        print(f"  ✓ accounts_receivable rows: {ar_count} (fresh: {ar_count == 0})")
        
        cursor.execute("SELECT COUNT(*) as count FROM ar_transactions")
        art_count = cursor.fetchone()['count']
        print(f"  ✓ ar_transactions rows: {art_count} (fresh: {art_count == 0})")
        
        print("\n" + "="*80)
        print("✅ ALL SCHEMA VALIDATION CHECKS PASSED")
        print("="*80 + "\n")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"\n✗ VALIDATION FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = run_validation()
    sys.exit(0 if success else 1)
