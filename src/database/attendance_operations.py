import logging
from datetime import datetime
from src.database.connection import execute_query
from src.config import POINTS_CONFIG

logger = logging.getLogger(__name__)

def create_attendance_request(user_id: int, photo_url: str = None):
    """Create an attendance request for today"""
    try:
        query = """
            INSERT INTO attendance_queue (user_id, request_date, photo_url, status)
            VALUES (%s, CURRENT_DATE, %s, 'pending')
            ON CONFLICT (user_id, request_date) 
            DO UPDATE SET photo_url = EXCLUDED.photo_url, status = 'pending'
            RETURNING *
        """
        result = execute_query(query, (user_id, photo_url), fetch_one=True)
        logger.info(f"Attendance request created for user {user_id}")
        return result
    except Exception as e:
        logger.error(f"Failed to create attendance request: {e}")
        return None

def get_pending_attendance_requests(limit: int = 20):
    """Get all pending attendance requests"""
    query = """
        SELECT a.*, u.full_name, u.telegram_id, u.telegram_username
        FROM attendance_queue a
        JOIN users u ON a.user_id = u.user_id
        WHERE a.status = 'pending'
        AND a.request_date = CURRENT_DATE
        ORDER BY a.created_at ASC
        LIMIT %s
    """
    return execute_query(query, (limit,))

def approve_attendance(attendance_id: int, admin_user_id: int):
    """Approve an attendance request"""
    try:
        existing = execute_query(
            """
            SELECT user_id, status,
                   (SELECT telegram_id FROM users WHERE user_id = attendance_queue.user_id) AS telegram_id
            FROM attendance_queue
            WHERE attendance_id = %s
            """,
            (attendance_id,),
            fetch_one=True,
        )

        if not existing:
            return None

        if existing.get('status') != 'pending':
            logger.info(f"Attendance {attendance_id} already {existing.get('status')}")
            existing['already_processed'] = True
            return existing

        # Update status and get user details only if pending
        query1 = """
            UPDATE attendance_queue 
            SET status = 'approved', approved_by = %s, approved_at = CURRENT_TIMESTAMP
            WHERE attendance_id = %s AND status = 'pending'
            RETURNING user_id, (SELECT telegram_id FROM users WHERE user_id = attendance_queue.user_id) as telegram_id
        """
        result = execute_query(query1, (admin_user_id, attendance_id), fetch_one=True)
        
        if result:
            user_id = result['user_id']
            # Award attendance points
            query2 = """
                INSERT INTO points_transactions (user_id, points, activity, description)
                VALUES (%s, %s, 'attendance', 'Gym attendance approved')
            """
            execute_query(query2, (user_id, POINTS_CONFIG['attendance']))
            
            # Update user points
            query3 = "UPDATE users SET total_points = total_points + %s WHERE user_id = %s"
            execute_query(query3, (POINTS_CONFIG['attendance'], user_id))
            
            logger.info(f"Attendance approved for user {user_id}, awarded {POINTS_CONFIG['attendance']} points")
            result['already_processed'] = False
            return result
        return None
    except Exception as e:
        logger.error(f"Failed to approve attendance: {e}")
        return None

def reject_attendance(attendance_id: int, admin_user_id: int, reason: str = ""):
    """Reject an attendance request"""
    try:
        existing = execute_query(
            "SELECT user_id, status, (SELECT telegram_id FROM users WHERE user_id = attendance_queue.user_id) AS telegram_id FROM attendance_queue WHERE attendance_id = %s",
            (attendance_id,),
            fetch_one=True,
        )

        if not existing:
            return None

        if existing.get('status') != 'pending':
            logger.info(f"Attendance {attendance_id} already {existing.get('status')}")
            existing['already_processed'] = True
            return existing

        query = """
            UPDATE attendance_queue 
            SET status = 'rejected', approved_by = %s, approved_at = CURRENT_TIMESTAMP
            WHERE attendance_id = %s AND status = 'pending'
            RETURNING user_id, (SELECT telegram_id FROM users WHERE user_id = attendance_queue.user_id) as telegram_id
        """
        result = execute_query(query, (admin_user_id, attendance_id), fetch_one=True)
        if result:
            result['already_processed'] = False
            logger.info(f"Attendance rejected for user {result['user_id']}, reason: {reason}")
        return result
    except Exception as e:
        logger.error(f"Failed to reject attendance: {e}")
        return None

