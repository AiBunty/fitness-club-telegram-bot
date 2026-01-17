"""
Migration: Add role column to users table for unified role management
This script adds a 'role' column to the users table and migrates existing admin/staff to the new system.
"""

import os
import sys
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

# Load environment
load_dotenv()

# Database config
DATABASE_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
}

def migrate():
    try:
        conn = psycopg2.connect(**DATABASE_CONFIG)
        cursor = conn.cursor()
        
        print("🔄 Starting migration...")
        
        # Check if role column already exists
        cursor.execute("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name='users' AND column_name='role'
        """)
        
        if cursor.fetchone():
            print("✅ Role column already exists. Skipping...")
            cursor.close()
            conn.close()
            return
        
        # Add role column with default 'user'
        print("📝 Adding 'role' column to users table...")
        cursor.execute("""
            ALTER TABLE users 
            ADD COLUMN role VARCHAR(20) DEFAULT 'user' NOT NULL
        """)
        
        # Migrate admins from admin_members table
        print("🔄 Migrating admins from admin_members table...")
        cursor.execute("""
            UPDATE users u 
            SET role = 'admin'
            WHERE u.user_id IN (SELECT user_id FROM admin_members)
        """)
        admin_count = cursor.rowcount
        print(f"✅ Migrated {admin_count} admins")
        
        # Migrate staff from staff_members table
        print("🔄 Migrating staff from staff_members table...")
        cursor.execute("""
            UPDATE users u 
            SET role = 'staff'
            WHERE u.user_id IN (SELECT user_id FROM staff_members)
            AND u.role = 'user'
        """)
        staff_count = cursor.rowcount
        print(f"✅ Migrated {staff_count} staff members")
        
        # Commit changes
        conn.commit()
        
        print("\n✅ Migration completed successfully!")
        print(f"📊 Summary:")
        print(f"   - Admins migrated: {admin_count}")
        print(f"   - Staff migrated: {staff_count}")
        print(f"   - Default role for new users: 'user'")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    migrate()
