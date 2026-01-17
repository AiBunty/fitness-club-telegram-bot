# 🥤 Shake Credit System - Quick Test Guide

## ✅ System Status
**Live and operational!** All shake credit features are now active.

---

## 🎮 How to Test

### **From Your Telegram Bot:**

#### 1️⃣ **Test Check Shake Credits**
```
/menu
↓
Click: 🥤 Check Shake Credits
↓
Expected: Shows current balance (0 initially, after initialization)
         Shows available actions: "🥛 Order Shake", "💾 Buy Shake Credits", "📊 View Report"
```

#### 2️⃣ **Test Buy Shake Credits**
```
/menu
↓
Click: 💾 Buy Shake Credits
↓
Expected: Message "You're about to purchase 25 shake credits for Rs 6000"
         Shows button: "✅ Confirm Purchase"
         
User clicks: ✅ Confirm Purchase
↓
Expected: Message "✅ Purchase request created! Pending admin approval"
         Purchase appears in admin queue
```

#### 3️⃣ **Admin: Approve Purchase**
```
/menu (as admin)
↓
Click: 🥤 Pending Shake Purchases
↓
Expected: Shows all pending purchase requests:
         - User ID and name
         - Credits requested (25)
         - Amount (Rs 6000)
         - Buttons: ✅ Approve | ❌ Reject
         
Admin clicks: ✅ Approve
↓
Expected: Credits transferred to user
         User receives: "✅ Your purchase of 25 credits has been approved!"
         Balance updates to show 25 available credits
         Admin sees next pending request
```

#### 4️⃣ **User: Order Shake (After Credits Available)**
```
After approving credits:

/menu
↓
Click: 🥤 Check Shake Credits
↓
Shows: "✅ Available Shake Credits: 25"
       Buttons: "🥛 Order Shake" | "💾 Buy More" | "📊 Report"

Click: 🥛 Order Shake
↓
Expected: Shows flavor options:
         🍓 Strawberry
         🍌 Banana
         🥗 Green Juice
         etc.
         
User clicks: 🍓 Strawberry
↓
Expected: ✅ Shake order placed!
         1️⃣ Credit deducted
         ✅ Available credits left: 24
         Your shake will be ready soon!
```

#### 5️⃣ **User: View Shake Report**
```
/menu
↓
Click: 🥤 Check Shake Credits
↓
Click: 📊 View Report
↓
Expected: Shows transaction history:
         DATE        | TYPE      | CREDITS | BALANCE
         ------------|-----------|---------|--------
         2026-01-16  | purchase  | +25     | +25
         2026-01-16  | consume   | -1      | 24
         
         (All transactions with dates)
```

#### 6️⃣ **Admin: Manual Shake Deduction (With Date)**
```
/menu (as admin)
↓
Click: 🍽️ Manual Shake Deduction
↓
Expected: Prompt to select user
         After selection: Calendar picker for date
         
Admin picks a date (e.g., 2026-01-15)
↓
Expected: ✅ 1 credit deducted
         Transaction recorded with selected date
         
User checks report:
↓
Expected: Transaction shows:
         DATE        | TYPE           | CREDITS | BALANCE
         2026-01-15  | admin_deduction| -1      | 23
         
         (With the manually selected date)
```

---

## 📊 Database Verification

### Check Raw Data (Optional):
```bash
# From command line, connect to PostgreSQL:
psql -U your_user -d your_db -c "SELECT * FROM shake_credits LIMIT 5;"
psql -U your_user -d your_db -c "SELECT * FROM shake_transactions ORDER BY created_at DESC LIMIT 10;"
psql -U your_user -d your_db -c "SELECT * FROM shake_purchases WHERE status='pending';"
```

---

## ✅ Expected Behaviors

| Action | Expected Result |
|--------|-----------------|
| New user checks credits | Shows 0 available credits |
| User buys 25 credits | Creates pending purchase request |
| Admin approves | 25 credits added, user notified |
| User orders shake | 1 credit deducted, balance updated |
| User checks report | Shows all transactions with dates |
| Admin manual deduction | Credit deducted with selected date |
| User has 0 credits tries order | Shows "Insufficient credits" message |

---

## 🔍 Troubleshooting

### Issue: "User doesn't see 💾 Buy Shake Credits button"
**Solution:** 
- Verify bot is restarted after migration
- Check user role is correct (not admin/staff)
- Try `/menu` again

### Issue: "Credits not showing after approval"
**Solution:**
- Check database: `SELECT * FROM shake_credits WHERE user_id = <user_id>`
- Check transactions: `SELECT * FROM shake_transactions WHERE user_id = <user_id>`
- Verify purchase status: `SELECT * FROM shake_purchases WHERE user_id = <user_id>`

### Issue: "Order shake button doesn't work"
**Solution:**
- Verify user has available credits
- Check logs for database errors
- Restart bot if needed

### Issue: "Admin can't see pending purchases"
**Solution:**
- Verify user is admin (check role_operations)
- Check if there are pending purchases: `SELECT * FROM shake_purchases WHERE status='pending'`
- Try `/menu` again

---

## 📱 Test Checklist

- [ ] ✅ Check Shake Credits - Shows 0 initially
- [ ] 💾 Buy Shake Credits - Creates purchase request
- [ ] 🥤 Pending Purchases (Admin) - Shows pending requests
- [ ] ✅ Approve Purchase - Credits transferred
- [ ] 🥛 Order Shake - After approval, order works
- [ ] 1️⃣ Credit deducted - Balance decreases
- [ ] 📊 Shake Report - Shows transaction history
- [ ] 🍽️ Manual Deduction - Admin can deduct with date
- [ ] 📅 Calendar date appears - In transaction history
- [ ] ❌ Reject Purchase - Admin can reject requests
- [ ] 💬 Notifications work - User receives messages on approve
- [ ] 🔒 Security - Only admins see admin buttons

---

## 💡 Key Points

1. **Pricing:** Rs 6000 for 25 credits (Rs 240 per credit)
2. **Deduction:** 1 credit per shake order
3. **Approval:** All purchases require admin approval
4. **Tracking:** All transactions logged with dates
5. **Reports:** Users can see full history anytime
6. **Security:** Admin-only operations protected

---

## 🎯 Feature Summary

✅ **User Can:**
- Check balance anytime
- Buy credit packages
- Order shakes with credits
- View transaction history

✅ **Admin Can:**
- Approve/reject purchases
- Manually deduct credits with date
- View all pending requests
- See all transactions

✅ **System:**
- Tracks all transactions
- Calculates running balance
- Logs dates for manual deductions
- Notifies users on approval
- Prevents unauthorized credits

---

## 🚀 Ready to Use!

The system is fully operational. Start testing from the Telegram bot using the test flows above.

**Status:** ✅ **LIVE**
**Bot Version:** Latest with Shake Credit System v1.0
**Database:** Connected and ready
**Features:** All 9 features active

Happy testing! 🎉
