import logging
from datetime import datetime, timedelta, date
from src.database.connection import execute_query, DatabaseConnection

logger = logging.getLogger(__name__)

# Challenge Types
CHALLENGE_TYPES = {
    'weight_loss': {'name': '💪 Weight Loss', 'goal': 'Lose 2kg', 'duration': 30},
    'consistency': {'name': '🔥 30-Day Streak', 'goal': '30 gym check-ins', 'duration': 30},
    'water_challenge': {'name': '💧 Hydration', 'goal': '100 cups of water', 'duration': 7},
    'gym_warrior': {'name': '🏋️ Gym Warrior', 'goal': '20 gym visits', 'duration': 30},
    'meal_prep': {'name': '🍽️ Meal Prep', 'goal': 'Log 60 meals', 'duration': 30},
}

def create_challenge(challenge_type: str, start_date: datetime = None, duration_days: int = None,
                    name: str = None, description: str = None, price: float = 0, 
                    is_free: bool = True, created_by: int = None):
    """Create a new challenge with pricing and admin info"""
    try:
        if challenge_type not in CHALLENGE_TYPES:
            return None
        
        challenge_config = CHALLENGE_TYPES[challenge_type]
        
        if not start_date:
            start_date = datetime.now()
        if not duration_days:
            duration_days = challenge_config['duration']
        if not name:
            name = challenge_config['name']
        
        end_date = start_date + timedelta(days=duration_days)
        
        # Convert datetime to date if needed
        if isinstance(start_date, datetime):
            start_date = start_date.date()
        if isinstance(end_date, datetime):
            end_date = end_date.date()
        
        # Determine status based on start date
        status = 'scheduled' if start_date > date.today() else 'active'
        
        query1 = """
            INSERT INTO challenges 
            (name, description, challenge_type, start_date, end_date, 
             price, is_free, status, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        execute_query(
            query1, 
            (name, description, challenge_type, start_date, end_date, 
             price, is_free, status, created_by)
        )
        
        # Get the created challenge
        query2 = "SELECT challenge_id, name, challenge_type, start_date, end_date, price, is_free, status FROM challenges WHERE name = %s AND challenge_type = %s ORDER BY challenge_id DESC LIMIT 1"
        result = execute_query(query2, (name, challenge_type), fetch_one=True)
        logger.info(f"Challenge created: {challenge_type} - {name}")
        return result
    except Exception as e:
        logger.error(f"Failed to create challenge: {e}")
        return None

def join_challenge(user_id: int, challenge_id: int, status: str = 'approved'):
    """User joins a challenge"""
    try:
        query1 = """
            INSERT INTO challenge_participants (challenge_id, user_id, joined_date, status)
            VALUES (%s, %s, CURRENT_TIMESTAMP, %s)
        """
        execute_query(query1, (challenge_id, user_id, status))
        
        # Get the created record
        query2 = "SELECT * FROM challenge_participants WHERE user_id = %s AND challenge_id = %s ORDER BY participant_id DESC LIMIT 1"
        result = execute_query(query2, (user_id, challenge_id), fetch_one=True)
        logger.info(f"User {user_id} joined challenge {challenge_id} with status {status}")
        return result
    except Exception as e:
        logger.error(f"Failed to join challenge: {e}")
        return None

def is_user_in_challenge(user_id: int, challenge_id: int) -> bool:
    """Check if user is participating in a challenge"""
    try:
        query = """
            SELECT 1 FROM challenge_participants
            WHERE user_id = %s AND challenge_id = %s
            LIMIT 1
        """
        result = execute_query(query, (user_id, challenge_id), fetch_one=True)
        return bool(result)
    except Exception as e:
        logger.error(f"Error checking user in challenge: {e}")
        return False

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

def get_challenge_by_id(challenge_id: int):
    """Get challenge details by ID"""
    query = """
        SELECT * FROM challenges
        WHERE challenge_id = %s
    """
    return execute_query(query, (challenge_id,), fetch_one=True)

def get_scheduled_challenges():
    """Get challenges scheduled to start today"""
    query = """
        SELECT * FROM challenges
        WHERE status = 'scheduled'
        AND start_date = CURRENT_DATE
        AND broadcast_sent = FALSE
        ORDER BY start_date ASC
    """
    return execute_query(query)

def mark_challenge_broadcast_sent(challenge_id: int):
    """Mark challenge as having broadcast sent"""
    try:
        query = """
            UPDATE challenges
            SET broadcast_sent = TRUE, status = 'active'
            WHERE challenge_id = %s
        """
        execute_query(query, (challenge_id,))
        logger.info(f"Challenge {challenge_id} marked as broadcast sent")
        return True
    except Exception as e:
        logger.error(f"Failed to mark broadcast sent: {e}")
        return False

def get_participant_data(user_id: int, challenge_id: int):
    """Get detailed participant data including daily progress"""
    query = """
        SELECT 
            cp.*,
            c.name as challenge_name,
            c.challenge_type,
            c.start_date,
            c.end_date,
            u.full_name,
            u.username
        FROM challenge_participants cp
        JOIN challenges c ON cp.challenge_id = c.challenge_id
        JOIN users u ON cp.user_id = u.user_id
        WHERE cp.user_id = %s AND cp.challenge_id = %s
    """
    return execute_query(query, (user_id, challenge_id), fetch_one=True)

def get_challenge_participants(challenge_id: int, status: str = None, limit: int = None):
    """Get all participants for a challenge, optionally filtered by status"""
    if status:
        query = """
            SELECT 
                cp.*,
                u.full_name as user_name,
                u.username
            FROM challenge_participants cp
            JOIN users u ON cp.user_id = u.user_id
            WHERE cp.challenge_id = %s AND cp.status = %s
            ORDER BY cp.total_points DESC
        """
        if limit:
            query += f" LIMIT {limit}"
        return execute_query(query, (challenge_id, status))
    else:
        query = """
            SELECT 
                cp.*,
                u.full_name as user_name,
                u.username
            FROM challenge_participants cp
            JOIN users u ON cp.user_id = u.user_id
            WHERE cp.challenge_id = %s
            ORDER BY cp.total_points DESC
        """
        if limit:
            query += f" LIMIT {limit}"
        return execute_query(query, (challenge_id,))

def update_participant_daily_progress(user_id: int, challenge_id: int, 
                                     date_key: str, daily_data: dict):
    """Update participant's daily progress JSON"""
    try:
        import json
        db = DatabaseConnection()
        
        query = """
            UPDATE challenge_participants 
            SET daily_progress = jsonb_set(
                COALESCE(daily_progress, '{}'::jsonb),
                %s::text[],
                %s::jsonb
            )
            WHERE challenge_id = %s AND user_id = %s
        """
        
        db.execute_update(query, (
            [date_key],
            json.dumps(daily_data),
            challenge_id,
            user_id
        ))
        
        logger.info(f"Updated daily progress for user {user_id} on {date_key}")
        return True
    except Exception as e:
        logger.error(f"Failed to update daily progress: {e}")
        return False

