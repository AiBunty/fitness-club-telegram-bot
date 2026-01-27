#!/usr/bin/env python3
"""
Migrate users from JSON registry to SQLite database
Populates the users table with data from users.json
"""

import json
import sqlite3
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent
LOCAL_DB_PATH = PROJECT_ROOT / 'fitness_club.db'
USERS_JSON = PROJECT_ROOT / 'data' / 'users.json'

print("\n" + "=" * 80)
print("USER DATA MIGRATION: JSON to SQLite")
print("=" * 80)
print(f"\nSource: {USERS_JSON}")
print(f"Target: {LOCAL_DB_PATH}")
print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# Load users from JSON
if not USERS_JSON.exists():
    print(f"[ERROR] Users file not found: {USERS_JSON}")
    exit(1)

try:
    with open(USERS_JSON, 'r', encoding='utf-8') as f:
        users_data = json.load(f)
    print(f"[OK] Loaded {len(users_data)} users from JSON")
except Exception as e:
    print(f"[ERROR] Failed to load JSON: {e}")
    exit(1)

# Connect to SQLite
try:
    conn = sqlite3.connect(str(LOCAL_DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    print(f"[OK] Connected to SQLite database")
except Exception as e:
    print(f"[ERROR] Failed to connect to database: {e}")
    exit(1)

# Check if users table exists and has the right columns
try:
    cursor.execute("PRAGMA table_info(users)")
    columns = cursor.fetchall()
    if not columns:
        print("[ERROR] Users table does not exist or is empty")
        exit(1)
    column_names = [col[1] for col in columns]
    print(f"[OK] Users table exists with {len(column_names)} columns")
except Exception as e:
    print(f"[ERROR] Failed to check table: {e}")
    exit(1)

# Migrate users
migrated = 0
skipped = 0

print("\n" + "=" * 80)
print("MIGRATING USERS")
print("=" * 80 + "\n")

for user_data in users_data:
    try:
        user_id = user_data.get('user_id') or user_data.get('telegram_id')
        full_name = user_data.get('full_name', f"User {user_id}")
        username = user_data.get('username', '').lstrip('@') if user_data.get('username') else None
        phone = user_data.get('phone')
        age = user_data.get('age')
        
        # Check if user already exists
        cursor.execute("SELECT COUNT(*) FROM users WHERE user_id = ?", (user_id,))
        if cursor.fetchone()[0] > 0:
            print(f"  [SKIP] User {user_id} already exists")
            skipped += 1
            continue
        
        # Insert user
        insert_sql = """
            INSERT INTO users (
                user_id, telegram_username, full_name, phone, age,
                role, fee_status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        cursor.execute(insert_sql, (
            user_id,
            username,
            full_name,
            phone,
            age,
            'member',  # default role
            'unpaid',  # default fee_status
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))
        
        print(f"  [OK] User {user_id}: {full_name}")
        migrated += 1
        
    except Exception as e:
        print(f"  [ERROR] Failed to migrate user {user_id}: {e}")

conn.commit()

# Verify
print("\n" + "=" * 80)
print("VERIFICATION")
print("=" * 80 + "\n")

cursor.execute("SELECT COUNT(*) FROM users")
total_users = cursor.fetchone()[0]
print(f"[OK] Total users in database: {total_users}")

cursor.execute("SELECT user_id, full_name, telegram_username FROM users ORDER BY user_id")
users = cursor.fetchall()
if users:
    print(f"\n[INFO] Users in database:")
    for user in users:
        print(f"  - ID: {user[0]:<15} Name: {user[1]:<25} Username: {user[2] or 'N/A'}")

cursor.close()
conn.close()

print("\n" + "=" * 80)
print("MIGRATION SUMMARY")
print("=" * 80)
print(f"[OK] Users migrated: {migrated}")
print(f"[OK] Users skipped:  {skipped}")
print(f"[OK] Total in DB:    {total_users}")
print(f"\n[SUCCESS] USER MIGRATION COMPLETE!\n")
