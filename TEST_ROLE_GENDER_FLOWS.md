# Test Guide: Role-Based Menu & Gender Field Implementation

## Pre-Test Checklist
- ✅ Migration: `migrate_add_gender.py` executed successfully
- ✅ Database: Gender column added to users table
- ✅ Code: All modifications applied (see summary below)
- ✅ Bot: Ready to restart

## Implementation Summary

### Changes Made:
1. **Database**: Added `gender` VARCHAR(20) column to `users` table (nullable, allows NULL)
2. **User Registration**: Added Step 5/6 - Gender selection (Male/Female/Trans)
3. **Role Verification**: Enhanced admin/staff menu access with double-verification
4. **Approval Scoping**: Payment/Shake/Attendance/NewUser require approval; Weight/Water/Habits auto-save
5. **Super Admin**: Always shows as "🛡️ Admin" role in /whoami

### Key Files Modified:
- `src/handlers/user_handlers.py`: Added `get_gender()` function, gender selection between weight and profile_pic
- `src/database/user_operations.py`: Updated `create_user()` to accept `gender` parameter
- `src/bot.py`: Added GENDER state to registration handler
- `src/handlers/role_keyboard_handlers.py`: Enhanced double-verification for admin/staff
- `src/utils/auth.py`: Fixed /whoami to show super admin as admin role
- `.env`: Updated SUPER_ADMIN_USER_ID=424837855, SUPER_ADMIN_PASSWORD=121212

---

## Test Flows

### TEST 1: New User Registration (6-Step Flow with Gender)
**Objective**: Verify complete registration flow includes gender selection

**Steps**:
1. Start bot with `/start` command (or send /start message)
2. Tap "🚀 Register Now" button
3. **Step 1/6 - Name**: Send your name (e.g., "John Test")
   - ✅ Expected: Proceeds to phone step
4. **Step 2/6 - Phone**: Send phone number (e.g., "1234567890")
   - ✅ Expected: Proceeds to age step
5. **Step 3/6 - Age**: Send age as number (e.g., "25")
   - ✅ Expected: Proceeds to weight step
6. **Step 4/6 - Weight**: Send weight (e.g., "75")
   - ✅ Expected: Proceeds to **gender step** ← NEW!
7. **Step 5/6 - Gender**: Select from Male/Female/Trans
   - ✅ Expected: Keyboard shows 3 options (Male, Female, Trans)
   - ✅ Expected: After selection, proceeds to profile pic step
8. **Step 6/6 - Profile Pic**: Send a photo or /skip
   - ✅ Expected: Registration completes with "🎉 Registration Successful!" message
   - ✅ Expected: Shows referral code and pending approval status
   - ✅ Expected: Gender is saved in database

**Verification**:
```bash
# Check gender was saved in database
SELECT user_id, full_name, gender, created_at 
FROM users 
WHERE user_id = <TEST_USER_ID> 
ORDER BY created_at DESC LIMIT 1;
```
Expected: Gender column shows "Male", "Female", or "Trans" (not NULL)

---

### TEST 2: Role Verification - Admin Access
**Objective**: Verify super admin has dual-verified access to admin menu

**Prerequisites**: 
- Super admin user ID: 424837855
- Test with this user ID in Telegram

**Steps**:
1. Send `/start` as super admin (ID: 424837855)
   - ✅ Expected: "🛡️ Admin access granted. Registration not required..." message
   - ✅ Expected: Admin menu should display automatically
2. Send `/whoami`
   - ✅ Expected: Shows "🛡️ Admin" (force-set role regardless of DB)
3. Send `/menu`
   - ✅ Expected: Shows ADMIN_MENU (Approvals, Broadcast, etc.)

**Verification**:
- Admin menu is displayed with all admin options
- No error messages about access denial
- Registration is bypassed for admin

---

### TEST 3: Unregistered User Menu
**Objective**: Verify unregistered users get limited menu

**Steps**:
1. Use a new Telegram user ID (not registered yet)
2. Send `/menu` without completing registration
   - ✅ Expected: Limited menu appears (only basic options)
   - ✅ Expected: NOT showing admin/staff/payment options

---

### TEST 4: Registered User Menu (Role Isolation)
**Objective**: Verify registered users see USER_MENU only

**Prerequisites**:
- Create a new test user and complete registration with gender selection
- User should have approval_status = 'pending' initially

**Steps**:
1. Complete registration flow (TEST 1)
2. Send `/menu`
   - ✅ Expected: Shows USER_MENU (Activity, Dashboard, My Profile, etc.)
   - ✅ Expected: NO admin/staff options visible
3. Send `/whoami`
   - ✅ Expected: Shows "User" role

