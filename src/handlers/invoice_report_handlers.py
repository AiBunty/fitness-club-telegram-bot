"""
Invoice Report Handler Module
Manages invoice report generation and delivery for admin users
Supports Monthly, Quarterly, 6-Month, Yearly, and Custom date range reports
"""

from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ConversationHandler, 
    CallbackContext,
    CallbackQueryHandler,
    MessageHandler,
    filters
)
from telegram.constants import ChatAction

from src.database.invoice_reports import (
    get_monthly_invoices, get_monthly_summary,
    get_quarterly_invoices, get_quarterly_summary,
    get_six_month_invoices, get_six_month_summary,
    get_yearly_invoices, get_yearly_summary,
    get_custom_date_range_invoices, get_custom_date_range_summary
)
from src.utils.invoice_excel_export import generate_invoice_report_excel


# Conversation states for custom date range
CUSTOM_DATE_INPUT = 1




async def cmd_invoice_reports(update: Update, context: CallbackContext):
    """
    Main invoice reports menu
    Provides options for Monthly, Quarterly, 6-Month, Yearly, and Custom reports
    """
    query = update.callback_query
    if query:
        await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("📅 Monthly", callback_data="invoice_monthly"),
         InlineKeyboardButton("📊 Quarterly", callback_data="invoice_quarterly")],
        [InlineKeyboardButton("📈 6 Months", callback_data="invoice_six_months"),
         InlineKeyboardButton("📉 Yearly", callback_data="invoice_yearly")],
        [InlineKeyboardButton("🗓️ Custom Date Range", callback_data="invoice_custom")],
        [InlineKeyboardButton("⬅️ Back to Dashboard", callback_data="cmd_admin_dashboard")],
        [InlineKeyboardButton("⬅️ Back to Admin Menu", callback_data="cmd_admin_back")],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = """
*📊 Invoice Reports*

Select a report period:

• *Monthly* - Current month invoices
• *Quarterly* - Select which quarter
• *6 Months* - First or second half of year
• *Yearly* - Full year invoices
• *Custom Date Range* - Enter specific dates

Format for custom dates: DD.MM.YYYY (e.g., 01.01.2026 to 31.01.2026)
    """
    
    if query:
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')


async def callback_invoice_report_monthly(update: Update, context: CallbackContext):
    """Handle monthly report generation"""
    query = update.callback_query
    await query.answer()
    
    # Show month selection
    now = datetime.now()
        keyboard = [
            [InlineKeyboardButton("⬅️ Back to Reports", callback_data="cmd_invoice_reports")],
            [InlineKeyboardButton("⬅️ Back to Admin Menu", callback_data="cmd_admin_back")],
        ]
    for i in range(12):
        d = datetime(now.year if i == 0 else now.year - 1, 
                     (now.month - i) if i < now.month else (12 + now.month - i), 1)
        month_name = d.strftime('%B %Y')
        callback = f"invoice_monthly_{d.year}_{d.month}"
        keyboard.append([InlineKeyboardButton(month_name, callback_data=callback)])
    
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="cmd_invoice_reports")])
    keyboard.append([InlineKeyboardButton("⬅️ Back to Admin Menu", callback_data="cmd_admin_back")])
    keyboard.append([InlineKeyboardButton("⬅️ Back to Admin Menu", callback_data="cmd_admin_back")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "📅 Select Month:",
        reply_markup=reply_markup
    )


async def callback_invoice_monthly_selected(update: Update, context: CallbackContext):
    """Generate monthly invoice report"""
    query = update.callback_query
    await query.answer()
    
    # Parse callback data: invoice_monthly_YYYY_MM
    parts = query.data.split('_')
    year = int(parts[2])
    month = int(parts[3])
    
    await query.edit_message_text("⏳ Generating monthly report...", reply_markup=None)
    
    from src.database.invoice_reports import get_monthly_invoices, get_monthly_summary
    
    try:
        invoices = get_monthly_invoices(year, month)
        summary = get_monthly_summary(year, month)
        
        month_name = datetime(year, month, 1).strftime('%B %Y')
        
        excel_buffer = generate_invoice_report_excel(invoices, summary, month_name)
        filename = f'Invoice_Report_{month_name.replace(" ", "_")}.xlsx'
        
        await context.bot.send_chat_action(update.effective_chat.id, ChatAction.UPLOAD_DOCUMENT)
        
        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=excel_buffer,
            filename=filename,
            caption=f"📊 Monthly Invoice Report - {month_name}\n\n"
                   f"Total Invoices: {summary['total_invoices']}\n"
                   f"Total Amount: ₹{summary['total_amount']:,.2f}\n"
                   f"Paid: ₹{summary['paid_amount']:,.2f}\n"
                   f"Pending: ₹{summary['pending_amount']:,.2f}"
        )
        
        # Show menu again
        await cmd_invoice_reports(update, context)
        
    except Exception as e:
        await query.edit_message_text(f"❌ Error generating report: {str(e)}")


