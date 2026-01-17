"""
Registration & Approval Guard Functions
========================================

Prevents unregistered or unapproved users from accessing features.
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from src.database.user_operations import user_exists, get_user_approval_status
from src.utils.auth import is_admin_id

logger = logging.getLogger(__name__)


async def check_registration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Check if user is registered. If not, send message and return False.
    Returns True if registered, False if not.
    """
    user_id = update.effective_user.id
    
    if not user_exists(user_id):
        if update.callback_query:
            await update.callback_query.answer(
                "❌ You must register first. Use /register",
                show_alert=True
            )
        else:
            await update.message.reply_text(
                "❌ You must register first to access this feature.\n"
                "Use /register to begin."
            )
        return False
    
    return True


async def check_approval(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Check if user is approved. If not registered or not approved, send message and return False.
    Returns True if approved, False otherwise.
    """
    user_id = update.effective_user.id
    
    # Check if registered first
    if not user_exists(user_id):
        if update.callback_query:
            await update.callback_query.answer(
                "❌ You must register first. Use /register",
                show_alert=True
            )
        else:
            await update.message.reply_text(
                "❌ You must register first to access this feature.\n"
                "Use /register to begin."
            )
        return False
    
    # Check approval status
    approval_status = get_user_approval_status(user_id)
    
    if approval_status == 'rejected':
        if update.callback_query:
            await update.callback_query.answer(
                "❌ Your registration was rejected. Contact admin.",
                show_alert=True
            )
        else:
            await update.message.reply_text(
                "❌ Your registration was rejected.\n"
                "Contact admin for more information."
            )
        return False
    
    if approval_status == 'pending':
        if update.callback_query:
            await update.callback_query.answer(
                "⏳ Your registration is pending admin approval.",
                show_alert=True
            )
        else:
            await update.message.reply_text(
                "⏳ Your registration is pending admin approval.\n"
                "Please wait for the admin to review your application."
            )
        return False
    
    # Approved
    if approval_status != 'approved':
        if update.callback_query:
            await update.callback_query.answer(
                "❌ Access denied. Invalid status.",
                show_alert=True
            )
        else:
            await update.message.reply_text(
                "❌ Access denied. Invalid status."
            )
        return False
    
    return True


async def check_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Check if user is admin. If not, send message and return False.
    Returns True if admin, False otherwise.
    """
    user_id = update.effective_user.id
    
    # Admins don't need to be registered
    if is_admin_id(user_id):
        return True
    
    if update.callback_query:
        await update.callback_query.answer(
            "❌ Admin access only",
            show_alert=True
        )
    else:
        await update.message.reply_text(
            "❌ This command is for admins only."
        )
    
    return False
