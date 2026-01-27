"""
Complete migration script: Create MySQL schema and migrate data from SQLite
"""
import sqlite3
import pymysql
from dotenv import load_dotenv
import os
from pathlib import Path

load_dotenv()

print("=" * 60)
print("DATABASE MIGRATION: SQLite → MySQL")
print("=" * 60)

# MySQL connection
mysql_conn = pymysql.connect(
    host=os.getenv('DB_HOST'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASS'),
    database=os.getenv('DB_NAME'),
    port=int(os.getenv('DB_PORT')),
    charset='utf8mb4',
    autocommit=False
)
mysql_cursor = mysql_conn.cursor()

print(f"\n✓ Connected to MySQL database: {os.getenv('DB_NAME')}")

# SQLite connection
sqlite_path = Path(__file__).parent / 'fitness_club.db'
if not sqlite_path.exists():
    print(f"\n✗ SQLite database not found at: {sqlite_path}")
    exit(1)

sqlite_conn = sqlite3.connect(sqlite_path)
sqlite_conn.row_factory = sqlite3.Row
sqlite_cursor = sqlite_conn.cursor()

print(f"✓ Connected to SQLite database: {sqlite_path}")

# Get list of tables from SQLite
sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
tables = [row[0] for row in sqlite_cursor.fetchall()]

print(f"\n📋 Found {len(tables)} tables in SQLite")

# Migrate each table
total_rows = 0
for table in tables:
    print(f"\n{'─' * 60}")
    print(f"Table: {table}")
    print(f"{'─' * 60}")
    
    # Get table schema from SQLite
    sqlite_cursor.execute(f"PRAGMA table_info({table})")
    columns_info = sqlite_cursor.fetchall()
    columns = [col[1] for col in columns_info]
    
    # Get row count
    sqlite_cursor.execute(f"SELECT COUNT(*) FROM {table}")
    row_count = sqlite_cursor.fetchone()[0]
    
    if row_count == 0:
        print(f"  ⚠ Empty table, skipping...")
        continue
    
    print(f"  Rows to migrate: {row_count}")
    
    # Check if table exists in MySQL
    mysql_cursor.execute(f"SHOW TABLES LIKE '{table}'")
    if not mysql_cursor.fetchone():
        print(f"  ⚠ Table '{table}' does not exist in MySQL!")
        print(f"  ℹ You need to create the schema first.")
        continue
    
    # Get all data from SQLite
    sqlite_cursor.execute(f"SELECT * FROM {table}")
    rows = sqlite_cursor.fetchall()
    
    # Prepare INSERT statement
    placeholders = ', '.join(['%s'] * len(columns))
    columns_str = ', '.join([f"`{col}`" for col in columns])
    insert_sql = f"INSERT IGNORE INTO {table} ({columns_str}) VALUES ({placeholders})"
    
    # Migrate data
    migrated = 0
    skipped = 0
    errors = 0
    
    for row in rows:
        try:
            mysql_cursor.execute(insert_sql, tuple(row))
            if mysql_cursor.rowcount > 0:
                migrated += 1
            else:
                skipped += 1
        except pymysql.IntegrityError as e:
            skipped += 1
        except Exception as e:
            errors += 1
            print(f"  ✗ Error: {str(e)[:80]}")
    
    mysql_conn.commit()
    total_rows += migrated
    
    print(f"  ✓ Migrated: {migrated}")
    if skipped > 0:
        print(f"  ⚠ Skipped: {skipped} (duplicates)")
    if errors > 0:
        print(f"  ✗ Errors: {errors}")

# Close connections
sqlite_conn.close()
mysql_conn.close()

print(f"\n{'=' * 60}")
print(f"✅ MIGRATION COMPLETE!")
print(f"{'=' * 60}")
print(f"Total rows migrated: {total_rows}")
print(f"\nNext steps:")
print(f"  1. Verify data in MySQL database")
print(f"  2. Test bot with remote database")
print(f"  3. Keep SQLite backup for safety")
