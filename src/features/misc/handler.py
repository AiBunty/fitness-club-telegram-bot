"""
Miscellaneous Handlers Module
Handles utility commands like whoami and telegram ID display
"""

from telegram import Update
from telegram.ext import ContextTypes
from src.utils.auth import whoami_text


async def cmd_whoami(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Display user information, registration status, and subscription details.
    
    Shows:
    - Telegram ID
    - Full name
    - Role (admin/staff/user)
    - Subscription status (ACTIVE/GRACE/EXPIRED/Not Required)
    - Subscription expiry date
    
    No access gates - shows registration status explicitly.
    Admins and staff are exempt from subscription requirements.
    
    Args:
        update: The incoming update
        context: The callback context
    """
    uid = update.effective_user.id

    # No gates; show registration status explicitly
    from src.database.user_operations import get_user
    from src.database.subscription_operations import (
        get_user_subscription, 
        is_subscription_active, 
        is_in_grace_period
    )
    from src.utils.auth import is_admin_id, is_staff

    user = get_user(uid)

    if not user:
        text = (
            "❌ You are not registered.\n"
            f"🆔 Telegram ID: {uid}\n"
            "👉 Please register to continue."
        )
    else:
        role = user.get('role') or ('admin' if is_admin_id(uid) else 'staff' if is_staff(uid) else 'user')
        
        # Admins and Staff are exempt from subscription requirements
        if is_admin_id(uid) or is_staff(uid):
            sub_status = "Not Required"
            expiry_text = "Not Required"
        else:
            sub_status = "UNKNOWN"
            expiry_text = "N/A"
            try:
                sub = get_user_subscription(uid)
                if sub and is_subscription_active(uid):
                    sub_status = "ACTIVE"
                elif sub and is_in_grace_period(uid):
                    sub_status = "GRACE"
                else:
                    sub_status = "EXPIRED"
                if sub and sub.get('end_date'):
                    expiry_text = str(sub.get('end_date'))
            except Exception:
                pass

        text = (
            f"👤 Name: {user.get('full_name','User')}\n"
            f"🆔 Telegram ID: {uid}\n"
            f"👔 Role: {role}\n"
            f"📦 Subscription: {sub_status}\n"
            f"📅 Expiry: {expiry_text}"
        )

    if update.callback_query:
        await update.callback_query.answer()
        message = update.callback_query.message
    else:
        message = update.message

    await message.reply_text(text, parse_mode='Markdown')


async def cmd_get_telegram_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Display user's Telegram ID in a copyable format.
    
    Creates a clean message with the user ID in monospace format
    that can be tapped to copy. Useful for registration and verification.
    
    Args:
        update: The incoming update
        context: The callback context
    """
    uid = update.effective_user.id
    
    # Handle both command and callback contexts
    if update.callback_query:
        await update.callback_query.answer()
        message = update.callback_query.message
    else:
        message = update.message
    
    # Create a clean, copyable message with the ID
    id_message = (
        f"🔢 *Your Telegram ID*\n\n"
        f"`{uid}`\n\n"
        f"_Tap the number above to copy it._\n"
        f"You can use this ID to register or verify your account."
    )
    
    await message.reply_text(id_message, parse_mode='Markdown')
