# 🥤 Shake Credit System - Complete File Index

## 📍 Quick Navigation

### Documentation (Read These First)
1. [SHAKE_CREDIT_IMPLEMENTATION_SUMMARY.md](SHAKE_CREDIT_IMPLEMENTATION_SUMMARY.md) - **START HERE** - Complete overview
2. [SHAKE_CREDIT_SYSTEM_DEPLOYED.md](SHAKE_CREDIT_SYSTEM_DEPLOYED.md) - Full technical documentation
3. [SHAKE_CREDIT_QUICK_TEST.md](SHAKE_CREDIT_QUICK_TEST.md) - Testing guide with examples

---

## 🗄️ Database Files

### Migration & Initialization
| File | Purpose | Status |
|------|---------|--------|
| `migrate_shake_credits.py` | Creates 3 tables + indexes | ✅ Executed |
| `init_shake_credits.py` | Initialize user credits | ✅ Completed |

### Database Schema
| Table | Columns | Purpose |
|-------|---------|---------|
| `shake_credits` | credit_id, user_id, total_credits, used_credits, available_credits, last_updated | User balance tracking |
| `shake_transactions` | transaction_id, user_id, credit_change, transaction_type, description, reference_date, created_at | Complete transaction log |
| `shake_purchases` | purchase_id, user_id, credits_requested, amount, status, approved_by, approved_at, created_at | Purchase workflow |

---

## 💻 Code Files

### Database Operations Layer
**File:** `src/database/shake_credits_operations.py`

**Functions (14 total):**

| Function | Parameters | Returns | Purpose |
|----------|-----------|---------|---------|
| `init_user_credits(user_id)` | user_id | void | Initialize 0 balance for new user |
| `get_user_credits(user_id)` | user_id | dict | Get user's total, used, available credits |
| `add_credits(user_id, credits, type, desc)` | user_id, amount, type, description | int | Add credits (purchase/referral/gift) |
| `consume_credit(user_id, reason)` | user_id, reason | bool | Deduct 1 credit (auto on shake order) |
| `consume_credit_with_date(uid, date, reason)` | user_id, date, reason | bool | Admin deduction with date |
| `create_purchase_request(user_id, credits)` | user_id, credits | int | Create purchase request (25 credits for Rs 6000) |
| `get_pending_purchase_requests(limit)` | limit=10 | list | Get all pending requests for admin |
| `approve_purchase(purchase_id, admin_id)` | purchase_id, admin_id | bool | Approve and transfer credits |
| `reject_purchase(purchase_id, admin_id)` | purchase_id, admin_id | bool | Reject purchase request |
| `get_shake_report(user_id)` | user_id | dict | Get user's transaction history |
| `get_all_user_reports()` | none | list | Get all users' reports |
| `_log_transaction(uid, change, type, desc, date)` | Internal | void | Log transaction internally |
| `_update_balance(user_id)` | Internal | void | Recalculate balance internally |

**Constants:**
```python
CREDIT_COST = 6000              # Rs 6000 per package
CREDITS_PER_PURCHASE = 25       # 25 credits per package
COST_PER_CREDIT = 240           # Rs 240 per credit
```

---

### User & Admin Handlers
**File:** `src/handlers/shake_credit_handlers.py`

**User Commands:**

| Function | Triggers | Buttons Shown | Actions |
|----------|----------|---------------|---------|
| `cmd_buy_shake_credits()` | "💾 Buy Shake Credits" button | ✅ Confirm (25 credits) | Create purchase request |
| `cmd_check_shake_credits()` | "🥤 Check Shake Credits" button | 🥛 Order, 💾 Buy, 📊 Report | Show balance + actions |
| `cmd_order_shake()` | "🥛 Order Shake" button | Flavor buttons | Check credits, show options |
| `cmd_shake_report()` | "📊 Shake Report" button | Print report | Show transaction history |

**Admin Commands:**

