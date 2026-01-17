# 📢 Broadcast & Follow-up System Documentation

## Overview

The broadcast system allows admins to send personalized messages to users and automatically follow up with inactive members to encourage them to return to the gym.

---

## Features

### 1. **Manual Broadcast Messages** 📤
Admin can send personalized messages to specific user groups:
- **All Users**: Every registered member
- **Active Users**: Members who visited in the last 30 days  
- **Inactive Users**: Members who haven't visited in 30+ days

### 2. **Message Personalization** ✨
Messages can use `{name}` placeholder which gets replaced with each user's name:
```
"Hi {name}, we miss you at the gym!"
→ "Hi John Doe, we miss you at the gym!"
```

### 3. **Automated Follow-up System** 🤖
Automatically sends motivational messages to inactive users:
- **7 days inactive**: Friendly reminder
- **14 days inactive**: Motivational message
- **30 days inactive**: Special offer + free session

### 4. **Broadcast History Tracking** 📊
All broadcasts are logged in database with:
- User ID
- Message sent
- Broadcast type
- Timestamp

---

## How to Use (Admin)

### Sending a Broadcast

1. **Start Broadcast:**
   - Click "📢 Broadcast" button in Admin Menu
   - Or use `/broadcast` command

2. **Select Audience:**
   - Choose from:
     - `📢 All Users` - Everyone
     - `✅ Active Users` - Last 30 days
     - `💤 Inactive Users` - 30+ days inactive

3. **Compose Message:**
   - Type your message
   - Use `{name}` for personalization
   - Example: `Hi {name}, special offer this week! 💪`

4. **Preview & Confirm:**
   - Review preview with sample name
   - See recipient count
   - Click "✅ Send Broadcast"

5. **Track Progress:**
   - Bot shows sending progress
   - Final report: successful/failed sends

### Viewing Follow-up Settings

1. Click "🤖 Follow-up Settings" in Admin Menu
2. See current status:
   - Follow-up schedule (7, 14, 30 days)
   - Recent messages sent
   - System status

3. View follow-up log:
   - Click "📊 View Follow-up Log"
   - See recent automated messages

---

## Follow-up Message Templates

### 7-Day Inactive (Friendly Reminder)
```
Hi {name}! 👋

We noticed you haven't visited the gym in a week. Everything okay?

💪 Your fitness journey is important to us!
We're here whenever you're ready to get back on track.

Need help with your schedule? Just let us know! 😊
```

### 14-Day Inactive (Motivational)
```
Hey {name}! 🌟

It's been 2 weeks since we've seen you at the gym. We miss you!

🎯 Remember your goals? Let's crush them together!
Your membership is active and waiting for you.

Reply to this message if you need any motivation or support! 💪
```

### 30-Day Inactive (Special Offer)
```
Hello {name}! 🏋️‍♂️

A whole month has passed since your last visit. We really miss seeing you!

🔥 Don't let your progress slip away!
📅 Special offer: Book a free personal training session with us!

Let's get you back on track. Your health matters! ❤️

Reply 'YES' to schedule your comeback session!
```

---

## Database Schema

### broadcast_log Table
```sql
CREATE TABLE broadcast_log (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    message TEXT NOT NULL,
    broadcast_type VARCHAR(50) NOT NULL,
    sent_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Indexes for performance
CREATE INDEX idx_broadcast_log_user_id ON broadcast_log(user_id);
CREATE INDEX idx_broadcast_log_type ON broadcast_log(broadcast_type);
CREATE INDEX idx_broadcast_log_sent_at ON broadcast_log(sent_at);
```

### Broadcast Types
- `all` - Manual broadcast to all users
- `active` - Manual broadcast to active users
- `inactive` - Manual broadcast to inactive users
- `followup_7d` - Automated 7-day follow-up
- `followup_14d` - Automated 14-day follow-up
- `followup_30d` - Automated 30-day follow-up

---

## User Activity Logic

### Active User Definition
User is considered **active** if they have at least one attendance record in the last 30 days:
```sql
SELECT DISTINCT u.user_id, u.full_name
FROM users u
INNER JOIN attendance_log a ON u.user_id = a.user_id
WHERE u.is_active = TRUE 
AND a.created_at >= NOW() - INTERVAL '30 days'
```

### Inactive User Definition
User is considered **inactive** if they have NO attendance in the last 30 days:
```sql
SELECT u.user_id, u.full_name FROM users u
WHERE u.is_active = TRUE
AND NOT EXISTS (
    SELECT 1 FROM attendance_log a
    WHERE a.user_id = u.user_id
    AND a.created_at >= NOW() - INTERVAL '30 days'
)
```

---

## Scheduled Jobs

### Daily Follow-up Job
**Time:** 9:00 AM every day  
**Function:** `send_followup_to_inactive_users()`  
**Purpose:** Check for users inactive for exactly 7, 14, or 30 days and send appropriate message

