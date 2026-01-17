# Payment Request System Documentation

## Overview
Complete payment request and approval workflow where users submit payment proof and admins approve with amount and subscription duration.

## User Flow

### 1. Submit Payment Request
Users click "💳 Request Payment Approval" button in user menu or use `/request_payment` command.

**Steps:**
1. **Enter Amount**: User enters the payment amount (₹)
2. **Upload Proof**: User uploads payment screenshot/photo (optional - can skip)
3. **Add Notes**: User can add transaction ID or notes (optional - can skip)
4. **Submit**: Request is created with status "pending"

**Features:**
- Duplicate check: Can't submit if already has pending request
- Shows current subscription status before submission
- Automatically notifies all admins when submitted

### 2. Track Request Status
- Request ID generated for tracking
- User gets notification when admin reviews (approved/rejected)
- User can check subscription status anytime via payment status

## Admin Flow

### 1. View Pending Requests
Admins click "💳 Pending Payment Requests" button in admin menu or use `/pending_requests` command.

**Display:**
- List of all pending payment requests
- User details (name, username, user ID)
- Amount requested
- Request date and time
- Notes (if provided)
- Review button for each request

### 2. Review Individual Request
Admin clicks "✅ Review #RequestID" button.

**Display:**
- Complete request details
- Payment proof image (if uploaded)
- User information
- Approve/Reject buttons

### 3. Approve Payment
Admin clicks "✅ Approve" button.

