#!/usr/bin/env python3
"""Check where admin data is stored"""

from src.database.connection import execute_query

try:
    print("Checking admin_roles table...")
    result = execute_query(
        "SELECT user_id, created_by FROM admin_roles LIMIT 10;",
        fetch_one=False
    )
    if result:
        print(f"✅ Found {len(result)} admins in admin_roles table:")
        for row in result:
            print(f"   - User ID: {row['user_id']}")
    else:
        print("   ❌ No admins in admin_roles table")
    
    print("\n Checking users table where role='admin'...")
    result = execute_query(
        "SELECT user_id, username FROM users WHERE role = 'admin' LIMIT 10;",
        fetch_one=False
    )
    if result:
        print(f"✅ Found {len(result)} admins in users table:")
        for row in result:
            print(f"   - User ID: {row['user_id']}, Username: {row.get('username')}")
    else:
        print("   ❌ No admins in users table with role='admin'")
        
    print("\n  Checking all roles in users table...")
    result = execute_query(
        "SELECT DISTINCT role FROM users;",
        fetch_one=False
    )
    if result:
        print(f"✅ Available roles: {[r['role'] for r in result]}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
