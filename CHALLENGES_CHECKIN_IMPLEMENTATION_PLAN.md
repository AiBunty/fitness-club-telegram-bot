# Challenges + Gym Check-in Implementation Plan

**Created**: January 18, 2026  
**Status**: Ready for Implementation  
**Scope**: Complete implementation of Challenges System and Enhanced Gym Check-in

---

## 🎯 Executive Summary

This plan implements two core features:
1. **Challenges System** - Admin-created fitness challenges with optional pricing, AR payment integration, points engine, leaderboards, and end-of-challenge reports
2. **Enhanced Gym Check-in** - Approval-based check-ins with motivational messages and points rewards

---

## ⏰ CUTOFF TIMES - MASTER RULE

### Single Daily Cutoff: 8:00 PM

**All daily activities close at 8:00 PM sharp:**
- ✅ Weight logging entries
- ✅ Water intake entries  
- ✅ Meal logging entries
- ✅ Habit tracking entries
- ✅ Gym check-in submissions

**After 8:00 PM:**
- ❌ No new entries accepted for that day
- ❌ Bot shows: "Daily logging window closed. Come back tomorrow!"
- ✅ Users can still browse menus, view leaderboards, check progress

### Challenge Start Notification

When a challenge starts (or user joins), they receive:

```
🏆 Challenge Started: [Challenge Name]

📅 Duration: [Start Date] - [End Date]
💰 Entry Fee: [Rs. X or FREE]

⏰ IMPORTANT: Daily Cutoff Time
🕗 All activities close at 8:00 PM daily
   - Weight logs
   - Water intake
   - Meals & Habits
   - Gym check-ins

Plan your day accordingly! ⚡
```

### 10:00 PM Daily Processing

After all entries are locked:
- ✅ Calculate daily points for all participants
- ✅ Update challenge progress records
- ✅ Refresh leaderboard rankings
- ✅ Check for 6-day check-in bonus eligibility
- ✅ Generate daily summary logs

---

## 💳 PAYMENT SYSTEM - UNIVERSAL STANDARD

### Master Payment Pattern

**This pattern applies to ALL payment features:**
- Subscription Plans
- PT Subscriptions  
- Store Product Orders
- One-Day Events
- Challenge Entry Fees
- Shake Credit Purchases

### Default Values on Approval

```python
# When admin approves ANY payment request:
payment_data = {
    'method': 'unknown',           # ALWAYS this value
    'due_date': datetime.now(),    # Approval date = due date
    'grace_days': 0                # Default: no grace period
}
```

### Configurable Grace Period

```python
# Optional: Can be configured per feature
PAYMENT_CONFIG = {
    'subscriptions': {'grace_days': 3},
    'challenges': {'grace_days': 0},      # No grace for challenges
    'events': {'grace_days': 1},
    'store_products': {'grace_days': 0}
}
```

### AR Integration Flow

**On payment approval for challenges:**

```python
# Step 1: Create receivable
receivable_id = create_receivable(
    user_id=user_id,
    amount=challenge_price,
    description=f"Challenge Entry: {challenge_name}",
    method='unknown',                    # Universal default
    due_date=datetime.now().date()      # Today = due date
)

# Step 2: Create transaction (if partial payment)
if payment_amount > 0:
    transaction_id = create_transactions(
        receivable_id=receivable_id,
        amount=payment_amount,
        payment_date=datetime.now().date(),
        created_by=admin_id
    )

# Step 3: Update status
update_receivable_status(receivable_id)
# Status becomes:
# - 'paid' if amount_due <= 0
# - 'partial' if 0 < amount_due < original_amount
# - 'unpaid' if amount_due == original_amount

# Step 4: Enable reminders (if unpaid/partial)
if status in ['unpaid', 'partial']:
    schedule_payment_reminder(
        receivable_id=receivable_id,
        reminder_frequency='daily'
    )
```

### Payment Reminder Messages

```
⚠️ Payment Reminder

Challenge: [Challenge Name]
💰 Amount Due: Rs. [X]
📅 Due Date: [Date]

Please complete your payment to continue participating.

/view_receivables to see details
```

---

## 💬 MOTIVATIONAL MESSAGES - DATABASE STORAGE

### Database Table Schema

```sql
CREATE TABLE motivational_messages (
    id SERIAL PRIMARY KEY,
    message_text TEXT NOT NULL,
    category VARCHAR(50) DEFAULT 'checkin',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    used_count INTEGER DEFAULT 0
);

-- Index for fast random selection
CREATE INDEX idx_motivational_active ON motivational_messages(is_active) 
WHERE is_active = TRUE;
```

