"""Utility functions for callback query handling"""
import logging
from telegram import Update

logger = logging.getLogger(__name__)


async def safe_answer_callback_query(update: Update, text: str = None, show_alert: bool = False) -> bool:
    """
    Safely answer a callback query, handling expired/stale queries gracefully.
    
    Args:
        update: The Update object containing the callback query
        text: Optional notification text
        show_alert: Whether to show as alert popup
        
    Returns:
        True if answer was successful, False if query was expired/invalid
    """
    if not update.callback_query:
        return False
        
    try:
        await update.callback_query.answer(text=text, show_alert=show_alert)
        return True
    except Exception as e:
        # Query is too old, expired, or already answered
        logger.debug(f"Could not answer callback query (likely expired): {e}")
        return False
