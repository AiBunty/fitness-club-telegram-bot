"""
Migration: Add subscription tables
"""

import logging
from src.database.connection import execute_query

logger = logging.getLogger(__name__)


def migrate_add_subscriptions():
    """Create subscription and subscription_requests tables"""
    try:
        # Create subscription_requests table
        execute_query(
            """
            CREATE TABLE IF NOT EXISTS subscription_requests (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                plan_id VARCHAR(20) NOT NULL,
                amount INTEGER NOT NULL,
                status VARCHAR(20) DEFAULT 'pending',
                requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                approved_at TIMESTAMP,
                rejection_reason TEXT
            )
            """
        )
        logger.info("subscription_requests table created/verified")
        
        # Create subscriptions table
        execute_query(
            """
            CREATE TABLE IF NOT EXISTS subscriptions (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL UNIQUE REFERENCES users(user_id) ON DELETE CASCADE,
                plan_id VARCHAR(20) NOT NULL,
                amount INTEGER NOT NULL,
                start_date TIMESTAMP NOT NULL,
                end_date TIMESTAMP NOT NULL,
                status VARCHAR(20) DEFAULT 'active',
                grace_period_end TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        logger.info("subscriptions table created/verified")
        
        # Create subscription_reminders table for tracking follow-ups
        execute_query(
            """
            CREATE TABLE IF NOT EXISTS subscription_reminders (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                reminder_type VARCHAR(50),
                last_sent_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        logger.info("subscription_reminders table created/verified")
        
        return True
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False


if __name__ == "__main__":
    print("Running subscription migration...")
    if migrate_add_subscriptions():
        print("✅ Migration completed successfully!")
    else:
        print("❌ Migration failed!")
