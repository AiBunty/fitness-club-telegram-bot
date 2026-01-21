import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger("src.handlers.debug_handlers")

async def raw_update_logger(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
