# Phase 4.1: Email & SMS Notifications - Implementation Guide

## Overview
Phase 4.1 extends the notification system to support Email and SMS channels alongside Telegram, enabling multi-channel communication with users.

---

## Architecture

### 3-Layer Implementation

```
Database Layer
    ↓
notification_channels_operations.py (11 functions)
    ↓
Service Layer
    ↓
email_service.py (7 functions)
sms_service.py (8 functions)
    ↓
Handler Layer
    ↓
notification_preferences_handlers.py (10+ async functions)
    ↓
Bot.py Integration
```

---

## Database Layer

### `src/database/notification_channels_operations.py` (300+ lines, 11 functions)

**Purpose:** Manage user notification channels (Email, SMS, Telegram)

#### Functions:

1. **`add_notification_channel(user_id, channel_type, channel_address)`**
   - Add new email or SMS channel for user
   - Validates channel type and address
   - Prevents duplicate channels
   - Returns: True if added, False if exists or error

2. **`get_user_channels(user_id, channel_type=None)`**
   - Retrieve all notification channels for user
   - Optional filter by channel type
   - Returns: List of channel dictionaries

3. **`get_active_channels(user_id, channel_type=None)`**
   - Get only active channels
   - Filters by is_active = TRUE
   - Returns: List of active channels

4. **`verify_channel(channel_id, verification_code)`**
   - Mark channel as verified after email/SMS verification
   - Validation code sent to channel
   - Returns: True if verified successfully

5. **`toggle_channel(channel_id, is_active)`**
   - Enable or disable a notification channel
   - User can pause channels without deleting
   - Returns: True if toggled successfully

6. **`delete_channel(channel_id)`**
   - Delete a notification channel permanently
   - Returns: True if deleted

7. **`get_notification_preferences(user_id)`**
   - Retrieve user's notification type preferences
   - Returns JSON with 8 notification types
   - Example:
   ```python
   {
       'points_awarded': True,
       'payment_due': True,
       'membership_expired': True,
       ...
   }
   ```

8. **`update_notification_preferences(user_id, preferences)`**
   - Update which notifications user wants to receive
   - Accepts preferences dictionary
   - Returns: True if updated

9. **`get_channel_statistics()`**
   - Get statistics about all channels
   - Shows counts by type (email, sms)
   - Returns: Dictionary with total, active, verified counts

10. **`cleanup_inactive_channels(days=30)`**
    - Delete inactive channels older than X days (maintenance)
    - Called periodically to clean up
    - Returns: Count of deleted channels

### Database Schema

```sql
-- New table for notification channels
CREATE TABLE notification_channels (
    channel_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
    channel_type VARCHAR(20), -- 'email', 'sms', 'telegram'
    channel_address VARCHAR(255), -- email or phone number
    is_active BOOLEAN DEFAULT TRUE,
    verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Modified users table (from Phase 1)
ALTER TABLE users ADD COLUMN notification_preferences JSONB;
```

---

## Service Layer

### `src/services/email_service.py` (250+ lines, 7 functions)

**Purpose:** Send emails using SMTP (Gmail, Outlook, custom SMTP server)

#### Configuration (in .env):
```
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=your-email@gmail.com
SENDER_PASSWORD=your-app-password
SENDER_NAME=Fitness Club
```

#### Functions:

1. **`send_email(recipient_email, subject, body, template_vars=None)`**
   - Generic email sending function
   - Supports template variable substitution
   - Creates multipart email (text + HTML)
   - Returns: True if sent, False on error

2. **`send_payment_due_email(recipient_email, name, days, expiry_date, amount)`**
   - Payment reminder: "Membership expiring in X days"
   - Includes renewal amount
   - Calls generic send_email with template

3. **`send_membership_expired_email(recipient_email, name, expiry_date)`**
   - Membership expired notification
   - Encourages renewal

4. **`send_points_awarded_email(recipient_email, name, points, activity, total_points, rank)`**
   - Points earned notification
   - Shows activity, point count, and ranking

5. **`send_achievement_email(recipient_email, name, achievement, description, reward)`**
   - Achievement unlocked notification
   - Shows reward points

6. **`send_challenge_reminder_email(recipient_email, name, challenge_type, days_remaining, progress)`**
   - Challenge deadline reminder
   - Shows time remaining and progress