| Function | Triggers | Display | Actions |
|----------|----------|---------|---------|
| `cmd_admin_pending_purchases()` | "🥤 Pending Shake Purchases" button | Purchase list | ✅ Approve / ❌ Reject |

**Helper Functions:**
- `process_shake_order(user_id, flavor_id, context)` - Place shake order, deduct credit

**Conversation States:**
```python
BUY_CREDITS = 0              # Buying credits flow
CONFIRM_PURCHASE = 1         # Confirming Rs 6000 purchase
ORDER_SHAKE_FLAVOR = 2       # Selecting shake flavor
ADMIN_SELECT_USER_DATE = 3   # Admin selecting user & date
```

---

### Callback Routing
**File:** `src/handlers/callback_handlers.py`

**Routes Added (15+ callbacks):**

| Callback | Handler | Action |
|----------|---------|--------|
| `cmd_check_shake_credits` | → cmd_check_shake_credits() | Show balance |
| `cmd_order_shake` | → cmd_order_shake() | Show flavors |
| `cmd_buy_shake_credits` | → cmd_buy_shake_credits() | Buy dialog |
| `cmd_shake_report` | → cmd_shake_report() | Show report |
| `cmd_admin_pending_purchases` | → cmd_admin_pending_purchases() | Admin queue |
| `confirm_buy_25` | → create_purchase_request() | Create request |
| `approve_purchase_*` | → approve_purchase() | Transfer credits |
| `reject_purchase_*` | → reject_purchase() | Reject |
| `order_flavor_*` | → process_shake_order() | Place order |

---

### Menu Integration
**File:** `src/handlers/role_keyboard_handlers.py`

**User Menu Addition:**
```python
USER_MENU buttons += [
    "🥤 Check Shake Credits",      # New
    "🥛 Order Shake",               # New
    "💾 Buy Shake Credits"          # New
]
# Now 16 buttons total
```

**Admin Menu Addition:**
```python
ADMIN_MENU buttons += [
    "🥤 Pending Shake Purchases",   # New
    "🍽️ Manual Shake Deduction"     # New
]
# Now 20 buttons total
```

---

## 🔄 Data Flow Diagrams

### Purchase Flow:
```
User clicks "💾 Buy Shake Credits"
    ↓
    ConversationHandler: BUY_CREDITS state
    ↓
    Shows: "Purchase 25 credits for Rs 6000?"
    ↓
    User clicks "✅ Confirm Purchase"
    ↓
    Callback: confirm_buy_25
    ↓
    create_purchase_request(user_id, 25)
    ↓
    Database: INSERT into shake_purchases (status='pending')
    ↓
    User message: "✅ Purchase request created! Pending admin approval"
    ↓
    Admin sees in "🥤 Pending Shake Purchases"
    ↓
    Admin clicks "✅ Approve"
    ↓
    Callback: approve_purchase_<id>
    ↓
    approve_purchase(purchase_id, admin_id)
    ↓
    Database: 
      - UPDATE shake_purchases SET status='approved'
      - INSERT into shake_transactions (type='purchase', change=+25)
      - UPDATE shake_credits SET total=total+25, available=available+25
    ↓
    User notified: "✅ Your purchase of 25 credits has been approved!"
    ↓
    User balance updated to 25 available
```

### Order Flow:
```
User clicks "🥛 Order Shake"
    ↓
    ConversationHandler: ORDER_SHAKE_FLAVOR state
    ↓
    Check: Does user have credits?
    ↓
    If NO → "❌ You don't have credits to order"
    If YES → Show flavor buttons
    ↓
    User selects flavor (e.g., 🍓 Strawberry)
    ↓
    Callback: order_flavor_<id>
    ↓
    process_shake_order(user_id, flavor_id, context)
    ↓
    Database:
      - INSERT into shake_requests (status='ordered')
      - consume_credit(user_id, 'shake_order')
      - INSERT into shake_transactions (type='consume', change=-1)
      - UPDATE shake_credits SET used_credits=used_credits+1, available=available-1
    ↓
    User message: "✅ Shake order placed! 1 credit deducted. Balance: 24 credits"
    ↓
    Order complete
```

