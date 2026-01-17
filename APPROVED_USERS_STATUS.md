# 🎯 Approved Users - Status Change System

## ✅ Status: FULLY IMPLEMENTED

Approved users automatically get their status changed so they can use the app.

---

## Quick Overview

```
Payment Approved by Admin
        ↓
    Database Updates:
    • subscription_requests → status = 'approved'
    • subscriptions → status = 'active' ← KEY
    • users → approval_status = 'approved'
        ↓
    User Receives Notification:
    "✅ Payment Approved! Send /menu to access"
        ↓
    User Sends /menu
        ↓
    System Checks:
    • Is subscription.status = 'active'? ✅
    • Is end_date in future? ✅
        ↓
    User Sees Full Menu ✅
```

---

## The Two Status Types

### 1️⃣ Subscription Status (`subscriptions.status`)
- **Before Approval**: `inactive` or missing record
- **After Approval**: `active` ✅
- **Checked By**: Menu access validation
- **Expires**: On `end_date` (with 7-day grace period)

### 2️⃣ User Approval Status (`users.approval_status`)
- **Before Approval**: `pending`
- **After Approval**: `approved` ✅
- **Purpose**: Registration verification

---

## What Happens When Admin Approves

### Admin's Action:
1. Receives payment notification
2. Clicks "✅ Approve" button
3. Enters amount received (e.g., 2500)
4. Selects end date (e.g., 17-Feb-2026)
5. Confirms

### System's Action (Automatic):
```python
# 1. Update subscription request
UPDATE subscription_requests 
SET status = 'approved' 
WHERE id = request_id

# 2. Create/Update subscription record
INSERT/UPDATE subscriptions 
SET status = 'active',        # ← KEY: Enables access
    end_date = '2026-02-17',
    grace_period_end = '2026-02-24'

# 3. Update user status
UPDATE users 
SET approval_status = 'approved'

# 4. Send confirmation to user
Message: "✅ Payment Approved! 
          Send /menu to access the app"
```

### User's Result:
- ✅ Receives confirmation message
- ✅ Can send `/menu` command
- ✅ Sees full menu with all features
- ✅ Can track activities, weight, enter challenges, etc.

---

## User Access Check

When user sends `/menu`, bot checks:

```python
def check_access(user_id):
    # Get subscription from database
    sub = get_user_subscription(user_id)
    
    if not sub:
        return "No subscription found - show subscribe button"
    
    if sub['status'] != 'active':
        return "Subscription inactive - show subscribe button"
    
    if datetime.now() > sub['end_date']:
        if datetime.now() <= sub['grace_period_end']:
            return "Show menu - in grace period"
        else:
            return "Show subscribe button - expired"
    
    return "Show full menu ✅"
```

---

## Verification

### For User:
```
1. User receives: "✅ Payment Approved! Send /menu to access"
2. User sends: /menu
3. User sees: Full menu (not subscription block)
```

### For Admin:
```sql
SELECT s.status, s.end_date, u.approval_status, sr.status
FROM subscriptions s
JOIN users u ON s.user_id = u.user_id
JOIN subscription_requests sr ON sr.id = ?
WHERE s.user_id = ?;

-- Expected:
-- status: 'active'
-- end_date: 2026-02-17 (future date)
-- approval_status: 'approved'
-- (request) status: 'approved'
```

---

## Features Available After Approval

Once approved and accessing menu, user can:
- ✅ 💪 Track activities and workouts
- ✅ ⚖️ Log weight and track progress
- ✅ 🏆 Participate in challenges
- ✅ 🥤 Place shake orders
- ✅ 📊 View statistics and reports
- ✅ ⚙️ Update profile and preferences
- ✅ 📞 Contact support

---

## If User Can't Access Menu

**Troubleshoot:**

1. **User should try:**
   - Send `/start` to refresh session
   - Then send `/menu`

2. **Admin should check:**
   ```sql
   -- Was approval actually saved?
   SELECT * FROM subscriptions WHERE user_id = ?;
   SELECT * FROM subscription_requests WHERE user_id = ? 
   ORDER BY id DESC LIMIT 1;
   ```

3. **Verify database has:**
   - `subscriptions.status = 'active'`
   - `subscriptions.end_date` > NOW()
   - `users.approval_status = 'approved'`

4. **If database is correct:**
   - Restart bot
   - Try again

---

## Recent Improvements (v1.1)

**Enhanced Approval Message:**
- ✨ Added "What to do next" section
- ✨ Listed all available features
- ✨ Clear instruction to send `/menu`
- ✨ Better user experience

**Before:**
```
✅ Payment Approved!
...
You now have full access to all gym features!
Thank you for subscribing! 🙏
```

**After:**
```
✅ Payment Approved!
...
You now have full access to all gym features!

📱 What to do next:
1️⃣ Send /menu to access the app
2️⃣ Enjoy all features:
   • 💪 Activity Tracking
   • ⚖️ Weight Tracking
   • 🏆 Challenges
   • 🥤 Shake Orders
   • 📊 Statistics

Thank you for subscribing! 🙏
```

---

## Files Involved

| File | Function | Purpose |
|------|----------|---------|
| `src/handlers/subscription_handlers.py` | `callback_approve_with_date()` | Main approval handler |
| `src/database/subscription_operations.py` | `approve_subscription()` | Sets status to active |
| `src/database/user_operations.py` | `approve_user()` | Sets user approved |
| `src/handlers/role_keyboard_handlers.py` | `show_role_menu()` | Checks subscription before showing menu |
| `src/handlers/user_handlers.py` | `handle_start()` | Checks subscription on /start |

---

## Status Flow Diagram

```
┌─────────────────────────────────────────────────────────┐
│                 USER REGISTRATION                       │
│              (Status: pending)                          │
└────────────────────┬────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────┐
│                USER SUBSCRIPTION REQUEST                │
│         (Status: pending, awaiting payment)            │
└────────────────────┬────────────────────────────────────┘
                     │
                     ↓ (User pays)
┌─────────────────────────────────────────────────────────┐
│               ADMIN RECEIVES NOTIFICATION               │
│            (Waits for admin approval)                  │
└────────────────────┬────────────────────────────────────┘
                     │
                     ↓ (Admin clicks Approve)
┌─────────────────────────────────────────────────────────┐
│                   ✅ APPROVED                           │
│   subscriptions.status = 'active'                      │
│   users.approval_status = 'approved'                   │
│   User receives confirmation message                   │
└────────────────────┬────────────────────────────────────┘
                     │
                     ↓ (User sends /menu)
┌─────────────────────────────────────────────────────────┐
│              📱 FULL MENU ACCESS                        │
│         All features available to user                 │
│         (Until subscription.end_date)                  │
└─────────────────────────────────────────────────────────┘
```

---

## Summary

✅ **Everything is automated!**

When admin approves a payment:
1. Database is updated instantly
2. User status changes to approved
3. Subscription marked as active
4. User gets confirmation with instructions
5. User can access everything

**No manual steps needed!** The system handles all status changes automatically.

🚀 Ready to use!
