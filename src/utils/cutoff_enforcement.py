"""
Daily Cutoff Enforcement
Handles 8 PM cutoff for all daily activity logging
"""

from datetime import datetime, time
import logging

logger = logging.getLogger(__name__)

# Daily cutoff time (8:00 PM)
DAILY_CUTOFF_TIME = time(20, 0)  # 8:00 PM

# Global flag (can be toggled by scheduled job)
_daily_logging_open = True

def is_logging_window_open() -> bool:
    """
    Check if daily logging window is currently open
    Logging closes at 8:00 PM daily
    
    Returns:
        bool: True if before cutoff, False if after cutoff
    """
    global _daily_logging_open
    
    current_time = datetime.now().time()
    
    # If after 8 PM, logging is closed
    if current_time >= DAILY_CUTOFF_TIME:
        _daily_logging_open = False
        return False
    
    # Before 8 PM, logging is open
    _daily_logging_open = True
    return True

def get_cutoff_message() -> str:
    """
    Get the message to show when logging window is closed
    
    Returns:
        str: Cutoff message
    """
    return (
        "⏰ Daily logging window closed at 8:00 PM.\n\n"
        "All activities must be logged before 8 PM daily:\n"
        "• Weight logs\n"
        "• Water intake\n"
        "• Meals & habits\n"
        "• Gym check-ins\n\n"
        "Come back tomorrow! 💪"
    )

def get_cutoff_info() -> dict:
    """
    Get information about the cutoff time
    
    Returns:
        dict: Cutoff information
    """
    return {
        'cutoff_time': '20:00',  # 8:00 PM in 24-hour format
        'cutoff_display': '8:00 PM',
        'is_open': is_logging_window_open(),
        'activities_affected': [
            'Weight logging',
            'Water intake',
            'Meal logging',
            'Habit tracking',
            'Gym check-in'
        ]
    }

def get_cutoff_warning_message() -> str:
    """
    Get a warning message to show before cutoff (e.g., at 7 PM)
    
    Returns:
        str: Warning message
    """
    return (
        "⚠️ Reminder: Daily Cutoff at 8:00 PM\n\n"
        "You have less than 1 hour to log:\n"
        "• Today's weight\n"
        "• Water intake\n"
        "• Meals & habits\n"
        "• Gym check-in\n\n"
        "Don't miss your points! ⏰"
    )

def enforce_cutoff_check(activity_name: str = "activity") -> tuple:
    """
    Check if activity is allowed based on cutoff time
    Returns (allowed, message)
    
    Args:
        activity_name: Name of the activity being attempted
    
    Returns:
        tuple: (bool: allowed, str: message if not allowed)
    """
    if is_logging_window_open():
        return (True, None)
    else:
        logger.info(f"Activity '{activity_name}' blocked - after cutoff time")
        return (False, get_cutoff_message())

def get_time_until_cutoff() -> dict:
    """
    Get time remaining until cutoff
    
    Returns:
        dict: Time information
    """
    now = datetime.now()
    cutoff_today = datetime.combine(now.date(), DAILY_CUTOFF_TIME)
    
    if now.time() >= DAILY_CUTOFF_TIME:
        return {
            'cutoff_passed': True,
            'hours_remaining': 0,
            'minutes_remaining': 0
        }
    
    time_remaining = cutoff_today - now
    hours = time_remaining.seconds // 3600
    minutes = (time_remaining.seconds % 3600) // 60
    
    return {
        'cutoff_passed': False,
        'hours_remaining': hours,
        'minutes_remaining': minutes
    }

def should_send_cutoff_warning() -> bool:
    """
    Check if cutoff warning should be sent (e.g., at 7 PM)
    
    Returns:
        bool: True if warning should be sent
    """
    now = datetime.now().time()
    warning_time = time(19, 0)  # 7:00 PM
    warning_end = time(19, 5)   # 7:05 PM (5-minute window)
    
    return warning_time <= now < warning_end

# Challenge start notification message with cutoff info
def get_challenge_start_cutoff_message(challenge_name: str, start_date: str, 
                                      end_date: str, price: str) -> str:
    """
    Get challenge start message with cutoff information
    
    Args:
        challenge_name: Name of the challenge
        start_date: Start date string
        end_date: End date string
        price: Price string (e.g., "FREE" or "Rs. 500")
    
    Returns:
        str: Formatted message
    """
    return f"""🏆 Challenge Started: {challenge_name}

📅 Duration: {start_date} - {end_date}
💰 Entry Fee: {price}

⏰ IMPORTANT: Daily Cutoff Time
🕗 All activities close at 8:00 PM daily
   • Weight logs
   • Water intake
   • Meals & Habits
   • Gym check-ins

Plan your day accordingly! ⚡

Points will be calculated at 10:00 PM each night.
"""

def get_welcome_message_with_cutoff(challenge_name: str) -> str:
    """
    Get welcome message when user joins challenge
    
    Args:
        challenge_name: Name of the challenge
    
    Returns:
        str: Welcome message
    """
    return f"""✅ Welcome to {challenge_name}!

⏰ Daily Cutoff: 8:00 PM
All activities must be logged before 8 PM daily.

📊 Points are calculated at 10 PM each night.
🏆 Check leaderboard anytime: /leaderboard

Good luck! 💪
"""
