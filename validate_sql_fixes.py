#!/usr/bin/env python3
"""
Database Schema Validation & Fixes
Checks and fixes user_id type issues that cause 'Chat not found' errors
"""

import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.database.connection import execute_query

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def check_user_id_type():
    """Check if user_id column is BIGINT (needed for Telegram IDs)"""
    logger.info("=" * 70)
    logger.info("DATABASE SCHEMA VALIDATION")
    logger.info("=" * 70)
    
    try:
        # Get column information
        result = execute_query("DESCRIBE users", fetch_one=False)
        
        if not result:
            logger.error("❌ Failed to query users table")
            return False
        
        logger.info(f"\n✅ Users table structure:")
        user_id_type = None
        
        for row in result:
            if isinstance(row, dict):
                col_name = row.get('Field') or row.get('field')
                col_type = row.get('Type') or row.get('type')
            else:
                col_name = row[0]
                col_type = row[1]
            
            if col_name == 'user_id':
                user_id_type = col_type
                logger.info(f"   user_id: {col_type}")
            else:
                logger.info(f"   {col_name}: {col_type}")
        
        # Validate
        logger.info("\n" + "=" * 70)
        logger.info("VALIDATION RESULTS")
        logger.info("=" * 70)
        
        if user_id_type:
            if 'BIGINT' in user_id_type.upper():
                logger.info("✅ user_id is BIGINT - Correct!")
                logger.info("   Telegram IDs (up to 10 digits) will NOT overflow")
                return True
            else:
                logger.error(f"❌ user_id is {user_id_type} - WRONG!")
                logger.error("   This causes 'Chat not found' errors for large Telegram IDs")
                logger.error("\n🔧 FIX: Run this SQL command in MySQL:")
                logger.error("   ALTER TABLE users MODIFY COLUMN user_id BIGINT NOT NULL;")
                return False
        else:
            logger.error("❌ user_id column not found in users table")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error checking schema: {e}")
        logger.error("\nMake sure your database connection is configured in .env")
        return False

def fix_user_id_type():
    """Attempt to fix user_id type if needed"""
    logger.info("\n" + "=" * 70)
    logger.info("ATTEMPTING DATABASE FIX")
    logger.info("=" * 70)
    
    try:
        # Check current type first
        result = execute_query("DESCRIBE users", fetch_one=False)
        user_id_type = None
        
        for row in result:
            if isinstance(row, dict):
                if row.get('Field') == 'user_id':
                    user_id_type = row.get('Type')
            else:
                if row[0] == 'user_id':
                    user_id_type = row[1]
        
        if user_id_type and 'BIGINT' not in user_id_type.upper():
            logger.info(f"Current type: {user_id_type}")
            logger.info("Attempting to convert to BIGINT...")
            
            execute_query(
                "ALTER TABLE users MODIFY COLUMN user_id BIGINT NOT NULL",
                fetch_one=False
            )
            
            logger.info("✅ Successfully converted user_id to BIGINT")
            return True
        else:
            logger.info("✅ user_id is already BIGINT, no fix needed")
            return True
            
    except Exception as e:
        logger.error(f"❌ Failed to fix user_id type: {e}")
        logger.error("Manual fix required - Run in MySQL:")
        logger.error("  ALTER TABLE users MODIFY COLUMN user_id BIGINT NOT NULL;")
        return False

def check_all_sql_compatibility():
    """Verify all SQL compatibility fixes"""
    logger.info("\n" + "=" * 70)
    logger.info("SQL COMPATIBILITY CHECK")
    logger.info("=" * 70)
    
    files_to_check = {
        "src/invoices_v2/search_db_only.py": "::BIGINT",
        "src/invoices_v2/search_items_db_only.py": "::INT",
        "src/handlers/delete_user_db_only.py": "::BIGINT",
    }
    
    all_fixed = True
    
    for file_path, pattern in files_to_check.items():
        full_path = project_root / file_path
        
        if full_path.exists():
            with open(full_path, 'r') as f:
                content = f.read()
            
            if pattern in content:
                logger.error(f"❌ {file_path}: Still contains {pattern}")
                all_fixed = False
            else:
                logger.info(f"✅ {file_path}: PostgreSQL syntax removed")
        else:
            logger.warning(f"⏭️  {file_path}: File not found")
    
    return all_fixed

if __name__ == '__main__':
    # Run all checks
    schema_ok = check_user_id_type()
    sql_ok = check_all_sql_compatibility()
    
    logger.info("\n" + "=" * 70)
    logger.info("SUMMARY")
    logger.info("=" * 70)
    
    if not schema_ok:
        logger.info("\n🔧 Attempting automatic database fix...")
        schema_ok = fix_user_id_type()
    
    if schema_ok and sql_ok:
        logger.info("\n✅ ALL CHECKS PASSED - System ready for invoice operations!")
        sys.exit(0)
    else:
        logger.info("\n⚠️  ISSUES FOUND - See details above")
        sys.exit(1)
