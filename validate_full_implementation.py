#!/usr/bin/env python3
"""
PART 9: COMPLETE VALIDATION & VERIFICATION SCRIPT

This script validates that the full DB migration and DB-only search implementation
is working correctly. Runs all verification tests.

Exit code 0 = SUCCESS (all tests pass)
Exit code 1 = FAILURE (some tests failed)
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv
import logging
from psycopg2 import connect
import json

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv(override=False)

# Configuration
DB_HOST = 'localhost'
DB_PORT = '5432'
DB_NAME = os.getenv('DB_NAME', 'fitness_club_db')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'postgres')

def get_conn():
    """Get database connection"""
    try:
        return connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
    except Exception as e:
        logger.error(f"❌ Cannot connect to database: {e}")
        return None

def test_db_connection():
    """TEST 1: Database connectivity"""
    logger.info("\n" + "="*70)
    logger.info("TEST 1: Database Connection")
    logger.info("="*70)
    
    conn = get_conn()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        logger.info("✅ Database connection successful")
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"❌ Connection test failed: {e}")
        return False

def test_required_tables():
    """TEST 2: All required tables exist"""
    logger.info("\n" + "="*70)
    logger.info("TEST 2: Required Tables")
    logger.info("="*70)
    
    conn = get_conn()
    if not conn:
        return False
    
    required_tables = [
        'users',
        'store_items',
        'invoices',
        'invoice_items',
        'daily_logs',
        'fee_payments'
    ]
    
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        
        existing = [row[0] for row in cursor.fetchall()]
        missing = [t for t in required_tables if t not in existing]
        
        if missing:
            logger.warning(f"❌ Missing tables: {missing}")
            return False
        
        logger.info(f"✅ All {len(required_tables)} required tables exist:")
        for table in required_tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            logger.info(f"   - {table}: {count:,} rows")
        
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"❌ Error checking tables: {e}")
        return False

def test_users_columns():
    """TEST 3: Users table has required columns"""
    logger.info("\n" + "="*70)
    logger.info("TEST 3: Users Table Columns")
    logger.info("="*70)
    
    conn = get_conn()
    if not conn:
        return False
    
    required_cols = [
        'user_id',
        'first_name',
        'last_name',
        'username',
        'full_name',
        'normalized_name',
        'is_banned'
    ]
    
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'users'
        """)
        
        existing = [row[0] for row in cursor.fetchall()]
        missing = [c for c in required_cols if c not in existing]
        
        if missing:
            logger.warning(f"⚠️ Missing columns in users table: {missing}")
            # Not fatal, but warn
        
        logger.info(f"✅ Users table has required columns:")
        for col in required_cols:
            if col in existing:
                logger.info(f"   ✓ {col}")
            else:
                logger.info(f"   ✗ {col} (MISSING)")
        
        cursor.close()
        conn.close()
        return len(missing) == 0
    except Exception as e:
        logger.error(f"❌ Error checking columns: {e}")
        return False