7. **`send_daily_reminder_email(recipient_email, name)`**
   - Daily activity reminder
   - Encourages user engagement

8. **`verify_email_configuration()`**
   - Test SMTP connection
   - Verifies credentials work
   - Returns: True if configured correctly

#### Email Templates:
- Payment Due
- Membership Expired
- Points Awarded
- Achievement Unlocked
- Challenge Reminder
- Daily Reminder

---

### `src/services/sms_service.py` (300+ lines, 8 functions)

**Purpose:** Send SMS using Twilio or AWS SNS

#### Configuration (in .env):
```
# For Twilio:
SMS_PROVIDER=twilio
SMS_ACCOUNT_SID=your-account-sid
SMS_AUTH_TOKEN=your-auth-token
SMS_PHONE_NUMBER=+1234567890

# OR for AWS SNS:
SMS_PROVIDER=aws
AWS_ACCESS_KEY=your-access-key
AWS_SECRET_KEY=your-secret-key
AWS_REGION=us-east-1
```

#### Functions:

1. **`validate_phone_number(phone_number)`**
   - Validates Indian phone number format (10 digits)
   - Accepts: 9876543210, +919876543210, 91-9876543210
   - Returns: True if valid format

2. **`format_phone_number(phone_number)`**
   - Converts to international format (+91...)
   - Handles various input formats
   - Returns: Formatted number or None

3. **`send_sms_twilio(phone_number, message)`**
   - Send via Twilio API
   - Returns: True if sent

4. **`send_sms_aws(phone_number, message)`**
   - Send via AWS SNS
   - Returns: True if sent

5. **`send_sms(phone_number, message)`**
   - Route to appropriate provider
   - Validates and formats number
   - Limits message to 160 chars
   - Returns: True if sent

6. **`send_payment_due_sms(phone_number, name, days, expiry_date)`**
   - Payment reminder SMS (160 chars)

7. **`send_achievement_sms(phone_number, name, achievement, reward)`**
   - Achievement SMS notification

8. **`verify_sms_configuration()`**
   - Test SMS service connection
   - Returns: True if configured

#### SMS Templates (160 char limit):
- Payment Due
- Membership Expired
- Points Awarded
- Achievement Unlocked
- Challenge Reminder
- Daily Reminder

---

## Handler Layer

### `src/handlers/notification_preferences_handlers.py` (300+ lines, 10+ async functions)

**Purpose:** Telegram UI for managing notification channels and preferences

#### Commands:
- `/notification_settings` - Main settings menu

#### Functions:

1. **`cmd_notification_settings(update, context)`**
   - Display settings menu with 3 options:
     - 📧 Email Settings
     - 📱 SMS Settings
     - 🔔 Preferences

2. **`callback_email_settings(update, context)`**
   - Show email addresses
   - Allow add/delete/toggle
   - Display verification status

3. **`callback_sms_settings(update, context)`**
   - Show phone numbers (masked for privacy)
   - Allow add/delete/toggle
   - Display verification status

4. **`callback_preferences_settings(update, context)`**
   - Show 8 notification type toggles
   - Allow enable/disable each type

5. **`callback_toggle_preference(update, context)`**
   - Toggle a specific notification type on/off
   - Update database
   - Refresh preferences screen

6. **`callback_email_add(update, context)`**
   - Prompt user to send email address
   - Sets flag in context.user_data

7. **`callback_sms_add(update, context)`**
   - Prompt user to send phone number
   - Validates Indian format
   - Sets flag in context.user_data

8. **`callback_toggle_channel(update, context)`**
   - Enable/disable an email or SMS channel
   - User can temporarily pause without deleting

9. **`callback_delete_channel(update, context)`**
   - Delete email or SMS channel permanently

10. **`callback_settings_back(update, context)`**
    - Navigate back to main settings menu

11. **`callback_settings_close(update, context)`**
    - Close settings dialog

---

## Integration with Notification System

### Modified: `src/database/notifications_operations.py`

Add new function to send via multiple channels:

