#!/usr/bin/env python3
"""Check admin in users table"""

from src.database.connection import execute_query

try:
    print("Checking users table for admins...")
    result = execute_query(
        "SELECT user_id, username, role FROM users WHERE role = 'admin' LIMIT 10;",
        fetch_one=False
    )
    if result:
        print(f"✅ Found {len(result)} admins:")
        for row in result:
            print(f"   - User ID: {row['user_id']}, Username: {row.get('username')}, Role: {row['role']}")
    else:
        print("❌ No users with role='admin'")
    
    print("\nChecking all roles...")
    result = execute_query(
        "SELECT role, COUNT(*) as count FROM users GROUP BY role;",
        fetch_one=False
    )
    if result:
        for row in result:
            print(f"   - Role: {row['role']}, Count: {row['count']}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
