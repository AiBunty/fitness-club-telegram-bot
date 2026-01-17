import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from src.database.payment_operations import (
    get_revenue_stats, get_monthly_revenue, get_active_members_count,
    get_pending_payments
)
from src.database.statistics_operations import (
    get_platform_statistics, get_engagement_metrics, get_top_activities
)
from src.database.challenges_operations import get_challenge_stats
from src.utils.auth import is_admin

logger = logging.getLogger(__name__)

async def cmd_admin_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show admin dashboard"""
    # Handle both command and callback contexts
    if update.callback_query:
        await update.callback_query.answer()
        message = update.callback_query.message
    else:
        message = update.message
    
    # is_admin is a synchronous function, don't await it
    if not is_admin(update.effective_user.id):
        await message.reply_text("❌ Admin access only.")
        return
    
    keyboard = [
        [InlineKeyboardButton("💰 Revenue Stats", callback_data="dashboard_revenue"),
         InlineKeyboardButton("👥 Member Stats", callback_data="dashboard_members")],
        [InlineKeyboardButton("📊 Engagement", callback_data="dashboard_engagement"),
         InlineKeyboardButton("🏆 Challenges", callback_data="dashboard_challenges")],
        [InlineKeyboardButton("🔥 Top Activities", callback_data="dashboard_activities")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await message.reply_text(
        "📊 *Admin Dashboard*\n\nSelect a report to view:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def callback_revenue_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show revenue statistics"""
    query = update.callback_query
    
    if not is_admin(query.from_user.id):
        await query.answer("❌ Admin access only.", show_alert=True)
        return
    
    await query.answer()
    
    revenue = get_revenue_stats()
    monthly = get_monthly_revenue()
    
    message = "💰 *Revenue Statistics*\n\n"
    message += f"Total Revenue: ₹{revenue['total_revenue'] or 0:,.2f}\n"
    message += f"Total Payments: {revenue['total_payments']}\n"
    message += f"Avg Payment: ₹{revenue['avg_payment'] or 0:,.2f}\n"
    message += f"Unique Payers: {revenue['unique_payers']}\n\n"
    
    message += "📅 *This Month*\n"
    message += f"Monthly Revenue: ₹{monthly['monthly_revenue'] or 0:,.2f}\n"
    message += f"Transactions: {monthly['transaction_count']}\n"
    message += f"Payers: {monthly['payers']}\n"
    
    keyboard = [[InlineKeyboardButton("📊 Back to Dashboard", callback_data="admin_dashboard")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=message,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def callback_member_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show member statistics"""
    query = update.callback_query
    
    if not is_admin(query.from_user.id):
        await query.answer("❌ Admin access only.", show_alert=True)
        return
    
    await query.answer()
    
    stats = get_platform_statistics()
    active = get_active_members_count()
    pending = get_pending_payments()
    
    message = "👥 *Member Statistics*\n\n"
    message += f"Total Users: {stats['total_users']}\n"
    message += f"Active Members: {stats['active_members']}\n"
    message += f"Average Points: {int(stats['avg_points'] or 0)}\n"
    message += f"Pending Payments: {len(pending) if pending else 0}\n\n"
    
    message += "📈 *Today's Activity*\n"
    message += f"Active Users: {stats['today_users']}\n"
    message += f"Activities Logged: {stats['today_activities']}\n"
    
    keyboard = [[InlineKeyboardButton("📊 Back to Dashboard", callback_data="admin_dashboard")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=message,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def callback_engagement_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show engagement statistics"""
    query = update.callback_query
    
    if not is_admin(query.from_user.id):
        await query.answer("❌ Admin access only.", show_alert=True)
        return
    
    await query.answer()
    
    engagement = get_engagement_metrics()
    
    message = "📊 *Engagement Metrics* (Last 30 days)\n\n"
    message += f"Active Users: {engagement['active_users']}\n"
    message += f"Paid Members: {engagement['paid_members']}\n"
    message += f"Total Points: {int(engagement['total_points_awarded'] or 0):,}\n"
    message += f"Activities: {engagement['total_transactions']}\n"
    message += f"Avg Points/Activity: {int(engagement['avg_points_per_activity'] or 0)}\n"
    
    keyboard = [[InlineKeyboardButton("📊 Back to Dashboard", callback_data="admin_dashboard")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=message,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def callback_challenge_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show challenge statistics"""
    query = update.callback_query
    
    if not is_admin(query.from_user.id):
        await query.answer("❌ Admin access only.", show_alert=True)
        return
    
    await query.answer()
    
    stats = get_challenge_stats()
    
    message = "🏆 *Challenge Statistics*\n\n"
    message += f"Total Challenges: {stats['total_challenges']}\n"
    message += f"Active Challenges: {stats['active_challenges']}\n"
    message += f"Completed: {stats['completed_challenges']}\n\n"
    
    message += "👥 *Participation*\n"
    message += f"Active Participants: {stats['active_participants']}\n"
    message += f"Users Completed: {stats['users_completed']}\n"
    
    keyboard = [[InlineKeyboardButton("📊 Back to Dashboard", callback_data="admin_dashboard")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=message,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def callback_top_activities(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show top activities"""
    query = update.callback_query
    
    if not is_admin(query.from_user.id):
        await query.answer("❌ Admin access only.", show_alert=True)
        return
    
    await query.answer()
    
    activities = get_top_activities()
    
    message = "🔥 *Top Activities* (Last 30 days)\n\n"
    
    if activities:
        for i, activity in enumerate(activities[:5], 1):
            message += f"{i}. {activity['activity']}\n"
            message += f"   • Count: {activity['frequency']}\n"
            message += f"   • Points: {int(activity['total_points'] or 0)}\n\n"
    
    keyboard = [[InlineKeyboardButton("📊 Back to Dashboard", callback_data="admin_dashboard")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=message,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def callback_admin_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Return to admin dashboard"""
    query = update.callback_query
    
    if not is_admin(query.from_user.id):
        await query.answer("❌ Admin access only.", show_alert=True)
        return
    
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("💰 Revenue Stats", callback_data="dashboard_revenue"),
         InlineKeyboardButton("👥 Member Stats", callback_data="dashboard_members")],
        [InlineKeyboardButton("📊 Engagement", callback_data="dashboard_engagement"),
         InlineKeyboardButton("🏆 Challenges", callback_data="dashboard_challenges")],
        [InlineKeyboardButton("🔥 Top Activities", callback_data="dashboard_activities")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text="📊 *Admin Dashboard*\n\nSelect a report to view:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

# Callback router for analytics
async def handle_analytics_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Route analytics callbacks"""
    query = update.callback_query
    
    if query.data == "dashboard_revenue":
        await callback_revenue_stats(update, context)
    elif query.data == "dashboard_members":
        await callback_member_stats(update, context)
    elif query.data == "dashboard_engagement":
        await callback_engagement_stats(update, context)
    elif query.data == "dashboard_challenges":
        await callback_challenge_stats(update, context)
    elif query.data == "dashboard_activities":
        await callback_top_activities(update, context)
    elif query.data == "admin_dashboard":
        await callback_admin_dashboard(update, context)
