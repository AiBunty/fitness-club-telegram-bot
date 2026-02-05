# Admin Flow - Fitness Club Bot

## Overview
Admins manage users, invoices, payments, subscriptions, and system operations through the Telegram bot with advanced dashboards and controls.

---

## 1. Role Detection System - /start

### First Interaction - Role Detection
When any user sends `/start`, the bot performs role detection based on database lookup:

```
User sends /start
  ↓
Bot retrieves:
  • Telegram user_id
  • Telegram username
  • Chat ID
  ↓
QUERY: admin_members table
  SELECT * FROM admin_members WHERE user_id = <telegram_id>
  ↓
  ├→ Found & is_active = true
  │  └→ ROLE: ADMIN
  │      ├→ Load full admin dashboard
  │      ├→ Full access to all features
  │      └→ Can manage system
  │
  ├→ Found & is_active = false
  │  └→ ROLE: STAFF
  │      ├→ Load limited dashboard
  │      ├→ Restricted permissions
  │      └→ View-only or support mode
  │
  └→ NOT found
     └→ QUERY: users table
        SELECT * FROM users WHERE telegram_id = <telegram_id>
        ↓
        ├→ Found
        │  └→ ROLE: USER
        │      ├→ Load user dashboard
        │      └→ Regular member access
        │
        └→ NOT found
           └→ ROLE: NEW USER
               ├→ Load registration form
               └→ Collect profile info
```

### Role Hierarchy & Permissions

**ADMIN (Super User)**
- Database flag: `admin_members.is_active = true`
- Permissions:
  - ✅ View all users
  - ✅ Create/edit/delete invoices
  - ✅ Process payments
  - ✅ Manage subscriptions
  - ✅ Manage products/store
  - ✅ Send broadcasts
  - ✅ View analytics
  - ✅ Add/remove staff
  - ✅ System settings
  - ✅ Access audit logs

**STAFF (Limited Admin)**
- Database flag: `admin_members.is_active = false`
- Assigned role: `admin_members.role` (e.g., "support", "store_manager")
- Permissions (by role):
  - Support Staff:
    - ✅ View user profiles
    - ✅ Send messages to users
    - ✅ View payment history
    - ❌ Create invoices
    - ❌ Process payments
  - Store Manager:
    - ✅ Manage products
    - ✅ View sales
    - ✅ Stock management
    - ❌ Create invoices
    - ❌ Manage users

**USER (Regular Member)**
- Database flag: `users.user_id` exists
- Permissions:
  - ✅ View own profile
  - ✅ View own invoices
  - ✅ Pay invoices
  - ✅ Track activities
  - ✅ Manage subscription
  - ❌ View other users
  - ❌ Create invoices
  - ❌ Access admin features

**NEW USER (Unregistered)**
- Not in database yet
- Permissions:
  - ✅ Complete registration
  - ✅ Provide personal info
  - ❌ Access any features until registered

---

## 2. Admin Onboarding - /start (After Role Detection)

### Entry Point
Admin sends `/start` command to the bot

### Flow
1. **Role Verification** (Described above)
   - Bot checks `admin_members` table
   - If found & is_active=true: Admin
   - If found & is_active=false: Staff
   - Routes to appropriate dashboard

2. **Admin Dashboard Display**
   - Quick stats: Active users, Pending payments, Revenue, Overdue invoices
   - Admin menu with role-based actions
   - Quick access buttons: Create Invoice, View Payments, User Management
   - Notifications: Payment alerts, Support tickets, System messages
   - Navigation to specific admin modules

---

## 2. User Management

### Admin Dashboard - Manage Users `/admin`
1. **View All Users**
   - List all active users with status
   - Search by name, phone, or Telegram ID
   - Filter by subscription tier or status

2. **User Details**
   - Profile: Name, Phone, Email, Telegram ID, Username
   - Subscription: Current tier, renewal date, status
   - Activity: Last login, habits tracked, payments
   - History: All invoices, payment records

3. **User Actions**
   - **Edit Profile** - Update name, phone, email
   - **Change Subscription** - Upgrade/downgrade tier (manual)
   - **Reset Password** - Force re-registration
   - **Deactivate/Activate** - Suspend or reactivate user account
   - **Send Custom Message** - Direct message to user
   - **Export Data** - Download user data (name, activity, payments)

### User Approval Status
- **Pending** - Waiting for first payment
- **Active** - Subscription valid and paid
- **Suspended** - Payment overdue or deactivated by admin
- **Inactive** - No activity for 30+ days

---

## 3. Invoice Management - /invoices

### Create Invoice Workflow
1. **Select User**
   - Search by name or Telegram ID
   - Confirmation with user details

2. **Add Items**
   - Browse store items or add custom items
   - Set quantity and discount
   - Calculate total with GST

3. **Set Invoice Details**
   - Invoice number (auto-generated)
   - Due date
   - Payment terms (immediate/installment)
   - Notes/memo

