import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from src.database.user_operations import user_exists, create_user, get_user, is_user_banned
from src.database.attendance_operations import (
    create_attendance_request, get_user_attendance_today, approve_attendance
)
from src.config import SUPER_ADMIN_USER_ID, POINTS_CONFIG, GEOFENCE_LAT, GEOFENCE_LNG, GEOFENCE_RADIUS_M
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
from src.utils.geo import haversine_distance_m
from src.database.activity_operations import get_user_points, get_leaderboard
from src.handlers.role_keyboard_handlers import show_role_menu
from src.utils.auth import is_admin_id
from src.utils.role_notifications import get_moderator_chat_ids
from src.utils.guards import check_registration, check_approval
from src.database.subscription_operations import (
    get_user_subscription, is_subscription_active, is_in_grace_period
)
from src.utils.callback_utils import safe_answer_callback_query

logger = logging.getLogger(__name__)

# Conversation states
NAME, PHONE, AGE, WEIGHT, GENDER, PROFILE_PIC = range(6)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show rich welcome with a Register button; do not start registration yet."""
    msg = update.effective_message
    user_id = update.effective_user.id
    payload = context.args[0] if context.args else None
    
    # Set commands based on user's role (async, doesn't block)
    try:
        from src.bot import set_commands_for_user
        context.application.create_task(set_commands_for_user(user_id, context.bot))
    except Exception as e:
        logger.warning(f"Could not set user commands: {e}")
    
    # Check if user is banned - block access
    if user_exists(user_id) and is_user_banned(user_id):
        await msg.reply_text(
            "🚫 *Account Blocked*\n\n"
            "Your account has been banned and you cannot access the app.\n"
            "Contact support for more information.",
            parse_mode="Markdown"
        )
        return ConversationHandler.END
    
    # Handle studio check-in payload from QR deep link first
    if payload == "studio_checkin":
        # Geofenced check-in: request user location first
        if not user_exists(user_id):
            buttons = InlineKeyboardMarkup([[InlineKeyboardButton("🚀 Register Now", callback_data="register")]])
            await msg.reply_text(
                "You scanned the studio check-in QR. Please register first to log attendance.",
                reply_markup=buttons,
            )
            return ConversationHandler.END

        if not (GEOFENCE_LAT and GEOFENCE_LNG):
            await msg.reply_text("❌ Geofence not configured. Contact admin.")
            return ConversationHandler.END

        keyboard = ReplyKeyboardMarkup(
            [[KeyboardButton(text="📍 Share Location", request_location=True)]],
            one_time_keyboard=True,
            resize_keyboard=True,
        )
        context.user_data['awaiting_geo_checkin'] = True
        await msg.reply_text(
            "Please share your location to complete check-in (10m radius).",
            reply_markup=keyboard,
        )
        return ConversationHandler.END

    # Allow admins to bypass registration entirely
    if is_admin_id(user_id) and not user_exists(user_id):
        await msg.reply_text(
            "🛡️ Admin access granted. Registration not required. Opening admin menu..."
        )
        await show_role_menu(update, context)
        return ConversationHandler.END

    # No payload path: greet existing users or show welcome for new
    if user_exists(user_id):
        user = get_user(user_id)
        
        # Check subscription status for regular users
        if not is_admin_id(user_id):
            sub = get_user_subscription(user_id)
            
            if not sub or not is_subscription_active(user_id):
                # Check if in grace period
                if is_in_grace_period(user_id):
                    await msg.reply_text(
                        f"⚠️ Welcome back, {user['full_name']}!\n\n"
                        "🔔 Your subscription has expired but you're in the grace period.\n\n"
                        "Please renew your subscription to continue using the app.\n"
                        "Use /subscribe to renew now!",
                        parse_mode="Markdown"
                    )
                else:
                    # No subscription or expired past grace period
                    keyboard = InlineKeyboardMarkup([
                        [InlineKeyboardButton("💪 Subscribe Now", callback_data="start_subscribe")]
                    ])
                    await msg.reply_text(
                        f"Hello {user['full_name']}! 👋\n\n"
                        "🔒 To access the fitness club app, you need an active subscription.\n\n"
                        "Choose a subscription plan to unlock:\n"
                        "• Activity tracking\n"
                        "• Weight tracking\n"
                        "• Challenge participation\n"
                        "• Shake orders\n"
                        "• And much more!\n\n"
                        "Tap below to get started 👇",
                        reply_markup=keyboard
                    )
                return ConversationHandler.END
        
        await msg.reply_text(
            f"Welcome back, {user['full_name']}! 👋\n\n"
            "Tap Admin/Staff/User buttons via /menu to navigate."
        )
        return ConversationHandler.END

    welcome_text = (
        "🏋️ *Welcome to Wani's Level Up Club!* 💪\n"
        "✨ *A Herbalife Fitness Studio where Transformation Meets Community!*\n\n"
        "Hey there, Champion! 👋\n"
        "You've just taken the first step toward a healthier, stronger YOU! 🌱\n\n"
        "At Wani's Level Up Club, we believe fitness isn't just about workouts — it's a lifestyle.\n"
        "Here's what awaits you inside ⤵️\n\n"
        "🔥 *Community Workouts* – Feel the energy, train together, grow together!\n"
        "🏋️‍♂️ *Personal Training (PT)* – Custom guidance to help you smash your goals\n"
        "🥤 *Herbalife Nutrition & Shakes* – Fuel your fitness with science-backed nutrition\n"
        "🤝 *Supportive Community* – Stay motivated with like-minded achievers\n\n"
        "Let's get started! 🚀\n"
        "Tap below to register and begin your Level Up journey today 👇"
    )
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Register Now", callback_data="register")]
    ])
    await msg.reply_text(welcome_text, reply_markup=buttons, parse_mode='Markdown')
    return ConversationHandler.END


async def handle_location_for_checkin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.location:
        return
    user_id = message.from_user.id
    if not context.user_data.get('awaiting_geo_checkin'):
        return

    context.user_data.pop('awaiting_geo_checkin', None)
    user_location = message.location
    try:
        lat_u = float(user_location.latitude)
        lng_u = float(user_location.longitude)
        lat_c = float(GEOFENCE_LAT)
        lng_c = float(GEOFENCE_LNG)
        radius_m = float(GEOFENCE_RADIUS_M or 10)
    except Exception:
        await message.reply_text("❌ Invalid geofence. Contact admin.", reply_markup=ReplyKeyboardRemove())
        return

    distance = haversine_distance_m(lat_u, lng_u, lat_c, lng_c)
    if distance > radius_m:
        await message.reply_text(
            f"⛔ Out of range ({int(distance)} m). Be near the studio.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    already = get_user_attendance_today(user_id)
    if already and (already.get('status') in ('pending', 'approved')):
        await message.reply_text("📌 Attendance already recorded for today.", reply_markup=ReplyKeyboardRemove())
        return

    created = create_attendance_request(user_id, photo_url=None)
    if not created:
        await message.reply_text("❌ Failed to record attendance. Please try again.", reply_markup=ReplyKeyboardRemove())
        return

    user = get_user(user_id)
    fee_status = (user.get('fee_status') or '').lower()
    if fee_status in ("paid", "active"):
        try:
            attendance_id = created.get('attendance_id')
            if attendance_id is not None:
                approve_attendance(attendance_id, int(SUPER_ADMIN_USER_ID or 0))
                pts = POINTS_CONFIG.get('attendance', 0)
                await message.reply_text(
                    f"✅ Attendance logged and approved. +{pts} points awarded!",
                    reply_markup=ReplyKeyboardRemove(),
                )
                return
        except Exception:
            pass
        await message.reply_text("✅ Attendance logged. Awaiting approval.", reply_markup=ReplyKeyboardRemove())
        # Notify moderators for manual approval with instant buttons
        attendance_id = created.get('attendance_id')
        user_phone = user.get('phone', 'N/A')
        
        for chat_id in get_moderator_chat_ids(include_staff=True):
            try:
                notification_text = (
                    "🔔 *NEW GYM CHECK-IN REQUEST*\n\n"
                    f"👤 *User:* {user['full_name']}\n"
                    f"📱 *ID:* {user_id}\n"
                    f"📞 *Phone:* {user_phone}\n"
                    f"📅 *Date:* {created.get('request_date')}\n"
                    f"🏢 *Attendance ID:* {attendance_id}\n\n"
                    "⏳ *Status:* PENDING YOUR APPROVAL\n\n"
                    "Click buttons below to approve or reject:"
                )
                
                keyboard = [
                    [InlineKeyboardButton("✅ Approve", callback_data=f"approve_attend_{attendance_id}"),
                     InlineKeyboardButton("❌ Reject", callback_data=f"reject_attend_{attendance_id}")],
                ]
                
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=notification_text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Failed to notify moderator {chat_id} for attendance: {e}")
        return

    await message.reply_text("📝 Attendance recorded. Pending approval (membership inactive).", reply_markup=ReplyKeyboardRemove())
    attendance_id = created.get('attendance_id')
    user_phone = user.get('phone', 'N/A')
    
    for chat_id in get_moderator_chat_ids(include_staff=True):
        try:
            notification_text = (
                "🔔 *NEW GYM CHECK-IN REQUEST (INACTIVE)*\n\n"
                f"👤 *User:* {user['full_name']}\n"
                f"📱 *ID:* {user_id}\n"
                f"📞 *Phone:* {user_phone}\n"
                f"📅 *Date:* {created.get('request_date')}\n"
                f"🏢 *Attendance ID:* {attendance_id}\n\n"
                "⚠️ *Note:* User has inactive/expired membership\n"
                "⏳ *Status:* PENDING YOUR APPROVAL\n\n"
                "Click buttons below to approve or reject:"
            )
            
            keyboard = [
                [InlineKeyboardButton("✅ Approve", callback_data=f"approve_attend_{attendance_id}"),
                 InlineKeyboardButton("❌ Reject", callback_data=f"reject_attend_{attendance_id}")],
            ]
            
            await context.bot.send_message(
                chat_id=chat_id,
                text=notification_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Failed to notify moderator {chat_id} for attendance: {e}")
    return

async def begin_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point for registration via /register or register button."""
    msg = update.effective_message
    user_id = update.effective_user.id

    if user_exists(user_id):
        user = get_user(user_id)
        await msg.reply_text(
            f"Welcome back, {user['full_name']}! 👋\n\nUse /menu to see options."
        )
        return ConversationHandler.END

    await msg.reply_text(
        "**Step 1/5:** What's your full name?",
        parse_mode='Markdown'
    )
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text
    await update.message.reply_text(
        "**Step 2/5:** What's your phone number?\n"
        "(Format: +91XXXXXXXXXX)",
        parse_mode='Markdown'
    )
    return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['phone'] = update.message.text
    await update.message.reply_text("**Step 3/5:** How old are you?", parse_mode='Markdown')
    return AGE

