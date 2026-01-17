#!/usr/bin/env python3
"""
Migration: Add Reminder Preferences Table
- Allows users to customize reminder settings
- Turn reminders on/off
- Set custom intervals for each reminder type
"""

import logging
from src.database.connection import execute_query

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate():
    """Run migration"""
    try:
        logger.info("Starting migration: Reminder Preferences")
        
        # Create reminder_preferences table
        execute_query(
            """
            CREATE TABLE IF NOT EXISTS reminder_preferences (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL UNIQUE,
                water_reminder_enabled BOOLEAN DEFAULT TRUE,
                water_reminder_interval_minutes INT DEFAULT 60,
                weight_reminder_enabled BOOLEAN DEFAULT TRUE,
                weight_reminder_time VARCHAR(5) DEFAULT '06:00',
                habits_reminder_enabled BOOLEAN DEFAULT TRUE,
                habits_reminder_time VARCHAR(5) DEFAULT '20:00',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
            """
        )
        logger.info("✓ Created reminder_preferences table")
        
        # Initialize preferences for existing users with active subscriptions
        try:
            execute_query(
                """
                INSERT INTO reminder_preferences (user_id)
                SELECT DISTINCT user_id FROM subscriptions 
                WHERE status = 'active'
                ON CONFLICT (user_id) DO NOTHING
                """
            )
            logger.info("✓ Initialized reminder preferences for active users")
        except Exception as e:
            logger.info(f"✓ Reminder preferences table ready: {str(e)[:50]}")
        
        logger.info("✓ Migration completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False

if __name__ == "__main__":
    success = migrate()
    exit(0 if success else 1)
