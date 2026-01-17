"""
Broadcast messaging system for admin
- Personalized messages to all users
- Targeted broadcasts (active/inactive users)
- Automated follow-up system for inactive members
"""

import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from src.database.role_operations import is_admin as is_admin_db
from src.database.connection import execute_query

logger = logging.getLogger(__name__)

# Conversation states
BROADCAST_SELECT, BROADCAST_MESSAGE, CONFIRM_BROADCAST = range(3)

# Broadcast types
BROADCAST_ALL = "all"
BROADCAST_ACTIVE = "active"
BROADCAST_INACTIVE = "inactive"


async def cmd_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start broadcast menu - Admin only"""
    user_id = update.effective_user.id
    
    # Handle both command and callback contexts
    if update.callback_query:
        await update.callback_query.answer()
        message = update.callback_query.message
    else:
        message = update.message
    
    if not is_admin_db(user_id):
        await message.reply_text("❌ Admin access only.")
        return ConversationHandler.END
    
    keyboard = [
        [InlineKeyboardButton("📢 All Users", callback_data="broadcast_all")],
        [InlineKeyboardButton("✅ Active Users Only", callback_data="broadcast_active")],
        [InlineKeyboardButton("💤 Inactive Users Only", callback_data="broadcast_inactive")],
        [InlineKeyboardButton("❌ Cancel", callback_data="broadcast_cancel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = (
        "📢 *Broadcast Message System*\n\n"
        "Select who should receive the message:\n\n"
        "• *All Users* - Everyone registered\n"
        "• *Active Users* - Members active in last 30 days\n"
        "• *Inactive Users* - Members inactive 30+ days\n\n"
        "Messages will be personalized with user's name."
    )
    
    await message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    return BROADCAST_SELECT


async def broadcast_select_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle broadcast type selection"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "broadcast_cancel":
        await query.edit_message_text("❌ Broadcast cancelled.")
        return ConversationHandler.END
    
    # Store broadcast type
    broadcast_type = query.data.replace("broadcast_", "")
    context.user_data['broadcast_type'] = broadcast_type
    
    # Get user count
    if broadcast_type == BROADCAST_ALL:
        count_query = "SELECT COUNT(*) as count FROM users WHERE is_active = TRUE"
        type_name = "All Users"
    elif broadcast_type == BROADCAST_ACTIVE:
        count_query = """
            SELECT COUNT(DISTINCT u.user_id) as count 
            FROM users u
            LEFT JOIN attendance_log a ON u.user_id = a.user_id
            WHERE u.is_active = TRUE 
            AND a.created_at >= NOW() - INTERVAL '30 days'
        """
        type_name = "Active Users (last 30 days)"
    else:  # BROADCAST_INACTIVE
        count_query = """
            SELECT COUNT(*) as count FROM users u
            WHERE u.is_active = TRUE
            AND NOT EXISTS (
                SELECT 1 FROM attendance_log a
                WHERE a.user_id = u.user_id
                AND a.created_at >= NOW() - INTERVAL '30 days'
            )
        """
        type_name = "Inactive Users (30+ days)"
    
    result = execute_query(count_query, fetch_one=True)
    user_count = result['count'] if result else 0
    
    context.user_data['broadcast_count'] = user_count
    
    text = (
        f"📢 *Broadcast to: {type_name}*\n\n"
        f"👥 Recipients: *{user_count}* users\n\n"
        "📝 Now send your message:\n\n"
        "You can use `{name}` in your message to personalize it.\n"
        "Example: \"Hi {name}, we miss you at the gym!\"\n\n"
        "Type /cancel to abort."
    )
    
    await query.edit_message_text(text, parse_mode='Markdown')
    return BROADCAST_MESSAGE


async def broadcast_receive_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive and confirm broadcast message"""
    message_text = update.message.text
    context.user_data['broadcast_message'] = message_text
    
    broadcast_type = context.user_data['broadcast_type']
    user_count = context.user_data['broadcast_count']
    
    # Show preview with personalization
    preview = message_text.replace("{name}", "John Doe")
    
    keyboard = [
        [InlineKeyboardButton("✅ Send Broadcast", callback_data="confirm_send")],
        [InlineKeyboardButton("❌ Cancel", callback_data="confirm_cancel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = (
        "📋 *Broadcast Preview*\n\n"
        f"👥 Recipients: {user_count} users\n"
        f"📢 Type: {broadcast_type.title()}\n\n"
        "*Preview:*\n"
        f"{preview}\n\n"
        "Ready to send?"
    )
    
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    return CONFIRM_BROADCAST


async def broadcast_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send broadcast to all selected users"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "confirm_cancel":
        await query.edit_message_text("❌ Broadcast cancelled.")
        return ConversationHandler.END
    
    broadcast_type = context.user_data['broadcast_type']
    message_template = context.user_data['broadcast_message']
    
    # Get recipient list
    if broadcast_type == BROADCAST_ALL:
        user_query = """
            SELECT user_id, full_name FROM users 
            WHERE is_active = TRUE
            ORDER BY user_id
        """
    elif broadcast_type == BROADCAST_ACTIVE:
        user_query = """
            SELECT DISTINCT u.user_id, u.full_name
            FROM users u
            INNER JOIN attendance_log a ON u.user_id = a.user_id
            WHERE u.is_active = TRUE 
            AND a.created_at >= NOW() - INTERVAL '30 days'
            ORDER BY u.user_id
        """
    else:  # BROADCAST_INACTIVE
        user_query = """
            SELECT u.user_id, u.full_name FROM users u
            WHERE u.is_active = TRUE
            AND NOT EXISTS (
                SELECT 1 FROM attendance_log a
                WHERE a.user_id = u.user_id
                AND a.created_at >= NOW() - INTERVAL '30 days'
            )
            ORDER BY u.user_id
        """
    
    users = execute_query(user_query, fetch_all=True)
    
    if not users:
        await query.edit_message_text("❌ No users found to send broadcast.")
        return ConversationHandler.END
    
    await query.edit_message_text(f"📤 Sending to {len(users)} users... Please wait.")
    
    # Send to all users
    success_count = 0
    fail_count = 0
    
    for user in users:
        try:
            # Personalize message
            personalized_message = message_template.replace("{name}", user['full_name'] or "there")
            
            # Send message
            await context.bot.send_message(
                chat_id=user['user_id'],
                text=personalized_message,
                parse_mode='Markdown'
            )
            success_count += 1
            
            # Log broadcast
            execute_query(
                """
                INSERT INTO broadcast_log (user_id, message, broadcast_type, sent_at)
                VALUES (%s, %s, %s, NOW())
                """,
                (user['user_id'], message_template, broadcast_type)
            )
            
        except Exception as e:
            logger.error(f"Failed to send to {user['user_id']}: {e}")
            fail_count += 1
    
    # Final report
    report_text = (
        "✅ *Broadcast Complete!*\n\n"
        f"📤 Sent: {success_count}\n"
        f"❌ Failed: {fail_count}\n"
        f"📊 Total: {len(users)}"
    )
    
    await context.bot.send_message(
        chat_id=update.effective_user.id,
        text=report_text,
        parse_mode='Markdown'
    )
    
    return ConversationHandler.END


async def broadcast_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel broadcast conversation"""
    await update.message.reply_text("❌ Broadcast cancelled.")
    return ConversationHandler.END


# ==================== AUTOMATED FOLLOW-UP SYSTEM ====================

async def send_followup_to_inactive_users(context: ContextTypes.DEFAULT_TYPE):
    """
    Scheduled job to send automated follow-up messages to inactive users
    Runs daily to check for users inactive for 7, 14, 30 days
    """
    logger.info("Running automated follow-up for inactive users...")
    
    # Define follow-up templates for different inactivity periods
    followup_templates = {
        7: {
            'message': (
                "Hi {name}! 👋\n\n"
                "We noticed you haven't visited the gym in a week. "
                "Everything okay?\n\n"
                "💪 Your fitness journey is important to us!\n"
                "We're here whenever you're ready to get back on track.\n\n"
                "Need help with your schedule? Just let us know! 😊"
            ),
            'days': 7
        },
        14: {
            'message': (
                "Hey {name}! 🌟\n\n"
                "It's been 2 weeks since we've seen you at the gym. "
                "We miss you!\n\n"
                "🎯 Remember your goals? Let's crush them together!\n"
                "Your membership is active and waiting for you.\n\n"
                "Reply to this message if you need any motivation or support! 💪"
            ),
            'days': 14
        },
        30: {
            'message': (
                "Hello {name}! 🏋️‍♂️\n\n"
                "A whole month has passed since your last visit. "
                "We really miss seeing you!\n\n"
                "🔥 Don't let your progress slip away!\n"
                "📅 Special offer: Book a free personal training session with us!\n\n"
                "Let's get you back on track. Your health matters! ❤️\n\n"
                "Reply 'YES' to schedule your comeback session!"
            ),
            'days': 30
        }
    }
    
    for days, template in followup_templates.items():
        # Query users inactive for exactly this many days
        query = f"""
            SELECT u.user_id, u.full_name
            FROM users u
            WHERE u.is_active = TRUE
            AND NOT EXISTS (
                SELECT 1 FROM attendance_log a
                WHERE a.user_id = u.user_id
                AND a.created_at >= NOW() - INTERVAL '{days} days'
            )
            AND EXISTS (
                SELECT 1 FROM attendance_log a2
                WHERE a2.user_id = u.user_id
                AND a2.created_at >= NOW() - INTERVAL '{days + 1} days'
                AND a2.created_at < NOW() - INTERVAL '{days} days'
            )
            AND NOT EXISTS (
                SELECT 1 FROM broadcast_log bl
                WHERE bl.user_id = u.user_id
                AND bl.broadcast_type = 'followup_{days}d'
                AND bl.sent_at >= NOW() - INTERVAL '{days} days'
            )
        """
        
        users = execute_query(query, fetch_all=True)
        
        if not users:
            logger.info(f"No users found for {days}-day follow-up")
            continue
        
        logger.info(f"Sending {days}-day follow-up to {len(users)} users")
        
        for user in users:
            try:
                # Personalize message
                message = template['message'].replace("{name}", user['full_name'] or "there")
                
                # Send message
                await context.bot.send_message(
                    chat_id=user['user_id'],
                    text=message
                )
                
                # Log follow-up
                execute_query(
                    """
                    INSERT INTO broadcast_log (user_id, message, broadcast_type, sent_at)
                    VALUES (%s, %s, %s, NOW())
                    """,
                    (user['user_id'], message, f'followup_{days}d')
                )
                
                logger.info(f"Sent {days}-day follow-up to user {user['user_id']}")
                
            except Exception as e:
                logger.error(f"Failed to send {days}-day follow-up to {user['user_id']}: {e}")


async def cmd_followup_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: Configure automated follow-up settings"""
    user_id = update.effective_user.id
    
    # Handle both command and callback contexts
    if update.callback_query:
        await update.callback_query.answer()
        message = update.callback_query.message
    else:
        message = update.message
    
    if not is_admin_db(user_id):
        await message.reply_text("❌ Admin access only.")
        return
    
    # Get current follow-up stats
    query = """
        SELECT 
            COUNT(DISTINCT user_id) FILTER (WHERE broadcast_type = 'followup_7d' AND sent_at >= NOW() - INTERVAL '7 days') as sent_7d,
            COUNT(DISTINCT user_id) FILTER (WHERE broadcast_type = 'followup_14d' AND sent_at >= NOW() - INTERVAL '14 days') as sent_14d,
            COUNT(DISTINCT user_id) FILTER (WHERE broadcast_type = 'followup_30d' AND sent_at >= NOW() - INTERVAL '30 days') as sent_30d
        FROM broadcast_log
    """
    
    stats = execute_query(query, fetch_one=True)
    
    keyboard = [
        [InlineKeyboardButton("📊 View Follow-up Log", callback_data="view_followup_log")],
        [InlineKeyboardButton("🔙 Back", callback_data="cmd_admin_dashboard")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = (
        "🤖 *Automated Follow-up System*\n\n"
        "*Status:* ✅ Active\n\n"
        "*Follow-up Schedule:*\n"
        "• 7 days inactive → Friendly reminder\n"
        "• 14 days inactive → Motivational message\n"
        "• 30 days inactive → Special offer\n\n"
        "*Messages Sent (Recent):*\n"
        f"• 7-day: {stats['sent_7d'] if stats else 0} users\n"
        f"• 14-day: {stats['sent_14d'] if stats else 0} users\n"
        f"• 30-day: {stats['sent_30d'] if stats else 0} users\n\n"
        "_Follow-ups run automatically every day at 9 AM_"
    )
    
    await message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')


async def view_broadcast_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: View broadcast history"""
    query = update.callback_query
    await query.answer()
    
    if not is_admin_db(update.effective_user.id):
        await query.edit_message_text("❌ Admin access only.")
        return
    
    # Get recent broadcasts
    history_query = """
        SELECT 
            broadcast_type,
            COUNT(*) as recipient_count,
            DATE(sent_at) as send_date
        FROM broadcast_log
        WHERE sent_at >= NOW() - INTERVAL '30 days'
        GROUP BY broadcast_type, DATE(sent_at)
        ORDER BY send_date DESC
        LIMIT 10
    """
    
    history = execute_query(history_query, fetch_all=True)
    
    if not history:
        await query.edit_message_text("📭 No broadcast history in the last 30 days.")
        return
    
    text = "📊 *Broadcast History (Last 30 Days)*\n\n"
    
    for record in history:
        broadcast_type = record['broadcast_type'].replace('_', ' ').title()
        text += f"📅 {record['send_date']}\n"
        text += f"📢 {broadcast_type}: {record['recipient_count']} users\n"
        text += "─────────────\n"
    
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="cmd_admin_dashboard")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')


# Create conversation handler
def get_broadcast_conversation_handler():
    """Returns the ConversationHandler for broadcast system"""
    return ConversationHandler(
        entry_points=[
            CommandHandler('broadcast', cmd_broadcast),
            CallbackQueryHandler(cmd_broadcast, pattern='^cmd_broadcast$')
        ],
        states={
            BROADCAST_SELECT: [
                CallbackQueryHandler(broadcast_select_type, pattern='^broadcast_')
            ],
            BROADCAST_MESSAGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, broadcast_receive_message),
                CommandHandler('cancel', broadcast_cancel)
            ],
            CONFIRM_BROADCAST: [
                CallbackQueryHandler(broadcast_send, pattern='^confirm_')
            ]
        },
        fallbacks=[CommandHandler('cancel', broadcast_cancel)],
        name="broadcast_conversation",
        persistent=False
    )