async def get_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        age = int(update.message.text)
        if age < 10 or age > 100:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Please enter a valid age (10-100).")
        return AGE
    
    context.user_data['age'] = age
    await update.message.reply_text(
        "**Step 4/5:** What's your current weight? (in kg)",
        parse_mode='Markdown'
    )
    return WEIGHT

async def get_weight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        weight = float(update.message.text)
        if weight <= 0 or weight > 300:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Please enter a valid weight.")
        return WEIGHT
    
    context.user_data['weight'] = weight
    keyboard = [
        ["Male"],
        ["Female"],
        ["Trans"]
    ]
    await update.message.reply_text(
        "**Step 5/6:** What is your gender?",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True),
        parse_mode='Markdown'
    )
    return GENDER

async def get_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    gender = update.message.text.strip()
    if gender not in ["Male", "Female", "Trans"]:
        keyboard = [
            ["Male"],
            ["Female"],
            ["Trans"]
        ]
        await update.message.reply_text(
            "Please select: Male, Female, or Trans",
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        )
        return GENDER
    
    context.user_data['gender'] = gender
    await update.message.reply_text(
        "**Step 6/6:** 📸 *Profile Picture Required*\n\n"
        "🔴 *Profile picture is MANDATORY to proceed.*\n\n"
        "Please upload your profile picture now.",
        parse_mode='Markdown'
    )
    return PROFILE_PIC

