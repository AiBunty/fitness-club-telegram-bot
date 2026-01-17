# 🚀 Broadcast System - Quick Start Guide

## ✅ Implementation Complete!

All broadcast features have been successfully implemented and are ready to use.

---

## 📋 What's New?

### 1. **Admin Menu** (16 buttons now)
Two new buttons added:
- 📢 **Broadcast** - Send messages to users
- 🤖 **Follow-up Settings** - View automated follow-up status

### 2. **Database**
New table created: `broadcast_log`
- Tracks all broadcast messages
- Records automated follow-ups
- Enables analytics and history

### 3. **Scheduled Jobs**
Automated follow-up system runs **daily at 9:00 AM**:
- 7-day inactive → Friendly reminder
- 14-day inactive → Motivational message
- 30-day inactive → Special offer + free session

---

## 🎯 How to Test

### Test 1: Manual Broadcast

1. **Open Telegram bot**
2. Send `/menu` or `/start`
3. Click **"📢 Broadcast"** button
4. Select audience:
   - All Users
   - Active Users (last 30 days)
   - Inactive Users (30+ days)
5. Type message: `"Hi {name}, this is a test message! 🎉"`
6. Preview and confirm
7. Check that message is sent to all selected users

### Test 2: View Follow-up Settings

1. Click **"🤖 Follow-up Settings"** button
2. See current status:
   - Automated follow-up schedule
   - Recent messages sent
   - System status
3. Click **"📊 View Follow-up Log"** to see history

### Test 3: Check Database

Run in database:
```sql
-- View all broadcasts
SELECT * FROM broadcast_log ORDER BY sent_at DESC LIMIT 10;

-- Count by type
SELECT broadcast_type, COUNT(*) 
FROM broadcast_log 
GROUP BY broadcast_type;
```

---

## 📢 Broadcast Message Examples

### For All Users
```
"🎉 Big announcement! {name}, we have new equipment arriving next week! Come check it out! 💪"
```

### For Active Users
```
"Great job {name}! 🏆 You're crushing it! Keep up the excellent work! Your dedication inspires us! 🔥"
```

### For Inactive Users
```
"Hey {name}! 😊 We noticed you haven't been to the gym in a while. Everything okay? We're here for you! Let's get back on track together! 💪❤️"
```

---

## 🤖 Automated Follow-up Messages

### These Run Automatically Every Day at 9 AM:

**7 Days Inactive:**
```
Hi {name}! 👋

We noticed you haven't visited the gym in a week. Everything okay?

💪 Your fitness journey is important to us!
We're here whenever you're ready to get back on track.

Need help with your schedule? Just let us know! 😊
```

**14 Days Inactive:**
```
Hey {name}! 🌟

It's been 2 weeks since we've seen you at the gym. We miss you!

🎯 Remember your goals? Let's crush them together!
Your membership is active and waiting for you.

Reply to this message if you need any motivation or support! 💪
```

**30 Days Inactive:**
```
Hello {name}! 🏋️‍♂️

A whole month has passed since your last visit. We really miss seeing you!

🔥 Don't let your progress slip away!
📅 Special offer: Book a free personal training session with us!

Let's get you back on track. Your health matters! ❤️

Reply 'YES' to schedule your comeback session!
```

---

## 📊 Bot Commands Added

### New Commands:
- `/broadcast` - Start broadcast system
- `/followup_settings` - View follow-up settings

### All Admin Commands:
```
/menu - Main menu
/admin_dashboard - Analytics dashboard
/broadcast - Send broadcast message
/followup_settings - Follow-up configuration
/pending_attendance - Review check-ins
/pending_shakes - Review shake orders
/add_staff - Assign staff role
/remove_staff - Remove staff role
/add_admin - Assign admin role
/remove_admin - Remove admin role
```

---

## 🔍 Monitoring

### Check Bot Logs
File: `logs/fitness_bot.log`

Look for:
```
INFO - Scheduled daily follow-up job at 9:00 AM
INFO - Running automated follow-up for inactive users...
INFO - Sending 7-day follow-up to X users
INFO - Sent 7-day follow-up to user 123456789
```

### Check Database
```sql
-- Recent broadcasts
SELECT 
    broadcast_type, 
    COUNT(*) as count,
    DATE(sent_at) as date
FROM broadcast_log
WHERE sent_at >= NOW() - INTERVAL '7 days'
GROUP BY broadcast_type, DATE(sent_at)
ORDER BY date DESC;

-- User broadcast history
SELECT * FROM broadcast_log
WHERE user_id = 424837855  -- Your user ID
ORDER BY sent_at DESC;
```