def add_participant_points(user_id: int, challenge_id: int, points: int):
    """Add points to participant's total"""
    try:
        query = """
            UPDATE challenge_participants
            SET total_points = total_points + %s
            WHERE challenge_id = %s AND user_id = %s
        """
        execute_query(query, (points, challenge_id, user_id))
        logger.info(f"Added {points} points to user {user_id} in challenge {challenge_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to add participant points: {e}")
        return False

def complete_challenge(challenge_id: int):
    """Mark challenge as completed and update all participants"""
    try:
        # Update challenge status
        query1 = """
            UPDATE challenges
            SET status = 'completed'
            WHERE challenge_id = %s
        """
        execute_query(query1, (challenge_id,))
        
        # Update all active participants to completed
        query2 = """
            UPDATE challenge_participants
            SET status = 'completed'
            WHERE challenge_id = %s AND status = 'active'
        """
        execute_query(query2, (challenge_id,))
        
        logger.info(f"Challenge {challenge_id} marked as completed")
        return True
    except Exception as e:
        logger.error(f"Failed to complete challenge: {e}")
        return False

def get_user_rank_in_challenge(user_id: int, challenge_id: int) -> int:
    """Get user's rank in a specific challenge"""
    query = """
        SELECT rank FROM (
            SELECT 
                user_id,
                RANK() OVER (ORDER BY total_points DESC) as rank
            FROM challenge_participants
            WHERE challenge_id = %s 
            AND approval_status = 'approved'
            AND status = 'active'
        ) ranked
        WHERE user_id = %s
    """
    result = execute_query(query, (challenge_id, user_id), fetch_one=True)
    return result['rank'] if result else None
