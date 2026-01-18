# Shake Credits Payment Flow - Implementation Complete

## Overview
Fixed the shake credits purchase system to match the subscription payment flow with:
- ✅ Payment method selection (Cash/UPI)
- ✅ Admin amount entry for partial payments
- ✅ Part payment support with discount calculation  
- ✅ Store menu for users and admins
- ✅ Database migration completed

## Changes Made

### 1. Database Schema Update
**File:** `migrate_shake_payments.py` (NEW)

Added columns to `shake_purchases` table:
- `payment_method` VARCHAR(10) - Stores 'cash', 'upi', or 'unknown'
- `amount_paid` DECIMAL(10,2) - Stores actual amount received (for partial payments)

**Run Migration:**
```bash
python migrate_shake_payments.py
```

**Result:**
```
✅ payment_method column added
✅ amount_paid column added
```

---

### 2. Database Operations Updated
**File:** [src/database/shake_credits_operations.py](src/database/shake_credits_operations.py)

#### Updated Functions:

**`create_purchase_request(user_id, credits, payment_method='unknown')`**
- Added `payment_method` parameter
- Stores payment method when creating purchase request

**`get_pending_purchase_requests()`**
- Now includes `payment_method` in query results

**`approve_purchase(purchase_id, admin_user_id, amount_paid=None)`**
- Added `amount_paid` parameter for partial payments
- Calculates discount automatically: `discount = amount - amount_paid`
- Updates AR receivable with correct discount and final amount
- Records transaction with actual payment method (not 'unknown')

**Key Changes:**
```python
# Before
def create_purchase_request(user_id: int, credits: int) -> dict:
    ...
    
# After  
def create_purchase_request(user_id: int, credits: int, payment_method: str = 'unknown') -> dict:
    ...
```

---

### 3. Handler Updates
**File:** [src/handlers/shake_credit_handlers.py](src/handlers/shake_credit_handlers.py)

#### New Conversation States:
```python
BUY_CREDITS, CONFIRM_PURCHASE, SELECT_PAYMENT_METHOD, ENTER_UPI_ID, 
ORDER_SHAKE_FLAVOR, ADMIN_SELECT_USER_DATE, ADMIN_ENTER_AMOUNT = range(7)
```

#### New Functions Added:

**`callback_approve_shake_purchase(update, context)`**
- Admin starts approval process
- Asks admin to enter amount received
- Shows purchase details and expected amount

**`handle_shake_approval_amount(update, context)`**
- Handles admin's amount input
- Validates amount > 0
- Approves purchase with actual amount paid
- Calculates discount automatically
- Notifies user of approval

**`callback_reject_shake_purchase(update, context)`**
- Admin rejects purchase request
- Updates status to 'rejected'

**Admin Amount Entry Flow:**
```
1. Admin clicks "✅ Approve" on pending purchase
2. Bot asks: "Enter Amount Received"
3. Admin replies: 6000 (or partial amount like 5000)
4. Bot approves with discount calculation
5. User gets notification with credits added
```

---

### 4. Callback Routing
**File:** [src/handlers/callback_handlers.py](src/handlers/callback_handlers.py)

#### New Imports:
```python
from src.handlers.shake_credit_handlers import (
    cmd_buy_shake_credits, cmd_check_shake_credits, cmd_shake_report,
    cmd_admin_pending_purchases, process_shake_order,
    callback_confirm_buy_credits,          # NEW
    callback_select_shake_payment,         # NEW
    callback_approve_shake_purchase,       # NEW
    callback_reject_shake_purchase         # NEW
)
```

#### New Callback Patterns:
```python
elif query.data == "confirm_buy_25":
    await callback_confirm_buy_credits(update, context)
elif query.data.startswith("shake_pay_"):
    await callback_select_shake_payment(update, context)
elif query.data.startswith("approve_shake_purchase_"):
    await callback_approve_shake_purchase(update, context)
elif query.data.startswith("reject_shake_purchase_"):
    await callback_reject_shake_purchase(update, context)
```

---

### 5. Store Menu Added
**Files:** 
- [src/handlers/role_keyboard_handlers.py](src/handlers/role_keyboard_handlers.py)
- [src/handlers/commerce_hub_handlers.py](src/handlers/commerce_hub_handlers.py)
- [src/handlers/callback_handlers.py](src/handlers/callback_handlers.py)

#### User Menu Button:
```python
[InlineKeyboardButton("🛒 Store", callback_data="cmd_user_store")],
```

#### Admin Menu Buttons:
```python
[InlineKeyboardButton("💳 Pending Shake Purchases", callback_data="cmd_pending_shake_purchases")],
[InlineKeyboardButton("🛒 Manage Store", callback_data="cmd_manage_store")],
```

#### New Function: `cmd_user_store(update, context)`
- Shows all active store products
- Displays product categories
- Shows MRP, discount, final price
- Shows stock availability
- Message: "Contact admin to purchase products"

---

## User Flow (Complete Purchase Journey)

### User Side:
```
1. User clicks "💾 Buy Shake Credits" from menu
   └─ Shows: "🥤 Buy Shake Credits"
          "💵 Price: Rs 6000 for 25 credits"
          "💰 Cost per credit: Rs 240"
   
2. User clicks "✅ 25 Credits"
   └─ Shows: "💳 Select Payment Method"
          Options: "💵 Cash Payment" or "📱 UPI Payment"

3. User selects "💵 Cash"
   └─ Shows: "✅ Purchase Request Created"
          "🥤 Credits: 25"
          "💵 Amount: Rs 6000.00"
          "⏳ Status: Pending Admin Approval"

4. [Admin approves - see below]

5. User receives: "✅ Your Shake Credit Purchase is Approved!"
                  "🥤 25 credits added to your account"
                  "✅ Available to use now!"
```