---

## 🎛️ Customization Options

### Change Follow-up Schedule

Edit `src/handlers/broadcast_handlers.py`:
```python
followup_templates = {
    7: {...},   # Change to different days
    14: {...},
    30: {...},
}
```

### Change Follow-up Time

Edit `src/bot.py`:
```python
job_queue.run_daily(
    send_followup_to_inactive_users,
    time=time(hour=10, minute=0),  # Change to 10:00 AM
    name="inactive_user_followup"
)
```

### Edit Message Templates

Edit templates in `src/handlers/broadcast_handlers.py`:
```python
followup_templates = {
    7: {
        'message': "Your custom message here for {name}...",
        'days': 7
    }
}
```

---

## 🔧 Files Modified/Created

### New Files:
1. `src/handlers/broadcast_handlers.py` - All broadcast logic
2. `migrate_broadcast_log.py` - Database migration script
3. `BROADCAST_SYSTEM_DOCS.md` - Full documentation
4. `BROADCAST_QUICKSTART.md` - This file

### Modified Files:
1. `src/bot.py` - Added broadcast handlers & scheduled job
2. `src/handlers/role_keyboard_handlers.py` - Added 2 admin buttons

### Database:
1. New table: `broadcast_log` with indexes

---

## ✅ System Status

### Current State:
- ✅ Bot running with broadcast system
- ✅ Database table created
- ✅ Admin menu updated (16 buttons)
- ✅ Scheduled job registered (9 AM daily)
- ✅ All handlers registered
- ✅ Menu button configured

### Next Steps:
1. **Test Manual Broadcast** - Send test message to verify
2. **Monitor Follow-ups** - Check logs tomorrow at 9 AM
3. **Customize Messages** - Edit templates to match your brand
4. **Track Effectiveness** - Monitor user engagement

---

## 📈 Expected Results

### Manual Broadcasts:
- Admin can send personalized messages instantly
- Messages include user's name automatically
- Can target specific user groups
- Full tracking in database

### Automated Follow-ups:
- Run every morning at 9 AM
- Target users at 7, 14, 30-day milestones
- No duplicates (smart filtering)
- Motivate inactive users to return

---

## 🆘 Troubleshooting

### Bot Not Showing Broadcast Button
**Solution:** Restart bot or send `/menu` command

### Messages Not Sending
**Check:**
1. Are you admin? Send `/whoami` to verify
2. Is bot running? Check terminal
3. Are there users in database?
4. Check logs: `logs/fitness_bot.log`

### Follow-ups Not Working
**Check:**
1. Is bot running continuously?
2. Wait until 9 AM next day
3. Check database: `SELECT * FROM broadcast_log WHERE broadcast_type LIKE 'followup%'`
4. Verify users meet inactivity criteria

---

## 📞 Support

### Documentation:
- Full Docs: `BROADCAST_SYSTEM_DOCS.md`
- This Guide: `BROADCAST_QUICKSTART.md`
- Bot Logs: `logs/fitness_bot.log`

### Database Queries:
```sql
-- Check broadcast_log table
SELECT * FROM broadcast_log ORDER BY sent_at DESC LIMIT 5;

-- Count users by activity
SELECT 
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM attendance_log a 
            WHERE a.user_id = u.user_id 
            AND a.created_at >= NOW() - INTERVAL '30 days'
        ) THEN 'Active'
        ELSE 'Inactive'
    END as status,
    COUNT(*) as count
FROM users u
WHERE u.is_active = TRUE
GROUP BY status;
```

---

## 🎉 Success!

Your fitness club bot now has a complete broadcast and follow-up system!

**Key Features:**
- 📢 Send targeted broadcasts
- 🤖 Automated follow-ups
- 📊 Full tracking & history
- 🎯 Personalized messages
- ⏰ Daily scheduling

**Impact:**
- Re-engage inactive members
- Boost attendance rates
- Improve member retention
- Strengthen community

---

**Ready to broadcast!** 🚀

Open Telegram → Click "📢 Broadcast" → Start engaging your members!

---

**Last Updated:** January 9, 2026  
**Version:** 1.0  
**Status:** ✅ Production Ready
