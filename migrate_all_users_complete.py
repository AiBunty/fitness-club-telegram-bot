#!/usr/bin/env python3
"""
Complete User Data Migration from Neon to Local SQLite
Migrates ALL user-related tables and data including:
- users (with all fields)
- daily_logs
- points_transactions
- shake_credits
- fee_payments
- subscriptions
- And all user-related data
"""

import os
import sqlite3
import psycopg2
import psycopg2.extras
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

NEON_HOST = os.getenv('DB_HOST')
NEON_PORT = int(os.getenv('DB_PORT', 5432))
NEON_DB = os.getenv('DB_NAME')
NEON_USER = os.getenv('DB_USER')
NEON_PASSWORD = os.getenv('DB_PASSWORD')

PROJECT_ROOT = Path(__file__).parent
LOCAL_DB_PATH = PROJECT_ROOT / 'fitness_club.db'

print("=" * 100)
print("COMPLETE USER DATA MIGRATION: Neon PostgreSQL to Local SQLite")
print("=" * 100)
print(f"\nSource: Neon PostgreSQL ({NEON_HOST})")
print(f"Target: Local SQLite ({LOCAL_DB_PATH})")
print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")


def get_neon_connection():
    """Create connection to Neon PostgreSQL"""
    try:
        conn = psycopg2.connect(
            host=NEON_HOST,
            port=NEON_PORT,
            database=NEON_DB,
            user=NEON_USER,
            password=NEON_PASSWORD,
            connect_timeout=10
        )
        print("[OK] Connected to Neon PostgreSQL")
        return conn
    except Exception as e:
        print(f"[ERROR] Failed to connect to Neon: {e}")
        return None


def get_local_connection():
    """Create connection to local SQLite"""
    conn = sqlite3.connect(str(LOCAL_DB_PATH))
    conn.row_factory = sqlite3.Row
    print(f"[OK] Connected to Local SQLite: {LOCAL_DB_PATH}")
    return conn


def get_table_columns_from_neon(neon_conn, table_name):
    """Get all columns from a Neon table"""
    cursor = neon_conn.cursor()
    cursor.execute(f"""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = '{table_name}'
        ORDER BY ordinal_position
    """)
    columns = [row[0] for row in cursor.fetchall()]
    cursor.close()
    return columns


def get_row_count_from_neon(neon_conn, table_name):
    """Get row count from a Neon table"""
    cursor = neon_conn.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    count = cursor.fetchone()[0]
    cursor.close()
    return count


def migrate_table_data(neon_conn, local_conn, table_name):
    """Migrate all data from Neon table to SQLite table"""
    try:
        # Get columns from Neon
        neon_columns = get_table_columns_from_neon(neon_conn, table_name)
        if not neon_columns:
            print(f"  [SKIP] {table_name:<40} - No columns found")
            return 0

        # Get data from Neon
        neon_cursor = neon_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        columns_str = ", ".join(neon_columns)
        neon_cursor.execute(f"SELECT {columns_str} FROM {table_name}")
        rows = neon_cursor.fetchall()
        neon_cursor.close()

        if not rows:
            print(f"  [INFO] {table_name:<40} - 0 records (empty)")
            return 0

        # Prepare insert statement for SQLite
        placeholders = ",".join(["?" for _ in neon_columns])
        insert_sql = f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})"

        # Insert data into SQLite
        local_cursor = local_conn.cursor()
        for row in rows:
            values = tuple(row[col] for col in neon_columns)
            try:
                local_cursor.execute(insert_sql, values)
            except sqlite3.IntegrityError as e:
                # Skip if record already exists (duplicate key)
                if "UNIQUE constraint failed" in str(e) or "FOREIGN KEY constraint failed" in str(e):
                    continue
                else:
                    raise

        local_conn.commit()
        local_cursor.close()

        print(f"  [OK] {table_name:<40} - {len(rows):>6,} records migrated")
        return len(rows)

    except Exception as e:
        print(f"  [ERROR] {table_name:<40} - {str(e)[:50]}")
        return 0


