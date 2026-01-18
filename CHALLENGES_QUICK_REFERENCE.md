# Challenges System - Quick Reference Guide

## 🚀 Quick Start for Developers

### What's Already Done

**Database**: ✅ All tables created, 15 messages loaded, columns added  
**Payment**: ✅ AR integration ready (method='unknown', due_date=today)  
**Points**: ✅ Engine ready (checkin 100, water 5, weight 20, habits 5, shake 50)  
**Cutoff**: ✅ Enforced at 8 PM in all activity handlers  
**Broadcasts**: ✅ Scheduled jobs ready for challenges, payments, points  
**Motivational**: ✅ Database with 15 messages, random selection ready  

### What's Left to Build

1. **Admin Challenge Creation** (Day 1)
   - File: `src/handlers/admin_challenge_handlers.py`
   - Use: `create_challenge()` from challenges_operations.py
   - Pattern: Follow broadcast_handlers.py for multi-step flow

2. **User Challenge Participation** (Day 1-2)
   - Update: `src/handlers/challenge_handlers.py`
   - Free: Instant approval, add points, send welcome
   - Paid: Queue approval, create AR, send reminders

3. **Leaderboard & Reports** (Day 2)
   - Query: Updated `get_challenge_leaderboard()`
   - Display: Top 10 with rankings
   - Charts: Weight journey + activity breakdown (matplotlib)

4. **Testing** (Day 2-3)
   - Create free/paid challenges
   - Join and log activities
   - Verify points and leaderboard
   - Check scheduled jobs

---

## 💻 Code Snippets for Handlers

### Import Challenge Modules
```python
from src.database.challenges_operations import (
    create_challenge, get_active_challenges, get_challenge_by_id,
    join_challenge, get_challenge_participants
)
from src.database.challenge_payment_operations import (
    approve_challenge_participation, get_participant_payment_status
)
from src.database.motivational_operations import get_random_motivational_message
from src.utils.challenge_points import award_challenge_points
from src.utils.cutoff_enforcement import get_challenge_start_cutoff_message
```

### Award Points on Approval (Check-in Example)
```python
# In approval handler
message = get_random_motivational_message()  # From DB
points = award_challenge_points(
    user_id=user_id,
    challenge_id=None,  # Don't count in challenge if approving solo checkin
    activity_type='checkin',
    metadata={'weekly_checkins': get_weekly_checkin_count(user_id)}
)
await context.bot.send_message(
    chat_id=user_id,
    text=f"✅ Approved! +{points} points\n\n{message}"
)
```

### Join Challenge (Free)
```python
# User joins free challenge
challenge = get_challenge_by_id(challenge_id)

# Instant approval
db = DatabaseConnection()
db.execute_insert("""
    INSERT INTO challenge_participants 
    (challenge_id, user_id, approval_status, payment_status)
    VALUES (%s, %s, 'approved', 'na')
""", (challenge_id, user_id))

# Send welcome
from src.utils.cutoff_enforcement import get_welcome_message_with_cutoff
welcome = get_welcome_message_with_cutoff(challenge['name'])
await context.bot.send_message(chat_id=user_id, text=welcome)
```

### Join Challenge (Paid)
```python
# User requests to join paid challenge
result = approve_challenge_participation(user_id, challenge_id, admin_id)

if result['success'] and result['requires_payment']:
    # AR created, send payment notification
    amount = result['amount']
    receivable_id = result['receivable_id']
    
    message = f"""
💳 Payment Required for {challenge['name']}

Amount: Rs. {amount}
Method: Bank Transfer or Cash
(Admin will confirm)

Awaiting admin approval...
"""
    await context.bot.send_message(chat_id=user_id, text=message)
```

### Send Motivational Message
```python
# On check-in approval
msg = get_random_motivational_message()  # Random from 15 messages
# Message automatically tracked in DB (used_count incremented)
```

### Check Points Configuration
```python
from src.utils.challenge_points import CHALLENGE_POINTS_CONFIG

print(CHALLENGE_POINTS_CONFIG['checkin'])
# Output: {'base_points': 100, 'bonus_6day': 200, ...}

print(CHALLENGE_POINTS_CONFIG['water'])
# Output: {'points_per_unit': 5, 'unit_size': 500, ...}
```

---

## 📅 Scheduled Jobs Already Running

### At 00:05 AM
```python
broadcast_challenge_starts()
```
- Gets challenges scheduled for today
- Broadcasts to all active users
- Includes "⏰ Daily Cutoff at 8 PM" message
- Marks challenge as broadcast_sent

### At 10:00 AM
```python
send_challenge_payment_reminders()
```
- Sends reminders for unpaid/partial participants
- Only for active challenges
- Uses universal payment method format

### At 10:00 PM
```python
process_daily_challenge_points()
```
- For all active challenges:
  - Gets each participant's daily activities
  - Awards points (check-in, water, weight, habits, shake)
  - Checks 6-day bonus eligibility
  - Updates daily progress JSON
  - Sends summary to each user
- Example summary:
  ```
  📊 Daily Points in Weight Loss Challenge
  ✅ Check-in: +100 pts
  💧 Water: +25 pts
  ⚖️ Weight: +20 pts
  🏆 Total Today: +145 pts
  ```

---

## 🕐 Cutoff System

