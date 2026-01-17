import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from src.database.attendance_operations import (
    get_pending_attendance_requests, approve_attendance, reject_attendance, award_weekly_bonus
)
from src.database.shake_operations import (
    get_pending_shakes, approve_shake, complete_shake, cancel_shake
)
from src.utils.auth import is_admin_id
from src.database.staff_operations import add_staff, remove_staff, list_staff
from src.database.admin_operations import add_admin, remove_admin
from src.database.role_operations import list_admins
from src.database.user_operations import approve_user, reject_user, get_pending_users, get_user

logger = logging.getLogger(__name__)


def get_admin_ids() -> list:
    """Get list of all admin user IDs"""
    try:
        admins = list_admins()
        if admins:
            return [admin.get('user_id') for admin in admins if admin.get('user_id')]
    except Exception as e:
        logger.error(f"Error getting admin IDs: {e}")
    return []


async def cmd_pending_attendance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show pending attendance requests for admin"""
    if not is_admin_id(update.effective_user.id):
        # Handle both command and callback contexts
        if update.callback_query:
            await update.callback_query.answer("❌ Admin access only.")
            return
        await update.message.reply_text("❌ Admin access only.")
        return
    
    # Handle both command and callback contexts
    if update.callback_query:
        await update.callback_query.answer()
        message = update.callback_query.message
    else:
        message = update.message
    
    pending = get_pending_attendance_requests()
    
    if not pending:
        await message.reply_text("✅ No pending attendance requests!")
        return
    
    text = "📋 *Pending Attendance Requests*\n\n"
    
    for req in pending[:5]:  # Show first 5
        text += f"👤 {req['full_name']}\n"
        text += f"📅 {req['request_date']}\n"
        if req['photo_url']:
            text += f"📸 Photo attached\n"
        text += f"─────────────────\n"
    
    if len(pending) > 5:
        text += f"\n...and {len(pending) - 5} more"
    
    keyboard = [
        [InlineKeyboardButton("✅ Review Requests", callback_data="review_attendance_1")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await message.reply_text(
        text,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def cmd_pending_shakes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show pending shake requests for admin"""
    if not is_admin_id(update.effective_user.id):
        await update.message.reply_text("❌ Admin access only.")
        return
    
    pending = get_pending_shakes()
    
    if not pending:
        await update.message.reply_text("✅ No pending shake requests!")
        return
    
    message = "🥛 *Pending Shake Requests*\n\n"
    
    for req in pending[:5]:  # Show first 5
        message += f"👤 {req['full_name']}\n"
        message += f"🍓 {req['flavor_name']}\n"
        if req['notes']:
            message += f"📝 {req['notes']}\n"
        message += f"─────────────────\n"
    
    if len(pending) > 5:
        message += f"\n...and {len(pending) - 5} more"
    
    keyboard = [
        [InlineKeyboardButton("🥛 Review Shakes", callback_data="review_shakes_1")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        message,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def callback_review_attendance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Review and approve attendance requests"""
    query = update.callback_query
    
    if not is_admin_id(query.from_user.id):
        await query.answer("❌ Admin access only.", show_alert=True)
        return
    
    pending = get_pending_attendance_requests(limit=1)
    
    if not pending:
        await query.answer("✅ No more pending requests!", show_alert=True)
        return
    
    req = pending[0]
    
    message = f"👤 *{req['full_name']}*\n"
    message += f"📱 @{req['telegram_username'] or 'unknown'}\n"
    message += f"📅 {req['request_date']}\n"
    
    keyboard = [
        [InlineKeyboardButton("✅ Approve", callback_data=f"approve_attend_{req['attendance_id']}"),
         InlineKeyboardButton("❌ Reject", callback_data=f"reject_attend_{req['attendance_id']}")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=message,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def callback_review_shakes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Review and approve shake requests"""
    query = update.callback_query
    
    if not is_admin_id(query.from_user.id):
        await query.answer("❌ Admin access only.", show_alert=True)
        return
    
    pending = get_pending_shakes(limit=1)
    
    if not pending:
        await query.answer("✅ No more pending requests!", show_alert=True)
        return
    
    shake = pending[0]
    
    message = f"👤 *{shake['full_name']}*\n"
    message += f"📱 @{shake['telegram_username'] or 'unknown'}\n"
    message += f"🍓 *Flavor:* {shake['flavor_name']}\n"
    
    if shake['notes']:
        message += f"📝 *Notes:* {shake['notes']}\n"
    
    keyboard = [
        [InlineKeyboardButton("✅ Ready", callback_data=f"ready_shake_{shake['shake_request_id']}"),
         InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_shake_{shake['shake_request_id']}")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=message,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def callback_approve_attend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Approve attendance"""
    query = update.callback_query
    admin_id = query.from_user.id
    
    if not is_admin_id(admin_id):
        await query.answer("❌ Admin access only.", show_alert=True)
        return
    
    attend_id = int(query.data.split("_")[-1])
    result = approve_attendance(attend_id, admin_id)
    
    if result and result.get('already_processed'):
        await query.answer(f"Already {result.get('status', 'processed')} by someone else", show_alert=True)
        await callback_review_attendance(update, context)
        return

    if result:
        await query.answer("✅ Approved!", show_alert=False)
        
        # Notify user about approval
        user_id = result['user_id']
        try:
            from src.config import POINTS_CONFIG
            
            # Build notification message
            notification_text = (
                f"✅ *Attendance Approved!*\n\n"
                f"Your gym check-in has been approved by admin.\n"
                f"💰 Points Earned: +{POINTS_CONFIG['attendance']}\n"
            )
            
            # Check if user earned weekly bonus
            bonus_result = award_weekly_bonus(user_id, admin_id)
            if bonus_result:
                notification_text += (
                    f"\n🎉 *Weekly Bonus Unlocked!*\n"
                    f"Attendance: {bonus_result['days_attended']}/6 days\n"
                    f"🏆 Bonus Points: +{bonus_result['bonus_points']} 🏆"
                )
            
            notification_text += "\n\nKeep up the great work! 💪"
            
            await context.bot.send_message(
                chat_id=result.get('telegram_id', user_id),
                text=notification_text,
                parse_mode='Markdown'
            )
            logger.info(f"Attendance approval notification sent to user {user_id}")
        except Exception as e:
            logger.error(f"Failed to notify user {user_id} about attendance approval: {e}")
        
        # Show next request
        await callback_review_attendance(update, context)
    else:
        await query.answer("❌ Failed to approve", show_alert=True)

async def callback_reject_attend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reject attendance"""
    query = update.callback_query
    admin_id = query.from_user.id
    
    if not is_admin_id(admin_id):
        await query.answer("❌ Admin access only.", show_alert=True)
        return
    
    attend_id = int(query.data.split("_")[-1])
    result = reject_attendance(attend_id, admin_id, "Not valid")
    
    if result and result.get('already_processed'):
        await query.answer(f"Already {result.get('status', 'processed')} by someone else", show_alert=True)
        await callback_review_attendance(update, context)
        return

    if result:
        await query.answer("❌ Rejected", show_alert=False)
        
        # Notify user about rejection
        user_id = result['user_id']
        try:
            await context.bot.send_message(
                chat_id=result.get('telegram_id', user_id),
                text=(
                    f"❌ *Attendance Request Not Approved*\n\n"
                    f"Your gym check-in request was not approved.\n"
                    f"Please ensure you're at the correct location and try again.\n\n"
                    f"Contact admin if you need assistance."
                ),
                parse_mode='Markdown'
            )
            logger.info(f"Attendance rejection notification sent to user {user_id}")
        except Exception as e:
            logger.error(f"Failed to notify user {user_id} about attendance rejection: {e}")
        
        # Show next request
        await callback_review_attendance(update, context)
    else:
        await query.answer("❌ Failed to reject", show_alert=True)

async def callback_ready_shake(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mark shake as ready"""
    query = update.callback_query
    admin_id = query.from_user.id
    
    if not is_admin_id(admin_id):
        await query.answer("❌ Admin access only.", show_alert=True)
        return
    
    shake_id = int(query.data.split("_")[-1])
    result = approve_shake(shake_id, admin_id)
    
    if result and result.get('already_processed'):
        await query.answer(f"Already {result.get('status', 'processed')}", show_alert=True)
        await callback_review_shakes(update, context)
        return

    if result:
        await query.answer("✅ Marked ready!", show_alert=False)
        
        # Notify user that shake is ready
        try:
            user_id = result.get('user_id')
            telegram_id = result.get('telegram_id', user_id)
            flavor_name = result.get('flavor_name', 'Your shake')
            
            await context.bot.send_message(
                chat_id=telegram_id,
                text=(
                    f"🥛 *Shake Ready!*\n\n"
                    f"Your {flavor_name} shake is ready!\n"
                    f"Please collect it from the counter.\n\n"
                    f"Enjoy! 😊"
                ),
                parse_mode='Markdown'
            )
            logger.info(f"Shake ready notification sent to user {user_id}")
        except Exception as e:
            logger.error(f"Failed to notify user about shake: {e}")
        
        # Show next shake
        await callback_review_shakes(update, context)
    else:
        await query.answer("❌ Failed to prepare", show_alert=True)

async def callback_cancel_shake(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel shake request"""
    query = update.callback_query
    
    if not is_admin_id(query.from_user.id):
        await query.answer("❌ Admin access only.", show_alert=True)
        return
    
    shake_id = int(query.data.split("_")[-1])
    result = cancel_shake(shake_id, "Cancelled by admin")
    
    if result:
        await query.answer("❌ Cancelled", show_alert=False)
        
        # Notify user about cancellation
        try:
            user_id = result.get('user_id')
            telegram_id = result.get('telegram_id', user_id)
            flavor_name = result.get('flavor_name', 'shake')
            
            await context.bot.send_message(
                chat_id=telegram_id,
                text=(
                    f"❌ *Shake Request Cancelled*\n\n"
                    f"Your {flavor_name} request has been cancelled.\n"
                    f"Please contact admin if you need assistance."
                ),
                parse_mode='Markdown'
            )
            logger.info(f"Shake cancellation notification sent to user {user_id}")
        except Exception as e:
            logger.error(f"Failed to notify user about shake cancellation: {e}")
        
        # Show next shake
        await callback_review_shakes(update, context)
    else:
        await query.answer("❌ Failed to cancel", show_alert=True)


# --- Staff management commands ---

async def cmd_add_staff(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: assign a staff ID; either via argument or prompt for paste."""
    admin_id = update.effective_user.id
    if not is_admin_id(admin_id):
        await update.message.reply_text("❌ Admin access only.")
        return

    # If ID passed as argument, use it. Else prompt and await next numeric message.
    if context.args:
        try:
            staff_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("Please provide a numeric Telegram ID.")
            return
        if add_staff(staff_id, admin_id):
            await update.message.reply_text(f"✅ Added staff: {staff_id}")
        else:
            await update.message.reply_text("❌ Failed to add staff.")
        return

    # Handle both command and callback query
    message = update.callback_query.message if update.callback_query else update.message
    context.user_data['awaiting_staff_add'] = True
    await message.reply_text("Paste the staff Telegram ID to add.")


async def cmd_remove_staff(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: remove a staff ID; via argument or prompt."""
    admin_id = update.effective_user.id
    if not is_admin_id(admin_id):
        await update.message.reply_text("❌ Admin access only.")
        return

    if context.args:
        try:
            staff_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("Please provide a numeric Telegram ID.")
            return
        if remove_staff(staff_id):
            await update.message.reply_text(f"✅ Removed staff: {staff_id}")
        else:
            await update.message.reply_text("❌ Staff not found or failed.")
        return

    context.user_data['awaiting_staff_remove'] = True
    await update.message.reply_text("Paste the staff Telegram ID to remove.")


async def cmd_list_staff(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: list current staff IDs."""
    admin_id = update.effective_user.id
    if not is_admin_id(admin_id):
        await update.message.reply_text("❌ Admin access only.")
        return
    rows = list_staff()
    if not rows:
        await update.message.reply_text("No staff assigned yet.")
        return
    lines = [f"🧑‍🍳 {r['staff_id']} (added_by {r['added_by']})" for r in rows[:50]]
    await update.message.reply_text("\n".join(lines))


async def handle_staff_id_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Capture a numeric message when awaiting staff add/remove."""
    if not update.message or not update.message.text:
        return
    admin_id = update.effective_user.id
    if not is_admin_id(admin_id):
        return
    text = update.message.text.strip()
    if not text.isdigit():
        return
    staff_id = int(text)

    if context.user_data.get('awaiting_staff_add'):
        context.user_data['awaiting_staff_add'] = False
        if add_staff(staff_id, admin_id):
            await update.message.reply_text(f"✅ Added staff: {staff_id}")
            # Update commands for the new staff member
            try:
                from src.bot import set_commands_for_user
                context.application.create_task(set_commands_for_user(staff_id, context.bot))
            except Exception as e:
                logger.warning(f"Could not update commands for new staff {staff_id}: {e}")
        else:
            await update.message.reply_text("❌ Failed to add staff.")
        return

    if context.user_data.get('awaiting_staff_remove'):
        context.user_data['awaiting_staff_remove'] = False
        if remove_staff(staff_id):
            await update.message.reply_text(f"✅ Removed staff: {staff_id}")
            # Update commands for the removed staff (they're now just users)
            try:
                from src.bot import set_commands_for_user
                context.application.create_task(set_commands_for_user(staff_id, context.bot))
            except Exception as e:
                logger.warning(f"Could not update commands for removed staff {staff_id}: {e}")
        else:
            await update.message.reply_text("❌ Staff not found or failed.")
        return

    # Admin assignments via pasted ID
    if context.user_data.get('awaiting_admin_add'):
        context.user_data['awaiting_admin_add'] = False
        if add_admin(staff_id, admin_id):
            await update.message.reply_text(f"✅ Added admin: {staff_id}")
            # Update commands for the new admin
            try:
                from src.bot import set_commands_for_user
                context.application.create_task(set_commands_for_user(staff_id, context.bot))
            except Exception as e:
                logger.warning(f"Could not update commands for new admin {staff_id}: {e}")
        else:
            await update.message.reply_text("❌ Failed to add admin.")
        return

    if context.user_data.get('awaiting_admin_remove'):
        context.user_data['awaiting_admin_remove'] = False
        if remove_admin(staff_id):
            await update.message.reply_text(f"✅ Removed admin: {staff_id}")
            # Update commands for the removed admin (they're now just users/staff)
            try:
                from src.bot import set_commands_for_user
                context.application.create_task(set_commands_for_user(staff_id, context.bot))
            except Exception as e:
                logger.warning(f"Could not update commands for removed admin {staff_id}: {e}")
        else:
            await update.message.reply_text("❌ Admin not found or failed.")
        return

    # User management via pasted ID
    if context.user_data.get('awaiting_user_delete'):
        from src.database.user_operations import get_user, delete_user
        context.user_data['awaiting_user_delete'] = False
        user = get_user(staff_id)
        if not user:
            await update.message.reply_text(f"❌ User {staff_id} not found.")
            return
        
        # Create confirmation keyboard
        keyboard = [
            [InlineKeyboardButton("✅ Yes, Delete", callback_data=f"confirm_delete_{staff_id}"),
             InlineKeyboardButton("❌ Cancel", callback_data="cancel_delete")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"⚠️ *Confirm Deletion*\n\n"
            f"User: {user['full_name']}\n"
            f"ID: `{staff_id}`\n"
            f"Phone: {user['phone']}\n\n"
            f"This will permanently delete all their data!\n"
            f"Are you sure?",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return

    if context.user_data.get('awaiting_user_ban'):
        from src.database.user_operations import ban_user, get_user
        context.user_data['awaiting_user_ban'] = False
        user = get_user(staff_id)
        if not user:
            await update.message.reply_text(f"❌ User {staff_id} not found.")
            return
        
        result = ban_user(staff_id, "Banned by admin")
        if result:
            await update.message.reply_text(
                f"🚫 *User Banned*\n\n"
                f"User: {result['full_name']}\n"
                f"ID: `{staff_id}`",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text("❌ Failed to ban user.")
        return

    if context.user_data.get('awaiting_user_unban'):
        from src.database.user_operations import unban_user
        context.user_data['awaiting_user_unban'] = False
        result = unban_user(staff_id)
        if result:
            await update.message.reply_text(
                f"✅ *User Unbanned*\n\n"
                f"User: {result['full_name']}\n"
                f"ID: `{staff_id}`",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text("❌ User not found or not banned.")
        return


async def cmd_add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_id = update.effective_user.id
    if not is_admin_id(admin_id):
        await update.message.reply_text("❌ Admin access only.")
        return
    if context.args:
        try:
            new_admin_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("Please provide a numeric Telegram ID.")
            return
        if add_admin(new_admin_id, admin_id):
            await update.message.reply_text(f"✅ Added admin: {new_admin_id}")
            # Update commands for the new admin
            try:
                from src.bot import set_commands_for_user
                context.application.create_task(set_commands_for_user(new_admin_id, context.bot))
            except Exception as e:
                logger.warning(f"Could not update commands for new admin {new_admin_id}: {e}")
        else:
            await update.message.reply_text("❌ Failed to add admin.")
        return
    # Handle both command and callback query
    message = update.callback_query.message if update.callback_query else update.message
    context.user_data['awaiting_admin_add'] = True
    await message.reply_text("Paste the admin Telegram ID to add.")


async def cmd_remove_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_id = update.effective_user.id
    if not is_admin_id(admin_id):
        await update.message.reply_text("❌ Admin access only.")
        return
    if context.args:
        try:
            target_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("Please provide a numeric Telegram ID.")
            return
        if remove_admin(target_id):
            await update.message.reply_text(f"✅ Removed admin: {target_id}")
        else:
            await update.message.reply_text("❌ Admin not found or failed.")
        return
    context.user_data['awaiting_admin_remove'] = True
    await update.message.reply_text("Paste the admin Telegram ID to remove.")


async def cmd_list_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_id = update.effective_user.id
    if not is_admin_id(admin_id):
        await update.message.reply_text("❌ Admin access only.")
        return
    rows = list_admins()
    if not rows:
        await update.message.reply_text("No admins assigned yet.")
        return
    lines = [f"🛡️ {r['admin_id']} (added_by {r['added_by']})" for r in rows[:50]]
    await update.message.reply_text("\n".join(lines))


async def cmd_list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all registered users with pagination"""
    from src.database.user_operations import get_all_users, get_total_users_count
    
    if not is_admin_id(update.effective_user.id):
        # Handle both command and callback contexts
        if update.callback_query:
            await update.callback_query.answer("❌ Admin access only.")
            return
        await update.message.reply_text("❌ Admin access only.")
        return
    
    # Handle both command and callback contexts
    if update.callback_query:
        await update.callback_query.answer()
        message = update.callback_query.message
    else:
        message = update.message
    
    total_users = get_total_users_count()
    users = get_all_users()
    
    if not users:
        await message.reply_text("📋 No users registered yet.")
        return
    
    text = f"👥 *Registered Users: {total_users}*\n\n"
    
    # Show first 10 users
    for user in users[:10]:
        status_emoji = "🚫" if user.get('is_banned') else "✅"
        role_emoji = "🛡️" if user['role'] == 'admin' else "🧑‍🍳" if user['role'] == 'staff' else "👤"
        role_text = user['role'].capitalize() if user['role'] else "User"
        text += f"{status_emoji} {role_emoji} *{user['full_name']}*\n"
        text += f"   ID: `{user['user_id']}`\n"
        text += f"   Role: {role_text}\n"
        text += f"   Phone: {user['phone']}\n"
        text += f"   Fee: {user.get('fee_status', 'unpaid')}\n"
        text += f"─────────────────\n"
    
    if len(users) > 10:
        text += f"\n_Showing 10 of {total_users} users_"
    
    keyboard = [
        [InlineKeyboardButton("🗑️ Delete User", callback_data="admin_delete_user"),
         InlineKeyboardButton("🚫 Ban User", callback_data="admin_ban_user")],
        [InlineKeyboardButton("✅ Unban User", callback_data="admin_unban_user")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")


async def cmd_delete_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete a user by ID"""
    from src.database.user_operations import delete_user, get_user
    
    if not is_admin_id(update.effective_user.id):
        await update.message.reply_text("❌ Admin access only.")
        return
    
    # Handle both command and callback contexts
    if update.callback_query:
        await update.callback_query.answer()
        message = update.callback_query.message
        context.user_data['awaiting_user_delete'] = True
        await message.reply_text(
            "⚠️ *Delete User*\n\n"
            "Send the Telegram ID of the user you want to delete.\n"
            "⚠️ This will permanently remove all their data!",
            parse_mode="Markdown"
        )
        return
    
    if context.args:
        try:
            target_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ Please provide a valid numeric Telegram ID.")
            return
        
        # Check if user exists
        user = get_user(target_id)
        if not user:
            await update.message.reply_text(f"❌ User {target_id} not found.")
            return
        
        # Confirm deletion
        keyboard = [
            [InlineKeyboardButton("✅ Yes, Delete", callback_data=f"confirm_delete_{target_id}"),
             InlineKeyboardButton("❌ Cancel", callback_data="cancel_delete")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"⚠️ *Confirm Deletion*\n\n"
            f"User: {user['full_name']}\n"
            f"ID: `{target_id}`\n"
            f"Phone: {user['phone']}\n\n"
            f"This will permanently delete all their data!\n"
            f"Are you sure?",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return
    
    context.user_data['awaiting_user_delete'] = True
    await update.message.reply_text(
        "⚠️ *Delete User*\n\n"
        "Send the Telegram ID of the user you want to delete.\n"
        "⚠️ This will permanently remove all their data!",
        parse_mode="Markdown"
    )


async def cmd_ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ban a user by ID"""
    from src.database.user_operations import ban_user, get_user
    
    if not is_admin_id(update.effective_user.id):
        await update.message.reply_text("❌ Admin access only.")
        return
    
    # Handle both command and callback contexts
    if update.callback_query:
        await update.callback_query.answer()
        message = update.callback_query.message
        context.user_data['awaiting_user_ban'] = True
        await message.reply_text(
            "🚫 *Ban User*\n\n"
            "Send the Telegram ID of the user you want to ban.",
            parse_mode="Markdown"
        )
        return
    
    if context.args:
        try:
            target_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ Please provide a valid numeric Telegram ID.")
            return
        
        # Check if user exists
        user = get_user(target_id)
        if not user:
            await update.message.reply_text(f"❌ User {target_id} not found.")
            return
        
        # Ban user with optional reason
        reason = " ".join(context.args[1:]) if len(context.args) > 1 else "Banned by admin"
        result = ban_user(target_id, reason)
        
        if result:
            await update.message.reply_text(
                f"🚫 *User Banned*\n\n"
                f"User: {result['full_name']}\n"
                f"ID: `{target_id}`\n"
                f"Reason: {reason}",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text("❌ Failed to ban user.")
        return
    
    context.user_data['awaiting_user_ban'] = True
    await update.message.reply_text(
        "🚫 *Ban User*\n\n"
        "Send the Telegram ID of the user you want to ban.",
        parse_mode="Markdown"
    )


async def cmd_unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unban a user by ID"""
    from src.database.user_operations import unban_user, get_user
    
    if not is_admin_id(update.effective_user.id):
        await update.message.reply_text("❌ Admin access only.")
        return
    
    # Handle both command and callback contexts
    if update.callback_query:
        await update.callback_query.answer()
        message = update.callback_query.message
        context.user_data['awaiting_user_unban'] = True
        await message.reply_text(
            "✅ *Unban User*\n\n"
            "Send the Telegram ID of the user you want to unban.",
            parse_mode="Markdown"
        )
        return
    
    if context.args:
        try:
            target_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ Please provide a valid numeric Telegram ID.")
            return
        
        result = unban_user(target_id)
        
        if result:
            await update.message.reply_text(
                f"✅ *User Unbanned*\n\n"
                f"User: {result['full_name']}\n"
                f"ID: `{target_id}`",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text("❌ User not found or not banned.")
        return
    
    context.user_data['awaiting_user_unban'] = True
    await update.message.reply_text(
        "✅ *Unban User*\n\n"
        "Send the Telegram ID of the user you want to unban.",
        parse_mode="Markdown"
    )

async def callback_approve_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Approve a pending user registration"""
    query = update.callback_query
    await query.answer()
    
    admin_id = update.effective_user.id
    
    if not is_admin_id(admin_id):
        await query.edit_message_text("❌ Admin access only.")
        return
    
    user_id = int(query.data.split('_')[-1])
    
    # Get user details
    user = get_user(user_id)
    if not user:
        await query.edit_message_text("❌ User not found.")
        return
    
    # Check if already approved
    if user.get('approval_status') == 'approved':
        await query.edit_message_text(
            f"✅ *Already Approved*\n\n"
            f"User {user['full_name']} was already approved.",
            parse_mode='Markdown'
        )
        return
    
    # Approve the user
    result = approve_user(user_id, admin_id)
    
    if result:
        await query.edit_message_text(
            f"✅ *User Approved*\n\n"
            f"👤 Name: {result['full_name']}\n"
            f"🆔 ID: `{user_id}`\n\n"
            "User has been notified.",
            parse_mode='Markdown'
        )
        
        # Notify the user
        try:
            # Show subscription prompt after approval
            keyboard = [[InlineKeyboardButton("💪 Subscribe Now", callback_data="start_subscribe")]]
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    f"🎉 *Registration Approved!*\n\n"
                    f"Welcome to the Fitness Club, {user['full_name']}!\n\n"
                    "Your registration has been approved. 🎊\n\n"
                    "🔒 *Next Step: Subscribe to access the app*\n\n"
                    "Choose a subscription plan below to unlock all features:"
                ),
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Failed to notify user {user_id}: {e}")
    else:
        await query.edit_message_text("❌ Failed to approve user.")

async def callback_reject_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reject a pending user registration"""
    query = update.callback_query
    await query.answer()
    
    admin_id = update.effective_user.id
    
    if not is_admin_id(admin_id):
        await query.edit_message_text("❌ Admin access only.")
        return
    
    user_id = int(query.data.split('_')[-1])
    
    # Get user details
    user = get_user(user_id)
    if not user:
        await query.edit_message_text("❌ User not found.")
        return
    
    # Check if already processed
    if user.get('approval_status') != 'pending':
        await query.edit_message_text(
            f"ℹ️ *Already Processed*\n\n"
            f"User {user['full_name']} was already {user.get('approval_status')}.",
            parse_mode='Markdown'
        )
        return
    
    # Reject the user
    result = reject_user(user_id, admin_id)
    
    if result:
        await query.edit_message_text(
            f"❌ *User Rejected*\n\n"
            f"👤 Name: {result['full_name']}\n"
            f"🆔 ID: `{user_id}`\n\n"
            "User has been notified.",
            parse_mode='Markdown'
        )
        
        # Notify the user
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    f"❌ *Registration Not Approved*\n\n"
                    f"Hello {user['full_name']},\n\n"
                    "Your registration could not be approved at this time.\n"
                    "Please contact admin for more information.\n\n"
                    "You can reach out via the contact details shared earlier."
                ),
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Failed to notify user {user_id}: {e}")
    else:
        await query.edit_message_text("❌ Failed to reject user.")

async def cmd_pending_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show pending user registrations"""
    admin_id = update.effective_user.id
    
    if not is_admin_id(admin_id):
        if update.callback_query:
            await update.callback_query.answer("❌ Admin access only.")
            return
        await update.message.reply_text("❌ Admin access only.")
        return
    
    # Handle both command and callback contexts
    if update.callback_query:
        await update.callback_query.answer()
        message = update.callback_query.message
    else:
        message = update.message
    
    pending = get_pending_users()
    
    if not pending:
        await message.reply_text("✅ No pending user registrations!")
        return
    
    text = "👥 *Pending User Registrations*\n\n"
    
    for user in pending[:10]:  # Show first 10
        text += f"👤 {user['full_name']}\n"
        text += f"🆔 ID: `{user['user_id']}`\n"
        text += f"📞 {user['phone']}\n"
        text += f"📅 Registered: {user['created_at'].strftime('%d %b %Y')}\n"
        text += f"─────────────────\n"
    
    if len(pending) > 10:
        text += f"\n...and {len(pending) - 10} more\n"
    
    text += "\nUse the buttons on registration notifications to approve/reject."
    
    await message.reply_text(text, parse_mode='Markdown')
