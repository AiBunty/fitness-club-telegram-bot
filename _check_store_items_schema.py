#!/usr/bin/env python3
"""
Diagnostic check: Verify store_items table schema and test search
"""
import os
import sys

os.environ['USE_LOCAL_DB'] = 'false'
os.environ['USE_REMOTE_DB'] = 'true'
os.environ['ENV'] = 'remote'

sys.path.insert(0, '.')

from src.config import DATABASE_CONFIG
import pymysql

print("=" * 80)
print("DIAGNOSTIC CHECK: Store Items Table Schema")
print("=" * 80)

try:
    conn = pymysql.connect(
        host=DATABASE_CONFIG['host'],
        port=DATABASE_CONFIG['port'],
        user=DATABASE_CONFIG['user'],
        password=DATABASE_CONFIG['password'],
        database=DATABASE_CONFIG['database']
    )
    cur = conn.cursor()
    
    # Check 1: Get all columns
    print("\n✓ Connected to database")
    print(f"  Database: {DATABASE_CONFIG['database']}")
    print(f"  Host: {DATABASE_CONFIG['host']}")
    
    # Check 2: Query schema
    cur.execute("""
        SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE
        FROM information_schema.COLUMNS 
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'store_items'
        ORDER BY ORDINAL_POSITION
    """, (DATABASE_CONFIG['database'],))
    
    schema_rows = cur.fetchall()
    
    if not schema_rows:
        print("\n❌ ERROR: store_items table NOT FOUND in database!")
        sys.exit(1)
    
    print(f"\n✓ store_items table found with {len(schema_rows)} columns:")
    print("\n  COLUMN_NAME      | COLUMN_TYPE     | IS_NULLABLE")
    print("  " + "-" * 50)
    
    cols = {}
    for row in schema_rows:
        col_name, col_type, is_nullable = row
        cols[col_name] = col_type
        print(f"  {col_name:16} | {col_type:15} | {is_nullable}")
    
    # Check 3: Expected columns
    print("\n" + "=" * 80)
    print("SCHEMA VALIDATION:")
    print("=" * 80)
    
    expected = {'serial', 'name', 'hsn', 'mrp', 'gst'}
    found = set(cols.keys())
    
    missing = expected - found
    extra = found - expected
    
    if missing:
        print(f"\n❌ MISSING columns: {missing}")
    else:
        print(f"\n✓ All expected columns present: {expected}")
    
    if extra:
        print(f"⚠️  Extra columns: {extra}")
    
    # Check 4: Count rows
    print("\n" + "=" * 80)
    print("DATA CHECK:")
    print("=" * 80)
    
    cur.execute("SELECT COUNT(*) as count FROM store_items")
    count_row = cur.fetchone()
    count = count_row[0] if count_row else 0
    
    print(f"\n✓ Total items in store_items table: {count}")
    
    # Check 5: Test search with serial #2
    if count > 0:
        print("\n" + "=" * 80)
        print("TEST SEARCH (Serial #2):")
        print("=" * 80)
        
        cur.execute("SELECT serial, name, hsn, mrp, gst FROM store_items WHERE serial = %s", (2,))
        test_row = cur.fetchone()
        
        if test_row:
            print(f"\n✓ FOUND item with serial #2:")
            print(f"  Serial: {test_row[0]}")
            print(f"  Name: {test_row[1]}")
            print(f"  HSN: {test_row[2]}")
            print(f"  MRP: {test_row[3]}")
            print(f"  GST: {test_row[4]}")
        else:
            print(f"\n⚠️  NO item found with serial #2")
            
            # Show first 5 items
            cur.execute("SELECT serial, name FROM store_items LIMIT 5")
            first_items = cur.fetchall()
            print(f"\n  First items in table:")
            for item in first_items:
                print(f"    - Serial #{item[0]}: {item[1]}")
    
    # Check 6: Test numeric string conversion
    print("\n" + "=" * 80)
    print("STRING CONVERSION TEST:")
    print("=" * 80)
    
    test_cases = ["2", "1", "999", "abc", "2.5"]
    for test in test_cases:
        is_digit = test.isdigit()
        print(f"  '{test}'.isdigit() = {is_digit}")
    
    cur.close()
    conn.close()
    
    print("\n" + "=" * 80)
    print("✓ DIAGNOSTIC CHECK COMPLETE")
    print("=" * 80)

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
