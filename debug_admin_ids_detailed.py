#!/usr/bin/env python3
"""Debug get_admin_ids with logging"""

import logging
from src.database.role_operations import list_admins

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def get_admin_ids_debug() -> list:
    """Get list of all admin user IDs - with debug logging"""
    try:
        print("Calling list_admins()...")
        admins = list_admins()
        print(f"list_admins() returned: {admins}")
        print(f"Type: {type(admins)}")
        
        if admins:
            result = [admin.get('user_id') for admin in admins if admin.get('user_id')]
            print(f"Extracted user_ids: {result}")
            return result
        else:
            print("admins is falsy")
    except Exception as e:
        logger.error(f"Error getting admin IDs: {e}", exc_info=True)
    return []

try:
    admin_ids = get_admin_ids_debug()
    print(f"\nFinal result: {admin_ids}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
