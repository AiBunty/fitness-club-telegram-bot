"""
Debug Handlers Module
Handles debug and logging utilities
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger("src.features.debug.handler")


async def raw_update_logger(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Logs raw updates in a concise format.
    
    Used for debugging purposes to log all incoming updates.
    This function can be added to the application to monitor all updates.
    
    Args:
        update: The incoming Telegram update
        context: The callback context
    """
    try:
        # Log a concise summary to avoid flooding
        if update.message:
            sender = update.effective_user.id if update.effective_user else 'unknown'
            text = getattr(update.message, 'text', '')
            logger.info(f"[RAW] message from={sender} text={text}")
        elif update.callback_query:
            sender = update.callback_query.from_user.id
            data = update.callback_query.data
            logger.info(f"[RAW] callback from={sender} data={data}")
        else:
            logger.info(f"[RAW] update type={type(update)}")
    except Exception:
        logger.exception("[RAW] Failed to log update")
