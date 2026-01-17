# 🚀 User Status Change - Quick Reference

## Status Types

| Status | Table | Purpose | Values |
|--------|-------|---------|--------|
| **Subscription Status** | `subscriptions.status` | Can user use app? | `active` / `inactive` |
| **User Approval Status** | `users.approval_status` | Is user verified? | `pending` / `approved` / `rejected` |

---

## Status Changes on Approval

```
BEFORE Admin Approves:
├─ subscription_requests.status = 'pending'
├─ subscriptions.status = null (or 'inactive')
└─ users.approval_status = 'pending'

↓ Admin clicks Approve + selects date ↓

AFTER Admin Approves:
├─ subscription_requests.status = 'approved' ✅
├─ subscriptions.status = 'active' ✅
├─ subscriptions.end_date = selected_date ✅
└─ users.approval_status = 'approved' ✅

↓ User sends /menu ↓

ACCESS GRANTED:
└─ User sees full menu + all features ✅
```

---

## What User Sees

### Before Approval:
```
🔒 To access the fitness club app, 
   you need an active subscription.
   
[💪 Subscribe Now]
```

### After Approval:
```
✅ Payment Approved!

📋 Payment Receipt
💰 Amount: Rs. 2,500
📅 Valid Until: 17-02-2026
✓ Plan: 1 Month Plan

🎉 You now have full access to all gym features!

📱 What to do next:
1️⃣ Send /menu to access the app
2️⃣ Enjoy features:
   • 💪 Activity Tracking
   • ⚖️ Weight Tracking
   • 🏆 Challenges
   • 🥤 Shake Orders
   • 📊 Statistics
```

### When User Sends `/menu`:
```
👤 USER MENU

🏋️ Activity Tracking
⚖️ Weight Tracking
🏆 Challenges
🥤 Shake Orders
📊 Statistics
⚙️ Settings
```

---

## Database Verification

### Check if user has access:
```sql
SELECT s.status, s.end_date, u.approval_status 
FROM subscriptions s
JOIN users u ON s.user_id = u.user_id
WHERE s.user_id = YOUR_USER_ID;
```

**Expected output:**
```
status       end_date       approval_status
'active'     2026-02-17     'approved'
```

---

## Code Flow

```python
# When user clicks /menu:
user_id = update.effective_user.id

# Check subscription
subscription = get_user_subscription(user_id)

# Is it active?
if subscription and subscription['status'] == 'active':
    # Show menu ✅
    await show_menu()
else:
    # Ask to subscribe ❌
    await show_subscribe_button()
```

---

## Change Log

### v1.0 - Initial Implementation
- ✅ Admin approval updates subscription status
- ✅ User approval status also updated
- ✅ Notification sent to user
- ✅ User can access menu after `/menu` command

### v1.1 - Improved UX (Latest)
- ✅ Added clear instructions in approval message
- ✅ Listed all available features
- ✅ Better guidance on next steps (send `/menu`)

---

## FAQ

**Q: User says they're approved but can't access menu?**
A: Ask them to:
1. Send `/start` to refresh session
2. Then send `/menu`

**Q: How long does status take to update?**
A: Instant! Database is updated immediately.

**Q: Can admin un-approve?**
A: Currently no. Need manual DB update if needed.

**Q: What if end_date is in past?**
A: User can still see menu (grace period of 7 days), then access blocked.

---

## Implementation Complete ✅

All user status changes are automatic when admin approves!
Users now get clear instructions and full access.