async def callback_invoice_report_quarterly(update: Update, context: CallbackContext):
    """Handle quarterly report generation"""
    query = update.callback_query
    await query.answer()
    
    now = datetime.now()
    keyboard = []
    
    # Current and previous years, all 4 quarters
    for year_offset in range(2):
        year = now.year - year_offset
        for quarter in range(1, 5):
            quarter_name = f"Q{quarter} {year}"
            callback = f"invoice_quarterly_{year}_{quarter}"
            keyboard.append([InlineKeyboardButton(quarter_name, callback_data=callback)])
    
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="cmd_invoice_reports")])
    keyboard.append([InlineKeyboardButton("⬅️ Back to Admin Menu", callback_data="cmd_admin_back")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "📊 Select Quarter:",
        reply_markup=reply_markup
    )


async def callback_invoice_quarterly_selected(update: Update, context: CallbackContext):
    """Generate quarterly invoice report"""
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split('_')
    year = int(parts[2])
    quarter = int(parts[3])
    
    await query.edit_message_text("⏳ Generating quarterly report...", reply_markup=None)
    
    try:
        invoices = get_quarterly_invoices(year, quarter)
        summary = get_quarterly_summary(year, quarter)
        
        period_name = f"Q{quarter} {year}"
        
        excel_buffer = generate_invoice_report_excel(invoices, summary, period_name)
        filename = f'Invoice_Report_{period_name}.xlsx'
        
        await context.bot.send_chat_action(update.effective_chat.id, ChatAction.UPLOAD_DOCUMENT)
        
        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=excel_buffer,
            filename=filename,
            caption=f"📊 Quarterly Invoice Report - {period_name}\n\n"
                   f"Total Invoices: {summary['total_invoices']}\n"
                   f"Total Amount: ₹{summary['total_amount']:,.2f}\n"
                   f"Paid: ₹{summary['paid_amount']:,.2f}\n"
                   f"Pending: ₹{summary['pending_amount']:,.2f}"
        )
        
        await cmd_invoice_reports(update, context)
        
    except Exception as e:
        await query.edit_message_text(f"❌ Error generating report: {str(e)}")


async def callback_invoice_report_six_months(update: Update, context: CallbackContext):
    """Handle 6-month report generation"""
    query = update.callback_query
    await query.answer()
    
    now = datetime.now()
    current_half = 1 if now.month <= 6 else 2
    
    keyboard = []
    for year_offset in range(2):
        year = now.year - year_offset
        for half in range(1, 3):
            half_name = f"H{half} {year}"
            callback = f"invoice_six_months_{year}_{half}"
            keyboard.append([InlineKeyboardButton(half_name, callback_data=callback)])
    
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="cmd_invoice_reports")])
    keyboard.append([InlineKeyboardButton("⬅️ Back to Admin Menu", callback_data="cmd_admin_back")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "📈 Select 6-Month Period:",
        reply_markup=reply_markup
    )


async def callback_invoice_six_months_selected(update: Update, context: CallbackContext):
    """Generate 6-month invoice report"""
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split('_')
    year = int(parts[3])
    half = int(parts[4])
    
    await query.edit_message_text("⏳ Generating 6-month report...", reply_markup=None)
    
    try:
        invoices = get_six_month_invoices(year, half)
        summary = get_six_month_summary(year, half)
        
        period_name = f"H{half} {year}"
        
        excel_buffer = generate_invoice_report_excel(invoices, summary, period_name)
        filename = f'Invoice_Report_{period_name}.xlsx'
        
        await context.bot.send_chat_action(update.effective_chat.id, ChatAction.UPLOAD_DOCUMENT)
        
        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=excel_buffer,
            filename=filename,
            caption=f"📈 6-Month Invoice Report - {period_name}\n\n"
                   f"Total Invoices: {summary['total_invoices']}\n"
                   f"Total Amount: ₹{summary['total_amount']:,.2f}\n"
                   f"Paid: ₹{summary['paid_amount']:,.2f}\n"
                   f"Pending: ₹{summary['pending_amount']:,.2f}"
        )
        
        await cmd_invoice_reports(update, context)
        
    except Exception as e:
        await query.edit_message_text(f"❌ Error generating report: {str(e)}")


