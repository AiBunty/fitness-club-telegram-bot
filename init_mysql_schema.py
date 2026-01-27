#!/usr/bin/env python3
"""
Initialize MySQL database schema by extracting schema from SQLite and converting to MySQL
"""
import sqlite3
import pymysql
from dotenv import load_dotenv
import os
from pathlib import Path

load_dotenv()

print("=" * 70)
print("MYSQL DATABASE SCHEMA INITIALIZATION")
print("=" * 70)

# SQLite connection to extract schema
sqlite_path = Path(__file__).parent / 'fitness_club.db'
sqlite_conn = sqlite3.connect(sqlite_path)
sqlite_cursor = sqlite_conn.cursor()

# MySQL connection
mysql_conn = pymysql.connect(
    host=os.getenv('DB_HOST'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASS'),
    database=os.getenv('DB_NAME'),
    port=int(os.getenv('DB_PORT')),
    charset='utf8mb4'
)
mysql_cursor = mysql_conn.cursor()

print(f"\n✓ Connected to MySQL: {os.getenv('DB_NAME')}")
print(f"✓ Connected to SQLite: {sqlite_path}")

# Type conversion mapping from SQLite to MySQL
def convert_sqlite_type_to_mysql(sqlite_type):
    sqlite_type = sqlite_type.upper()
    if 'INT' in sqlite_type or sqlite_type == 'INTEGER':
        if 'BIGINT' in sqlite_type:
            return 'BIGINT'
        return 'INT'
    elif 'TEXT' in sqlite_type:
        return 'VARCHAR(500)'  # Use VARCHAR instead of TEXT for better compatibility
    elif 'VARCHAR' in sqlite_type or 'CHAR' in sqlite_type:
        return sqlite_type
    elif 'REAL' in sqlite_type or 'FLOAT' in sqlite_type or 'DOUBLE' in sqlite_type:
        return 'DOUBLE'
    elif 'DECIMAL' in sqlite_type:
        return sqlite_type
    elif 'BOOL' in sqlite_type:
        return 'TINYINT(1)'
    elif 'DATE' in sqlite_type or 'TIME' in sqlite_type:
        return sqlite_type
    else:
        return 'VARCHAR(500)'

# Get all tables
sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
tables = [row[0] for row in sqlite_cursor.fetchall()]

print(f"\n📋 Found {len(tables)} tables to create")

created_count = 0
for table in tables:
    print(f"\n{'─' * 70}")
    print(f"Creating table: {table}")
    
    # Get table schema
    sqlite_cursor.execute(f"PRAGMA table_info({table})")
    columns = sqlite_cursor.fetchall()
    
    # Build CREATE TABLE statement for MySQL
    column_defs = []
    primary_keys = []
    
    for col in columns:
        col_id, col_name, col_type, not_null, default_val, is_pk = col
        
        mysql_type = convert_sqlite_type_to_mysql(col_type)
        
        col_def = f"`{col_name}` {mysql_type}"
        
        # Handle auto-increment for primary keys
        if is_pk and 'INT' in mysql_type.upper() and col_name.endswith('_id'):
            col_def += " AUTO_INCREMENT"
            primary_keys.append(col_name)
        elif is_pk:
            primary_keys.append(col_name)
        
        if not_null:
            col_def += " NOT NULL"
        
        if default_val is not None:
            if default_val.upper() in ('CURRENT_TIMESTAMP', 'NOW()'):
                col_def += " DEFAULT CURRENT_TIMESTAMP"
            elif default_val.isdigit() or default_val.replace('.', '', 1).isdigit() or default_val.replace('-', '', 1).isdigit():
                col_def += f" DEFAULT {default_val}"
            else:
                # Escape single quotes in default value and use single quotes
                escaped_val = default_val.replace("'", "''")
                col_def += f" DEFAULT '{escaped_val}'"
        
        column_defs.append(col_def)
    
    # Add primary key constraint
    if primary_keys:
        column_defs.append(f"PRIMARY KEY ({', '.join([f'`{pk}`' for pk in primary_keys])})")
    
    create_table_sql = f"CREATE TABLE IF NOT EXISTS `{table}` (\n  " + ",\n  ".join(column_defs) + "\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"
    
    try:
        mysql_cursor.execute(create_table_sql)
        mysql_conn.commit()
        print(f"  ✓ Created table: {table}")
        created_count += 1
    except Exception as e:
        print(f"  ✗ Error creating table {table}: {e}")
        print(f"  SQL: {create_table_sql[:200]}...")

# Close connections
sqlite_conn.close()
mysql_conn.close()

print(f"\n{'=' * 70}")
print(f"✅ SCHEMA INITIALIZATION COMPLETE!")
print(f"{'=' * 70}")
print(f"Tables created: {created_count}/{len(tables)}")
print(f"\nNext step: Run migrate_data.py to transfer data from SQLite to MySQL")
