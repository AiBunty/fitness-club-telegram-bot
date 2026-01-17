# Phase 2 Commands & Features Reference

## 📱 User Commands

### Registration & Main Menu
```
/start              Register new user (5-step process)
/menu               Show main menu with buttons
/cancel             Cancel current operation
```

### Activity Logging
```
/weight             Log today's weight (10 points)
/water              Log water intake (5 points/cup)
/meal               Log meal photo (15 points each, max 4)
/habits             Complete daily habits (20 points)
/checkin            Check in to gym (50 points when approved)
```

### Information
```
/stats              View your statistics and points
/help               View available commands
```

## 👨‍💼 Admin Commands

```
/pending_attendance  Review pending gym check-ins
/pending_shakes      Review pending shake orders
```

## 🎮 Interactive Menu Buttons (`/menu`)

### Main Menu Layout:
```
┌─────────────────────────────────────┐
│  🏋️ Fitness Club Menu                │
│                                      │
│  👤 John Doe                         │
│  💳 Status: PAID                     │
│  ⭐ Points: 150                       │
│                                      │
│  [📊 My Stats] [🏋️ Check In]        │
│  [💪 Log Activity] [🥛 Order Shake]  │
│  [🏆 Leaderboard] [⚙️ Settings]     │
└─────────────────────────────────────┘
```

### Button Functions:

**📊 My Stats**
- Shows today's activities
- Weight logged: ✅ or ❌
- Water cups: Current count
- Meals logged: Count/4
- Habits: ✅ or ❌
- Total points: Your current total

**🏋️ Check In**
- Option 1: Upload gym photo
- Option 2: Text-only check-in
- Creates pending request
- Admin approval needed

**💪 Log Activity**
- ⚖️ Log Weight (10 pts)
- 💧 Log Water (5 pts/cup)
- 🍽️ Log Meal (15 pts)
- 💪 Complete Habits (20 pts)

**🥛 Order Shake**
- Shows available flavors
- Select and order
- Admin prepares
- Status updates when ready

**🏆 Leaderboard**
- Top 10 members shown
- 🥇 🥈 🥉 medals
- Point totals
- Ranked by total_points

**⚙️ Settings**
- Update profile info
- Payment status
- Notification preferences

## 🎯 Points System

### Points Earned:
```
Activity            Points    Frequency    Max/Day
─────────────────────────────────────────────────
Gym Attendance        50      Once         1
Weight Logging        10      Once         1
Water (500ml)          5      Per cup      20
Meal Photos           15      Each meal    4
Daily Habits          20      Once         1
─────────────────────────────────────────────────
MAXIMUM DAILY:        200
```

### How Points Work:
1. User completes activity
2. Bot validates and logs it
3. Points awarded instantly
4. Total updated
5. Leaderboard recalculated
6. Transaction recorded

## 📊 Admin Panel Workflow

### Attendance Approval
```
Admin: /pending_attendance
   ↓
Bot: Shows pending request #1
   ├─ User: John Doe
   ├─ Date: 2026-01-09
   ├─ Photo: Yes/No
   └─ Buttons:
      [✅ Approve] [❌ Reject]

Admin: Clicks ✅ Approve
   ↓
Bot: 
   - Records attendance
   - Awards 50 points
   - Shows next request

Admin: Can continue processing or stop
```

### Shake Request Processing
```
Admin: /pending_shakes
   ↓
Bot: Shows pending shake #1
   ├─ User: Jane Smith
   ├─ Flavor: Vanilla
   ├─ Notes: (if any)
   └─ Buttons:
      [✅ Ready] [❌ Cancel]

Admin: Clicks ✅ Ready
   ↓
Bot:
   - Marks as ready
   - Notifies user
   - Shows next request

Admin: Continue processing
```

## 🔄 Data Flow Examples

### Example 1: User Logs Weight
```
User: /weight
   ↓
Bot: "Enter weight in kg"
   ↓
User: 75.5
   ↓
Bot: Validates (30-300kg range)
   ↓
Database: 
   - Inserts into daily_logs
   - Adds points_transaction
   - Updates user.total_points
   ↓
User: "✅ Weight Logged. 75.5kg. +10 points!"
```

### Example 2: User Orders Shake
```
User: /menu → 🥛 Order Shake
   ↓
Bot: "Select flavor" [Vanilla] [Chocolate] [Mango]...
   ↓
User: Clicks [Vanilla]
   ↓
Database:
   - Creates shake_request
   - Status: pending
   ↓
Admin: /pending_shakes → Sees request
   ↓
Admin: Clicks ✅ Ready
   ↓
Database:
   - Updates status: ready
   - Records prepared_by
   - Sets prepared_at time
   ↓
User: Notified to pick up shake
```

### Example 3: Admin Approves Attendance
```
Admin: /pending_attendance
   ↓
Bot: Shows pending check-in request
   ↓
Admin: Reviews user details & photo
   ↓
Admin: Clicks ✅ Approve
   ↓
Database:
   - Updates status: approved
   - Records approved_by (admin ID)
   - Awards 50 points to user
   - Creates transaction entry
   ↓
User: Notified "+50 points for attendance! Total: 200"
   ↓
Admin: Bot shows next pending request
```

## 🗄️ Database Tables (Phase 2 Relevant)

```
daily_logs
├─ user_id
├─ log_date
├─ weight (nullable)
├─ water_cups
├─ meals_logged
├─ habits_completed
└─ attendance

points_transactions
├─ transaction_id
├─ user_id
├─ points
├─ activity (weight_log, water, meal_photo, etc.)
├─ description
└─ created_at

attendance_queue
├─ attendance_id
├─ user_id
├─ request_date
├─ photo_url (nullable)
├─ status (pending, approved, rejected)
├─ approved_by (admin user_id)
└─ approved_at

shake_requests
├─ shake_request_id
├─ user_id
├─ flavor_id
├─ notes
├─ status (pending, ready, completed, cancelled)
├─ prepared_by
└─ prepared_at
```

## 🔐 Permission Model

### User
- Can log own activities
- Can view own stats
- Can order shakes
- Can request attendance
- Read leaderboard

### Admin
- Can view all pending requests
- Can approve/reject attendance
- Can mark shakes ready/cancel
- Can view user points history
- Access to admin commands

### Super Admin
- All admin permissions
- Can manage admin users
- Can modify points manually
- Can reset user accounts

## 📋 Error Handling

### User Input Validation:
```
Weight: 30-300 kg
Age: 10-100 years
Phone: +91 format
Water: 1-20 cups
Meals: 0-4 per day
```

### Database Error Handling:
- Connection failures → Bot stops safely
- Transaction conflicts → Automatic retry
- Duplicate entries → ON CONFLICT handling
- Invalid data → User notified to retry

## 🎯 Testing Checklist

- [ ] `/weight` logs and awards points
- [ ] `/water` logs and awards points
- [ ] `/meal` accepts photo and awards points
- [ ] `/habits` completes and awards points
- [ ] `/checkin` creates attendance request
- [ ] `/menu` shows all buttons
- [ ] Stats button shows correct activities
- [ ] Leaderboard shows top 10
- [ ] `/pending_attendance` shows requests
- [ ] `/pending_shakes` shows requests
- [ ] Approve buttons work
- [ ] Reject buttons work
- [ ] Points calculated correctly
- [ ] Transactions logged

---

**Last Updated:** 2026-01-09
**Phase:** 2
**Status:** ✅ Complete
