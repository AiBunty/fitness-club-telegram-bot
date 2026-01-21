# Invoice v2 Flow Testing - Live Monitoring Guide

**Bot Status:** ✅ RUNNING  
**Start Time:** 2026-01-21 08:45:14  
**Logs Location:** `fitness-club-telegram-bot/logs/fitness_bot.log`

---

## Flow Testing Procedures

### Test #1: User Search in Invoice v2 ⭐ PRIMARY

**Objective:** Verify user search returns correct message (not item search message)

**Steps:**
1. Send `/invoices` to bot
2. Click "Create Invoice" button
3. Enter partial user name (e.g., "par" or "admin")
4. **Expected Result:**
   - "❌ No users found. Try again:" OR user list with matching names
   - **NOT:** "No items found. Try another name."

**Success Indicators:**
- Log shows: `[INVOICE_V2] handle_user_search CALLED`
- Log shows: `[INVOICE_V2] user_search_results count=X`
- Returns users, not items

**Failure Indicators:**
- Message: "No items found. Try another name."
- Log shows: `[STORE_SEARCH]` during user search state
- No `handle_user_search` log entry

---

### Test #2: Item Search in Invoice v2

**Objective:** Verify item search works after user selected

**Steps:**
1. Complete Test #1 and select a user
2. Should see "📦 Select an item to add to invoice"
3. Enter item name (e.g., "shake" or "water")
4. **Expected Result:**
   - List of matching store items OR "❌ No items found"
   - Items should show: `Serial # | Item Name | Price`

**Success Indicators:**
- Log shows: `SEARCH_STORE_ITEM` state
- Returns store items correctly
- Serial numbers present

---

### Test #3: Create Store Item (Create Flow)

**Objective:** Verify no search interference during item creation

**Steps:**
1. Admin → Store Management → Create Item
2. Enter item name (e.g., "Protein Shake v2")
3. Enter price (e.g., 150)
4. Enter HSN code
5. **Expected Result:**
   - Item created successfully
   - No "searched in items" error
   - Item appears in list

---

### Test #4: Bulk Upload Items

**Objective:** Verify Excel upload works

**Steps:**
1. Admin → Store Management → Bulk Upload Items
2. Send Excel file with items
3. **Expected Result:**
   - "✅ Upload successful! X items processed"
   - Items created in database

---

## Real-Time Log Monitoring

### Key Log Markers to Watch

```
✅ SUCCESS PATTERNS:
[INVOICE_V2] search_user_start      - User entered invoice user search
[INVOICE_V2] handle_user_search CALLED  - Handler received text
[INVOICE_V2] user_search_results count=X - Search executed
SEARCH_STORE_ITEM              - Item search state active

❌ ERROR PATTERNS:
[STORE_SEARCH] DEPRECATED      - Wrong search handler triggered
No users found. Try again:     - Correct user search response
No items found.                - Should only appear in SEARCH_STORE_ITEM state
ERROR                          - Database or process error
Traceback                      - Exception occurred
```

### Live Log Commands

**View last 50 lines:**
```powershell
Get-Content 'logs/fitness_bot.log' -Tail 50
```

**Real-time tail:**
```powershell
Get-Content 'logs/fitness_bot.log' -Wait
```

**Search for Invoice v2 logs:**
```powershell
Select-String '\[INVOICE_V2\]' 'logs/fitness_bot.log' | Select-Object -Last 20
```

**Search for errors:**
```powershell
Select-String 'ERROR|Traceback|exception' 'logs/fitness_bot.log' -Context 2 | Select-Object -Last 30
```

---

## Testing Checklist

| Test | Expected | Status | Notes |
|------|----------|--------|-------|
| User search message | "No users found" | ⏳ PENDING | User search, not item search |
| User search returns list | Shows user names | ⏳ PENDING | Can select from results |
| Item search after user | Shows store items | ⏳ PENDING | Serial # present |
| Create item flow | Item created | ⏳ PENDING | No search interference |
| Bulk upload | File processed | ⏳ PENDING | Items in database |

---

## Common Issues & Solutions

### Issue: "No items found" during user search
**Cause:** Global text handler consuming message before conversation handler  
**Status:** ✅ FIXED - Handler moved to group=1  
**Verification:** Search for `[INVOICE_V2] handle_user_search CALLED` in logs

### Issue: Invoice button not responding
**Cause:** Pattern mismatch `cmd_invoices_v2` vs `cmd_invoices`  
**Status:** ✅ FIXED - Updated to `cmd_invoices`

### Issue: Store Create Item shows "No items found"
**Cause:** Global search handler intercepting text input  
**Status:** ✅ FIXED - Removed duplicate handler registration

### Issue: Bulk Upload doesn't respond
**Cause:** Missing `BULK_UPLOAD_AWAIT` state  
**Status:** ✅ FIXED - Added state with document handler

---

## Session Progress

**Fixes Applied:**
1. ✅ Added connection timeout (10s) for remote PostgreSQL
2. ✅ Reduced pool size: minconn=5→2, maxconn=50→20 (faster init)
3. ✅ Moved global handler to group=1 (conversation priority fix)
4. ✅ Enhanced logging in user_search handler

**Current Status:** BOT RUNNING, READY FOR TESTING

**Next Steps:**
1. Test Invoice v2 user search flow
2. Monitor logs in real-time for any issues
3. Test store operations
4. Verify all flows work end-to-end

---

## Performance Notes

- Bot startup time: ~1 second (after connection pool optimization)
- Database pool: 2-20 connections (vs previous 5-50)
- Telegram polling: 10-second intervals
- Handler priority: Conversation (group 0) → Global (group 1)