### 15 Default Messages

```sql
INSERT INTO motivational_messages (message_text, category) VALUES
('🔥 Great job! You showed up today!'),
('💪 Another step towards your goals!'),
('⭐ Consistency is key - you're doing it!'),
('🚀 Keep this momentum going!'),
('🎯 You're building great habits!'),
('✨ Your dedication is inspiring!'),
('👏 Way to prioritize your health!'),
('🏆 Champions show up even when it's tough!'),
('💯 You're on fire this week!'),
('🌟 Every workout counts - nice work!'),
('⚡ You're stronger than you think!'),
('🎉 Crushing it! Keep going!'),
('💪 That's the spirit! Well done!'),
('🔥 You're unstoppable today!'),
('✅ One more day closer to your best self!');
```

### Message Rotation Logic

```python
def get_random_motivational_message():
    """
    Get random message from DB and increment usage counter
    """
    query = """
        SELECT id, message_text 
        FROM motivational_messages 
        WHERE is_active = TRUE 
        ORDER BY RANDOM() 
        LIMIT 1
    """
    
    message = execute_query(query)
    
    # Track usage
    update_query = """
        UPDATE motivational_messages 
        SET used_count = used_count + 1 
        WHERE id = %s
    """
    execute_update(update_query, (message['id'],))
    
    return message['message_text']
```

### Admin Management

Future enhancement (Phase 4.3+):
- `/admin_messages` - View all motivational messages
- `/add_message` - Add custom messages
- `/toggle_message` - Enable/disable messages
- View usage statistics

---

## 🗄️ DATABASE SCHEMA

### New Tables Required

#### 1. challenges Table

```sql
CREATE TABLE challenges (
    challenge_id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    challenge_type VARCHAR(50) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    price DECIMAL(10, 2) DEFAULT 0,
    is_free BOOLEAN DEFAULT TRUE,
    status VARCHAR(20) DEFAULT 'scheduled',
    created_by INTEGER REFERENCES users(user_id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    broadcast_sent BOOLEAN DEFAULT FALSE,
    
    CONSTRAINT chk_dates CHECK (end_date > start_date),
    CONSTRAINT chk_price CHECK (price >= 0),
    CONSTRAINT chk_status CHECK (status IN ('scheduled', 'active', 'completed', 'cancelled'))
);

CREATE INDEX idx_challenges_status ON challenges(status);
CREATE INDEX idx_challenges_dates ON challenges(start_date, end_date);
```

#### 2. challenge_participants Table

```sql
CREATE TABLE challenge_participants (
    participation_id SERIAL PRIMARY KEY,
    challenge_id INTEGER REFERENCES challenges(challenge_id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
    joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    approval_status VARCHAR(20) DEFAULT 'pending',
    payment_status VARCHAR(20) DEFAULT 'unpaid',
    receivable_id INTEGER REFERENCES accounts_receivable(receivable_id),
    total_points INTEGER DEFAULT 0,
    daily_progress JSONB DEFAULT '{}',
    status VARCHAR(20) DEFAULT 'active',
    
    CONSTRAINT chk_approval CHECK (approval_status IN ('pending', 'approved', 'rejected')),
    CONSTRAINT chk_payment CHECK (payment_status IN ('unpaid', 'partial', 'paid', 'na')),
    CONSTRAINT chk_participant_status CHECK (status IN ('active', 'withdrawn', 'completed')),
    UNIQUE(challenge_id, user_id)
);

CREATE INDEX idx_participants_challenge ON challenge_participants(challenge_id);
CREATE INDEX idx_participants_user ON challenge_participants(user_id);
CREATE INDEX idx_participants_approval ON challenge_participants(approval_status);
```

#### 3. motivational_messages Table

```sql
-- Already defined above in Motivational Messages section
```

### Modified Tables

#### points_transactions (existing)

```sql
-- Add challenge_id for tracking
ALTER TABLE points_transactions 
ADD COLUMN challenge_id INTEGER REFERENCES challenges(challenge_id);

CREATE INDEX idx_points_challenge ON points_transactions(challenge_id);
```

---

## 🎮 CHALLENGES SYSTEM - DETAILED FLOW

### Admin Challenge Creation

