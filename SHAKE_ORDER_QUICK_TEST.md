# 🥤 SHAKE ORDER SYSTEM - Quick Test Guide

**Status**: ✅ Ready to Test  
**Date**: January 17, 2026

---

## Quick Start (5 minutes)

### 1. Start Bot
```bash
cd c:\Users\ventu\Fitness\fitness-club-telegram-bot
python start_bot.py
```

**Expected Output**:
```
Testing database connection...
Database connection OK
Database OK! Starting bot...
Bot starting...
Application started
```

### 2. Test as Regular User (in Telegram)

**Scenario A: User Orders Shake**
```
Step 1: Send /menu
         ↓ See "🥛 Order Shake" button

Step 2: Tap "🥛 Order Shake"
         ↓ See 9 shake flavors + balance

Step 3: Select flavor (e.g., "🥤 Kulfi")
         ↓ See confirmation with details:
            ✅ Shake Order Summary
            👤 Name: [your name]
            🥤 Selected: Kulfi
            💳 Credits: -1
            💰 Before: 5
            💰 After: 4

Step 4: Tap "✅ Confirm Order"
         ↓ See success:
            ✅ Shake Order Placed!
            💰 Balance: 4 (updated)
            📋 Request ID: #XX

Expected: Balance decreases by 1 ✅
```

### 3. Test as Admin (in Telegram)

**Scenario B: Admin Approves Order**
```
Step 1: Receive notification:
         🔔 NEW SHAKE ORDER - PENDING APPROVAL
         👤 User: John Doe
         🥤 Flavor: Kulfi
         📋 Request ID: #47
         [✅ Approve & Ready]

Step 2: Tap "✅ Approve & Ready"
         ↓ See confirmation:
            ✅ SHAKE APPROVED & READY
            👤 User: John Doe
            🥤 Flavor: Kulfi
            💰 Balance: 4
            [✅ Mark Completed]

Step 3: Tap "✅ Mark Completed"
         ↓ See final:
            ✅ SHAKE DELIVERED
            🥤 Kulfi delivered to John Doe

Expected: User receives 2 confirmations ✅
```

---

## Menu Items (9 Shakes)

```
🥤 Kulfi .................... Traditional ice cream
🍓 Strawberry ............... Fresh & fruity
🍦 Vanilla .................. Classic taste
🍫 Dutch Chocolate .......... Rich & dark
🥭 Mango .................... Tropical flavor
🍊 Orange Cream ............. Citrus smoothness
🌿 Paan ..................... Traditional flavor
🌹 Rose Kheer ............... Dessert shake
🍌 Banana Caramel ........... Sweet combo
```

---

## Confirmation Message Flow

### User Order Confirmation (After Selection)
```
✅ Shake Order Summary

👤 Name: John Doe
🥤 Selected: Kulfi
💳 Credits Deduction: -1
💰 Current Balance: 5
💰 Balance After: 4
📅 Date: 17-Jan-2026
⏰ Time: 03:30 PM

⏳ Status: Pending Admin Approval

Your shake request has been sent to admin for approval.
```

### Admin Approval Notification
```
🔔 NEW SHAKE ORDER - PENDING APPROVAL

👤 User: John Doe
📱 Telegram ID: 123456789
🥤 Flavor: Kulfi
📋 Request ID: #47
📅 Date: 17-Jan-2026
⏰ Time: 03:30 PM

⏳ Status: PENDING YOUR APPROVAL
```

### User Ready Notification (After Admin Approve)
```
✅ YOUR SHAKE IS READY!

🥤 Flavor: Kulfi
💳 Credits Deducted: 1
💰 Remaining Balance: 4
📅 Date: 17-Jan-2026
⏰ Time: 03:30 PM
📋 Request ID: #47

Your shake has been approved and is ready for pickup! 🎉
```

### Admin Approval Confirmation
```
✅ SHAKE APPROVED & READY

👤 User: John Doe
📱 ID: 123456789
🥤 Flavor: Kulfi
📋 Request ID: #47
💰 Credits Deducted: 1
💰 User Balance: 4

✅ Status: READY FOR PICKUP
```

### User Final Confirmation (After Delivery)
```
🎉 SHAKE DELIVERY COMPLETE!

👤 Name: John Doe
🥤 Flavor: Kulfi
💳 Credits Deducted: 1
💰 Current Balance: 4
📅 Date: 17-Jan-2026
📋 Request ID: #47

✅ Status: COMPLETED

Thank you for choosing our shakes! 💪
```

---

## Test Scenarios

### Scenario 1: Happy Path (All Steps)
```
1. User orders → Gets confirmation
2. Credit deducted → Balance shows -1
3. Admin notified → See pending order
4. Admin approves → User & admin get notifications
5. Admin completes → User gets final message

✅ Expected: 5 messages total (3 user + 2 admin)
```

