#!/usr/bin/env python3
"""
Test Database Connection Script
Tests the PostgreSQL connection and verifies tables exist.
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.database.connection import test_connection, execute_query
from src.config import DATABASE_CONFIG
import logging

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

def test_db_connection():
    """Test basic database connection."""
    logger.info("=" * 60)
    logger.info("Testing Fitness Club Bot Database Connection")
    logger.info("=" * 60)
    
    # Test connection
    logger.info("\n1. Testing connection...")
    if test_connection():
        logger.info("✅ Connection successful!")
    else:
        logger.error("❌ Connection failed!")
        return False
    
    # Check if tables exist
    logger.info("\n2. Checking database tables...")
    try:
        tables = execute_query(
            """SELECT table_name FROM information_schema.tables 
               WHERE table_schema = 'public' 
               ORDER BY table_name"""
        )
        
        if tables:
            logger.info(f"✅ Found {len(tables)} tables:")
            for table in tables:
                logger.info(f"   - {table['table_name']}")
        else:
            logger.warning("⚠️ No tables found. Run schema.sql to create tables.")
            logger.warning("\nTo create tables, run:")
            logger.warning(f"  psql -U {DATABASE_CONFIG['user']} -h {DATABASE_CONFIG['host']} -d {DATABASE_CONFIG['database']} -f schema.sql")
            return False
    except Exception as e:
        logger.error(f"❌ Error checking tables: {e}")
        return False
    
    # Count users
    logger.info("\n3. Checking user count...")
    try:
        result = execute_query(
            "SELECT COUNT(*) as count FROM users",
            fetch_one=True
        )
        logger.info(f"✅ Users in database: {result['count']}")
    except Exception as e:
        logger.error(f"❌ Error checking users: {e}")
        return False
    
    logger.info("\n" + "=" * 60)
    logger.info("✅ All tests passed!")
    logger.info("=" * 60)
    logger.info("\nYou can now run the bot:")
    logger.info("  python src/bot.py")
    
    return True

if __name__ == '__main__':
    success = test_db_connection()
    sys.exit(0 if success else 1)

