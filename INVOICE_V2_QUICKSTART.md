# Invoice v2 - Quick Start Guide

## 🚀 Immediate Testing Steps

### 1. Start Bot
```powershell
cd C:\Users\ventu\Fitness\fitness-club-telegram-bot
python start_bot.py
```

### 2. Admin Test Flow

**Step 1: Open Admin Menu**
- Send `/start` to bot
- Click "Admin Menu" (if admin)

**Step 2: Create Invoice**
- Click "🧾 Invoices"
- Should see: "📄 Invoice Menu" with "➕ Create Invoice"

**Step 3: Search User**
- Click "➕ Create Invoice"
- Enter user search: name, @username, or telegram_id
- Example: "John" or "424837855"

**Step 4: Select User**
- Click on user from results
- Should see: "✅ Selected: {user}"

**Step 5: Add Store Item**
- Click "🔍 Search Store Item"
- Enter: "1" (serial) or "Protein" (name)
- Select item
- Enter quantity: "2"
- Enter discount: "10"
- Should see item summary

**Step 6: Finish Items**
- Click "➡️ Finish Items"
- Enter shipping: "50"

**Step 7: Send Invoice**
- Review final summary
- Click "📤 Send Invoice"
- Should see: "✅ Invoice {id} sent to user and admin!"

**Step 8: Check Deliveries**
- User receives PDF + Pay/Reject buttons
- Admin receives same PDF + Delete/Resend buttons

### 3. User Test Flow

**Step 1: User Opens Invoice**
- User receives invoice PDF from bot
- Sees: "Invoice ID: {id}", Amount, PDF

**Step 2: User Actions**
- Click "💳 Pay Bill" → Routes to payment flow
- OR Click "❌ Reject Bill" → Notifies admin

## 🔍 Debugging

### Check Logs
```powershell
Get-Content logs/fitness_bot.log -Tail 50 -Wait
```

### Look for:
```
[INVOICE_V2] entry_point admin={id}
[INVOICE_V2] user_selected user_id={id}
[INVOICE_V2] store_item_selected serial={serial}
[INVOICE_V2] item_added name={name}
[INVOICE_V2] invoice_sent_to_user invoice_id={id}
[INVOICE_V2] invoice_sent_to_admin invoice_id={id}
```

### Common Issues

**"No users found"**
- Check: `data/users.json` exists and has users
- Fix: Ensure user registry pre-handler is active

**"No items found"**
- Check: `data/store_items.json` exists
- Fix: Add test items via existing Store Items menu

**Invoice button not responding**
- Check: Bot logs for callback routing
- Check: Handler registration in bot.py
- Check: No pattern exclusion conflicts

## 📝 Test Data Setup

### Create Test Store Item
1. Admin Menu → "🏬 Create Store Items"
2. Add item: Name="Test Item", HSN="1234", MRP=100, GST=18
3. Item gets auto serial #1

### Verify User Registry
```powershell
cd C:\Users\ventu\Fitness\fitness-club-telegram-bot
python -c "import json; print(json.dumps(json.load(open('data/users.json')), indent=2))"
```

## 🎯 Success Criteria

✅ Admin clicks Invoices → Shows Invoice Menu  
✅ User search returns results  
✅ Item search (serial/name) works  
✅ Invoice generates PDF correctly  
✅ User receives invoice + buttons  
✅ Admin receives copy of invoice  
✅ Pay button routes to payment  
✅ Reject button notifies admin  

## 🚨 Rollback Plan (if needed)

**If v2 has issues, restore legacy:**

1. Comment out v2 registration in `src/bot.py`:
```python
# Invoice v2 (DISABLED)
# from src.invoices_v2.handlers import get_invoice_v2_handler, handle_pay_bill, handle_reject_bill
# application.add_handler(get_invoice_v2_handler())
```

2. Uncomment legacy handlers:
```python
# Invoice creation conversation (LEGACY)
from src.handlers.invoice_handlers import get_invoice_conversation_handler
application.add_handler(get_invoice_conversation_handler())
```

3. Restore old callback routing in `src/handlers/callback_handlers.py`:
```python
elif query.data == "cmd_invoices":
    from src.handlers.invoice_handlers import cmd_create_invoice_start
    await cmd_create_invoice_start(update, context)
```

4. Restart bot

## 📊 Monitoring

**Check invoice creation:**
```powershell
python -c "import json; inv = json.load(open('data/invoices_v2.json')); print(f'Total invoices: {len(inv)}'); print('Recent:', inv[-3:])"
```

**Check store items:**
```powershell
python -c "import json; items = json.load(open('data/store_items.json')); print(f'Total items: {len(items)}'); [print(f'{i[\"serial\"]}: {i[\"name\"]}') for i in items[:5]]"
```

## 🎉 Next Steps After Testing

1. Monitor logs for errors
2. Test edge cases (cancellations, invalid input)
3. Verify admin copy delivery works
4. Test user Pay/Reject actions
5. Verify GST calculations (inclusive/exclusive)
6. Test with multiple items in invoice
7. Verify PDF formatting looks correct

**Questions? Check:** `INVOICE_V2_COMPLETE.md` for full documentation