### Manual Deduction Flow:
```
Admin clicks "🍽️ Manual Shake Deduction"
    ↓
    ConversationHandler: ADMIN_SELECT_USER_DATE state
    ↓
    Admin enters user ID
    ↓
    Calendar picker appears
    ↓
    Admin selects date (e.g., 2026-01-15)
    ↓
    consume_credit_with_date(user_id, '2026-01-15', 'admin_deduction')
    ↓
    Database:
      - INSERT into shake_transactions (
          type='admin_deduction', 
          change=-1, 
          reference_date='2026-01-15'
        )
      - UPDATE shake_credits SET used_credits=used_credits+1
    ↓
    Message: "✅ 1 credit deducted from user with date 2026-01-15"
    ↓
    User can see in report: admin_deduction on 2026-01-15
```

---

## 🧩 Integration Points

### With User Operations:
- `get_user(user_id)` - Get user info before credit operations
- `user_exists(user_id)` - Verify user before creating credits

### With Activity Handlers:
- Called after shake order (`cmd_order_shake`)
- Updates points on shake order (if configured)
- Logs to activity history

### With Role Handlers:
- `get_user_role(user_id)` - Verify admin for approvals
- `is_admin_id(admin_id)` - Security check
- Menu buttons shown based on role

### With Callback Routing:
- All shake callbacks routed through `handle_callback_query`
- Error handling for missing users/credits

### With Database Connection:
- All operations use `execute_query()`
- Transactions auto-committed
- Error logging on failures

---

## 📊 Sample Data Queries

### Get User Balance:
```python
from src.database.shake_credits_operations import get_user_credits
balance = get_user_credits(1206519616)
# Returns: {
#     'total_credits': 25,
#     'used_credits': 1,
#     'available_credits': 24
# }
```

### Create Purchase Request:
```python
from src.database.shake_credits_operations import create_purchase_request
purchase_id = create_purchase_request(1206519616, 25)
# Returns: purchase_id (int)
# Creates: 1 row in shake_purchases with status='pending'
```

### Approve Purchase:
```python
from src.database.shake_credits_operations import approve_purchase
success = approve_purchase(purchase_id, admin_user_id)
# Returns: True/False
# Updates: shake_purchases status='approved'
# Adds: +25 credits to user
# Logs: transaction of type='purchase'
```

### Consume Credit:
```python
from src.database.shake_credits_operations import consume_credit
success = consume_credit(1206519616, 'shake_order')
# Returns: True/False
# Logs: transaction of type='consume'
# Updates: balance automatically
```

### Get Transactions:
```python
from src.database.shake_credits_operations import get_shake_report
report = get_shake_report(1206519616)
# Returns: {
#     'total_credits': 25,
#     'used_credits': 1,
#     'available_credits': 24,
#     'transactions': [
#         {
#             'type': 'purchase',
#             'change': +25,
#             'date': '2026-01-16',
#             'description': 'Purchased 25 credits'
#         },
#         {
#             'type': 'consume',
#             'change': -1,
#             'date': '2026-01-16',
#             'description': 'Shake order placed'
#         }
#     ]
# }
```

---

## 🔍 Debugging Guide

### Check if Tables Exist:
```sql
SELECT tablename FROM pg_tables WHERE tablename LIKE 'shake_%';
```

### View User Credits:
```sql
SELECT user_id, total_credits, used_credits, available_credits 
FROM shake_credits 
WHERE user_id = 1206519616;
```

### View Pending Purchases:
```sql
SELECT * FROM shake_purchases 
WHERE status = 'pending' 
ORDER BY created_at DESC;
```

