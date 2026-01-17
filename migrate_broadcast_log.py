"""
Migration: Create broadcast_log table for tracking broadcast messages and automated follow-ups
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.database.connection import execute_query

def create_broadcast_log_table():
    """Create broadcast_log table"""
    
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS broadcast_log (
        id SERIAL PRIMARY KEY,
        user_id BIGINT NOT NULL,
        message TEXT NOT NULL,
        broadcast_type VARCHAR(50) NOT NULL,
        sent_at TIMESTAMP DEFAULT NOW(),
        created_at TIMESTAMP DEFAULT NOW(),
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
    );
    
    -- Create index for faster queries
    CREATE INDEX IF NOT EXISTS idx_broadcast_log_user_id ON broadcast_log(user_id);
    CREATE INDEX IF NOT EXISTS idx_broadcast_log_type ON broadcast_log(broadcast_type);
    CREATE INDEX IF NOT EXISTS idx_broadcast_log_sent_at ON broadcast_log(sent_at);
    """
    
    try:
        execute_query(create_table_sql)
        print("✅ broadcast_log table created successfully!")
        print("✅ Indexes created successfully!")
        return True
    except Exception as e:
        print(f"❌ Error creating broadcast_log table: {e}")
        return False

if __name__ == "__main__":
    print("Creating broadcast_log table...")
    success = create_broadcast_log_table()
    
    if success:
        print("\n✅ Migration completed successfully!")
    else:
        print("\n❌ Migration failed!")
        sys.exit(1)
