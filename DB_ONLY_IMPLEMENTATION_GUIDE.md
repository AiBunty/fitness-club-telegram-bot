# COMPLETE MIGRATION: Neon → Local + DB-Only Searches

## MASTER SPEC

**LOCAL DATABASE IS THE ONLY SOURCE OF TRUTH**
- NO in-memory stores
- NO JSON registries  
- NO fallback logic
- ALL users, items, invoices, actions read/write from DB ONLY

---

## PART 1-3: DATABASE MIGRATION & SCHEMA ✅ COMPLETE

### Files Created:
1. **migrate_neon_to_local.py**
   - Exports schema-only from Neon
   - Exports data from Neon
   - Resets local database
   - Imports schema locally
   - Imports data locally
   - Resets sequences
   - Validates row counts

2. **validate_schema_part23.py**
   - Ensures users table has all columns
   - Ensures store_items table exists
   - Creates indexes for performance
   - Validates data was migrated

3. **schema.sql** (Updated)
   - Added store_items table with columns: item_id, serial_no, item_name, normalized_item_name, hsn_code, mrp, gst_percent, is_active
   - Added invoices table
   - Added invoice_items table
   - Removed JSON-based storage requirements

### Users Table (DB-ONLY):
```sql
user_id (BIGINT, PK, indexed)
first_name (VARCHAR)
last_name (VARCHAR)
username (VARCHAR)
full_name (VARCHAR)
normalized_name (VARCHAR, indexed)  -- lowercase, trimmed, collapsed spaces
is_banned (BOOLEAN, default FALSE)
created_at (TIMESTAMP)
updated_at (TIMESTAMP)
... other columns ...
```

### Store Items Table (DB-ONLY):
```sql
item_id (SERIAL, PK)
serial_no (INT, UNIQUE, indexed)
item_name (VARCHAR)
normalized_item_name (VARCHAR, indexed)
hsn_code (VARCHAR)
mrp (DECIMAL)
gst_percent (DECIMAL, default 18.0)
is_active (BOOLEAN, default TRUE, indexed)
created_at (TIMESTAMP)
updated_at (TIMESTAMP)
```

### Actions:
```bash
# 1. Run migration (exports from Neon, imports to local)
python migrate_neon_to_local.py

# 2. Validate schema (ensures all columns exist)
python validate_schema_part23.py

# 3. Verify data
psql -h localhost -U postgres -d fitness_club_db -c "SELECT COUNT(*) FROM users;"
psql -h localhost -U postgres -d fitness_club_db -c "SELECT COUNT(*) FROM store_items;"
```

---

## PART 4-6: DB-ONLY SEARCH HANDLERS ✅ COMPLETE

### PART 4: Invoice User Search (DB-Only)

**File:** `src/invoices_v2/search_db_only.py`

Function: `search_users_db_only(query: str, limit: int = 10) -> List[Dict]`

**Searches:**
- Numeric: Exact telegram_id match
- Text: Partial match on first_name, last_name, full_name, username, normalized_name

**CRITICAL:** No memory fallback, no JSON registry

**Response:**
- Success: List of users with user_id, first_name, last_name, full_name, username
- No match: Empty list → "No users found. Try another name or Telegram ID."

**Usage in invoices_v2/handlers.py:**
```python
# OLD (with fallback):
from src.invoices_v2.utils import search_users
results = search_users(query, limit=10)  # May fallback to JSON registry

# NEW (DB-only):
from src.invoices_v2.search_db_only import search_users_db_only
results = search_users_db_only(query, limit=10)  # ONLY DB, never falls back
```

### PART 5: Delete User Search (DB-Only + Flow Isolated)

**File:** `src/handlers/delete_user_db_only.py`

Function: `search_delete_user_db_only(query: str, limit: int = 10) -> List[Dict]`

**IDENTICAL logic to invoice user search**

**Key Addition: Flow Isolation**
```python
# Entry point LOCKS DELETE_USER flow
set_active_flow(admin_id, FLOW_DELETE_USER)

# Every handler CHECKS ownership
if not check_flow_ownership(admin_id, FLOW_DELETE_USER):
    return ConversationHandler.END  # Ignore if wrong flow

# Exit handler CLEARS lock
clear_active_flow(admin_id, FLOW_DELETE_USER)
```

**States:**
- DELETE_USER_SEARCH: Admin entering search term
- DELETE_USER_CONFIRM: Admin confirming deletion

**Guards:** If active_flow != DELETE_USER, handler ignores input

### PART 6: Invoice Item Search (DB-Only, No User Confusion)

**File:** `src/invoices_v2/search_items_db_only.py`

Function: `search_store_items_db_only(query: str, limit: int = 20) -> List[Dict]`

**CRITICAL DISTINCTION:**
- Searches store_items table ONLY (never users)
- Returns: item_id, serial_no, item_name, mrp, gst_percent
- Never returns user data

