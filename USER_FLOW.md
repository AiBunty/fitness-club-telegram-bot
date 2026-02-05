# User Flow - Fitness Club Bot

## Overview
Users interact with the Fitness Club bot through Telegram to manage memberships, track activities, and receive notifications.

---

## 1. Role Detection System - /start

### First Interaction Detection
When any user sends `/start`, the bot performs role detection:

```
User sends /start
  ↓
Bot retrieves user_id from Telegram
  ↓
Check admin_members table
  ├→ User found & active → ADMIN ROLE
  │   └→ Load Admin Dashboard
  ├→ User found but inactive → STAFF ROLE
  │   └→ Load Limited Admin Dashboard (view-only)
  └→ User NOT found → Check users table
      ├→ User found → USER ROLE
      │   └→ Load User Dashboard
      └→ User NOT found → NEW USER
          └→ Show Registration Form
```

### Role Definitions

**ADMIN**
- User ID exists in `admin_members` table with `is_active=true`
- Full access to all bot features
- Can manage users, invoices, payments, subscriptions, store, and system settings
- Can add/remove other admins or staff
- Can view analytics and reports

**STAFF**
- User ID exists in `admin_members` table with `is_active=false`
- Limited access based on assigned role
- Can view user data and help with support
- Cannot create invoices or modify system settings
- Can send messages and provide support

**USER**
- User ID exists in `users` table
- Regular member access only
- Can manage own subscription, track activities, make payments
- Cannot access admin features

**NEW USER**
- User ID NOT in any system table
- First-time user joining the platform
- Must complete registration before accessing features

---

## 2. User Onboarding - /start (After Role Detection)

### Entry Point
User sends `/start` command to the bot

### Flow
1. **Role Check** (Described above)
   - Bot determines if ADMIN, STAFF, USER, or NEW USER
   - Routes to appropriate dashboard

2. **Username Resolution** (New Users Only)
   - If user has a username (@username), bot extracts it from Telegram profile
   - Searches database for matching username in `users.telegram_username`
   - If found: links existing account and updates `telegram_id`
   - This enables invoice sending even if user was previously added without Telegram ID
   - Example: User "John" was added via admin with user_id=2147483647 (placeholder)
     - User starts bot with Telegram username @johnfitness
     - Bot finds matching record and updates telegram_id to actual value

3. **User Registration** (New Users Only)
   - Display registration form with ConversationHandler
   - Collect: Name, Phone, Email, Optional: Telegram Username
   - Validate phone format and email
   - Store in `users` table with `telegram_id`, `telegram_username`, registration date

4. **Dashboard Display**
   - Show quick stats: Active subscription, Credits, Pending payments
   - Display menu buttons: Subscription, Habits, Weight, Water, Meal, Payments, Store, Help

---

## 2. Subscription Management

### View Subscription `/subscription`
- Current tier (Free/Basic/Premium/Elite)
- Renewal date
- Features unlocked
- Payment status

### Upgrade/Downgrade
1. User selects desired tier
2. Bot calculates charges/credits
3. Displays pricing and payment terms
4. Redirects to payment flow
5. Updates subscription in database on success

---

## 3. Activity Tracking

### Habits Tracking `/habits`
- Daily checkin for fitness goals
- Tracks: Workouts, Running, Cycling, Stretching, etc.
- Data stored in `user_habits` table
- Reminders sent at 8:00 PM daily

### Weight Tracking `/weight`
- User inputs current weight
- Records historical data
- Shows progress graph (if available)

### Water Intake `/water`
- Log water consumption
- Daily goal tracking
- Reminders for hydration

### Meal Logging `/meal`
- Log meals consumed
- Basic food database for quick selection
- Calorie tracking (if integrated)

---

## 4. Payment System - Complete Flow

### 4.1 Invoice Creation (Admin Initiates)

**Step 1: Admin Access Invoice Menu**
```
Admin sends /invoices
  ↓
Bot verifies admin role (checks admin_members table)
  ↓
Display invoice options:
  • Create Invoice
  • View Pending Invoices
  • View Payment History
  • Payment Reports
```

