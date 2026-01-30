"""
Admin Settings Handlers
- Configure UPI ID and QR code
- Manage subscription settings
"""

import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from src.database.connection import execute_query

logger = logging.getLogger(__name__)


def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    try:
        result = execute_query(
            "SELECT role FROM users WHERE user_id = %s",
            (user_id,),
            fetch_one=True
        )
        if result:
            return result[0] == 'admin'
    except:
        pass
    return False

# States
ADMIN_SETTINGS_MENU, ENTER_UPI_ID, ENTER_GYM_NAME, UPLOAD_QR_CODE = range(4)


async def cmd_admin_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: Settings menu"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin access only.")
        return ConversationHandler.END
    
    keyboard = [
        [InlineKeyboardButton("📱 Configure UPI ID", callback_data="settings_upi_id")],
        [InlineKeyboardButton("🏢 Gym Name", callback_data="settings_gym_name")],
        [InlineKeyboardButton("🖼️ Upload QR Code", callback_data="settings_upload_qr")],
        [InlineKeyboardButton("❌ Close", callback_data="settings_close")],
        [InlineKeyboardButton("⬅️ Back to Admin Menu", callback_data="cmd_admin_back")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "⚙️ *Admin Settings*\n\n"
        "Configure gym details and payment options:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    
    return ADMIN_SETTINGS_MENU


async def callback_settings_upi_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Edit UPI ID"""
    query = update.callback_query
    await query.answer()
    
    # Get current UPI ID
    result = execute_query(
        "SELECT upi_id FROM gym_settings WHERE id = 1",
        fetch_one=True
    )
    current_upi = result[0] if result else "Not set"
    
    await query.message.reply_text(
        f"📱 *Current UPI ID:* `{current_upi}`\n\n"
        f"Send new UPI ID (e.g., yourname@upi):",
        parse_mode="Markdown"
    )
    
    return ENTER_UPI_ID


async def handle_upi_id_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle UPI ID input"""
    upi_id = update.message.text.strip()
    
    if "@" not in upi_id or len(upi_id) < 5:
        await update.message.reply_text(
            "❌ Invalid UPI ID format. Please use format: name@bankname (e.g., gym@upi)"
        )
        return ENTER_UPI_ID
    
    # Update database
    try:
        execute_query(
            "UPDATE gym_settings SET upi_id = %s, updated_at = NOW() WHERE id = 1",
            (upi_id,)
        )
        
        await update.message.reply_text(
            f"✅ UPI ID updated to: `{upi_id}`\n\n"
            f"This will be used for all QR code generation.",
            parse_mode="Markdown"
        )
        logger.info(f"UPI ID updated: {upi_id}")
        
    except Exception as e:
        logger.error(f"Error updating UPI ID: {e}")
        await update.message.reply_text("❌ Error updating UPI ID. Please try again.")
        return ENTER_UPI_ID
    
    return ConversationHandler.END


async def callback_settings_gym_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Edit Gym Name"""
    query = update.callback_query
    await query.answer()
    
    # Get current gym name
    result = execute_query(
        "SELECT gym_name FROM gym_settings WHERE id = 1",
        fetch_one=True
    )
    current_name = result[0] if result else "Fitness Club Gym"
    
    await query.message.reply_text(
        f"🏢 *Current Gym Name:* `{current_name}`\n\n"
        f"Send new gym name:",
        parse_mode="Markdown"
    )
    
    return ENTER_GYM_NAME


async def handle_gym_name_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle gym name input"""
    gym_name = update.message.text.strip()
    
    if len(gym_name) < 3 or len(gym_name) > 100:
        await update.message.reply_text(
            "❌ Gym name should be between 3 and 100 characters."
        )
        return ENTER_GYM_NAME
    
    # Update database
    try:
        execute_query(
            "UPDATE gym_settings SET gym_name = %s, updated_at = NOW() WHERE id = 1",
            (gym_name,)
        )
        
        await update.message.reply_text(
            f"✅ Gym name updated to: `{gym_name}`",
            parse_mode="Markdown"
        )
        logger.info(f"Gym name updated: {gym_name}")
        
    except Exception as e:
        logger.error(f"Error updating gym name: {e}")
        await update.message.reply_text("❌ Error updating gym name. Please try again.")
        return ENTER_GYM_NAME
    
    return ConversationHandler.END


async def callback_settings_upload_qr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Upload custom QR code"""
    query = update.callback_query
    await query.answer()
    
    await query.message.reply_text(
        "🖼️ *Upload Custom QR Code*\n\n"
        "Send an image file of your custom QR code.\n"
        "This will be used instead of auto-generated QR codes.",
        parse_mode="Markdown"
    )
    
    return UPLOAD_QR_CODE


async def handle_qr_code_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle QR code image upload"""
    user_id = update.effective_user.id
    
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        
        # Save file_id to database
        try:
            execute_query(
                "UPDATE gym_settings SET qr_code_url = %s, updated_at = NOW() WHERE id = 1",
                (file_id,)
            )
            
            await update.message.reply_text(
                "✅ QR Code uploaded successfully!\n\n"
                "This QR code will now be used for all UPI payments.",
                parse_mode="Markdown"
            )
            logger.info(f"QR code uploaded by admin {user_id}")
            
        except Exception as e:
            logger.error(f"Error saving QR code: {e}")
            await update.message.reply_text("❌ Error saving QR code. Please try again.")
            return UPLOAD_QR_CODE
    else:
        await update.message.reply_text(
            "❌ Please send a photo/image file.\n"
            "Use the attachment button to send an image."
        )
        return UPLOAD_QR_CODE
    
    return ConversationHandler.END


async def callback_settings_close(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Close settings menu"""
    query = update.callback_query
    await query.answer()

    keyboard = [[InlineKeyboardButton("⬅️ Back to Admin Menu", callback_data="cmd_admin_back")]]
    await query.edit_message_text("✅ Settings menu closed.", reply_markup=InlineKeyboardMarkup(keyboard))
    return ConversationHandler.END


def get_admin_settings_handler():
    """Get settings conversation handler"""
    return ConversationHandler(
        entry_points=[
            CommandHandler('settings', cmd_admin_settings),
        ],
        states={
            ADMIN_SETTINGS_MENU: [
                CallbackQueryHandler(callback_settings_upi_id, pattern="^settings_upi_id$"),
                CallbackQueryHandler(callback_settings_gym_name, pattern="^settings_gym_name$"),
                CallbackQueryHandler(callback_settings_upload_qr, pattern="^settings_upload_qr$"),
                CallbackQueryHandler(callback_settings_close, pattern="^settings_close$"),
            ],
            ENTER_UPI_ID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_upi_id_input),
            ],
            ENTER_GYM_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_gym_name_input),
            ],
            UPLOAD_QR_CODE: [
                MessageHandler(filters.PHOTO, handle_qr_code_upload),
            ],
        },
        fallbacks=[],
        per_message=False
    )