#### Flow:
1. `/admin_challenges` → Admin Challenges Dashboard
2. "➕ Create New Challenge" button
3. Conversation flow collects:
   - Challenge Name
   - Challenge Type (Weight Loss, Consistency, Water, Gym Warrior, etc.)
   - Start Date (calendar picker)
   - End Date (calendar picker)
   - Pricing: "Is this a FREE challenge?" → Yes/No
   - If paid: Enter amount
   - Description (optional)
4. Confirmation screen shows all details
5. On confirm → Challenge created, scheduled for broadcast

#### Database Operation:

```python
def create_challenge(name, challenge_type, start_date, end_date, 
                    is_free, price, description, admin_id):
    query = """
        INSERT INTO challenges 
        (name, description, challenge_type, start_date, end_date, 
         price, is_free, status, created_by)
        VALUES (%s, %s, %s, %s, %s, %s, %s, 'scheduled', %s)
        RETURNING challenge_id
    """
    
    challenge_id = execute_insert(query, (
        name, description, challenge_type, start_date, end_date,
        price if not is_free else 0, is_free, admin_id
    ))
    
    return challenge_id
```

### Broadcast on Schedule

When challenge start_date arrives:

```python
def broadcast_challenge_start(challenge_id):
    """
    Triggered by scheduled job at midnight on start_date
    """
    challenge = get_challenge_by_id(challenge_id)
    
    message = f"""
🏆 NEW CHALLENGE STARTING TODAY!

📋 {challenge['name']}
🎯 Type: {challenge['challenge_type']}
📅 Duration: {challenge['start_date']} - {challenge['end_date']}
💰 Entry: {"FREE" if challenge['is_free'] else f"Rs. {challenge['price']}"}

{challenge['description']}

⏰ IMPORTANT: Daily Cutoff - 8:00 PM
All activities must be logged before 8 PM daily!

Join now: /challenges
"""
    
    # Send to all active/approved users
    users = get_all_active_users()
    for user in users:
        bot.send_message(user['user_id'], message)
    
    # Update challenge status
    update_query = """
        UPDATE challenges 
        SET status = 'active', broadcast_sent = TRUE 
        WHERE challenge_id = %s
    """
    execute_update(update_query, (challenge_id,))
```

### User Join Flow

#### For FREE Challenges:

1. User: `/challenges` → See active challenges
2. Click challenge → View details
3. "Join Challenge" button
4. Instant approval, no payment needed:
   ```sql
   INSERT INTO challenge_participants 
   (challenge_id, user_id, approval_status, payment_status, status)
   VALUES (%s, %s, 'approved', 'na', 'active')
   ```
5. User receives welcome message with cutoff reminder

#### For PAID Challenges:

1. User: `/challenges` → See active challenges
2. Click challenge → View details with price
3. "Join Challenge (Rs. X)" button
4. Create approval request:
   ```sql
   INSERT INTO challenge_participants 
   (challenge_id, user_id, approval_status, payment_status, status)
   VALUES (%s, %s, 'pending', 'unpaid', 'active')
   ```
5. Admin receives notification:
   ```
   💰 Challenge Join Request
   
   User: [Name] (@username)
   Challenge: [Challenge Name]
   Amount: Rs. [X]
   
   Approve? ✅ | Reject? ❌
   ```
6. On admin approval → Call AR integration (see Payment System section above)
7. If payment_status = 'paid' → Send welcome with cutoff reminder
8. If payment_status = 'unpaid'/'partial' → Send payment reminder daily

### Points Engine

#### Activity-to-Points Mapping

```python
CHALLENGE_POINTS_CONFIG = {
    'checkin': {
        'base_points': 100,
        'bonus_6day': 200,
        'description': '100 points per check-in, 200 bonus for 6+ days/week'
    },
    'water': {
        'points_per_unit': 5,
        'unit_size': 500,  # ml
        'description': '5 points per 500ml glass'
    },
    'weight': {
        'daily_log': 20,
        'description': '20 points for daily weight logging'
    },
    'habits': {
        'points_per_habit': 5,
        'description': '5 points per habit completed'
    },
    'shake': {
        'points_per_shake': 50,
        'description': '50 points per protein shake purchased'
    }
}
```

#### Points Calculation

