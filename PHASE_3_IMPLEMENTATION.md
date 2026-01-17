# Phase 3: Payment System, Analytics & Challenges
## Implementation Guide

### Overview
Phase 3 introduces monetization (membership fees), comprehensive analytics/reporting, user challenges/competitions, and a notification system. This phase enables gym revenue tracking, member management, and gamification features.

---

## Phase 3 Architecture

### Database Modules Created

#### 1. `src/database/payment_operations.py` (11 Functions)
**Purpose:** Manage membership fees, payment records, and member status

**Key Functions:**
- `get_user_fee_status(user_id)` - Check if member is paid/active
- `record_fee_payment(user_id, amount, payment_method, duration_days)` - Record payment transaction
- `is_member_active(user_id)` - Validate active membership
- `get_pending_payments()` - List unpaid/expired members
- `get_payment_history(user_id, limit=10)` - User's payment record
- `get_revenue_stats()` - Total revenue, transaction count, average
- `get_monthly_revenue(month, year)` - Financial data by period
- `get_active_members_count()` - Count of paid members
- `get_expiring_memberships(days_ahead=7)` - Members expiring soon
- `extend_membership(user_id, duration_days)` - Extend expiry
- `revoke_membership(user_id, reason)` - Remove access

**Database Tables Used:**
- `users` (fee_status, fee_expiry_date)
- `fee_payments` (new table in Phase 1 schema)

---

#### 2. `src/database/statistics_operations.py` (9 Functions)
**Purpose:** Provide comprehensive analytics and user statistics

**Key Functions:**
- `get_user_statistics(user_id)` - Comprehensive stats (points, activity counts)
- `get_leaderboard_with_stats(limit=10)` - Ranked leaderboard with metrics
- `get_weight_progress(user_id, days=30)` - Weight tracking over time
- `get_consistency_stats(user_id)` - 30-day consistency metrics
- `get_top_activities()` - Most popular activities (frequency, points)
- `get_engagement_metrics()` - Platform engagement stats
- `get_weekly_comparison(user_id)` - Current vs previous week
- `get_attendance_streak(user_id)` - Current gym visit streak
- `get_platform_statistics()` - Overall platform stats

**Database Tables Used:**
- `users`, `user_activities`, `weight_logs`
- All activity and tracking tables

---

#### 3. `src/database/challenges_operations.py` (11 Functions)
**Purpose:** Manage user challenges and competitions

**Challenge Types:**
- `weight_loss` - Achieve weight loss target
- `consistency` - Log activities daily
- `water_challenge` - Daily water intake goal
- `gym_warrior` - Gym check-in frequency
- `meal_prep` - Meal preparation tracking

**Key Functions:**
- `create_challenge(challenge_type, start_date, duration_days)` - Create new challenge
- `join_challenge(user_id, challenge_id)` - User joins challenge
- `get_active_challenges()` - Current active challenges
- `get_user_challenges(user_id)` - User's participating challenges
- `get_challenge_progress(challenge_id, user_id)` - Calculate progress (type-specific logic)
- `get_challenge_leaderboard(challenge_id, limit=10)` - Challenge rankings
- `award_challenge_reward(user_id, challenge_id, reward_points=100)` - Award completion points
- `get_challenge_stats()` - Challenge statistics
- `update_challenge_progress(user_id, challenge_id, progress_value)` - Update tracking

**Database Tables Used:**
- `challenges` (new table)
- `challenge_participants` (new table)

---

#### 4. `src/database/notifications_operations.py` (15 Functions)
**Purpose:** Manage user notifications and messaging

**Notification Types:**
1. `points_awarded` - Points earned
2. `attendance_approved` - Check-in approved
3. `payment_due` - Payment reminder
4. `membership_expired` - Membership expiry
5. `achievement_unlocked` - Badge/milestone
6. `challenge_reminder` - Challenge deadline
7. `leaderboard_update` - Ranking changes
8. `shake_ready` - Protein shake ready
9. `daily_reminder` - Engagement reminder

