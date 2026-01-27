#!/usr/bin/env python3
"""
Complete migration from Neon PostgreSQL to Local SQLite
Migrates ALL tables and data from production to local database
"""

import os
import sqlite3
import psycopg2
import psycopg2.extras
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
NEON_HOST = os.getenv('DB_HOST')
NEON_PORT = int(os.getenv('DB_PORT', 5432))
NEON_DB = os.getenv('DB_NAME')
NEON_USER = os.getenv('DB_USER')
NEON_PASSWORD = os.getenv('DB_PASSWORD')

PROJECT_ROOT = Path(__file__).parent
LOCAL_DB_PATH = PROJECT_ROOT / 'fitness_club.db'

print("=" * 80)
print("COMPLETE DATABASE MIGRATION: Neon PostgreSQL to Local SQLite")
print("=" * 80)
print(f"\nSource: Neon PostgreSQL ({NEON_HOST})")
print(f"Target: Local SQLite ({LOCAL_DB_PATH})")
print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")


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


def get_all_tables_from_neon(neon_conn):
    """Get list of all user tables from Neon"""
    cursor = neon_conn.cursor()
    cursor.execute("""
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_type = 'BASE TABLE'
        ORDER BY table_name
    """)
    tables = [row[0] for row in cursor.fetchall()]
    cursor.close()
    return sorted(tables)


def get_table_schema_from_neon(neon_conn, table_name):
    """Get CREATE TABLE statement for a table from Neon"""
    cursor = neon_conn.cursor()
    cursor.execute(f"""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = '{table_name}'
        ORDER BY ordinal_position
    """)
    columns = cursor.fetchall()
    cursor.close()
    return columns


def convert_pg_type_to_sqlite(pg_type):
    """Convert PostgreSQL data types to SQLite equivalents"""
    pg_type = pg_type.lower()
    
    if 'int' in pg_type:
        return 'INTEGER'
    elif 'bigint' in pg_type:
        return 'INTEGER'
    elif 'serial' in pg_type:
        return 'INTEGER'
    elif 'boolean' in pg_type:
        return 'BOOLEAN'
    elif 'decimal' in pg_type or 'numeric' in pg_type:
        return 'REAL'
    elif 'timestamp' in pg_type:
        return 'TIMESTAMP'
    elif 'date' in pg_type:
        return 'DATE'
    elif 'text' in pg_type:
        return 'TEXT'
    else:
        return 'TEXT'


def create_table_in_sqlite(local_conn, table_name, columns_info):
    """Create table in SQLite based on Neon schema"""
    col_defs = []
    for col_name, col_type, is_nullable, col_default in columns_info:
        sqlite_type = convert_pg_type_to_sqlite(col_type)
        
        col_def = f"  {col_name} {sqlite_type}"
        
        if is_nullable == 'NO':
            col_def += " NOT NULL"
        
        if col_default:
            col_def += f" DEFAULT {col_default}"
        
        col_defs.append(col_def)
    
    create_sql = f"CREATE TABLE IF NOT EXISTS {table_name} (\n" + ",\n".join(col_defs) + "\n)"
    
    cursor = local_conn.cursor()
    try:
        cursor.execute(create_sql)
        local_conn.commit()
        print(f"  [OK] {table_name}")
        return True
    except Exception as e:
        print(f"  [WARN] Error creating {table_name}: {e}")
        cursor.close()
        return False


def copy_table_data(neon_conn, local_conn, table_name):
    """Copy all data from Neon table to SQLite table"""
    try:
        neon_cursor = neon_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        neon_cursor.execute(f"SELECT * FROM {table_name}")
        rows = neon_cursor.fetchall()
        neon_cursor.close()
        
        if not rows:
            print(f"  [INFO] {table_name} - 0 records (empty)")
            return 0
        
        columns = list(rows[0].keys())
        placeholders = ",".join(["?" for _ in columns])
        insert_sql = f"INSERT INTO {table_name} ({','.join(columns)}) VALUES ({placeholders})"
        
        local_cursor = local_conn.cursor()
        for row in rows:
            values = tuple(row[col] for col in columns)
            local_cursor.execute(insert_sql, values)
        
        local_conn.commit()
        local_cursor.close()
        
        print(f"  [OK] {table_name} - {len(rows)} records")
        return len(rows)
    
    except Exception as e:
        print(f"  [ERROR] {table_name}: {e}")
        return 0