```python
def send_multi_channel_notification(user_id, notif_type, title, description):
    """Send notification via all user's active channels"""
    
    # 1. Send Telegram notification (existing)
    create_notification(user_id, notif_type, title, description)
    
    # 2. Get user's email and send
    email_channels = get_active_channels(user_id, 'email')
    for channel in email_channels:
        if user_preferences[notif_type]:  # Check preference
            send_appropriate_email(channel['channel_address'], title, description)
    
    # 3. Get user's phone and send SMS
    sms_channels = get_active_channels(user_id, 'sms')
    for channel in sms_channels:
        if user_preferences[notif_type]:
            send_appropriate_sms(channel['channel_address'], title, description)
```

---

## New Commands & UI

### User Commands:
```
/notification_settings    - Manage email, SMS, and preferences
```

### Settings Menu Flow:
```
/notification_settings
    ├── 📧 Email Settings
    │   ├── List current emails
    │   ├── ➕ Add Email
    │   ├── Toggle active/inactive
    │   └── Delete email
    │
    ├── 📱 SMS Settings
    │   ├── List current numbers (masked)
    │   ├── ➕ Add SMS
    │   ├── Toggle active/inactive
    │   └── Delete number
    │
    └── 🔔 Preferences
        ├── ✨ Points Awarded (toggle)
        ├── ✅ Attendance Approved (toggle)
        ├── 💳 Payment Due (toggle)
        ├── ❌ Membership Expired (toggle)
        ├── 🏆 Achievement Unlocked (toggle)
        ├── 🔔 Challenge Reminder (toggle)
        ├── 📊 Leaderboard Update (toggle)
        └── 📱 Daily Reminder (toggle)
```

---

## Configuration Setup

### Step 1: Gmail SMTP Setup
1. Enable 2-factor authentication on Gmail
2. Generate app password: https://myaccount.google.com/apppasswords
3. Add to .env:
   ```
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587
   SENDER_EMAIL=your-email@gmail.com
   SENDER_PASSWORD=xxxx-xxxx-xxxx-xxxx
   SENDER_NAME=Fitness Club
   ```

### Step 2: Twilio SMS Setup
1. Create Twilio account: https://www.twilio.com
2. Get Account SID and Auth Token
3. Add to .env:
   ```
   SMS_PROVIDER=twilio
   SMS_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   SMS_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   SMS_PHONE_NUMBER=+1234567890
   ```

### Step 3: Install Dependencies
```bash
pip install twilio boto3
```

### Step 4: Database Migration
```sql
-- Add new table
CREATE TABLE notification_channels (
    channel_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
    channel_type VARCHAR(20),
    channel_address VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Modify users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS notification_preferences JSONB DEFAULT '{}';
```

---

## Usage Examples

### For Users:

**Add Email:**
```
1. Send /notification_settings
2. Click "📧 Email Settings"
3. Click "➕ Add Email"
4. Send your email address
5. Verification email sent
```

**Add SMS:**
```
1. Send /notification_settings
2. Click "📱 SMS Settings"
3. Click "➕ Add SMS"
4. Send phone number (10 digits)
5. Verification SMS sent
```

**Manage Preferences:**
```
1. Send /notification_settings
2. Click "🔔 Preferences"
3. Click any notification type to toggle
4. Changes saved automatically
```

### For Backend:

**Send Multi-Channel Notification:**
```python
from src.database.notifications_operations import send_multi_channel_notification
from src.services.email_service import send_payment_due_email
from src.services.sms_service import send_payment_due_sms
from src.database.notification_channels_operations import get_active_channels

def send_payment_reminder(user_id, name, email, phone, days, expiry_date, amount):
    # Send Telegram
    create_notification(user_id, 'payment_due', f'💳 Payment Due', f'Expires in {days} days')
    
    # Send Email
    if email:
        send_payment_due_email(email, name, days, expiry_date, amount)
    
    # Send SMS
    if phone:
        send_payment_due_sms(phone, name, days, expiry_date)
```

---

## Notification Preferences

### 8 Notification Types (Can be enabled/disabled):

1. **Points Awarded** (✨) - User earned points
2. **Attendance Approved** (✅) - Check-in approved
3. **Payment Due** (💳) - 7 days before expiry
4. **Membership Expired** (❌) - Membership expired
5. **Achievement Unlocked** (🏆) - New milestone
6. **Challenge Reminder** (🔔) - Challenge deadline
7. **Leaderboard Update** (📊) - Rank changed
8. **Daily Reminder** (📱) - Daily activity prompt