**Key Functions:**
- `create_notification(user_id, type, title, description, link_data)` - Create notification
- `get_user_notifications(user_id, unread_only=True, limit=20)` - Retrieve notifications
- `mark_notification_read(notification_id)` - Mark as read
- `mark_all_notifications_read(user_id)` - Bulk read
- `delete_notification(notification_id)` - Remove
- `get_unread_count(user_id)` - Count unread
- **Specific Senders:**
  - `send_points_notification(user_id, points)` - Award points
  - `send_attendance_approved_notification(user_id)` - Check-in approved
  - `send_payment_due_notification(user_id)` - Payment reminder
  - `send_membership_expired_notification(user_id)` - Expired alert
  - `send_achievement_notification(user_id, achievement)` - Achievement unlocked
  - `send_challenge_reminder(user_id, challenge_id)` - Challenge deadline
  - `send_leaderboard_notification(user_id)` - Ranking update
  - `send_daily_reminder(user_id)` - Engagement reminder
  - `send_shake_ready_notification(user_id)` - Shake ready
- `get_notification_stats()` - Statistics
- `cleanup_old_notifications(days=30)` - Maintenance

**Database Tables Used:**
- `notifications` (new table)

---

### Handler Modules Created

#### 1. `src/handlers/analytics_handlers.py` (8 Async Functions)
**Purpose:** Admin dashboard and reporting

**Routes:**
- `/admin_dashboard` → `cmd_admin_dashboard()` - Main dashboard
- Callbacks:
  - `💰 Revenue` → `callback_revenue_stats()` - Revenue report
  - `👥 Members` → `callback_member_stats()` - Member statistics
  - `📊 Engagement` → `callback_engagement_stats()` - Engagement metrics
  - `🏆 Challenges` → `callback_challenge_stats()` - Challenge statistics
  - `🔥 Top Activities` → `callback_top_activities()` - Popular activities
  - `↩️ Back` → `callback_admin_dashboard()` - Return to dashboard
  - Router: `handle_analytics_callback()` - Callback dispatcher

**Display Data:**
- Revenue: Total, transaction count, average payment, monthly breakdown
- Members: Total users, active members, average points, pending payments
- Engagement: Active users (30-day), paid members, total points
- Challenges: Active count, participation, completion rate
- Top Activities: Top 5 with frequency and points

---

#### 2. `src/handlers/payment_handlers.py` (12 Functions)
**Purpose:** Payment and membership management UI

**Commands/Callbacks:**
- `/payment_status` → `cmd_payment_status()` - Show payment status
- `/challenges` → `cmd_challenges()` - Show active challenges
- `💳 Pay Fee` → `callback_pay_fee()` - Start payment flow
- Payment flow (ConversationHandler):
  - `PAYMENT_AMOUNT` state - Select duration
  - `PAYMENT_METHOD` state - Select payment method
  - `PAYMENT_CONFIRM` state - Confirm payment

**Payment Options:**
- ₹500 for 30 days
- ₹1000 for 60 days
- ₹1500 for 90 days

**Payment Methods:**
- Card payment
- Bank transfer

**Additional Callbacks:**
- `callback_join_challenge()` - Join challenge
- `callback_challenge_leaderboard()` - View leaderboard
- `callback_close()` - Close dialog

---

#### 3. `src/handlers/challenge_handlers.py` (9 Functions)
**Purpose:** User challenge interface and participation

**Commands:**
- `/challenges` → `cmd_challenges()` - Show all challenges
- `/my_challenges` → `cmd_my_challenges()` - Show user's challenges

**Callbacks:**
- `challenge_view_<id>` → `callback_challenge_view()` - View details
- `challenge_join_<id>` → `callback_challenge_join()` - Join challenge
- `challenge_progress_<id>` → `callback_challenge_progress()` - Show progress
- `challenge_board_<id>` → `callback_challenge_leaderboard()` - Leaderboard
- `challenge_back` → `callback_challenge_back()` - Back to list
- `challenge_close` → `callback_challenge_close()` - Close

**Features:**
- View active challenges
- Join/leave challenges
- Track personal progress
- View leaderboard
- Type-specific progress tracking

---

#### 4. `src/handlers/notification_handlers.py` (7 Functions)
**Purpose:** Notification viewing and management

**Commands:**
- `/notifications` → `cmd_notifications()` - List notifications

**Callbacks:**
- `notif_<id>` → `callback_view_notification()` - View details
- `delete_notif_<id>` → `callback_delete_notification()` - Delete
- `mark_all_read` → `callback_mark_all_read()` - Mark all as read
- `notif_back` → `callback_notification_back()` - Back to list
- `close_notif` → `callback_close_notifications()` - Close

