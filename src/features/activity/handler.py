"""
Activity Handlers Module
Handles user activity logging (weight, water, meals, habits, check-ins)
"""

import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from src.database.activity_operations import (
    log_weight, log_water, log_meal, log_habits, get_today_log, get_today_weight, get_yesterday_weight
)
from src.database.attendance_operations import (
    create_attendance_request, get_user_attendance_today
)
from src.utils.guards import check_approval
from src.utils.access_gate import check_app_feature_access
from src.utils.cutoff_enforcement import enforce_cutoff_check

logger = logging.getLogger("src.features.activity.handler")

# Conversation states
WEIGHT_VALUE, WATER_CUPS, MEAL_PHOTO, HABITS_CONFIRM, CHECKIN_METHOD, CHECKIN_PHOTO = range(6)

async def cmd_weight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start weight logging or handle edit_weight callback"""
    # Check access gate first
    if not await check_app_feature_access(update, context):
        return ConversationHandler.END
    
    # Check if approved first
    if not await check_approval(update, context):
        return ConversationHandler.END
    
    # Check cutoff time
    allowed, cutoff_message = enforce_cutoff_check("weight logging")
    if not allowed:
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.message.reply_text(cutoff_message)
        else:
            await update.message.reply_text(cutoff_message)
        return ConversationHandler.END
    
    # Handle both command and callback contexts
    if update.callback_query:
        await update.callback_query.answer()
        user = update.callback_query.from_user
        message = update.callback_query.message
        callback_data = update.callback_query.data
    else:
        user = update.message.from_user
        message = update.message
        callback_data = None
    
    # If this is an edit_weight callback, send edit prompt and return WEIGHT_VALUE
    if callback_data == "edit_weight":
        current_weight = get_today_weight(user.id)
        keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data="cancel")]]
        # Set a flag in user_data to indicate edit mode
        context.user_data['weight_edit_mode'] = True
        await message.reply_text(
            f"✏️ *Edit Your Weight*\n\n"
            f"Current Weight: {current_weight} kg\n\n"
            f"Enter your new weight in kg (e.g., 76.5):",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        logger.info(f"[WEIGHT_EDIT] User {user.id} started editing weight. Current: {current_weight}kg")
        return WEIGHT_VALUE
    
    # Check if weight already entered today
    today_weight = get_today_weight(user.id)
    if today_weight:
        keyboard = [
            [InlineKeyboardButton("✏️ Edit Weight", callback_data="edit_weight")],
            [InlineKeyboardButton("👋 Come Tomorrow", callback_data="cancel")],
        ]
        await message.reply_text(
            f"✅ *Weight Already Logged Today*\n\n"
            f"📊 Your Weight: {today_weight} kg\n\n"
            f"You have already entered your weight for today. "
            f"Come back tomorrow to log again! 💪\n\n"
            f"Want to edit it?",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        logger.info(f"[WEIGHT_DUPLICATE] User {user.id} attempted to log weight again. Already logged: {today_weight}kg")
        return ConversationHandler.END
    
    logger.info(f"User {user.id} started weight logging - Chat ID: {message.chat_id}")
    
    reply_keyboard = [["⏭️ Skip"], ["❌ Cancel"]]
    await message.reply_text(
        "⚖️ *Log Your Weight*\n\nEnter your weight in kg (e.g., 75.5):",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
        parse_mode="Markdown"
    )
    logger.info(f"[WEIGHT_MSG_SENT] Sent to chat_id: {message.chat_id}")
    
    return WEIGHT_VALUE

async def get_weight_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process weight input"""
    user = update.message.from_user
    text = update.message.text
    
    if text == "⏭️ Skip":
        await update.message.reply_text(
            "⏭️ Skipped weight logging.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END
    
    if text == "❌ Cancel":
        await update.message.reply_text(
            "❌ Cancelled.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END
    
    try:
        weight = float(text)
        if weight < 30 or weight > 300:
            await update.message.reply_text(
                "❌ Invalid weight. Please enter a value between 30-300 kg."
            )
            return WEIGHT_VALUE

        # Get yesterday's weight for comparison
        from src.database.activity_operations import get_yesterday_weight
        yesterday_weight = get_yesterday_weight(user.id)
        # Normalize Decimal -> float to avoid TypeError when mixing types
        try:
            from decimal import Decimal
            if isinstance(yesterday_weight, Decimal):
                yesterday_weight = float(yesterday_weight)
        except Exception:
            # If decimal import fails or conversion fails, leave as-is and rely on later checks
            pass

        # If in edit mode, just update weight, then clear the flag
        if context.user_data.get('weight_edit_mode'):
            context.user_data.pop('weight_edit_mode', None)
            logger.info(f"[WEIGHT_EDIT] User {user.id} is editing weight to {weight}")
            try:
                result = log_weight(user.id, weight)
            except Exception as e:
                logger.error(f"[WEIGHT_EDIT_ERROR] DB error for user {user.id}: {e}", exc_info=True)
                await update.message.reply_text(
                    "❌ An error occurred while updating your weight. Please try again later or contact admin."
                )
                return WEIGHT_VALUE
        else:
            try:
                result = log_weight(user.id, weight)
            except Exception as e:
                logger.error(f"[WEIGHT_LOG_ERROR] DB error for user {user.id}: {e}", exc_info=True)
                await update.message.reply_text(
                    "❌ An error occurred while logging your weight. Please try again later or contact admin."
                )
                return WEIGHT_VALUE

        if result:
            message_text = f"✅ *Weight Logged Successfully!*\n\n"
            message_text += f"📊 Today's Weight: {weight} kg\n"

            if yesterday_weight:
                diff = weight - yesterday_weight
                if diff > 0:
                    message_text += f"📈 Weight Gain: +{abs(diff):.2f} kg from yesterday ({yesterday_weight} kg)\n"
                elif diff < 0:
                    message_text += f"📉 Weight Loss: -{abs(diff):.2f} kg from yesterday ({yesterday_weight} kg)\n"
                else:
                    message_text += f"➡️ No change from yesterday ({yesterday_weight} kg)\n"
            else:
                message_text += f"ℹ️ No previous weight data to compare\n"

            message_text += f"💰 Points Awarded: +10\n"
            message_text += f"📈 Keep tracking your progress! 💪"

            # Mark success in user_data to avoid sending duplicate error messages
            context.user_data['weight_success_sent'] = True
            try:
                await update.message.reply_text(
                    message_text,
                    reply_markup=ReplyKeyboardRemove(),
                    parse_mode="Markdown"
                )
            finally:
                # remove the flag after sending (no longer needed)
                context.user_data.pop('weight_success_sent', None)
        else:
            logger.error(f"[WEIGHT_LOG_FAIL] log_weight returned None for user {user.id}, weight: {weight}")
            await update.message.reply_text(
                "❌ Failed to log weight. Try again."
            )
            return WEIGHT_VALUE

    except ValueError:
        logger.warning(f"[WEIGHT_INPUT_ERROR] User {user.id} sent invalid input for weight: '{text}'. State: WEIGHT_VALUE")
        await update.message.reply_text(
            "❌ Invalid input for weight. Please enter a number (e.g., 75.5). If you see a message about 'number 1-5', please report this to admin."
        )
        return WEIGHT_VALUE
    except Exception as e:
        logger.error(f"[WEIGHT_INPUT_FATAL] Unexpected error for user {user.id}: {e}", exc_info=True)
        # If we already sent success to this user in this flow, skip sending the generic error
        if context.user_data.get('weight_success_sent'):
            logger.info(f"[WEIGHT_INPUT_FATAL] Suppressing error message because success was already sent to user {user.id}")
            context.user_data.pop('weight_success_sent', None)
            return ConversationHandler.END
        await update.message.reply_text(
            "❌ An unexpected error occurred. Please try again later or contact admin."
        )
        return WEIGHT_VALUE

    return ConversationHandler.END

async def cmd_water(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start water intake logging"""
    # Check access gate first
    if not await check_app_feature_access(update, context):
        return ConversationHandler.END

    # Check if approved first
    if not await check_approval(update, context):
        return ConversationHandler.END
    
    # Check cutoff time
    allowed, cutoff_message = enforce_cutoff_check("water logging")
    if not allowed:
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.message.reply_text(cutoff_message)
        else:
            await update.message.reply_text(cutoff_message)
        return ConversationHandler.END
    
    # Handle both command and callback contexts
    if update.callback_query:
        await update.callback_query.answer()
        user = update.callback_query.from_user
        message = update.callback_query.message
    else:
        user = update.message.from_user
        message = update.message
    
    logger.info(f"User {user.id} started water logging - Chat ID: {message.chat_id}")
    
    reply_keyboard = [["1", "2", "3"], ["4", "5"], ["❌ Cancel"]]
    await message.reply_text(
        "💧 *Log Water Intake*\n\nHow many 500ml cups did you drink?",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
        parse_mode="Markdown"
    )
    logger.info(f"[WATER_MSG_SENT] Sent to chat_id: {message.chat_id}")
    
    return WATER_CUPS

async def get_water(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process water intake input"""
    user = update.message.from_user
    text = update.message.text
    
    if text == "❌ Cancel":
        await update.message.reply_text(
            "❌ Cancelled.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END
    
    try:
        cups = int(text)
        if cups < 1 or cups > 20:
            raise ValueError
        
        result = log_water(user.id, cups)
        
        if result:
            points = cups * 5  # 5 points per cup
            total_cups_today = result['water_cups']
            total_ml_today = total_cups_today * 500
            await update.message.reply_text(
                f"✅ *Water Intake Logged Successfully!*\n\n"
                f"💧 Cups Logged: {cups} x 500ml = {cups * 500}ml\n"
                f"📊 Today's Total: {total_cups_today} cups = {total_ml_today}ml\n"
                f"💰 Points Awarded: +{points}\n"
                f"💡 Hydration tip: Keep it up! 💪",
                reply_markup=ReplyKeyboardRemove(),
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                "❌ Failed to log water. Try again."
            )
            return WATER_CUPS
            
    except (ValueError, TypeError):
        await update.message.reply_text(
            "❌ Invalid input. Please select a number 1-5."
        )
        return WATER_CUPS
    
    return ConversationHandler.END

async def cmd_meal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start meal photo logging"""
    # Check access gate first
    if not await check_app_feature_access(update, context):
        return ConversationHandler.END

    # Check if approved first
    if not await check_approval(update, context):
        return ConversationHandler.END
    
    # Check cutoff time
    allowed, cutoff_message = enforce_cutoff_check("meal logging")
    if not allowed:
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.message.reply_text(cutoff_message)
        else:
            await update.message.reply_text(cutoff_message)
        return ConversationHandler.END
    
    # Handle both command and callback contexts
    if update.callback_query:
        await update.callback_query.answer()
        user = update.callback_query.from_user
        message = update.callback_query.message
    else:
        user = update.message.from_user
        message = update.message
    
    logger.info(f"User {user.id} started meal photo logging")
    
    today_log = get_today_log(user.id)
    meals_logged = today_log['meals_logged'] if today_log else 0
    
    if meals_logged >= 4:
        await message.reply_text(
            f"🍽️ *Meal Photos*\n\nYou've already logged 4 meals today! ✅"
        )
        return ConversationHandler.END
    
    await message.reply_text(
        f"🍽️ *Log Meal Photo*\n\nMeals logged today: {meals_logged}/4\n\n"
        f"Send a photo of your meal (or /cancel to skip):",
        parse_mode="Markdown"
    )
    
    return MEAL_PHOTO

async def get_meal_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process meal photo"""
    user = update.message.from_user
    
    if update.message.photo:
        # Save photo file_id
        photo = update.message.photo[-1]
        
        result = log_meal(user.id)
        
        if result:
            today_log = get_today_log(user.id)
            meals_logged = today_log['meals_logged'] if today_log else 0
            
            await update.message.reply_text(
                f"✅ *Meal Photo Logged Successfully!*\n\n"
                f"🍽️ Meals Logged Today: {meals_logged}/4\n"
                f"💰 Points Awarded: +15\n"
                f"📍 Goal Progress: {meals_logged}/4 meals for bonus! 🎯",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                "❌ Failed to log meal. Try again."
            )
            return MEAL_PHOTO
    else:
        await update.message.reply_text(
            "❌ Please send a photo of your meal."
        )
        return MEAL_PHOTO
    
    return ConversationHandler.END

async def cmd_habits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start habit completion logging with interactive buttons"""
    # Check access gate first
    if not await check_app_feature_access(update, context):
        return ConversationHandler.END

    # Check if approved first
    if not await check_approval(update, context):
        return ConversationHandler.END
    
    # Check cutoff time
    allowed, cutoff_message = enforce_cutoff_check("habit tracking")
    if not allowed:
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.message.reply_text(cutoff_message)
        else:
            await update.message.reply_text(cutoff_message)
        return ConversationHandler.END
    
    # Handle both command and callback contexts
    if update.callback_query:
        await update.callback_query.answer()
        user = update.callback_query.from_user
        message = update.callback_query.message
    else:
        user = update.message.from_user
        message = update.message
    
    logger.info(f"User {user.id} starting habit completion")
    
    # Initialize habit state in context
    if 'habits' not in context.user_data:
        context.user_data['habits'] = {
            'morning_shake': False,
            'exercise': False,
            'water': False,
            'second_shake': False,
            'healthy_dinner': False,
            'sleep': False,
            'no_junk': False,
            'no_smoking': False,
        }
    
    # Build habit buttons with checkmarks
    keyboard = _build_habits_keyboard(context.user_data['habits'])
    
    await message.reply_text(
        "💪 *Daily Habits*\n\nWhich habits did you complete today?\n"
        "Tap to toggle ✓ or ○",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    
    return HABITS_CONFIRM


def _build_habits_keyboard(habits_state):
    """Build habit buttons with visual checkmarks"""
    habits = [
        ('morning_shake', '🥤 Morning Shake'),
        ('exercise', '💪 Exercise'),
        ('water', '💧 Enough Water'),
        ('second_shake', '🥤 2nd Shake'),
        ('healthy_dinner', '🍽️ Healthy Dinner'),
        ('sleep', '😴 Good Sleep'),
        ('no_junk', '🚫 No Junk Food'),
        ('no_smoking', '🚭 No Smoking'),
    ]
    
    buttons = []
    for habit_key, habit_label in habits:
        is_done = habits_state.get(habit_key, False)
        checkmark = "✓" if is_done else "○"
        button_text = f"{habit_label} ({checkmark})"
        buttons.append([InlineKeyboardButton(button_text, callback_data=f"habit_toggle_{habit_key}")])
    
    # Add Submit button
    buttons.append([InlineKeyboardButton("📤 Submit & Continue", callback_data="habit_submit")])
    
    return InlineKeyboardMarkup(buttons)


async def get_habits_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle habit button toggling"""
    query = update.callback_query
    
    if not query:
        return HABITS_CONFIRM
    
    await query.answer()
    
    if query.data == "habit_submit":
        # Submit habits and calculate wellness score
        habits = context.user_data.get('habits', {})
        completed_count = sum(1 for v in habits.values() if v)
        
        result = log_habits(update.effective_user.id)
        
        if result:
            score = completed_count  # Wellness score = number of habits completed
            await query.edit_message_text(
                f"✅ *Habits Submission Complete!*\n\n"
                f"💪 Habits Completed: {completed_count}/8\n"
                f"⭐ Wellness Score: {score}\n"
                f"💰 Points Awarded: +{completed_count * 5}\n"
                f"🔥 Great effort! Keep the momentum going! 🎉",
                parse_mode="Markdown"
            )
            context.user_data.pop('habits', None)
            return ConversationHandler.END
        else:
            await query.edit_message_text("❌ Failed to submit. Try again.")
            return HABITS_CONFIRM
    
    elif query.data.startswith("habit_toggle_"):
        habit_key = query.data.replace("habit_toggle_", "")
        if habit_key in context.user_data['habits']:
            context.user_data['habits'][habit_key] = not context.user_data['habits'][habit_key]
        
        # Refresh keyboard with updated state
        keyboard = _build_habits_keyboard(context.user_data['habits'])
        await query.edit_message_reply_markup(reply_markup=keyboard)
    
    return HABITS_CONFIRM


async def cmd_checkin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start check-in process"""
    # Check access gate first
    if not await check_app_feature_access(update, context):
        return ConversationHandler.END

    # Check if approved first
    if not await check_approval(update, context):
        return ConversationHandler.END
    
    # Check cutoff time
    allowed, cutoff_message = enforce_cutoff_check("gym check-in")
    if not allowed:
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.message.reply_text(cutoff_message)
        else:
            await update.message.reply_text(cutoff_message)
        return ConversationHandler.END
    
    # Handle both command and callback contexts
    if update.callback_query:
        await update.callback_query.answer()
        user = update.callback_query.from_user
        message = update.callback_query.message
    else:
        user = update.message.from_user
        message = update.message
    
    logger.info(f"User {user.id} started check-in")
    
    # Check if already checked in today
    existing = get_user_attendance_today(user.id)
    if existing:
        status_text = "✅ Already approved" if existing['status'] == 'approved' else "⏳ Pending approval"
        await message.reply_text(
            f"🏋️ *Check In*\n\n{status_text} for today."
        )
        return ConversationHandler.END
    
    reply_keyboard = [["📸 Upload Photo", "📝 Text Check-in"], ["❌ Cancel"]]
    await message.reply_text(
        "🏋️ *Check In to the Gym*\n\nHow would you like to check in?",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
        parse_mode="Markdown"
    )
    
    return CHECKIN_METHOD


async def get_checkin_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process check-in method selection"""
    user = update.message.from_user
    text = update.message.text
    
    if text == "❌ Cancel":
        await update.message.reply_text(
            "❌ Check-in cancelled.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END
    
    if text == "📸 Upload Photo":
        context.user_data['checkin_method'] = 'photo'
        await update.message.reply_text(
            "📸 Send a gym selfie or equipment photo:",
            reply_markup=ReplyKeyboardRemove()
        )
        return CHECKIN_PHOTO
    elif text == "📝 Text Check-in":
        result = create_attendance_request(user.id)
        if result:
            await update.message.reply_text(
                "✅ *Check In Submitted*\n\nAwait admin approval. You'll get 50 points once approved! 🎉",
                reply_markup=ReplyKeyboardRemove(),
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                "❌ Failed to create check-in. Try again."
            )
            return CHECKIN_METHOD
        return ConversationHandler.END
    
    return CHECKIN_METHOD


async def get_checkin_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process check-in photo"""
    user = update.message.from_user
    
    if update.message.photo:
        photo = update.message.photo[-1]
        photo_url = f"https://t.me/c/{photo.file_id}"
        
        result = create_attendance_request(user.id, photo_url)
        
        if result:
            await update.message.reply_text(
                "✅ *Check In Submitted*\n\nAwait admin approval. You'll get 50 points once approved! 🎉",
                reply_markup=ReplyKeyboardRemove(),
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                "❌ Failed to create check-in. Try again."
            )
            return CHECKIN_PHOTO
    else:
        await update.message.reply_text(
            "❌ Please send a photo."
        )
        return CHECKIN_PHOTO
    
    return ConversationHandler.END


async def cancel_activity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel activity logging"""
    await update.message.reply_text(
        "❌ Cancelled.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END