### Admin Side:
```
1. Admin clicks "💳 Pending Shake Purchases" from menu
   └─ Shows first pending purchase with user details

2. Admin clicks "✅ Approve"
   └─ Bot asks: "*💰 Enter Amount Received*"
          "User: John Doe"
          "Credits: 25"
          "Expected: Rs 6,000"
          "Please reply with the amount you received"
          "💡 For part payment, enter the actual amount received"

3. Admin replies: 5000 (or 6000 for full payment)
   └─ Bot processes:
      • Adds 25 credits to user
      • Creates AR receivable with Rs 1000 discount
      • Records payment method as 'cash'
      • Notifies user

4. Admin sees: "✅ Shake Purchase Approved!"
               "User: John Doe"
               "Credits: 25"
               "Amount: Rs 5,000.00"
               "💸 Discount: Rs 1,000.00"
               "Credits have been added to user's account"
```

---

## Part Payment Example

**Scenario:** User buys 25 credits (Rs 6000) but pays Rs 5000

**Database Records:**
```sql
-- shake_purchases table
purchase_id: 1
amount: 6000.00
payment_method: 'cash'
amount_paid: 5000.00
status: 'approved'

-- shake_credits table (user credits updated)
total_credits: 25
available_credits: 25

-- ar_receivables table
bill_amount: 6000.00
discount_amount: 1000.00
final_amount: 5000.00
amount_collected: 5000.00
status: 'paid'
```

**Result:** User gets 25 credits, AR shows Rs 1000 discount, fully paid status

---

## Store Menu Features

### User Store View:
```
🛒 *Store Products*

*Supplements*
• *Whey Protein*
  High-quality whey protein powder
  Price: ~~Rs 3500~~ → *Rs 2800* (-20%)
  ✅ In Stock (10)

• *BCAA*
  Essential amino acids
  Price: ~~Rs 1500~~ → *Rs 1200* (-20%)
  ❌ Out of Stock

💬 Contact admin to purchase products.
```

### Admin Store Management:
```
🛒 *Manage Store Products*

📥 Download Sample Excel
📤 Bulk Upload Products
📋 List Products
⬅️ Back
```

---

## Testing the Implementation

### Test Payment Flow:
1. **As User:**
   - Open bot → Click "💾 Buy Shake Credits"
   - Select "✅ 25 Credits"
   - Choose "💵 Cash Payment"
   - Verify: "✅ Purchase Request Created" message appears

2. **As Admin:**
   - Click "💳 Pending Shake Purchases"
   - Click "✅ Approve"
   - Reply with amount: 6000
   - Verify: User receives approval notification

3. **Test Part Payment:**
   - Repeat above, but reply with: 5000
   - Verify: Discount Rs 1000 shown
   - Check AR: `discount_amount` should be 1000

### Test Store Menu:
1. **As User:**
   - Click "🛒 Store" from menu
   - Verify: Products displayed with prices

2. **As Admin:**
   - Click "🛒 Manage Store"
   - Verify: Management options appear

---

## Database Queries for Verification

### Check Shake Purchases:
```sql
SELECT 
    sp.purchase_id,
    u.full_name,
    sp.credits_requested,
    sp.amount,
    sp.payment_method,
    sp.amount_paid,
    sp.status,
    sp.created_at
FROM shake_purchases sp
JOIN users u ON sp.user_id = u.user_id
ORDER BY sp.created_at DESC
LIMIT 10;
```

### Check AR Integration:
```sql
SELECT 
    r.receivable_id,
    r.receivable_type,
    r.source_id as purchase_id,
    r.bill_amount,
    r.discount_amount,
    r.final_amount,
    r.amount_collected,
    r.status
FROM ar_receivables r
WHERE r.receivable_type = 'shake_credit'
ORDER BY r.created_at DESC;
```

### Check User Credits:
```sql
SELECT 
    u.full_name,
    sc.total_credits,
    sc.available_credits,
    sc.used_credits,
    sc.last_updated
FROM shake_credits sc
JOIN users u ON sc.user_id = u.user_id
ORDER BY sc.last_updated DESC;
```

---

## Files Modified

1. ✅ **migrate_shake_payments.py** (NEW) - Database migration
2. ✅ **src/database/shake_credits_operations.py** - Payment method support
3. ✅ **src/handlers/shake_credit_handlers.py** - Admin approval with amount entry
4. ✅ **src/handlers/callback_handlers.py** - New callback routing
5. ✅ **src/handlers/role_keyboard_handlers.py** - Store menu buttons (already existed)
6. ✅ **src/handlers/commerce_hub_handlers.py** - User store function

---

## Summary

### ✅ Issues Resolved:
1. **Payment Method Selection:** User can now choose Cash or UPI
2. **Admin Amount Entry:** Admin enters actual amount received
3. **Part Payment Support:** Automatic discount calculation
4. **Store Menu:** Available for both users and admins

### 🔄 Flow Changes:
- **Before:** Purchase request → Admin approve → Credits added
- **After:** Purchase request → Select payment → Admin enters amount → Credits added with discount

### 📊 Integration:
- ✅ AR System: Properly records receivables with discounts
- ✅ Payment Methods: Tracked ('cash', 'upi')
- ✅ Partial Payments: Supported with automatic discount
- ✅ User Notifications: Approval/rejection messages sent

### 🎯 Next Steps:
1. Test the complete flow with real users
2. Monitor AR reports for shake credit purchases
3. Verify discount calculations are correct
4. Add more payment methods if needed (bank transfer, etc.)

---

**Status:** ✅ **COMPLETE** - Bot running and accepting shake credit purchases with payment method selection and part payment support!

**Last Updated:** January 18, 2026 19:19 IST
