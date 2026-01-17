#!/usr/bin/env python3
"""Debug get_admin_ids function"""

from src.handlers.admin_handlers import get_admin_ids

try:
    print("Testing get_admin_ids()...")
    admin_ids = get_admin_ids()
    print(f"Result: {admin_ids}")
    print(f"Type: {type(admin_ids)}")
    print(f"Length: {len(admin_ids)}")
    
    if admin_ids:
        print("✅ Admins found!")
        for admin_id in admin_ids:
            print(f"  - Admin ID: {admin_id}")
    else:
        print("❌ No admins returned")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