```python
def award_challenge_points(user_id, challenge_id, activity_type, 
                          quantity=1, metadata=None):
    """
    Award points for challenge activities
    """
    config = CHALLENGE_POINTS_CONFIG.get(activity_type)
    
    # Calculate points based on activity
    if activity_type == 'checkin':
        points = config['base_points']
        
        # Check for 6-day bonus
        if metadata and metadata.get('weekly_checkins') >= 6:
            points += config['bonus_6day']
    
    elif activity_type == 'water':
        # quantity = ml consumed
        glasses = quantity / config['unit_size']
        points = int(glasses * config['points_per_unit'])
    
    elif activity_type == 'weight':
        points = config['daily_log']
    
    elif activity_type == 'habits':
        # quantity = number of habits completed
        points = quantity * config['points_per_habit']
    
    elif activity_type == 'shake':
        # quantity = number of shakes
        points = quantity * config['points_per_shake']
    
    else:
        points = 0
    
    # Insert transaction
    query = """
        INSERT INTO points_transactions 
        (user_id, points, transaction_type, description, challenge_id)
        VALUES (%s, %s, %s, %s, %s)
    """
    execute_insert(query, (
        user_id, points, activity_type, 
        f"{activity_type.title()} activity", challenge_id
    ))
    
    # Update participant total
    update_query = """
        UPDATE challenge_participants 
        SET total_points = total_points + %s
        WHERE challenge_id = %s AND user_id = %s
    """
    execute_update(update_query, (points, challenge_id, user_id))
    
    return points
```

### Scheduled Jobs

#### 8:00 PM - Cutoff Enforcement

```python
def enforce_daily_cutoff():
    """
    Runs at 8:00 PM daily
    No new entries accepted after this
    """
    # Set global flag
    DAILY_LOGGING_OPEN = False
    
    # All handler checks:
    if not DAILY_LOGGING_OPEN:
        return "⏰ Daily logging window closed at 8:00 PM. See you tomorrow!"
```

#### 10:00 PM - Daily Processing

```python
def process_daily_challenge_updates():
    """
    Runs at 10:00 PM daily
    Calculate points, update progress, refresh leaderboards
    """
    active_challenges = get_active_challenges()
    today = datetime.now().date()
    
    for challenge in active_challenges:
        participants = get_challenge_participants(challenge['challenge_id'])
        
        for participant in participants:
            user_id = participant['user_id']
            
            # Get today's activities
            activities = get_user_daily_activities(user_id, today)
            
            # Award points
            daily_points = 0
            
            if activities['checkin']:
                weekly_checkins = get_weekly_checkin_count(user_id)
                points = award_challenge_points(
                    user_id, challenge['challenge_id'], 'checkin',
                    metadata={'weekly_checkins': weekly_checkins}
                )
                daily_points += points
            
            if activities['water_ml'] > 0:
                points = award_challenge_points(
                    user_id, challenge['challenge_id'], 'water',
                    quantity=activities['water_ml']
                )
                daily_points += points
            
            if activities['weight_logged']:
                points = award_challenge_points(
                    user_id, challenge['challenge_id'], 'weight'
                )
                daily_points += points
            
            if activities['habits_count'] > 0:
                points = award_challenge_points(
                    user_id, challenge['challenge_id'], 'habits',
                    quantity=activities['habits_count']
                )
                daily_points += points
            
            # Update daily progress JSON
            update_query = """
                UPDATE challenge_participants 
                SET daily_progress = jsonb_set(
                    daily_progress, 
                    %s, 
                    %s
                )
                WHERE challenge_id = %s AND user_id = %s
            """
            execute_update(update_query, (
                f'{{{today}}}',
                json.dumps({'points': daily_points, 'activities': activities}),
                challenge['challenge_id'],
                user_id
            ))
        
        # Refresh leaderboard
        refresh_challenge_leaderboard(challenge['challenge_id'])
```

### Leaderboard

#### Query:

```python
def get_challenge_leaderboard(challenge_id, limit=10):
    """
    Get top participants by total points
    """
    query = """
        SELECT 
            cp.user_id,
            u.full_name,
            u.username,
            cp.total_points,
            cp.joined_date,
            RANK() OVER (ORDER BY cp.total_points DESC) as rank
        FROM challenge_participants cp
        JOIN users u ON cp.user_id = u.user_id
        WHERE cp.challenge_id = %s 
        AND cp.approval_status = 'approved'
        AND cp.status = 'active'
        ORDER BY cp.total_points DESC
        LIMIT %s
    """
    
    return execute_query(query, (challenge_id, limit))
```

#### Display:

