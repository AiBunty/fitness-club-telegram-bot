#!/usr/bin/env python3
"""
Migration: Add UPI Settings table and screenshot support
- Creates gym_settings table for admin to configure UPI ID
- Adds screenshot_file_id column to subscription_payments table
"""

import logging
from src.database.connection import execute_query

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate():
    """Run migration"""
    try:
        logger.info("Starting migration: UPI Settings and Screenshot Support")
        
        # Create gym_settings table
        execute_query(
            """
            CREATE TABLE IF NOT EXISTS gym_settings (
                id SERIAL PRIMARY KEY,
                upi_id VARCHAR(100),
                gym_name VARCHAR(255),
                qr_code_url TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        logger.info("✓ Created gym_settings table")
        
        # Insert default settings if not exists
        try:
            result = execute_query(
                "SELECT COUNT(*) FROM gym_settings",
                fetch_one=True
            )
            
            if result and result[0] == 0:
                execute_query(
                    """
                    INSERT INTO gym_settings (id, upi_id, gym_name) 
                    VALUES (1, '9158243377@ybl', 'Fitness Club Gym')
                    """
                )
                logger.info("✓ Inserted default gym settings")
            else:
                logger.info("✓ Gym settings already exist")
        except Exception as e:
            logger.info(f"✓ Gym settings already exist: {str(e)[:50]}")
        
        # Check if screenshot_file_id column exists
        col_check = execute_query(
            """
            SELECT column_name FROM information_schema.columns 
            WHERE table_name='subscription_payments' AND column_name='screenshot_file_id'
            """,
            fetch_one=True
        )
        
        if not col_check:
            # Add screenshot_file_id column to subscription_payments
            execute_query(
                """
                ALTER TABLE subscription_payments 
                ADD COLUMN screenshot_file_id VARCHAR(255)
                """
            )
            logger.info("✓ Added screenshot_file_id column to subscription_payments")
        else:
            logger.info("✓ screenshot_file_id column already exists")
        
        logger.info("✓ Migration completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False

if __name__ == "__main__":
    success = migrate()
    exit(0 if success else 1)