**Steps:**
1. **Enter Amount**: Admin enters approved amount (suggests user's amount if provided)
2. **Select Duration**: Admin selects subscription duration:
   - 30 days (1 month)
   - 60 days (2 months)
   - 90 days (3 months)
   - 180 days (6 months)
   - 365 days (1 year)

**What Happens:**
1. Payment request status → "approved"
2. Record created in `fee_payments` table
3. User's subscription activated:
   - `fee_status` → "paid"
   - `fee_paid_date` → today's date
   - `fee_expiry_date` → calculated based on duration
4. User receives notification with approval details
5. Admin sees confirmation message

### 4. Reject Payment
Admin clicks "❌ Reject" button.

**What Happens:**
1. Payment request status → "rejected"
2. User receives rejection notification
3. User can submit new request

## Database Schema

### `payment_requests` Table
```sql
- request_id (PRIMARY KEY)
- user_id (FK to users)
- amount (DECIMAL)
- payment_proof_url (VARCHAR) - Telegram file_id of payment screenshot
- notes (TEXT) - User's notes/transaction ID
- status (VARCHAR) - 'pending', 'approved', 'rejected'
- requested_at (TIMESTAMP)
- reviewed_by (INT FK to users) - Admin who reviewed
- reviewed_at (TIMESTAMP)
- rejection_reason (TEXT)
```

### `fee_payments` Table
```sql
- payment_id (PRIMARY KEY)
- user_id (FK to users)
- amount (DECIMAL)
- payment_method (VARCHAR) - 'manual' for request-approved payments
- status (VARCHAR) - 'completed'
- duration_days (INT) - Subscription duration
- notes (TEXT) - Auto-generated approval note
- approved_by (INT FK to users) - Admin who approved
- approved_at (TIMESTAMP)
- created_at (TIMESTAMP)
```

### `users` Table (Payment Columns)
```sql
- fee_status (VARCHAR) - 'paid', 'unpaid', 'expired'
- fee_paid_date (DATE) - Last payment date
- fee_expiry_date (DATE) - Subscription expiry date
```

## Key Features

### For Users:
✅ Simple 3-step submission process
✅ Can skip payment proof if not available
✅ Can add notes for admin
✅ Duplicate request prevention
✅ Automatic notifications on approval/rejection
✅ Shows current subscription status

### For Admins:
✅ View all pending requests in one place
✅ See payment proof images
✅ Flexible approval with custom amount and duration
✅ Automatic subscription activation
✅ User notification on approval
✅ Reject with reason capability
✅ Quick review interface

## Technical Implementation

### Conversation Handlers
1. **payment_request_conversation**:
   - Entry: `/request_payment` command or button click
   - States: REQUEST_AMOUNT → REQUEST_PROOF → REQUEST_NOTES
   - Fallback: `/cancel` command

2. **approval_conversation**:
   - Entry: "Approve" button callback
   - States: APPROVE_AMOUNT → APPROVE_DURATION
   - No fallback (completes on duration selection)

### Button Routing
- User menu: `cmd_request_payment` → opens request submission
- Admin menu: `cmd_pending_requests` → lists pending requests
- Review button: `review_request_{id}` → shows request details
- Approve button: `approve_req_{id}` → starts approval flow
- Reject button: `reject_req_{id}` → rejects request
- Duration buttons: `duration_30`, `duration_60`, etc. → finalizes approval

### Database Operations
File: `src/database/payment_request_operations.py`

Functions:
- `create_payment_request()` - Submit new request
- `get_pending_payment_requests()` - List all pending
- `get_payment_request_by_id()` - Get specific request
- `approve_payment_request()` - Approve and activate subscription
- `reject_payment_request()` - Reject request
- `has_pending_payment_request()` - Check for duplicates
- `get_user_payment_requests()` - User's request history

## Usage Examples

### User Submits Payment Request
```
User: Clicks "💳 Request Payment Approval"
Bot: "Please enter the amount you paid (in ₹):"
User: 1500
Bot: "📸 Please send payment proof or /skip"
User: [Sends screenshot]
Bot: "✅ Payment proof received! Add notes or /skip"
User: "UPI Ref: 123456789"
Bot: "✅ Payment Request Submitted! Request ID: #42"
     [Notifies all admins]
```

### Admin Approves Request
```
Admin: Clicks "💳 Pending Payment Requests"
Bot: Shows list with "✅ Review #42" button
Admin: Clicks "✅ Review #42"
Bot: Shows full details with payment proof
Admin: Clicks "✅ Approve"
Bot: "Please enter the approved amount (in ₹):"
Admin: 1500
Bot: "⏰ Select subscription duration:" [Shows duration buttons]
Admin: Clicks "90 days (3 months)"
Bot: "✅ Payment Request Approved!"
     [User gets notification: "Your subscription is active until DD MMM YYYY"]
```

### Admin Rejects Request
```
Admin: Clicks "❌ Reject" on request #42
Bot: "❌ Payment Request Rejected"
     [User gets notification: "Your payment request #42 was not approved"]
```

## Status Workflow

```
User Submits → status: 'pending'
              ↓
        Admin Reviews
       /            \
   Approve         Reject
      ↓               ↓
status: 'approved'  status: 'rejected'
      ↓
Subscription Activated:
- fee_status = 'paid'
- fee_paid_date = today
- fee_expiry_date = today + duration
- Record in fee_payments
```

## Notifications

### User Notifications:
1. **On Submission**: "✅ Payment Request Submitted! Status: ⏳ Pending Admin Approval"
2. **On Approval**: "✅ Payment Approved! Your subscription is now active! Valid Until: DD MMM YYYY"
3. **On Rejection**: "❌ Payment Request Rejected. Please contact admin for more information."

### Admin Notifications:
1. **New Request**: "🔔 New Payment Request #ID from User (Amount: ₹X) - Click to review"

## Commands

### User Commands:
- `/request_payment` - Submit payment approval request

### Admin Commands:
- `/pending_requests` - View all pending payment requests

### Callback Data Patterns:
- `cmd_request_payment` - Open request submission
- `cmd_pending_requests` - List pending requests
- `review_request_{id}` - Review specific request
- `approve_req_{id}` - Start approval process
- `reject_req_{id}` - Reject request
- `duration_{days}` - Finalize approval with duration

## Migration Status

✅ Database migration completed:
- `payment_requests` table created
- `fee_payments` table created
- `users` table updated with fee columns
- All indexes created

✅ Handler code completed:
- User submission flow
- Admin approval flow
- Button routing
- Notifications

✅ Integration completed:
- Handlers registered in `bot.py`
- Buttons added to menus
- Commands added to bot menu
- Callback routing configured

## Testing Checklist

### User Flow:
- [ ] Click "Request Payment Approval" button
- [ ] Enter valid amount
- [ ] Upload payment proof image
- [ ] Add notes with transaction ID
- [ ] Verify request submitted successfully
- [ ] Check duplicate request prevention

### Admin Flow:
- [ ] Click "Pending Payment Requests" button
- [ ] Verify list shows all pending requests
- [ ] Click "Review #X" button
- [ ] Verify payment proof displays correctly
- [ ] Click "Approve" button
- [ ] Enter amount
- [ ] Select duration
- [ ] Verify approval confirmation
- [ ] Check user received notification

### Database:
- [ ] Verify payment_requests record created
- [ ] Verify fee_payments record created on approval
- [ ] Verify users.fee_status updated
- [ ] Verify users.fee_expiry_date calculated correctly

## File Structure

```
src/
├── database/
│   ├── payment_request_operations.py    [NEW] Database operations
│   └── payment_operations.py            [EXISTING] Fee status operations
├── handlers/
│   ├── payment_request_handlers.py      [NEW] Request/approval handlers
│   ├── payment_handlers.py              [EXISTING] Direct payment flow
│   ├── callback_handlers.py             [MODIFIED] Added routing
│   └── role_keyboard_handlers.py        [MODIFIED] Added buttons
└── bot.py                                [MODIFIED] Registered handlers

migrate_payment_system.py                 [NEW] Database migration
PAYMENT_REQUEST_SYSTEM.md                 [NEW] This documentation
```

## Success Criteria

✅ **User Experience**:
- Simple 3-step submission
- Can skip optional fields
- Clear status updates
- Instant notifications

✅ **Admin Experience**:
- Easy to review requests
- See payment proof inline
- Flexible approval options
- Automatic subscription activation

✅ **Data Integrity**:
- No duplicate pending requests
- Accurate subscription dates
- Complete audit trail
- Proper status tracking

## Next Steps

1. **Test complete workflow** with real data
2. **Add request history** view for users
3. **Add bulk approval** capability for admins
4. **Add payment reminders** before expiry
5. **Add payment reports** in admin dashboard