def get_user_attendance_today(user_id: int):
    """Check if user already requested attendance today"""
    query = """
        SELECT * FROM attendance_queue 
        WHERE user_id = %s AND request_date = CURRENT_DATE
    """
    return execute_query(query, (user_id,), fetch_one=True)

def get_user_attendance_history(user_id: int, days: int = 30):
    """Get user's attendance history"""
    query = """
        SELECT * FROM attendance_queue 
        WHERE user_id = %s 
        AND request_date >= CURRENT_DATE - %s * INTERVAL '1 day'
        AND status = 'approved'
        ORDER BY request_date DESC
    """
    return execute_query(query, (user_id, days))

def get_monthly_attendance(user_id: int, month: int = None, year: int = None):
    """Get user's attendance count for a month"""
    if not month:
        month = datetime.now().month
    if not year:
        year = datetime.now().year
    
    query = """
        SELECT COUNT(*) as days_attended
        FROM attendance_queue
        WHERE user_id = %s
        AND status = 'approved'
        AND EXTRACT(MONTH FROM request_date) = %s
        AND EXTRACT(YEAR FROM request_date) = %s
    """
    result = execute_query(query, (user_id, month, year), fetch_one=True)
    return result['days_attended'] if result else 0
def get_weekly_attendance_count(user_id: int):
    """
    Get user's attendance count for current week (Monday-Saturday).
    Excludes Sundays (holiday).
    """
    query = """
        SELECT COUNT(*) as days_attended
        FROM attendance_queue
        WHERE user_id = %s
        AND status = 'approved'
        AND request_date >= CURRENT_DATE - INTERVAL '7 days'
        AND EXTRACT(DOW FROM request_date) != 0
        AND request_date <= CURRENT_DATE
    """
    result = execute_query(query, (user_id,), fetch_one=True)
    return result['days_attended'] if result else 0

def award_weekly_bonus(user_id: int, admin_user_id: int):
    """
    Award 200 bonus points if user has attended 6+ days in current week.
    Only awards once per week.
    """
    try:
        # Check if already awarded bonus this week
        query_check = """
            SELECT COUNT(*) as bonus_count
            FROM points_transactions
            WHERE user_id = %s
            AND activity = 'weekly_bonus'
            AND DATE(created_at) >= CURRENT_DATE - INTERVAL '7 days'
        """
        bonus_result = execute_query(query_check, (user_id,), fetch_one=True)
        
        if bonus_result and bonus_result['bonus_count'] > 0:
            logger.info(f"User {user_id} already received weekly bonus this week")
            return None
        
        # Check weekly attendance (6 or more days, excluding Sunday)
        attendance_count = get_weekly_attendance_count(user_id)
        
        if attendance_count >= 6:
            # Award bonus
            bonus_points = 200
            
            query_add = """
                INSERT INTO points_transactions (user_id, points, activity, description)
                VALUES (%s, %s, 'weekly_bonus', 'Weekly attendance bonus (6+ days)')
            """
            execute_query(query_add, (user_id, bonus_points))
            
            # Update user points
            query_update = "UPDATE users SET total_points = total_points + %s WHERE user_id = %s"
            execute_query(query_update, (bonus_points, user_id))
            
            logger.info(f"Weekly bonus awarded to user {user_id}: {attendance_count} days attended, +{bonus_points} points")
            return {'user_id': user_id, 'days_attended': attendance_count, 'bonus_points': bonus_points}
        else:
            logger.info(f"User {user_id} has {attendance_count} days, needs 6 for bonus")
            return None
    except Exception as e:
        logger.error(f"Failed to award weekly bonus: {e}")
        return None