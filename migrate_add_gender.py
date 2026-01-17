"""
Migration: Add gender field to users table
"""

import logging
from src.database.connection import execute_query

logger = logging.getLogger(__name__)

def migrate():
    """Add gender column to users table"""
    try:
        # Check if column already exists
        check_query = """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name = 'gender'
        """
        result = execute_query(check_query)
        
        if result:
            logger.info("✅ Gender column already exists")
            return True
        
        # Add gender column
        alter_query = """
            ALTER TABLE users
            ADD COLUMN gender VARCHAR(20) DEFAULT NULL
        """
        execute_query(alter_query)
        logger.info("✅ Gender column added to users table")
        return True
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        return False

if __name__ == "__main__":
    if migrate():
        print("✅ Migration completed successfully")
    else:
        print("❌ Migration failed")