### View All Transactions for User:
```sql
SELECT * FROM shake_transactions 
WHERE user_id = 1206519616 
ORDER BY created_at DESC;
```

### Check Bot Logs:
```bash
# View recent logs
tail -f logs/bot.log

# Search for shake operations
grep -i "shake" logs/*.log

# Search for errors
grep "ERROR" logs/*.log
```

---

## ✅ Verification Checklist

Use this to verify the system is working:

- [ ] **Tables Created:** All 3 tables exist in database
- [ ] **Indexes Created:** 4 indexes exist for performance
- [ ] **User Credits:** User has 0 credits after init_shake_credits.py
- [ ] **Menu Buttons:** 3 buttons in user menu, 2 in admin menu
- [ ] **Callbacks Routed:** All 15+ callbacks accessible
- [ ] **Purchase Flow:** Can create and approve purchases
- [ ] **Order Flow:** Can order shakes with credits
- [ ] **Manual Deduction:** Can deduct credits with date
- [ ] **Transaction Log:** All transactions appear in database
- [ ] **User Notifications:** Users receive confirmation messages
- [ ] **Admin Notifications:** Admins see pending requests
- [ ] **Balance Calculation:** Auto-calculated correctly

---

## 📞 Quick Help

### "User doesn't see shake buttons"
1. Check bot is running: `ps aux | grep python`
2. Verify bot was restarted after code changes
3. Check user role: `SELECT role FROM users WHERE user_id = <id>`
4. Try `/menu` again in Telegram

### "Credits not deducted"
1. Check user has available credits: `SELECT * FROM shake_credits WHERE user_id = <id>`
2. Check database connection: `python init_db.py`
3. View logs: `grep -i "consume" logs/*.log`
4. Restart bot

### "Transactions not showing"
1. Check table has data: `SELECT COUNT(*) FROM shake_transactions;`
2. Verify user_id in transactions: `SELECT DISTINCT user_id FROM shake_transactions;`
3. Check transaction_type values: `SELECT DISTINCT transaction_type FROM shake_transactions;`

---

## 🎯 Key Constants

| Constant | Value | File | Line |
|----------|-------|------|------|
| CREDIT_COST | 6000 | shake_credits_operations.py | ~10 |
| CREDITS_PER_PURCHASE | 25 | shake_credits_operations.py | ~11 |
| COST_PER_CREDIT | 240 | shake_credits_operations.py | ~12 |

To change: Edit constants and restart bot.

---

## 📁 Directory Structure

```
fitness-club-telegram-bot/
├── migrate_shake_credits.py                 ← Migration script
├── init_shake_credits.py                    ← User initialization
├── src/
│   ├── database/
│   │   └── shake_credits_operations.py      ← Database layer (14 functions)
│   └── handlers/
│       ├── shake_credit_handlers.py         ← User/admin handlers (9 features)
│       ├── role_keyboard_handlers.py        ← Menu integration (modified)
│       └── callback_handlers.py             ← Callback routing (modified)
├── SHAKE_CREDIT_IMPLEMENTATION_SUMMARY.md   ← Overview
├── SHAKE_CREDIT_SYSTEM_DEPLOYED.md          ← Technical docs
├── SHAKE_CREDIT_QUICK_TEST.md               ← Testing guide
└── SHAKE_CREDIT_FILES_INDEX.md              ← This file
```

---

## 🚀 System Status

| Component | Status | Details |
|-----------|--------|---------|
| **Database** | ✅ Live | 3 tables, 4 indexes |
| **Operations** | ✅ Active | 14 functions |
| **Handlers** | ✅ Active | 9 features |
| **Callbacks** | ✅ Routed | 15+ routes |
| **Bot** | ✅ Running | Latest version |
| **API** | ✅ Connected | Telegram API OK |

---

**Last Updated:** 2026-01-16 23:23 UTC  
**System Version:** 1.0  
**Status:** ✅ LIVE

For questions or issues, refer to the main documentation files or contact support.