### How It Works
```python
from src.utils.cutoff_enforcement import enforce_cutoff_check

# Before any activity logging:
allowed, message = enforce_cutoff_check("weight logging")
if not allowed:
    await update.message.reply_text(message)
    # User sees: "Daily logging window closed at 8:00 PM..."
    return ConversationHandler.END
```

### What's Blocked After 8 PM
- ❌ Weight logging
- ❌ Water intake
- ❌ Meal logging
- ❌ Habit tracking
- ❌ Gym check-in

### What's Still Allowed After 8 PM
- ✅ View challenges
- ✅ View leaderboard
- ✅ View points summary
- ✅ Browse store products
- ✅ Check payment status

---

## 💳 Payment Integration Pattern

### Universal Defaults
```python
# Every payment approval uses these defaults:
payment_data = {
    'method': 'unknown',              # Master of truth value
    'due_date': datetime.now().date()  # Today = due date, no delay
}

# Optional: Grace period (configured per feature)
# challenges: 0 days
# subscriptions: 3 days
# store_products: 0 days
```

### AR Flow for Challenges
```python
# When user pays for challenge entry:

1. create_receivable(
    user_id, amount, description='Challenge Entry: {name}',
    method='unknown',  # Always this
    due_date=today     # Approval date = due date
)

2. create_transactions(receivable_id, payment_amount, today, admin_id)

3. update_receivable_status(receivable_id)
   # Updates to: 'paid', 'partial', or 'unpaid'

4. Daily reminders sent via send_challenge_payment_reminders()
```

---

## 🗂️ File Structure

```
src/
├── database/
│   ├── challenges_operations.py       [13 functions added]
│   ├── challenge_payment_operations.py [NEW]
│   └── motivational_operations.py     [NEW]
├── handlers/
│   ├── activity_handlers.py           [Updated: cutoff in 5 commands]
│   ├── admin_challenge_handlers.py    [TODO]
│   └── challenge_handlers.py          [Update leaderboard/reports]
├── utils/
│   ├── challenge_points.py            [NEW]
│   ├── cutoff_enforcement.py          [NEW]
│   └── scheduled_jobs.py              [3 new functions added]
└── config.py
    └── CHALLENGE_POINTS_CONFIG        [defined in challenge_points.py]

migrate_challenges_system.py [NEW - run first]
PHASE_5_COMPLETION_SUMMARY.md [NEW - this doc]
```

---

## 🧪 Testing Checklist

### Database
- [ ] `python migrate_challenges_system.py` runs successfully
- [ ] All 3 tables present in DB
- [ ] 15 motivational messages loaded
- [ ] points_transactions has challenge_id column

### Cutoff Enforcement
- [ ] Before 8 PM: Activities allowed, points awarded
- [ ] After 8 PM: Activities blocked, message shown
- [ ] Message includes all blocked activity types

### Points Engine
- [ ] Check-in awards 100 points
- [ ] Water awards 5 points per 500ml
- [ ] Weight awards 20 points
- [ ] Habits award 5 points each
- [ ] 6-day bonus awards 200 additional points

### Payment System
- [ ] Free challenge: Instant approval, no AR needed
- [ ] Paid challenge: AR created with method='unknown', due_date=today
- [ ] Reminders sent daily for unpaid participants

### Scheduled Jobs
- [ ] 00:05 AM: Challenge broadcasts sent
- [ ] 10:00 AM: Payment reminders sent
- [ ] 10:00 PM: Points calculated, leaderboard updated

### Motivational Messages
- [ ] Random selection works (different each approval)
- [ ] Usage count increments in DB
- [ ] 15 unique messages rotate

---

## 🔧 Debugging Tips

### Check if points are calculating
```sql
-- See all transactions for a user in a challenge
SELECT * FROM points_transactions 
WHERE user_id = {user_id} AND challenge_id = {challenge_id}
ORDER BY created_at DESC;
```

### Check challenge participation
```sql
-- See participant status, payment, points
SELECT cp.*, c.name, u.full_name FROM challenge_participants cp
JOIN challenges c ON cp.challenge_id = c.challenge_id
JOIN users u ON cp.user_id = u.user_id
WHERE c.challenge_id = {challenge_id};
```

### Check AR status
```sql
-- See payment status for challenge participant
SELECT ar.* FROM accounts_receivable ar
WHERE ar.receivable_id IN (
    SELECT receivable_id FROM challenge_participants 
    WHERE challenge_id = {challenge_id}
);
```

### Check motivational messages
```sql
-- See message stats
SELECT 
    COUNT(*) as total,
    SUM(CASE WHEN is_active THEN 1 ELSE 0 END) as active,
    SUM(used_count) as total_uses
FROM motivational_messages;
```

---

## 📞 Key Functions Reference

| Function | Module | Purpose |
|----------|--------|---------|
| `create_challenge()` | challenges_ops | Create new challenge |
| `join_challenge()` | challenges_ops | User joins challenge |
| `award_challenge_points()` | challenge_points | Award points for activity |
| `enforce_cutoff_check()` | cutoff_enforcement | Check if logging allowed |
| `get_random_motivational_message()` | motivational_ops | Get random message |
| `approve_challenge_participation()` | challenge_payment_ops | Approve + create AR |
| `send_challenge_payment_reminders()` | scheduled_jobs | Daily payment reminders |
| `process_daily_challenge_points()` | scheduled_jobs | Daily point calculation |
| `broadcast_challenge_starts()` | scheduled_jobs | Broadcast new challenges |

---

**Ready to implement Phase 6: Admin Challenge Creation!** 🚀
