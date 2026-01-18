"""
Challenge Points Engine
Handles point calculations and awards for challenge activities
"""

from datetime import datetime, timedelta
from src.database.connection import DatabaseConnection
from src.database.challenges_operations import add_participant_points
import logging

logger = logging.getLogger(__name__)

# Points configuration for challenge activities
CHALLENGE_POINTS_CONFIG = {
    'checkin': {
        'base_points': 100,
        'bonus_6day': 200,
        'description': '100 points per check-in, 200 bonus for 6+ days/week'
    },
    'water': {
        'points_per_unit': 5,
        'unit_size': 500,  # ml
        'description': '5 points per 500ml glass'
    },
    'weight': {
        'daily_log': 20,
        'description': '20 points for daily weight logging'
    },
    'habits': {
        'points_per_habit': 5,
        'description': '5 points per habit completed'
    },
    'shake': {
        'points_per_shake': 50,
        'description': '50 points per protein shake purchased'
    }
}

def award_challenge_points(user_id: int, challenge_id: int, activity_type: str, 
                          quantity: int = 1, metadata: dict = None) -> int:
    """
    Award points for challenge activities
    
    Args:
        user_id: User ID
        challenge_id: Challenge ID (can be None for non-challenge points)
        activity_type: Type of activity ('checkin', 'water', 'weight', 'habits', 'shake')
        quantity: Amount of activity (default: 1)
        metadata: Additional data for calculation (e.g., weekly_checkins)
    
    Returns:
        int: Points awarded
    """
    try:
        if activity_type not in CHALLENGE_POINTS_CONFIG:
            logger.warning(f"Unknown activity type: {activity_type}")
            return 0
        
        config = CHALLENGE_POINTS_CONFIG[activity_type]
        points = 0
        
        # Calculate points based on activity type
        if activity_type == 'checkin':
            points = config['base_points']
            
            # Check for 6-day bonus
            if metadata and metadata.get('weekly_checkins', 0) >= 6:
                points += config['bonus_6day']
                logger.info(f"User {user_id} earned 6-day check-in bonus!")
        
        elif activity_type == 'water':
            # quantity = ml consumed
            glasses = quantity / config['unit_size']
            points = int(glasses * config['points_per_unit'])
        
        elif activity_type == 'weight':
            points = config['daily_log']
        
        elif activity_type == 'habits':
            # quantity = number of habits completed
            points = quantity * config['points_per_habit']
        
        elif activity_type == 'shake':
            # quantity = number of shakes
            points = quantity * config['points_per_shake']
        
        if points <= 0:
            return 0
        
        # Insert points transaction
        db = DatabaseConnection()
        transaction_query = """
            INSERT INTO points_transactions 
            (user_id, points, transaction_type, description, challenge_id)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING transaction_id
        """
        
        transaction_id = db.execute_insert(transaction_query, (
            user_id, 
            points, 
            activity_type, 
            f"{activity_type.title()} activity", 
            challenge_id
        ))
        
        # Update participant total points if challenge_id provided
        if challenge_id:
            add_participant_points(user_id, challenge_id, points)
        
        logger.info(f"Awarded {points} points to user {user_id} for {activity_type}")
        return points
        
    except Exception as e:
        logger.error(f"Error awarding challenge points: {e}")
        return 0

def get_weekly_checkin_count(user_id: int) -> int:
    """
    Get user's check-in count for current week (Monday-Sunday)
    
    Args:
        user_id: User ID
    
    Returns:
        int: Number of approved check-ins this week
    """
    try:
        db = DatabaseConnection()
        query = """
            SELECT COUNT(*) as count
            FROM attendance_queue
            WHERE user_id = %s
            AND status = 'approved'
            AND approved_at >= DATE_TRUNC('week', CURRENT_DATE)
            AND approved_at < DATE_TRUNC('week', CURRENT_DATE) + INTERVAL '7 days'
        """
        
        result = db.execute_query(query, (user_id,))
        return result['count'] if result else 0
        
    except Exception as e:
        logger.error(f"Error getting weekly check-in count: {e}")
        return 0

