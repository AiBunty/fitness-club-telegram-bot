#!/usr/bin/env python3
"""
Database Migration: Create audit_log table for store items bulk upload
Run this to initialize the audit tracking system
"""

import os
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_audit_log_table():
    """Create audit_log table in database"""
    try:
        from src.config import DATABASE_CONFIG
        from src.database.connection import get_db_connection
        
        connection = get_db_connection()
        cursor = connection.cursor()
        
        # Create audit_log table
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS audit_log (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id BIGINT NOT NULL COMMENT 'Admin user ID who made the change',
            entity_type VARCHAR(50) NOT NULL COMMENT 'Type of entity (e.g., store_items)',
            entity_id INT NOT NULL COMMENT 'ID of the entity',
            action VARCHAR(50) NOT NULL COMMENT 'Action performed (e.g., bulk_upload_update, manual_edit)',
            old_value JSON COMMENT 'Previous state as JSON',
            new_value JSON COMMENT 'New state as JSON',
            description VARCHAR(255) COMMENT 'Human-readable description',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            INDEX idx_entity (entity_type, entity_id),
            INDEX idx_user_time (user_id, created_at),
            INDEX idx_action (action),
            INDEX idx_time (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        COMMENT='Audit trail for all store item changes'
        """
        
        cursor.execute(create_table_sql)
        connection.commit()
        logger.info("✅ audit_log table created successfully")
        
        # Add UNIQUE constraint to store_items serial if not exists
        alter_serial_sql = """
        ALTER TABLE store_items 
        ADD UNIQUE KEY unique_serial (serial)
        """
        
        try:
            cursor.execute(alter_serial_sql)
            connection.commit()
            logger.info("✅ UNIQUE constraint added to store_items.serial")
        except Exception as e:
            if "Duplicate entry" in str(e) or "already exists" in str(e):
                logger.info("ℹ️ UNIQUE constraint already exists on store_items.serial")
            else:
                logger.warning(f"⚠️ Could not add UNIQUE constraint: {e}")
        
        cursor.close()
        connection.close()
        
        return True
    
    except Exception as e:
        logger.error(f"❌ Error creating audit_log table: {e}")
        return False


if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.insert(0, '.')
    
    # Set environment for remote database
    os.environ['USE_LOCAL_DB'] = 'false'
    os.environ['USE_REMOTE_DB'] = 'true'
    os.environ['ENV'] = 'remote'
    
    logger.info("Starting database migration...")
    success = create_audit_log_table()
    
    if success:
        logger.info("✅ Migration completed successfully!")
        sys.exit(0)
    else:
        logger.error("❌ Migration failed")
        sys.exit(1)
