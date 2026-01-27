"""Admin flow to edit the welcome message stored in DB."""

import logging
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, MessageHandler, filters
from src.utils.auth import is_admin_id
from src.utils.welcome_message import get_welcome_message, update_welcome_message

logger = logging.getLogger(__name__)

WAITING_FOR_WELCOME_TEXT = range(1)


async def start_edit_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_admin_id(uid):
        logger.warning(f"[SECURITY] Non-admin {uid} attempted to edit welcome message")
        await (update.callback_query or update.message).answer()
        await (update.callback_query.message if update.callback_query else update.message).reply_text(
            "❌ Admin access only."
        )
        return ConversationHandler.END

    if update.callback_query:
        await update.callback_query.answer()

    current = get_welcome_message()
    await (update.callback_query.message if update.callback_query else update.message).reply_text(
        "📝 *Edit Welcome Message*\n\n"
        "Current message:\n\n"
        f"{current}\n\n"
        "Please send the new welcome message text.",
        parse_mode='Markdown'
    )
    return WAITING_FOR_WELCOME_TEXT


async def save_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_admin_id(uid):
        logger.warning(f"[SECURITY] Non-admin {uid} attempted to save welcome message")
        await update.message.reply_text("❌ Admin access only.")
        return ConversationHandler.END

    new_text = (update.message.text or '').strip()
    if not new_text:
        await update.message.reply_text("❌ Please send a non-empty welcome message.")
        return WAITING_FOR_WELCOME_TEXT

    update_welcome_message(new_text)
    await update.message.reply_text("✅ Welcome message updated successfully.")
    return ConversationHandler.END


def get_welcome_message_admin_handler():
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(start_edit_welcome, pattern="^cmd_edit_welcome_message$")],
        states={
            WAITING_FOR_WELCOME_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_welcome)],
        },
        fallbacks=[],
        per_message=False,
    )