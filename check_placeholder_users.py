#!/usr/bin/env python3
"""
Diagnostic Script: Check for users with placeholder telegram_id

Identifies users who have placeholder telegram_id (>= 2147483647)
These users were imported but never sent /start to the bot.
"""
import pymysql
import sys
from dotenv import load_dotenv
import os

load_dotenv()

# Database connection
host = os.getenv('DB_HOST')
port = int(os.getenv('DB_PORT', 3306))
database = os.getenv('DB_NAME')
user = os.getenv('DB_USER')
password = os.getenv('DB_PASS')

print("=" * 70)
print("PLACEHOLDER TELEGRAM_ID DIAGNOSTIC")
print("=" * 70)
print(f"\nDatabase: {database}")
print(f"Host: {host}:{port}\n")

try:
    conn = pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        cursorclass=pymysql.cursors.DictCursor
    )
    cursor = conn.cursor()
    
    # Query users with placeholder IDs
    query = """
        SELECT 
            user_id,
            telegram_id,
            full_name,
            telegram_username,
            phone,
            role,
            fee_status,
            created_at
        FROM users 
        WHERE telegram_id >= 2147483647
        ORDER BY created_at DESC
    """
    
    cursor.execute(query)
    results = cursor.fetchall()
    
    print(f"{'='*70}")
    print(f"USERS WITH PLACEHOLDER TELEGRAM_ID (>= 2147483647)")
    print(f"{'='*70}\n")
    
    if not results:
        print("✅ No users with placeholder telegram_id found!")
        print("\nAll users have valid telegram_id values.")
    else:
        print(f"⚠️  Found {len(results)} user(s) with placeholder telegram_id:\n")
        
        for idx, user in enumerate(results, 1):
            print(f"{idx}. {user['full_name']}")
            print(f"   User ID: {user['user_id']}")
            print(f"   Telegram ID: {user['telegram_id']} (PLACEHOLDER)")
            print(f"   Username: @{user['telegram_username'] or 'N/A'}")
            print(f"   Phone: {user['phone'] or 'N/A'}")
            print(f"   Role: {user['role']}")
            print(f"   Fee Status: {user['fee_status']}")
            print(f"   Created: {user['created_at']}")
            print()
        
        print(f"{'='*70}")
        print("IMPACT:")
        print(f"{'='*70}")
        print("• These users will NOT appear in invoice user search")
        print("• Invoices cannot be created for these users until they connect")
        print("• Users must send /start to the bot to update their telegram_id")
        print()
        print(f"{'='*70}")
        print("ACTION REQUIRED:")
        print(f"{'='*70}")
        print("Contact these users and ask them to:")
        print("  1. Open Telegram")
        print("  2. Send /start to your bot")
        print("  3. Their telegram_id will be automatically updated")
        print()
    
    # Get total user count for context
    cursor.execute("SELECT COUNT(*) as total FROM users")
    total = cursor.fetchone()['total']
    
    print(f"{'='*70}")
    print(f"SUMMARY")
    print(f"{'='*70}")
    print(f"Total users in database: {total}")
    print(f"Users with placeholder ID: {len(results)}")
    print(f"Users with valid ID: {total - len(results)}")
    print(f"Percentage valid: {((total - len(results)) / total * 100):.1f}%")
    print()
    
    conn.close()
    sys.exit(0)
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    sys.exit(1)