**Searches:**
- Numeric: Exact serial_no match
- Text: Partial match on item_name, normalized_item_name

**Response must show:**
- Serial No
- Item Name
- MRP
- GST %

**If no match:**
```
"No items found. Try another item name or serial number."
```

**NEVER respond with:**
```
❌ "No users found" (that's for user search!)
❌ User names or telegram IDs
```

---

## PART 7: FLOW ISOLATION GUARDS (IMPLEMENTATION CHECKLIST)

### Already Implemented (from flow_manager.py):

**File:** `src/utils/flow_manager.py` (existing)

Functions available:
```python
set_active_flow(admin_id, flow_name)
get_active_flow(admin_id)
is_flow_active(admin_id, flow_name)
check_flow_ownership(admin_id, expected_flow)  # Returns bool
clear_active_flow(admin_id, flow_name)
guard_flow_ownership()  # Async variant with optional alert
debug_flows()  # Shows all active flows
```

### Valid Flows (Constants):
```python
FLOW_DELETE_USER = "DELETE_USER"
FLOW_BAN_USER = "BAN_USER"
FLOW_UNBAN_USER = "UNBAN_USER"
FLOW_INVOICE_CREATE = "INVOICE_CREATE"
FLOW_INVOICE_V2_CREATE = "INVOICE_V2_CREATE"
FLOW_AR_RECORD_PAYMENT = "AR_RECORD_PAYMENT"
FLOW_STORE_ITEM_CREATE = "STORE_ITEM_CREATE"
FLOW_STORE_ITEM_EDIT = "STORE_ITEM_EDIT"
FLOW_BROADCAST = "BROADCAST"
FLOW_PAYMENT_REQUEST = "PAYMENT_REQUEST"
```

### Implementation Pattern (for each flow):

**1. Entry Point - Lock Flow**
```python
async def cmd_some_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    admin_id = ...
    set_active_flow(admin_id, FLOW_SOME_ACTION)  # LOCK
    # ... continue with flow ...
```

**2. All Text/Callback Handlers - Check Ownership**
```python
async def handle_user_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    admin_id = update.effective_user.id
    
    # GUARD: Only process if this handler owns the flow
    if not check_flow_ownership(admin_id, FLOW_SOME_ACTION):
        await update.effective_user.send_message("❌ Please start over")
        return ConversationHandler.END  # REJECT if wrong flow
    
    # ... process message ...
```

**3. All Exit Handlers - Clear Lock**
```python
async def handle_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    admin_id = ...
    clear_active_flow(admin_id, FLOW_SOME_ACTION)  # UNLOCK on cancel
    return ConversationHandler.END

async def handle_complete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    admin_id = ...
    clear_active_flow(admin_id, FLOW_SOME_ACTION)  # UNLOCK on completion
    return ConversationHandler.END

async def handle_error(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    admin_id = ...
    clear_active_flow(admin_id, FLOW_SOME_ACTION)  # UNLOCK even on error!
    return ConversationHandler.END
```

### MANDATORY: Clear on ALL Exit Paths
- ✅ Success completion
- ✅ User cancels
- ✅ Error occurred
- ✅ Timeout or unexpected state

### Testing Flow Isolation:

```python
from src.utils.flow_manager import debug_flows

# Check active flows
print(debug_flows())  # Shows all active flows per admin

# Expected output during Delete User flow:
# Admin 424837855: FLOW_DELETE_USER
```

---

## PART 8: REMOVE ALL NON-DB LOGIC

### Files That Need Cleanup:

1. **src/invoices_v2/utils.py**
   - Remove `search_users()` fallback to user_registry
   - Remove user registry JSON reads
   - Keep ONLY DB queries

2. **src/invoices_v2/handlers.py**
   - Replace: `from src.invoices_v2.utils import search_users`
   - With: `from src.invoices_v2.search_db_only import search_users_db_only`
   - Replace all: `search_users()` → `search_users_db_only()`

3. **src/handlers/invoice_handlers.py**
   - Remove: `from src.utils.user_registry import search_registry`
   - Remove: Registry fallback logic
   - Replace with: DB-only search

4. **src/invoices_v2/store.py**
   - Replace: `search_item()` to ONLY query store_items table
   - Remove: JSON file reads
   - Remove: Memory caches

5. **Delete user flow handler** (wherever it lives)
   - Remove: Memory-based user lookups
   - Replace with: `search_delete_user_db_only()`
   - Add flow isolation guards

### Removal Checklist:
```
❌ Remove: user_registry JSON file reads
❌ Remove: USERS_FILE JSON loads
❌ Remove: store_items JSON loads  
❌ Remove: invoices_v2.json memory stores
❌ Remove: context.user_data user caching for searches
❌ Remove: in-memory user registry fallback
❌ Remove: "try DB, fallback to JSON" pattern
✅ Keep: Flow manager (already DB-only)
✅ Keep: Database connection pool
```

---

## PART 9: VALIDATION & TESTING

