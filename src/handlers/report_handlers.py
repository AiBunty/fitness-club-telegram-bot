"""
Admin report command handlers
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from src.utils.report_generator import (
    generate_active_members_report,
    generate_inactive_members_report,
    generate_expiring_soon_report,
    generate_daily_activity_report,
    generate_top_performers_report,
    generate_inactive_users_report,
    generate_membership_overview_report,
    generate_eod_report,
    export_members_to_csv
)
from src.database.reports_operations import (
    get_active_members,
    get_inactive_members,
    move_expired_to_inactive
)

logger = logging.getLogger(__name__)


async def cmd_reports_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Show admin reports menu
    """
    if update.callback_query:
        await update.callback_query.answer()
        message = update.callback_query.message
    else:
        message = update.message
    
    keyboard = [
        [InlineKeyboardButton("📊 Membership Overview", callback_data="report_overview")],
        [InlineKeyboardButton("✅ Active Members", callback_data="report_active"),
         InlineKeyboardButton("❌ Inactive Members", callback_data="report_inactive")],
        [InlineKeyboardButton("⏰ Expiring Soon", callback_data="report_expiring")],
        [InlineKeyboardButton("📈 Today's Activity", callback_data="report_today")],
        [InlineKeyboardButton("🏆 Top Performers (7d)", callback_data="report_top_performers")],
        [InlineKeyboardButton("😴 Inactive Users (7d)", callback_data="report_inactive_users")],
        [InlineKeyboardButton("🌙 EOD Report", callback_data="report_eod")],
        [InlineKeyboardButton("📥 Export Full Lists", callback_data="report_export")],
        [InlineKeyboardButton("🔄 Move Expired to Inactive", callback_data="report_move_expired")],
        [InlineKeyboardButton("❌ Close", callback_data="close")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = "📊 *Admin Reports Menu*\n\nSelect a report to view:"
    
    if update.callback_query:
        await message.edit_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")


async def callback_report_overview(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show membership overview"""
    query = update.callback_query
    await query.answer()
    
    report = generate_membership_overview_report()
    
    keyboard = [[InlineKeyboardButton("📱 Back to Reports", callback_data="cmd_reports_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(report, reply_markup=reply_markup, parse_mode="Markdown")


async def callback_report_active(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show active members report with expiry details"""
    query = update.callback_query
    await query.answer("Generating report...")
    
    report = generate_active_members_report(limit=20)
    
    keyboard = [
        [InlineKeyboardButton("📥 Export Full List", callback_data="export_active")],
        [InlineKeyboardButton("📱 Back to Reports", callback_data="cmd_reports_menu"),
         InlineKeyboardButton("❌ Close", callback_data="close")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(report, reply_markup=reply_markup, parse_mode="Markdown")


async def callback_report_inactive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show inactive members report"""
    query = update.callback_query
    await query.answer("Generating report...")
    
    report = generate_inactive_members_report(limit=20)
    
    keyboard = [
        [InlineKeyboardButton("📥 Export Full List", callback_data="export_inactive")],
        [InlineKeyboardButton("📱 Back to Reports", callback_data="cmd_reports_menu"),
         InlineKeyboardButton("❌ Close", callback_data="close")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(report, reply_markup=reply_markup, parse_mode="Markdown")


async def callback_report_expiring(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show expiring soon report"""
    query = update.callback_query
    await query.answer()
    
    report = generate_expiring_soon_report(days=7)
    
    keyboard = [[InlineKeyboardButton("📱 Back to Reports", callback_data="cmd_reports_menu"),
                 InlineKeyboardButton("❌ Close", callback_data="close")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(report, reply_markup=reply_markup, parse_mode="Markdown")


async def callback_report_today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show today's activity report"""
    query = update.callback_query
    await query.answer("Generating report...")
    
    report = generate_daily_activity_report()
    
    keyboard = [[InlineKeyboardButton("📱 Back to Reports", callback_data="cmd_reports_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Split report if too long
    if len(report) > 4000:
        parts = [report[i:i+4000] for i in range(0, len(report), 4000)]
        for i, part in enumerate(parts):
            if i == len(parts) - 1:
                await query.message.reply_text(part, reply_markup=reply_markup, parse_mode="Markdown")
            else:
                await query.message.reply_text(part, parse_mode="Markdown")
        await query.delete_message()
    else:
        await query.edit_message_text(report, reply_markup=reply_markup, parse_mode="Markdown")


async def callback_report_top_performers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show top performers report"""
    query = update.callback_query
    await query.answer()
    
    report = generate_top_performers_report(days=7)
    
    keyboard = [[InlineKeyboardButton("📱 Back to Reports", callback_data="cmd_reports_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(report, reply_markup=reply_markup, parse_mode="Markdown")


async def callback_report_inactive_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show inactive users report"""
    query = update.callback_query
    await query.answer()
    
    report = generate_inactive_users_report(days=7)
    
    keyboard = [[InlineKeyboardButton("📱 Back to Reports", callback_data="cmd_reports_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(report, reply_markup=reply_markup, parse_mode="Markdown")


async def callback_report_eod(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show End of Day report"""
    query = update.callback_query
    await query.answer("Generating EOD report...")
    
    report = generate_eod_report()
    
    keyboard = [[InlineKeyboardButton("📱 Back to Reports", callback_data="cmd_reports_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Split report if too long
    if len(report) > 4000:
        parts = [report[i:i+4000] for i in range(0, len(report), 4000)]
        for i, part in enumerate(parts):
            if i == len(parts) - 1:
                await query.message.reply_text(part, reply_markup=reply_markup, parse_mode="Markdown")
            else:
                await query.message.reply_text(part, parse_mode="Markdown")
        await query.delete_message()
    else:
        await query.edit_message_text(report, reply_markup=reply_markup, parse_mode="Markdown")


async def callback_export_active(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Export active members to CSV"""
    query = update.callback_query
    await query.answer("Exporting...")
    
    members = get_active_members()
    csv_file = export_members_to_csv(members, "active_members.csv")
    
    await query.message.reply_document(
        document=csv_file,
        filename="active_members.csv",
        caption=f"📊 Active Members Export\nTotal: {len(members)} members"
    )
    
    await query.answer("Export complete!")


async def callback_export_inactive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Export inactive members to CSV"""
    query = update.callback_query
    await query.answer("Exporting...")
    
    members = get_inactive_members()
    csv_file = export_members_to_csv(members, "inactive_members.csv")
    
    await query.message.reply_document(
        document=csv_file,
        filename="inactive_members.csv",
        caption=f"📊 Inactive Members Export\nTotal: {len(members)} members"
    )
    
    await query.answer("Export complete!")


async def callback_report_export(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show export options"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("📥 Export Active Members", callback_data="export_active")],
        [InlineKeyboardButton("📥 Export Inactive Members", callback_data="export_inactive")],
        [InlineKeyboardButton("📱 Back to Reports", callback_data="cmd_reports_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = "📥 *Export Member Lists*\n\nSelect list to export as CSV:"
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")


async def callback_move_expired(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Move expired members to inactive status"""
    query = update.callback_query
    await query.answer("Processing...")
    
    count = move_expired_to_inactive()
    
    keyboard = [[InlineKeyboardButton("📱 Back to Reports", callback_data="cmd_reports_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = f"✅ *Expiry Check Complete*\n\n"
    text += f"Moved {count} members to inactive status.\n"
    text += f"(Members with fees expired 7+ days ago)\n\n"
    text += f"_These members can be re-activated when they pay fees._"
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