**Step 2: Admin Selects User**
```
Admin clicks "Create Invoice"
  ↓
Bot displays user search interface
  ├→ Search by name (fuzzy match)
  ├→ Search by phone
  ├→ Search by Telegram ID
  └→ Show recent users
  ↓
Admin selects user from list
  ↓
Bot displays selected user details:
  • Name, Phone, Email
  • Current subscription tier
  • Outstanding balance
  • Invoice history (last 3)
```

**Step 3: Admin Adds Invoice Items**
```
Admin clicks "Add Items"
  ↓
For each item:
  ├→ Browse Store Catalog
  │  └→ Select item → Quantity
  ├→ OR Add Custom Item
  │  └→ Enter: Name, Amount, Quantity
  └→ Apply Discount (optional)
     └→ Enter discount %
  ↓
Bot calculates:
  • Item subtotal
  • GST (as per product rate or default 18%)
  • Total after discount
```

**Step 4: Admin Sets Invoice Terms**
```
Admin enters:
  • Due Date (calendar picker)
  • Payment Terms:
    ├→ Immediate Payment
    ├→ 7 Days
    ├→ 30 Days
    └→ Custom Days
  • Notes/Memo (optional)
  • Invoice Number (auto-generated or custom)
  ↓
Bot generates invoice JSON:
  {
    "invoice_id": "0643D684",
    "user_id": "<actual_telegram_id>",
    "user_name": "Sayali (@sayaliwani09)",
    "telegram_id": "<resolved_id>",
    "items": [...],
    "subtotal": 1000,
    "gst": 180,
    "total": 1180,
    "due_date": "2026-02-10",
    "status": "created",
    "created_at": "2026-02-01T10:00:00"
  }
```

**Step 5: Validation & Preview**
```
Before sending, bot validates:
  ├→ telegram_id is NOT placeholder (< 2147483647)
  │  └→ If invalid: Show error & suggest /start
  ├→ User exists in database
  ├→ Invoice total > 0
  └→ Due date is in future
  ↓
Admin reviews invoice:
  • Preview PDF format
  • Verify all details
  • Click "Send to User" or "Cancel"
```

**Step 6: Send to User**
```
Bot sends Telegram message to user with:
  ├→ Invoice details (formatted PDF preview)
  ├→ Amount: ₹<total>
  ├→ Due date
  ├→ Items breakdown
  ├→ Two buttons:
  │  ├→ 💳 Pay Bill
  │  └→ ❌ Reject Bill
  └→ Invoice marked as "sent" in database
  ↓
Admin sees confirmation:
  • ✅ Invoice sent to <user_name>
  • Message preview
  • Timestamp
```

---

### 4.2 User Receives Invoice

**Step 1: Notification**
```
User receives message:
  "Invoice #0643D684 from Fitness Club
   Amount: ₹1,180
   Due: 10 Feb 2026
   
   Items:
   • Herbalife Formula 1: 1 x ₹500
   • Personal Training: 1 x ₹500
   
   Subtotal: ₹1,000
   GST (18%): ₹180
   Total: ₹1,180
   
   [💳 Pay Bill] [❌ Reject Bill]"
```

**Step 2: User Reviews Invoice**
```
User can:
  ├→ View invoice details
  ├→ Ask questions via message
  └→ Choose action:
     ├→ Pay immediately
     └→ Reject with reason
```

---

### 4.3 Payment Processing Flow

**Option A: User Clicks 💳 Pay Bill**
```
User clicks "Pay Bill" button
  ↓
Bot starts payment conversation:
  • Verify invoice details
  • Check if payment gateway configured
  ↓
Redirect to payment gateway:
  • Stripe → Stripe payment link
  • Razorpay → Razorpay checkout
  • Manual → Ask for bank details or UPI
  ↓
Payment Gateway Processing:
  ├→ User enters card/UPI details
  ├→ Payment processed
  └→ Returns success/failure response
  ↓
Bot receives payment notification:
  ├→ Success (HTTP 200):
  │  ├→ Mark invoice as "paid"
  │  ├→ Update user payment history
  │  ├→ Send receipt to user
  │  ├→ Notify admin of payment
  │  └→ Update wallet/credits if applicable
  │
  └→ Failure:
     ├→ Notify user of failure
     ├→ Show error reason
     ├→ Option to retry
     └→ Invoice remains "pending"
```