def migrate_all_tables():
    """Main migration function"""
    neon_conn = get_neon_connection()
    if not neon_conn:
        print("\n[ERROR] Migration aborted: Cannot connect to Neon")
        return False
    
    local_conn = get_local_connection()
    
    print("\n" + "=" * 80)
    print("STEP 1: Getting table list from Neon")
    print("=" * 80)
    
    tables = get_all_tables_from_neon(neon_conn)
    print(f"\n[INFO] Found {len(tables)} tables in Neon:")
    for table in tables:
        print(f"  - {table}")
    
    print("\n" + "=" * 80)
    print("STEP 2: Creating tables in Local SQLite")
    print("=" * 80 + "\n")
    
    created_tables = []
    for table_name in tables:
        schema = get_table_schema_from_neon(neon_conn, table_name)
        if create_table_in_sqlite(local_conn, table_name, schema):
            created_tables.append(table_name)
    
    print("\n" + "=" * 80)
    print("STEP 3: Copying data from Neon to Local SQLite")
    print("=" * 80 + "\n")
    
    total_records = 0
    for table_name in created_tables:
        records = copy_table_data(neon_conn, local_conn, table_name)
        total_records += records
    
    print("\n" + "=" * 80)
    print("STEP 4: Creating indexes")
    print("=" * 80 + "\n")
    
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_users_username ON users(telegram_username)",
        "CREATE INDEX IF NOT EXISTS idx_daily_logs_user_date ON daily_logs(user_id, log_date)",
        "CREATE INDEX IF NOT EXISTS idx_points_transactions_user ON points_transactions(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_shake_requests_user ON shake_requests(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_attendance_queue_user_date ON attendance_queue(user_id, log_date)",
        "CREATE INDEX IF NOT EXISTS idx_meal_photos_user ON meal_photos(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_fee_payments_user ON fee_payments(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_attendance_overrides_user ON attendance_overrides(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_attendance_overrides_admin ON attendance_overrides(admin_id)",
        "CREATE INDEX IF NOT EXISTS idx_store_items_name ON store_items(name)",
        "CREATE INDEX IF NOT EXISTS idx_store_items_hsn ON store_items(hsn)",
    ]
    
    cursor = local_conn.cursor()
    for idx_sql in indexes:
        try:
            cursor.execute(idx_sql)
            table_part = idx_sql.split('ON')[0].strip()
            print(f"  [OK] {table_part}")
        except Exception as e:
            print(f"  [WARN] Error: {e}")
    
    local_conn.commit()
    cursor.close()
    
    print("\n" + "=" * 80)
    print("STEP 5: Verifying migration")
    print("=" * 80 + "\n")
    
    cursor = local_conn.cursor()
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table'
    """)
    local_tables = sorted([row[0] for row in cursor.fetchall()])
    
    print(f"[INFO] Local SQLite now contains {len(local_tables)} tables:\n")
    for table in local_tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"  - {table:<40} {count:>10,} records")
    
    cursor.close()
    
    print("\n" + "=" * 80)
    print("MIGRATION SUMMARY")
    print("=" * 80)
    print(f"[OK] Tables migrated:  {len(created_tables)}")
    print(f"[OK] Total records:    {total_records:,}")
    print(f"[OK] Target database:  {LOCAL_DB_PATH}")
    print(f"[OK] Time:             {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n[SUCCESS] MIGRATION COMPLETE!\n")
    
    local_conn.close()
    neon_conn.close()
    
    return True


if __name__ == "__main__":
    try:
        success = migrate_all_tables()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n[WARN] Migration interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\n\n[ERROR] Unexpected error: {e}")
        exit(1)