def check_and_award_weekly_bonus(user_id: int) -> dict:
    """
    Check if user qualifies for 6-day weekly bonus and award it
    Only awards once per week
    
    Args:
        user_id: User ID
    
    Returns:
        dict: {'awarded': bool, 'points': int, 'message': str}
    """
    try:
        weekly_count = get_weekly_checkin_count(user_id)
        
        if weekly_count < 6:
            return {
                'awarded': False,
                'points': 0,
                'message': f'Need 6+ check-ins, current: {weekly_count}'
            }
        
        # Check if bonus already awarded this week
        db = DatabaseConnection()
        check_query = """
            SELECT COUNT(*) as count
            FROM points_transactions
            WHERE user_id = %s
            AND transaction_type = 'checkin_bonus'
            AND created_at >= DATE_TRUNC('week', CURRENT_DATE)
        """
        
        result = db.execute_query(check_query, (user_id,))
        
        if result and result['count'] > 0:
            return {
                'awarded': False,
                'points': 0,
                'message': 'Weekly bonus already awarded'
            }
        
        # Award bonus
        bonus_points = CHALLENGE_POINTS_CONFIG['checkin']['bonus_6day']
        insert_query = """
            INSERT INTO points_transactions 
            (user_id, points, transaction_type, description)
            VALUES (%s, %s, 'checkin_bonus', 'Weekly 6-day check-in bonus')
        """
        db.execute_insert(insert_query, (user_id, bonus_points))
        
        logger.info(f"Awarded weekly bonus to user {user_id}: {bonus_points} points")
        
        return {
            'awarded': True,
            'points': bonus_points,
            'message': f'🎉 BONUS! +{bonus_points} points for 6+ check-ins this week!'
        }
        
    except Exception as e:
        logger.error(f"Error checking weekly bonus: {e}")
        return {
            'awarded': False,
            'points': 0,
            'message': str(e)
        }

def get_user_daily_activities(user_id: int, activity_date: datetime.date = None) -> dict:
    """
    Get all activities for a user on a specific date
    
    Args:
        user_id: User ID
        activity_date: Date to check (defaults to today)
    
    Returns:
        dict: Activity summary
    """
    try:
        if activity_date is None:
            activity_date = datetime.now().date()
        
        db = DatabaseConnection()
        
        # Check if user checked in
        checkin_query = """
            SELECT COUNT(*) > 0 as checked_in
            FROM attendance_queue
            WHERE user_id = %s
            AND status = 'approved'
            AND DATE(approved_at) = %s
        """
        checkin_result = db.execute_query(checkin_query, (user_id, activity_date))
        
        # Get daily log data
        log_query = """
            SELECT 
                weight,
                water_cups,
                meals_logged,
                habits_completed
            FROM daily_logs
            WHERE user_id = %s
            AND log_date = %s
        """
        log_result = db.execute_query(log_query, (user_id, activity_date))
        
        # Get shake purchases
        shake_query = """
            SELECT COUNT(*) as shake_count
            FROM shake_purchases
            WHERE user_id = %s
            AND DATE(purchase_date) = %s
            AND status = 'approved'
        """
        shake_result = db.execute_query(shake_query, (user_id, activity_date))
        
        return {
            'checkin': checkin_result['checked_in'] if checkin_result else False,
            'water_ml': (log_result['water_cups'] * 500) if log_result and log_result['water_cups'] else 0,
            'weight': float(log_result['weight']) if log_result and log_result['weight'] else None,
            'weight_logged': log_result is not None and log_result.get('weight') is not None,
            'habits_count': log_result['habits_completed'] if log_result and log_result['habits_completed'] else 0,
            'shake_count': shake_result['shake_count'] if shake_result else 0
        }
        
    except Exception as e:
        logger.error(f"Error getting daily activities: {e}")
        return {
            'checkin': False,
            'water_ml': 0,
            'weight': None,
            'weight_logged': False,
            'habits_count': 0,
            'shake_count': 0
        }

def get_challenge_points_summary(user_id: int, challenge_id: int) -> dict:
    """
    Get breakdown of points earned in a challenge
    
    Args:
        user_id: User ID
        challenge_id: Challenge ID
    
    Returns:
        dict: Points breakdown by activity type
    """
    try:
        db = DatabaseConnection()
        query = """
            SELECT 
                transaction_type,
                SUM(points) as total_points,
                COUNT(*) as activity_count
            FROM points_transactions
            WHERE user_id = %s
            AND challenge_id = %s
            GROUP BY transaction_type
            ORDER BY total_points DESC
        """
        
        results = db.execute_query(query, (user_id, challenge_id), fetch_all=True)
        
        breakdown = {}
        total = 0
        
        if results:
            for row in results:
                breakdown[row['transaction_type']] = {
                    'points': int(row['total_points']),
                    'count': int(row['activity_count'])
                }
                total += int(row['total_points'])
        
        return {
            'total_points': total,
            'breakdown': breakdown
        }
        
    except Exception as e:
        logger.error(f"Error getting points summary: {e}")
        return {
            'total_points': 0,
            'breakdown': {}
        }
