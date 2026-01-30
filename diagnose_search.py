#!/usr/bin/env python3
"""
Standalone diagnostic: Check store_items schema and search without triggering bot
"""
import os
import sys

# Set environment BEFORE any imports
os.environ['USE_LOCAL_DB'] = 'false'
os.environ['USE_REMOTE_DB'] = 'true'
os.environ['ENV'] = 'remote'

import pymysql
from dotenv import load_dotenv

# Load .env
load_dotenv()

DATABASE_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', '3306')),
    'database': os.getenv('DB_NAME', 'fitness_club_db'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASS', os.getenv('DB_PASSWORD', '')),
}

print("=" * 80)
print("DIAGNOSTIC: Store Items Table Schema & Search")
print("=" * 80)

try:
    conn = pymysql.connect(
        host=DATABASE_CONFIG['host'],
        port=DATABASE_CONFIG['port'],
        user=DATABASE_CONFIG['user'],
        password=DATABASE_CONFIG['password'],
        database=DATABASE_CONFIG['database']
    )
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    print(f"\n✓ Connected to {DATABASE_CONFIG['database']} @ {DATABASE_CONFIG['host']}")
    
    # Check 1: Get column names
    print("\n--- CHECK 1: Store_items Columns ---")
    cursor.execute('''
        SELECT COLUMN_NAME, COLUMN_TYPE 
        FROM information_schema.COLUMNS 
        WHERE TABLE_SCHEMA = DATABASE() 
        AND TABLE_NAME = "store_items"
        ORDER BY ORDINAL_POSITION
    ''')
    
    rows = cursor.fetchall()
    if not rows:
        print("❌ NO COLUMNS FOUND - Table does not exist or empty schema!")
    else:
        print(f"✓ Found {len(rows)} columns:")
        columns = set()
        for row in rows:
            col_name = row['COLUMN_NAME']
            col_type = row['COLUMN_TYPE']
            print(f"  - {col_name}: {col_type}")
            columns.add(col_name)
        
        # Check 2: Verify expected columns
        print("\n--- CHECK 2: Expected Columns Verification ---")
        expected_sets = {
            'serial_name': {'serial', 'name', 'mrp', 'gst'},
            'item_name': {'item_id', 'item_name', 'mrp', 'gst_percent'},
            'serial_no': {'serial_no'},
        }
        
        for schema_name, expected_cols in expected_sets.items():
            if expected_cols.issubset(columns):
                print(f"  ✓ {schema_name}: ALL FOUND {expected_cols}")
            else:
                missing = expected_cols - columns
                print(f"  ✗ {schema_name}: MISSING {missing}")
    
    # Check 3: Count rows
    print("\n--- CHECK 3: Row Count ---")
    cursor.execute('SELECT COUNT(*) as cnt FROM store_items')
    count_result = cursor.fetchone()
    print(f"  Total rows: {count_result['cnt']}")
    
    # Check 4: Test search for serial = 2
    print("\n--- CHECK 4: Test Search (serial = 2) ---")
    if 'serial' in columns:
        cursor.execute('SELECT * FROM store_items WHERE serial = 2 LIMIT 1')
        result = cursor.fetchone()
        if result:
            print(f"  ✓ Found: {result}")
        else:
            print(f"  ✗ NOT FOUND - No row with serial = 2")
    else:
        print(f"  ⚠ Skipped: 'serial' column not in table")
    
    # Check 5: Test search with numeric cast
    print("\n--- CHECK 5: Test Search (numeric conversion) ---")
    cursor.execute("SELECT * FROM store_items WHERE CAST(serial AS SIGNED) = 2 LIMIT 1")
    result = cursor.fetchone()
    if result:
        print(f"  ✓ Found with CAST: {result}")
    else:
        print(f"  ✗ NOT FOUND even with CAST")
    
    # Check 6: Show first few rows
    print("\n--- CHECK 6: Sample Rows ---")
    cursor.execute('SELECT * FROM store_items LIMIT 3')
    samples = cursor.fetchall()
    for i, row in enumerate(samples, 1):
        print(f"  Row {i}: {row}")
    
    conn.close()
    print("\n" + "=" * 80)
    
except Exception as e:
    print(f"\n❌ ERROR: {type(e).__name__}")
    print(f"   {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
