# 🏋️ Admin Dashboard Flow & Architecture

## 📋 Table of Contents
1. [Overview](#overview)
2. [Admin Flow Structure](#admin-flow-structure)
3. [Button Flow Diagrams](#button-flow-diagrams)
4. [Database Operations](#database-operations)
5. [Debugging Guide](#debugging-guide)
6. [Common Issues & Fixes](#common-issues--fixes)

---

## Overview

The Fitness Bot has a hierarchical role-based system with three main user types:
- **👤 User** (Regular Member)
- **👨‍💼 Staff** (Gym Staff)
- **🛡️ Admin** (Administrator)

Each role has a specific menu with relevant features.

---

## Admin Flow Structure

### 🎯 Entry Points

1. **Initial Access**
   ```
   User presses /start 
   → System checks role from database (users.role)
   → Shows appropriate menu (User/Staff/Admin)
   ```

2. **Menu Access**
   ```
   /menu command
   → role_keyboard_handlers.show_role_menu()
   → Displays role-specific inline buttons
   ```

### 🔐 Role Detection Flow

```python
# File: src/utils/auth.py
# File: src/database/role_operations.py

1. User ID received from Telegram
2. Query: SELECT role FROM users WHERE user_id = ?
3. Role values: 'user', 'staff', 'admin'
4. Display corresponding menu
```

**Key Functions:**
- `get_user_role(user_id)` → Returns 'admin', 'staff', or 'user'
- `is_admin(user_id)` → Returns True/False
- `is_staff(user_id)` → Returns True/False

---

## Button Flow Diagrams

### 👤 USER MENU FLOW

```
┌─────────────────────────────────────┐
│         👤 USER MENU                │
├─────────────────────────────────────┤
│ [📊 My Stats] [🔔 Notifications]   │
│ [⚖️ Weight]   [💧 Water]            │
│ [🍽️ Meals]    [💪 Habits]           │
│ [🏋️ Check-In] [🎯 Challenges]      │
│ [🆔 My QR]    [👤 Who Am I]         │
└─────────────────────────────────────┘
```

**Button → Handler Mapping:**

| Button | Callback Data | Handler | File |
|--------|---------------|---------|------|
| 📊 My Stats | `cmd_stats` | `callback_stats()` | callback_handlers.py |
| 🔔 Notifications | `cmd_notifications` | `cmd_notifications()` | notification_handlers.py |
| ⚖️ Weight | `cmd_weight` | `cmd_weight()` | activity_handlers.py |
| 💧 Water | `cmd_water` | `cmd_water()` | activity_handlers.py |
| 🍽️ Meals | `cmd_meal` | `cmd_meal()` | activity_handlers.py |
| 💪 Habits | `cmd_habits` | `cmd_habits()` | activity_handlers.py |
| 🏋️ Check-In | `cmd_checkin` | `cmd_checkin()` | activity_handlers.py |
| 🎯 Challenges | `cmd_challenges` | `cmd_challenges()` | challenge_handlers.py |
| 🆔 My QR | `cmd_qrcode` | `cmd_qrcode()` | user_handlers.py |
| 👤 Who Am I | `cmd_whoami` | `cmd_whoami()` | misc_handlers.py |

---

### 👨‍💼 STAFF MENU FLOW

```
┌─────────────────────────────────────┐
│         👨‍💼 STAFF MENU              │
├─────────────────────────────────────┤
│ [📊 My Stats] [🔔 Notifications]   │
│ [⚖️ Weight]   [💧 Water]            │
│ [🍽️ Meals]    [💪 Habits]           │
│ [🏋️ Check-In] [🎯 Challenges]      │
│ [🆔 My QR]    [👤 Who Am I]         │
│ ───────────────────────────────     │
│ STAFF FUNCTIONS:                    │
│ [✅ Pending Attendance]             │
│ [🥛 Pending Shakes]                 │
└─────────────────────────────────────┘
```

**Staff-Only Buttons:**

| Button | Callback Data | Handler | Purpose |
|--------|---------------|---------|---------|
| ✅ Pending Attendance | `cmd_pending_attendance` | `cmd_pending_attendance()` | Review gym check-ins |
| 🥛 Pending Shakes | `cmd_pending_shakes` | `cmd_pending_shakes()` | Review shake orders |

---

### 🛡️ ADMIN MENU FLOW

```
┌─────────────────────────────────────┐
│         🛡️ ADMIN MENU               │
├─────────────────────────────────────┤
│ [📊 My Stats] [🔔 Notifications]   │
│ [⚖️ Weight]   [💧 Water]            │
│ [🍽️ Meals]    [💪 Habits]           │
│ [🏋️ Check-In] [🎯 Challenges]      │
│ [🆔 My QR]    [👤 Who Am I]         │
│ ───────────────────────────────     │
│ STAFF FUNCTIONS:                    │
│ [✅ Pending Attendance]             │
│ [🥛 Pending Shakes]                 │
│ ───────────────────────────────     │
│ ADMIN FUNCTIONS:                    │
│ [📊 Admin Dashboard]                │
│ [🔐 Role Management]                │
│    ├─ Add Admin                     │
│    ├─ Remove Admin                  │
│    ├─ Add Staff                     │
│    ├─ Remove Staff                  │
│    └─ List Roles                    │
└─────────────────────────────────────┘
```

---

## 📊 Admin Dashboard Flow (Detailed)

### Main Dashboard

```
┌─────────────────────────────────────┐
│      📊 ADMIN DASHBOARD             │
├─────────────────────────────────────┤
│ [💰 Revenue Stats] [👥 Member Stats]│
│ [📊 Engagement]    [🏆 Challenges]  │
│ [🔥 Top Activities]                 │
└─────────────────────────────────────┘
```

### Flow Diagram

```
User clicks "📊 Admin Dashboard"
    │
    ├─→ callback_data: "cmd_admin_dashboard"
    │
    ├─→ Handler: cmd_admin_dashboard()
    │   File: src/handlers/analytics_handlers.py
    │
    ├─→ Check: is_admin(user_id)
    │   ├─ YES → Show dashboard menu
    │   └─ NO  → "❌ Admin access only"
    │
    └─→ Display 5 report options

User clicks report button
    │
    ├─→ [💰 Revenue Stats]
    │   ├─ callback_data: "dashboard_revenue"
    │   ├─ Handler: callback_revenue_stats()
    │   ├─ DB: get_revenue_stats(), get_monthly_revenue()
    │   └─ Shows: Total revenue, payments, avg payment
    │
    ├─→ [👥 Member Stats]
    │   ├─ callback_data: "dashboard_members"
    │   ├─ Handler: callback_member_stats()
    │   ├─ DB: get_platform_statistics(), get_active_members_count()
    │   └─ Shows: Total users, active members, avg points
    │
    ├─→ [📊 Engagement]
    │   ├─ callback_data: "dashboard_engagement"
    │   ├─ Handler: callback_engagement_stats()
    │   ├─ DB: get_engagement_metrics()
    │   └─ Shows: Active users, paid members, total points
    │
    ├─→ [🏆 Challenges]
    │   ├─ callback_data: "dashboard_challenges"
    │   ├─ Handler: callback_challenge_stats()
    │   ├─ DB: get_challenge_stats()
    │   └─ Shows: Total/active challenges, participants
    │
    └─→ [🔥 Top Activities]
        ├─ callback_data: "dashboard_activities"
        ├─ Handler: callback_top_activities()
        ├─ DB: get_top_activities()
        └─ Shows: Most popular activities
```

---

## Database Operations

### Admin Dashboard Queries

#### 1. Revenue Stats
```sql
-- get_revenue_stats()
SELECT 
    COUNT(*) as total_payments,
    SUM(amount) as total_revenue,
    AVG(amount) as avg_payment,
    COUNT(DISTINCT user_id) as unique_payers
FROM payments
WHERE status = 'completed'

-- get_monthly_revenue()
SELECT 
    SUM(amount) as monthly_revenue,
    COUNT(*) as transaction_count,
    COUNT(DISTINCT user_id) as payers
FROM payments
WHERE status = 'completed'
  AND payment_date >= DATE_TRUNC('month', CURRENT_DATE)
```

#### 2. Member Stats
```sql
-- get_platform_statistics()
SELECT 
    COUNT(*) as total_users,
    COUNT(CASE WHEN is_active = TRUE THEN 1 END) as active_members,
    AVG(points) as avg_points,
    COUNT(CASE WHEN last_activity_date = CURRENT_DATE THEN 1 END) as today_users
FROM users
```

#### 3. Engagement Metrics
```sql
-- get_engagement_metrics()
SELECT 
    COUNT(DISTINCT user_id) as active_users,
    COUNT(DISTINCT CASE WHEN has_paid = TRUE THEN user_id END) as paid_members,
    SUM(points_earned) as total_points_awarded,
    COUNT(*) as total_transactions,
    AVG(points_earned) as avg_points_per_activity
FROM activity_logs
WHERE activity_date >= CURRENT_DATE - INTERVAL '30 days'
```

#### 4. Challenge Stats
```sql
-- get_challenge_stats()
SELECT 
    COUNT(*) as total_challenges,
    COUNT(CASE WHEN status = 'active' THEN 1 END) as active_challenges,
    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_challenges,
    COUNT(DISTINCT user_id) as active_participants
FROM challenges
LEFT JOIN challenge_participants ON challenges.id = challenge_participants.challenge_id
```

---

## Debugging Guide

### 🔍 How to Debug Button Flows

#### 1. Enable Detailed Logging

Add to your handlers:
```python
import logging
logger = logging.getLogger(__name__)

async def your_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"Handler called by user {user_id}")
    
    if update.callback_query:
        logger.info(f"Callback data: {update.callback_query.data}")
    
    # Your code here
```

#### 2. Check Current Logs

```bash
# View live logs
tail -f logs/fitness_bot.log

# Search for errors
grep "ERROR" logs/fitness_bot.log

# Search for specific user
grep "user_id: 424837855" logs/fitness_bot.log
```

#### 3. Test Role Detection

```python
# In Python console or test script
from src.database.role_operations import get_user_role

user_id = 424837855
role = get_user_role(user_id)
print(f"User {user_id} has role: {role}")
```

#### 4. Verify Database Queries

```sql
-- Check user's role
SELECT user_id, full_name, role FROM users WHERE user_id = 424837855;

-- Check all admins
SELECT user_id, full_name, role FROM users WHERE role = 'admin';

-- Check all staff
SELECT user_id, full_name, role FROM users WHERE role = 'staff';
```

---

## Common Issues & Fixes

### ❌ Issue 1: "AttributeError: 'NoneType' object has no attribute 'reply_text'"

**Cause:** Handler expects `update.message` but receives `update.callback_query`

**Fix:**
```python
# ❌ Wrong
async def my_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello")

# ✅ Correct
async def my_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        message = update.callback_query.message
    else:
        message = update.message
    
    await message.reply_text("Hello")
```

---

### ❌ Issue 2: "TypeError: object bool can't be used in 'await' expression"

**Cause:** Trying to await a non-async function

**Fix:**
```python
# ❌ Wrong
if not await is_admin(user_id):
    return

# ✅ Correct
if not is_admin(user_id):
    return
```

---

### ❌ Issue 3: "Admin still shows as User"

**Cause:** Role not set in database

**Fix:**
```python
# Run the set_admin_role.py script
python set_admin_role.py

# Or manually in database:
UPDATE users SET role = 'admin' WHERE user_id = 424837855;
```

---

### ❌ Issue 4: "Button does nothing when clicked"

**Debugging Steps:**

1. Check if callback is registered:
```python
# In src/handlers/callback_handlers.py
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    logger.info(f"Received callback: {query.data}")  # Add this
    # ... rest of code
```

2. Verify callback_data matches:
```python
# Button definition
InlineKeyboardButton("Test", callback_data="cmd_test")

# Handler
elif query.data == "cmd_test":
    await cmd_test(update, context)
```

3. Check handler is imported:
```python
# At top of callback_handlers.py
from src.handlers.admin_handlers import cmd_pending_attendance
```

---

## 📝 Handler Registration Checklist

When adding new button:

- [ ] Define button in menu (role_keyboard_handlers.py)
- [ ] Create handler function
- [ ] Add callback routing in callback_handlers.py
- [ ] Handle both command and callback contexts
- [ ] Add role check if needed
- [ ] Test with actual user
- [ ] Check logs for errors

---

## 🔄 Complete Request/Response Flow

```
User Action (Button Click)
    ↓
Telegram sends CallbackQuery to bot
    ↓
bot.py receives update
    ↓
CallbackQueryHandler routes to handle_callback_query()
    ↓
handle_callback_query() checks query.data
    ↓
Routes to specific handler (e.g., cmd_admin_dashboard)
    ↓
Handler:
  1. Answers callback query
  2. Checks permissions (is_admin/is_staff)
  3. Queries database
  4. Formats response
  5. Sends message with new buttons
    ↓
User sees response in Telegram
```

---

## 📊 Architecture Summary

```
┌────────────────────────────────────────────┐
│              User Interface                │
│         (Telegram Mobile App)              │
└───────────────┬────────────────────────────┘
                │
                ↓
┌────────────────────────────────────────────┐
│           Telegram Bot API                 │
└───────────────┬────────────────────────────┘
                │
                ↓
┌────────────────────────────────────────────┐
│         src/bot.py (Main Entry)            │
│  - Application setup                       │
│  - Handler registration                    │
│  - ConversationHandlers                    │
└───────────────┬────────────────────────────┘
                │
                ↓
┌────────────────────────────────────────────┐
│      src/handlers/ (Request Routing)       │
│                                            │
│  ├─ callback_handlers.py                  │
│  │   (Routes all button clicks)           │
│  │                                         │
│  ├─ role_keyboard_handlers.py             │
│  │   (Shows role-specific menus)          │
│  │                                         │
│  ├─ analytics_handlers.py                 │
│  │   (Admin dashboard & reports)          │
│  │                                         │
│  ├─ activity_handlers.py                  │
│  │   (Weight, water, meals, habits)       │
│  │                                         │
│  ├─ user_handlers.py                      │
│  │   (Registration, QR codes)             │
│  │                                         │
│  └─ admin_handlers.py                     │
│      (Admin functions, role mgmt)         │
└───────────────┬────────────────────────────┘
                │
                ↓
┌────────────────────────────────────────────┐
│      src/database/ (Data Layer)            │
│                                            │
│  ├─ role_operations.py                    │
│  │   (Role checks & management)           │
│  │                                         │
│  ├─ user_operations.py                    │
│  │   (User CRUD)                          │
│  │                                         │
│  ├─ activity_operations.py                │
│  │   (Activity logging)                   │
│  │                                         │
│  ├─ payment_operations.py                 │
│  │   (Payment tracking)                   │
│  │                                         │
│  └─ statistics_operations.py              │
│      (Analytics queries)                  │
└───────────────┬────────────────────────────┘
                │
                ↓
┌────────────────────────────────────────────┐
│      PostgreSQL Database (Neon)            │
│                                            │
│  ├─ users (role, points, profile)         │
│  ├─ activity_logs                         │
│  ├─ payments                              │
│  ├─ challenges                            │
│  └─ notifications                         │
└────────────────────────────────────────────┘
```

---

## 🚀 Quick Start Testing

1. **Test User Role:**
   ```
   /start → Should show User menu
   /whoami → Shows "🙋 User"
   ```

2. **Test Admin Role:**
   ```
   Run: python set_admin_role.py
   /start → Should show Admin menu
   /whoami → Shows "🛡️ Admin"
   Click "📊 Admin Dashboard" → Shows dashboard
   ```

3. **Test All Buttons:**
   - Click each button in menu
   - Check logs for errors
   - Verify response appears

---

## 📞 Support & Troubleshooting

If you encounter issues:

1. Check `logs/fitness_bot.log` for errors
2. Verify database connection
3. Confirm role is set correctly
4. Ensure bot is running (only one instance)
5. Check Telegram Bot API status

---

**Last Updated:** January 9, 2026
**Bot Version:** 2.0
**Python Version:** 3.11
