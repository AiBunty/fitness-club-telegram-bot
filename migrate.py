#!/usr/bin/env python3
"""
Migration: Add profile_pic_url column to users table
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.database.connection import DatabaseConnection
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate():
    """Add profile_pic_url column to users table"""
    try:
        db = DatabaseConnection()
        conn = db.get_connection()
        conn.autocommit = True
        cursor = conn.cursor()
        
        logger.info("Adding profile_pic_url column to users table...")
        cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS profile_pic_url TEXT;")
        
        logger.info("✅ Migration successful!")
        cursor.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        return False

if __name__ == '__main__':
    success = migrate()
    sys.exit(0 if success else 1)
