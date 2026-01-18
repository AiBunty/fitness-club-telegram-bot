#!/usr/bin/env python3
"""
Migration: Add attendance_overrides table for QR system admin overrides
"""

import sys
from src.database.connection import get_connection

def migrate():
    """Create attendance_overrides table"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Create table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS attendance_overrides (
                override_id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                admin_id BIGINT NOT NULL,
                reason TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            );
        """)
        
        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_attendance_overrides_user 
            ON attendance_overrides(user_id);
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_attendance_overrides_admin 
            ON attendance_overrides(admin_id);
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_attendance_overrides_date 
            ON attendance_overrides(created_at);
        """)
        
        conn.commit()
        print("✅ Migration successful: attendance_overrides table created")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    success = migrate()
    sys.exit(0 if success else 1)