```
🏆 Challenge Leaderboard

Challenge: [Name]
Updated: [Timestamp]

🥇 1. [User Name] - 1,250 pts
🥈 2. [User Name] - 1,100 pts
🥉 3. [User Name] - 980 pts
4. [User Name] - 875 pts
5. [User Name] - 820 pts
...
10. [User Name] - 450 pts

Your Rank: #7 (720 pts)
Keep pushing! 💪
```

### End-of-Challenge Reports

#### Graphical Report Generation

```python
import matplotlib.pyplot as plt
import io

def generate_challenge_report(user_id, challenge_id):
    """
    Generate visual summary of user's challenge performance
    """
    # Get user data
    participant = get_participant_data(user_id, challenge_id)
    challenge = get_challenge_by_id(challenge_id)
    
    # Prepare data
    daily_progress = participant['daily_progress']
    dates = sorted(daily_progress.keys())
    
    # Weight journey data
    weight_data = []
    for date in dates:
        if 'weight' in daily_progress[date]['activities']:
            weight_data.append({
                'date': date,
                'weight': daily_progress[date]['activities']['weight']
            })
    
    # Activity breakdown
    activity_totals = {
        'checkin': 0,
        'water': 0,
        'weight': 0,
        'habits': 0,
        'shake': 0
    }
    
    for date in dates:
        activities = daily_progress[date]['activities']
        for activity in activity_totals.keys():
            if activity in activities:
                activity_totals[activity] += 1
    
    # Create figure with 2 subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
    
    # Chart 1: Weight Journey
    if weight_data:
        weights = [w['weight'] for w in weight_data]
        dates_weight = [w['date'] for w in weight_data]
        
        ax1.plot(dates_weight, weights, marker='o', linewidth=2, color='#4CAF50')
        ax1.set_title(f'Weight Journey - {challenge["name"]}', fontsize=14, fontweight='bold')
        ax1.set_xlabel('Date')
        ax1.set_ylabel('Weight (kg)')
        ax1.grid(True, alpha=0.3)
        
        # Show improvement
        if len(weights) > 1:
            change = weights[-1] - weights[0]
            color = 'green' if change < 0 else 'red'
            ax1.text(0.5, 0.95, f'Change: {change:+.1f} kg', 
                    transform=ax1.transAxes, ha='center',
                    bbox=dict(boxstyle='round', facecolor=color, alpha=0.3))
    
    # Chart 2: Activity Breakdown
    activities = list(activity_totals.keys())
    counts = list(activity_totals.values())
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8']
    
    ax2.bar(activities, counts, color=colors)
    ax2.set_title('Activity Breakdown', fontsize=14, fontweight='bold')
    ax2.set_xlabel('Activity Type')
    ax2.set_ylabel('Days Completed')
    ax2.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    
    # Save to buffer
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
    buffer.seek(0)
    plt.close()
    
    return buffer
```

#### Report Message

```python
def send_challenge_completion_report(user_id, challenge_id):
    """
    Send comprehensive end-of-challenge report
    """
    # Generate chart
    chart_buffer = generate_challenge_report(user_id, challenge_id)
    
    # Get stats
    participant = get_participant_data(user_id, challenge_id)
    leaderboard = get_challenge_leaderboard(challenge_id, limit=100)
    user_rank = next((i+1 for i, p in enumerate(leaderboard) 
                     if p['user_id'] == user_id), None)
    
    # Calculate stats
    total_days = len(participant['daily_progress'])
    total_points = participant['total_points']
    
    # Generate improvement suggestions
    suggestions = generate_improvement_suggestions(participant)
    
    message = f"""
🏆 Challenge Complete!

📊 Your Performance Summary:

📈 Final Stats:
• Total Points: {total_points}
• Rank: #{user_rank} out of {len(leaderboard)}
• Days Active: {total_days}

💡 Improvement Suggestions:
{suggestions}

Great effort! 🎉
Ready for the next challenge?
"""
    
    # Send chart + message
    bot.send_photo(user_id, photo=chart_buffer, caption=message)
```

#### Improvement Suggestions Logic

