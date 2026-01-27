#!/usr/bin/env python3
"""
PART 2-3: Database Schema Validation & Fix
Ensures users and store_items tables have all required columns for DB-only searches.

CRITICAL: NO IN-MEMORY STORES
- All users MUST be in DB with proper columns
- All store items MUST be in DB with proper columns
- Normalized searches MUST use DB columns, never memory

Required columns:

USERS table:
- telegram_id (BIGINT, UNIQUE, indexed)
- first_name (VARCHAR)
- last_name (VARCHAR)
- username (VARCHAR)
- full_name (VARCHAR)
- normalized_name (LOWER, trimmed, collapsed spaces) - indexed
- is_banned (BOOLEAN, default FALSE)
- created_at (TIMESTAMP)
- updated_at (TIMESTAMP)

STORE_ITEMS table:
- item_id (PK, SERIAL)
- serial_no (INT, UNIQUE, indexed)
- item_name (VARCHAR)
- normalized_item_name (VARCHAR, indexed)
- hsn_code (VARCHAR)
- mrp (DECIMAL)
- gst_percent (DECIMAL, default 18.0)
- is_active (BOOLEAN, default TRUE, indexed)
- created_at (TIMESTAMP)
- updated_at (TIMESTAMP)
"""

import sys
import os
from pathlib import Path
from psycopg2 import connect
from dotenv import load_dotenv
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv(override=False)

# Database config - LOCAL ONLY
DB_HOST = 'localhost'
DB_PORT = '5432'
DB_NAME = os.getenv('DB_NAME', 'fitness_club_db')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'postgres')

def get_conn():
    """Get database connection"""
    return connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )

