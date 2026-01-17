# Next Steps - Role Menu & Gender Field

## 1. Run Migration to Add Gender Field

```bash
cd c:\Users\ventu\Fitness\fitness-club-telegram-bot
python migrate_add_gender.py
```

Expected output:
```
✅ Migration completed successfully
```

## 2. Restart the Bot

Stop any running bot instance and start fresh:
```bash
Stop-Process -Name python -Force
python start_bot.py
```

## 3. Test Registration Flow

### Test 1: New User Registration (6 Steps)
1. Send `/start` to bot
2. Click "🚀 Register Now"
3. Step 1: Enter name (e.g., "Test User")
4. Step 2: Enter phone (e.g., "+919876543210")
5. Step 3: Enter age (e.g., "25")
6. Step 4: Enter weight (e.g., "75.5")
7. **Step 5: Select gender** (New!) → Choose "Male", "Female", or "Trans"
8. Step 6: Send profile picture or /skip
9. See admin notification with gender field displayed

### Test 2: Admin Role Verification
1. Send `/whoami`
2. Verify: "👔 Role: 🛡️ Admin" (should show admin role)
3. Send `/menu`
4. Verify: Shows "🛡️ ADMIN MENU" with all admin options
5. Cannot see any user/staff-only options

### Test 3: Unregistered User Menu
1. Create new Telegram account or use different user ID
2. Send `/menu`
3. Verify: Shows "👤 WELCOME" (limited options)
4. Send `/register`
5. Complete 6-step registration WITH gender field

### Test 4: Role Isolation (Register as User)
1. Register a regular user
2. After approval, send `/menu`
3. Verify: Shows "🙋 USER MENU" only
4. Verify: No admin/staff options visible

## 4. Verify Concurrent Approvals Still Work

### Test Concurrent Payment Approval
1. User submits payment request
2. Admin1 clicks approve, fills amount & dates
3. Admin2 tries to approve same request
4. Verify: Admin2 sees "Already approved" message

### Test Concurrent Attendance Approval
1. User submits check-in
2. Admin1 approves
3. Admin2 tries to approve same check-in
4. Verify: Admin2 sees "Already approved" message

## 5. Verify Approval Gates (Payment/Shakes Locked)

### Test: Unapproved User Cannot Order Shakes
1. Register user but DON'T approve yet
2. User tries `/menu` → "Check Shake Credits"
3. Verify: Error "Registration pending approval"
4. Admin approves user
5. User tries again
6. Verify: Now can see shake credits

## Files Modified

✅ `src/handlers/role_keyboard_handlers.py` - Enhanced `show_role_menu()` with double verification
✅ `src/handlers/user_handlers.py` - Added gender selection step (step 5/6)
✅ `src/database/user_operations.py` - Updated `create_user()` to accept gender
✅ `src/bot.py` - Added GENDER state and get_gender handler to registration
✅ `migrate_add_gender.py` - NEW migration script for gender field

## Rollback (If Needed)

If issues occur, roles remain unchanged but gender field rollback:
```sql
ALTER TABLE users DROP COLUMN gender;
```

But migration is idempotent - can run `migrate_add_gender.py` again safely.