**Features:**
- View unread/all notifications
- Mark as read individually or bulk
- Delete notifications
- Navigate notification details

---

## Integration with Bot

### Phase 3 Handler Registration in `bot.py`

```python
# Phase 3 Commands
application.add_handler(CommandHandler('payment_status', cmd_payment_status))
application.add_handler(CommandHandler('challenges', cmd_challenges))
application.add_handler(CommandHandler('my_challenges', cmd_my_challenges))
application.add_handler(CommandHandler('notifications', cmd_notifications))
application.add_handler(CommandHandler('admin_dashboard', cmd_admin_dashboard))

# Payment Conversation
payment_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(callback_pay_fee, pattern="^pay_fee$")],
    states={
        PAYMENT_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_payment_amount)],
        PAYMENT_METHOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_payment_method)],
        PAYMENT_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_payment)],
    },
    fallbacks=[CommandHandler('cancel', cancel_payment)]
)
application.add_handler(payment_handler)

# Callback handlers for Phase 3
application.add_handler(CallbackQueryHandler(handle_analytics_callback))
application.add_handler(CallbackQueryHandler(callback_view_notification, pattern="^notif_"))
application.add_handler(CallbackQueryHandler(callback_challenge_view, pattern="^challenge_view_"))
# ... more callback handlers
```

---

## Database Schema Requirements

### New Tables (Phase 3)

**fee_payments:**
```sql
CREATE TABLE fee_payments (
    payment_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id),
    amount DECIMAL,
    payment_method VARCHAR(50),
    paid_date TIMESTAMP,
    duration_days INTEGER,
    notes TEXT
);
```

**challenges:**
```sql
CREATE TABLE challenges (
    challenge_id SERIAL PRIMARY KEY,
    challenge_type VARCHAR(50),
    start_date DATE,
    end_date DATE,
    duration_days INTEGER,
    is_active BOOLEAN,
    description TEXT
);
```

**challenge_participants:**
```sql
CREATE TABLE challenge_participants (
    participant_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id),
    challenge_id INTEGER REFERENCES challenges(challenge_id),
    joined_date TIMESTAMP,
    progress_value DECIMAL,
    completed BOOLEAN
);
```

**notifications:**
```sql
CREATE TABLE notifications (
    notification_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id),
    notification_type VARCHAR(50),
    title VARCHAR(255),
    description TEXT,
    link_data TEXT,
    is_read BOOLEAN,
    created_at TIMESTAMP,
    deleted_at TIMESTAMP
);
```

### Modified Tables

**users:**
```sql
ALTER TABLE users ADD COLUMN fee_status VARCHAR(20); -- 'paid' or 'unpaid'
ALTER TABLE users ADD COLUMN fee_expiry_date DATE;
```

---

## Usage Examples

### For Users

**Check membership status:**
```
/payment_status
```

**View challenges:**
```
/challenges
```

**Join a challenge:**
- Send `/challenges`
- Click challenge name
- Click "Join Challenge"

**View notifications:**
```
/notifications
```

**Track challenge progress:**
- Send `/challenges` or `/my_challenges`
- Click challenge
- Click "My Progress"

### For Admins

**View analytics:**
```
/admin_dashboard
```

**Drill down into data:**
- Click "💰 Revenue" for payment details
- Click "👥 Members" for membership stats
- Click "📊 Engagement" for activity metrics
- Click "🏆 Challenges" for competition stats
- Click "🔥 Top Activities" for popular activities

---

## Notification System

### Automatic Triggers

Notifications are sent automatically for:
1. **Points Awarded** - User logs activity and earns points
2. **Attendance Approved** - Admin approves gym check-in
3. **Payment Due** - 7 days before membership expires
4. **Membership Expired** - Membership expires
5. **Achievement Unlocked** - User reaches milestone
6. **Challenge Reminder** - Challenge deadline approaching
7. **Leaderboard Update** - User's rank changes
8. **Daily Reminder** - Engagement reminder (optional)
9. **Shake Ready** - Protein shake available (if integrated)

### Sending Notifications

```python
from src.database.notifications_operations import send_points_notification

# Send points notification
send_points_notification(user_id=123, points=50)

# Send payment due notification
send_payment_due_notification(user_id=123)

# Create custom notification
create_notification(
    user_id=123,
    notification_type='achievement_unlocked',
    title='🏆 Milestone: 1000 Points!',
    description='You reached 1000 total points!',
    link_data='leaderboard'
)
```