**Logic:**
1. Query users inactive for exactly X days
2. Check they haven't already received this follow-up
3. Send personalized message
4. Log to broadcast_log with type `followup_Xd`

**Duplicate Prevention:**
System checks if user already received the same follow-up type within the period:
```sql
AND NOT EXISTS (
    SELECT 1 FROM broadcast_log bl
    WHERE bl.user_id = u.user_id
    AND bl.broadcast_type = 'followup_7d'
    AND bl.sent_at >= NOW() - INTERVAL '7 days'
)
```

---

## Admin Menu Changes

### New Buttons Added (2 total)

**Before (14 buttons):**
```
📈 Dashboard
✔️ Pending Attendance
🥤 Pending Shakes
💳 Payment Status
📊 Notifications
➕ Add Staff
➖ Remove Staff
📋 List Staff
➕ Add Admin
➖ Remove Admin
📋 List Admins
🆔 Who Am I?
```

**After (16 buttons):**
```
📈 Dashboard
📢 Broadcast               ← NEW
🤖 Follow-up Settings      ← NEW
✔️ Pending Attendance
🥤 Pending Shakes
💳 Payment Status
📊 Notifications
➕ Add Staff
➖ Remove Staff
📋 List Staff
➕ Add Admin
➖ Remove Admin
📋 List Admins
🆔 Who Am I?
```

---

## Flow Diagrams

### Manual Broadcast Flow
```
Admin clicks "📢 Broadcast"
    ↓
Select audience type
(All / Active / Inactive)
    ↓
System shows recipient count
    ↓
Admin types message
(with {name} placeholders)
    ↓
Preview shown with sample
    ↓
Admin confirms ✅
    ↓
System sends to all recipients
    ↓
Progress report shown
(Success / Failed counts)
    ↓
Messages logged to database
```

### Automated Follow-up Flow
```
Daily at 9:00 AM
    ↓
Job runs: send_followup_to_inactive_users()
    ↓
Check users inactive 7 days
├─ Send 7-day message
└─ Log to broadcast_log
    ↓
Check users inactive 14 days
├─ Send 14-day message
└─ Log to broadcast_log
    ↓
Check users inactive 30 days
├─ Send 30-day message
└─ Log to broadcast_log
    ↓
Skip users who already received
that specific follow-up recently
```

---

## Error Handling

### Failed Message Sends
- Each send is wrapped in try/except
- Failed sends are logged but don't stop the broadcast
- Final report shows success/failed counts
- Admin can retry if needed

### Database Errors
- Connection errors logged to `logs/fitness_bot.log`
- Broadcast fails gracefully
- User sees error message

### Message Limits
- Telegram has rate limits (~30 messages/second)
- System sends messages sequentially
- No delay needed for typical gym sizes (< 500 members)

---

## Testing Guide

### Test Manual Broadcast

1. **Setup:**
   - Have at least 2 registered users
   - One active (attended in last 30 days)
   - One inactive (no attendance 30+ days)

2. **Test All Users:**
   ```
   /broadcast
   → Select "All Users"
   → Type: "Hello {name}, this is a test! 🎉"
   → Confirm
   → Check both users receive personalized messages
   ```

3. **Test Active Only:**
   ```
   /broadcast
   → Select "Active Users"
   → Type: "Great job {name}! Keep it up! 💪"
   → Confirm
   → Only active user should receive
   ```

4. **Test Inactive Only:**
   ```
   /broadcast
   → Select "Inactive Users"
   → Type: "We miss you {name}! Come back! ❤️"
   → Confirm
   → Only inactive user should receive
   ```

### Test Automated Follow-up

1. **Manual Trigger (Testing):**
   Add temporary function in bot.py:
   ```python
   # Test follow-up immediately
   await send_followup_to_inactive_users(application)
   ```

2. **Check Database:**
   ```sql
   SELECT * FROM broadcast_log 
   WHERE broadcast_type LIKE 'followup%'
   ORDER BY sent_at DESC;
   ```

3. **Verify Logic:**
   - User inactive 7 days gets 7-day message
   - User inactive 14 days gets 14-day message
   - User inactive 30 days gets 30-day message
   - No duplicates sent

### Test Edge Cases

1. **No Recipients:**
   - Select audience with 0 users
   - Should show "No users found"

2. **Duplicate Follow-ups:**
   - User gets 7-day follow-up
   - Run job again same day
   - Should not send duplicate

3. **Message Too Long:**
   - Telegram limit: 4096 characters
   - System should handle gracefully

---

## Performance Considerations

### Query Optimization
- All user queries use indexes
- `attendance_log` has index on `user_id` and `created_at`
- Broadcast queries use `EXISTS` subqueries (fast)

