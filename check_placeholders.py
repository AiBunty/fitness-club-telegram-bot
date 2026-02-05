#!/usr/bin/env python3
"""Quick script to test database connection and check placeholder users"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from config import DATABASE_CONFIG, USE_REMOTE_DB, USE_LOCAL_DB
import pymysql
from pymysql.cursors import DictCursor

try:
    if USE_LOCAL_DB and not USE_REMOTE_DB:
        print("❌ This database check requires remote MySQL database.")
        print(f"   Current config: USE_LOCAL_DB={USE_LOCAL_DB}, USE_REMOTE_DB={USE_REMOTE_DB}")
        sys.exit(1)
    
    print("Connecting to database...")
    print(f"Host: {DATABASE_CONFIG.get('host')}")
    print(f"Port: {DATABASE_CONFIG.get('port')}")
    print(f"Database: {DATABASE_CONFIG.get('database')}")
    
    db_config = dict(DATABASE_CONFIG)
    db_config['cursorclass'] = DictCursor
    db_config['autocommit'] = False
    db_config['charset'] = 'utf8mb4'
    db_config['connect_timeout'] = 30
    db_config['read_timeout'] = 30
    db_config['write_timeout'] = 30
    
    conn = pymysql.connect(**db_config)
    print("✅ Connected!\n")
    
    cursor = conn.cursor()
    
    # Find users with placeholder IDs
    print("=== CHECKING FOR PLACEHOLDER IDS ===\n")
    cursor.execute("""
        SELECT user_id, full_name, telegram_username 
        FROM users 
        WHERE user_id >= 2147483647
        ORDER BY full_name
    """)
    
    placeholder_users = cursor.fetchall()
    if placeholder_users:
        print(f"Found {len(placeholder_users)} user(s) with placeholder IDs:\n")
        for user in placeholder_users:
            print(f"  • {user['full_name']} (@{user['telegram_username']})")
            print(f"    Current ID: {user['user_id']}")
    else:
        print("✅ No placeholder IDs found!")
    
    print("\n=== CHECKING ALL USERS ===\n")
    cursor.execute("""
        SELECT user_id, full_name, telegram_username, role 
        FROM users 
        ORDER BY full_name
    """)
    
    all_users = cursor.fetchall()
    print(f"Total users in database: {len(all_users)}\n")
    if all_users:
        for user in all_users:
            role_str = f" [{user['role']}]" if user['role'] else ""
            print(f"  {user['user_id']:>12} | {user['full_name']:30} | @{user['telegram_username']}{role_str}")
    
    cursor.close()
    conn.close()
    print("\n✅ Database check complete")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
