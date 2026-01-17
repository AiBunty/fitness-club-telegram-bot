"""
Subscription Scheduled Jobs
- Expiry reminders (2 days before)
- Grace period daily reminders
- Follow-up messages (every 3 days after grace)
- Auto-lock expired subscriptions
"""

import logging
from datetime import datetime, timedelta
from telegram import Bot
from src.database.subscription_operations import (
    get_expiring_subscriptions, get_users_in_grace_period,
    get_expired_subscriptions, mark_subscription_locked
)

logger = logging.getLogger(__name__)


async def send_expiry_reminders(bot: Bot):
    """Send reminders 2 days before subscription expiry"""
    try:
        expiring = get_expiring_subscriptions(days_ahead=2)
        
        if not expiring:
            logger.info("No subscriptions expiring in 2 days")
            return
        
        for sub in expiring:
            try:
                await bot.send_message(
                    chat_id=sub['user_id'],
                    text="⚠️ *Subscription Expiring Soon*\n\n"
                         f"Your gym subscription will expire in 2 days.\n\n"
                         f"📅 End Date: {sub['end_date'].strftime('%d-%m-%Y')}\n\n"
                         "🔄 Renew now to avoid interruption!\n"
                         "Use /subscribe to renew your membership.",
                    parse_mode="Markdown"
                )
                logger.info(f"Expiry reminder sent to user {sub['user_id']}")
            except Exception as e:
                logger.error(f"Failed to send expiry reminder to {sub['user_id']}: {e}")
        
        logger.info(f"Sent expiry reminders to {len(expiring)} users")
        
    except Exception as e:
        logger.error(f"Error in send_expiry_reminders: {e}")


async def send_grace_period_reminders(bot: Bot):
    """Send daily reminders during grace period"""
    try:
        grace_users = get_users_in_grace_period()
        
        if not grace_users:
            logger.info("No users in grace period")
            return
        
        for user in grace_users:
            try:
                days_left = (user['grace_period_end'] - datetime.now()).days
                
                await bot.send_message(
                    chat_id=user['user_id'],
                    text="🔔 *Grace Period Active*\n\n"
                         f"Your subscription has expired, but you have {days_left} days "
                         f"of grace period remaining.\n\n"
                         "⚠️ *Important:* After the grace period, your account will be locked "
                         "and you won't be able to access the app.\n\n"
                         "💪 Renew now to continue your fitness journey!\n"
                         "Use /subscribe to renew.",
                    parse_mode="Markdown"
                )
                logger.info(f"Grace period reminder sent to user {user['user_id']}")
            except Exception as e:
                logger.error(f"Failed to send grace reminder to {user['user_id']}: {e}")
        
        logger.info(f"Sent grace period reminders to {len(grace_users)} users")
        
    except Exception as e:
        logger.error(f"Error in send_grace_period_reminders: {e}")


async def send_followup_reminders(bot: Bot):
    """Send follow-up messages every 3 days after grace period"""
    try:
        expired = get_expired_subscriptions()
        
        if not expired:
            logger.info("No expired subscriptions to follow up")
            return
        
        motivational_messages = [
            "💪 *We Miss You!*\n\nYour fitness journey is waiting! Come back stronger.\n\n"
            "Your body deserves the best care. Renew your subscription today!",
            
            "🏋️ *Ready to Get Back?*\n\nEvery day is a chance to restart your fitness goals.\n\n"
            "Your gym family is waiting for you. Let's do this!",
            
            "🔥 *Don't Give Up!*\n\nYour progress matters. Consistency is key to success.\n\n"
            "Renew now and get back on track with your goals!",
            
            "⭐ *You've Got This!*\n\nRemember why you started. Your goals are still achievable.\n\n"
            "Join back and let's crush those fitness milestones together!"
        ]
        
        for i, user in enumerate(expired):
            try:
                message = motivational_messages[i % len(motivational_messages)]
                
                await bot.send_message(
                    chat_id=user['user_id'],
                    text=f"{message}\n\n"
                         "Use /subscribe to rejoin the fitness club.",
                    parse_mode="Markdown"
                )
                logger.info(f"Follow-up reminder sent to user {user['user_id']}")
            except Exception as e:
                logger.error(f"Failed to send follow-up to {user['user_id']}: {e}")
        
        logger.info(f"Sent follow-up reminders to {len(expired)} users")
        
    except Exception as e:
        logger.error(f"Error in send_followup_reminders: {e}")


async def lock_expired_subscriptions(bot: Bot):
    """Lock subscriptions that are past grace period"""
    try:
        expired = get_expired_subscriptions()
        
        if not expired:
            logger.info("No subscriptions to lock")
            return
        
        locked_count = 0
        for user in expired:
            try:
                if mark_subscription_locked(user['user_id']):
                    locked_count += 1
                    
                    # Notify user
                    await bot.send_message(
                        chat_id=user['user_id'],
                        text="🔒 *Account Locked*\n\n"
                             "Your subscription has expired and the grace period has ended.\n\n"
                             "Your account is now locked. To regain access, please renew your subscription.\n\n"
                             "Use /subscribe to renew and unlock your account.",
                        parse_mode="Markdown"
                    )
                    logger.info(f"Locked subscription for user {user['user_id']}")
            except Exception as e:
                logger.error(f"Failed to lock subscription for {user['user_id']}: {e}")
        
        logger.info(f"Locked {locked_count} expired subscriptions")
        
    except Exception as e:
        logger.error(f"Error in lock_expired_subscriptions: {e}")
