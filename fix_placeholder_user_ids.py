#!/usr/bin/env python3
"""
Database Migration: Fix Placeholder User IDs

This script identifies users with placeholder Telegram IDs (>= 2147483647) in the database
and replaces them with actual Telegram IDs from the migration mapping.

Placeholder IDs indicate users who haven't sent /start to the bot and received their
real Telegram ID from the update context.

CRITICAL: This should be run ONCE before resuming bot operations.
"""

import os
import sys
import pymysql
from pymysql.cursors import DictCursor
from typing import Dict, List, Tuple, Optional

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from config import DATABASE_CONFIG, USE_REMOTE_DB, USE_LOCAL_DB


# Mapping of users with placeholder IDs to their actual Telegram IDs
# This data comes from COMPLETE_DATA_MIGRATION_REPORT.md
PLACEHOLDER_ID_FIXES: Dict[int, Tuple[str, int]] = {
    2147483647: ('Sayali Sunil Wani', 6133468540),
    # Add more mappings here as needed
    # Format: placeholder_id: ('full_name', actual_telegram_id)
}

INT32_MAX = 2147483647  # Used as placeholder when user hasn't sent /start


def connect_db():
    """Create database connection."""
    try:
        if USE_LOCAL_DB and not USE_REMOTE_DB:
            print("❌ This migration requires remote MySQL database.")
            print(f"   Current config: USE_LOCAL_DB={USE_LOCAL_DB}, USE_REMOTE_DB={USE_REMOTE_DB}")
            sys.exit(1)
        
        config = dict(DATABASE_CONFIG)
        config['cursorclass'] = DictCursor
        config['autocommit'] = False
        config['charset'] = 'utf8mb4'
        config['connect_timeout'] = 30
        config['read_timeout'] = 30
        config['write_timeout'] = 30
        
        conn = pymysql.connect(**config)
        return conn
    except pymysql.Error as e:
        print(f"❌ Database connection failed: {e}")
        sys.exit(1)


def find_placeholder_users(conn) -> List[Dict]:
    """Find all users with placeholder IDs in database."""
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT user_id, full_name, telegram_username, phone 
            FROM users 
            WHERE user_id >= %s
            ORDER BY full_name
        """, (INT32_MAX,))
        return cursor.fetchall()
    finally:
        cursor.close()


def fix_placeholder_user(conn, placeholder_id: int, actual_id: int, 
                        full_name: str) -> bool:
    """Replace placeholder user_id with actual Telegram ID.
    
    IMPORTANT: user_id is PRIMARY KEY, so we must update all references carefully
    """
    cursor = conn.cursor()
    try:
        # Check if actual_id already exists
        cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (actual_id,))
        if cursor.fetchone():
            print(f"  ⚠️  Actual ID {actual_id} already exists in database for {full_name}")
            cursor.close()
            return False
        
        # Begin transaction
        cursor.execute("START TRANSACTION")
        
        # Update invoices to use new ID first (if any exist)
        cursor.execute("""
            UPDATE invoices 
            SET user_id = %s 
            WHERE user_id = %s
        """, (actual_id, placeholder_id))
        invoices_updated = cursor.rowcount
        
        # Update user record
        cursor.execute("""
            UPDATE users 
            SET user_id = %s 
            WHERE user_id = %s
        """, (actual_id, placeholder_id))
        users_updated = cursor.rowcount
        
        if users_updated == 0:
            cursor.execute("ROLLBACK")
            print(f"  ❌ User not found with placeholder ID {placeholder_id}")
            cursor.close()
            return False
        
        # Commit transaction
        cursor.execute("COMMIT")
        print(f"  ✅ Fixed {full_name}: {placeholder_id} → {actual_id}")
        print(f"     (Updated {invoices_updated} invoices, {users_updated} user record)")
        cursor.close()
        return True
        
    except pymysql.Error as e:
        try:
            cursor.execute("ROLLBACK")
        except:
            pass
        print(f"  ❌ Error fixing user {placeholder_id}: {e}")
        cursor.close()
        return False


def verify_fixes(conn) -> Dict[str, int]:
    """Verify all placeholder IDs have been fixed."""
    cursor = conn.cursor()
    try:
        # Check for remaining placeholders
        cursor.execute("""
            SELECT user_id, full_name 
            FROM users 
            WHERE user_id >= %s
            ORDER BY full_name
        """, (INT32_MAX,))
        remaining = cursor.fetchall()
        
        # Check for expected fixed users
        cursor.execute("""
            SELECT user_id, full_name, telegram_username 
            FROM users 
            WHERE full_name LIKE %s
            ORDER BY full_name
        """, ('%Sayali%',))
        fixed_users = cursor.fetchall()
        
        cursor.close()
        return {
            'remaining_placeholders': len(remaining),
            'fixed_users': fixed_users,
            'remaining_list': remaining
        }
    except:
        cursor.close()
        return {
            'remaining_placeholders': -1,
            'fixed_users': [],
            'remaining_list': []
        }


def main():
    """Main migration function."""
    print("\n" + "="*70)
    print("DATABASE MIGRATION: Fix Placeholder User IDs")
    print("="*70 + "\n")
    
    conn = connect_db()
    try:
        # Step 1: Find current placeholder users
        print("STEP 1: Scanning database for placeholder user IDs...\n")
        placeholder_users = find_placeholder_users(conn)
        
        if not placeholder_users:
            print("✅ No placeholder user IDs found in database\n")
            return
        
        print(f"Found {len(placeholder_users)} user(s) with placeholder IDs:\n")
        for user in placeholder_users:
            print(f"  • {user['full_name']} (@{user['telegram_username']})")
            print(f"    ID: {user['user_id']}")
        
        # Step 2: Apply fixes
        print(f"\n\nSTEP 2: Fixing placeholder IDs from mapping...\n")
        
        fixes_applied = 0
        fixes_available = len([p for p in placeholder_users 
                              if p['user_id'] in PLACEHOLDER_ID_FIXES])
        
        for user in placeholder_users:
            if user['user_id'] not in PLACEHOLDER_ID_FIXES:
                print(f"⚠️  No mapping found for {user['full_name']} (ID: {user['user_id']})")
                print(f"   → Skipping. User needs to send /start to bot to get real Telegram ID")
                continue
            
            full_name, actual_id = PLACEHOLDER_ID_FIXES[user['user_id']]
            if fix_placeholder_user(conn, user['user_id'], actual_id, full_name):
                fixes_applied += 1
        
        print(f"\n\nSTEP 3: Verification...\n")
        
        verification = verify_fixes(conn)
        
        if verification['remaining_placeholders'] > 0:
            print(f"⚠️  {verification['remaining_placeholders']} placeholder IDs remain:\n")
            for user in verification['remaining_list']:
                print(f"  • {user['full_name']}: {user['user_id']}")
            print("\n💡 These users need to send /start to bot to receive real Telegram ID")
        else:
            print("✅ All placeholder IDs have been fixed!")
        
        print(f"\n✅ Fixed users:\n")
        for user in verification['fixed_users']:
            username = f"@{user['telegram_username']}" if user['telegram_username'] else "no username"
            print(f"  • {user['full_name']} ({username})")
            print(f"    Real Telegram ID: {user['user_id']}")
        
        print(f"\n{'='*70}")
        print(f"Migration Complete: {fixes_applied}/{fixes_available} mappings applied")
        print(f"{'='*70}\n")
        
    finally:
        conn.close()


if __name__ == '__main__':
    main()