async def callback_invoice_report_yearly(update: Update, context: CallbackContext):
    """Handle yearly report generation"""
    query = update.callback_query
    await query.answer()
    
    now = datetime.now()
    keyboard = []
    
    for year_offset in range(3):
        year = now.year - year_offset
        callback = f"invoice_yearly_{year}"
        keyboard.append([InlineKeyboardButton(str(year), callback_data=callback)])
    
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="cmd_invoice_reports")])
    keyboard.append([InlineKeyboardButton("⬅️ Back to Admin Menu", callback_data="cmd_admin_back")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "📉 Select Year:",
        reply_markup=reply_markup
    )


async def callback_invoice_yearly_selected(update: Update, context: CallbackContext):
    """Generate yearly invoice report"""
    query = update.callback_query
    await query.answer()
    
    year = int(query.data.split('_')[2])
    
    await query.edit_message_text("⏳ Generating yearly report...", reply_markup=None)
    
    try:
        invoices = get_yearly_invoices(year)
        summary = get_yearly_summary(year)
        
        period_name = str(year)
        
        excel_buffer = generate_invoice_report_excel(invoices, summary, period_name)
        filename = f'Invoice_Report_{year}.xlsx'
        
        await context.bot.send_chat_action(update.effective_chat.id, ChatAction.UPLOAD_DOCUMENT)
        
        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=excel_buffer,
            filename=filename,
            caption=f"📉 Yearly Invoice Report - {year}\n\n"
                   f"Total Invoices: {summary['total_invoices']}\n"
                   f"Total Amount: ₹{summary['total_amount']:,.2f}\n"
                   f"Paid: ₹{summary['paid_amount']:,.2f}\n"
                   f"Pending: ₹{summary['pending_amount']:,.2f}"
        )
        
        await cmd_invoice_reports(update, context)
        
    except Exception as e:
        await query.edit_message_text(f"❌ Error generating report: {str(e)}")


async def callback_invoice_report_custom(update: Update, context: CallbackContext):
    """Handle custom date range report"""
    query = update.callback_query
    await query.answer()
    
    text = """
🗓️ *Custom Date Range Report*

Please enter the date range in this format:

`DD.MM.YYYY to DD.MM.YYYY`

*Examples:*
• `01.01.2026 to 31.01.2026` - January 2026
• `01.01.2026 to 31.03.2026` - Q1 2026
• `01.04.2025 to 31.03.2026` - Financial year

Max range: 2 years (730 days)
Dates will be auto-swapped if reversed.
    """
    
    await query.edit_message_text(text, parse_mode='Markdown')
    return CUSTOM_DATE_INPUT


