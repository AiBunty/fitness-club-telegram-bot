#!/usr/bin/env python3
"""Debug script to check admin IDs in database"""

from src.database.role_operations import list_admins
from src.database.connection import execute_query

try:
    print("🔍 Checking admin setup in database...\n")
    
    # Get all admins
    admins = list_admins()
    print(f"✅ Admins found: {len(admins)}")
    
    if admins:
        for admin in admins:
            print(f"   - User ID: {admin.get('user_id')}, Username: {admin.get('username')}, Name: {admin.get('name')}")
    else:
        print("   ❌ No admins found in database!")
    
    # Get all users with admin role
    print("\n🔍 Checking users table for admin role...\n")
    result = execute_query(
        "SELECT user_id, name, username, role FROM users WHERE role = 'admin' LIMIT 10;",
        fetch_one=False
    )
    
    if result:
        print(f"✅ Users with admin role: {len(result)}")
        for row in result:
            print(f"   - User ID: {row['user_id']}, Name: {row['name']}, Username: {row['username']}")
    else:
        print("   ❌ No users with admin role found!")
    
    print("\n💡 If no admins found, you need to:")
    print("   1. Create a user account in the bot")
    print("   2. Run: python set_admin_role.py")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
