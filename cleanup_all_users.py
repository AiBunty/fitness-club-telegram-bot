"""
Remove All Users from Database (Keep Admin Only)
================================================

This script deletes all users EXCEPT the admin (ID: 424837855)
and all their related data to start fresh.

Tables affected:
- daily_logs
- points_transactions
- shake_requests
- shake_credits
- attendance_queue
- meal_photos
- admin_sessions
- fee_payments
- referral_rewards
- notifications
- users

Admin (ID: 424837855) will be preserved.
"""

import logging
from src.database.connection import execute_query

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ADMIN_ID = 424837855

def cleanup_users():
    """Remove all users except admin and their related data"""
    
    try:
        # Get count of users before cleanup
        result = execute_query(
            "SELECT COUNT(*) as count FROM users WHERE user_id != %s",
            (ADMIN_ID,),
            fetch_one=True
        )
        user_count = result['count'] if result else 0
        logger.info(f"📊 Found {user_count} users to delete (excluding admin)")
        
        if user_count == 0:
            logger.info("✅ No users to delete. Database is already clean!")
            return
        
        # Delete from related tables (cascade will handle some, but being explicit for safety)
        tables_to_clean = [
            ('daily_logs', 'user_id'),
            ('points_transactions', 'user_id'),
            ('shake_requests', 'user_id'),
            ('shake_credits', 'user_id'),
            ('attendance_queue', 'user_id'),
            ('meal_photos', 'user_id'),
            ('admin_sessions', 'user_id'),
            ('fee_payments', 'user_id'),
            ('notifications', 'user_id'),
            ('referral_rewards', 'referrer_id'),  # Delete where user is referrer
            ('referral_rewards', 'referred_id'),  # Delete where user is referred
        ]
        
        logger.info("🗑️  Deleting user data from related tables...")
        
        for table, column in tables_to_clean:
            try:
                query = f"DELETE FROM {table} WHERE {column} != %s"
                execute_query(query, (ADMIN_ID,))
                logger.info(f"  ✅ Cleaned: {table}")
            except Exception as e:
                logger.warning(f"  ⚠️  Issue with {table}: {e}")
        
        # Delete all users except admin
        logger.info("🗑️  Deleting all users (except admin)...")
        execute_query(
            "DELETE FROM users WHERE user_id != %s",
            (ADMIN_ID,)
        )
        logger.info("  ✅ All non-admin users deleted")
        
        # Verify admin still exists
        admin = execute_query(
            "SELECT user_id, full_name, role FROM users WHERE user_id = %s",
            (ADMIN_ID,),
            fetch_one=True
        )
        
        if admin:
            logger.info(f"✅ Admin preserved: {admin['full_name']} (ID: {admin['user_id']}, Role: {admin['role']})")
        else:
            logger.warning("⚠️  Warning: Admin user not found!")
        
        # Final count
        result = execute_query(
            "SELECT COUNT(*) as count FROM users",
            fetch_one=True
        )
        final_count = result['count'] if result else 0
        logger.info(f"✅ Cleanup complete! Users remaining: {final_count}")
        logger.info("✅ Database is now clean and ready to start fresh!")
        logger.info("✅ Admin user is preserved and ready to approve new registrations.")
        
    except Exception as e:
        logger.error(f"❌ Error during cleanup: {e}")
        raise

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("🗑️  DATABASE CLEANUP - REMOVE ALL USERS")
    logger.info("=" * 60)
    logger.info(f"Admin ID to preserve: {ADMIN_ID}")
    logger.info("")
    
    cleanup_users()
    
    logger.info("")
    logger.info("=" * 60)
    logger.info("✅ CLEANUP COMPLETE!")
    logger.info("=" * 60)
