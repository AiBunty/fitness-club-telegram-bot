"""
Attendance eligibility check - reuses existing subscription logic
Enforces grace period rules (3 days max, 3 attendances max if unpaid)
"""

import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def check_attendance_eligibility(user_id: int) -> dict:
    """
    Check if user is eligible to mark attendance
    Reuses existing subscription_operations functions
    
    Args:
        user_id: Telegram user ID
    
    Returns:
        {
            'eligible': bool,
            'reason': str,
            'grace_days_left': int,
            'grace_attempts_left': int
        }
    """
    try:
        from src.database.subscription_operations import is_subscription_active, is_in_grace_period
        from src.database.user_operations import get_user
        
        # Get user data
        user = get_user(user_id)
        if not user:
            logger.warning(f"User not found: {user_id}")
            return {
                'eligible': False,
                'reason': 'USER_NOT_FOUND',
                'grace_days_left': 0,
                'grace_attempts_left': 0
            }
        
        # Check subscription status
        if is_subscription_active(user_id):
            logger.debug(f"User {user_id} has active subscription")
            return {
                'eligible': True,
                'reason': 'SUBSCRIPTION_ACTIVE',
                'grace_days_left': 0,
                'grace_attempts_left': 0
            }
        
        # Check if in grace period
        if is_in_grace_period(user_id):
            logger.debug(f"User {user_id} is in grace period")
            # TODO: Track grace usage (3 attempts, 3 days max)
            # For MVP: Allow all grace period attempts
            return {
                'eligible': True,
                'reason': 'GRACE_PERIOD_ACTIVE',
                'grace_days_left': 3,
                'grace_attempts_left': 3
            }
        
        # Not eligible
        logger.info(f"User {user_id} not eligible: subscription unpaid and grace expired")
        return {
            'eligible': False,
            'reason': 'SUBSCRIPTION_UNPAID',
            'grace_days_left': 0,
            'grace_attempts_left': 0
        }
        
    except Exception as e:
        logger.error(f"Error checking attendance eligibility for user {user_id}: {e}")
        return {
            'eligible': False,
            'reason': 'SERVER_ERROR',
            'grace_days_left': 0,
            'grace_attempts_left': 0
        }