4. **Review & Send**
   - Preview invoice formatting
   - Confirm recipient
   - Send to user via Telegram
   - Invoice sent with buttons: 💳 Pay Bill, ❌ Reject Bill

### Invoice Status Tracking
- **Created** - Invoice generated, pending delivery
- **Sent** - Delivered to user's Telegram
- **Viewed** - User viewed invoice
- **Paid** - Payment received
- **Rejected** - User rejected with notes
- **Overdue** - Payment due date passed

### Invoice Management Dashboard
1. **Filter & Search**
   - By user name
   - By status (Pending, Paid, Rejected, Overdue)
   - By date range
   - By invoice ID

2. **Invoice Actions**
   - **View Details** - Full invoice with payment history
   - **Resend to User** - Send again if telegram_id valid
   - **Mark as Paid** - Manual payment marking
   - **Reject Invoice** - Remove from user's queue
   - **Download PDF** - Get invoice copy for records

### Invoice Failure Handling
**Invalid Telegram ID Detection:**
- If telegram_id ≥ 2147483647 (placeholder): Cannot send
- Admin sees error: "Invalid telegram_id (placeholder detected)"
- Suggested action: "💡 Ask user to send /start to the bot, then use 🔁 Resend button"
- Solution: User sends `/start` → telegram_id updates → admin resends successfully

---

## 4. Payment Management

### Payment Dashboard
1. **View Pending Payments**
   - All unpaid invoices with due dates
   - Overdue alerts highlighted
   - Total amount pending

2. **Process Payment**
   - User initiates payment → Notification to admin
   - Mark as verified/completed
   - Send receipt to user

3. **Manual Payment Entry**
   - Record offline payments (cash, check, bank transfer)
   - Link payment to specific invoice
   - Send digital receipt to user

4. **Payment Reminders**
   - Automatic reminders sent to users at 11:00 AM daily
   - Manual reminder option for specific users
   - Customizable message

### Payment Reports
- Daily revenue summary
- User payment history
- Outstanding receivables
- Payment method breakdown (if tracked)

---

## 5. Subscription Management

### Subscription Dashboard
1. **View All Subscriptions**
   - List users by tier: Free, Basic, Premium, Elite
   - Renewal dates and auto-renewal status
   - Usage metrics per tier

2. **Manage Individual Subscription**
   - **View Details** - Current tier, renewal date, features
   - **Change Tier** - Manual upgrade/downgrade (credits applied)
   - **Extend Period** - Add months to subscription
   - **Renew Now** - Force immediate renewal
   - **Suspend** - Pause active subscription
   - **Cancel** - End subscription and notify user

3. **Subscription Settings** (System-wide)
   - Tier pricing
   - Features per tier
   - Renewal terms
   - Grace period length
   - Auto-renewal behavior

### Renewal Management
- Scheduled renewal reminders sent to users at 9:00 AM daily
- Automatic renewal on due date (if enabled)
- Failed renewal notifications

---

## 6. Store & Product Management

### Store Admin Panel
1. **View All Products**
   - List with serial number, name, price, quantity
   - Filter by category
   - Stock level indicators

2. **Add Product**
   - Name, Description
   - Serial number (unique identifier)
   - Price and GST rate
   - Category
   - Stock quantity
   - Upload image (optional)

3. **Edit Product**
   - Update price, stock, description
   - Deactivate/reactivate product
   - Archive old products

4. **Store Reporting**
   - Sales by product
   - Revenue breakdown
   - Stock alert for low inventory
   - Top selling items

### GST Management
- Set GST rate per product (5%, 12%, 18%, 28%)
- Calculate automatically in invoices
- GST reports for tax filing

---

## 7. Broadcast & Communication

### Send Broadcast Message
1. **Select Recipients**
   - All users
   - By subscription tier
   - By status (active/inactive)
   - Custom list

2. **Compose Message**
   - Text, links, buttons
   - Preview before sending
   - Schedule for specific time

3. **Message Tracking**
   - Delivery status (sent/failed)
   - Read receipts (if enabled)
   - Response tracking

### System Announcements
- Maintenance alerts
- New feature announcements
- Policy updates
- Emergency notifications

---

## 8. User Challenges & Approvals

### Challenge Management
1. **Create Challenge**
   - Name, description, duration
   - Requirements (proof needed)
   - Reward/incentive
   - Start date and deadline

2. **View Checkins**
   - Users awaiting approval
   - Review submitted proofs (photos/videos)
   - Approve or reject with feedback

3. **Track Progress**
   - See which users joined
   - Check completion rate
   - Archive completed challenges

---

## 9. Approval Workflows

### User Activity Approvals
1. **Habit/Activity Review**
   - Admin can approve or reject submitted activities
   - Provide feedback to user
   - Update user's tracking record

2. **Weight & Progress Reviews**
   - Monitor user progress
   - Set goals and track milestones
   - Provide coaching feedback

---

## 10. Analytics & Reporting