**Verification**:
- User menu is role-appropriate
- Cannot access admin or staff functions

---

### TEST 5: Concurrent Approval Guard (Payment Request)
**Objective**: Verify "Already processed" message prevents double-approval

**Prerequisites**:
- Admin user ready
- Registered user with pending payment request

**Steps**:
1. As regular user: Send payment request (e.g., `/payment` or button)
2. As admin: Tap "✅ Approve" button for that payment
   - ✅ Expected: "Payment approved!" message
3. **Immediately** tap "✅ Approve" button again
   - ✅ Expected: "❌ This payment request has already been processed"
   - ✅ Expected: NO duplicate approvals in database

**Verification**:
```bash
SELECT COUNT(*) FROM payment_requests 
WHERE user_id = <TEST_USER_ID> AND status = 'approved';
# Expected: 1 (not 2)
```

---

### TEST 6: Approval Gates - Payment Request
**Objective**: Verify unapproved users cannot access payment

**Prerequisites**:
- New test user (approval_status = 'pending')

**Steps**:
1. As unapproved user: Try to access payment function (e.g., /request_payment)
   - ✅ Expected: "❌ Your account is pending approval. Please wait..." or similar
   - ✅ Expected: Cannot proceed with payment request

---

### TEST 7: Auto-Save Routes (Weight, Water, Habits)
**Objective**: Verify these routes bypass approval

**Prerequisites**:
- Registered but UNAPPROVED user
- Admin ready to approve

**Steps**:
1. As unapproved user: Send weight update (e.g., /weight or button)
   - ✅ Expected: Accept weight WITHOUT requiring approval
   - ✅ Expected: Saved immediately, no "pending approval" message
2. As unapproved user: Send water intake (e.g., /water or button)
   - ✅ Expected: Accept water WITHOUT requiring approval
   - ✅ Expected: Saved immediately
3. As unapproved user: Send habits (e.g., /habits or button)
   - ✅ Expected: Accept habits WITHOUT requiring approval
   - ✅ Expected: Saved immediately

---

## Summary Table

| Feature | Status | Details |
|---------|--------|---------|
| Gender Column | ✅ Complete | Added to DB, nullable, VARCHAR(20) |
| Gender Selection | ✅ Complete | Step 5/6 in registration |
| Admin Verification | ✅ Complete | Double-check in show_role_menu() |
| Role Menu Isolation | ✅ Complete | Admin/Staff/User separate menus |
| Approval Gates | ✅ Complete | Payment/Shake/Attendance/NewUser |
| Auto-Save Routes | ✅ Complete | Weight/Water/Habits bypass approval |
| Concurrent Guards | ✅ Complete | "Already processed" messages |
| Super Admin Bypass | ✅ Complete | Admin access without registration |

---

## How to Run Bot

```bash
# Terminal 1: Start bot
cd c:\Users\ventu\Fitness\fitness-club-telegram-bot
C:/Users/ventu/Fitness/.venv/Scripts/python.exe start_bot.py

# Bot logs will show:
# - Database connection OK
# - Bot starting...
# - Ready to accept commands
```

## Bot Commands

- `/start` - Welcome & registration
- `/menu` - Show role-based menu
- `/whoami` - Show user role
- `/cancel` - Cancel current operation

---

## Expected Success

✅ All 7 tests pass
✅ Gender field persists in database
✅ Role-based access control enforced
✅ Approval flow works correctly
✅ No concurrent approval issues
✅ Super admin auto-bypasses registration

---

## Troubleshooting

### Bot Won't Start
- Check: `python start_bot.py` output for errors
- Check: Database connection ("Database connection OK" message)
- Check: Bot token in `.env` file

### Gender Not Saving
- Check: `verify_gender_migration.py` output - should show gender column
- Check: User registration completes without errors
- Check: Database query shows gender value for test user

### Admin Menu Not Showing
- Check: User ID matches SUPER_ADMIN_USER_ID in .env (424837855)
- Check: `/whoami` shows "🛡️ Admin"
- Check: `show_role_menu()` is called from `start_command()`

### Approval Gates Not Working
- Check: Payment/Shake requests show approval requirement
- Check: Weight/Water accept immediately without approval
- Check: Database `approval_status` column has correct values

---

## Next Steps

1. **Start Bot**: `C:/Users/ventu/Fitness/.venv/Scripts/python.exe start_bot.py`
2. **Run Tests**: Follow test flows 1-7 above
3. **Document Issues**: Note any failures with exact error messages
4. **Verify DB**: Run queries to confirm gender field and approval states
5. **Complete Handoff**: All tests pass = implementation complete