---

## Configuration

### Points Configuration (Existing from Phase 2)
```python
POINTS_CONFIG = {
    'weight_log': 10,
    'water_log': 5,
    'meal_photo': 15,
    'habit_log': 10,
    'gym_checkin': 25,
    'bonus_hydration': 5,
    'bonus_meals': 5,
    'daily_bonus': 20
}
```

### Challenge Configuration
```python
CHALLENGE_TYPES = {
    'weight_loss': {
        'duration': 30,
        'description': 'Lose weight',
        'reward': 200
    },
    'consistency': {
        'duration': 30,
        'description': 'Log activities daily',
        'reward': 150
    },
    'water_challenge': {
        'duration': 30,
        'description': '8 glasses daily',
        'reward': 100
    },
    'gym_warrior': {
        'duration': 30,
        'description': '20+ gym visits',
        'reward': 200
    },
    'meal_prep': {
        'duration': 30,
        'description': '30 meals logged',
        'reward': 150
    }
}
```

---

## Testing Phase 3

### Test Payment Flow
1. Send `/payment_status` (should show UNPAID)
2. Click "💳 Pay Membership Fee"
3. Select ₹500 for 30 days
4. Select payment method
5. Confirm payment
6. Verify fee_status = 'paid' in database

### Test Challenges
1. Send `/challenges`
2. Click challenge type
3. Click "✅ Join Challenge"
4. Send `/my_challenges`
5. Verify challenge appears
6. Click "📈 My Progress" and verify progress tracking

### Test Notifications
1. Log activities and earn points
2. Send `/notifications`
3. Verify notification appears
4. Click to view details
5. Test mark as read and delete

### Test Admin Dashboard
1. Send `/admin_dashboard`
2. Click "💰 Revenue" - verify payment data
3. Click "👥 Members" - verify member count
4. Click "📊 Engagement" - verify activity metrics
5. Click "🏆 Challenges" - verify challenge stats

---

## Error Handling

All Phase 3 functions include comprehensive error handling:
- Invalid user IDs → Return None or empty list
- Database errors → Log and return error message
- Invalid dates/amounts → Validation before processing
- Transaction failures → Rollback and log

Example:
```python
def record_fee_payment(user_id, amount, payment_method, duration_days, notes=""):
    try:
        if not user_id or amount <= 0:
            logger.warning(f"Invalid payment: user_id={user_id}, amount={amount}")
            return False
        
        # Processing...
        return True
    except Exception as e:
        logger.error(f"Payment recording failed: {str(e)}")
        return False
```

---

## Performance Considerations

1. **Leaderboard queries** - Use pagination (limit 10-50)
2. **Challenge progress** - Cache calculations when possible
3. **Notification retrieval** - Index on (user_id, is_read)
4. **Analytics queries** - Pre-calculate or schedule batch jobs

---

## Next Steps (Phase 4+)

- SMS/Email notifications
- API integration (payment gateway, SMS service)
- Mobile app
- Web dashboard for coaches
- Advanced analytics/reports
- Referral system
- Premium features

---

## Files Modified/Created

**New Files:**
- `src/database/payment_operations.py` (190 lines, 11 functions)
- `src/database/statistics_operations.py` (260 lines, 9 functions)
- `src/database/challenges_operations.py` (240 lines, 11 functions)
- `src/database/notifications_operations.py` (250 lines, 15 functions)
- `src/handlers/analytics_handlers.py` (240 lines, 8 async functions)
- `src/handlers/payment_handlers.py` (~280 lines, 12 functions)
- `src/handlers/challenge_handlers.py` (~240 lines, 9 functions)
- `src/handlers/notification_handlers.py` (~180 lines, 7 functions)

**Modified Files:**
- `src/bot.py` - Added Phase 3 imports and handler registration

**Total Phase 3 Code:** ~1,880 lines across 8 modules

---

## Summary

Phase 3 is complete with:
✅ Payment system for membership fees
✅ Comprehensive analytics and reporting
✅ Challenge/competition system with 5 challenge types
✅ Multi-channel notification system
✅ Admin dashboard with real-time metrics
✅ Full Telegram UI integration

All modules follow the established 3-layer architecture (database → handlers → bot) with comprehensive error handling and logging.
