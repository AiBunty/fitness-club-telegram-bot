# 🎯 PAYMENT TERMS WORKFLOW - VISUAL FLOWCHARTS

---

## Flow 1: PAID Shake Order (2-Minute Path)

```
┌─────────────────────────────────────────────────────────────┐
│ USER: Order Shake                                           │
│ 1. Clicks "Order Shake"                                    │
│ 2. Selects flavor (e.g., Vanilla)                         │
│ 3. Confirms order                                          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
        ┌────────────────────────────┐
        │ SYSTEM: Process Order      │
        │ • Deduct 1 credit          │
        │ • Save to DB as 'pending'  │
        └────────────────┬───────────┘
                         │
                         ▼
    ┌────────────────────────────────────────────┐
    │ ADMIN: Receive Instant Notification        │
    │                                            │
    │ 🔔 *NEW SHAKE ORDER*                      │
    │ 👤 User: John Doe                         │
    │ 🥤 Flavor: Vanilla                        │
    │ 💳 Credits Deducted: 1                    │
    │                                            │
    │ [💵 PAID] [📋 CREDIT] [❌ CANCEL]        │
    └────────────────┬──────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │ ADMIN CLICKS: 💵 PAID   │
        └────────────┬────────────┘
                     │
                     ▼
        ┌────────────────────────────┐
        │ SYSTEM: Mark as Paid       │
        │ • Payment_status = PAID    │
        │ • Status = READY           │
        │ • Payment_terms = PAID     │
        └────────────┬───────────────┘
                     │
                     ▼
    ┌────────────────────────────────────┐
    │ USER: Receive Confirmation         │
    │                                    │
    │ ✅ *Shake Approved - PAID*         │
    │ 🥤 Vanilla                        │
    │ 💵 Status: PAID                   │
    │                                    │
    │ Your shake is ready for pickup! 🎉 │
    └────────────────────────────────────┘
                     │
                     ▼
        ┌────────────────────────────┐
        │ NO REMINDERS SENT          │
        │ ORDER COMPLETE ✅          │
        └────────────────────────────┘
```

---

## Flow 2: CREDIT TERMS Shake Order (7-Day Path with Reminders)

