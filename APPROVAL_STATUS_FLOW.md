# User Approval & Subscription Status Flow

## The Two Types of Status

### 1. **User Approval Status** (`users.approval_status`)
- **Values**: `pending` → `approved` → (optionally `rejected`)
- **Purpose**: Admin registration review
- **Checked By**: Admin dashboard
- **Updated By**: `approve_user()` function

### 2. **Subscription Status** (`subscriptions.status`)
- **Values**: `pending` → `active` or `inactive`
- **Purpose**: Determines if user can access app features
- **Checked By**: `is_subscription_active()` function
- **Updated By**: `approve_subscription()` function

---

## Complete Approval Flow

### Step 1: User Initiates Payment
```
/subscribe → Select Plan → Select Payment Method (UPI/Cash)
```

### Step 2: Admin Reviews Payment
- User sends payment (UPI or Cash)
- Admin receives notification with QR code or payment details
- Admin clicks "✅ Approve" button

### Step 3: Admin Enters Amount & Date
```
Admin clicks Approve → Enters amount received → Selects end date → Clicks confirm date
```

### Step 4: Subscription is Activated
At this point, the `approve_subscription()` function does:

1. **Updates subscription_requests table**
   ```sql
   UPDATE subscription_requests 
   SET status = 'approved', approved_at = NOW()
   WHERE id = {request_id}
   ```

2. **Creates or Updates subscriptions table**
   ```sql
   INSERT INTO subscriptions (
       user_id, plan_id, amount, 
       start_date, end_date, 
       status = 'active', 
       grace_period_end, created_at
   )
   VALUES (...)
   
   -- OR if user already has subscription:
   UPDATE subscriptions 
   SET status = 'active', end_date = {new_end_date}, ...
   WHERE user_id = {user_id}
   ```

3. **Sets user approval status**
   ```sql
   UPDATE users 
   SET approval_status = 'approved'
   WHERE user_id = {user_id}
   ```

4. **Sends confirmation to user**
   - Message: "✅ Payment Approved!"
   - Shows: Amount, Valid Until date, Plan name
   - States: "You now have full access to all gym features!"

### Step 5: User Gains Access
After approval, when user runs `/menu` or `/start`:

```python
# Check subscription
is_subscription_active(user_id)
├─ Get subscription from DB
├─ Check: status == 'active' AND now <= end_date
└─ Return True → Show menu items
```

---

## Database Queries to Verify

### Check if user has active subscription:
```sql
SELECT * FROM subscriptions 
WHERE user_id = {user_id} 
AND status = 'active' 
AND NOW() <= end_date;
```

### Check user approval status:
```sql
SELECT approval_status FROM users 
WHERE user_id = {user_id};
```

### Check subscription request approval:
```sql
SELECT status FROM subscription_requests 
WHERE id = {request_id};
```

---

## Troubleshooting

### ❌ User still can't access menu after approval

**Check these in order:**

1. **Database - Subscriptions table**
   ```sql
   SELECT * FROM subscriptions WHERE user_id = {user_id};
   ```
   - Should have: `status = 'active'`, `end_date` in future

2. **Database - Subscription Requests table**
   ```sql
   SELECT * FROM subscription_requests WHERE user_id = {user_id} ORDER BY id DESC LIMIT 1;
   ```
   - Should have: `status = 'approved'`

3. **User action needed**
   - User must send `/menu` or `/start` command after approval
   - Session may cache old data

4. **Bot restart**
   - Sometimes bot cache needs clearing
   - Kill and restart the bot process

### ⚠️ User got approval message but menu still blocked

1. User should try `/menu` again
2. If still blocked, check database for:
   - `subscriptions.end_date` is in future
   - `subscriptions.status` is 'active'
   - Current time vs stored time

---

## Confirmation Message Content

When user is approved, they receive:

```
✅ Payment Approved!

📋 Payment Receipt
💰 Amount: Rs. 2,500
📅 Valid Until: 17-02-2026
✓ Plan: 1 Month Plan

🎉 You now have full access to all gym features!

Thank you for subscribing! 🙏
```

Then user should send `/menu` to access the app.

---

## Summary

✅ **The system is working correctly** - all statuses are being updated:
- Subscription request marked as `approved`
- Subscription record created/updated with `status='active'` and future `end_date`
- User approval status set to `approved`
- User receives confirmation message

Users can then use `/menu` to access features!
