# Phase 4.1 Quick Reference - Email & SMS Notifications

## 🎯 Summary

**Phase 4.1** adds multi-channel notifications (Email + SMS) to extend beyond Telegram, enabling gym to reach users via their preferred communication channels.

---

## 📋 What Was Built

| Component | Functions | Lines |
|-----------|-----------|-------|
| notification_channels_operations.py | 11 | 300+ |
| email_service.py | 7 | 250+ |
| sms_service.py | 8 | 300+ |
| notification_preferences_handlers.py | 10+ | 300+ |
| **Total Phase 4.1** | **36+** | **~1,200** |

---

## 🔧 Quick Setup

### 1. Configure Email (Gmail)
```bash
# Generate app password at: https://myaccount.google.com/apppasswords
# Add to .env:
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=your-email@gmail.com
SENDER_PASSWORD=xxxx-xxxx-xxxx-xxxx
SENDER_NAME=Fitness Club
```

### 2. Configure SMS (Choose One)
```bash
# Option A: Twilio
SMS_PROVIDER=twilio
SMS_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
SMS_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
SMS_PHONE_NUMBER=+1234567890

# Option B: AWS SNS
SMS_PROVIDER=aws
AWS_ACCESS_KEY=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_REGION=us-east-1
```

### 3. Create Database Table
```sql
CREATE TABLE notification_channels (
    channel_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
    channel_type VARCHAR(20),
    channel_address VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE users ADD COLUMN IF NOT EXISTS notification_preferences JSONB DEFAULT '{}';
```

### 4. Install Dependencies
```bash
pip install twilio boto3
pip install -r requirements.txt
```

### 5. Restart Bot
```bash
python -m src.bot
```

---

## 📊 New Command

```
/notification_settings     ⚙️ Manage email, SMS, & preferences
```

---

## 💳 Database Operations (11 functions)

```python
from src.database.notification_channels_operations import *

# Add channel
add_notification_channel(user_id, 'email', 'user@example.com')
add_notification_channel(user_id, 'sms', '919876543210')

# Get channels
channels = get_user_channels(user_id)
active = get_active_channels(user_id)
email_only = get_active_channels(user_id, 'email')

# Manage channels
toggle_channel(channel_id, True)    # Enable
delete_channel(channel_id)          # Delete
verify_channel(channel_id, code)    # Verify

# Preferences
prefs = get_notification_preferences(user_id)
update_notification_preferences(user_id, {'points_awarded': False})

# Stats & Maintenance
stats = get_channel_statistics()
cleanup_inactive_channels(30)
```

---

## 📧 Email Service (7 functions)

```python
from src.services.email_service import *

# Generic
send_email(recipient, subject, body, template_vars)

# Specific notifications
send_payment_due_email(email, name, days, expiry, amount)
send_membership_expired_email(email, name, expiry)
send_points_awarded_email(email, name, points, activity, total, rank)
send_achievement_email(email, name, achievement, desc, reward)
send_challenge_reminder_email(email, name, challenge, days, progress)
send_daily_reminder_email(email, name)

# Config
verify_email_configuration()
```

**Email Templates:**
- Payment Due
- Membership Expired
- Points Awarded
- Achievement Unlocked
- Challenge Reminder
- Daily Reminder

---

## 📱 SMS Service (8 functions)

```python
from src.services.sms_service import *

# Utilities
validate_phone_number(phone)        # Check format
format_phone_number(phone)          # Convert to +91...

# Generic
send_sms(phone, message)            # Auto provider selection
send_sms_twilio(phone, message)     # Force Twilio
send_sms_aws(phone, message)        # Force AWS SNS

# Specific notifications
send_payment_due_sms(phone, name, days, expiry)
send_membership_expired_sms(phone, name, expiry)
send_points_awarded_sms(phone, name, points, activity)
send_achievement_sms(phone, name, achievement, reward)
send_challenge_reminder_sms(phone, name, challenge, days, progress)
send_daily_reminder_sms(phone, name)

# Config
verify_sms_configuration()
```

**SMS Templates** (160 char limit):
- Payment Due
- Membership Expired
- Points Awarded
- Achievement Unlocked
- Challenge Reminder
- Daily Reminder

---

## 🔔 Notification Preferences (8 types)

Users can enable/disable notifications:

| Type | Emoji | Default |
|------|-------|---------|
| Points Awarded | ✨ | ON |
| Attendance Approved | ✅ | ON |
| Payment Due | 💳 | ON |
| Membership Expired | ❌ | ON |
| Achievement Unlocked | 🏆 | ON |
| Challenge Reminder | 🔔 | ON |
| Leaderboard Update | 📊 | ON |
| Daily Reminder | 📱 | OFF |

**Control:** `/notification_settings` → `🔔 Preferences`

---

## 🎯 User Flows

### Add Email
```
/notification_settings
  → 📧 Email Settings
    → ➕ Add Email
    → Send email address
    → Check inbox for verification
    → ✅ Verified
```

### Add SMS
```
/notification_settings
  → 📱 SMS Settings
    → ➕ Add SMS
    → Send phone (10 digits)
    → Check SMS for verification code
    → ✅ Verified
```

### Change Preferences
```
/notification_settings
  → 🔔 Preferences
    → Click notification type to toggle
    → ✅ Changes saved immediately
```

### Manage Channels
```
/notification_settings
  → 📧 Email Settings OR 📱 SMS Settings
    → Click channel
    → ✅ Toggle active/inactive
    → 🗑 Delete channel
```

---

## 🔧 Handler Functions (notification_preferences_handlers.py)

