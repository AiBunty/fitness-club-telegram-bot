# Menu Testing Guide - Role-Based Buttons

## Bot Status ✅
Bot is **RUNNING SUCCESSFULLY** with all handlers properly registered.

---

## How to Test Different Roles

### Setup
1. Bot is now running and listening for messages
2. Users are identified by their Telegram ID
3. Roles are determined by:
   - **User**: Default (not in ADMIN_IDS or STAFF_IDS)
   - **Staff**: Listed in `STAFF_IDS` in `.env` or added via `/add_staff`
   - **Admin**: Listed in `ADMIN_IDS` in `.env` or added via `/add_admin`

### Current Role Configuration (from .env)
```
ADMIN_IDS=PASTE_YOUR_NUMERIC_ID_HERE
STAFF_IDS=
SUPER_ADMIN_USER_ID=PDForexEa
```

---

## Testing Steps

### Test 1: Regular User Menu
**Action:** Message the bot "Hi" or "/menu"  
**Expected Behavior:**
- Greeting: "👋 Hey [User Name]! 😊"
- Menu shows **User commands only**:
  - 📊 Notifications
  - 🏆 Challenges
  - ⚖️ Log Weight
  - 💧 Log Water
  - 🍽️ Log Meal
  - 🏋️ Gym Check-in
  - ✅ Daily Habits
  - 📱 My QR Code
  - 🆔 Who Am I?

### Test 2: Interactive Habits Feature
**Action:** Click `✅ Daily Habits` button in user menu  
**Expected Behavior:**
- Shows 8 habit buttons with toggles:
  - 🥤 Morning Shake (○)
  - 💪 Exercise (○)
  - 💧 Enough Water (○)
  - 🥤 2nd Shake (○)
  - 🍽️ Healthy Dinner (○)
  - 😴 Good Sleep (○)
  - 🚫 No Junk Food (○)
  - 🚭 No Smoking (○)
- Click each to toggle ✓/○
- 📤 Submit & Continue button
- **Result:** Shows wellness score and awards points

### Test 3: Staff Menu (After Configuration)
**Prerequisite:** Set your numeric ID in `ADMIN_IDS` or add via `/add_staff`  
**Action:** Message "Hi" or "/menu"  
**Expected Behavior:**
- Menu shows **Staff commands**:
  - ✔️ Pending Attendance
  - 🥤 Pending Shakes
  - 📊 Notifications
  - 🏆 Challenges
  - 🆔 Who Am I?

### Test 4: Admin Menu (After Configuration)
**Prerequisite:** Set your numeric ID in `ADMIN_IDS` or added via `/add_admin`  
**Action:** Message "Hi" or "/menu"  
**Expected Behavior:**
- Menu shows **Admin commands**:
  - 📈 Dashboard
  - ✔️ Pending Attendance
  - 🥤 Pending Shakes
  - 💳 Payment Status
  - 📊 Notifications
  - ➕ Add Staff
  - ➖ Remove Staff
  - 📋 List Staff
  - ➕ Add Admin
  - ➖ Remove Admin
  - 📋 List Admins
  - 🆔 Who Am I?

### Test 5: Greeting Handler
**Action:** Type "Hi", "Hello", "Hey", or "Greetings"  
**Expected Behavior:**
- Instant personalized greeting: "👋 Hey [Name]! 😊"
- Auto-shows role-specific menu
- Works from anywhere (no need to remember `/menu`)

### Test 6: Geofenced QR Check-in
**Prerequisite:** Generate studio QR with: `python generate_checkin_qr.py`  
**Action:** Scan the printed QR code  
**Expected Behavior:**
1. Bot says "Please share your location to complete check-in (10m radius)"
2. Click "📍 Share Location" button
3. Share location (pin on map)
4. **If within 10m of geofence**: "✅ Attendance logged and approved. +10 points!"
5. **If outside 10m**: "⛔ Out of range (XXX m). Be near the studio."

---

## Roles Configuration

### To Set Admin Manually
Edit `.env`:
```
ADMIN_IDS=123456789
```
(Replace 123456789 with your numeric Telegram ID)

### To Set Admin via Chat (For Super Admin)
Message the bot:
```
/add_admin
<paste numeric ID>
```

### To Get Your ID
Message: `/whoami`  
Response: `Your Telegram ID: 123456789`

---

## Button Types Used

| Feature | Type | Appearance |
|---------|------|-----------|
| Menu items | Inline buttons | On message, no keyboard replacement |
| Role selection | Auto-detect | No manual selection needed |
| Habit toggles | Inline buttons | ✓/○ visual feedback |
| Location sharing | Reply button | Request location on keyboard |

---

## Features Summary

✅ **Role-Based Auto-Detection**
- No manual role selection
- Menu automatically shows user's relevant commands

✅ **Interactive Buttons**
- All commands as buttons (not slash commands)
- Callbacks handle routing
- Visual feedback (✓ checkmarks for habits)

✅ **Greeting Handler**
- Natural language: "Hi", "Hello", "Hey"
- Personalized: Uses stored name
- Instant menu: No extra clicks needed

✅ **Geofenced QR Check-in**
- Request location on QR scan
- Validate distance (10m radius)
- Auto-attendance for active members
- Points awarded on successful check-in

✅ **Habits with Wellness Score**
- Toggle habits with visual indicators
- Submit all at once
- Calculate score (# completed)
- Award bonus points

---

## Next Steps

1. **Update `.env` with your Telegram ID** for admin access
2. **Generate studio QR** for testing geofence
3. **Send "Hi"** to bot to see personalized menu
4. **Test habit logging** with interactive buttons
5. **Scan studio QR** to test geofenced attendance

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Bot not responding | Ensure bot is running in terminal |
| Commands not showing | Make sure ADMIN_IDS is set for admin/staff features |
| Location request not appearing | Use Telegram app (desktop doesn't support) |
| Geofence always out of range | Verify GEOFENCE_LAT/LNG/RADIUS_M in `.env` |
| Menu buttons not interactive | Check callback handlers registered in bot.py |