```python
def generate_improvement_suggestions(participant):
    """
    AI-style suggestions based on activity patterns
    """
    daily_progress = participant['daily_progress']
    suggestions = []
    
    # Analyze patterns
    checkin_rate = calculate_activity_rate(daily_progress, 'checkin')
    water_rate = calculate_activity_rate(daily_progress, 'water')
    weight_consistency = calculate_activity_rate(daily_progress, 'weight')
    
    if checkin_rate < 0.7:
        suggestions.append("📍 Try to check in more consistently - aim for 6+ days/week for bonus points!")
    
    if water_rate < 0.5:
        suggestions.append("💧 Stay hydrated! Set reminders to log your water intake daily.")
    
    if weight_consistency < 0.8:
        suggestions.append("⚖️ Daily weigh-ins help track progress - make it a morning routine!")
    
    # Weight improvement
    weight_data = extract_weight_data(daily_progress)
    if weight_data and len(weight_data) > 7:
        trend = calculate_weight_trend(weight_data)
        if trend > 0:
            suggestions.append("🎯 Focus on consistent calorie deficit and increase cardio sessions.")
        elif trend < -1:
            suggestions.append("⚠️ Weight loss is too rapid - ensure you're eating enough protein.")
    
    if not suggestions:
        suggestions.append("🌟 Excellent performance! Keep this consistency in the next challenge!")
    
    return '\n'.join(f"• {s}" for s in suggestions)
```

---

## 🏃 GYM CHECK-IN - DETAILED FLOW

### User Check-in Submission

#### Flow:
1. User: `/checkin` or clicks "Gym Check-in" button
2. Bot checks if cutoff passed:
   ```python
   now = datetime.now().time()
   cutoff = time(20, 0)  # 8:00 PM
   
   if now > cutoff:
       return "⏰ Daily logging window closed at 8:00 PM. See you tomorrow!"
   ```
3. If before cutoff → Ask method:
   ```
   📸 How would you like to check in?
   
   [Photo Check-in] [Text Check-in]
   ```
4. User selects Photo → Upload gym selfie
5. User selects Text → Send location/description
6. Create approval request:
   ```sql
   INSERT INTO attendance_queue 
   (user_id, check_in_time, photo_path, status)
   VALUES (%s, NOW(), %s, 'pending')
   ```
7. User receives: "✅ Check-in submitted! Awaiting admin approval."

### Admin Approval

#### Flow:
1. Admin receives notification:
   ```
   📸 Gym Check-in Request
   
   User: [Name] (@username)
   Time: [HH:MM]
   
   [Photo if provided]
   
   Approve? ✅ | Reject? ❌
   ```
2. Admin clicks ✅ Approve
3. System executes:
   ```python
   # Update attendance queue
   UPDATE attendance_queue 
   SET status = 'approved', approved_by = admin_id, approved_at = NOW()
   WHERE queue_id = %s
   
   # Award points
   award_challenge_points(user_id, None, 'checkin')
   
   # Get random motivational message
   message = get_random_motivational_message()
   
   # Send to user
   bot.send_message(user_id, f"✅ Check-in Approved! +100 points\n\n{message}")
   ```

### 6-Day Bonus Logic

```python
def check_weekly_bonus(user_id):
    """
    Called during 10 PM daily processing
    Check if user has 6+ check-ins this week
    """
    query = """
        SELECT COUNT(*) as count
        FROM attendance_queue
        WHERE user_id = %s
        AND status = 'approved'
        AND approved_at >= DATE_TRUNC('week', CURRENT_DATE)
        AND approved_at < DATE_TRUNC('week', CURRENT_DATE) + INTERVAL '7 days'
    """
    
    result = execute_query(query, (user_id,))
    
    if result['count'] >= 6:
        # Award bonus (only once per week)
        bonus_query = """
            SELECT COUNT(*) FROM points_transactions
            WHERE user_id = %s
            AND transaction_type = 'checkin_bonus'
            AND created_at >= DATE_TRUNC('week', CURRENT_DATE)
        """
        
        already_awarded = execute_query(bonus_query, (user_id,))
        
        if already_awarded['count'] == 0:
            # Award 200 bonus points
            insert_query = """
                INSERT INTO points_transactions 
                (user_id, points, transaction_type, description)
                VALUES (%s, 200, 'checkin_bonus', 'Weekly 6-day check-in bonus')
            """
            execute_insert(insert_query, (user_id,))
            
            # Notify user
            bot.send_message(user_id, 
                "🎉 BONUS UNLOCKED! +200 points for 6+ check-ins this week! 💪")
```

---

## 📋 IMPLEMENTATION CHECKLIST

### Phase 1: Database Setup (Day 1)

- [ ] Create migration script `migrate_challenges_system.py`
- [ ] Add `challenges` table
- [ ] Add `challenge_participants` table
- [ ] Add `motivational_messages` table with 15 default entries
- [ ] Modify `points_transactions` to add `challenge_id` column
- [ ] Run migration and verify all tables created
- [ ] Test: Insert sample challenge and participant records

