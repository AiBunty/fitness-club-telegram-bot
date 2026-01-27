"""
ACCESS GATE - Mandatory Registration & Subscription Validation

CRITICAL: Every incoming message/callback must pass this gate.

User States:
1. NEW_USER - Not registered - ❌ DENIED
2. REGISTERED_NO_SUBSCRIPTION - Registered but no active plan - ❌ DENIED
3. ACTIVE_SUBSCRIBER - Registered + active subscription - ✅ ALLOWED
4. EXPIRED_SUBSCRIBER - Registered but subscription expired - ❌ DENIED

Entry Rules:
- EVERY message/callback checks registration first
- If not registered → redirect to registration ONLY
- If registered but no subscription → show ONLY subscription plans
- If subscription expired → show renewal options ONLY
- Only ACTIVE_SUBSCRIBER can access any app features
"""

import logging
from typing import Dict, Optional, Tuple
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from src.database.user_operations import user_exists as db_user_exists, get_user
from src.database.subscription_operations import (
    get_user_subscription, is_subscription_active
)
from src.utils.auth import is_admin_id
from src.config import USE_LOCAL_DB

logger = logging.getLogger(__name__)

# User state constants
STATE_NEW_USER = "NEW_USER"
STATE_REGISTERED_NO_SUBSCRIPTION = "REGISTERED_NO_SUBSCRIPTION"
STATE_ACTIVE_SUBSCRIBER = "ACTIVE_SUBSCRIBER"
STATE_EXPIRED_SUBSCRIBER = "EXPIRED_SUBSCRIBER"


def get_user_access_state(user_id: int) -> Tuple[str, Optional[Dict]]:
    """
    Determine user's access state.
    
    Returns: (state, user_dict)
    - (NEW_USER, None)
    - (REGISTERED_NO_SUBSCRIPTION, user_dict)
    - (ACTIVE_SUBSCRIBER, user_dict)
    - (EXPIRED_SUBSCRIBER, user_dict)
    """
    try:
        # Check if user exists in DB
        if not db_user_exists(user_id):
            logger.info(f"[ACCESS] user_state NEW_USER telegram_id={user_id}")
            return STATE_NEW_USER, None
        
        user = get_user(user_id)
        
        # Admin and Staff bypass - always active
        if is_admin_id(user_id) or is_staff(user_id):
            role = "ADMIN" if is_admin_id(user_id) else "STAFF"
            logger.info(f"[ACCESS] user_state {role} telegram_id={user_id} (subscription exempt)")
            return STATE_ACTIVE_SUBSCRIBER, user
        
        # In local DB mode, skip subscription checks
        if USE_LOCAL_DB:
            logger.info(f"[ACCESS] user_state LOCAL_DB_MODE telegram_id={user_id} (skipping subscription)")
            return STATE_ACTIVE_SUBSCRIBER, user
        
        # Check subscription
        sub = get_user_subscription(user_id)
        
        if not sub:
            logger.info(f"[ACCESS] user_state REGISTERED_NO_SUBSCRIPTION telegram_id={user_id}")
            return STATE_REGISTERED_NO_SUBSCRIPTION, user
        
        if is_subscription_active(user_id):
            logger.info(f"[ACCESS] user_state ACTIVE_SUBSCRIBER telegram_id={user_id}")
            return STATE_ACTIVE_SUBSCRIBER, user
        else:
            logger.info(f"[ACCESS] user_state EXPIRED_SUBSCRIBER telegram_id={user_id}")
            return STATE_EXPIRED_SUBSCRIBER, user
    
    except Exception as e:
        logger.error(f"[ACCESS] error_getting_state telegram_id={user_id}: {e}")
        # Default: deny access
        return STATE_NEW_USER, None