```
┌─────────────────────────────────────────────────────────────┐
│ USER: Order Shake                                           │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
        ┌────────────────────────────┐
        │ SYSTEM: Process Order      │
        └────────────┬───────────────┘
                     │
                     ▼
    ┌────────────────────────────────────────────┐
    │ ADMIN: Receive Instant Notification        │
    │ [💵 PAID] [📋 CREDIT TERMS] [❌ CANCEL]   │
    └────────────────┬──────────────────────────┘
                     │
        ┌────────────┴────────────────────────┐
        │ ADMIN CLICKS: 📋 CREDIT TERMS       │
        └────────────┬─────────────────────────┘
                     │
                     ▼
        ┌────────────────────────────────────┐
        │ SYSTEM: Set Credit Terms           │
        │ • Payment_status = pending         │
        │ • Payment_terms = CREDIT           │
        │ • Due_date = 7 days from now       │
        └────────────┬──────────────────────┘
                     │
                     ▼
    ┌────────────────────────────────────┐
    │ USER: Receive Order Notification   │
    │                                    │
    │ ✅ *Order Approved - Credit Terms* │
    │ 💳 Payment Due: 7 days            │
    │ [✅ Mark as Paid]                 │
    └────────────────┬───────────────────┘
                     │
          ╔──────────┴──────────╗
          │                     │
          ▼ (User pays)         ▼ (Payment overdue)
    ┌─────────────┐      ┌──────────────────────┐
    │ USER READY  │      │ DAILY at 11:00 AM    │
    │ TO PAY      │      │ SCHEDULED JOB RUNS   │
    │             │      └──────────┬───────────┘
    └──────┬──────┘                 │
           │                         ▼
           │             ┌────────────────────────────────────┐
           │             │ SYSTEM: Check overdue payments    │
           │             │ • Query: payment_date < TODAY     │
           │             │ • Get all pending credit orders   │
           │             └────────────┬─────────────────────┘
           │                          │
           │                          ▼
           │             ┌────────────────────────────────────┐
           │             │ IF overdue AND <= 3 reminders     │
           │             │ Send reminder to user             │
           │             └────────────┬─────────────────────┘
           │                          │
           │                          ▼
           │    ┌────────────────────────────────────────┐
           │    │ USER: Receive Payment Reminder         │
           │    │                                        │
           │    │ 💳 *PAYMENT REMINDER*                │
           │    │ Order ID: #123                        │
           │    │ Due Date: Jan 24                      │
           │    │ Status: OVERDUE                       │
           │    │ [✅ Mark as Paid]                     │
           │    └────────────┬───────────────────────────┘
           │                 │
           │     ┌───────────┴──────────┐
           │     │ USER CLICKS:          │
           │     │ ✅ Mark as Paid       │
           │     └───────────┬──────────┘
           │                 │
           └─────────────────┤
                             ▼
        ┌────────────────────────────────────┐
        │ SYSTEM: Mark User Paid              │
        │ • Payment_status = user_confirmed  │
        │ • Notify all admins                │
        └────────────┬──────────────────────┘
                     │
                     ▼
    ┌──────────────────────────────────────┐
    │ ADMIN: Receive Approval Notification │
    │                                      │
    │ 🔔 *USER PAYMENT CONFIRMATION*      │
    │ User: John Doe confirmed payment     │
    │ Order ID: #123                       │
    │                                      │
    │ [✅ Approve Payment]                 │
    └────────────┬─────────────────────────┘
                 │
    ┌────────────┴──────────┐
    │ ADMIN CLICKS:         │
    │ ✅ Approve Payment    │
    └────────────┬──────────┘
                 │
                 ▼
    ┌──────────────────────────────────┐
    │ SYSTEM: Approve & Stop Reminders │
    │ • Payment_status = PAID          │
    │ • Stop sending reminders         │
    │ • Notify user                    │
    └────────────┬─────────────────────┘
                 │
                 ▼
    ┌──────────────────────────────────┐
    │ USER: Final Confirmation         │
    │                                  │
    │ ✅ *Payment Approved!*          │
    │ Order #123 payment confirmed    │
    │ Thank you! 🙏                   │
    │                                  │
    │ ORDER COMPLETE ✅               │
    └──────────────────────────────────┘
```

---

## Flow 3: Gym Check-in Approval (1-Minute Path)

```
┌─────────────────────────────────────────────┐
│ USER: Check In                              │
│ 1. Sends location (or manual check-in)     │
└────────────────────┬────────────────────────┘
                     │
                     ▼
        ┌────────────────────────────────┐
        │ SYSTEM: Process Check-in        │
        │ • Save to attendance_queue      │
        │ • Status = pending              │
        └────────────┬────────────────────┘
                     │
                     ▼
    ┌──────────────────────────────────────┐
    │ USER: Receive Acknowledgment         │
    │                                      │
    │ ✅ Attendance logged               │
    │ Awaiting admin approval             │
    └──────────────────────────────────────┘
                     │
                     ▼
    ┌─────────────────────────────────────────┐
    │ ADMIN: Receive Instant Notification     │
    │                                         │
    │ 🔔 *NEW GYM CHECK-IN*                 │
    │ 👤 User: John Doe                      │
    │ 📞 Phone: 9876543210                  │
    │ 📅 Date: Jan 17, 2026                 │
    │ 🏢 Attendance ID: 456                  │
    │                                         │
    │ [✅ APPROVE] [❌ REJECT]              │
    └────────────────┬────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
        │ SCENARIO A              │ SCENARIO B
        │ ADMIN CLICKS:           │ ADMIN CLICKS:
        │ ✅ APPROVE              │ ❌ REJECT
        │                         │
        ▼                         ▼
    ┌──────────────────┐    ┌──────────────────────┐
    │ SYSTEM: Approve  │    │ SYSTEM: Reject       │
    │ • Status = OK    │    │ • Status = rejected  │
    │ • Award +50 pts  │    │ • Notify user reason │
    └────────┬─────────┘    └──────────┬───────────┘
             │                         │
             ▼                         ▼
    ┌──────────────────────┐  ┌─────────────────────┐
    │ USER: Success        │  │ USER: Rejected      │
    │                      │  │                     │
    │ ✅ Attendance OK!    │  │ ❌ Check-in failed  │
    │ +50 points awarded   │  │ Please try again    │
    │                      │  │ Contact admin       │
    └──────────────────────┘  └─────────────────────┘
```