**Option B: User Clicks ❌ Reject Bill**
```
User clicks "Reject Bill" button
  ↓
Bot shows rejection form:
  "Why are you rejecting this invoice?
   
   • Incorrect amount
   • Items not received
   • Quality issues
   • Other reason
   
   [Submit] [Cancel]"
  ↓
User selects reason & submits
  ↓
Bot updates invoice:
  • Status: "rejected"
  • Rejection reason stored
  • Rejection timestamp
  ↓
Admin notified:
  "Invoice #0643D684 rejected by user
   Reason: <reason>
   
   [View Invoice] [Contact User] [Delete]"
  ↓
Invoice removed from user's payment queue
```

---

### 4.4 Payment Reminders (Automated)

**Scheduled Reminders**
```
Daily at 11:00 AM:
  ↓
Check all pending invoices (status != "paid" & status != "rejected")
  ↓
For each pending invoice:
  ├→ Check due date
  ├→ If today or overdue:
  │  └→ Send reminder to user
  ├→ Message:
  │  "💬 Reminder: Invoice #0643D684
  │   Amount: ₹1,180
  │   Due: TODAY (or <N> days overdue)
  │   
  │   [💳 Pay Now] [View Invoice]"
  │
  └→ Log reminder sent
```

**Manual Reminder (Admin)**
```
Admin selects invoice → "Send Reminder"
  ↓
Customize message (optional)
  ↓
Bot sends to user immediately
  ↓
Admin sees: ✅ Reminder sent
```

---

### 4.5 Payment History & Receipts

**User Views Payment History**
```
User clicks "Payments" in main menu
  ↓
Bots shows:
  • Pending Invoices (with 💳 Pay buttons)
  • Paid Invoices (with receipt links)
  • Rejected Invoices (read-only)
  ↓
User can:
  ├→ Click invoice to view details
  ├→ Download receipt PDF (for paid invoices)
  ├→ View payment date & method
  └→ See transaction ID
```

**Receipt Generation**
```
When invoice marked as paid:
  ↓
Bot generates receipt:
  ├→ Receipt #: Auto-generated
  ├→ Original invoice ID
  ├→ Amount paid
  ├→ Payment date & time
  ├→ Payment method
  ├→ Transaction ID (from gateway)
  └→ Company stamp/signature (if configured)
  ↓
Receipt sent to user as:
  • PDF attachment
  • Also saved in invoice record
```

---

### 4.6 Error Handling - Invalid Telegram ID

**Scenario: Admin tries to send invoice to user with placeholder telegram_id**
```
Admin attempts to send invoice
  ↓
Bot validates telegram_id:
  
  if telegram_id >= 2147483647:
    ├→ VALIDATION FAILS
    ├→ Status: Cannot send
    └→ Error message to admin:
        "❌ Cannot send invoice
         
         Issue: Invalid telegram_id (placeholder detected)
         
         💡 Solution:
         1. Ask user to send /start to the bot
         2. This will update their telegram_id
         3. Click 🔁 Resend button to send invoice
         
         [Resend Later] [Delete Invoice]"
  ↓
Admin communicates with user to send /start
  ↓
User sends /start
  ↓
/start handler resolves username and updates telegram_id
  ↓
Admin clicks "Resend" button
  ↓
Bot validates telegram_id again (now valid)
  ↓
Invoice sends successfully! ✅
```

---

### Payment Flow Summary Diagram

```
ADMIN SIDE                          USER SIDE

Create Invoice                      User receives
  ├→ Select user                    notification
  ├→ Add items                           ↓
  ├→ Set terms                      Reviews
  ├→ Validate                           ↓
  └→ Preview & Send                 Chooses:
       ↓                            ├→ Pay Bill
  ✅ Sent to user                   │   ├→ Payment gateway
       ↓                            │   ├→ Process payment
  Track Status                      │   └→ Receipt sent
  ├→ Pending                        │
  ├→ Viewed                         └→ Reject Bill
  ├→ Paid ← Receipt                     ├→ Provide reason
  ├→ Overdue → Send Reminder           └→ Removed from queue
  └→ Rejected                            ↓
                                    Payment history updated
```

