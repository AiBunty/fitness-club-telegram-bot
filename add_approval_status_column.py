"""
Migration script to add approval_status column to MySQL users table.
This column is required for user search functionality in invoices.
"""
import pymysql
from dotenv import load_dotenv
import os
import sys

load_dotenv()

def add_approval_status_column():
    """Add approval_status column to users table with default value 'approved'"""
    try:
        # Connect to MySQL
        conn = pymysql.connect(
            host=os.getenv('DB_HOST'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASS'),
            database=os.getenv('DB_NAME'),
            port=int(os.getenv('DB_PORT', 3306)),
            charset='utf8mb4'
        )
        
        print(f"✅ Connected to MySQL: {os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}")
        print(f"   Database: {os.getenv('DB_NAME')}")
        
        cursor = conn.cursor()
        
        # Check if column already exists
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = %s 
            AND TABLE_NAME = 'users' 
            AND COLUMN_NAME = 'approval_status'
        """, (os.getenv('DB_NAME'),))
        
        exists = cursor.fetchone()[0]
        
        if exists:
            print("⚠️  Column 'approval_status' already exists in users table")
        else:
            # Add approval_status column
            print("📝 Adding 'approval_status' column to users table...")
            cursor.execute("""
                ALTER TABLE users 
                ADD COLUMN approval_status VARCHAR(20) DEFAULT 'approved'
            """)
            conn.commit()
            print("✅ Column 'approval_status' added successfully")
        
        # Set all existing users to 'approved' status (in case they have NULL)
        print("📝 Updating existing users to 'approved' status...")
        cursor.execute("""
            UPDATE users 
            SET approval_status = 'approved' 
            WHERE approval_status IS NULL OR approval_status = ''
        """)
        conn.commit()
        updated_count = cursor.rowcount
        print(f"✅ Updated {updated_count} users to 'approved' status")
        
        # Verify the column
        cursor.execute("SHOW COLUMNS FROM users LIKE 'approval_status'")
        result = cursor.fetchone()
        if result:
            print(f"✅ Verification successful: {result}")
        
        # Show sample data
        cursor.execute("SELECT user_id, full_name, approval_status FROM users LIMIT 3")
        print("\n📋 Sample users with approval_status:")
        for row in cursor.fetchall():
            print(f"   • User ID: {row[0]}, Name: {row[1]}, Status: {row[2]}")
        
        cursor.close()
        conn.close()
        
        print("\n✅ Migration completed successfully!")
        print("   The users table now has the 'approval_status' column.")
        print("   User search in invoices should now work correctly.")
        return True
        
    except Exception as e:
        print(f"\n❌ Error during migration: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = add_approval_status_column()
    sys.exit(0 if success else 1)