async def get_profile_pic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Capture profile picture from user"""
    user_id = update.effective_user.id
    username = update.effective_user.username
    profile_pic_url = None
    
    # Check if user sent a photo
    if update.message.photo:
        # Get the file ID from Telegram (this is persistent)
        photo = update.message.photo[-1]  # Get highest resolution
        # Store the file_id instead of file_path - file_id is persistent
        profile_pic_url = photo.file_id
        await update.message.reply_text("✅ Profile picture saved!")
    else:
        await update.message.reply_text(
            "❌ *Profile picture is required!*\n\n"
            "🔴 You must upload a photo to continue registration.\n\n"
            "Please send your profile picture now.",
            parse_mode='Markdown'
        )
        return PROFILE_PIC
    
    try:
        result = create_user(
            user_id=user_id,
            username=username,
            full_name=context.user_data['name'],
            phone=context.user_data['phone'],
            age=context.user_data['age'],
            initial_weight=context.user_data['weight'],
            gender=context.user_data.get('gender'),
            profile_pic_url=profile_pic_url
        )

        # Success message - send defensively (Markdown first, then plain text fallback)
        user_confirmation_text_md = (
            "🎉 *Registration Successful!*\n\n"
            f"Name: {context.user_data['name']}\n"
            f"Referral Code: {result['referral_code']}\n\n"
            "Now let's get you subscribed to unlock full access!\n\n"
            "Tap /subscribe to choose your subscription plan."
        )

        user_confirmation_text_plain = (
            "🎉 Registration Successful!\n\n"
            f"Name: {context.user_data['name']}\n"
            f"Referral Code: {result['referral_code']}\n\n"
            "Now let's get you subscribed to unlock full access!\n\n"
            "Tap /subscribe to choose your subscription plan."
        )

        try:
            await update.message.reply_text(user_confirmation_text_md, parse_mode='Markdown')
        except Exception as e:
            logger.warning(f"Could not send Markdown registration reply to user {user_id}: {e} - sending plain text instead")
            try:
                await update.message.reply_text(user_confirmation_text_plain)
            except Exception as e2:
                logger.error(f"Failed to send any registration confirmation to user {user_id}: {e2}")

        # Forward profile photo and user details to all admins (run regardless of user message success)
        try:
            from src.handlers.admin_handlers import get_admin_ids
            from datetime import datetime

            admin_ids = get_admin_ids()
            logger.info(f"Profile saved: Found {len(admin_ids)} admins to notify")

            admin_message = (
                f"*👤 New Profile Registration*\n\n"
                f"Name: {context.user_data['name']}\n"
                f"Phone: {context.user_data['phone']}\n"
                f"Age: {context.user_data['age']}\n"
                f"Weight: {context.user_data['weight']} kg\n"
                f"Gender: {context.user_data.get('gender', 'N/A')}\n"
                f"Telegram ID: {user_id}\n"
                f"Username: @{username if username else 'Not set'}\n"
                f"Referral Code: {result['referral_code']}\n"
                f"Registered: {datetime.now().strftime('%d-%m-%Y %H:%M')}\n\n"
                f"✅ Profile saved successfully!"
            )

            if not admin_ids:
                logger.warning("No admins found to notify about new profile")
            else:
                for admin_id in admin_ids:
                    try:
                        # Send profile photo with user details
                        if profile_pic_url:
                            try:
                                await context.bot.send_photo(
                                    chat_id=admin_id,
                                    photo=profile_pic_url,
                                    caption=admin_message,
                                    parse_mode="Markdown"
                                )
                                logger.info(f"✅ Profile photo notification sent to admin {admin_id} for user {user_id}")
                            except Exception as pic_error:
                                logger.debug(f"Could not send profile photo, sending text only: {pic_error}")
                                try:
                                    await context.bot.send_message(
                                        chat_id=admin_id,
                                        text=admin_message,
                                        parse_mode="Markdown"
                                    )
                                except Exception:
                                    # If Markdown fails for admin, send plain text
                                    await context.bot.send_message(
                                        chat_id=admin_id,
                                        text=admin_message
                                    )
                        else:
                            try:
                                await context.bot.send_message(
                                    chat_id=admin_id,
                                    text=admin_message,
                                    parse_mode="Markdown"
                                )
                            except Exception:
                                await context.bot.send_message(
                                    chat_id=admin_id,
                                    text=admin_message
                                )
                    except Exception as e:
                        logger.error(f"❌ Failed to send profile notification to admin {admin_id}: {e}")
        except Exception as e:
            logger.error(f"Error sending profile notification to admins: {e}")
        
        # End registration conversation - user will use /subscribe command
        # Admin approval will happen after subscription and payment is complete
        return ConversationHandler.END

    except Exception as e:
        logger.error(f"Registration failed for user {user_id}: {e}")
        await update.message.reply_text(
            "❌ Registration failed. Please tap /start to try again.\n"
            "If it keeps failing, share this with admin so we can fix it."
        )
        context.user_data.clear()
        return ConversationHandler.END

async def cancel_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Registration cancelled.")
    context.user_data.clear()
    return ConversationHandler.END

async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Check if approved
    if not await check_approval(update, context):
        return
    
    # Auto-detect role and show role-specific menu with inline buttons
    await show_role_menu(update, context)


async def cmd_qrcode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send user's gym login QR code."""
    user_id = update.effective_user.id
    
    # Check if approved first
    if not await check_approval(update, context):
        return
    
    # Handle both command and callback contexts
    if update.callback_query:
        await update.callback_query.answer()
        message = update.callback_query.message
    else:
        message = update.message
    
    await message.reply_text(
        "✅ Registered successfully!\n\n"
        "Your profile is ready. Tap /subscribe to choose a subscription plan.",
        parse_mode='Markdown'
    )


