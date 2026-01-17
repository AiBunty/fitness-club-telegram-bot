from telegram import Update
from telegram.ext import ContextTypes
from src.utils.auth import whoami_text

async def cmd_whoami(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    
    # Handle both command and callback contexts
    if update.callback_query:
        await update.callback_query.answer()
        message = update.callback_query.message
    else:
        message = update.message
    
    await message.reply_text(whoami_text(uid), parse_mode='Markdown')

async def cmd_get_telegram_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display user's Telegram ID in a copyable format"""
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