### Memory Usage
- Messages sent one at a time (sequential)
- No batch loading of all users
- Low memory footprint

### Database Load
- Follow-up job runs once daily
- Manual broadcasts are admin-initiated
- Minimal impact on normal operations

---

## Monitoring & Logs

### Bot Logs
Location: `logs/fitness_bot.log`

**Look for:**
```
INFO - Running automated follow-up for inactive users...
INFO - Sending 7-day follow-up to 5 users
INFO - Sent 7-day follow-up to user 123456789
ERROR - Failed to send 7-day follow-up to 987654321: ...
```

### Database Queries
```sql
-- Recent broadcasts
SELECT broadcast_type, COUNT(*), DATE(sent_at)
FROM broadcast_log
GROUP BY broadcast_type, DATE(sent_at)
ORDER BY DATE(sent_at) DESC;

-- User broadcast history
SELECT * FROM broadcast_log
WHERE user_id = 424837855
ORDER BY sent_at DESC;

-- Follow-up effectiveness
SELECT 
    bl.broadcast_type,
    COUNT(DISTINCT a.user_id) as returned_users
FROM broadcast_log bl
LEFT JOIN attendance_log a 
    ON bl.user_id = a.user_id 
    AND a.created_at > bl.sent_at
    AND a.created_at < bl.sent_at + INTERVAL '7 days'
WHERE bl.broadcast_type LIKE 'followup%'
GROUP BY bl.broadcast_type;
```

---

## Customization

### Change Follow-up Schedule
Edit in `broadcast_handlers.py`:
```python
followup_templates = {
    7: {...},   # Change to 5 days
    14: {...},  # Change to 10 days
    30: {...},  # Change to 21 days
}
```

### Change Follow-up Time
Edit in `bot.py`:
```python
job_queue.run_daily(
    send_followup_to_inactive_users,
    time=time(hour=10, minute=30),  # Change to 10:30 AM
    name="inactive_user_followup"
)
```

### Add More Follow-up Milestones
Add to `followup_templates`:
```python
60: {
    'message': "Long time no see {name}! 😢...",
    'days': 60
}
```

### Customize Messages
Edit message templates in `broadcast_handlers.py`:
```python
followup_templates = {
    7: {
        'message': "Your custom message for {name}...",
        'days': 7
    }
}
```

---

## Troubleshooting

### Issue: Broadcasts not sending
**Check:**
1. Is user an admin? (`is_admin()` returns True)
2. Are there users in database? (`SELECT COUNT(*) FROM users`)
3. Check bot logs for errors
4. Verify internet connection

### Issue: Personalization not working
**Check:**
1. Message contains `{name}` placeholder
2. Users have `full_name` in database
3. Check broadcast_log for actual sent message

### Issue: Follow-ups not running
**Check:**
1. Scheduled job registered? (Check startup logs)
2. Bot running continuously? (Not restarting)
3. Users exist matching inactivity criteria
4. Check `broadcast_log` for recent `followup_*` entries

### Issue: Duplicate follow-ups
**Check:**
1. Duplicate prevention query working
2. Database has correct indexes
3. Bot not running multiple instances

---

## Security Considerations

### Admin-Only Access
- All broadcast functions check `is_admin()` 
- Non-admins get "❌ Admin access only" message
- Callback queries also validated

### Rate Limiting
- Telegram enforces rate limits automatically
- Bot handles errors gracefully
- No infinite loops or spam

### Data Privacy
- Messages logged only with user_id (no sensitive data)
- Full message stored for audit purposes
- Old logs can be archived/deleted

---

## Future Enhancements

### Possible Additions
1. **Scheduled Broadcasts**: Set broadcast to send at specific time
2. **A/B Testing**: Send different messages to test effectiveness
3. **Response Tracking**: Track user responses to follow-ups
4. **Rich Media**: Send images, videos in broadcasts
5. **Segment Filters**: More advanced targeting (age, membership tier, etc.)
6. **Analytics Dashboard**: View broadcast performance metrics
7. **Draft Messages**: Save message templates
8. **Multi-Language**: Send broadcasts in user's preferred language

---

## Summary

✅ **Implemented Features:**
- Manual broadcast to All/Active/Inactive users
- Personalized messages with `{name}` placeholder
- Automated follow-up at 7, 14, 30 days
- Broadcast history tracking
- Admin-only access control
- Duplicate prevention for follow-ups
- Daily scheduled job at 9 AM
- Comprehensive logging

📊 **Admin Buttons:** 2 new buttons (Broadcast, Follow-up Settings)

🗄️ **Database:** 1 new table (broadcast_log)

⏰ **Scheduled Jobs:** 1 daily job (9:00 AM)

🎯 **User Targeting:** 3 audience types + 3 automated tiers

---

**Last Updated:** January 9, 2026  
**Version:** 1.0  
**Status:** ✅ Production Ready
