"""
Restore Admin User to Database
==============================

Creates the admin user if it doesn't exist.
Admin ID: 424837855
"""

import logging
from src.database.connection import execute_query

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ADMIN_ID = 424837855
ADMIN_USERNAME = "admin"
ADMIN_NAME = "Admin"

def restore_admin():
    """Restore or create admin user"""
    
    try:
        # Check if admin exists
        admin = execute_query(
            "SELECT user_id, full_name, role FROM users WHERE user_id = %s",
            (ADMIN_ID,),
            fetch_one=True
        )
        
        if admin:
            logger.info(f"✅ Admin already exists: {admin['full_name']}")
            return
        
        logger.info("🔧 Creating admin user...")
        
        # Create admin user with proper SQL
        query = """
            INSERT INTO users (
                user_id, telegram_username, full_name, role, 
                fee_status, approval_status
            ) VALUES (%s, %s, %s, %s, %s, %s)
        """
        
        execute_query(
            query,
            (ADMIN_ID, ADMIN_USERNAME, ADMIN_NAME, 'admin', 'paid', 'approved')
        )
        
        # Verify admin was created
        admin = execute_query(
            "SELECT user_id, full_name, role FROM users WHERE user_id = %s",
            (ADMIN_ID,),
            fetch_one=True
        )
        
        if admin:
            logger.info(f"✅ Admin restored: {admin['full_name']} (ID: {admin['user_id']}, Role: {admin['role']})")
        
    except Exception as e:
        logger.error(f"❌ Error restoring admin: {e}")
        raise

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("🔧 RESTORE ADMIN USER")
    logger.info("=" * 60)
    
    restore_admin()
    
    logger.info("=" * 60)
    logger.info("✅ DONE!")
    logger.info("=" * 60)