async def handle_custom_date_input(update: Update, context: CallbackContext):
    """Handle custom date input and generate report"""
    user_input = update.message.text.strip()
    
    # Parse input: "DD.MM.YYYY to DD.MM.YYYY"
    if ' to ' not in user_input:
        await update.message.reply_text(
            "❌ Invalid format!\n\n"
            "Please use: `DD.MM.YYYY to DD.MM.YYYY`\n\n"
            "Example: `01.01.2026 to 31.01.2026`",
            parse_mode='Markdown'
        )
        return CUSTOM_DATE_INPUT
    
    try:
        parts = user_input.split(' to ')
        start_str = parts[0].strip()
        end_str = parts[1].strip()
        
        start_date = datetime.strptime(start_str, "%d.%m.%Y")
        end_date = datetime.strptime(end_str, "%d.%m.%Y")
        
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid date format!\n\n"
            "Use: `DD.MM.YYYY to DD.MM.YYYY`\n\n"
            "Examples:\n"
            "• `01.01.2026 to 31.01.2026`\n"
            "• `15.03.2025 to 20.06.2025`",
            parse_mode='Markdown'
        )
        return CUSTOM_DATE_INPUT
    
    # Generate report
    msg = await update.message.reply_text("⏳ Generating custom date range report...")
    
    try:
        success, invoices, error = get_custom_date_range_invoices(start_date, end_date)
        
        if not success:
            await msg.edit_text(f"❌ {error}")
            return CUSTOM_DATE_INPUT
        
        success, summary, error = get_custom_date_range_summary(start_date, end_date)
        
        if not success:
            await msg.edit_text(f"❌ {error}")
            return CUSTOM_DATE_INPUT
        
        period_name = f"{start_date.strftime('%d.%m.%Y')} to {end_date.strftime('%d.%m.%Y')}"
        
        excel_buffer = generate_invoice_report_excel(invoices, summary, period_name)
        filename = f'Invoice_Report_{start_date.strftime("%d%m%Y")}_to_{end_date.strftime("%d%m%Y")}.xlsx'
        
        await context.bot.send_chat_action(update.effective_chat.id, ChatAction.UPLOAD_DOCUMENT)
        
        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=excel_buffer,
            filename=filename,
            caption=f"🗓️ Custom Date Range Invoice Report\n"
                   f"{start_date.strftime('%d.%m.%Y')} to {end_date.strftime('%d.%m.%Y')}\n\n"
                   f"Total Invoices: {summary['total_invoices']}\n"
                   f"Total Amount: ₹{summary['total_amount']:,.2f}\n"
                   f"Paid: ₹{summary['paid_amount']:,.2f}\n"
                   f"Pending: ₹{summary['pending_amount']:,.2f}"
        )
        
        await msg.delete()
        
        # Show menu again
        keyboard = [
            [InlineKeyboardButton("⬅️ Back to Reports", callback_data="cmd_invoice_reports")],
            [InlineKeyboardButton("🏠 Back to Dashboard", callback_data="cmd_admin_panel")]
        ]
        await update.message.reply_text(
            "✅ Report generated and sent above.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        return ConversationHandler.END
        
    except Exception as e:
        await msg.edit_text(f"❌ Error generating report: {str(e)}")
        return CUSTOM_DATE_INPUT


def get_invoice_report_conversation_handler():
    """
    Create and return the invoice report conversation handler
    
    Returns:
        ConversationHandler configured for invoice reports
    """
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(cmd_invoice_reports, pattern="^cmd_invoice_reports$"),
        ],
        states={
            ConversationHandler.END: [],
            CUSTOM_DATE_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_custom_date_input),
            ]
        },
        fallbacks=[
            CallbackQueryHandler(cmd_invoice_reports, pattern="^cmd_invoice_reports$"),
        ],
        per_user=True,
        per_chat=False,
        per_message=False,
        name="invoice_reports",
        persistent=False
    )


def get_invoice_report_callbacks():
    """
    Create and return CallbackQueryHandlers for invoice report callbacks
    These handle the button clicks in the report menus
    
    Returns:
        List of CallbackQueryHandler objects
    """
    return [
        CallbackQueryHandler(callback_invoice_report_monthly, pattern="^invoice_monthly$"),
        CallbackQueryHandler(callback_invoice_monthly_selected, pattern="^invoice_monthly_"),
        CallbackQueryHandler(callback_invoice_report_quarterly, pattern="^invoice_quarterly$"),
        CallbackQueryHandler(callback_invoice_quarterly_selected, pattern="^invoice_quarterly_"),
        CallbackQueryHandler(callback_invoice_report_six_months, pattern="^invoice_six_months$"),
        CallbackQueryHandler(callback_invoice_six_months_selected, pattern="^invoice_six_months_"),
        CallbackQueryHandler(callback_invoice_report_yearly, pattern="^invoice_yearly$"),
        CallbackQueryHandler(callback_invoice_yearly_selected, pattern="^invoice_yearly_"),
        CallbackQueryHandler(callback_invoice_report_custom, pattern="^invoice_custom$"),
    ]
