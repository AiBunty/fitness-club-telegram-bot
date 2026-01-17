"""
Scheduled jobs for automated tasks
"""
import logging
from datetime import datetime
from telegram.ext import ContextTypes
from src.utils.report_generator import generate_eod_report
from src.database.reports_operations import move_expired_to_inactive
from src.database.user_operations import get_all_paid_users
from src.config import SUPER_ADMIN_USER_ID

logger = logging.getLogger(__name__)


async def send_eod_report(context: ContextTypes.DEFAULT_TYPE):
    """
    Send End of Day report to admin at 23:55
    """
    try:
        logger.info("Generating EOD report...")
        
        report = generate_eod_report()
        
        # Send to super admin
        if SUPER_ADMIN_USER_ID:
            await context.bot.send_message(
                chat_id=int(SUPER_ADMIN_USER_ID),
                text=report,
                parse_mode="Markdown"
            )
            logger.info(f"EOD report sent to admin {SUPER_ADMIN_USER_ID}")
        else:
            logger.warning("SUPER_ADMIN_USER_ID not configured, EOD report not sent")
    
    except Exception as e:
        logger.error(f"Error sending EOD report: {e}")


async def check_expired_memberships(context: ContextTypes.DEFAULT_TYPE):
    """
    Check and move expired memberships to inactive (7-day grace period)
    Runs daily at 00:01
    """
    try:
        logger.info("Checking expired memberships...")
        
        count = move_expired_to_inactive()
        
        if count > 0:
            message = f"⚠️ *Auto-Expiry Alert*\n\n"
            message += f"Moved {count} members to inactive status.\n"
            message += f"These memberships expired 7+ days ago.\n\n"
            message += f"_Use /reports to view inactive members list._"
            
            # Send notification to admin
            if SUPER_ADMIN_USER_ID:
                await context.bot.send_message(
                    chat_id=int(SUPER_ADMIN_USER_ID),
                    text=message,
                    parse_mode="Markdown"
                )
                logger.info(f"Expiry alert sent to admin: {count} members moved")
        else:
            logger.info("No memberships to expire")
    
    except Exception as e:
        logger.error(f"Error checking expired memberships: {e}")


async def send_water_reminder_hourly(context: ContextTypes.DEFAULT_TYPE):
    """
    Send water reminder to users based on their interval preference
    Respects user's enabled/disabled and interval settings
    Skips sending between 8 PM (20:00) and 6 AM (06:00) for better sleep
    """
    try:
        from datetime import datetime, timedelta
        from src.database.reminder_operations import get_reminder_preferences
        
        # Get current hour
        current_hour = datetime.now().hour
        
        # Skip reminders during night hours (20:00 to 06:00)
        if current_hour >= 20 or current_hour < 6:
            logger.info(f"Skipping water reminders during night hours ({current_hour}:00)")
            return
        
        logger.info("Sending water reminders based on user preferences...")
        
        # Get all users with paid memberships
        paid_users = get_all_paid_users()
        
        if not paid_users:
            logger.info("No paid users found for water reminder")
            return
        
        reminder_text = (
            "💧 *Hydration Reminder*\n\n"
            "Time to log your water intake! 💦\n\n"
            "Staying hydrated helps you stay fit and healthy.\n"
            "Use /water to log your water consumption."
        )
        
        # Create inline buttons for quick actions
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        keyboard = [
            [
                InlineKeyboardButton("💧 Log Water", callback_data="cmd_water"),
                InlineKeyboardButton("⚙️ Reminder Settings", callback_data="cmd_reminders"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        sent_count = 0
        for user in paid_users:
            try:
                # Get user's reminder preferences
                prefs = get_reminder_preferences(user['user_id'])
                
                # Skip if water reminders are disabled
                if not prefs or not prefs.get('water_reminder_enabled', True):
                    logger.debug(f"Water reminders disabled for user {user['user_id']}")
                    continue
                
                # Get user's interval preference (default 60 minutes)
                interval_minutes = prefs.get('water_reminder_interval_minutes', 60)
                
                # Get last reminder time from context (stored per user)
                last_reminder_key = f"last_water_reminder_{user['user_id']}"
                last_reminder = context.user_data.get(last_reminder_key) if hasattr(context, 'user_data') else None
                
                # If we don't have last reminder info, use a persistent storage approach
                # Store in database or use a simple time check
                current_time = datetime.now()
                
                # For now, use a simple approach: check if we should send based on current hour matching interval
                # This ensures approximately the right interval
                minutes_since_hour = current_time.minute
                
                # Only send at the start of each interval period
                # For example: if interval is 120 (2 hours), send at 0:00, 2:00, 4:00, etc.
                should_send = (current_hour * 60 + minutes_since_hour) % interval_minutes < 5
                
                if should_send:
                    await context.bot.send_message(
                        chat_id=user['user_id'],
                        text=reminder_text,
                        parse_mode="Markdown",
                        reply_markup=reply_markup
                    )
                    sent_count += 1
                    logger.debug(f"Water reminder sent to user {user['user_id']} (interval: {interval_minutes}min)")
                else:
                    logger.debug(f"Skipping user {user['user_id']} - not time for next reminder (interval: {interval_minutes}min)")
            except Exception as e:
                logger.debug(f"Could not send water reminder to user {user['user_id']}: {e}")
        
        logger.info(f"Water reminders sent to {sent_count} users")
    
    except Exception as e:
        logger.error(f"Error sending water reminders: {e}")


async def send_weight_reminder_morning(context: ContextTypes.DEFAULT_TYPE):
    """
    Send morning reminder at 9 AM to log weight
    """
    try:
        logger.info("Sending morning weight reminders...")
        
        # Get all users with paid memberships
        paid_users = get_all_paid_users()
        
        if not paid_users:
            logger.info("No paid users found for weight reminder")
            return
        
        reminder_text = (
            "⚖️ *Good Morning!* ☀️\n\n"
            "Time to log your weight today! 📊\n\n"
            "Tracking your weight daily helps you monitor your fitness progress.\n"
            "Use /weight to log your weight."
        )
        
        sent_count = 0
        for user in paid_users:
            try:
                await context.bot.send_message(
                    chat_id=user['user_id'],
                    text=reminder_text,
                    parse_mode="Markdown"
                )
                sent_count += 1
            except Exception as e:
                logger.debug(f"Could not send weight reminder to user {user['user_id']}: {e}")
        
        logger.info(f"Weight reminders sent to {sent_count} users")
    
    except Exception as e:
        logger.error(f"Error sending weight reminders: {e}")


async def send_habits_reminder_evening(context: ContextTypes.DEFAULT_TYPE):
    """
    Send evening reminder at 8 PM to log daily habits
    """
    try:
        logger.info("Sending evening habits reminders...")
        
        # Get all users with paid memberships
        paid_users = get_all_paid_users()
        
        if not paid_users:
            logger.info("No paid users found for habits reminder")
            return
        
        reminder_text = (
            "✅ *Evening Check*\n\n"
            "Time to log your daily habits! 📝\n\n"
            "Completing your daily habits keeps you on track with your fitness goals.\n"
            "Use /habits to log your habits for today."
        )
        
        sent_count = 0
        for user in paid_users:
            try:
                await context.bot.send_message(
                    chat_id=user['user_id'],
                    text=reminder_text,
                    parse_mode="Markdown"
                )
                sent_count += 1
            except Exception as e:
                logger.debug(f"Could not send habits reminder to user {user['user_id']}: {e}")
        
        logger.info(f"Habits reminders sent to {sent_count} users")
    
    except Exception as e:
        logger.error(f"Error sending habits reminders: {e}")
