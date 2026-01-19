"""
Scheduled jobs for automated tasks
"""
import logging
from datetime import datetime
from telegram.ext import ContextTypes
from src.utils.report_generator import generate_eod_report
from src.database.reports_operations import move_expired_to_inactive
from src.database.user_operations import get_all_paid_users
from src.config import SUPER_ADMIN_USER_ID

logger = logging.getLogger(__name__)


async def send_eod_report(context: ContextTypes.DEFAULT_TYPE):
    """
    Send End of Day report to admin at 23:55
    """
    try:
        logger.info("Generating EOD report...")
        
        report = generate_eod_report()
        
        # Send to super admin
        if SUPER_ADMIN_USER_ID:
            await context.bot.send_message(
                chat_id=int(SUPER_ADMIN_USER_ID),
                text=report,
                parse_mode="Markdown"
            )
            logger.info(f"EOD report sent to admin {SUPER_ADMIN_USER_ID}")
        else:
            logger.warning("SUPER_ADMIN_USER_ID not configured, EOD report not sent")
    
    except Exception as e:
        logger.error(f"Error sending EOD report: {e}")


async def check_expired_memberships(context: ContextTypes.DEFAULT_TYPE):
    """
    Check and move expired memberships to inactive (7-day grace period)
    Runs daily at 00:01
    """
    try:
        logger.info("Checking expired memberships...")
        
        count = move_expired_to_inactive()
        
        if count > 0:
            message = f"⚠️ *Auto-Expiry Alert*\n\n"
            message += f"Moved {count} members to inactive status.\n"
            message += f"These memberships expired 7+ days ago.\n\n"
            message += f"_Use /reports to view inactive members list._"
            
            # Send notification to admin
            if SUPER_ADMIN_USER_ID:
                await context.bot.send_message(
                    chat_id=int(SUPER_ADMIN_USER_ID),
                    text=message,
                    parse_mode="Markdown"
                )
                logger.info(f"Expiry alert sent to admin: {count} members moved")
        else:
            logger.info("No memberships to expire")
    
    except Exception as e:
        logger.error(f"Error checking expired memberships: {e}")


