"""
Enhanced Admin Dashboard with Member Management & Export
- Member list with filtering
- Excel export functionality  
- User management (delete/ban)
- Analytics and reports
"""

import logging
import io
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler
from src.database.user_operations import (
    get_all_users, get_user, delete_user, ban_user, unban_user, is_user_banned
)
from src.utils.auth import is_admin
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from datetime import datetime

logger = logging.getLogger(__name__)

# Conversation states for user management
MANAGE_USER_MENU, SELECT_USER_ACTION, CONFIRM_DELETE, ENTER_BAN_REASON = range(4)


async def cmd_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main admin panel with all options"""
    if not is_admin(update.effective_user.id):
        if update.callback_query:
            await update.callback_query.answer("❌ Admin access only.")
        else:
            await update.message.reply_text("❌ Admin access only.")
        return
    
    # Handle both message and callback contexts
    if update.callback_query:
        await update.callback_query.answer()
        message = update.callback_query.message
    else:
        message = update.message
    
    keyboard = [
        [InlineKeyboardButton("👥 Member List", callback_data="admin_members_list"),
         InlineKeyboardButton("📊 Dashboard", callback_data="admin_dashboard")],
        [InlineKeyboardButton("👤 Manage Users", callback_data="admin_manage_users"),
         InlineKeyboardButton("📥 Excel Export", callback_data="admin_export_excel")],
        [InlineKeyboardButton("💰 Revenue Stats", callback_data="dashboard_revenue"),
         InlineKeyboardButton("📈 Engagement", callback_data="dashboard_engagement")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await message.reply_text(
        "🔧 *Admin Control Panel*\n\n"
        "Select an option below:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


async def cmd_member_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display list of all members with pagination"""
    query = update.callback_query
    
    if not is_admin(query.from_user.id):
        await query.answer("❌ Admin access only.", show_alert=True)
        return
    
    await query.answer()
    
    # Get page number from callback data or default to 1
    try:
        page = int(query.data.split('_')[-1]) if '_' in query.data else 1
    except:
        page = 1
    
    users = get_all_users()
    if not users:
        await query.edit_message_text("📭 No members found.")
        return
    
    # Pagination: 10 members per page
    per_page = 10
    total_pages = (len(users) + per_page - 1) // per_page
    page = max(1, min(page, total_pages))
    
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    page_users = users[start_idx:end_idx]
    
    # Build member list message
    message = "👥 *Member List*\n\n"
    message += f"Page {page}/{total_pages} (Total: {len(users)} members)\n"
    message += "─────────────────────────\n\n"
    
    for user in page_users:
        status = "🚫" if user.get('is_banned') else "✅"
        role_emoji = "👑" if user['role'] == 'super_admin' else "👮" if user['role'] == 'staff' else "👤"
        
        message += f"{status} {role_emoji} *{user['full_name']}*\n"
        message += f"   📱 {user['phone']}\n"
        message += f"   💳 Status: {user['fee_status']}\n"
        message += f"   📅 Joined: {user['created_at']}\n"
        message += f"   🆔 ID: `{user['user_id']}`\n"
        message += "─────────────────────────\n"
    
    # Build navigation and action buttons
    keyboard = []
    
    # Pagination buttons
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"admin_members_list_{page-1}"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton("➡️ Next", callback_data=f"admin_members_list_{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # Action buttons
    keyboard.append([
        InlineKeyboardButton("🔍 Filter", callback_data="admin_filter_members"),
        InlineKeyboardButton("👤 Select User", callback_data="admin_select_user")
    ])
    
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="admin_dashboard_menu")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=message,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


