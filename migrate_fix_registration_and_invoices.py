#!/usr/bin/env python3
"""
Migration: Fix User Registration & Invoice Sending
- Add missing columns: gender, profile_pic_url, approval_status
- Fix user_id column type: INT -> BIGINT (fixes invoice "Chat not found" error)
- Verify schema consistency with create_user() expectations

Date: January 28, 2026
"""
import pymysql
import sys
from dotenv import load_dotenv
import os

load_dotenv(override=True)

DB_HOST = os.getenv('DB_HOST')
DB_USER = os.getenv('DB_USER')
DB_PASS = os.getenv('DB_PASS')
DB_NAME = os.getenv('DB_NAME')
DB_PORT = int(os.getenv('DB_PORT', 3306))

print("[MIGRATION] Connecting to MySQL...")
try:
    conn = pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        port=DB_PORT,
        charset='utf8mb4'
    )
    cursor = conn.cursor()
    print(f"[MIGRATION] ✅ Connected to {DB_NAME}")
except Exception as e:
    print(f"[MIGRATION] ❌ Connection failed: {e}")
    sys.exit(1)

try:
    # Step 1: Check current users table structure
    print("\n[MIGRATION] Step 1: Analyzing current schema...")
    cursor.execute("DESC users")
    columns = cursor.fetchall()
    column_names = {col[0]: col[1] for col in columns}
    
    print("Current columns:")
    for col_name, col_type in column_names.items():
        print(f"  ✓ {col_name}: {col_type}")
    
    # Step 2: Check user_id column type
    print("\n[MIGRATION] Step 2: Checking user_id column type...")
    if 'INT' in column_names.get('user_id', ''):
        if 'BIGINT' not in column_names.get('user_id', ''):
            print(f"  ⚠️  user_id is {column_names['user_id']} (should be BIGINT)")
            print("     This causes invoice 'Chat not found' error (32-bit overflow)")
            print("  ℹ️  Will upgrade to BIGINT...")
            # Note: Can't directly change INT to BIGINT on non-empty table
            # Need to use MODIFY COLUMN
            cursor.execute("ALTER TABLE users MODIFY COLUMN user_id BIGINT")
            conn.commit()
            print("  ✅ user_id upgraded to BIGINT")
        else:
            print("  ✅ user_id is already BIGINT")
    
    # Step 3: Add missing columns
    print("\n[MIGRATION] Step 3: Adding missing columns...")
    
    missing_cols = {
        'gender': "VARCHAR(20)",
        'profile_pic_url': "TEXT",
        'approval_status': "VARCHAR(50) DEFAULT 'approved'"
    }
    
    for col_name, col_type in missing_cols.items():
        if col_name not in column_names:
            print(f"  ⚠️  {col_name} is missing")
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
            conn.commit()
            print(f"  ✅ Added {col_name} ({col_type})")
        else:
            print(f"  ✓ {col_name} already exists")
    
    # Step 4: Verify schema consistency
    print("\n[MIGRATION] Step 4: Verifying schema consistency...")
    cursor.execute("DESC users")
    columns = cursor.fetchall()
    final_columns = {col[0]: col[1] for col in columns}
    
    required_cols = {
        'user_id': 'BIGINT',
        'telegram_username': 'VARCHAR',
        'full_name': 'VARCHAR',
        'phone': 'VARCHAR',
        'age': 'INT',
        'initial_weight': 'DECIMAL',
        'current_weight': 'DECIMAL',
        'gender': 'VARCHAR',
        'profile_pic_url': 'TEXT',
        'referral_code': 'VARCHAR',
        'approval_status': 'VARCHAR'
    }
    
    all_good = True
    for col_name, col_type_expected in required_cols.items():
        if col_name not in final_columns:
            print(f"  ❌ {col_name} is still missing!")
            all_good = False
        else:
            actual_type = final_columns[col_name]
            if col_type_expected.upper() in actual_type.upper():
                print(f"  ✅ {col_name}: {actual_type}")
            else:
                print(f"  ⚠️  {col_name}: {actual_type} (expected {col_type_expected})")
    
    # Step 5: Check if any data exists and needs migration
    print("\n[MIGRATION] Step 5: Checking data integrity...")
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]
    print(f"  Total users in database: {user_count}")
    
    if user_count > 0:
        # Check for data that might need fixing
        cursor.execute("SELECT user_id FROM users WHERE user_id = 2147483647 LIMIT 1")
        result = cursor.fetchone()
        if result:
            print("  ⚠️  Found overflow user_id (2147483647) - data corruption detected")
            print("     This is from storing 64-bit IDs in 32-bit INT column")
            print("     Users with this ID cannot receive invoices")
        else:
            print("  ✅ No data corruption detected")
    
    conn.close()
    
    print("\n[MIGRATION] ✅ Migration complete!")
    print("\nNext steps:")
    print("1. Run the bot to test registration")
    print("2. Create a new user and verify registration succeeds")
    print("3. Generate an invoice and verify 'Chat not found' error is fixed")
    
except Exception as e:
    print(f"\n[MIGRATION] ❌ Error: {e}")
    conn.rollback()
    sys.exit(1)
finally:
    try:
        conn.close()
    except:
        pass
