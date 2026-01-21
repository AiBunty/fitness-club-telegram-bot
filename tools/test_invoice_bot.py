import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import logging
import os

from src.config import TELEGRAM_BOT_TOKEN

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_invoice_bot")

async def send_test_invoice_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔍 Search User", callback_data="cmd_invoices")]])
    await update.message.reply_text("Test invoice menu", reply_markup=kb)

async def test_cmd_invoices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("🔎 Type name, username, or part of name:")
    logger.info("[TEST] Prompted for search term")

async def test_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    logger.info(f"[TEST] Received message: {text}")
    try:
        from src.database.user_operations import search_users
        results = search_users(text, limit=10, offset=0)
        logger.info(f"[TEST] search_users returned {len(results) if results is not None else 0} results")
        await update.message.reply_text(f"Search results: {len(results) if results is not None else 0}")
    except Exception as e:
        logger.exception(f"[TEST] Error calling search_users: {e}")
        await update.message.reply_text(f"Error calling search_users: {e}")

if __name__ == '__main__':
    token = TELEGRAM_BOT_TOKEN or os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        print("TELEGRAM_BOT_TOKEN not set")
        raise SystemExit(1)
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler('test_invoice', send_test_invoice_menu))
    app.add_handler(CallbackQueryHandler(test_cmd_invoices, pattern="^cmd_invoices$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, test_message_handler))
    print("Starting test invoice bot (use /test_invoice)")
    app.run_polling()