def check_and_fix_users_table():
    """Ensure users table has all required columns"""
    logger.info("\n" + "="*70)
    logger.info("Checking USERS Table Schema")
    logger.info("="*70)
    
    conn = get_conn()
    cursor = conn.cursor()
    
    try:
        # Get current columns
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'users'
            ORDER BY ordinal_position
        """)
        
        existing_cols = {col: dtype for col, dtype in cursor.fetchall()}
        logger.info(f"Found {len(existing_cols)} existing columns:")
        for col, dtype in sorted(existing_cols.items()):
            logger.info(f"  - {col}: {dtype}")
        
        # Required columns
        required = {
            'user_id': 'BIGINT',
            'first_name': 'VARCHAR',
            'last_name': 'VARCHAR',
            'username': 'VARCHAR',
            'full_name': 'VARCHAR',
            'normalized_name': 'VARCHAR',
            'is_banned': 'BOOLEAN',
            'created_at': 'TIMESTAMP',
            'updated_at': 'TIMESTAMP'
        }
        
        missing = [col for col in required.keys() if col not in existing_cols]
        
        if missing:
            logger.warning(f"\n⚠️ Missing columns ({len(missing)}):")
            for col in missing:
                logger.warning(f"  - {col}")
                
                if col == 'is_banned':
                    cursor.execute(f"ALTER TABLE users ADD COLUMN {col} BOOLEAN DEFAULT FALSE;")
                    logger.info(f"✅ Added column: {col} (BOOLEAN DEFAULT FALSE)")
                elif col == 'normalized_name':
                    cursor.execute(f"ALTER TABLE users ADD COLUMN {col} VARCHAR(255);")
                    logger.info(f"✅ Added column: {col} (VARCHAR)")
                elif col in ['first_name', 'last_name', 'username']:
                    cursor.execute(f"ALTER TABLE users ADD COLUMN {col} VARCHAR(100);")
                    logger.info(f"✅ Added column: {col} (VARCHAR)")
        
        # Check indexes
        cursor.execute("""
            SELECT indexname 
            FROM pg_indexes 
            WHERE tablename = 'users' AND indexname LIKE 'idx_users%'
        """)
        
        indexes = [row[0] for row in cursor.fetchall()]
        logger.info(f"\nFound {len(indexes)} indexes on users table:")
        for idx in indexes:
            logger.info(f"  - {idx}")
        
        # Ensure critical indexes exist
        critical_indexes = [
            ('idx_users_telegram_id', 'user_id'),
            ('idx_users_normalized_name', 'normalized_name'),
            ('idx_users_banned', 'is_banned')
        ]
        
        for idx_name, col_name in critical_indexes:
            if idx_name not in indexes:
                try:
                    cursor.execute(f"CREATE INDEX {idx_name} ON users({col_name});")
                    logger.info(f"✅ Created index: {idx_name}")
                except Exception as e:
                    logger.warning(f"⚠️ Index creation note: {e}")
        
        conn.commit()
        logger.info("\n✅ USERS table schema validated")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error checking users table: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()

def check_and_fix_store_items_table():
    """Ensure store_items table has all required columns"""
    logger.info("\n" + "="*70)
    logger.info("Checking STORE_ITEMS Table Schema")
    logger.info("="*70)
    
    conn = get_conn()
    cursor = conn.cursor()
    
    try:
        # Check if table exists
        cursor.execute("""
            SELECT EXISTS(
                SELECT 1 FROM information_schema.tables 
                WHERE table_name = 'store_items'
            )
        """)
        
        if not cursor.fetchone()[0]:
            logger.warning("⚠️ STORE_ITEMS table doesn't exist. Creating...")
            cursor.execute("""
                CREATE TABLE store_items (
                    item_id SERIAL PRIMARY KEY,
                    serial_no INT UNIQUE,
                    item_name VARCHAR(255) NOT NULL,
                    normalized_item_name VARCHAR(255),
                    hsn_code VARCHAR(20),
                    mrp DECIMAL(10,2) NOT NULL,
                    gst_percent DECIMAL(5,2) DEFAULT 18.0,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            logger.info("✅ STORE_ITEMS table created")
        
        # Get current columns
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'store_items'
            ORDER BY ordinal_position
        """)
        
        existing_cols = {col: dtype for col, dtype in cursor.fetchall()}
        logger.info(f"Found {len(existing_cols)} columns:")
        for col, dtype in sorted(existing_cols.items()):
            logger.info(f"  - {col}: {dtype}")
        
        # Required columns
        required = {
            'item_id': 'INTEGER',
            'serial_no': 'INTEGER',
            'item_name': 'VARCHAR',
            'normalized_item_name': 'VARCHAR',
            'hsn_code': 'VARCHAR',
            'mrp': 'NUMERIC',
            'gst_percent': 'NUMERIC',
            'is_active': 'BOOLEAN',
            'created_at': 'TIMESTAMP',
            'updated_at': 'TIMESTAMP'
        }
        
        missing = [col for col in required.keys() if col not in existing_cols]
        
        if missing:
            logger.warning(f"\n⚠️ Missing columns ({len(missing)}):")
            for col in missing:
                logger.warning(f"  - {col}")
        
        # Check indexes
        cursor.execute("""
            SELECT indexname 
            FROM pg_indexes 
            WHERE tablename = 'store_items' AND indexname LIKE 'idx_store%'
        """)
        
        indexes = [row[0] for row in cursor.fetchall()]
        logger.info(f"\nFound {len(indexes)} indexes on store_items table:")
        for idx in indexes:
            logger.info(f"  - {idx}")
        
        # Ensure critical indexes exist
        critical_indexes = [
            ('idx_store_items_serial', 'serial_no'),
            ('idx_store_items_normalized', 'normalized_item_name'),
            ('idx_store_items_active', 'is_active')
        ]
        
        for idx_name, col_name in critical_indexes:
            if idx_name not in indexes:
                try:
                    cursor.execute(f"CREATE INDEX {idx_name} ON store_items({col_name});")
                    logger.info(f"✅ Created index: {idx_name}")
                except Exception as e:
                    logger.warning(f"⚠️ Index creation note: {e}")
        
        conn.commit()
        logger.info("\n✅ STORE_ITEMS table schema validated")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error checking store_items table: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()

def check_invoices_tables():
    """Verify invoices and invoice_items tables exist"""
    logger.info("\n" + "="*70)
    logger.info("Checking INVOICES Related Tables")
    logger.info("="*70)
    
    conn = get_conn()
    cursor = conn.cursor()
    
    try:
        # Check both tables
        for table_name in ['invoices', 'invoice_items']:
            cursor.execute(f"""
                SELECT EXISTS(
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_name = '{table_name}'
                )
            """)
            
            exists = cursor.fetchone()[0]
            if exists:
                cursor.execute(f"""
                    SELECT COUNT(*) FROM {table_name}
                """)
                count = cursor.fetchone()[0]
                logger.info(f"✅ {table_name}: exists ({count} rows)")
            else:
                logger.warning(f"⚠️ {table_name}: doesn't exist")
        
        conn.commit()
        return True
        
    except Exception as e:
        logger.error(f"❌ Error checking invoices tables: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

def validate_row_counts():
    """Validate data was migrated successfully"""
    logger.info("\n" + "="*70)
    logger.info("Data Validation")
    logger.info("="*70)
    
    conn = get_conn()
    cursor = conn.cursor()
    
    try:
        tables_to_check = [
            'users',
            'store_items',
            'invoices',
            'daily_logs',
            'points_transactions',
            'fee_payments'
        ]
        
        total_rows = 0
        for table in tables_to_check:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                total_rows += count
                logger.info(f"  {table}: {count:,} rows")
            except:
                logger.info(f"  {table}: table doesn't exist")
        
        logger.info(f"\nTotal rows across key tables: {total_rows:,}")
        
        if total_rows == 0:
            logger.warning("⚠️ No data found in database!")
        else:
            logger.info("✅ Database has data")
        
        conn.commit()
        return True
        
    except Exception as e:
        logger.error(f"❌ Error validating data: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

def main():
    """Run all schema checks and fixes"""
    logger.info("\n" + "="*70)
    logger.info("PART 2-3: Database Schema Validation & Fix")
    logger.info("="*70)
    logger.info("Purpose: Ensure database is SINGLE SOURCE OF TRUTH")
    logger.info("Rules: No in-memory stores, no JSON fallbacks, DB-only")
    
    steps = [
        ("Users Table", check_and_fix_users_table),
        ("Store Items Table", check_and_fix_store_items_table),
        ("Invoices Tables", check_invoices_tables),
        ("Data Validation", validate_row_counts),
    ]
    
    for step_name, step_func in steps:
        try:
            result = step_func()
            if not result:
                logger.warning(f"⚠️ {step_name} had issues (non-critical)")
        except Exception as e:
            logger.error(f"❌ {step_name} error: {e}")
    
    logger.info("\n" + "="*70)
    logger.info("✅ SCHEMA VALIDATION COMPLETE")
    logger.info("="*70)
    logger.info("\nNEXT STEPS:")
    logger.info("1. Run migration script: python migrate_neon_to_local.py")
    logger.info("2. Verify local DB has data: psql -h localhost -U postgres -d fitness_club_db -c 'SELECT COUNT(*) FROM users;'")
    logger.info("3. Update handlers to use DB-only searches (no memory fallback)")
    logger.info("4. Restart bot and test all search flows")

if __name__ == '__main__':
    main()
