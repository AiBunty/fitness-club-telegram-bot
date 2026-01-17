"""
Migration: Add approval_status field to users table
Run this once to add the approval system
"""
import psycopg2
from src.config import DATABASE_CONFIG

def migrate():
    try:
        conn = psycopg2.connect(
            host=DATABASE_CONFIG['host'],
            port=DATABASE_CONFIG['port'],
            database=DATABASE_CONFIG['database'],
            user=DATABASE_CONFIG['user'],
            password=DATABASE_CONFIG['password']
        )
        cur = conn.cursor()
        
        # Add approval_status column (default 'pending' for new users, 'approved' for existing)
        print("Adding approval_status column to users table...")
        cur.execute("""
            ALTER TABLE users 
            ADD COLUMN IF NOT EXISTS approval_status VARCHAR(20) DEFAULT 'approved'
        """)
        
        # Set existing users as approved
        cur.execute("""
            UPDATE users 
            SET approval_status = 'approved' 
            WHERE approval_status IS NULL
        """)
        
        conn.commit()
        print("✅ Migration completed successfully!")
        print("   - Added approval_status column")
        print("   - Existing users set as 'approved'")
        print("   - New users will be 'pending' by default")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")

if __name__ == '__main__':
    migrate()
