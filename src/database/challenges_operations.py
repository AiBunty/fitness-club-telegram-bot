import logging
from datetime import datetime, timedelta
from src.database.connection import execute_query

logger = logging.getLogger(__name__)

# Challenge Types
CHALLENGE_TYPES = {
    'weight_loss': {'name': '💪 Weight Loss', 'goal': 'Lose 2kg', 'duration': 30},
    'consistency': {'name': '🔥 30-Day Streak', 'goal': '30 gym check-ins', 'duration': 30},
    'water_challenge': {'name': '💧 Hydration', 'goal': '100 cups of water', 'duration': 7},
    'gym_warrior': {'name': '🏋️ Gym Warrior', 'goal': '20 gym visits', 'duration': 30},
    'meal_prep': {'name': '🍽️ Meal Prep', 'goal': 'Log 60 meals', 'duration': 30},
}

def create_challenge(challenge_type: str, start_date: datetime = None, duration_days: int = None):
    """Create a new challenge"""
    try:
        if challenge_type not in CHALLENGE_TYPES:
            return None
        
        challenge_config = CHALLENGE_TYPES[challenge_type]
        
        if not start_date:
            start_date = datetime.now()
        if not duration_days:
            duration_days = challenge_config['duration']
        
        end_date = start_date + timedelta(days=duration_days)
        
        query = """
            INSERT INTO challenges (challenge_type, start_date, end_date, status)
            VALUES (%s, %s, %s, 'active')
            RETURNING *
        """
        result = execute_query(query, (challenge_type, start_date, end_date), fetch_one=True)
        logger.info(f"Challenge created: {challenge_type}")
        return result
    except Exception as e:
        logger.error(f"Failed to create challenge: {e}")
        return None

def join_challenge(user_id: int, challenge_id: int):
    """User joins a challenge"""
    try:
        query = """
            INSERT INTO challenge_participants (challenge_id, user_id, joined_date, status)
            VALUES (%s, %s, CURRENT_TIMESTAMP, 'active')
            RETURNING *
        """
        result = execute_query(query, (challenge_id, user_id), fetch_one=True)
        logger.info(f"User {user_id} joined challenge {challenge_id}")
        return result
    except Exception as e:
        logger.error(f"Failed to join challenge: {e}")
        return None

def get_active_challenges():
    """Get all currently active challenges"""
    query = """
        SELECT * FROM challenges
        WHERE status = 'active'
        AND end_date >= CURRENT_DATE
        ORDER BY end_date ASC
    """
    return execute_query(query)

def get_user_challenges(user_id: int):
    """Get challenges user is participating in"""
    query = """
        SELECT 
            c.*,
            cp.status as participation_status,
            cp.joined_date
        FROM challenges c
        JOIN challenge_participants cp ON c.challenge_id = cp.challenge_id
        WHERE cp.user_id = %s
        AND c.status = 'active'
        ORDER BY c.end_date ASC
    """
    return execute_query(query, (user_id,))

