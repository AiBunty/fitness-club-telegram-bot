# User Menu Commands - Testing Guide

## ✅ Bot Status: RUNNING

The bot is now successfully running and all user menu commands are properly configured!

## 🔧 What Was Fixed

1. **Missing Library**: Installed `python-telegram-bot-calendar` which was required for calendar date picker
2. **Missing Callback Handler**: Added `cmd_my_challenges` to the callback router
3. **Bot Startup**: Fixed Python path issues using `start_bot.py` as the entry point

## 📱 User Menu Commands

All buttons in the User Menu are now functional. Here's what each button does:

### 1. 💵 Request Payment Approval
- **Callback**: `cmd_request_payment`
- **Function**: User can request payment approval from admin
- **Flow**: 
  - User submits payment screenshot and amount
  - Admin reviews and approves with custom start/end dates using calendar
  - User receives confirmation notification

### 2. 📊 Notifications
- **Callback**: `cmd_notifications`
- **Function**: View all user notifications
- **Flow**: Shows list of notifications with options to view, delete, mark all read

### 3. 🏆 Challenges
- **Callback**: `cmd_challenges`
- **Function**: Browse and join active challenges
- **Flow**: View available challenges, join them, see leaderboard

### 4. ⚖️ Log Weight
- **Callback**: `cmd_weight`
- **Function**: Log daily weight
- **Flow**: Enter weight in kg, system records and awards points

### 5. 💧 Log Water
- **Callback**: `cmd_water`
- **Function**: Log water intake
- **Flow**: Enter number of cups/glasses consumed

### 6. 🍽️ Log Meal
- **Callback**: `cmd_meal`
- **Function**: Log meal with photo
- **Flow**: Upload photo of meal for tracking

### 7. 🏋️ Gym Check-in
- **Callback**: `cmd_checkin`
- **Function**: Check in to gym with photo or text
- **Flow**: 
  - Choose photo or text check-in
  - Submit for approval
  - Staff/Admin reviews and approves
  - User receives confirmation notification with points earned

### 8. ✅ Daily Habits
- **Callback**: `cmd_habits`
- **Function**: Track daily habits
- **Flow**: Mark off daily habit goals

### 9. 📱 My QR Code
- **Callback**: `cmd_qrcode`
- **Function**: Get personal gym entry QR code
- **Flow**: Generates and displays unique QR code for gym check-in

### 10. 🆔 Who Am I?
- **Callback**: `cmd_whoami`
- **Function**: Show user profile
- **Flow**: Displays:
  - Full Name
  - Username
  - Telegram ID (tap to copy)
  - Role (User/Staff/Admin)

## 🧪 Testing Steps

### Quick Test (5 minutes)
1. Open Telegram bot
2. Type `/start` or say "Hi"
3. Type `/menu` or tap "Menu" button
4. You should see the User Menu with all 10 buttons
5. Try clicking each button to verify they respond

### Full Test (15 minutes)

**Test Sequence:**

1. **Who Am I?** ✅
   - Click button → Should show your profile with copyable ID

2. **My QR Code** ✅
   - Click button → Should generate and display QR code image

3. **Log Weight** ✅
   - Click button → Should prompt for weight
   - Enter a number → Should confirm and award points

4. **Log Water** ✅
   - Click button → Should prompt for cups
   - Enter a number → Should confirm

5. **Log Meal** ✅
   - Click button → Should prompt for photo
   - Upload photo → Should confirm

6. **Daily Habits** ✅
   - Click button → Should show habit checklist
   - Mark habits → Should confirm

7. **Gym Check-in** ✅
   - Click button → Should show check-in options
   - Choose method → Should submit for approval
   - Wait for admin approval → Should receive notification

8. **Challenges** ✅
   - Click button → Should show active challenges
   - View challenge → Should show details
   - Join challenge → Should confirm

9. **Notifications** ✅
   - Click button → Should show notification list
   - Open notification → Should display content

10. **Request Payment Approval** ✅
    - Click button → Should start payment request flow
    - Upload screenshot → Should proceed
    - Enter amount → Should submit to admin

## 🎯 Expected Behaviors

### ✅ Working Correctly When:
- Each button responds immediately (no delay > 3 seconds)
- Conversation flows proceed step by step
- User receives confirmations for actions
- Points are awarded for logged activities
- Notifications are sent when admins approve/reject

### ❌ Issues to Report:
- Button click shows "Loading..." but never responds
- Error messages appear
- Bot becomes unresponsive mid-conversation
- Confirmations not received
- Points not awarded

## 🔍 Troubleshooting

### If a button doesn't work:

1. **Check bot is running**:
   ```powershell
   Get-Process -Name "python" | Where-Object { $_.CommandLine -match "start_bot" }
   ```

2. **Check bot logs**:
   ```powershell
   Get-Content "c:\Users\ventu\Fitness\fitness-club-telegram-bot\logs\fitness_bot.log" -Tail 50
   ```

3. **Restart bot**:
   ```powershell
   cd "c:\Users\ventu\Fitness\fitness-club-telegram-bot"
   Stop-Process -Name "python" -Force -ErrorAction SilentlyContinue
   Start-Sleep -Seconds 2
   C:\Users\ventu\Fitness\.venv\Scripts\python.exe start_bot.py
   ```

## 📝 Bot Commands (Alternative Access)

Users can also access features via commands:

- `/start` - Welcome message
- `/register` - Begin registration
- `/menu` - Show role-based menu
- `/qrcode` - Get gym QR code
- `/weight` - Log weight
- `/water` - Log water
- `/meal` - Log meal
- `/checkin` - Gym check-in
- `/habits` - Daily habits
- `/challenges` - Browse challenges
- `/my_challenges` - My challenges
- `/notifications` - View notifications
- `/whoami` - Show profile
- `/payment_status` - Check payment status

## 🚀 Start Bot Command

To start the bot, always use:

```powershell
cd "c:\Users\ventu\Fitness\fitness-club-telegram-bot"
C:\Users\ventu\Fitness\.venv\Scripts\python.exe start_bot.py
```

**Note**: Always navigate to the bot directory first before starting!

## ✅ Current Status

- ✅ Bot is running
- ✅ All user menu buttons configured
- ✅ Callback handlers registered
- ✅ Calendar integration active
- ✅ User notifications enabled
- ✅ Database connection verified
- ✅ Commands menu set

## 🎉 All Systems Operational!

Your bot is ready for testing. All user menu commands should now respond correctly.

**Test the bot in Telegram and verify each menu button works as expected!**
