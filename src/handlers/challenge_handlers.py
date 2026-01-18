import logging
from datetime import datetime, date
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ChatAction
from src.database.challenges_operations import (
    get_active_challenges, get_user_challenges, get_challenge_progress,
    get_challenge_leaderboard, join_challenge, get_challenge_stats,
    CHALLENGE_TYPES, get_challenge_by_id, is_user_in_challenge,
    get_challenge_participants, get_user_rank_in_challenge
)
from src.database.challenge_payment_operations import approve_challenge_participation
from src.database.motivational_operations import get_random_motivational_message
from src.database.user_operations import get_user_by_id
from src.database.notifications_operations import send_challenge_reminder
from src.utils.guards import check_approval
from src.utils.cutoff_enforcement import get_challenge_start_cutoff_message
from src.utils.challenge_points import get_challenge_points_summary

logger = logging.getLogger(__name__)

async def cmd_challenges(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show active challenges"""
    user_id = update.effective_user.id
    
    # Handle both command and callback contexts
    if update.callback_query:
        await update.callback_query.answer()
        message = update.callback_query.message
    else:
        message = update.message
    
    challenges = get_active_challenges()
    user_challenges = get_user_challenges(user_id)
    user_challenge_ids = {c['challenge_id'] for c in user_challenges}
    
    if not challenges:
        await message.reply_text("🏆 No active challenges at the moment.")
        return
    
    keyboard = []
    for challenge in challenges:
        is_joined = challenge['challenge_id'] in user_challenge_ids
        prefix = "✅" if is_joined else "🏆"
        
        keyboard.append([
            InlineKeyboardButton(
                f"{prefix} {challenge['challenge_type']} ({'Joined' if is_joined else 'Join'})",
                callback_data=f"challenge_view_{challenge['challenge_id']}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("❌ Close", callback_data="challenge_close")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = "🏆 *Active Challenges*\n\n"
    text += f"Total: {len(challenges)}\n"
    text += f"Your Challenges: {len(user_challenges)}\n\n"
    text += "_Tap a challenge to view details_"
    
    await message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

async def callback_challenge_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View challenge details"""
    query = update.callback_query
    user_id = query.from_user.id
    
    challenge_id = int(query.data.split("_")[2])
    
    challenges = get_active_challenges()
    challenge = None
    for c in challenges:
        if c['challenge_id'] == challenge_id:
            challenge = c
            break
    
    if not challenge:
        await query.answer("❌ Challenge not found.", show_alert=True)
        return
    
    # Get user's progress if they're in the challenge
    user_challenges = get_user_challenges(user_id)
    is_joined = any(c['challenge_id'] == challenge_id for c in user_challenges)
    
    progress = None
    if is_joined:
        progress = get_challenge_progress(challenge_id, user_id)
    
    message = f"🏆 *{challenge['challenge_type']}*\n\n"
    message += f"Duration: {challenge['duration_days']} days\n"
    message += f"Status: {'✅ ACTIVE' if challenge['is_active'] else '❌ ENDED'}\n"
    
    if progress:
        message += f"\nYour Progress: {progress['progress_value'] or 0}\n"
    
    keyboard = []
    
    if is_joined:
        keyboard.append([
            InlineKeyboardButton("📊 Leaderboard", callback_data=f"challenge_board_{challenge_id}"),
            InlineKeyboardButton("📈 My Progress", callback_data=f"challenge_progress_{challenge_id}")
        ])
    else:
        keyboard.append([
            InlineKeyboardButton("✅ Join Challenge", callback_data=f"challenge_join_{challenge_id}")
        ])
    
    keyboard.append([InlineKeyboardButton("📱 Back", callback_data="challenge_back")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=message,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def callback_challenge_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Join a challenge"""
    query = update.callback_query
    user_id = query.from_user.id
    
    challenge_id = int(query.data.split("_")[2])
    
    result = join_challenge(user_id, challenge_id)
    
    if result:
        await query.answer("✅ Challenge joined!", show_alert=False)
        
        progress = get_challenge_progress(challenge_id, user_id)
        
        message = f"✅ *Challenge Joined!*\n\n"
        message += f"Challenge: {progress['challenge_type']}\n"
        message += f"Your Progress: {progress['progress_value'] or 0}\n"
        message += f"Status: ACTIVE\n\n"
        message += "_Good luck! 🍀_"
        
        keyboard = [
            [InlineKeyboardButton("🏆 Leaderboard", callback_data=f"challenge_board_{challenge_id}")],
            [InlineKeyboardButton("📱 Back", callback_data="challenge_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text=message,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    else:
        await query.answer("❌ Already in this challenge or error occurred.", show_alert=True)

async def callback_challenge_progress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's challenge progress"""
    query = update.callback_query
    user_id = query.from_user.id
    
    challenge_id = int(query.data.split("_")[2])
    
    progress = get_challenge_progress(challenge_id, user_id)
    
    if not progress:
        await query.answer("❌ Progress not found.", show_alert=True)
        return
    
    message = f"📈 *Your Challenge Progress*\n\n"
    message += f"Challenge: {progress['challenge_type']}\n"
    message += f"Current Progress: {progress['progress_value'] or 0}\n"
    message += f"Status: ACTIVE\n\n"
    
    # Type-specific messages
    if progress['challenge_type'] == 'weight_loss':
        message += "_Track your weight in profile settings_"
    elif progress['challenge_type'] == 'consistency':
        message += "_Log activities daily to build your streak_"
    elif progress['challenge_type'] == 'water_challenge':
        message += "_Log water intake in daily logs_"
    elif progress['challenge_type'] == 'gym_warrior':
        message += "_Log gym visits to increase your count_"
    elif progress['challenge_type'] == 'meal_prep':
        message += "_Log meal preparations daily_"
    
    keyboard = [
        [InlineKeyboardButton("🏆 Leaderboard", callback_data=f"challenge_board_{challenge_id}")],
        [InlineKeyboardButton("📱 Back", callback_data="challenge_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=message,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def callback_challenge_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show challenge leaderboard"""
    query = update.callback_query
    
    challenge_id = int(query.data.split("_")[2])
    
    leaderboard = get_challenge_leaderboard(challenge_id, limit=10)
    
    message = "🏆 *Challenge Leaderboard*\n\n"
    
    medals = ["🥇", "🥈", "🥉"]
    
    if leaderboard:
        for i, member in enumerate(leaderboard, 1):
            medal = medals[i-1] if i <= 3 else f"{i}."
            progress = member.get('progress_value', 0) or 0
            message += f"{medal} {member['full_name']}: {progress}\n"
    else:
        message += "_No participants yet_"
    
    keyboard = [
        [InlineKeyboardButton("📱 Back", callback_data="challenge_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=message,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def callback_challenge_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Go back to challenges list"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    challenges = get_active_challenges()
    user_challenges = get_user_challenges(user_id)
    user_challenge_ids = {c['challenge_id'] for c in user_challenges}
    
    keyboard = []
    for challenge in challenges:
        is_joined = challenge['challenge_id'] in user_challenge_ids
        prefix = "✅" if is_joined else "🏆"
        
        keyboard.append([
            InlineKeyboardButton(
                f"{prefix} {challenge['challenge_type']}",
                callback_data=f"challenge_view_{challenge['challenge_id']}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("❌ Close", callback_data="challenge_close")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = "🏆 *Active Challenges*\n\n"
    message += f"Total: {len(challenges)}\n"
    message += f"Your Challenges: {len(user_challenges)}\n\n"
    
    await query.edit_message_text(
        text=message,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def callback_challenge_close(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Close challenges"""
    query = update.callback_query
    await query.answer()
    await query.delete_message()

async def cmd_my_challenges(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's challenges"""
    # Check if approved first
    if not await check_approval(update, context):
        return
    
    user_id = update.effective_user.id
    
    challenges = get_user_challenges(user_id)
    
    if not challenges:
        await update.message.reply_text("🏆 You're not in any challenges yet.\n\nUse /challenges to join one!")
        return
    
    keyboard = []
    for challenge in challenges:
        keyboard.append([
            InlineKeyboardButton(
                f"🏆 {challenge['challenge_type']}",
                callback_data=f"challenge_view_{challenge['challenge_id']}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("❌ Close", callback_data="challenge_close")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = f"🏆 *My Challenges* ({len(challenges)})\n\n"
    
    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode="Markdown")

def register_challenge_callbacks(application):
    """Register all challenge-related callback handlers"""
    from telegram.ext import CallbackQueryHandler
    
    application.add_handler(CallbackQueryHandler(
        callback_challenge_view,
        pattern="^view_challenge_"
    ))
    application.add_handler(CallbackQueryHandler(
        callback_challenge_join,
        pattern="^join_challenge_"
    ))
    application.add_handler(CallbackQueryHandler(
        callback_challenge_progress,
        pattern="^challenge_progress_"
    ))
    application.add_handler(CallbackQueryHandler(
        callback_challenge_leaderboard,
        pattern="^challenge_board_"
    ))
    application.add_handler(CallbackQueryHandler(
        callback_challenge_back,
        pattern="^challenge_back$"
    ))
    application.add_handler(CallbackQueryHandler(
        callback_challenge_close,
        pattern="^challenge_close$"
    ))

