import logging
from datetime import datetime, timedelta
from src.database.connection import execute_query

logger = logging.getLogger(__name__)

def get_user_statistics(user_id: int):
    """Get comprehensive statistics for a user"""
    stats = {}
    
    # Total points
    query1 = "SELECT total_points FROM users WHERE user_id = %s"
    result = execute_query(query1, (user_id,), fetch_one=True)
    stats['total_points'] = result['total_points'] if result else 0
    
    # Today's activity
    query2 = "SELECT * FROM daily_logs WHERE user_id = %s AND log_date = CURRENT_DATE"
    result = execute_query(query2, (user_id,), fetch_one=True)
    stats['today_activity'] = result if result else None
    
    # This week stats
    query3 = """
        SELECT 
            COUNT(*) as days_logged,
            SUM(CASE WHEN weight IS NOT NULL THEN 1 ELSE 0 END) as weight_logs,
            SUM(water_cups) as total_water,
            SUM(meals_logged) as total_meals,
            COUNT(CASE WHEN habits_completed THEN 1 END) as habits_completed,
            COUNT(CASE WHEN attendance THEN 1 END) as attendance_count
        FROM daily_logs
        WHERE user_id = %s 
        AND log_date >= CURRENT_DATE - INTERVAL '7 days'
    """
    result = execute_query(query3, (user_id,), fetch_one=True)
    stats['weekly'] = result if result else None
    
    # Monthly stats
    query4 = """
        SELECT 
            COUNT(*) as days_logged,
            SUM(CASE WHEN weight IS NOT NULL THEN 1 ELSE 0 END) as weight_logs,
            SUM(water_cups) as total_water,
            SUM(meals_logged) as total_meals,
            COUNT(CASE WHEN habits_completed THEN 1 END) as habits_completed
        FROM daily_logs
        WHERE user_id = %s 
        AND log_date >= DATE_TRUNC('month', CURRENT_DATE)
    """
    result = execute_query(query4, (user_id,), fetch_one=True)
    stats['monthly'] = result if result else None
    
    # Weight progress
    query5 = """
        SELECT weight, log_date 
        FROM daily_logs
        WHERE user_id = %s AND weight IS NOT NULL
        ORDER BY log_date DESC
        LIMIT 2
    """
    results = execute_query(query5, (user_id,))
    if results and len(results) >= 2:
        current_weight = results[0]['weight']
        initial_weight = results[-1]['weight']
        stats['weight_change'] = initial_weight - current_weight
        stats['current_weight'] = current_weight
    
    return stats

def get_leaderboard_with_stats(limit: int = 10):
    """Get leaderboard with detailed statistics"""
    query = """
        SELECT 
            u.user_id,
            u.full_name,
            u.total_points,
            u.fee_status,
            COUNT(DISTINCT dl.log_date) as days_active,
            COUNT(DISTINCT CASE WHEN dl.attendance THEN dl.log_date END) as gym_visits,
            SUM(dl.water_cups) as total_water,
            ROW_NUMBER() OVER (ORDER BY u.total_points DESC) as rank
        FROM users u
        LEFT JOIN daily_logs dl ON u.user_id = dl.user_id 
            AND dl.log_date >= CURRENT_DATE - INTERVAL '30 days'
        WHERE u.fee_status = 'paid'
        GROUP BY u.user_id, u.full_name, u.total_points, u.fee_status
        ORDER BY u.total_points DESC
        LIMIT %s
    """
    return execute_query(query, (limit,))

def get_weight_progress(user_id: int, days: int = 30):
    """Get user's weight progression"""
    query = """
        SELECT log_date, weight 
        FROM daily_logs
        WHERE user_id = %s 
        AND weight IS NOT NULL
        AND log_date >= CURRENT_DATE - %s * INTERVAL '1 day'
        ORDER BY log_date ASC
    """
    return execute_query(query, (user_id, days))