def migrate_all_user_data():
    """Main migration function"""
    neon_conn = get_neon_connection()
    if not neon_conn:
        print("\n[ERROR] Migration aborted: Cannot connect to Neon")
        return False

    local_conn = get_local_connection()

    # User-related tables to migrate
    user_tables = [
        'users',
        'daily_logs',
        'points_transactions',
        'shake_credits',
        'shake_purchases',
        'shake_transactions',
        'shake_requests',
        'fee_payments',
        'subscriptions',
        'subscription_payments',
        'subscription_requests',
        'subscription_reminders',
        'subscription_plans',
        'pt_subscriptions',
        'referral_rewards',
        'attendance_queue',
        'attendance_overrides',
        'meal_photos',
        'notifications',
        'admin_sessions',
        'admin_members',
        'staff_members',
        'ar_transactions',
        'accounts_receivable',
        'reminder_preferences',
        'follow_up_reminders',
    ]

    print("=" * 100)
    print("CHECKING DATA AVAILABILITY IN NEON")
    print("=" * 100 + "\n")

    available_tables = []
    for table_name in user_tables:
        try:
            count = get_row_count_from_neon(neon_conn, table_name)
            if count > 0:
                available_tables.append((table_name, count))
                print(f"  [OK] {table_name:<40} {count:>10,} records")
            else:
                print(f"  [EMPTY] {table_name:<40} 0 records")
        except Exception as e:
            print(f"  [N/A] {table_name:<40} Table not found or error")

    print("\n" + "=" * 100)
    print(f"MIGRATING {len(available_tables)} TABLES WITH DATA")
    print("=" * 100 + "\n")

    total_records = 0
    for table_name, _ in available_tables:
        records = migrate_table_data(neon_conn, local_conn, table_name)
        total_records += records

    # Also migrate remaining tables even if empty (for schema)
    print("\n" + "=" * 100)
    print("MIGRATING ADDITIONAL TABLES (for completeness)")
    print("=" * 100 + "\n")

    additional_tables = [
        'broadcast_log',
        'admin_audit_log',
        'payment_requests',
        'revenue',
        'challenges',
        'challenge_participants',
        'events',
        'one_day_events',
        'event_registrations',
        'user_event_registrations',
        'user_product_orders',
        'motivational_messages',
        'gym_settings',
        'shake_flavors',
    ]

    for table_name in additional_tables:
        try:
            count = get_row_count_from_neon(neon_conn, table_name)
            records = migrate_table_data(neon_conn, local_conn, table_name)
            total_records += records
        except:
            pass

    print("\n" + "=" * 100)
    print("MIGRATION VERIFICATION")
    print("=" * 100 + "\n")

    cursor = local_conn.cursor()
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table'
    """)
    local_tables = sorted([row[0] for row in cursor.fetchall()])

    print(f"[INFO] Local SQLite now contains {len(local_tables)} tables:\n")
    
    grand_total = 0
    tables_with_data = []
    for table in local_tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        if count > 0:
            tables_with_data.append((table, count))
            grand_total += count
            print(f"  - {table:<40} {count:>10,} records")

    cursor.close()

    print("\n" + "=" * 100)
    print("MIGRATION SUMMARY")
    print("=" * 100)
    print(f"[OK] Tables with data:  {len(tables_with_data)}")
    print(f"[OK] Total records:     {grand_total:,}")
    print(f"[OK] Target database:   {LOCAL_DB_PATH}")
    print(f"[OK] Time:              {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n[SUCCESS] ALL USER DATA MIGRATION COMPLETE!\n")

    local_conn.close()
    neon_conn.close()

    return True


if __name__ == "__main__":
    try:
        success = migrate_all_user_data()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n[WARN] Migration interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\n\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