async def handle_greeting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Hi/Hello greetings and show personalized menu with role-based buttons."""
    user_id = update.effective_user.id
    
    # If not registered, prompt registration
    if not user_exists(user_id):
        buttons = InlineKeyboardMarkup([[InlineKeyboardButton("🚀 Register Now", callback_data="register")]])
        await update.message.reply_text(
            "👋 Hello! I'm Wani's Level Up Club Bot.\n\nPlease register first to get started.",
            reply_markup=buttons,
        )
        return
    
    # Registered user: greet by name and show menu
    user = get_user(user_id)
    name = user.get('full_name', 'Friend')
    
    greeting = (
        f"👋 Hey {name}! 😊\n\n"
        "How can I help you today? Here are your options:"
    )
    
    await update.message.reply_text(greeting)
    
    # Show role-based menu with buttons
    await show_role_menu(update, context)

def build_points_chart_text():
    """Build formatted points chart for all activities"""
    chart = "📊 *Points Earning Guide*\n\n"
    chart += "Here's how to earn points for each activity:\n\n"
    
    # Get points config
    activities = [
        ("🏋️ Gym Attendance", POINTS_CONFIG.get('attendance', 50), "1 checkin = 1 attendance record"),
        ("⚖️ Weight Log", POINTS_CONFIG.get('weight_log', 10), "Unlimited daily logs"),
        ("💧 Water Intake", POINTS_CONFIG.get('water_500ml', 5), "Per 500ml cup logged"),
        ("🍽️ Meal Photo", POINTS_CONFIG.get('meal_photo', 15), "Up to 4 per day"),
        ("💪 Daily Habits", POINTS_CONFIG.get('habits_complete', 20), "Complete habits get 5pts each"),
        ("🎉 Weekly Bonus", 200, "6+ days attendance in 7 days (excl. Sunday)"),
    ]
    
    for activity, points, notes in activities:
        chart += f"{activity}\n"
        chart += f"  💰 {points} points\n"
        chart += f"  📝 {notes}\n\n"
    
    chart += "💡 *Pro Tips:*\n"
    chart += "• Complete all daily habits for consistent points\n"
    chart += "• Attend 6+ days weekly to unlock 200 bonus points\n"
    chart += "• Consistent logging improves your profile\n\n"
    chart += "🏆 Top earners get featured in leaderboard!"
    
    return chart


async def cmd_points_chart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show points chart for all activities"""
    # Handle both command and callback contexts
    if update.callback_query:
        await update.callback_query.answer()
        message = update.callback_query.message
    else:
        message = update.message
    
    user_id = update.effective_user.id
    
    if not user_exists(user_id):
        await message.reply_text("You're not registered. Use /start")
        return
    
    chart_text = build_points_chart_text()
    
    await message.reply_text(
        chart_text,
        parse_mode='Markdown'
    )


