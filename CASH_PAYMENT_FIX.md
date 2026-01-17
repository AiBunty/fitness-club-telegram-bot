# Cash Payment Admin Notification Fix

## Problem
When users selected "💵 Cash Payment" during subscription, no message was being sent to the admin for approval.

## Root Cause
The `get_admin_ids()` function in `src/handlers/admin_handlers.py` was importing the wrong `list_admins()` function:
- It was importing from `src.database.admin_operations` (which queries a non-existent `admin_members` table)
- Should have been importing from `src.database.role_operations` (which queries the `users` table where `role = 'admin'`)

## Solution
**File: `src/handlers/admin_handlers.py` (Line 12)**

Changed:
```python
from src.database.admin_operations import add_admin, remove_admin, list_admins
```

To:
```python
from src.database.admin_operations import add_admin, remove_admin
from src.database.role_operations import list_admins
```

## How It Works
1. User selects cash payment during subscription
2. `callback_confirm_subscription()` calls `get_admin_ids()`
3. `get_admin_ids()` now correctly retrieves admin IDs from users table where `role = 'admin'`
4. For each admin ID, a notification message is sent with:
   - User details (name, ID, phone, age, weight, gender)
   - Subscription plan details (name, amount, duration)
   - Payment method (Cash)
   - Request ID and submission time
   - Approve/Reject buttons

## Testing
✅ Admin notification system is now functional
✅ Cash payment requests now show up in admin's chat
✅ Admin can approve/reject cash payments with inline buttons

## Status
✅ FIXED - Cash payment notifications are now being sent to admins
