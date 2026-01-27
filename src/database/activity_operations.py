import logging
from datetime import datetime
from src.database.connection import execute_query
from src.config import POINTS_CONFIG

logger = logging.getLogger(__name__)

def log_daily_activity(user_id: int, weight: float = None, water_cups: int = 0, 
                       meals_logged: int = 0, habits_completed: bool = False, 
                       attendance: bool = False):
    """Log daily activity for a user"""
    try:
        query = """
            INSERT INTO daily_logs 
            (user_id, log_date, weight, water_cups, meals_logged, habits_completed, attendance)
            VALUES (%s, CURRENT_DATE, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id, log_date) 
            DO UPDATE SET
                weight = COALESCE(EXCLUDED.weight, daily_logs.weight),
                water_cups = daily_logs.water_cups + EXCLUDED.water_cups,
                meals_logged = EXCLUDED.meals_logged,
                habits_completed = EXCLUDED.habits_completed,
                attendance = EXCLUDED.attendance
            RETURNING *
        """
        result = execute_query(query, (user_id, weight, water_cups, meals_logged, habits_completed, attendance), fetch_one=True)
        return result
    except Exception as e:
        logger.error(f"Failed to log daily activity: {e}")
        return None

def get_today_log(user_id: int):
    """Get today's activity log for user"""
    query = "SELECT * FROM daily_logs WHERE user_id = %s AND log_date = CURRENT_DATE"
    return execute_query(query, (user_id,), fetch_one=True)

def get_yesterday_weight(user_id: int):
    """Get user's weight from yesterday for comparison"""
    from src.config import USE_LOCAL_DB
    if USE_LOCAL_DB:
        # SQLite syntax
        query = """
            SELECT weight FROM daily_logs 
            WHERE user_id = ? AND log_date = date('now', '-1 day')
            AND weight IS NOT NULL
        """
    else:
        # PostgreSQL syntax
        query = """
            SELECT weight FROM daily_logs 
            WHERE user_id = %s AND log_date = CURRENT_DATE - INTERVAL '1 day'
            AND weight IS NOT NULL
        """
    result = execute_query(query, (user_id,), fetch_one=True)
    return result['weight'] if result else None

def get_today_weight(user_id: int):
    """Check if weight was already logged today"""
    query = """
        SELECT weight FROM daily_logs 
        WHERE user_id = %s AND log_date = CURRENT_DATE
        AND weight IS NOT NULL
    """
    result = execute_query(query, (user_id,), fetch_one=True)
    return result['weight'] if result else None

def log_weight(user_id: int, weight: float):
    """Log weight for today"""
    query = """
        INSERT INTO daily_logs (user_id, log_date, weight)
        VALUES (%s, CURRENT_DATE, %s)
        ON CONFLICT (user_id, log_date)
        DO UPDATE SET weight = %s
        RETURNING *
    """
    result = execute_query(query, (user_id, weight, weight), fetch_one=True)
    if result:
        logger.info(f"Weight logged for user {user_id}: {weight}kg")
        add_points(user_id, POINTS_CONFIG['weight_log'], 'weight_log', f'Weight logged: {weight}kg')
    return result

def log_water(user_id: int, cups: int = 1):
    """Log water intake"""
    query = """
        INSERT INTO daily_logs (user_id, log_date, water_cups)
        VALUES (%s, CURRENT_DATE, %s)
        ON CONFLICT (user_id, log_date)
        DO UPDATE SET water_cups = daily_logs.water_cups + %s
        RETURNING *
    """
    result = execute_query(query, (user_id, cups, cups), fetch_one=True)
    if result:
        points = POINTS_CONFIG['water_500ml'] * cups
        logger.info(f"Water logged for user {user_id}: {cups} cups")
        add_points(user_id, points, 'water_intake', f'Water: {cups} x 500ml')
    return result

def log_meal(user_id: int):
    """Log meal photo"""
    query = """
        INSERT INTO daily_logs (user_id, log_date, meals_logged)
        VALUES (%s, CURRENT_DATE, 1)
        ON CONFLICT (user_id, log_date)
        DO UPDATE SET meals_logged = daily_logs.meals_logged + 1
        WHERE daily_logs.meals_logged < 4
        RETURNING *
    """
    result = execute_query(query, (user_id,), fetch_one=True)
    if result:
        logger.info(f"Meal logged for user {user_id}")
        add_points(user_id, POINTS_CONFIG['meal_photo'], 'meal_photo', 'Meal photo logged')
    return result

def log_habits(user_id: int):
    """Mark habits as completed"""
    query = """
        INSERT INTO daily_logs (user_id, log_date, habits_completed)
        VALUES (%s, CURRENT_DATE, true)
        ON CONFLICT (user_id, log_date)
        DO UPDATE SET habits_completed = true
        RETURNING *
    """
    result = execute_query(query, (user_id,), fetch_one=True)
    if result:
        logger.info(f"Habits completed for user {user_id}")
        add_points(user_id, POINTS_CONFIG['habits_complete'], 'habits_complete', 'Daily habits completed')
    return result

def add_points(user_id: int, points: int, activity: str, description: str = ""):
    """Add points to user"""
    try:
        # Add to points_transactions
        query1 = """
            INSERT INTO points_transactions (user_id, points, activity, description)
            VALUES (%s, %s, %s, %s)
        """
        execute_query(query1, (user_id, points, activity, description))
        
        # Update user total_points
        query2 = "UPDATE users SET total_points = total_points + %s WHERE user_id = %s"
        execute_query(query2, (points, user_id))
        
        logger.info(f"Added {points} points to user {user_id} for {activity}")
        return True
    except Exception as e:
        logger.error(f"Failed to add points: {e}")
        return False

def get_user_points(user_id: int):
    """Get user's total points"""
    query = "SELECT total_points FROM users WHERE user_id = %s"
    result = execute_query(query, (user_id,), fetch_one=True)
    return result['total_points'] if result else 0

def get_leaderboard(limit: int = 10):
    """Get top users by points"""
    query = """
        SELECT user_id, full_name, total_points, telegram_username
        FROM users
        WHERE fee_status = 'paid'
        ORDER BY total_points DESC
        LIMIT %s
    """
    return execute_query(query, (limit,))
