"""
Quick script to set user role to admin in the database
"""

import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

DATABASE_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
}

USER_ID = 424837855

try:
    conn = psycopg2.connect(**DATABASE_CONFIG)
    cursor = conn.cursor()
    
    # Check current role
    cursor.execute("SELECT user_id, full_name, role FROM users WHERE user_id = %s", (USER_ID,))
    user = cursor.fetchone()
    
    if user:
        print(f"Current user: {user}")
        
        # Update role to admin
        cursor.execute("UPDATE users SET role = 'admin' WHERE user_id = %s", (USER_ID,))
        conn.commit()
        
        # Verify update
        cursor.execute("SELECT user_id, full_name, role FROM users WHERE user_id = %s", (USER_ID,))
        updated_user = cursor.fetchone()
        print(f"✅ Updated: {updated_user}")
    else:
        print(f"❌ User {USER_ID} not found")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Error: {e}")