### Dashboard Reports
1. **User Analytics**
   - Total users: active, inactive, suspended
   - New signups (daily, weekly, monthly)
   - User retention rate
   - Activity engagement

2. **Revenue Reports**
   - Total revenue (paid + pending)
   - Revenue by subscription tier
   - Revenue by product
   - Outstanding amount breakdown

3. **Activity Reports**
   - Habits tracked (daily completion %)
   - Weight tracking participation
   - Payment compliance rate
   - Subscription renewal rate

### Export Options
- CSV export for all reports
- Date range filtering
- Email scheduled reports

---

## 11. Settings & Configuration

### Admin Settings `/admin_settings`
1. **System Settings**
   - Subscription tier pricing
   - GST rates
   - Reminder times
   - Auto-renewal settings

2. **User Management**
   - Add/remove admins
   - Set admin roles and permissions
   - Admin audit log

3. **Payment Settings**
   - Payment gateway configuration
   - Accepted payment methods
   - Currency and locale

4. **Notification Settings**
   - Enable/disable reminder types
   - Customize messages
   - Schedule times

---

## 12. Admin Role Levels

### Super Admin
- All permissions
- Manage other admins
- System settings
- Full audit access

### Store Manager
- Product management
- Store reports
- User purchase history
- Cannot manage subscriptions/payments

### Membership Manager
- User management
- Subscription management
- Payment tracking
- Cannot modify system settings

### Support Manager
- View user details (read-only)
- Send custom messages
- Resolve support tickets
- Cannot process payments

---

## Admin Callback Button Actions

All admin buttons are callback-based for instant responsiveness:

### Invoice Actions
```
inv2_pay_<id>       → Mark invoice as paid
inv2_reject_<id>    → Reject invoice request
inv2_resend_<id>    → Resend to user
inv2_delete_<id>    → Delete invoice
```

### User Actions
```
user_view_<id>      → View user details
user_edit_<id>      → Edit user info
user_suspend_<id>   → Suspend user
user_delete_<id>    → Delete user
```

### Subscription Actions
```
sub_upgrade_<id>    → Upgrade subscription
sub_downgrade_<id>  → Downgrade subscription
sub_renew_<id>      → Renew subscription
```

---

## Admin Workflow Diagram

```
ADMIN LOGIN (/start)
  ↓
ADMIN DASHBOARD
  ├→ USER MANAGEMENT
  │  ├→ View All Users
  │  ├→ Search User
  │  ├→ Edit Profile
  │  ├→ Change Subscription
  │  └→ Send Message
  │
  ├→ INVOICE MANAGEMENT
  │  ├→ Create Invoice
  │  ├→ Select User & Items
  │  ├→ Preview & Send
  │  ├→ Track Status
  │  └→ Handle Failures (telegram_id validation)
  │
  ├→ PAYMENT MANAGEMENT
  │  ├→ View Pending
  │  ├→ Mark as Paid
  │  ├→ Send Reminder
  │  └→ Payment Reports
  │
  ├→ SUBSCRIPTION MANAGEMENT
  │  ├→ View All Subscriptions
  │  ├→ Change Tier
  │  ├→ Extend Period
  │  └→ Renewal Settings
  │
  ├→ STORE MANAGEMENT
  │  ├→ Add Product
  │  ├→ Edit Product
  │  ├→ Stock Management
  │  └→ Store Reports
  │
  ├→ BROADCAST
  │  ├→ Send Message
  │  ├→ Select Recipients
  │  └→ Track Delivery
  │
  ├→ CHALLENGES
  │  ├→ Create Challenge
  │  ├→ Review Checkins
  │  └→ Approve/Reject
  │
  └→ REPORTS & ANALYTICS
     ├→ User Analytics
     ├→ Revenue Reports
     ├→ Activity Reports
     └→ Export Data
```

---

## Current Issues & Resolutions

### Issue: Invoice send fails with "Chat not found"
**Root Cause:** User record has placeholder telegram_id (2147483647) from legacy system  
**Validation Logic:**
- Check if telegram_id ≥ 2147483647 before sending
- If invalid: Skip send, display admin error
- Admin error message includes: "Ask user to send /start, then use Resend button"

**Resolution Flow:**
1. Admin attempts to create invoice for user with invalid ID
2. Bot validates telegram_id before send
3. If invalid, admin sees: "Invalid telegram_id (placeholder detected)"
4. Admin communicates with user to send `/start`
5. `/start` handler resolves username and updates telegram_id in DB
6. Admin uses "Resend" button to send invoice
7. Success!

**Status:** ✅ Implemented - prevents failed sends and guides admin to solution

---

## Deployment Status
- ✅ Database: MySQL with telegram_id tracking
- ✅ Invoice System: Full v2 with validation
- ✅ Payment Processing: Integrated workflow
- ✅ Reminders: Scheduled via APScheduler
- ✅ Callbacks: Handler routing optimized
- ✅ Validation: telegram_id checks in place
