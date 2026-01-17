# Quick Test Commands & Expected Outputs

## Bot Startup
```bash
# Terminal command
cd c:\Users\ventu\Fitness\fitness-club-telegram-bot
C:/Users/ventu/Fitness/.venv/Scripts/python.exe start_bot.py
```

**Expected Log Output:**
```
Testing database connection...
2026-01-17 XX:XX:XX,XXX - src.database.connection - INFO - Database connection OK
2026-01-17 XX:XX:XX,XXX - src.bot - INFO - Database OK! Starting bot...
2026-01-17 XX:XX:XX,XXX - src.bot - INFO - Bot starting...
2026-01-17 XX:XX:XX,XXX - telegram.ext.Application - INFO - Application started
```

If you see this, bot is ready ✅

---

## Test 1: Gender Registration (NEW USER)

### Commands in Telegram Bot
1. `/start`
   - **Expected**: Welcome message + "🚀 Register Now" button
   
2. Click "🚀 Register Now"
   - **Expected**: "**Step 1/6:** Please enter your full name"
   
3. Send: `Test User`
   - **Expected**: "**Step 2/6:** Please enter your phone number"
   
4. Send: `1234567890`
   - **Expected**: "**Step 3/6:** Please enter your age"
   
5. Send: `25`
   - **Expected**: "**Step 4/6:** Please enter your current weight (kg)"
   
6. Send: `75`
   - **Expected**: "**Step 5/6:** Select your gender"
   - **Keyboard Appears**: 
     ```
     [Male]
     [Female]
     [Trans]
     ```
   
7. Tap: `Male` (or Female/Trans)
   - **Expected**: "**Step 6/6:** Please send your profile picture (or /skip)"
   
8. Send: `/skip` (or upload photo)
   - **Expected**: 
     ```
     🎉 Registration Successful!
     Name: Test User
     Referral Code: XXXXX...
     ⏳ Your registration is pending admin approval.
     ```

✅ **Success**: All 6 steps completed, gender selected

---

## Test 2: Super Admin Menu Access

### Commands in Telegram (IMPORTANT: Use User ID 424837855)
1. `/start`
   - **Expected**: "🛡️ Admin access granted. Registration not required..."
   
2. `/whoami`
   - **Expected**: 
     ```
     👤 **Your Role**: 🛡️ Admin
     Your ID: 424837855
     Username: @[your_username]
     ```
   
3. `/menu`
   - **Expected**: ADMIN_MENU appears with options like:
     ```
     ⚙️ Admin Panel
     ✅ Approvals
     📢 Broadcast
     ...
     ```

✅ **Success**: Admin menu accessible without registration

---

## Test 3: Regular User Menu

### Commands in Telegram (NEW REGISTERED USER)
1. Complete registration (Test 1)
2. `/whoami`
   - **Expected**: Shows "User" role (not Admin)
   
3. `/menu`
   - **Expected**: USER_MENU appears with options like:
     ```
     📊 Activity & Dashboard
     💪 My Profile
     💰 Payment
     ...
     ```
   - **NOT showing**: Approval, Broadcast, Admin options

✅ **Success**: Correct role-based menu

---

## Test 4: Concurrent Approval Check

### Admin Testing Payment Approval
1. User sends: `/request_payment` (or button)
   - **Expected**: Payment request created, waiting for approval
   
2. Admin sees: Approval button for that payment
   
3. Admin taps: "✅ Approve" button
   - **Expected**: "✅ Payment approved!"
   
4. Admin taps SAME button again immediately
   - **Expected**: "❌ This payment request has already been processed"
   - **NOT**: Duplicate approval

✅ **Success**: Guard prevents double-approval

---

## Test 5: Auto-Save Routes (No Approval Needed)

### As UNAPPROVED User (approval_status = 'pending')
1. `/weight` and send: `73`
   - **Expected**: "✅ Weight recorded!" (immediate, no approval)
   
2. `/water` and send: `8`
   - **Expected**: "✅ Water intake recorded!" (immediate, no approval)
   
3. `/habits` and send response
   - **Expected**: "✅ Habits saved!" (immediate, no approval)

✅ **Success**: Routes auto-save without approval gates

---

## Database Verification Queries

### Verify Gender Column Exists
```sql
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'users' 
ORDER BY ordinal_position;
```
**Expected**: Should show `gender | character varying` in the list

### Verify Gender Was Saved
```sql
SELECT user_id, full_name, gender, approval_status, created_at
FROM users
WHERE created_at > NOW() - INTERVAL '1 hour'
ORDER BY created_at DESC;
```
**Expected**: Recent test user shows gender value (Male/Female/Trans)

### Verify Approval Status
```sql
SELECT user_id, full_name, approval_status, role
FROM users
WHERE user_id = <TEST_USER_ID>;
```
**Expected**: Shows approval_status and role correctly

---

## Common Issues & Quick Fixes

### Issue: Bot crashes at startup
```
psycopg2.OperationalError: SSL connection has been closed
```
**Fix**: Wait 30 seconds for database to reconnect, then restart bot

### Issue: Gender keyboard not showing
**Check**: 
1. Did user complete steps 1-4?
2. Step 5 should show keyboard with 3 options
3. If still not showing, check bot logs for errors

### Issue: Admin menu won't appear
**Check**:
1. Verify user ID is exactly 424837855
2. Run `/whoami` to see role
3. Verify `.env` has `SUPER_ADMIN_USER_ID=424837855`

### Issue: Gender not saving in database
**Check**:
1. User completed all 6 steps without /cancel
2. Check bot logs for errors during registration
3. Run database verification query above

---

## Test Summary Checklist

- [ ] Bot starts without errors
- [ ] Gender selection appears in registration (Step 5/6)
- [ ] Gender saved in database for new user
- [ ] Super admin (424837855) shows 🛡️ Admin role
- [ ] Super admin can access admin menu without registration
- [ ] Regular user sees USER_MENU (not ADMIN_MENU)
- [ ] Concurrent payment approval shows "Already processed"
- [ ] Weight/Water/Habits accept immediately without approval
- [ ] Unapproved users blocked from payment/shake/attendance

**All items checked = Implementation Complete ✅**

---

## Need Help?

Check these files in order:
1. `TEST_ROLE_GENDER_FLOWS.md` - Detailed test guide
2. `IMPLEMENTATION_COMPLETE_SUMMARY.md` - What was changed
3. Bot logs in terminal - Check for error messages
4. Database queries - Verify data persists