async def send_water_reminder_hourly(context: ContextTypes.DEFAULT_TYPE):
    """
    Send water reminder to users based on their interval preference
    Respects user's enabled/disabled and interval settings
    Skips sending between 8 PM (20:00) and 6 AM (06:00) for better sleep
    """
    try:
        from datetime import datetime, timedelta
        from src.database.reminder_operations import get_reminder_preferences
        
        # Get current hour
        current_hour = datetime.now().hour
        
        # Skip reminders during night hours (20:00 to 06:00)
        if current_hour >= 20 or current_hour < 6:
            logger.info(f"Skipping water reminders during night hours ({current_hour}:00)")
            return
        
        logger.info("Sending water reminders based on user preferences...")
        
        # Get all users with paid memberships
        paid_users = get_all_paid_users()
        
        if not paid_users:
            logger.info("No paid users found for water reminder")
            return
        
        reminder_text = (
            "💧 *Hydration Reminder*\n\n"
            "Time to log your water intake! 💦\n\n"
            "Staying hydrated helps you stay fit and healthy.\n"
            "Use /water to log your water consumption."
        )
        
        # Create inline buttons for quick actions
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        keyboard = [
            [
                InlineKeyboardButton("💧 Log Water", callback_data="cmd_water"),
                InlineKeyboardButton("⚙️ Reminder Settings", callback_data="cmd_reminders"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        sent_count = 0
        for user in paid_users:
            try:
                # Get user's reminder preferences
                prefs = get_reminder_preferences(user['user_id'])
                
                # Skip if water reminders are disabled
                if not prefs or not prefs.get('water_reminder_enabled', True):
                    logger.debug(f"Water reminders disabled for user {user['user_id']}")
                    continue
                
                # Get user's interval preference (default 60 minutes)
                interval_minutes = prefs.get('water_reminder_interval_minutes', 60)
                
                # Get last reminder time from context (stored per user)
                last_reminder_key = f"last_water_reminder_{user['user_id']}"
                last_reminder = context.user_data.get(last_reminder_key) if hasattr(context, 'user_data') else None
                
                # If we don't have last reminder info, use a persistent storage approach
                # Store in database or use a simple time check
                current_time = datetime.now()
                
                # For now, use a simple approach: check if we should send based on current hour matching interval
                # This ensures approximately the right interval
                minutes_since_hour = current_time.minute
                
                # Only send at the start of each interval period
                # For example: if interval is 120 (2 hours), send at 0:00, 2:00, 4:00, etc.
                should_send = (current_hour * 60 + minutes_since_hour) % interval_minutes < 5
                
                if should_send:
                    await context.bot.send_message(
                        chat_id=user['user_id'],
                        text=reminder_text,
                        parse_mode="Markdown",
                        reply_markup=reply_markup
                    )
                    sent_count += 1
                    logger.debug(f"Water reminder sent to user {user['user_id']} (interval: {interval_minutes}min)")
                else:
                    logger.debug(f"Skipping user {user['user_id']} - not time for next reminder (interval: {interval_minutes}min)")
            except Exception as e:
                logger.debug(f"Could not send water reminder to user {user['user_id']}: {e}")
        
        logger.info(f"Water reminders sent to {sent_count} users")
    
    except Exception as e:
        logger.error(f"Error sending water reminders: {e}")


async def send_weight_reminder_morning(context: ContextTypes.DEFAULT_TYPE):
    """
    Send morning reminder at 9 AM to log weight
    Respects user's enabled/disabled setting
    """
    try:
        from src.database.reminder_operations import get_reminder_preferences
        logger.info("Sending morning weight reminders...")
        
        # Get all users with paid memberships
        paid_users = get_all_paid_users()
        
        if not paid_users:
            logger.info("No paid users found for weight reminder")
            return
        
        reminder_text = (
            "⚖️ *Good Morning!* ☀️\n\n"
            "Time to log your weight today! 📊\n\n"
            "Tracking your weight daily helps you monitor your fitness progress.\n"
            "Use /weight to log your weight."
        )
        
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        keyboard = [
            [
                InlineKeyboardButton("⚖️ Log Weight", callback_data="cmd_weight"),
                InlineKeyboardButton("⚙️ Reminder Settings", callback_data="cmd_reminders"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        sent_count = 0
        for user in paid_users:
            try:
                # Check user's reminder preferences
                prefs = get_reminder_preferences(user['user_id'])
                
                # Skip if weight reminders are disabled
                if not prefs or not prefs.get('weight_reminder_enabled', True):
                    logger.debug(f"Weight reminders disabled for user {user['user_id']}")
                    continue
                
                await context.bot.send_message(
                    chat_id=user['user_id'],
                    text=reminder_text,
                    parse_mode="Markdown",
                    reply_markup=reply_markup
                )
                sent_count += 1
            except Exception as e:
                logger.debug(f"Could not send weight reminder to user {user['user_id']}: {e}")
        
        logger.info(f"Weight reminders sent to {sent_count} users")
    
    except Exception as e:
        logger.error(f"Error sending weight reminders: {e}")


async def send_habits_reminder_evening(context: ContextTypes.DEFAULT_TYPE):
    """
    Send evening reminder at 8 PM to log daily habits
    Respects user's enabled/disabled setting
    """
    try:
        from src.database.reminder_operations import get_reminder_preferences
        logger.info("Sending evening habits reminders...")
        
        # Get all users with paid memberships
        paid_users = get_all_paid_users()
        
        if not paid_users:
            logger.info("No paid users found for habits reminder")
            return
        
        reminder_text = (
            "✅ *Evening Check*\n\n"
            "Time to log your daily habits! 📝\n\n"
            "Completing your daily habits keeps you on track with your fitness goals.\n"
            "Use /habits to log your habits for today."
        )
        
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        keyboard = [
            [
                InlineKeyboardButton("✅ Log Habits", callback_data="cmd_habits"),
                InlineKeyboardButton("⚙️ Reminder Settings", callback_data="cmd_reminders"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        sent_count = 0
        for user in paid_users:
            try:
                # Check user's reminder preferences
                prefs = get_reminder_preferences(user['user_id'])
                
                # Skip if habits reminders are disabled
                if not prefs or not prefs.get('habits_reminder_enabled', True):
                    logger.debug(f"Habits reminders disabled for user {user['user_id']}")
                    continue
                
                await context.bot.send_message(
                    chat_id=user['user_id'],
                    text=reminder_text,
                    parse_mode="Markdown",
                    reply_markup=reply_markup
                )
                sent_count += 1
            except Exception as e:
                logger.debug(f"Could not send habits reminder to user {user['user_id']}: {e}")
        
        logger.info(f"Habits reminders sent to {sent_count} users")
    
    except Exception as e:
        logger.error(f"Error sending habits reminders: {e}")

async def send_shake_credit_reminders(context: ContextTypes.DEFAULT_TYPE):
    """
    Send payment reminders for shake orders on credit terms
    Runs daily at 11:00 AM
    Checks for overdue payments and sends reminders to users
    """
    try:
        logger.info("Checking for overdue shake credit payments...")
        
        from src.database.shake_operations import get_pending_credit_shake_orders
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        # Get all pending credit-based shake orders
        pending_orders = get_pending_credit_shake_orders()
        
        if not pending_orders:
            logger.info("No pending credit shake orders requiring reminders")
            return
        
        sent_count = 0
        for order in pending_orders:
            try:
                user_id = order.get('user_id')
                shake_id = order.get('shake_request_id') or order.get('request_id')
                flavor_name = order.get('flavor_name', f"Flavor #{order.get('flavor_id')}")
                due_date = order.get('payment_due_date')
                overdue_count = order.get('overdue_reminder_count', 0)
                
                # Skip if already sent too many reminders (max 3)
                if overdue_count >= 3:
                    logger.info(f"Skipping user {user_id} shake {shake_id} - max reminders sent")
                    continue
                
                # Create reminder message
                reminder_text = (
                    "💳 *PAYMENT REMINDER - Shake Order*\n\n"
                    f"🥤 *Flavor:* {flavor_name}\n"
                    f"📋 *Order ID:* #{shake_id}\n"
                    f"📅 *Due Date:* {due_date}\n"
                    f"⚠️ *Status:* PAYMENT OVERDUE\n\n"
                    "Your shake order payment is overdue.\n"
                    "Please confirm payment to clear this reminder.\n\n"
                    "💳 Click below to confirm payment:"
                )
                
                keyboard = [
                    [InlineKeyboardButton("✅ Mark as Paid", callback_data=f"user_paid_shake_{shake_id}")],
                ]
                
                # Render template and prefer template buttons; fall back to existing keyboard
                from src.utils.event_dispatcher import render_event
                rendered, tpl_buttons = render_event('PAYMENT_REMINDER_1', {'name': user.get('full_name'), 'amount': f"₹{order.get('amount')}", 'due_date': None})
                final_markup = InlineKeyboardMarkup(keyboard)
                if tpl_buttons:
                    try:
                        km = []
                        for row in tpl_buttons:
                            r = []
                            for b in row:
                                r.append(InlineKeyboardButton(b.get('text','Button'), callback_data=b.get('callback_data','')))
                            km.append(r)
                        final_markup = InlineKeyboardMarkup(km)
                    except Exception:
                        pass

                await context.bot.send_message(
                    chat_id=user_id,
                    text=rendered or reminder_text,
                    reply_markup=final_markup,
                    parse_mode="Markdown"
                )
                # Schedule follow-ups for payment reminders
                try:
                    from src.utils.event_dispatcher import schedule_followups
                    if context and getattr(context, 'application', None):
                        schedule_followups(context.application, user_id, 'PAYMENT_REMINDER_1', {'name': user.get('full_name'), 'amount': order.get('amount')})
                except Exception:
                    logger.debug('Could not schedule follow-ups for PAYMENT_REMINDER_1')
                
                # Update reminder count with guard to avoid over-incrementing
                from src.database.connection import execute_query
                update_sql = (
                    "UPDATE shake_requests SET overdue_reminder_count = COALESCE(overdue_reminder_count,0) + 1 "
                    "WHERE shake_request_id = %s AND COALESCE(overdue_reminder_count,0) < 3"
                )
                rows_affected = execute_query(update_sql, (shake_id,))
                # Only count/send if we actually incremented the counter
                if not rows_affected or rows_affected <= 0:
                    logger.info(f"Skipping increment for shake {shake_id} (already at max reminders)")
                    continue
                
                sent_count += 1
            except Exception as e:
                logger.debug(f"Could not send reminder to user {order.get('user_id')}: {e}")
        
        logger.info(f"Shake credit payment reminders sent to {sent_count} users")
    
    except Exception as e:
        logger.error(f"Error sending shake credit reminders: {e}")


async def send_receivables_reminders(context: ContextTypes.DEFAULT_TYPE):
    """
    Send daily reminders for overdue accounts receivable to admins.
    """
    try:
        from src.database.ar_operations import get_overdue_receivables
        overdue = get_overdue_receivables()
        if not overdue:
            logger.info("No overdue receivables today")
            return
        count = len(overdue)
        msg = (
            "💳 *Overdue Receivables Summary*\n\n"
            f"Total overdue items: {count}\n"
            "Use Admin → 📤 Export Overdue to download CSV."
        )
        if SUPER_ADMIN_USER_ID:
            await context.bot.send_message(
                chat_id=int(SUPER_ADMIN_USER_ID),
                text=msg,
                parse_mode="Markdown"
            )
            logger.info(f"Receivables summary sent to admin: {count} items")
    except Exception as e:
        logger.error(f"Error sending receivables reminders: {e}")


# ==================== CHALLENGE SYSTEM JOBS ====================

async def broadcast_challenge_starts(context: ContextTypes.DEFAULT_TYPE):
    """
    Broadcast challenges that are scheduled to start today at midnight
    Runs daily at 00:05 AM
    """
    try:
        from src.database.challenges_operations import (
            get_scheduled_challenges, mark_challenge_broadcast_sent
        )
        from src.database.user_operations import get_all_active_users
        
        logger.info("Checking for challenges scheduled to start today...")
        
        # Get challenges scheduled for today
        challenges = get_scheduled_challenges()
        
        if not challenges:
            logger.info("No challenges scheduled to start today")
            return
        
        # Get all active/approved users for broadcasting
        active_users = get_all_active_users()
        
        if not active_users:
            logger.warning("No active users to broadcast to")
            return
        
        broadcast_count = 0
        for challenge in challenges:
            try:
                challenge_id = challenge['challenge_id']
                challenge_name = challenge['name']
                start_date = challenge['start_date']
                end_date = challenge['end_date']
                is_free = challenge['is_free']
                price = challenge['price']
                
                # Format price
                price_str = "FREE" if is_free else f"Rs. {price}"
                
                # Build broadcast message with cutoff info
                message = f"""🏆 NEW CHALLENGE STARTING TODAY!

📋 {challenge_name}
📅 Duration: {start_date} - {end_date}
💰 Entry Fee: {price_str}

⏰ IMPORTANT: Daily Cutoff - 8:00 PM
🕗 All activities must be logged before 8:00 PM daily:
   • Weight logs
   • Water intake
   • Meals & Habits
   • Gym check-ins

Points calculated at 10:00 PM each night!

Join now: /challenges
"""
                
                # Send to each active user
                for user in active_users:
                    try:
                        await context.bot.send_message(
                            chat_id=user['user_id'],
                            text=message,
                            parse_mode="HTML"
                        )
                    except Exception as e:
                        logger.debug(f"Could not send challenge broadcast to user {user['user_id']}: {e}")
                
                # Mark challenge as broadcast sent and set to active
                mark_challenge_broadcast_sent(challenge_id)
                logger.info(f"Challenge {challenge_id} broadcast completed")
                broadcast_count += 1
                
            except Exception as e:
                logger.error(f"Error broadcasting challenge {challenge.get('challenge_id')}: {e}")
        
        logger.info(f"Challenge broadcasts completed for {broadcast_count} challenges")
    
    except Exception as e:
        logger.error(f"Error in broadcast_challenge_starts: {e}")


async def hide_expired_events(context: ContextTypes.DEFAULT_TYPE):
    """
    Hide or expire events whose end_date is before today.
    Runs daily to ensure expired events are not shown in active listings.
    """
    try:
        logger.info("Checking for expired events to hide...")
        from src.database.connection import execute_query

        # Mark events as expired if end_date < CURRENT_DATE and status='active'
        update_sql = """
            UPDATE events
            SET status = 'expired', updated_at = NOW()
            WHERE status = 'active' AND end_date IS NOT NULL AND end_date < CURRENT_DATE
            RETURNING event_id
        """
        rows = execute_query(update_sql)
        count = len(rows) if rows else 0
        if count > 0:
            logger.info(f"Marked {count} events as expired")
            # Notify admin
            from src.config import SUPER_ADMIN_USER_ID
            if SUPER_ADMIN_USER_ID:
                await context.bot.send_message(
                    chat_id=int(SUPER_ADMIN_USER_ID),
                    text=f"⚠️ {count} events marked expired and hidden from listings.",
                    parse_mode="Markdown"
                )
        else:
            logger.info("No events to expire today")
    except Exception as e:
        logger.error(f"Error hiding expired events: {e}")


async def process_daily_challenge_points(context: ContextTypes.DEFAULT_TYPE):
    """
    Process daily challenge points and updates at 10:00 PM
    - Calculate points for all challenge participants
    - Update leaderboards
    - Check for weekly bonuses
    - Send daily summaries
    """
    try:
        from src.database.challenges_operations import (
            get_active_challenges, get_challenge_participants,
            update_participant_daily_progress, add_participant_points
        )
        from src.utils.challenge_points import (
            get_user_daily_activities, award_challenge_points, 
            check_and_award_weekly_bonus, CHALLENGE_POINTS_CONFIG
        )
        
        logger.info("Starting daily challenge point processing...")
        
        active_challenges = get_active_challenges()
        
        if not active_challenges:
            logger.info("No active challenges for point processing")
            return
        
        total_points_awarded = 0
        total_users_processed = 0
        
        for challenge in active_challenges:
            challenge_id = challenge['challenge_id']
            challenge_name = challenge['name']
            
            try:
                # Get all active participants
                participants = get_challenge_participants(challenge_id, status='active')
                
                if not participants:
                    logger.debug(f"No active participants for challenge {challenge_id}")
                    continue
                
                for participant in participants:
                    user_id = participant['user_id']
                    user_name = participant.get('full_name', f"User {user_id}")
                    
                    try:
                        from datetime import datetime
                        today = datetime.now().date()
                        
                        # Get user's daily activities
                        activities = get_user_daily_activities(user_id, today)
                        
                        daily_points = 0
                        daily_summary = []
                        
                        # Award points for each activity
                        if activities['checkin']:
                            weekly_count = get_weekly_checkin_count(user_id)
                            points = award_challenge_points(
                                user_id, challenge_id, 'checkin',
                                metadata={'weekly_checkins': weekly_count}
                            )
                            daily_points += points
                            daily_summary.append(f"✅ Check-in: +{points} pts")
                        
                        if activities['water_ml'] > 0:
                            points = award_challenge_points(
                                user_id, challenge_id, 'water',
                                quantity=activities['water_ml']
                            )
                            daily_points += points
                            daily_summary.append(f"💧 Water: +{points} pts")
                        
                        if activities['weight_logged']:
                            points = award_challenge_points(
                                user_id, challenge_id, 'weight'
                            )
                            daily_points += points
                            daily_summary.append(f"⚖️ Weight: +{points} pts")
                        
                        if activities['habits_count'] > 0:
                            points = award_challenge_points(
                                user_id, challenge_id, 'habits',
                                quantity=activities['habits_count']
                            )
                            daily_points += points
                            daily_summary.append(f"✨ Habits ({activities['habits_count']}): +{points} pts")
                        
                        # Update daily progress
                        update_participant_daily_progress(
                            user_id, challenge_id,
                            str(today),
                            {
                                'points': daily_points,
                                'activities': activities,
                                'summary': ', '.join(daily_summary) if daily_summary else 'No activities'
                            }
                        )
                        
                        # Check for weekly bonus
                        bonus_result = check_and_award_weekly_bonus(user_id)
                        if bonus_result['awarded']:
                            daily_points += bonus_result['points']
                            daily_summary.append(f"🎉 Weekly Bonus: +{bonus_result['points']} pts")
                        
                        if daily_points > 0:
                            # Notify user of daily points
                            try:
                                summary_text = f"""📊 Daily Points in {challenge_name}

{chr(10).join(daily_summary)}

🏆 Total Today: +{daily_points} pts"""
                                
                                await context.bot.send_message(
                                    chat_id=user_id,
                                    text=summary_text,
                                    parse_mode="HTML"
                                )
                            except Exception as e:
                                logger.debug(f"Could not send daily summary to user {user_id}: {e}")
                        
                        total_points_awarded += daily_points
                        total_users_processed += 1
                        
                    except Exception as e:
                        logger.error(f"Error processing points for user {user_id} in challenge {challenge_id}: {e}")
                
            except Exception as e:
                logger.error(f"Error processing challenge {challenge_id}: {e}")
        
        logger.info(f"Daily challenge processing complete: {total_users_processed} users, {total_points_awarded} points awarded")
    
    except Exception as e:
        logger.error(f"Error in process_daily_challenge_points: {e}")


async def send_challenge_payment_reminders(context: ContextTypes.DEFAULT_TYPE):
    """
    Send daily payment reminders for unpaid/partial challenge entry fees
    Runs daily at 10:00 AM
    """
    try:
        from src.database.challenge_payment_operations import get_unpaid_challenge_participants
        
        logger.info("Sending challenge payment reminders...")
        
        unpaid_participants = get_unpaid_challenge_participants()
        
        if not unpaid_participants:
            logger.info("No unpaid challenge participants requiring reminders")
            return
        
        sent_count = 0
        for participant in unpaid_participants:
            try:
                user_id = participant['user_id']
                challenge_name = participant['challenge_name']
                amount_due = float(participant['amount_due']) if participant['amount_due'] else 0
                due_date = participant['due_date']
                payment_status = participant['payment_status']
                
                if amount_due <= 0:
                    continue  # Skip if nothing due
                
                reminder_text = f"""⚠️ Payment Reminder

Challenge: {challenge_name}
💰 Amount Due: Rs. {amount_due}
📅 Due Date: {due_date}
Status: {payment_status.upper()}

Please complete your payment to continue participating in the challenge.

Use /view_receivables to see payment details.
"""
                
                await context.bot.send_message(
                    chat_id=user_id,
                    text=reminder_text,
                    parse_mode="HTML"
                )
                sent_count += 1
                
            except Exception as e:
                logger.debug(f"Could not send reminder to user {participant.get('user_id')}: {e}")
        
        logger.info(f"Challenge payment reminders sent to {sent_count} users")
    
    except Exception as e:
        logger.error(f"Error in send_challenge_payment_reminders: {e}")


def get_weekly_checkin_count(user_id: int) -> int:
    """
    Get user's check-in count for current week
    Helper function for daily processing
    """
    try:
        from src.database.connection import DatabaseConnection
        db = DatabaseConnection()
        
        query = """
            SELECT COUNT(*) as count
            FROM attendance_queue
            WHERE user_id = %s
            AND status = 'approved'
            AND approved_at >= DATE_TRUNC('week', CURRENT_DATE)
            AND approved_at < DATE_TRUNC('week', CURRENT_DATE) + INTERVAL '7 days'
        """
        
        result = db.execute_query(query, (user_id,))
        return result['count'] if result else 0
    except Exception as e:
        logger.error(f"Error getting weekly check-in count: {e}")
        return 0
