"""
Database operations for admin reports and analytics
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from src.database.connection import get_connection

logger = logging.getLogger(__name__)


def get_active_members(limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Get list of active members with paid fees
    Returns: List of members with fee_status = 'paid' or 'active' and not expired
    """
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        # FIX: Removed non-existent telegram_id column
        query = """
            SELECT 
                user_id,
                full_name,
                telegram_username,
                phone,
                fee_paid_date,
                fee_expiry_date,
                fee_status,
                total_points,
                created_at
            FROM users
            WHERE (fee_status IN ('paid', 'active'))
              AND (fee_expiry_date IS NULL OR fee_expiry_date >= CURRENT_DATE)
            ORDER BY fee_paid_date DESC
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        cur.execute(query)
        rows = cur.fetchall()
        
        members = []
        for row in rows:
            members.append({
                'user_id': row[0],
                'full_name': row[1],
                'telegram_username': row[2],
                'phone': row[3],
                'fee_paid_date': row[4],
                'fee_expiry_date': row[5],
                'fee_status': row[6],
                'total_points': row[7],
                'created_at': row[8]
            })
        
        cur.close()
        return members
        
    except Exception as e:
        logger.error(f"Error fetching active members: {e}")
        return []
    finally:
        # FIX: Ensure connection is returned to the pool for scalability
        if conn:
            from src.database.connection import DatabaseConnectionPool
            DatabaseConnectionPool().get_pool().putconn(conn)


def get_inactive_members(limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Get list of inactive members (unpaid or expired)
    Returns: List of members with fee_status != 'paid'/'active' or expired
    """
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        # FIX: Removed non-existent telegram_id column
        query = """
            SELECT 
                user_id,
                full_name,
                telegram_username,
                phone,
                fee_paid_date,
                fee_expiry_date,
                fee_status,
                total_points,
                created_at
            FROM users
            WHERE (fee_status NOT IN ('paid', 'active') OR fee_status IS NULL)
               OR (fee_expiry_date IS NOT NULL AND fee_expiry_date < CURRENT_DATE)
            ORDER BY 
                CASE WHEN fee_expiry_date IS NOT NULL THEN fee_expiry_date ELSE created_at END DESC
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        cur.execute(query)
        rows = cur.fetchall()
        
        members = []
        for row in rows:
            members.append({
                'user_id': row[0],
                'full_name': row[1],
                'telegram_username': row[2],
                'phone': row[3],
                'fee_paid_date': row[4],
                'fee_expiry_date': row[5],
                'fee_status': row[6],
                'total_points': row[7],
                'created_at': row[8]
            })
        
        cur.close()
        return members
        
    except Exception as e:
        logger.error(f"Error fetching inactive members: {e}")
        return []
    finally:
        # FIX: Ensure connection is returned to the pool for scalability
        if conn:
            from src.database.connection import DatabaseConnectionPool
            DatabaseConnectionPool().get_pool().putconn(conn)


def get_expiring_soon_members(days: int = 7) -> List[Dict[str, Any]]:
    """
    Get members whose subscription is expiring within X days
    """
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        # FIX: Removed non-existent telegram_id column
        query = """
            SELECT 
                user_id,
                full_name,
                telegram_username,
                phone,
                fee_paid_date,
                fee_expiry_date,
                fee_status,
                total_points
            FROM users
            WHERE fee_status IN ('paid', 'active')
              AND fee_expiry_date IS NOT NULL
              AND fee_expiry_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '%s days'
            ORDER BY fee_expiry_date ASC
        """
        
        cur.execute(query, (days,))
        rows = cur.fetchall()
        
        members = []
        for row in rows:
            members.append({
                'user_id': row[0],
                'full_name': row[1],
                'telegram_username': row[2],
                'phone': row[3],
                'fee_paid_date': row[4],
                'fee_expiry_date': row[5],
                'fee_status': row[6],
                'total_points': row[7],
                'days_remaining': (row[5] - datetime.now().date()).days if row[5] else None
            })
        
        cur.close()
        return members
        
    except Exception as e:
        logger.error(f"Error fetching expiring members: {e}")
        return []
    finally:
        # FIX: Ensure connection is returned to the pool for scalability
        if conn:
            from src.database.connection import DatabaseConnectionPool
            DatabaseConnectionPool().get_pool().putconn(conn)


def get_member_daily_activity(date: Optional[datetime] = None) -> List[Dict[str, Any]]:
    """
    Get all member activities for a specific date
    Returns: List of members with their daily activities
    """
    if not date:
        date = datetime.now()
    
    target_date = date.date()
    
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        
        # Get all users with their activity data for the day
        # FIX: Removed non-existent telegram_id column
        query = """
            SELECT 
                u.user_id,
                u.full_name,
                u.telegram_username,
                u.fee_status,
                
                -- Attendance
                (SELECT COUNT(*) FROM attendance_queue 
                 WHERE user_id = u.user_id 
                   AND DATE(check_in_time) = %s 
                   AND status = 'approved') as attendance_count,
                
                -- Weight logs
                (SELECT COUNT(*) FROM weight_logs 
                 WHERE user_id = u.user_id 
                   AND DATE(logged_at) = %s) as weight_logs,
                
                -- Water logs
                (SELECT COALESCE(SUM(cups), 0) FROM water_logs 
                 WHERE user_id = u.user_id 
                   AND DATE(logged_at) = %s) as water_cups,
                
                -- Meal logs
                (SELECT COUNT(*) FROM meal_logs 
                 WHERE user_id = u.user_id 
                   AND DATE(logged_at) = %s) as meal_logs,
                
                -- Habits
                (SELECT COUNT(*) FROM habit_logs 
                 WHERE user_id = u.user_id 
                   AND DATE(logged_at) = %s 
                   AND completed = true) as habits_completed,
                
                -- Shake orders
                (SELECT COUNT(*) FROM shake_queue 
                 WHERE user_id = u.user_id 
                   AND DATE(requested_at) = %s) as shake_orders,
                
                -- Points earned today
                u.total_points
                
            FROM users u
            ORDER BY u.full_name ASC
        """
        
        cur.execute(query, (target_date, target_date, target_date, target_date, target_date, target_date))
        rows = cur.fetchall()
        
        activities = []
        for row in rows:
            activity = {
                'user_id': row[0],
                'full_name': row[1],
                'telegram_username': row[2],
                'fee_status': row[3],
                'attendance_count': row[4],
                'weight_logs': row[5],
                'water_cups': row[6],
                'meal_logs': row[7],
                'habits_completed': row[8],
                'shake_orders': row[9],
                'total_points': row[10],
                'activity_score': row[4] + row[5] + (1 if row[6] > 0 else 0) + row[7] + row[8]
            }
            activities.append(activity)
        
        cur.close()
        return activities
        
    except Exception as e:
        logger.error(f"Error fetching member daily activity: {e}")
        return []
    finally:
        # FIX: Ensure connection is returned to the pool for scalability
        if conn:
            from src.database.connection import DatabaseConnectionPool
            DatabaseConnectionPool().get_pool().putconn(conn)


def get_top_performers(days: int = 7, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Get top performing members based on activity in last X days
    """
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        
        start_date = datetime.now().date() - timedelta(days=days)
        
        # FIX: Removed non-existent telegram_id column
        query = """
            SELECT 
                u.user_id,
                u.full_name,
                u.telegram_username,
                u.total_points,
                
                COUNT(DISTINCT DATE(aq.check_in_time)) as attendance_days,
                COUNT(DISTINCT DATE(wl.logged_at)) as weight_log_days,
                COUNT(DISTINCT DATE(wat.logged_at)) as water_log_days,
                COUNT(DISTINCT DATE(ml.logged_at)) as meal_log_days,
                COUNT(DISTINCT DATE(hl.logged_at)) as habit_log_days,
                
                (COUNT(DISTINCT DATE(aq.check_in_time)) + 
                 COUNT(DISTINCT DATE(wl.logged_at)) + 
                 COUNT(DISTINCT DATE(wat.logged_at)) + 
                 COUNT(DISTINCT DATE(ml.logged_at)) + 
                 COUNT(DISTINCT DATE(hl.logged_at))) as total_activity_days
                
            FROM users u
            LEFT JOIN attendance_queue aq ON u.user_id = aq.user_id 
                AND DATE(aq.check_in_time) >= %s 
                AND aq.status = 'approved'
            LEFT JOIN weight_logs wl ON u.user_id = wl.user_id 
                AND DATE(wl.logged_at) >= %s
            LEFT JOIN water_logs wat ON u.user_id = wat.user_id 
                AND DATE(wat.logged_at) >= %s
            LEFT JOIN meal_logs ml ON u.user_id = ml.user_id 
                AND DATE(ml.logged_at) >= %s
            LEFT JOIN habit_logs hl ON u.user_id = hl.user_id 
                AND DATE(hl.logged_at) >= %s 
                AND hl.completed = true
            
            GROUP BY u.user_id, u.full_name, u.telegram_username, u.total_points
            ORDER BY total_activity_days DESC, u.total_points DESC
            LIMIT %s
        """
        
        cur.execute(query, (start_date, start_date, start_date, start_date, start_date, limit))
        rows = cur.fetchall()
        
        performers = []
        for row in rows:
            performers.append({
                'user_id': row[0],
                'full_name': row[1],
                'telegram_username': row[2],
                'total_points': row[3],
                'attendance_days': row[4],
                'weight_log_days': row[5],
                'water_log_days': row[6],
                'meal_log_days': row[7],
                'habit_log_days': row[8],
                'total_activity_days': row[9]
            })
        
        cur.close()
        return performers
        
    except Exception as e:
        logger.error(f"Error fetching top performers: {e}")
        return []
    finally:
        # FIX: Ensure connection is returned to the pool for scalability
        if conn:
            from src.database.connection import DatabaseConnectionPool
            DatabaseConnectionPool().get_pool().putconn(conn)


