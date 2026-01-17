"""
Migration: Add ban fields to users table
Adds is_banned, ban_reason, and banned_at columns
"""
import psycopg2
from src.config import DATABASE_CONFIG

def migrate():
    conn = psycopg2.connect(**DATABASE_CONFIG)
    cursor = conn.cursor()
    
    try:
        # Check if columns already exist
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='users' AND column_name='is_banned'
        """)
        
        if cursor.fetchone():
            print("✅ Migration already applied - is_banned column exists")
            return
        
        print("📝 Adding ban fields to users table...")
        
        # Add ban columns
        cursor.execute("""
            ALTER TABLE users 
            ADD COLUMN IF NOT EXISTS is_banned BOOLEAN DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS ban_reason TEXT,
            ADD COLUMN IF NOT EXISTS banned_at TIMESTAMP
        """)
        
        conn.commit()
        print("✅ Migration complete - Ban fields added to users table")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Migration failed: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    migrate()