### Phase 2: Payment Integration (Day 1-2)

- [ ] Create `src/database/challenge_payment_operations.py`
- [ ] Implement `create_challenge_receivable()` function
- [ ] Implement `process_challenge_payment()` function
- [ ] Wire into admin approval handler
- [ ] Test: Create paid challenge, approve participant, verify AR record
- [ ] Test: Verify payment reminders for unpaid/partial participants

### Phase 3: Admin Challenge Creation (Day 2)

- [ ] Create `src/handlers/admin_challenge_handlers.py`
- [ ] Implement `/admin_challenges` command with dashboard
- [ ] Build challenge creation conversation flow
- [ ] Add calendar date pickers for start/end dates
- [ ] Add pricing toggle (free vs. paid)
- [ ] Implement challenge broadcast scheduler
- [ ] Test: Create free challenge, verify broadcast on start_date
- [ ] Test: Create paid challenge, verify pricing flow

### Phase 4: User Challenge Participation (Day 2-3)

- [ ] Update `src/handlers/challenge_handlers.py`
- [ ] Implement `/challenges` command showing active challenges
- [ ] Build challenge detail view with join button
- [ ] Implement join flow for free challenges (instant approval)
- [ ] Implement join flow for paid challenges (approval queue)
- [ ] Add challenge welcome message with cutoff time
- [ ] Test: Join free challenge, verify instant participation
- [ ] Test: Join paid challenge, verify approval queue

### Phase 5: Points Engine (Day 3)

- [ ] Add `CHALLENGE_POINTS_CONFIG` to `src/config.py`
- [ ] Create `src/utils/challenge_points.py`
- [ ] Implement `award_challenge_points()` function
- [ ] Wire check-in approval to points award
- [ ] Wire water logging to points award
- [ ] Wire weight logging to points award
- [ ] Wire habit tracking to points award
- [ ] Wire shake purchases to points award
- [ ] Test: Complete activities, verify points awarded correctly
- [ ] Test: Verify 6-day bonus calculation

### Phase 6: Cutoff Enforcement (Day 3)

- [ ] Create `src/utils/cutoff_enforcement.py`
- [ ] Add global flag `DAILY_LOGGING_OPEN`
- [ ] Update all activity handlers to check cutoff
- [ ] Add cutoff check message
- [ ] Test: Try logging before 8 PM (should work)
- [ ] Test: Try logging after 8 PM (should reject)

### Phase 7: Scheduled Jobs (Day 4)

- [ ] Update `src/utils/scheduled_jobs.py`
- [ ] Add 8:00 PM job: `enforce_daily_cutoff()`
- [ ] Add 10:00 PM job: `process_daily_challenge_updates()`
- [ ] Implement challenge progress calculation
- [ ] Implement weekly bonus check logic
- [ ] Implement leaderboard refresh
- [ ] Test: Verify jobs run at correct times
- [ ] Test: Verify points calculated correctly

### Phase 8: Leaderboard (Day 4)

- [ ] Create `src/database/challenge_leaderboard_operations.py`
- [ ] Implement `get_challenge_leaderboard()` query
- [ ] Build leaderboard display formatting
- [ ] Add `/leaderboard` command
- [ ] Show user's current rank
- [ ] Test: Multiple users, verify ranking logic

### Phase 9: Motivational Messages (Day 4)

- [ ] Create `src/database/motivational_operations.py`
- [ ] Implement `get_random_motivational_message()` function
- [ ] Wire into check-in approval flow
- [ ] Test: Approve multiple check-ins, verify different messages
- [ ] Test: Verify message rotation and usage tracking

### Phase 10: Graphical Reports (Day 5)

- [ ] Install matplotlib: `pip install matplotlib`
- [ ] Create `src/utils/challenge_reports.py`
- [ ] Implement `generate_challenge_report()` chart generation
- [ ] Implement weight journey line chart
- [ ] Implement activity breakdown bar chart
- [ ] Create `generate_improvement_suggestions()` logic
- [ ] Wire into challenge completion flow
- [ ] Test: Complete challenge, verify chart generation
- [ ] Test: Verify suggestions quality

### Phase 11: Broadcast System (Day 5)