def get_consistency_stats(user_id: int):
    """Get user's consistency metrics"""
    query = """
        SELECT 
            COUNT(*) as total_days,
            COUNT(CASE WHEN weight IS NOT NULL THEN 1 END) as weight_log_days,
            COUNT(CASE WHEN water_cups > 0 THEN 1 END) as water_log_days,
            COUNT(CASE WHEN meals_logged > 0 THEN 1 END) as meal_log_days,
            COUNT(CASE WHEN habits_completed THEN 1 END) as habit_days,
            COUNT(CASE WHEN attendance THEN 1 END) as gym_days
        FROM daily_logs
        WHERE user_id = %s
        AND log_date >= CURRENT_DATE - INTERVAL '30 days'
    """
    return execute_query(query, (user_id,), fetch_one=True)

def get_top_activities():
    """Get most common activities among all users"""
    query = """
        SELECT 
            activity,
            COUNT(*) as frequency,
            SUM(points) as total_points,
            AVG(points) as avg_points
        FROM points_transactions
        WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
        GROUP BY activity
        ORDER BY frequency DESC
    """
    return execute_query(query)

def get_engagement_metrics():
    """Get overall platform engagement"""
    query = """
        SELECT 
            COUNT(DISTINCT pt.user_id) as active_users,
            COUNT(DISTINCT CASE WHEN u.fee_status = 'paid' THEN u.user_id END) as paid_members,
            SUM(pt.points) as total_points_awarded,
            AVG(pt.points) as avg_points_per_activity,
            COUNT(*) as total_transactions
        FROM points_transactions pt
        LEFT JOIN users u ON pt.user_id = u.user_id
        WHERE pt.created_at >= CURRENT_DATE - INTERVAL '30 days'
    """
    return execute_query(query, fetch_one=True)

def get_weekly_comparison(user_id: int):
    """Compare user's current week vs previous week"""
    query = """
        SELECT 
            CASE 
                WHEN log_date >= CURRENT_DATE - INTERVAL '7 days' THEN 'Current'
                ELSE 'Previous'
            END as week,
            COUNT(*) as days_logged,
            SUM(CASE WHEN weight IS NOT NULL THEN 1 ELSE 0 END) as weight_logs,
            SUM(water_cups) as total_water,
            SUM(meals_logged) as total_meals
        FROM daily_logs
        WHERE user_id = %s
        AND log_date >= CURRENT_DATE - INTERVAL '14 days'
        GROUP BY week
    """
    return execute_query(query, (user_id,))

def get_attendance_streak(user_id: int):
    """Get user's current gym attendance streak"""
    query = """
        WITH RECURSIVE streak AS (
            SELECT 
                request_date,
                1 as streak_count,
                request_date as streak_start
            FROM attendance_queue
            WHERE user_id = %s 
            AND status = 'approved'
            AND request_date >= CURRENT_DATE - INTERVAL '100 days'
            
            UNION ALL
            
            SELECT 
                aq.request_date,
                s.streak_count + 1,
                s.streak_start
            FROM streak s
            JOIN attendance_queue aq ON aq.request_date = s.request_date + INTERVAL '1 day'
            WHERE aq.user_id = %s
            AND aq.status = 'approved'
        )
        SELECT MAX(streak_count) as current_streak
        FROM streak
        WHERE streak_start = (SELECT MAX(request_date) FROM attendance_queue 
                            WHERE user_id = %s AND status = 'approved') 
                            - (SELECT COUNT(*) - 1 FROM streak)
    """
    result = execute_query(query, (user_id, user_id, user_id), fetch_one=True)
    return result['current_streak'] if result else 0

def get_platform_statistics():
    """Get overall platform statistics"""
    query = """
        SELECT 
            (SELECT COUNT(*) FROM users) as total_users,
            (SELECT COUNT(*) FROM users WHERE fee_status = 'paid') as active_members,
            (SELECT SUM(total_points) FROM users) as total_points,
            (SELECT COUNT(*) FROM points_transactions 
             WHERE created_at >= CURRENT_DATE) as today_activities,
            (SELECT AVG(total_points) FROM users WHERE total_points > 0) as avg_points,
            (SELECT COUNT(DISTINCT user_id) FROM daily_logs 
             WHERE log_date = CURRENT_DATE) as today_users
    """
    return execute_query(query, fetch_one=True)