---

## Flow 4: Rejection & Credit Refund

```
ANY ORDER (Paid or Credit)
        │
        ▼
┌────────────────────────────────┐
│ ADMIN: Receives Notification   │
│ [💵 PAID] [📋 CREDIT] [❌ CANCEL] │
└────────────┬───────────────────┘
             │
    ┌────────┴──────────┐
    │ ADMIN CLICKS:     │
    │ ❌ CANCEL         │
    └────────┬──────────┘
             │
             ▼
    ┌─────────────────────────────┐
    │ SYSTEM: Cancel Order        │
    │ • Mark as cancelled         │
    │ • Refund 1 credit           │
    │ • Notify user               │
    └────────┬────────────────────┘
             │
             ▼
    ┌──────────────────────────────┐
    │ USER: Receive Notification   │
    │                              │
    │ ❌ *Order Cancelled*         │
    │ Flavor: Vanilla              │
    │                              │
    │ 💳 1 credit refunded         │
    │ Your credit balance: 25      │
    └──────────────────────────────┘
             │
             ▼
    ┌──────────────────────────────┐
    │ USER CAN ORDER AGAIN ✅      │
    └──────────────────────────────┘
```

---

## State Machine: Payment Status Transitions

```
                    ┌─────────────────────┐
                    │     START           │
                    │   (Order Created)   │
                    └──────────┬──────────┘
                               │
                    ┌──────────┴──────────┐
                    │ Admin Decides:      │
                    │ Paid or Credit      │
                    └──────────┬──────────┘
                               │
                ┌──────────────┼──────────────┐
                │              │              │
                ▼              ▼              ▼
        ┌────────────┐  ┌─────────────┐  ┌──────────┐
        │   PAID     │  │   CREDIT    │  │ CANCELLED│
        │  (Auto)    │  │  (Pending)  │  │ (Done)   │
        └──────┬─────┘  └──────┬──────┘  └──────────┘
               │                │
               │                ▼
               │         ┌─────────────────┐
               │         │ User Confirms   │
               │         │ Payment w/      │
               │         │ ✅ Mark Paid    │
               │         └────────┬────────┘
               │                  │
               │                  ▼
               │         ┌──────────────────┐
               │         │  USER_CONFIRMED  │
               │         │  (Awaiting Admin)│
               │         └────────┬─────────┘
               │                  │
               │                  ▼
               │         ┌──────────────────┐
               │         │ Admin Approves   │
               │         │ ✅ Approve Pay   │
               │         └────────┬─────────┘
               │                  │
               └──────────┬───────┘
                          │
                          ▼
                   ┌────────────┐
                   │   PAID     │
                   │ (Final)    │
                   └────────────┘
                       ✅ Done
```

---

## Database State Diagram

```
User Places Order
        │
        ▼
INSERT shake_requests:
├─ payment_status = 'pending'
├─ payment_terms = 'pending'
├─ follow_up_reminder_sent = FALSE
└─ overdue_reminder_count = 0

        │
        ▼ (Admin decides)
        │
    ┌───┴───┐
    │       │
    ▼       ▼
PAID      CREDIT TERMS
│         │
UPDATE:   UPDATE:
status=   status = ready
ready     payment_terms = credit
payment   payment_due_date = +7
_terms=   days
paid      follow_up_reminder_
payment   sent = FALSE
_status=
paid

        │         │
        │         ▼ (Daily 11 AM)
        │         │
        │      SEND REMINDER
        │         │
        │      UPDATE:
        │      overdue_reminder
        │      _count++
        │         │
        │         ▼ (User clicks)
        │         │
        │      UPDATE:
        │      payment_status =
        │      user_confirmed
        │         │
        │         ▼ (Admin approves)
        │         │
        │      UPDATE:
        │      payment_status=paid
        │      follow_up_reminder_
        │      sent = TRUE
        │         │
        └─────────┴────────────┐
                               │
                               ▼
                        🎉 ORDER COMPLETE
```

---

**These flows ensure:**
✅ Clear paths for all scenarios  
✅ Instant admin notifications  
✅ Automatic payment reminders  
✅ Complete audit trail in database  