---

## 5. Store/Products

### Browse Store `/store`
1. **Browse Items**
   - Search by name or serial number
   - Filter by category
   - View price and availability

2. **Purchase Flow**
   - Select item
   - Confirm quantity
   - Generate invoice
   - Complete payment (see Payment System)

---

## 6. Challenges & Checkins

### Join Challenge
- View available challenges
- Join active challenges
- See deadline and requirements

### Check In
1. User uploads proof (photo/video)
2. Submits check-in for the challenge
3. Admin reviews and approves
4. Marks completion on user record

---

## 7. Reminders & Notifications

### Scheduled Reminders
- **Evening Habits Reminder** - 8:00 PM daily
- **Subscription Expiry Reminder** - 9:00 AM daily
- **Payment Reminders** - 11:00 AM daily (for overdue invoices)
- **Follow-up Reminders** - Every 3 days at 11:00 AM

### Notification Types
- **Payment Requests** - Direct message with invoice
- **Subscription Updates** - Renewal confirmations
- **Habit Tracking** - Daily reminders and achievements
- **Challenge Updates** - New challenges, approvals
- **System Updates** - Maintenance alerts, feature announcements

---

## 8. Help & Support `/help`

### Available Options
- FAQ about subscriptions
- Payment troubleshooting
- Activity tracking guide
- Contact admin button
- Report issues

---

## 9. User Data Management

### Data Stored
- User Profile: Name, Phone, Email, Telegram ID, Username
- Subscription: Current tier, renewal date, status
- Activities: Habits, Weight, Water, Meals (historical)
- Payments: All invoices, payment status, dates
- Challenges: Joined challenges, completion status

### Privacy
- Users can request data export
- Users can delete account (removes sensitive data)
- Admins cannot view personal messages unless escalated

---

## 10. Callback Button Handling

All inline buttons in user messages route through callback handlers:
- **Button Click** → ConversationHandler intercepts callback
- **Validation** → Handler checks user permissions
- **Action** → Executes user request (payment, update, etc.)
- **Response** → Edit message or send confirmation

### Error Handling
- Invalid telegram_id (placeholder ≥ 2147483647): User is prompted to send `/start`
- Expired sessions: User redirected to menu
- Database errors: Graceful error message with retry option

---

## User Experience Flow Diagram

```
START
  ↓
New User? 
  ├→ Yes: Registration → Username Match?
  │         ├→ Yes: Link Account & Update telegram_id
  │         └→ No: Create New Account
  ├→ No: Load Dashboard
  ↓
DASHBOARD MENU
  ├→ Subscription (View/Upgrade)
  ├→ Habits (Daily Checkin)
  ├→ Weight (Log/View)
  ├→ Water (Log/Track)
  ├→ Meal (Log)
  ├→ Payments (View Invoices/Pay)
  ├→ Store (Browse/Purchase)
  ├→ Challenges (Join/Checkin)
  └→ Help (Support)
  ↓
PAYMENT FLOW (When needed)
  ├→ Receive Invoice
  ├→ Click 💳 Pay Bill
  ├→ Process Payment
  └→ Confirmation & Receipt
```

---

## Current Issues & Resolutions

### Issue: "Chat not found" on invoice send
**Cause:** telegram_id is invalid (placeholder ≥ 2147483647)  
**Resolution:** User must send `/start` to update telegram_id in database  
**Status:** Validation added - prevents sending to invalid IDs, prompts user

### Issue: Intermittent button failures
**Cause:** Handler registration race condition (catch-all consuming callbacks)  
**Resolution:** Removed `handle_analytics_callback` catch-all, registered in strict priority order  
**Status:** Fixed - all callback buttons now consistent

---

## Deployment Status
- ✅ Database: MySQL remote connection stable with VPS static IP
- ✅ Bot: Polling mode with allowed_updates=['message', 'callback_query']
- ✅ Handlers: All ConversationHandlers registered in priority order
- ✅ Invoices v2: JSON-based storage with telegram_id validation
- ✅ Reminders: APScheduler configured for all scheduled jobs