### Scenario 2: No Credits
```
1. User taps "Order Shake"
2. If balance = 0:
   ❌ No Credits Available
   You need 1 credit minimum
   [💾 Buy Credits]

✅ Expected: Error message + buy credits button
```

### Scenario 3: Not Approved
```
1. Unapproved user taps "Order Shake"
2. Response:
   ⏳ Registration Pending Approval
   Contact admin before ordering shakes

✅ Expected: Block with approval message
```

### Scenario 4: Duplicate Approval (Guard)
```
1. Admin approves shake
2. Admin taps approve again immediately
   ⚠️ This shake was already approved

✅ Expected: Warning, no duplicate in DB
```

---

## Database Checks

### Check Shake Flavors
```bash
python -c "
from src.database.connection import execute_query
flavors = execute_query('SELECT * FROM shake_flavors ORDER BY name ASC')
print('✅ Shake Flavors:')
for f in flavors:
    print(f'   {f[\"name\"]}')
"
```

**Expected**: 16 items showing all 9 items

### Check Orders Created
```sql
SELECT user_id, flavor_id, status, created_at 
FROM shake_requests 
WHERE created_at > NOW() - INTERVAL '1 hour'
ORDER BY created_at DESC;
```

**Expected**: Shows recent orders with status 'pending', 'ready', or 'completed'

### Check Credits Deducted
```sql
SELECT user_id, available_credits 
FROM shake_credits
WHERE user_id = <TEST_USER_ID>;
```

**Expected**: Shows reduced credits after order

---

## Expected Test Results

✅ **Test 1: User Can See Menu**
- Menu displays all 9 items
- Shows current balance
- Shows shakes this month count

✅ **Test 2: User Can Select Flavor**
- Selection confirmed with all details
- Date and time accurate
- Balance after calculation correct

✅ **Test 3: Credit Deducted Correctly**
- Balance decreases by exactly 1
- Database updated immediately
- Old balance shows in message

✅ **Test 4: Admin Gets Notification**
- Admin receives message with order details
- Contains user name, flavor, timestamp
- Has approval buttons

✅ **Test 5: Approval Sends Confirmations**
- User gets "ready" notification
- Admin gets approval confirmation
- Both have all required details

✅ **Test 6: Completion Works**
- Admin can mark complete
- User gets final "delivered" message
- Messages show all details

✅ **Test 7: Guards Work**
- Can't order without credits
- Can't order without approval
- Can't duplicate approvals
- All error messages clear

---

## Timestamps in Messages

**Format**: `DD-Mmm-YYYY HH:MM AM/PM`

Example: `17-Jan-2026 03:30 PM`

**Check**: Timestamps match bot server time

---

## Telegram Commands

```
/start    → Welcome
/menu     → Show menu with "Order Shake" button
/whoami   → Check your role
/cancel   → Cancel operation
```

---

## File Structure

```
New/Modified:
✅ src/handlers/shake_order_handlers.py (NEW - 400+ lines)
✅ src/handlers/callback_handlers.py (MODIFIED - added imports & callbacks)
✅ migrate_add_shake_menu.py (NEW - adds 6 items)

Unchanged:
✓ src/bot.py
✓ src/database/shake_operations.py
✓ src/database/shake_credits_operations.py
```

---

## Success Checklist

- [ ] Bot starts without errors
- [ ] Menu shows 9 shake items
- [ ] Can select a flavor
- [ ] Confirmation shows correct details
- [ ] Credit deducted (-1) on confirm
- [ ] Admin receives notification
- [ ] Admin can approve
- [ ] User gets ready notification
- [ ] Admin gets approval confirmation
- [ ] Admin can mark complete
- [ ] User gets final delivery message
- [ ] All timestamps accurate
- [ ] Balance updates correct
- [ ] Can't order without credits
- [ ] Can't order without approval

---

## Troubleshooting Quick Reference

| Problem | Check | Solution |
|---------|-------|----------|
| Menu not showing | User registered? | Register first with /start |
| No credit balance shown | User has credits? | Buy credits first |
| Flavor not selectable | Selection works? | Tap flavor → confirm → deduct |
| Admin gets no notification | Admin ID set? | Check is_admin_id() in auth |
| No confirmation sent | Approval tapped? | Admin must tap approve button |
| Balance doesn't change | Confirm tapped? | Must confirm order to deduct |
| Timestamps wrong | Server time correct? | Check system time |

---

## Next Step

```bash
# 1. Start bot
python start_bot.py

# 2. Follow quick start above

# 3. Check database:
SELECT * FROM shake_requests 
WHERE created_at > NOW() - INTERVAL '1 hour';

# 4. If all pass → ready for production
```

---

**Total Testing Time**: 15-20 minutes  
**Expected Messages**: 5+ per order  
**All Details Included**: ✅ YES
