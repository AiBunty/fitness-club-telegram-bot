# Role-Based Menu & Gender Field Implementation

## Changes Summary

### 1. **Role Verification BEFORE Menu Display** ✅
   - **File**: `src/handlers/role_keyboard_handlers.py`
   - **Change**: Enhanced `show_role_menu()` with security layers:
     - Double verification for admin and staff (role detected + re-verified)
     - Clear logging of all menu access attempts
     - Blocked users see error message with verification reason
     - No cross-role menu access possible
   - **Security**: Admin menu only shown to verified admins; staff menu only to verified staff

### 2. **Registration Flow Updated with Gender Field** ✅
   - **File**: `src/handlers/user_handlers.py`
   - **Changes**:
     - Added new step 5/6: "What is your gender?" (Male/Female/Trans)
     - Gender step comes BEFORE profile pic (step 6/6)
     - Gender field stored in user context
     - Admin notifications now include gender field
   - **States**: Updated `NAME, PHONE, AGE, WEIGHT, GENDER, PROFILE_PIC = range(6)`

### 3. **Database Migration for Gender Field** ✅
   - **File**: `migrate_add_gender.py`
   - **Change**: Adds optional `gender VARCHAR(20)` column to users table
   - **Safety**: Checks if column exists before adding (idempotent)

### 4. **Create User Function Updated** ✅
   - **File**: `src/database/user_operations.py`
   - **Change**: `create_user()` now accepts `gender` parameter
   - **Query**: Inserts gender into users table during registration

### 5. **Bot Conversation Handler Updated** ✅
   - **File**: `src/bot.py`
   - **Changes**:
     - Added `GENDER` to registration states
     - Added `get_gender` import
     - Registration handler now processes gender step between weight and profile pic

## User Flow After Changes

### Unregistered Users
1. See "👤 WELCOME" menu
2. Can only see registration/common options
3. Cannot access any admin/staff features
4. Upon /register, flow: Name → Phone → Age → Weight → **Gender** → Profile Pic
5. Registered but pending approval: Cannot access payment/shakes/attendance (approval gates active)

### Registered & Approved Users  
1. See "🙋 USER MENU"
2. Full access to: weight, water, meals, habits, check-in, payment, shakes, leaderboard
3. Weight/water/meals/habits auto-save (no approval needed)
4. Payment requests require approval
5. Shake purchases require approval

### Staff Members
1. See "🧑‍🍳 STAFF MENU"
2. Access: pending attendance, pending shakes, notifications, leaderboard
3. Can approve/reject attendance & shake requests
4. Cannot access admin functions (verified in handlers)

### Admins
1. See "🛡️ ADMIN MENU"
2. Full admin access (dashboard, user management, broadcasts, etc.)
3. Can manage staff, approvals, analytics
4. Super admin (ID 424837855) auto-detected even if unregistered

## Security Improvements

1. **Double Verification**: Admin/staff role verified twice before menu access
2. **Role Isolation**: Each role has separate menu; cross-role access blocked
3. **Unregistered Containment**: Unregistered users can only see basic menu
4. **Approval Gates**: Payment/shakes/attendance locked behind approval status
5. **Audit Logging**: All menu access attempts logged with role and user ID

## Testing Checklist

- [ ] Run migration: `python migrate_add_gender.py`
- [ ] Test unregistered user → /start → registration flow (6 steps + gender)
- [ ] Verify gender field shows in admin notification
- [ ] Admin /whoami shows "🛡️ Admin" even if unregistered
- [ ] Admin /menu shows ADMIN_MENU with all options
- [ ] User /menu shows USER_MENU only (no admin options)
- [ ] Concurrent approvals show "Already processed" message
- [ ] Unapproved users cannot access payment/shake requests