async def check_access_gate(
    update: Update, 
    context: ContextTypes.DEFAULT_TYPE,
    require_subscription: bool = True
) -> bool:
    """
    Master access gate for all features.
    
    Args:
        update: Telegram update
        context: Telegram context
        require_subscription: If True, require ACTIVE_SUBSCRIBER. If False, allow registered users.
    
    Returns:
        True if user has access, False otherwise
    
    Side effects:
        Sends appropriate message to user if access denied
    """
    user_id = update.effective_user.id
    state, user = get_user_access_state(user_id)
    
    # Get message/query for response
    msg_obj = update.effective_message
    query = update.callback_query
    
    # NEW USER - Redirect to registration
    if state == STATE_NEW_USER:
        logger.warning(f"[ACCESS] blocked NEW_USER telegram_id={user_id}")
        
        if query:
            await query.answer("❌ You must register first.", show_alert=True)
        else:
            await msg_obj.reply_text(
                "❌ You are not registered.\n\n"
                "Please complete registration to access the app.\n"
                "Use /register to begin."
            )
        return False
    
    # REGISTERED NO SUBSCRIPTION - Show subscription option only
    if state == STATE_REGISTERED_NO_SUBSCRIPTION:
        logger.warning(f"[ACCESS] blocked REGISTERED_NO_SUBSCRIPTION telegram_id={user_id}")
        
        if query:
            await query.answer(
                "🔒 No active subscription found. Please subscribe to continue.",
                show_alert=True
            )
        else:
            from telegram import InlineKeyboardMarkup, InlineKeyboardButton
            kb = InlineKeyboardMarkup([[
                InlineKeyboardButton("💪 Subscribe Now", callback_data="start_subscribe")
            ]])
            await msg_obj.reply_text(
                f"Hello {user.get('full_name', 'User')}! 👋\n\n"
                "🔒 To access the fitness club app, you need an active subscription.\n\n"
                "Available plans:\n"
                "• 30 Days - ₹500\n"
                "• 90 Days - ₹1,200\n"
                "• Annual - ₹4,000\n\n"
                "Choose a plan to get started 👇",
                reply_markup=kb
            )
        return False
    
    # EXPIRED SUBSCRIPTION - Show renewal option
    if state == STATE_EXPIRED_SUBSCRIBER:
        logger.warning(f"[ACCESS] blocked EXPIRED_SUBSCRIBER telegram_id={user_id}")
        
        if query:
            await query.answer("⏰ Your subscription has expired. Please renew to continue.", show_alert=True)
        else:
            from telegram import InlineKeyboardMarkup, InlineKeyboardButton
            kb = InlineKeyboardMarkup([[
                InlineKeyboardButton("🔄 Renew Subscription", callback_data="start_subscribe")
            ]])
            await msg_obj.reply_text(
                f"Welcome back {user.get('full_name', 'User')}! 👋\n\n"
                "⏰ Your subscription has expired.\n\n"
                "Please renew your subscription to continue accessing:\n"
                "• Activity tracking\n"
                "• Weight & water logs\n"
                "• Challenge participation\n"
                "• Shake orders\n"
                "• And more!\n\n"
                "Tap below to renew 👇",
                reply_markup=kb
            )
        return False
    
    # ACTIVE SUBSCRIBER - Allow access
    if state == STATE_ACTIVE_SUBSCRIBER:
        logger.info(f"[ACCESS] granted telegram_id={user_id} subscription_active=true")
        return True
    
    # Unknown state - deny
    logger.error(f"[ACCESS] unknown_state telegram_id={user_id} state={state}")
    if query:
        await query.answer("❌ Access denied. Please try again.", show_alert=True)
    else:
        await msg_obj.reply_text("❌ Access denied. Please register and subscribe.")
    return False


async def enforce_registration_only(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> bool:
    """
    Enforce registration gate (allow registered but unsubscribed users).
    Used for registration and subscription flows themselves.
    
    Returns: True if user is registered (or is admin), False otherwise
    """
    user_id = update.effective_user.id
    state, user = get_user_access_state(user_id)
    
    msg_obj = update.effective_message
    query = update.callback_query
    
    # Allow admins
    if is_admin_id(user_id):
        return True
    
    # NEW USER - Redirect to registration
    if state == STATE_NEW_USER:
        logger.warning(f"[ACCESS] blocked_unregistered_user telegram_id={user_id}")
        
        if query:
            await query.answer("❌ You must register first.", show_alert=True)
        else:
            await msg_obj.reply_text(
                "❌ You are not registered.\n\n"
                "Please complete registration to access the app.\n"
                "Use /register to begin."
            )
        return False
    
    # All other states (registered or better) are allowed
    logger.info(f"[ACCESS] granted_registered_user telegram_id={user_id} state={state}")
    return True


async def check_profile_access(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Check access for profile command.
    - Unregistered: redirect to registration
    - Registered (any): show profile
    """
    return await enforce_registration_only(update, context)


async def check_app_feature_access(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Check access for app features (menu, checkin, weight log, etc).
    - Unregistered: redirect to registration
    - Registered no subscription: show subscription gate
    - Subscribed: allow access
    """
    return await check_access_gate(update, context, require_subscription=True)


# ============================================================================
# LOGGING HELPERS
# ============================================================================

def log_access_attempt(user_id: int, action: str, result: bool) -> None:
    """Log access attempt"""
    status = "✅ GRANTED" if result else "❌ BLOCKED"
    state, _ = get_user_access_state(user_id)
    logger.info(f"[ACCESS] {status} action={action} user_id={user_id} state={state}")


# ============================================================================
# USAGE EXAMPLE
# ============================================================================
"""
In any handler that requires authentication:

async def my_feature_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # GATE: Check access
    if not await check_app_feature_access(update, context):
        return ConversationHandler.END  # User got error message
    
    # User has access - proceed with feature
    await update.effective_message.reply_text("Feature available!")

For profile/registration flows:

async def profile_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Allow unregistered users to register
    if not await enforce_registration_only(update, context):
        return ConversationHandler.END  # User got registration prompt
    
    # Show profile
    await show_user_profile(update, context)
"""
