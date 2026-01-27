"""
Reminder Settings Handlers
- User interface for configuring reminders
- Enable/disable reminders
- Set custom intervals and times
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from src.database.reminder_operations import (
    get_reminder_profile as get_reminder_preferences,
    toggle_water_reminder, set_water_reminder_interval,
    toggle_weight_reminder, set_weight_reminder_time,
    toggle_meal_reminder, set_meal_reminder_time,
)

# Backward-compatible aliases (map habits UI to dinner reminder for now)
def toggle_habits_reminder(user_id: int, enabled: bool) -> bool:
    return toggle_meal_reminder(user_id, "dinner", enabled)


def set_habits_reminder_time(user_id: int, time_str: str) -> bool:
    return set_meal_reminder_time(user_id, "dinner", time_str)

logger = logging.getLogger(__name__)

# States
REMINDER_MENU, WATER_SETTINGS, SET_WATER_INTERVAL, WEIGHT_SETTINGS, SET_WEIGHT_TIME, HABITS_SETTINGS, SET_HABITS_TIME = range(7)


async def cmd_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show reminder settings menu"""
    user_id = update.effective_user.id
    prefs = get_reminder_preferences(user_id)
    
    if not prefs:
        await update.message.reply_text("❌ Error loading reminder preferences")
        return ConversationHandler.END
    
    keyboard = [
        [InlineKeyboardButton(
            f"💧 Water Reminders {'✅' if prefs['water_reminder_enabled'] else '❌'}",
            callback_data="reminder_water"
        )],
        [InlineKeyboardButton(
            f"⚖️ Weight Reminders {'✅' if prefs['weight_reminder_enabled'] else '❌'}",
            callback_data="reminder_weight"
        )],
        [InlineKeyboardButton(
            f"📝 Habits Reminders {'✅' if prefs['habits_reminder_enabled'] else '❌'}",
            callback_data="reminder_habits"
        )],
        [InlineKeyboardButton("❌ Close", callback_data="reminder_close")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "⏰ *Reminder Settings*\n\n"
        "Customize your reminders to stay on track!\n"
        "Click on any reminder to configure it.",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    
    return REMINDER_MENU


async def callback_water_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Water reminder settings"""
    query = update.callback_query
    user_id = query.from_user.id
    prefs = get_reminder_preferences(user_id)
    
    if not prefs:
        await query.answer("Error loading preferences")
        return REMINDER_MENU
    
    await query.answer()
    
    is_enabled = prefs['water_reminder_enabled']
    interval = prefs['water_reminder_interval_minutes']
    
    keyboard = [
        [InlineKeyboardButton(
            f"{'Turn OFF' if is_enabled else 'Turn ON'} 🔔",
            callback_data=f"water_toggle_{not is_enabled}"
        )],
        [InlineKeyboardButton("⏱️ Set Interval", callback_data="water_interval")],
        [
            InlineKeyboardButton("← Back", callback_data="reminder_back"),
            InlineKeyboardButton("Close ❌", callback_data="reminder_close"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    status = "✅ ON" if is_enabled else "❌ OFF"
    message = (
        f"💧 *Water Reminders*\n\n"
        f"Status: {status}\n"
        f"Current Interval: Every {interval} minutes\n\n"
        f"Set how often you want to be reminded to drink water."
    )
    
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode="Markdown")
    return WATER_SETTINGS


async def callback_water_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle water reminders on/off"""
    query = update.callback_query
    user_id = query.from_user.id
    enabled = query.data.split("_")[2] == "True"
    
    await query.answer()
    
    success = toggle_water_reminder(user_id, enabled)
    
    if success:
        status = "✅ enabled" if enabled else "❌ disabled"
        await query.edit_message_text(
            f"💧 Water reminders {status}!",
            parse_mode="Markdown"
        )
        logger.info(f"Water reminder {status} for user {user_id}")
        # Reschedule per-user water reminder
        try:
            if context and getattr(context, 'application', None):
                from src.utils.scheduled_jobs import schedule_user_water_reminder, cancel_user_water_reminder
                prefs = get_reminder_preferences(user_id)
                if prefs and prefs.get('water_reminder_enabled', True):
                    interval = prefs.get('water_reminder_interval_minutes', 60)
                    schedule_user_water_reminder(context.application, user_id, interval)
                else:
                    cancel_user_water_reminder(context.application, user_id)
        except Exception:
            logger.debug('Could not reschedule water reminder')
        return REMINDER_MENU
    else:
        await query.edit_message_text("❌ Error updating reminder")
        return WATER_SETTINGS


async def callback_water_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show water reminder interval options"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("⏱️ Every 15 minutes", callback_data="water_interval_15")],
        [InlineKeyboardButton("⏱️ Every 30 minutes", callback_data="water_interval_30")],
        [InlineKeyboardButton("⏱️ Every 1 hour", callback_data="water_interval_60")],
        [InlineKeyboardButton("⏱️ Every 2 hours", callback_data="water_interval_120")],
        [InlineKeyboardButton("⏱️ Every 3 hours", callback_data="water_interval_180")],
        [InlineKeyboardButton("← Back", callback_data="reminder_water")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "💧 *Set Water Reminder Interval*\n\n"
        "Choose how often you want water reminders:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    
    return SET_WATER_INTERVAL


async def callback_set_water_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set water reminder interval"""
    query = update.callback_query
    user_id = query.from_user.id
    interval = int(query.data.split("_")[2])
    
    await query.answer()
    
    success = set_water_reminder_interval(user_id, interval)
    
    if success:
        interval_text = {
            15: "15 minutes",
            30: "30 minutes",
            60: "1 hour",
            120: "2 hours",
            180: "3 hours"
        }.get(interval, f"{interval} minutes")
        
        await query.edit_message_text(
            f"✅ Water reminders set to every **{interval_text}**",
            parse_mode="Markdown"
        )
        logger.info(f"Water interval set to {interval}m for user {user_id}")
        # Reschedule per-user water reminder with new interval
        try:
            if context and getattr(context, 'application', None):
                from src.utils.scheduled_jobs import schedule_user_water_reminder, cancel_user_water_reminder
                prefs = get_reminder_preferences(user_id)
                if prefs and prefs.get('water_reminder_enabled', True):
                    schedule_user_water_reminder(context.application, user_id, interval)
                else:
                    cancel_user_water_reminder(context.application, user_id)
        except Exception:
            logger.debug('Could not reschedule water reminder after interval change')
        return REMINDER_MENU
    else:
        await query.edit_message_text("❌ Error setting interval")
        return SET_WATER_INTERVAL


async def callback_weight_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Weight reminder settings"""
    query = update.callback_query
    user_id = query.from_user.id
    prefs = get_reminder_preferences(user_id)
    
    if not prefs:
        await query.answer("Error loading preferences")
        return REMINDER_MENU
    
    await query.answer()
    
    is_enabled = prefs['weight_reminder_enabled']
    time_str = prefs['weight_reminder_time']
    
    keyboard = [
        [InlineKeyboardButton(
            f"{'Turn OFF' if is_enabled else 'Turn ON'} 🔔",
            callback_data=f"weight_toggle_{not is_enabled}"
        )],
        [InlineKeyboardButton("⏰ Set Time", callback_data="weight_time")],
        [
            InlineKeyboardButton("← Back", callback_data="reminder_back"),
            InlineKeyboardButton("Close ❌", callback_data="reminder_close"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    status = "✅ ON" if is_enabled else "❌ OFF"
    message = (
        f"⚖️ *Weight Reminders*\n\n"
        f"Status: {status}\n"
        f"Current Time: {time_str}\n\n"
        f"Weigh yourself daily to track your progress!"
    )
    
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode="Markdown")
    return WEIGHT_SETTINGS


async def callback_weight_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle weight reminders on/off"""
    query = update.callback_query
    user_id = query.from_user.id
    enabled = query.data.split("_")[2] == "True"
    
    await query.answer()
    
    success = toggle_weight_reminder(user_id, enabled)
    
    if success:
        status = "✅ enabled" if enabled else "❌ disabled"
        await query.edit_message_text(
            f"⚖️ Weight reminders {status}!",
            parse_mode="Markdown"
        )
        logger.info(f"Weight reminder {status} for user {user_id}")
        # Reschedule per-user weight reminder
        try:
            if context and getattr(context, 'application', None):
                from src.utils.scheduled_jobs import schedule_user_weight_reminder, cancel_user_weight_reminder
                prefs = get_reminder_preferences(user_id)
                if prefs and prefs.get('weight_reminder_enabled', True):
                    time_str = prefs.get('weight_reminder_time', '06:00')
                    schedule_user_weight_reminder(context.application, user_id, time_str)
                else:
                    cancel_user_weight_reminder(context.application, user_id)
        except Exception:
            logger.debug('Could not reschedule weight reminder')
        return REMINDER_MENU
    else:
        await query.edit_message_text("❌ Error updating reminder")
        return WEIGHT_SETTINGS


async def callback_weight_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt for weight reminder time"""
    query = update.callback_query
    await query.answer()
    
    prefs = get_reminder_preferences(query.from_user.id)
    current_time = prefs['weight_reminder_time'] if prefs else "06:00"
    
    await query.edit_message_text(
        f"⚖️ *Set Weight Reminder Time*\n\n"
        f"Current time: {current_time}\n\n"
        f"Send time in HH:MM format (24-hour)\n"
        f"Example: 06:30 or 14:00",
        parse_mode="Markdown"
    )
    
    return SET_WEIGHT_TIME


async def handle_weight_time_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle weight reminder time input"""
    user_id = update.effective_user.id
    time_str = update.message.text.strip()
    
    success = set_weight_reminder_time(user_id, time_str)
    
    if success:
        await update.message.reply_text(
            f"✅ Weight reminder time set to **{time_str}**",
            parse_mode="Markdown"
        )
        logger.info(f"Weight time set to {time_str} for user {user_id}")
        # Reschedule per-user weight reminder at new time
        try:
            if context and getattr(context, 'application', None):
                from src.utils.scheduled_jobs import schedule_user_weight_reminder, cancel_user_weight_reminder
                prefs = get_reminder_preferences(user_id)
                if prefs and prefs.get('weight_reminder_enabled', True):
                    schedule_user_weight_reminder(context.application, user_id, time_str)
                else:
                    cancel_user_weight_reminder(context.application, user_id)
        except Exception:
            logger.debug('Could not reschedule weight reminder after time change')
        return REMINDER_MENU
    else:
        await update.message.reply_text(
            "❌ Invalid time format. Use HH:MM (e.g., 06:30)",
            parse_mode="Markdown"
        )
        return SET_WEIGHT_TIME


async def callback_habits_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Habits reminder settings"""
    query = update.callback_query
    user_id = query.from_user.id
    prefs = get_reminder_preferences(user_id)
    
    if not prefs:
        await query.answer("Error loading preferences")
        return REMINDER_MENU
    
    await query.answer()
    
    is_enabled = prefs['habits_reminder_enabled']
    time_str = prefs['habits_reminder_time']
    
    keyboard = [
        [InlineKeyboardButton(
            f"{'Turn OFF' if is_enabled else 'Turn ON'} 🔔",
            callback_data=f"habits_toggle_{not is_enabled}"
        )],
        [InlineKeyboardButton("⏰ Set Time", callback_data="habits_time")],
        [
            InlineKeyboardButton("← Back", callback_data="reminder_back"),
            InlineKeyboardButton("Close ❌", callback_data="reminder_close"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    status = "✅ ON" if is_enabled else "❌ OFF"
    message = (
        f"📝 *Habits Reminders*\n\n"
        f"Status: {status}\n"
        f"Current Time: {time_str}\n\n"
        f"Log your daily habits and stay consistent!"
    )
    
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode="Markdown")
    return HABITS_SETTINGS


async def callback_habits_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle habits reminders on/off"""
    query = update.callback_query
    user_id = query.from_user.id
    enabled = query.data.split("_")[2] == "True"
    
    await query.answer()
    
    success = toggle_habits_reminder(user_id, enabled)
    
    if success:
        status = "✅ enabled" if enabled else "❌ disabled"
        await query.edit_message_text(
            f"📝 Habits reminders {status}!",
            parse_mode="Markdown"
        )
        logger.info(f"Habits reminder {status} for user {user_id}")
        return REMINDER_MENU
    else:
        await query.edit_message_text("❌ Error updating reminder")
        return HABITS_SETTINGS


async def callback_habits_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt for habits reminder time"""
    query = update.callback_query
    await query.answer()
    
    prefs = get_reminder_preferences(query.from_user.id)
    current_time = prefs['habits_reminder_time'] if prefs else "20:00"
    
    await query.edit_message_text(
        f"📝 *Set Habits Reminder Time*\n\n"
        f"Current time: {current_time}\n\n"
        f"Send time in HH:MM format (24-hour)\n"
        f"Example: 20:00 or 21:30",
        parse_mode="Markdown"
    )
    
    return SET_HABITS_TIME


async def handle_habits_time_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle habits reminder time input"""
    user_id = update.effective_user.id
    time_str = update.message.text.strip()
    
    success = set_habits_reminder_time(user_id, time_str)
    
    if success:
        await update.message.reply_text(
            f"✅ Habits reminder time set to **{time_str}**",
            parse_mode="Markdown"
        )
        logger.info(f"Habits time set to {time_str} for user {user_id}")
        return REMINDER_MENU
    else:
        await update.message.reply_text(
            "❌ Invalid time format. Use HH:MM (e.g., 20:00)",
            parse_mode="Markdown"
        )
        return SET_HABITS_TIME


async def callback_reminder_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Go back to main reminder menu"""
    query = update.callback_query
    user_id = query.from_user.id
    prefs = get_reminder_preferences(user_id)
    
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton(
            f"💧 Water Reminders {'✅' if prefs['water_reminder_enabled'] else '❌'}",
            callback_data="reminder_water"
        )],
        [InlineKeyboardButton(
            f"⚖️ Weight Reminders {'✅' if prefs['weight_reminder_enabled'] else '❌'}",
            callback_data="reminder_weight"
        )],
        [InlineKeyboardButton(
            f"📝 Habits Reminders {'✅' if prefs['habits_reminder_enabled'] else '❌'}",
            callback_data="reminder_habits"
        )],
        [InlineKeyboardButton("❌ Close", callback_data="reminder_close")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "⏰ *Reminder Settings*\n\n"
        "Customize your reminders to stay on track!\n"
        "Click on any reminder to configure it.",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    
    return REMINDER_MENU


async def callback_reminder_close(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Close reminder settings"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text("✅ Reminder settings saved!")
    return ConversationHandler.END


async def callback_quick_log_water(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Quick action to start water logging from reminder"""
    query = update.callback_query
    await query.answer()
    
    from src.handlers.activity_handlers import cmd_water
    
    # Call the water command handler with the callback_query update
    await cmd_water(update, context)


async def callback_quick_set_water_timer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Quick action to set water reminder interval from reminder"""
    query = update.callback_query
    user_id = query.from_user.id
    prefs = get_reminder_preferences(user_id)
    
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("15 min ⚡", callback_data="quick_water_interval_15")],
        [InlineKeyboardButton("30 min", callback_data="quick_water_interval_30")],
        [InlineKeyboardButton("1 hour", callback_data="quick_water_interval_60")],
        [InlineKeyboardButton("2 hours", callback_data="quick_water_interval_120")],
        [InlineKeyboardButton("3 hours", callback_data="quick_water_interval_180")],
        [InlineKeyboardButton("✏️ Custom", callback_data="quick_water_interval_custom")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    current_interval = prefs.get('water_reminder_interval_minutes', 60)
    
    await query.edit_message_text(
        f"⏱️ *Set Water Reminder Interval*\n\n"
        f"Current: Every {current_interval} minutes\n\n"
        f"Select new interval:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


async def callback_quick_water_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle quick water interval selection"""
    query = update.callback_query
    user_id = query.from_user.id
    
    # Extract interval from callback_data (e.g., "quick_water_interval_30" -> 30)
    interval = int(query.data.split("_")[-1])
    
    await query.answer()
    
    success = set_water_reminder_interval(user_id, interval)
    
    if success:
        interval_text = {
            15: "15 minutes",
            30: "30 minutes",
            60: "1 hour",
            120: "2 hours",
            180: "3 hours"
        }.get(interval, f"{interval} minutes")
        
        await query.edit_message_text(
            f"✅ Water reminder interval set to **{interval_text}**",
            parse_mode="Markdown"
        )
        logger.info(f"Quick set water interval to {interval} minutes for user {user_id}")
    else:
        await query.edit_message_text("❌ Failed to set interval")


async def callback_quick_water_interval_custom(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle custom water interval input from reminder"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "⏱️ *Enter Custom Reminder Interval*\n\n"
        "Send the number of minutes between reminders\n\n"
        "Example: 45 or 90\n"
        "Valid range: 15 to 480 minutes (8 hours)",
        parse_mode="Markdown"
    )
    
    context.user_data['waiting_for_custom_water_interval'] = True


async def callback_quick_turn_off_water_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Quick action to turn off water reminders"""
    query = update.callback_query
    user_id = query.from_user.id
    
    await query.answer()
    
    success = toggle_water_reminder(user_id, False)
    
    if success:
        await query.edit_message_text(
            "❌ Water reminders turned **OFF**\n\n"
            "You can turn them back on anytime using /reminders",
            parse_mode="Markdown"
        )
        logger.info(f"Water reminders disabled for user {user_id}")
    else:
        await query.edit_message_text("❌ Failed to update settings")


async def handle_custom_water_interval_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle custom water interval input"""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    # CRITICAL: Only process if explicitly waiting for custom interval
    # Otherwise allow other handlers (ConversationHandlers) to process the message
    if not context.user_data.get('waiting_for_custom_water_interval'):
        return
    
    context.user_data['waiting_for_custom_water_interval'] = False
    
    try:
        interval = int(text)
        
        # Validate range
        if interval < 15 or interval > 480:
            await update.message.reply_text(
                "❌ Invalid interval! Must be between 15 and 480 minutes.",
                parse_mode="Markdown"
            )
            return
        
        # Save the custom interval
        success = set_water_reminder_interval(user_id, interval)
        
        if success:
            await update.message.reply_text(
                f"✅ Water reminder interval set to **{interval} minutes**",
                parse_mode="Markdown"
            )
            logger.info(f"Custom water interval set to {interval} minutes for user {user_id}")
        else:
            await update.message.reply_text("❌ Failed to set interval")
    except ValueError:
        await update.message.reply_text(
            "❌ Please enter a valid number (e.g., 30, 60, 90)",
            parse_mode="Markdown"
        )


def get_reminder_conversation_handler():
    """Get conversation handler for reminders"""
    return ConversationHandler(
        entry_points=[
            CommandHandler('reminders', cmd_reminders),
            CallbackQueryHandler(cmd_reminders, pattern="^cmd_reminders$"),
        ],
        states={
            REMINDER_MENU: [
                CallbackQueryHandler(callback_water_settings, pattern="^reminder_water$"),
                CallbackQueryHandler(callback_weight_settings, pattern="^reminder_weight$"),
                CallbackQueryHandler(callback_habits_settings, pattern="^reminder_habits$"),
                CallbackQueryHandler(callback_reminder_close, pattern="^reminder_close$"),
            ],
            WATER_SETTINGS: [
                CallbackQueryHandler(callback_water_toggle, pattern="^water_toggle_"),
                CallbackQueryHandler(callback_water_interval, pattern="^water_interval$"),
                CallbackQueryHandler(callback_reminder_back, pattern="^reminder_back$"),
                CallbackQueryHandler(callback_reminder_close, pattern="^reminder_close$"),
            ],
            SET_WATER_INTERVAL: [
                CallbackQueryHandler(callback_set_water_interval, pattern="^water_interval_"),
                CallbackQueryHandler(callback_water_settings, pattern="^reminder_water$"),
            ],
            WEIGHT_SETTINGS: [
                CallbackQueryHandler(callback_weight_toggle, pattern="^weight_toggle_"),
                CallbackQueryHandler(callback_weight_time, pattern="^weight_time$"),
                CallbackQueryHandler(callback_reminder_back, pattern="^reminder_back$"),
                CallbackQueryHandler(callback_reminder_close, pattern="^reminder_close$"),
            ],
            SET_WEIGHT_TIME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_weight_time_input),
            ],
            HABITS_SETTINGS: [
                CallbackQueryHandler(callback_habits_toggle, pattern="^habits_toggle_"),
                CallbackQueryHandler(callback_habits_time, pattern="^habits_time$"),
                CallbackQueryHandler(callback_reminder_back, pattern="^reminder_back$"),
                CallbackQueryHandler(callback_reminder_close, pattern="^reminder_close$"),
            ],
            SET_HABITS_TIME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_habits_time_input),
            ],
        },
        fallbacks=[],
        per_message=False
    )