def build_studio_rules_text():
    """Build formatted studio rules and regulations"""
    rules = "📋 *Studio Rules & Regulations*\n\n"
    
    rules += "✅ *Studio Hours:*\n"
    rules += "• Monday - Saturday: Open\n"
    rules += "• Sunday: CLOSED (Holiday)\n\n"
    
    rules += "🕐 *Batch Timings:*\n"
    rules += "• Saturday: Morning batches only (specific times)\n"
    rules += "• Other Days: Full day operations\n\n"
    
    rules += "👟 *Dress Code:*\n"
    rules += "• Indoor shoes REQUIRED for gym floor\n"
    rules += "• Outdoor shoes NOT allowed inside\n"
    rules += "• Proper workout attire expected\n\n"
    
    rules += "🏋️ *Facility Rules:*\n"
    rules += "• Hand towel MUST be carried\n"
    rules += "• Wipe equipment after use\n"
    rules += "• Maintain proper hygiene\n\n"
    
    rules += "🤝 *Code of Conduct:*\n"
    rules += "• Be polite and respectful to all members\n"
    rules += "• No smoking inside facility\n"
    rules += "• Keep noise levels reasonable\n"
    rules += "• Follow staff instructions\n\n"
    
    rules += "📢 *Important:*\n"
    rules += "Studio timing and rules may change. You'll be notified\n"
    rules += "via announcements if there are any updates.\n\n"
    
    rules += "❓ Questions? Contact staff members for clarification."
    
    return rules


async def cmd_studio_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show studio rules and regulations"""
    # Handle both command and callback contexts
    if update.callback_query:
        await safe_answer_callback_query(update)
        message = update.callback_query.message
    else:
        message = update.message
    
    user_id = update.effective_user.id
    
    if not user_exists(user_id):
        await message.reply_text("You're not registered. Use /start")
        return
    
    rules_text = build_studio_rules_text()
    
    await message.reply_text(
        rules_text,
        parse_mode='Markdown'
    )