### Pre-Deployment Checklist:

**Database:**
- [ ] Local DB has all tables: users, store_items, invoices, invoice_items
- [ ] All required columns exist
- [ ] All indexes created
- [ ] Row counts > 0 (data migrated from Neon)

**Search Functions:**
- [ ] `search_users_db_only()` returns DB results only
- [ ] `search_delete_user_db_only()` returns DB results only
- [ ] `search_store_items_db_only()` returns DB results only
- [ ] No fallback to JSON/memory happens

**Flow Isolation:**
- [ ] DELETE_USER flow locks when entry handler called
- [ ] DELETE_USER handlers reject messages from other flows
- [ ] DELETE_USER lock clears on completion
- [ ] INVOICE_V2_CREATE flow locked properly
- [ ] No cross-flow message routing

**Error Messages:**
- [ ] User search shows: "No users found. Try another..."
- [ ] Item search shows: "No items found. Try another..."
- [ ] Never mixed (no "No items" during user search)

**No In-Memory Storage:**
- [ ] No JSON registry reads during searches
- [ ] No fallback patterns
- [ ] No caching of user/item lists
- [ ] context.user_data doesn't contain copies of users/items

### Test Scenarios:

**Scenario 1: Invoice User Search**
```
1. Admin: /invoices
2. Click: Create Invoice
3. Search: "par" (for Parin)
4. Result: Should find users with "par" in name
   - NOT "No items found"
5. Select: User details shown correctly
```

**Scenario 2: Delete User Search**
```
1. Admin: Manage Users
2. Click: Delete User
3. Search: "123456789" (numeric ID)
4. Result: Should find exact user match
5. Confirm: User marked as deleted
6. Invoice flow should NOT be affected
```

**Scenario 3: Invoice Item Search**
```
1. Admin: Create Invoice
2. Select: User
3. Click: Search Store Items
4. Search: "234" (serial number)
5. Result: Should find item by serial
   - NOT user data mixed in
6. Response: Serial, Name, Price, GST%
```

**Scenario 4: Flow Isolation**
```
1. Admin A: Starts Delete User flow
2. Admin A: Enters search term "test"
   - Message routed to delete handler ✅
3. Admin B: Starts Invoice flow
   - Admin A's delete flow not affected ✅
4. Admin C: Starts Ban User flow
   - Admin A's delete flow and Admin B's invoice flow not affected ✅
```

**Scenario 5: No Memory Leaks**
```
1. Search for user
2. Search for item
3. Switch flows
4. No cached data from previous search remains
5. Each search fresh from DB
```

### Logging to Verify:

Look for these log patterns:

**Good (DB-only):**
```
[INVOICE_USER_SEARCH] db_only_search query='par'
[INVOICE_USER_SEARCH] text_match found 3 user(s)
[INVOICE_ITEM_SEARCH] db_only_search query='234'
[INVOICE_ITEM_SEARCH] numeric_match found serial=234
[FLOW] admin=424837855 started=INVOICE_V2_CREATE
[FLOW] admin=424837855 blocked DELETE_USER (active=INVOICE_V2_CREATE)
```

**Bad (should NOT see):**
```
[INVOICE_SEARCH] db_empty, trying json registry  ❌
[INVOICE_SEARCH] using_json_registry=true  ❌
fallback to user_registry  ❌
search_registry called  ❌
USERS_FILE loaded  ❌
```

---

## EXECUTION ORDER

1. **Run migration:**
   ```bash
   python migrate_neon_to_local.py
   ```

2. **Validate schema:**
   ```bash
   python validate_schema_part23.py
   ```

3. **Update imports in handlers:**
   - Replace old search functions with DB-only versions
   - Update all imports

4. **Test each search individually:**
   - Invoice user search
   - Delete user search
   - Invoice item search

5. **Test flow isolation:**
   - Multiple admins, multiple flows
   - Ensure no cross-contamination

6. **Remove non-DB logic:**
   - Remove JSON registry reads
   - Remove memory caches
   - Remove fallback patterns

7. **Full bot test:**
   - Restart bot
   - Run through all flows
   - Check logs for DB-only patterns

---

## FINAL STATE

**LOCAL DATABASE ONLY:**
- All users read from DB
- All items read from DB
- All invoices saved to DB
- No JSON files consulted for user/item data
- No in-memory registries
- ONE flow active per admin at a time
- All searches DB-backed

**NO MORE:**
- ❌ JSON user registry fallbacks
- ❌ Memory item caches
- ❌ Cross-flow message contamination
- ❌ Ambiguous message routing
- ❌ State collision bugs

---

## SUCCESS CRITERIA

✅ Database migration complete (100% data copied)
✅ All search functions DB-only (no fallbacks)
✅ Flow isolation working (one flow per admin)
✅ No cross-flow interference
✅ All logs show DB queries
✅ No memory/JSON fallback patterns
✅ Bot runs for 1 hour without state collision bugs