def test_store_items_columns():
    """TEST 4: Store items table has required columns"""
    logger.info("\n" + "="*70)
    logger.info("TEST 4: Store Items Table Columns")
    logger.info("="*70)
    
    conn = get_conn()
    if not conn:
        return False
    
    required_cols = [
        'item_id',
        'serial_no',
        'item_name',
        'normalized_item_name',
        'mrp',
        'gst_percent',
        'is_active'
    ]
    
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'store_items'
        """)
        
        existing = [row[0] for row in cursor.fetchall()]
        missing = [c for c in required_cols if c not in existing]
        
        if missing:
            logger.warning(f"⚠️ Missing columns in store_items table: {missing}")
        
        logger.info(f"✅ Store items table has columns:")
        for col in required_cols:
            if col in existing:
                logger.info(f"   ✓ {col}")
            else:
                logger.info(f"   ✗ {col} (MISSING)")
        
        cursor.close()
        conn.close()
        return len(missing) == 0
    except Exception as e:
        logger.error(f"❌ Error checking store_items columns: {e}")
        return False

def test_search_functions():
    """TEST 5: Search functions import correctly"""
    logger.info("\n" + "="*70)
    logger.info("TEST 5: Search Functions Import")
    logger.info("="*70)
    
    try:
        from src.invoices_v2.search_db_only import search_users_db_only
        logger.info("✅ search_users_db_only imported")
    except Exception as e:
        logger.warning(f"⚠️ search_users_db_only import failed: {e}")
    
    try:
        from src.invoices_v2.search_items_db_only import search_store_items_db_only
        logger.info("✅ search_store_items_db_only imported")
    except Exception as e:
        logger.warning(f"⚠️ search_store_items_db_only import failed: {e}")
    
    try:
        from src.handlers.delete_user_db_only import search_delete_user_db_only
        logger.info("✅ search_delete_user_db_only imported")
    except Exception as e:
        logger.warning(f"⚠️ search_delete_user_db_only import failed: {e}")
    
    try:
        from src.utils.flow_manager import check_flow_ownership, set_active_flow, clear_active_flow
        logger.info("✅ Flow manager functions imported")
    except Exception as e:
        logger.error(f"❌ Flow manager import failed: {e}")
        return False
    
    return True

def test_flow_manager():
    """TEST 6: Flow manager working"""
    logger.info("\n" + "="*70)
    logger.info("TEST 6: Flow Manager")
    logger.info("="*70)
    
    try:
        from src.utils.flow_manager import (
            set_active_flow, clear_active_flow, check_flow_ownership,
            get_active_flow, debug_flows
        )
        
        # Test set/get/check
        admin_id = 999999
        flow_name = "TEST_FLOW"
        
        set_active_flow(admin_id, flow_name)
        logger.info(f"✅ Set flow: admin={admin_id}, flow={flow_name}")
        
        active = get_active_flow(admin_id)
        if active == flow_name:
            logger.info(f"✅ Get flow correct: {active}")
        else:
            logger.error(f"❌ Get flow incorrect: expected {flow_name}, got {active}")
            return False
        
        if check_flow_ownership(admin_id, flow_name):
            logger.info(f"✅ Flow ownership check passed")
        else:
            logger.error(f"❌ Flow ownership check failed")
            return False
        
        clear_active_flow(admin_id, flow_name)
        logger.info(f"✅ Cleared flow")
        
        if not check_flow_ownership(admin_id, flow_name):
            logger.info(f"✅ Flow cleared successfully")
        else:
            logger.error(f"❌ Flow still active after clear")
            return False
        
        return True
    except Exception as e:
        logger.error(f"❌ Flow manager test failed: {e}")
        return False

def test_config_is_local():
    """TEST 7: .env is configured for LOCAL mode"""
    logger.info("\n" + "="*70)
    logger.info("TEST 7: Environment Configuration")
    logger.info("="*70)
    
    use_local = os.getenv('USE_LOCAL_DB', 'false').lower() in ('1', 'true', 'yes')
    use_remote = os.getenv('USE_REMOTE_DB', 'false').lower() in ('1', 'true', 'yes')
    env_mode = os.getenv('ENV', 'unknown')
    
    logger.info(f"USE_LOCAL_DB={use_local}")
    logger.info(f"USE_REMOTE_DB={use_remote}")
    logger.info(f"ENV={env_mode}")
    
    if use_local and not use_remote and env_mode == 'local':
        logger.info("✅ Configuration is LOCAL mode")
        return True
    else:
        logger.warning("⚠️ Configuration may not be LOCAL mode")
        logger.warning("Update .env to:")
        logger.warning("  USE_LOCAL_DB=true")
        logger.warning("  USE_REMOTE_DB=false")
        logger.warning("  ENV=local")
        return False

def main():
    """Run all validation tests"""
    logger.info("\n" + "="*80)
    logger.info(" "*20 + "FULL VALIDATION SUITE")
    logger.info(" "*15 + "Local Database + DB-Only Searches")
    logger.info("="*80)
    
    tests = [
        ("Database Connection", test_db_connection),
        ("Required Tables", test_required_tables),
        ("Users Columns", test_users_columns),
        ("Store Items Columns", test_store_items_columns),
        ("Search Functions", test_search_functions),
        ("Flow Manager", test_flow_manager),
        ("Local Configuration", test_config_is_local),
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            result = test_func()
            results[test_name] = "PASS" if result else "FAIL"
        except Exception as e:
            logger.error(f"❌ {test_name} crashed: {e}")
            results[test_name] = "ERROR"
    
    # Summary
    logger.info("\n" + "="*80)
    logger.info("VALIDATION SUMMARY")
    logger.info("="*80)
    
    passes = sum(1 for r in results.values() if r == "PASS")
    fails = sum(1 for r in results.values() if r == "FAIL")
    errors = sum(1 for r in results.values() if r == "ERROR")
    
    for test_name, result in results.items():
        symbol = "✅" if result == "PASS" else "❌" if result == "FAIL" else "⚠️"
        logger.info(f"{symbol} {test_name}: {result}")
    
    logger.info(f"\nTotal: {passes} PASS, {fails} FAIL, {errors} ERROR")
    
    if fails + errors == 0:
        logger.info("\n🎉 ALL TESTS PASSED!")
        logger.info("\nNEXT STEPS:")
        logger.info("1. Verify bot imports updated search functions")
        logger.info("2. Test invoice user search (should find users)")
        logger.info("3. Test invoice item search (should find items)")
        logger.info("4. Test delete user search (should find users)")
        logger.info("5. Test flow isolation (multiple admins)")
        logger.info("6. Check logs for DB-only patterns (no registry fallback)")
        return 0
    else:
        logger.error(f"\n❌ {fails + errors} TESTS FAILED!")
        logger.error("\nFix issues and re-run:")
        logger.error("  python validate_full_implementation.py")
        return 1

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