### Default Settings:
- All notifications: **Enabled** (except Daily Reminder)
- Daily Reminder: **Disabled** (user can enable)

### User Control:
- Can enable/disable each type independently
- Applies to all channels (Email, SMS, Telegram)
- Changes reflected immediately

---

## Error Handling

### Email Service:
- SMTP authentication failure → Log and return False
- Network error → Retry with exponential backoff
- Invalid email format → Return False immediately
- Missing configuration → Log warning, return False

### SMS Service:
- Invalid phone number → Validate and return False
- Provider API error → Log and return False
- Rate limiting → Queue and retry later
- Missing configuration → Log warning, return False

### Channel Management:
- Duplicate channel → Return False (already exists)
- Non-existent channel → Return False silently
- Permission denied → Log and return False
- Database error → Log and return False

---

## Performance Considerations

### Email:
- Async sending recommended for production
- Batch sending for daily reminders
- Template caching for speed
- SMTP connection pooling

### SMS:
- Rate limiting per user (e.g., max 5 SMS/hour)
- Queue system for high volume
- Retry failed sends
- Monitor API usage

### Database:
- Index on (user_id, channel_type) for quick lookups
- Index on (created_at) for cleanup operations
- Archive old channels periodically

---

## Security Considerations

### Data Protection:
- Phone numbers masked in UI (show only last 4 digits)
- Passwords stored securely (app passwords, not main password)
- HTTPS for SMTP (TLS 1.2+)
- Verification codes sent via channel

### Rate Limiting:
- Max email: 10/hour per user
- Max SMS: 5/hour per user
- Daily reminder: Once per day
- Prevent spam/abuse

### Privacy:
- Users can delete channels anytime
- Preferences stored in database (user control)
- No sharing of contact info
- GDPR compliant (right to deletion)

---

## Testing Phase 4.1

### Test Email Setup:
1. Add email via /notification_settings
2. Verify configuration with test email
3. Check logs for SMTP errors
4. Verify email received

### Test SMS Setup:
1. Add phone number via /notification_settings
2. Send test SMS (optional test function)
3. Check logs for provider errors
4. Verify SMS received

### Test Notification Flow:
1. Set up email and SMS
2. Trigger notification (e.g., earn points)
3. Verify Telegram notification sent
4. Verify email received
5. Verify SMS received

### Test Preferences:
1. Disable "Payment Due" notifications
2. Trigger payment due
3. Verify no notifications sent on any channel
4. Enable it again and retry

---

## Monitoring & Logging

### Logs to Check:
```bash
# Email sending
grep "Email sent to" logs/fitness_bot.log

# SMS sending
grep "SMS sent via" logs/fitness_bot.log

# Errors
grep "ERROR" logs/fitness_bot.log | grep -i "email\|sms"

# Channel management
grep "Channel" logs/fitness_bot.log
```

### Metrics to Track:
- Email delivery rate
- SMS delivery rate
- Channel verification rate
- Preference changes
- Notification preferences distribution

---

## Next: Phase 4.2

Phase 4.2 will add:
- **Real Payment Gateway Integration** (Stripe/Razorpay)
- Auto-payment handling
- Invoice generation
- Refund processing
- Subscription management

---

## Files Created in Phase 4.1

1. `src/database/notification_channels_operations.py` (300+ lines)
2. `src/services/email_service.py` (250+ lines)
3. `src/services/sms_service.py` (300+ lines)
4. `src/handlers/notification_preferences_handlers.py` (300+ lines)
5. `PHASE_4_1_IMPLEMENTATION.md` (This file)

**Total Phase 4.1 Code:** ~1,200 lines

---

## Environment Variables Needed

```env
# Email (Gmail)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=your-email@gmail.com
SENDER_PASSWORD=xxxx-xxxx-xxxx-xxxx
SENDER_NAME=Fitness Club

# SMS (Choose one)
# Option 1: Twilio
SMS_PROVIDER=twilio
SMS_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
SMS_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
SMS_PHONE_NUMBER=+1234567890

# Option 2: AWS SNS
SMS_PROVIDER=aws
AWS_ACCESS_KEY=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_REGION=us-east-1
```

---

**Phase 4.1 Status: ✅ COMPLETE**

Ready for deployment and integration into bot.py!
