"""
Migration script to transfer data from SQLite to MySQL
"""
import sqlite3
import pymysql
from dotenv import load_dotenv
import os
from pathlib import Path

load_dotenv()

# SQLite connection
sqlite_path = Path(__file__).parent / 'fitness_club.db'
sqlite_conn = sqlite3.connect(sqlite_path)
sqlite_conn.row_factory = sqlite3.Row

# MySQL connection
mysql_conn = pymysql.connect(
    host=os.getenv('DB_HOST'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASS'),
    database=os.getenv('DB_NAME'),
    port=int(os.getenv('DB_PORT')),
    charset='utf8mb4'
)

print("✓ Connected to both databases")

# Get list of tables from SQLite
sqlite_cursor = sqlite_conn.cursor()
sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
tables = [row[0] for row in sqlite_cursor.fetchall()]

print(f"\nFound {len(tables)} tables to migrate: {', '.join(tables)}")

# For each table, copy data
mysql_cursor = mysql_conn.cursor()

for table in tables:
    print(f"\n📋 Migrating table: {table}")
    
    # Get table schema from SQLite
    sqlite_cursor.execute(f"PRAGMA table_info({table})")
    columns_info = sqlite_cursor.fetchall()
    columns = [col[1] for col in columns_info]
    
    # Get all data from SQLite
    sqlite_cursor.execute(f"SELECT * FROM {table}")
    rows = sqlite_cursor.fetchall()
    
    if not rows:
        print(f"   ⚠ Table {table} is empty, skipping...")
        continue
    
    print(f"   Found {len(rows)} rows")
    
    # Create INSERT statement for MySQL
    placeholders = ', '.join(['%s'] * len(columns))
    columns_str = ', '.join([f"`{col}`" for col in columns])
    insert_sql = f"INSERT INTO {table} ({columns_str}) VALUES ({placeholders})"
    
    # Insert data into MySQL
    migrated = 0
    for row in rows:
        try:
            mysql_cursor.execute(insert_sql, tuple(row))
            migrated += 1
        except pymysql.IntegrityError as e:
            # Skip if already exists (duplicate key)
            if 'Duplicate entry' in str(e):
                print(f"   ⚠ Skipping duplicate row in {table}")
            else:
                print(f"   ✗ Error inserting row: {e}")
        except Exception as e:
            print(f"   ✗ Error inserting row: {e}")
    
    mysql_conn.commit()
    print(f"   ✓ Migrated {migrated} rows to {table}")

print("\n✅ Migration complete!")

# Close connections
sqlite_conn.close()
mysql_conn.close()

print("\nNext steps:")
print("1. Verify data in MySQL database")
print("2. Test bot with remote database")
print("3. Keep SQLite backup for safety")
