"""Shared helpers for clearing stale conversation state across admin flows."""
import logging
from telegram.ext import ConversationHandler, ContextTypes
from telegram import Update

logger = logging.getLogger(__name__)


def clear_stale_states(update: Update, context: ContextTypes.DEFAULT_TYPE, *, flow_name: str = "admin_flow"):
    """Clear user_data to stop cross-talk between admin flows.

    Returns ConversationHandler.END so callers can short-circuit other handlers
    that might still be listening on old state.
    """
    if context.user_data:
        logger.info("[STATE] Clearing stale states for %s keys=%s", flow_name, list(context.user_data.keys()))
        context.user_data.clear()
    return ConversationHandler.END