def get_challenge_progress(challenge_id: int, user_id: int):
    """Get user's progress on a challenge"""
    query = """
        SELECT c.*, cp.*, cp.progress_value as current_progress
        FROM challenges c
        JOIN challenge_participants cp ON c.challenge_id = cp.challenge_id
        WHERE c.challenge_id = %s AND cp.user_id = %s
    """
    result = execute_query(query, (challenge_id, user_id), fetch_one=True)
    
    if not result:
        return None
    
    # Calculate progress based on challenge type
    challenge_type = result['challenge_type']
    
    if challenge_type == 'weight_loss':
        # Get weight loss progress
        weight_query = """
            SELECT 
                (SELECT weight FROM daily_logs 
             WHERE user_id = %s AND log_date >= %s 
             ORDER BY log_date ASC LIMIT 1) as start_weight,
                (SELECT weight FROM daily_logs 
             WHERE user_id = %s AND weight IS NOT NULL
             ORDER BY log_date DESC LIMIT 1) as current_weight
        """
        weight_result = execute_query(weight_query, (user_id, result['start_date'], user_id), fetch_one=True)
        if weight_result and weight_result['start_weight'] and weight_result['current_weight']:
            result['progress'] = weight_result['start_weight'] - weight_result['current_weight']
    
    elif challenge_type == 'consistency':
        # Count gym visits
        visits_query = """
            SELECT COUNT(*) as visits
            FROM attendance_queue
            WHERE user_id = %s AND status = 'approved'
            AND request_date >= %s
        """
        visits_result = execute_query(visits_query, (user_id, result['start_date']), fetch_one=True)
        result['progress'] = visits_result['visits'] if visits_result else 0
    
    elif challenge_type == 'water_challenge':
        # Sum water cups
        water_query = """
            SELECT SUM(water_cups) as total_water
            FROM daily_logs
            WHERE user_id = %s AND log_date >= %s
        """
        water_result = execute_query(water_query, (user_id, result['start_date']), fetch_one=True)
        result['progress'] = water_result['total_water'] if water_result and water_result['total_water'] else 0
    
    elif challenge_type == 'gym_warrior':
        # Count gym visits
        visits_query = """
            SELECT COUNT(*) as visits
            FROM attendance_queue
            WHERE user_id = %s AND status = 'approved'
            AND request_date >= %s
        """
        visits_result = execute_query(visits_query, (user_id, result['start_date']), fetch_one=True)
        result['progress'] = visits_result['visits'] if visits_result else 0
    
    elif challenge_type == 'meal_prep':
        # Count meals logged
        meals_query = """
            SELECT SUM(meals_logged) as total_meals
            FROM daily_logs
            WHERE user_id = %s AND log_date >= %s
        """
        meals_result = execute_query(meals_query, (user_id, result['start_date']), fetch_one=True)
        result['progress'] = meals_result['total_meals'] if meals_result and meals_result['total_meals'] else 0
    
    return result

def get_challenge_leaderboard(challenge_id: int, limit: int = 10):
    """Get leaderboard for a specific challenge"""
    query = """
        SELECT 
            u.user_id,
            u.full_name,
            cp.progress_value,
            cp.status,
            cp.joined_date,
            ROW_NUMBER() OVER (ORDER BY cp.progress_value DESC) as rank
        FROM challenge_participants cp
        JOIN users u ON cp.user_id = u.user_id
        WHERE cp.challenge_id = %s
        ORDER BY cp.progress_value DESC
        LIMIT %s
    """
    return execute_query(query, (challenge_id, limit))

def award_challenge_reward(user_id: int, challenge_id: int, reward_points: int = 100):
    """Award points for completing a challenge"""
    try:
        query1 = """
            INSERT INTO points_transactions (user_id, points, activity, description)
            VALUES (%s, %s, 'challenge_completion', 'Challenge completed bonus')
        """
        execute_query(query1, (user_id, reward_points))
        
        query2 = "UPDATE users SET total_points = total_points + %s WHERE user_id = %s"
        execute_query(query2, (reward_points, user_id))
        
        query3 = """
            UPDATE challenge_participants
            SET status = 'completed'
            WHERE challenge_id = %s AND user_id = %s
        """
        execute_query(query3, (challenge_id, user_id))
        
        logger.info(f"Challenge reward awarded to user {user_id}: {reward_points} points")
        return True
    except Exception as e:
        logger.error(f"Failed to award challenge reward: {e}")
        return False

def get_challenge_stats():
    """Get overall challenge statistics"""
    query = """
        SELECT 
            COUNT(*) as total_challenges,
            COUNT(CASE WHEN status = 'active' THEN 1 END) as active_challenges,
            COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_challenges,
            (SELECT COUNT(*) FROM challenge_participants WHERE status = 'active') as active_participants,
            (SELECT COUNT(DISTINCT user_id) FROM challenge_participants 
             WHERE status = 'completed') as users_completed
        FROM challenges
    """
    return execute_query(query, fetch_one=True)

def update_challenge_progress(user_id: int, challenge_id: int, progress_value: int):
    """Update user's progress on a challenge"""
    try:
        query = """
            UPDATE challenge_participants
            SET progress_value = %s
            WHERE challenge_id = %s AND user_id = %s
        """
        execute_query(query, (progress_value, challenge_id, user_id))
        logger.info(f"Challenge progress updated for user {user_id}: {progress_value}")
        return True
    except Exception as e:
        logger.error(f"Failed to update challenge progress: {e}")
        return False
