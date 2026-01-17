#!/usr/bin/env python3
"""Debug list_admins function"""

from src.database.role_operations import list_admins
from src.database.connection import execute_query

try:
    print("Testing direct query...")
    result = execute_query(
        "SELECT user_id, full_name FROM users WHERE role = 'admin' ORDER BY user_id",
        fetch_one=False
    )
    print(f"Direct query result: {result}")
    print(f"Type: {type(result)}")
    
    print("\nTesting list_admins() function...")
    admins = list_admins()
    print(f"list_admins() result: {admins}")
    print(f"Type: {type(admins)}")
    print(f"Length: {len(admins)}")
    
    if admins:
        for admin in admins:
            print(f"  - Admin: {admin}")
            if isinstance(admin, dict):
                print(f"    User ID: {admin.get('user_id')}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
