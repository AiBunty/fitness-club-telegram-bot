"""
Admin Challenge Management Handlers
Allows admins to create, manage, and monitor challenges
"""

import logging
from datetime import datetime, date, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ChatAction

from src.database.challenges_operations import (
    create_challenge, CHALLENGE_TYPES, get_active_challenges, get_challenge_stats
)
from src.database.challenge_payment_operations import get_unpaid_challenge_participants
from src.utils.guards import check_admin
from src.utils.cutoff_enforcement import get_challenge_start_cutoff_message

logger = logging.getLogger(__name__)

# Conversation states
CREATE_NAME, CREATE_TYPE, CREATE_START, CREATE_END, CREATE_PRICING, CREATE_AMOUNT, CREATE_DESC, CREATE_CONFIRM = range(8)

async def cmd_admin_challenges(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin challenges management dashboard"""
    if not await check_admin(update, context):
        return ConversationHandler.END
    
    user = update.message.from_user
    logger.info(f"Admin {user.id} opened challenges dashboard")
    
    # Get statistics
    stats = get_challenge_stats()
    
    message = """🏆 *Challenge Management Dashboard*

📊 *Statistics:*
"""
    
    if stats:
        message += f"""• Total Challenges: {stats.get('total_challenges', 0)}
• Active: {stats.get('active_challenges', 0)}
• Completed: {stats.get('completed_challenges', 0)}
• Active Participants: {stats.get('active_participants', 0)}
• Users Completed: {stats.get('users_completed', 0)}"""
    else:
        message += "• No challenges yet"
    
    message += "\n\n*Quick Actions:*"
    
    keyboard = [
        [InlineKeyboardButton("➕ Create Challenge", callback_data="admin_create_challenge")],
        [InlineKeyboardButton("📋 View Active", callback_data="admin_view_active_challenges")],
        [InlineKeyboardButton("💳 Payment Status", callback_data="admin_payment_status")],
        [InlineKeyboardButton("📊 Challenge Stats", callback_data="admin_challenge_stats")],
        [InlineKeyboardButton("⬅️ Back to Admin Menu", callback_data="cmd_admin_back")],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(message, parse_mode="Markdown", reply_markup=reply_markup)

async def callback_create_challenge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start challenge creation flow"""
    await update.callback_query.answer()
    await update.callback_query.message.reply_text(
        "📝 *Create New Challenge*\n\n"
        "Let's create a new fitness challenge! What's the name?",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup([["/cancel"]], one_time_keyboard=True)
    )
    return CREATE_NAME

async def process_challenge_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process challenge name input"""
    text = update.message.text
    
    if text == "/cancel":
        await update.message.reply_text("❌ Challenge creation cancelled.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    
    if len(text) < 3 or len(text) > 100:
        await update.message.reply_text("❌ Challenge name must be 3-100 characters.")
        return CREATE_NAME
    
    context.user_data['challenge_name'] = text
    
    # Show challenge types
    message = "🎯 *Select Challenge Type:*\n\n"
    
    buttons = []
    for idx, (type_key, type_info) in enumerate(CHALLENGE_TYPES.items()):
        message += f"• {type_info['name']}: {type_info['goal']}\n"
        buttons.append([InlineKeyboardButton(type_info['name'], callback_data=f"chal_type_{type_key}")])
    
    reply_markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text(message, parse_mode="Markdown", reply_markup=reply_markup, reply_to_message_id=update.message.message_id)
    
    return CREATE_TYPE

async def callback_challenge_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process challenge type selection"""
    await update.callback_query.answer()
    
    type_key = update.callback_query.data.replace("chal_type_", "")
    
    if type_key not in CHALLENGE_TYPES:
        await update.callback_query.answer("Invalid type selected", show_alert=True)
        return CREATE_TYPE
    
    context.user_data['challenge_type'] = type_key
    
    # Ask for start date
    message = """📅 *Start Date*

Enter the start date (YYYY-MM-DD format):
Example: 2026-02-01

Today is: """ + datetime.now().strftime("%Y-%m-%d")
    
    await update.callback_query.message.reply_text(
        message,
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup([["/cancel"]], one_time_keyboard=True)
    )
    
    return CREATE_START

async def process_start_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process start date input"""
    text = update.message.text
    
    if text == "/cancel":
        await update.message.reply_text("❌ Challenge creation cancelled.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    
    try:
        start_date = datetime.strptime(text, "%Y-%m-%d").date()
        
        if start_date < date.today():
            await update.message.reply_text("❌ Start date must be today or in the future.")
            return CREATE_START
        
        context.user_data['start_date'] = start_date
        
        # Ask for end date
        message = f"""📅 *End Date*

Start date: {start_date}

Enter the end date (YYYY-MM-DD format):
Must be after start date."""
        
        await update.message.reply_text(
            message,
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup([["/cancel"]], one_time_keyboard=True)
        )
        
        return CREATE_END
    
    except ValueError:
        await update.message.reply_text("❌ Invalid date format. Please use YYYY-MM-DD (e.g., 2026-02-01)")
        return CREATE_START

async def process_end_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process end date input"""
    text = update.message.text
    
    if text == "/cancel":
        await update.message.reply_text("❌ Challenge creation cancelled.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    
    try:
        end_date = datetime.strptime(text, "%Y-%m-%d").date()
        start_date = context.user_data['start_date']
        
        if end_date <= start_date:
            await update.message.reply_text("❌ End date must be after start date.")
            return CREATE_END
        
        context.user_data['end_date'] = end_date
        
        # Ask for pricing
        message = "💰 *Pricing*\n\nIs this challenge FREE or PAID?"
        
        keyboard = [
            [InlineKeyboardButton("🎉 FREE", callback_data="chal_pricing_free")],
            [InlineKeyboardButton("💳 PAID", callback_data="chal_pricing_paid")],
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            message,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        
        return CREATE_PRICING
    
    except ValueError:
        await update.message.reply_text("❌ Invalid date format. Please use YYYY-MM-DD (e.g., 2026-02-28)")
        return CREATE_END

async def callback_challenge_pricing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process pricing selection"""
    await update.callback_query.answer()
    
    is_free = update.callback_query.data.endswith("free")
    context.user_data['is_free'] = is_free
    
    if is_free:
        context.user_data['price'] = 0
        
        # Ask for description
        message = "📝 *Description*\n\nEnter a brief description of the challenge (or /skip):"
        await update.callback_query.message.reply_text(
            message,
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup([["/skip"], ["/cancel"]], one_time_keyboard=True)
        )
        return CREATE_DESC
    else:
        # Ask for amount
        message = "💰 *Entry Fee*\n\nEnter the entry fee in rupees (e.g., 500):"
        await update.callback_query.message.reply_text(
            message,
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup([["/cancel"]], one_time_keyboard=True)
        )
        return CREATE_AMOUNT

async def process_entry_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process entry fee input"""
    text = update.message.text
    
    if text == "/cancel":
        await update.message.reply_text("❌ Challenge creation cancelled.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    
    try:
        price = float(text)
        
        if price <= 0 or price > 50000:
            await update.message.reply_text("❌ Entry fee must be between Rs. 1 and Rs. 50,000")
            return CREATE_AMOUNT
        
        context.user_data['price'] = price
        
        # Ask for description
        message = "📝 *Description*\n\nEnter a brief description of the challenge (or /skip):"
        await update.message.reply_text(
            message,
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup([["/skip"], ["/cancel"]], one_time_keyboard=True)
        )
        
        return CREATE_DESC
    
    except ValueError:
        await update.message.reply_text("❌ Please enter a valid number (e.g., 500)")
        return CREATE_AMOUNT

async def process_challenge_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process challenge description"""
    text = update.message.text
    
    if text == "/cancel":
        await update.message.reply_text("❌ Challenge creation cancelled.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    
    if text != "/skip":
        if len(text) < 5 or len(text) > 500:
            await update.message.reply_text("❌ Description must be 5-500 characters.")
            return CREATE_DESC
        
        context.user_data['description'] = text
    else:
        context.user_data['description'] = None
    
    # Show confirmation
    challenge_name = context.user_data['challenge_name']
    challenge_type = context.user_data['challenge_type']
    start_date = context.user_data['start_date']
    end_date = context.user_data['end_date']
    is_free = context.user_data['is_free']
    price = context.user_data['price']
    description = context.user_data.get('description', 'No description')
    
    type_info = CHALLENGE_TYPES[challenge_type]
    price_str = "FREE" if is_free else f"Rs. {price}"
    
    message = f"""✅ *Confirm Challenge Creation*

📋 *{challenge_name}*
🎯 Type: {type_info['name']}
📅 Duration: {start_date} → {end_date}
💰 Entry: {price_str}
📝 Description: {description}

⏰ Cutoff: 8:00 PM daily
📊 Points: Calculated at 10:00 PM
🏆 Leaderboard: Updated daily

Proceed?"""
    
    keyboard = [
        [InlineKeyboardButton("✅ Create", callback_data="confirm_create_challenge")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel_create_challenge")],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        message,
        parse_mode="Markdown",
        reply_markup=reply_markup,
        reply_to_message_id=update.message.message_id
    )
    
    return CREATE_CONFIRM

async def callback_confirm_create(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm and create challenge"""
    await update.callback_query.answer()
    await update.callback_query.message.chat.send_action(ChatAction.TYPING)
    
    # Extract data
    name = context.user_data['challenge_name']
    challenge_type = context.user_data['challenge_type']
    start_date = context.user_data['start_date']
    end_date = context.user_data['end_date']
    is_free = context.user_data['is_free']
    price = context.user_data['price']
    description = context.user_data.get('description')
    admin_id = update.callback_query.from_user.id
    
    # Create challenge
    challenge = create_challenge(
        challenge_type=challenge_type,
        name=name,
        description=description,
        start_date=start_date,
        end_date=end_date,
        is_free=is_free,
        price=price,
        created_by=admin_id
    )
    
    if challenge:
        challenge_id = challenge['challenge_id']
        logger.info(f"Challenge {challenge_id} created by admin {admin_id}")
        
        # Prepare broadcast message
        price_str = "FREE" if is_free else f"Rs. {price}"
        broadcast_msg = get_challenge_start_cutoff_message(
            name, str(start_date), str(end_date), price_str
        )
        
        message = f"""✅ *Challenge Created Successfully!*

Challenge ID: #{challenge_id}
Name: {name}

📅 Scheduled: {start_date}
🔔 Broadcast: Automatic at 12:01 AM on {start_date}

Participants will receive:
{broadcast_msg}

Status: SCHEDULED"""
        
        await update.callback_query.message.reply_text(message, parse_mode="Markdown")
        
        # Clear user data
        context.user_data.clear()
    else:
        await update.callback_query.message.reply_text(
            "❌ Failed to create challenge. Please try again.",
            parse_mode="Markdown"
        )
    
    return ConversationHandler.END

async def callback_cancel_create(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel challenge creation"""
    await update.callback_query.answer()
    await update.callback_query.message.reply_text("❌ Challenge creation cancelled.")
    context.user_data.clear()
    return ConversationHandler.END

async def callback_view_active_challenges(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View all active challenges"""
    await update.callback_query.answer()
    
    challenges = get_active_challenges()
    
    if not challenges:
        await update.callback_query.message.reply_text("📭 No active challenges at the moment.")
        return
    
    message = "🏆 *Active Challenges:*\n\n"
    
    for challenge in challenges:
        status = "🔴 Scheduled" if challenge['status'] == 'scheduled' else "🟢 Active"
        price_str = "FREE" if challenge['is_free'] else f"Rs. {challenge['price']}"
        
        message += f"""
• *{challenge['name']}*
  ID: #{challenge['challenge_id']}
  Status: {status}
  Dates: {challenge['start_date']} → {challenge['end_date']}
  Entry: {price_str}
"""
    
    await update.callback_query.message.reply_text(message, parse_mode="Markdown")

async def callback_payment_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View payment status for paid challenges"""
    await update.callback_query.answer()
    
    unpaid = get_unpaid_challenge_participants()
    
    if not unpaid:
        await update.callback_query.message.reply_text(
            "✅ All challenge payments are up to date!",
            parse_mode="Markdown"
        )
        return
    
    message = f"💳 *Pending Payments:*\n\n({len(unpaid)} users)\n"
    
    for participant in unpaid[:10]:  # Show first 10
        message += f"""
• {participant['full_name']} (@{participant['username']})
  Challenge: {participant['challenge_name']}
  Amount Due: Rs. {participant['amount_due']}
  Due: {participant['due_date']}
"""
    
    if len(unpaid) > 10:
        message += f"\n... and {len(unpaid) - 10} more"
    
    await update.callback_query.message.reply_text(message, parse_mode="Markdown")

async def callback_challenge_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View challenge statistics"""
    await update.callback_query.answer()
    
    stats = get_challenge_stats()
    
    if stats:
        message = """📊 *Challenge Statistics*

• Total Challenges: {}
• Active: {}
• Completed: {}
• Active Participants: {}
• Users Completed: {}""".format(
            stats.get('total_challenges', 0),
            stats.get('active_challenges', 0),
            stats.get('completed_challenges', 0),
            stats.get('active_participants', 0),
            stats.get('users_completed', 0)
        )
    else:
        message = "📊 *Challenge Statistics*\n\nNo data available yet."
    
    await update.callback_query.message.reply_text(message, parse_mode="Markdown")

def get_admin_challenge_handler():
    """Return ConversationHandler for admin challenge creation"""
    from telegram.ext import MessageHandler, filters, CallbackQueryHandler
    
    return ConversationHandler(
        entry_points=[CommandHandler("admin_challenges", cmd_admin_challenges)],
        states={
            CREATE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_challenge_name)],
            CREATE_TYPE: [CallbackQueryHandler(callback_challenge_type)],
            CREATE_START: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_start_date)],
            CREATE_END: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_end_date)],
            CREATE_PRICING: [CallbackQueryHandler(callback_challenge_pricing)],
            CREATE_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_entry_amount)],
            CREATE_DESC: [MessageHandler(filters.TEXT, process_challenge_desc)],
            CREATE_CONFIRM: [
                CallbackQueryHandler(callback_confirm_create, pattern="^confirm_create_challenge$"),
                CallbackQueryHandler(callback_cancel_create, pattern="^cancel_create_challenge$")
            ],
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
        allow_reentry=False
    )

# Import at module level for convenience
from telegram.ext import CommandHandler