async def cmd_manage_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Select user for management operations"""
    query = update.callback_query
    
    if not is_admin(query.from_user.id):
        await query.answer("❌ Admin access only.", show_alert=True)
        return
    
    await query.answer()
    
    await query.edit_message_text(
        text="👤 *Manage Users*\n\n"
        "Send the User ID of the member you want to manage:\n\n"
        "Example: `424837855`",
        parse_mode="Markdown"
    )
    
    return MANAGE_USER_MENU


async def handle_user_id_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user ID input for management"""
    try:
        user_id = int(update.message.text)
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid format. Please send a valid User ID (numbers only).\n\n"
            "Example: `424837855`",
            parse_mode="Markdown"
        )
        return MANAGE_USER_MENU
    
    # Get user details
    user = get_user(user_id)
    if not user:
        await update.message.reply_text(
            f"❌ User with ID `{user_id}` not found.\n\n"
            "Please try again or use /cancel to exit.",
            parse_mode="Markdown"
        )
        return MANAGE_USER_MENU
    
    # Store user_id in context for later use
    context.user_data['selected_user_id'] = user_id
    context.user_data['selected_user'] = user
    
    # Show user details and management options
    is_banned = user.get('is_banned', False)
    status = "🚫 BANNED" if is_banned else "✅ ACTIVE"
    
    message = f"👤 *User Details*\n\n"
    message += f"Name: *{user['full_name']}*\n"
    message += f"📱 Phone: {user['phone']}\n"
    message += f"Age: {user['age']}\n"
    message += f"Gender: {user.get('gender', 'N/A')}\n"
    message += f"Role: {user['role']}\n"
    message += f"Fee Status: {user['fee_status']}\n"
    message += f"Status: {status}\n"
    message += f"Joined: {user['created_at']}\n"
    
    # Management buttons
    keyboard = [
        [InlineKeyboardButton("🚫 Ban User" if not is_banned else "✅ Unban User", 
                              callback_data="manage_toggle_ban")],
        [InlineKeyboardButton("🗑️ Delete User", callback_data="manage_delete_user")],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="admin_manage_users_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        message,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    
    return SELECT_USER_ACTION


async def callback_toggle_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ask for ban reason before banning user"""
    query = update.callback_query
    user_id = context.user_data.get('selected_user_id')
    user = context.user_data.get('selected_user')
    
    if not user_id or not user:
        await query.answer("❌ User information not found.")
        return
    
    await query.answer()
    
    is_currently_banned = user.get('is_banned', False)
    
    if is_currently_banned:
        # Unban user immediately
        unban_user(user_id)
        logger.info(f"Admin {query.from_user.id} unbanned user {user_id}")
        
        # Send notification to user
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text="✅ *Account Unbanned*\n\n"
                     "Your account has been unbanned and is now active. "
                     "You can access the fitness club services again.",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Could not send unban notification to user {user_id}: {e}")
        
        # Send confirmation to admin
        await query.edit_message_text(
            f"✅ User *{user['full_name']}* has been unbanned.\n\n"
            f"📢 Notification sent to user",
            parse_mode="Markdown"
        )
    else:
        # Ask for ban reason
        await query.edit_message_text(
            f"🚫 *Ban User: {user['full_name']}*\n\n"
            f"Please provide a reason for banning this user:\n\n"
            f"Example: \"Non-payment\", \"Disruptive behavior\", \"Suspended membership\"",
            parse_mode="Markdown"
        )
        return ENTER_BAN_REASON




async def handle_ban_reason_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle ban reason input and execute ban"""
    ban_reason = update.message.text.strip()
    user_id = context.user_data.get('selected_user_id')
    user = context.user_data.get('selected_user')
    admin_id = update.effective_user.id
    admin_name = update.effective_user.first_name or "Admin"
    
    if not user_id or not user:
        await update.message.reply_text("❌ User information not found.")
        return ENTER_BAN_REASON
    
    # Ban the user with reason
    ban_user(user_id, reason=ban_reason)
    
    logger.info(f"Admin {admin_id} banned user {user_id} with reason: {ban_reason}")
    
    # Send notification to banned user
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text="🚫 *Account Banned*\n\n"
                 f"Your account has been banned.\n\n"
                 f"**Reason:** {ban_reason}\n\n"
                 f"If you believe this is a mistake, please contact the fitness club administrator.",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Could not send ban notification to user {user_id}: {e}")
    
    # Send confirmation to admin
    keyboard = [
        [InlineKeyboardButton("🔙 Back to Admin Panel", callback_data="admin_dashboard_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"✅ *Ban Executed*\n\n"
        f"User: *{user['full_name']}* (ID: `{user_id}`)\n"
        f"Reason: {ban_reason}\n\n"
        f"📢 Notification sent to user",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    
    return SELECT_USER_ACTION


async def callback_delete_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm deletion of user"""
    query = update.callback_query
    user_id = context.user_data.get('selected_user_id')
    user = context.user_data.get('selected_user')
    
    if not user_id or not user:
        await query.answer("❌ User information not found.")
        return
    
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("✅ Yes, Delete", callback_data="confirm_delete_user"),
         InlineKeyboardButton("❌ Cancel", callback_data="admin_manage_users_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"⚠️ *Are you sure you want to delete {user['full_name']}?*\n\n"
        "This will:\n"
        "• Remove user from database\n"
        "• Delete all activity logs\n"
        "• Delete all payment records\n\n"
        "This action cannot be undone!",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    
    return CONFIRM_DELETE


async def callback_confirm_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm and execute user deletion"""
    query = update.callback_query
    user_id = context.user_data.get('selected_user_id')
    user = context.user_data.get('selected_user')
    admin_id = query.from_user.id
    admin_name = query.from_user.first_name or "Admin"
    
    if not user_id or not user:
        await query.answer("❌ User information not found.")
        return
    
    await query.answer()
    
    try:
        # Send notification to user BEFORE deletion
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text="🗑️ *Account Deleted*\n\n"
                     "Your account has been permanently deleted from the fitness club system. "
                     "All your data, including membership records and activity logs, have been removed.\n\n"
                     "If you wish to rejoin, you will need to register as a new member.",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.warning(f"Could not send deletion notification to user {user_id}: {e}")
        
        # Delete the user
        delete_user(user_id)
        logger.info(f"Admin {admin_id} deleted user {user_id}")
        
        # Send confirmation to admin
        keyboard = [
            [InlineKeyboardButton("🔙 Back to Admin Panel", callback_data="admin_dashboard_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"✅ *User Deleted Successfully*\n\n"
            f"User: *{user['full_name']}* (ID: `{user_id}`)\n\n"
            f"📢 Notification sent to user\n"
            f"🗂️ All records removed from database",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        
        # Clear context
        context.user_data.pop('selected_user_id', None)
        context.user_data.pop('selected_user', None)
        
    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        await query.edit_message_text(f"❌ Error deleting user: {str(e)}")


async def cmd_export_excel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Export all members to Excel file"""
    query = update.callback_query
    
    if not is_admin(query.from_user.id):
        await query.answer("❌ Admin access only.", show_alert=True)
        return
    
    await query.answer()
    
    try:
        # Get all users
        users = get_all_users()
        if not users:
            await query.edit_message_text("📭 No members to export.")
            return
        
        # Create Excel workbook
        workbook = openpyxl.Workbook()
        worksheet = workbook.active
        worksheet.title = "Members"
        
        # Define headers
        headers = ["User ID", "Name", "Phone", "Gender", "Age", "Role", "Fee Status", "Joined Date", "Status"]
        
        # Style headers
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF", size=12)
        
        # Write headers
        for col, header in enumerate(headers, 1):
            cell = worksheet.cell(row=1, column=col)
            cell.value = header
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        
        # Write data
        for row, user in enumerate(users, 2):
            worksheet.cell(row=row, column=1).value = user['user_id']
            worksheet.cell(row=row, column=2).value = user['full_name']
            worksheet.cell(row=row, column=3).value = user['phone']
            worksheet.cell(row=row, column=4).value = user.get('gender', 'N/A')
            worksheet.cell(row=row, column=5).value = user.get('age', 'N/A')
            worksheet.cell(row=row, column=6).value = user.get('role', 'user')
            worksheet.cell(row=row, column=7).value = user['fee_status']
            worksheet.cell(row=row, column=8).value = str(user['created_at'])
            
            status = "🚫 Banned" if user.get('is_banned') else "✅ Active"
            worksheet.cell(row=row, column=9).value = status
            
            # Center align all cells
            for col in range(1, 10):
                worksheet.cell(row=row, column=col).alignment = Alignment(horizontal="center", vertical="center")
        
        # Adjust column widths
        worksheet.column_dimensions['A'].width = 12
        worksheet.column_dimensions['B'].width = 20
        worksheet.column_dimensions['C'].width = 15
        worksheet.column_dimensions['D'].width = 12
        worksheet.column_dimensions['E'].width = 10
        worksheet.column_dimensions['F'].width = 12
        worksheet.column_dimensions['G'].width = 12
        worksheet.column_dimensions['H'].width = 18
        worksheet.column_dimensions['I'].width = 12
        
        # Save to bytes
        excel_file = io.BytesIO()
        workbook.save(excel_file)
        excel_file.seek(0)
        
        # Send file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"Members_Export_{timestamp}.xlsx"
        
        await context.bot.send_document(
            chat_id=query.from_user.id,
            document=excel_file,
            filename=filename,
            caption=f"📊 *Member Export*\n\nTotal members: {len(users)}\nExported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        logger.info(f"Admin {query.from_user.id} exported {len(users)} members to Excel")
        
        # Show confirmation
        await query.edit_message_text(
            f"✅ *Export Complete*\n\n"
            f"File: {filename}\n"
            f"Members exported: {len(users)}\n"
            f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Error exporting Excel: {e}")
        await query.edit_message_text(f"❌ Error creating export: {str(e)}")


async def callback_back_to_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Return to admin panel"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("👥 Member List", callback_data="admin_members_list_1"),
         InlineKeyboardButton("📊 Dashboard", callback_data="admin_dashboard")],
        [InlineKeyboardButton("👤 Manage Users", callback_data="admin_manage_users"),
         InlineKeyboardButton("📥 Excel Export", callback_data="admin_export_excel")],
        [InlineKeyboardButton("💰 Revenue Stats", callback_data="dashboard_revenue"),
         InlineKeyboardButton("📈 Engagement", callback_data="dashboard_engagement")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text="🔧 *Admin Control Panel*\n\nSelect an option below:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


def get_manage_users_conversation_handler():
    """Get conversation handler for user management"""
    from telegram.ext import ConversationHandler, MessageHandler, filters, CallbackQueryHandler
    
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(cmd_manage_users, pattern="^admin_manage_users$")],
        states={
            MANAGE_USER_MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_id_input),
                CallbackQueryHandler(cmd_manage_users, pattern="^admin_manage_users$"),
            ],
            SELECT_USER_ACTION: [
                CallbackQueryHandler(callback_toggle_ban, pattern="^manage_toggle_ban$"),
                CallbackQueryHandler(callback_delete_user, pattern="^manage_delete_user$"),
                CallbackQueryHandler(cmd_manage_users, pattern="^admin_manage_users_back$"),
            ],
            CONFIRM_DELETE: [
                CallbackQueryHandler(callback_confirm_delete, pattern="^confirm_delete_user$"),
                CallbackQueryHandler(cmd_manage_users, pattern="^admin_dashboard_menu$"),
            ],
            ENTER_BAN_REASON: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ban_reason_input),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(callback_back_to_admin_panel, pattern="^admin_dashboard_menu$"),
            CommandHandler('cancel', lambda u, c: ConversationHandler.END)
        ],
        per_message=False
    )