def get_inactive_users(days: int = 7, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Get members with no activity in last X days
    """
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        
        start_date = datetime.now().date() - timedelta(days=days)
        
        # FIX: Removed non-existent telegram_id column
        query = """
            SELECT 
                u.user_id,
                u.full_name,
                u.telegram_username,
                u.fee_status,
                u.total_points,
                
                COALESCE(MAX(aq.check_in_time), u.created_at) as last_activity
                
            FROM users u
            LEFT JOIN attendance_queue aq ON u.user_id = aq.user_id 
                AND aq.status = 'approved'
            LEFT JOIN weight_logs wl ON u.user_id = wl.user_id
            LEFT JOIN water_logs wat ON u.user_id = wat.user_id
            LEFT JOIN meal_logs ml ON u.user_id = ml.user_id
            LEFT JOIN habit_logs hl ON u.user_id = hl.user_id
            
            GROUP BY u.user_id, u.full_name, u.telegram_username, 
                     u.fee_status, u.total_points, u.created_at
            
            HAVING COALESCE(MAX(GREATEST(
                COALESCE(aq.check_in_time, '1900-01-01'::timestamp),
                COALESCE(wl.logged_at, '1900-01-01'::timestamp),
                COALESCE(wat.logged_at, '1900-01-01'::timestamp),
                COALESCE(ml.logged_at, '1900-01-01'::timestamp),
                COALESCE(hl.logged_at, '1900-01-01'::timestamp)
            )), u.created_at) < %s
            
            ORDER BY last_activity ASC
            LIMIT %s
        """
        
        cur.execute(query, (datetime.now() - timedelta(days=days), limit))
        rows = cur.fetchall()
        
        inactive = []
        for row in rows:
            days_inactive = (datetime.now() - row[5]).days if row[5] else 0
            inactive.append({
                'user_id': row[0],
                'full_name': row[1],
                'telegram_username': row[2],
                'fee_status': row[3],
                'total_points': row[4],
                'last_activity': row[5],
                'days_inactive': days_inactive
            })
        
        cur.close()
        return inactive
        
    except Exception as e:
        logger.error(f"Error fetching inactive users: {e}")
        return []
    finally:
        # FIX: Ensure connection is returned to the pool for scalability
        if conn:
            from src.database.connection import DatabaseConnectionPool
            DatabaseConnectionPool().get_pool().putconn(conn)


def move_expired_to_inactive() -> int:
    """
    Move members with expired fees (7+ days past expiry) to inactive status
    Returns: Number of members moved
    """
    conn = get_connection()
    if not conn:
        return 0
    
    try:
        cur = conn.cursor()
        
        grace_period_date = datetime.now().date() - timedelta(days=7)
        
        # FIX: Removed non-existent telegram_id column
        query = """
            UPDATE users
            SET fee_status = 'expired'
            WHERE fee_status IN ('paid', 'active')
              AND fee_expiry_date IS NOT NULL
              AND fee_expiry_date < %s
            RETURNING user_id, full_name, fee_expiry_date
        """
        
        cur.execute(query, (grace_period_date,))
        moved = cur.fetchall()
        conn.commit()
        
        logger.info(f"Moved {len(moved)} members to inactive status")
        
        for member in moved:
            logger.info(f"Expired: {member[1]} (ID: {member[0]}) - Expired on {member[2]}")
        
        cur.close()
        return len(moved)
        
    except Exception as e:
        logger.error(f"Error moving expired members: {e}")
        if conn:
            conn.rollback()
        return 0
    finally:
        # FIX: Ensure connection is returned to the pool for scalability
        if conn:
            from src.database.connection import DatabaseConnectionPool
            DatabaseConnectionPool().get_pool().putconn(conn)


def get_membership_stats() -> Dict[str, Any]:
    """
    Get overall membership statistics
    """
    conn = get_connection()
    if not conn:
        return {}
    
    try:
        cur = conn.cursor()
        
        query = """
            SELECT 
                COUNT(*) as total_members,
                COUNT(*) FILTER (WHERE fee_status IN ('paid', 'active') 
                    AND (fee_expiry_date IS NULL OR fee_expiry_date >= CURRENT_DATE)) as active_members,
                COUNT(*) FILTER (WHERE fee_status NOT IN ('paid', 'active') 
                    OR (fee_expiry_date IS NOT NULL AND fee_expiry_date < CURRENT_DATE)) as inactive_members,
                COUNT(*) FILTER (WHERE fee_expiry_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '7 days') as expiring_soon,
                COUNT(*) FILTER (WHERE created_at >= CURRENT_DATE - INTERVAL '30 days') as new_this_month,
                COALESCE(SUM(total_points), 0) as total_points_all
            FROM users
        """
        
        cur.execute(query)
        row = cur.fetchone()
        
        stats = {
            'total_members': row[0],
            'active_members': row[1],
            'inactive_members': row[2],
            'expiring_soon': row[3],
            'new_this_month': row[4],
            'total_points_all': row[5]
        }
        
        cur.close()
        return stats
        
    except Exception as e:
        logger.error(f"Error fetching membership stats: {e}")
        return {}