- [ ] Update `src/handlers/broadcast_handlers.py`
- [ ] Implement `broadcast_challenge_start()` function
- [ ] Add challenge start notification scheduler
- [ ] Add cutoff time in welcome messages
- [ ] Test: Schedule challenge, verify broadcast on start_date
- [ ] Test: Join challenge, verify welcome with cutoff info

### Phase 12: Testing & Validation (Day 6)

- [ ] End-to-end test: Admin creates free challenge
- [ ] End-to-end test: User joins free challenge
- [ ] End-to-end test: Admin creates paid challenge
- [ ] End-to-end test: User joins paid challenge with payment
- [ ] End-to-end test: Complete activities before 8 PM
- [ ] End-to-end test: Try activities after 8 PM (should reject)
- [ ] End-to-end test: Get 6-day bonus
- [ ] End-to-end test: View leaderboard
- [ ] End-to-end test: Complete challenge, receive report
- [ ] Load test: 50 users in one challenge

### Phase 13: Documentation (Day 6)

- [ ] Create `CHALLENGES_USER_GUIDE.md`
- [ ] Create `CHALLENGES_ADMIN_GUIDE.md`
- [ ] Create `CHALLENGES_POINTS_REFERENCE.md`
- [ ] Update `DOCUMENTATION_INDEX.md`
- [ ] Document payment flow integration
- [ ] Document cutoff enforcement logic
- [ ] Add troubleshooting section

---

## 🎯 SUCCESS CRITERIA

### Challenges System
✅ Admin can create free and paid challenges  
✅ Challenges broadcast automatically on start_date  
✅ Users receive cutoff time notification  
✅ Free challenges = instant join  
✅ Paid challenges = approval queue + AR integration  
✅ Payment reminders work for unpaid participants  
✅ Points awarded correctly for all activity types  
✅ 6-day bonus calculated and awarded  
✅ Leaderboard updates daily at 10 PM  
✅ End-of-challenge reports generated with charts  
✅ Improvement suggestions personalized  

### Gym Check-in
✅ Users can submit photo or text check-ins  
✅ Check-ins blocked after 8 PM cutoff  
✅ Admin receives approval requests  
✅ Approved check-ins award +100 points  
✅ Random motivational message from DB pool  
✅ 15 unique messages rotate correctly  
✅ Messages tracked in database  

### Cutoff Enforcement
✅ All activity handlers check 8 PM cutoff  
✅ Rejection message shown after cutoff  
✅ Daily processing runs at 10 PM  
✅ Users notified of cutoff on challenge join  

### Payment System
✅ All payment approvals use method='unknown'  
✅ due_date set to approval date  
✅ Grace period configurable per feature  
✅ AR receivables created correctly  
✅ Payment reminders sent daily  

---

## 🚀 DEPLOYMENT STEPS

1. **Backup Database**
   ```bash
   pg_dump -U postgres fitness_club > backup_before_challenges.sql
   ```

2. **Run Migration**
   ```bash
   python migrate_challenges_system.py
   ```

3. **Verify Tables**
   ```sql
   SELECT table_name FROM information_schema.tables 
   WHERE table_name IN ('challenges', 'challenge_participants', 'motivational_messages');
   ```

4. **Update Requirements**
   ```bash
   pip install matplotlib
   pip freeze > requirements.txt
   ```

5. **Test in Development**
   - Create test challenge
   - Join as test user
   - Submit activities
   - Verify points
   - Check leaderboard

6. **Deploy to Production**
   ```bash
   git add .
   git commit -m "feat: challenges system + enhanced check-in"
   git push origin main
   ```

7. **Monitor Logs**
   ```bash
   tail -f logs/bot.log
   ```

---

## 📚 RELATED DOCUMENTATION

- [APPROVAL_STATUS_FLOW.md](APPROVAL_STATUS_FLOW.md) - Universal payment approval pattern
- [PHASE_4_2_SUMMARY.md](PHASE_4_2_SUMMARY.md) - Commerce Hub implementation reference
- [PAYMENT_REQUEST_SYSTEM.md](PAYMENT_REQUEST_SYSTEM.md) - AR integration patterns
- [BROADCAST_SYSTEM_DOCS.md](BROADCAST_SYSTEM_DOCS.md) - Broadcast notification system

---

**Plan Status**: ✅ **READY FOR IMPLEMENTATION**  
**Estimated Duration**: 6 days  
**Risk Level**: Medium (complex points calculation, chart generation)  
**Dependencies**: matplotlib library, scheduled jobs infrastructure
