# 🎯 Subscription System Testing Guide

## ✅ System Status
**Bot Started Successfully:** 2026-01-17 12:43:11
- ✅ All handlers registered
- ✅ Scheduled jobs active
- ✅ Database connected
- ✅ Subscription features ready

---

## 📋 Test Checklist

### **1. User Subscription Flow**

#### Test: Subscribe Command
1. **As regular user**, send `/subscribe`
2. **Expected:** See 3 plan options:
   - Plan 1: Rs.2,500 for 30 days
   - Plan 2: Rs.7,000 for 90 days
   - Plan 3: Rs.13,500 for 180 days

#### Test: Plan Selection
1. Click any plan button (e.g., "30 Days - Rs.2,500")
2. **Expected:** See confirmation message with plan details
3. Click "✅ Confirm & Request"
4. **Expected:** "🎉 Subscription request submitted! Wait for admin approval."

#### Test: View Subscription Status
1. Send `/my_subscription`
2. **Expected:** "⏳ Your subscription is pending approval"

---

### **2. Admin Approval Flow**

#### Test: View Pending Requests
1. **As admin**, send `/admin_subscriptions`
2. **Expected:** List of pending subscription requests with user details

#### Test: Standard Approval
1. Click "✅ Approve" on any request
2. Click "Standard Approval"
3. **Expected:** 
   - Admin sees confirmation
   - User receives approval notification with amount and end date
4. Send `/my_subscription` as user
5. **Expected:** Active subscription details displayed

#### Test: Custom Approval
1. Click "✅ Approve" on any request
2. Click "Custom Approval"
3. Enter custom amount (e.g., "2000")
4. Select end date from calendar
5. **Expected:**
   - Admin sees confirmation
   - User receives approval with custom amount and date

#### Test: Rejection
1. Click "❌ Reject" on any request
2. Enter rejection reason
3. **Expected:**
   - Admin sees confirmation
   - User receives rejection notification with reason

---

### **3. Access Control Tests**

#### Test: Start Command Without Subscription
1. **As new user**, send `/start` (after registration)
2. **Expected:** 
   - "🔒 To access the fitness club app, you need an active subscription"
   - See "💪 Subscribe Now" button

#### Test: Menu Access Without Subscription
1. **As user without subscription**, send `/menu`
2. **Expected:** Blocked with subscription prompt

#### Test: Start Command With Active Subscription
1. **As user with active subscription**, send `/start`
2. **Expected:** Normal welcome message and menu access

---

### **4. Grace Period Tests**

#### Test: Subscription Expiry
1. **Wait for subscription to expire** (or manually set end_date to past in database)
2. Send `/start` as user
3. **Expected:** 
   - "⚠️ Your subscription has expired but you're in the grace period"
   - Can still access menu (7-day grace period)

#### Test: Grace Period Daily Reminder
1. **During grace period**, check at 10:00 AM
2. **Expected:** User receives:
   - "🔔 Your subscription is in grace period"
   - Days remaining count
   - Reminder to renew

#### Test: Post-Grace Lockdown
1. **After 7-day grace period**, send `/start`
2. **Expected:**
   - "🔒 Your account has been locked due to expired subscription"
   - Must renew to access

---

### **5. Notification Tests**

#### Test: Expiry Reminder (2 Days Before)
1. **2 days before expiry**, check at 9:00 AM
2. **Expected:** User receives:
   - "⚠️ Subscription Expiring Soon"
   - End date shown
   - Prompt to renew

#### Test: Follow-up Messages
1. **After grace period expires**, check every 3 days at 11:00 AM
2. **Expected:** User receives motivational messages:
   - "💪 We Miss You!"
   - "🏋️ Ready to Get Back?"
   - "🔥 Don't Give Up!"
   - "⭐ You've Got This!"

---

## 🔧 Scheduled Jobs Status

| Job | Schedule | Status | Purpose |
|-----|----------|--------|---------|
| **Expiry Reminders** | Daily 9:00 AM | ✅ Active | 2 days before notification |
| **Grace Period Reminders** | Daily 10:00 AM | ✅ Active | Daily during 7-day grace |
| **Follow-up Messages** | Every 3 days 11:00 AM | ✅ Active | Motivational reminders |
| **Lock Expired** | Daily 12:05 AM | ✅ Active | Auto-lock after grace |

---

## 💾 Database Tables

### `subscriptions`
- Tracks active subscriptions
- Fields: user_id, plan_id, amount, start_date, end_date, status, grace_period_end

### `subscription_requests`
- Pending approval requests
- Fields: user_id, plan_id, amount, status, requested_at, approved_at, rejection_reason

### `subscription_reminders`
- Reminder history
- Fields: user_id, reminder_type, last_sent_at

---

## 🎨 Subscription Plans

| Plan ID | Duration | Price | Description |
|---------|----------|-------|-------------|
| `plan_30` | 30 days | Rs.2,500 | Monthly membership |
| `plan_90` | 90 days | Rs.7,000 | Quarterly membership |
| `plan_180` | 180 days | Rs.13,500 | Half-yearly membership |

---

## 🔍 Troubleshooting

### Issue: User can't subscribe
- **Check:** Is user registered?
- **Fix:** Send `/register` first

### Issue: Admin doesn't see pending requests
- **Check:** Are there any requests?
- **Fix:** Have user submit request via `/subscribe`

### Issue: Scheduled jobs not running
- **Check:** Bot logs for job execution
- **Fix:** Restart bot: `taskkill /F /IM python.exe` then start again

### Issue: User still blocked after approval
- **Check:** Database subscription status
- **Fix:** Verify end_date is in future, status is 'active'

---

## 📝 Quick Commands

### User Commands
```
/subscribe          - Subscribe to gym membership
/my_subscription    - View subscription status
/start              - Check access (shows subscription prompt if needed)
/menu               - Access main menu (requires active subscription)
```

### Admin Commands
```
/admin_subscriptions - View and manage pending subscriptions
/admin_panel        - Admin dashboard
```

---

## 🎯 Expected User Journey

1. **Registration** → User registers via `/register`
2. **Subscribe** → User sends `/subscribe`, selects plan, confirms
3. **Wait for Approval** → Admin approves via `/admin_subscriptions`
4. **Access Granted** → User can now use all app features
5. **Expiry Warning** → 2 days before expiry, user gets reminder
6. **Expiry** → Subscription expires, 7-day grace period starts
7. **Grace Reminders** → Daily reminders during grace
8. **Lockdown** → After 7 days, account locked until renewal
9. **Follow-up** → Every 3 days, motivational messages sent

---

## 🚀 Production Readiness

✅ **Completed:**
- Database migration successful
- All handlers registered
- Scheduled jobs active
- Access control implemented
- Notifications configured
- Admin approval workflow ready

⚠️ **Before Production:**
- Test full user journey end-to-end
- Verify all scheduled jobs execute at correct times
- Test edge cases (expired subscriptions, grace period transitions)
- Confirm payment integration (if applicable)
- Set up monitoring for failed jobs

---

## 📞 Support

**Bot Status:** ✅ Running
**Database:** ✅ Connected
**Scheduled Jobs:** ✅ Active (11 jobs registered)

**Last Updated:** 2026-01-17 12:43:11
