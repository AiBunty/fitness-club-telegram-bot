#!/usr/bin/env python3
"""Check users table schema"""

from src.database.connection import execute_query

try:
    print("Checking users table schema...")
    result = execute_query(
        "SELECT column_name, data_type FROM information_schema.columns WHERE table_name='users' ORDER BY ordinal_position;",
        fetch_one=False
    )
    if result:
        print("✅ Users table columns:")
        for row in result:
            print(f"   - {row['column_name']}: {row['data_type']}")
    
    print("\nChecking for admins with role='admin'...")
    result = execute_query(
        "SELECT user_id, role FROM users WHERE role = 'admin' LIMIT 10;",
        fetch_one=False
    )
    if result:
        print(f"✅ Found {len(result)} admins")
    else:
        print("❌ No admins found")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