```python
# Commands
cmd_notification_settings()     # Main menu

# Callbacks
callback_email_settings()       # Show email list
callback_sms_settings()         # Show SMS list
callback_preferences_settings() # Show preference toggles

callback_email_add()            # Prompt for email
callback_sms_add()              # Prompt for phone

callback_toggle_preference()    # Toggle notif type
callback_toggle_channel()       # Toggle email/SMS
callback_delete_channel()       # Delete channel

callback_settings_back()        # Back to menu
callback_settings_close()       # Close dialog
```

---

## 🚀 Multi-Channel Notification Flow

### When Points Are Earned:

```
User logs activity
  ↓
Points awarded
  ↓
create_notification(user_id, 'points_awarded', ...)  [Telegram]
  ↓
Get user's email channels + check preference
  ↓
send_points_awarded_email(email, ...)                [Email]
  ↓
Get user's SMS channels + check preference
  ↓
send_points_awarded_sms(phone, ...)                  [SMS]
```

---

## 📊 Configuration Examples

### Gmail Setup
```python
# .env
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=fitness-club@gmail.com
SENDER_PASSWORD=app-password-16-chars
SENDER_NAME=Fitness Club Bot
```

### Twilio Setup
```python
# .env
SMS_PROVIDER=twilio
SMS_ACCOUNT_SID=AC1234567890abcdef
SMS_AUTH_TOKEN=abcdef1234567890
SMS_PHONE_NUMBER=+14155552671
```

### AWS SNS Setup
```python
# .env
SMS_PROVIDER=aws
AWS_ACCESS_KEY=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_REGION=ap-south-1  # For India
```

---

## 🧪 Testing

### Test Email
```python
from src.services.email_service import send_email

success = send_email(
    "test@example.com",
    "Test Email",
    "This is a test email from Fitness Club!"
)
print("Email sent!" if success else "Failed")
```

### Test SMS
```python
from src.services.sms_service import send_sms

success = send_sms("+919876543210", "Test SMS from Fitness Club!")
print("SMS sent!" if success else "Failed")
```

### Test Channel Management
```python
from src.database.notification_channels_operations import *

# Add
add_notification_channel(user_id, 'email', 'user@example.com')

# Get
channels = get_user_channels(user_id)
print(channels)

# Toggle
toggle_channel(channel_id, False)

# Verify config
from src.services.email_service import verify_email_configuration
verify_email_configuration()
```

---

## 🔍 Database Queries

```sql
-- All channels for user
SELECT * FROM notification_channels WHERE user_id = 123;

-- Active email channels
SELECT * FROM notification_channels 
WHERE user_id = 123 AND channel_type = 'email' AND is_active = TRUE;

-- Verified SMS channels
SELECT * FROM notification_channels 
WHERE user_id = 123 AND channel_type = 'sms' AND verified = TRUE;

-- Channel statistics
SELECT channel_type, COUNT(*), 
  COUNT(CASE WHEN is_active THEN 1 END) as active
FROM notification_channels
GROUP BY channel_type;
```

---

## ⚙️ Validation Rules

### Email
- Valid email format (user@domain.com)
- Max length: 255 characters
- Case-insensitive

### Phone Number (SMS)
- Indian format: 10 digits starting with 6-9
- Accepts: 9876543210, +919876543210, 91-9876543210
- Converts to: +919876543210

### SMS Message
- Max 160 characters (SMS standard)
- Longer messages auto-truncated
- Sent as single message

---

## 📈 Usage Statistics

### Database Operations:
```python
stats = get_channel_statistics()
# Returns:
# {
#     'email': {'total': 150, 'active': 120, 'verified': 115},
#     'sms': {'total': 80, 'active': 65, 'verified': 60},
#     'telegram': {'total': 200, 'active': 200, 'verified': 200}
# }
```

---

## 🔐 Security Features

✅ Phone numbers masked in UI (show last 4 digits only)
✅ Passwords never stored (use app passwords)
✅ HTTPS/TLS for all communications
✅ Rate limiting (max 10 emails, 5 SMS per hour)
✅ Users can delete channels anytime
✅ Preferences fully user-controlled
✅ Verification before activation

---

## 🐛 Error Handling

### Email Errors
- SMTP auth fail → Return False, log error
- Network error → Log, user retried manually
- Invalid format → Return False immediately

### SMS Errors
- Invalid phone → Return False, show error
- Provider API error → Log, retry queue
- Rate limit → Queue for later

### Channel Errors
- Duplicate → Return False
- Not found → Fail silently
- Permission → Log error

---

## 📊 Metrics to Monitor

Track in logs:
- Email delivery rate (target: 99%)
- SMS delivery rate (target: 98%)
- Channel verification rate
- Active channel growth
- Preference changes
- Error rates by type

---

## 🚀 Next: Phase 4.2

**Phase 4.2 - Payment Gateway Integration:**
- Stripe integration
- Razorpay integration
- Auto-payment handling
- Invoice generation
- Webhook processing

---

## 📞 Support

### Check Logs
```bash
tail -f logs/fitness_bot.log | grep -i "email\|sms"
```

### Verify Config
```python
from src.services.email_service import verify_email_configuration
from src.services.sms_service import verify_sms_configuration

email_ok = verify_email_configuration()
sms_ok = verify_sms_configuration()

print(f"Email: {'✅' if email_ok else '❌'}")
print(f"SMS: {'✅' if sms_ok else '❌'}")
```

---

**Phase 4.1 Complete!** Ready for deployment 🚀
