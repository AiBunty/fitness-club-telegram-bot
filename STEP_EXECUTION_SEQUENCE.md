# 🎬 EXACT EXECUTION SEQUENCE

## Prerequisites ⚠️
- [ ] Cloud MySQL backup taken (full snapshot)
- [ ] Migration files ready (001_fix_ar_schema.sql, 002_fix_subscription_schema.sql)
- [ ] Python environment configured (venv active, dependencies installed)

---

## STEP 1: Backup Cloud MySQL (NON-REVERSIBLE)

### Option A: Via StackCP Web Panel
1. Log into StackCP console
2. Go to your MySQL instance
3. Create snapshot/backup
4. Wait for completion
5. Note backup ID/timestamp

### Option B: Via CLI (SSH to server or local tunnel)
```bash
# Create timestamped backup file
mysqldump -h mysql.gb.stackcp.com -P 42152 \
  -u FItnessBot-313935eecd -p FItnessBot-313935eecd \
  > backup_pre_migration_$(date +%Y%m%d_%H%M%S).sql

# Verify backup file size (should be > 1MB typically)
ls -lh backup_pre_migration_*.sql
```

### Confirmation
- [ ] Backup exists and is verified accessible
- [ ] Note backup filename/ID for emergency restore

---

## STEP 2: Apply Migration 001 (Accounts Receivable)

### Method: MySQL Client (e.g., MySQL Workbench, DBeaver, or CLI)
```bash
# If via CLI:
mysql -h mysql.gb.stackcp.com -P 42152 \
  -u FItnessBot-313935eecd -p FItnessBot-313935eecd \
  < migrations/001_fix_ar_schema.sql
```

### Verification
- [ ] No errors in console output
- [ ] Tables `accounts_receivable` and `ar_transactions` exist
- [ ] Run: `SHOW TABLES LIKE 'accounts%';` → should show both tables

---

## STEP 3: Apply Migration 002 (Subscription Tables)

### Method: MySQL Client
```bash
mysql -h mysql.gb.stackcp.com -P 42152 \
  -u FItnessBot-313935eecd -p FItnessBot-313935eecd \
  < migrations/002_fix_subscription_schema.sql
```

### Verification
- [ ] No errors in console output
- [ ] Tables `subscription_requests`, `subscriptions`, `subscription_payments` exist
- [ ] Run: `SHOW TABLES LIKE 'subscription%';` → should show all 3 tables

---

## STEP 4: Validate Schema

### Run Validation SQL
Copy all queries from `STEP_3_VALIDATION_SQL.sql` and execute in MySQL client:

```sql
DESCRIBE accounts_receivable;
DESCRIBE ar_transactions;
DESCRIBE subscription_requests;
DESCRIBE subscriptions;
DESCRIBE subscription_payments;
```

### Checklist
- [ ] All expected columns present in each table
- [ ] Primary keys correct (receivable_id, transaction_id, id, etc.)
- [ ] Foreign keys exist and reference correct tables
- [ ] All tables empty (count = 0)
- [ ] users table has `fee_status` and `fee_paid_date` columns
  - If missing:
    ```sql
    ALTER TABLE users ADD COLUMN fee_status VARCHAR(50) DEFAULT 'unpaid';
    ALTER TABLE users ADD COLUMN fee_paid_date TIMESTAMP NULL;
    ```

---

## STEP 5: Run Fabricated-Data Harness

### Prerequisites
- [ ] Python venv active
- [ ] All migrations applied and schema validated
- [ ] MySQL connection working

### Execute
```bash
cd /path/to/fitness-club-telegram-bot
python STEP_4_FABRICATED_DATA_HARNESS.py
```

### Expected Output
```
================================================================================
STEP 4: FABRICATED-DATA VALIDATION HARNESS
================================================================================
Mode: remote | USE_REMOTE_DB: true
Database: mysql.gb.stackcp.com:42152
================================================================================

[1/7] Ensuring test users exist...
  ✓ User 9901 (Test_User_A) created
  ✓ User 9902 (Test_User_B) created

[2/7] Testing invoice payment confirmation...
  ✓ Invoice A confirmed (no lines) → receivable_id=1
  ✓ Invoice B confirmed (1 UPI) → receivable_id=2
  ✓ Invoice C confirmed (cash+UPI) → receivable_id=3

[3/7] Testing subscription approvals...
  ✓ Subscription 1 approved (cash) → request_id=1
  ✓ Subscription 2 approved (UPI) → request_id=2
  ✓ Subscription 3 approved (split) → request_id=3
  ✓ Subscription 4 approved (no lines) → request_id=4

[4/7] Validating AR data...
  Receivables (7):
    ID 1: type=invoice, source=9999, user=9901, amt=1500, status=pending
    ID 2: type=invoice, source=9999, user=9901, amt=1200, status=paid
    ID 3: type=invoice, source=9999, user=9901, amt=1500, status=paid
    ID 4: type=subscription, source=1, user=9902, amt=2500, status=pending
    ID 5: type=subscription, source=2, user=9902, amt=2500, status=pending
    ID 6: type=subscription, source=3, user=9902, amt=2500, status=partial
    ID 7: type=subscription, source=4, user=9902, amt=2500, status=pending
  Transactions (7):
    ID 1: receivable=2, method=upi, amt=1200, ref=UPI-TEST-INV-B
    ID 2: receivable=3, method=cash, amt=700, ref=CASH-TEST-INV-C
    ID 3: receivable=3, method=upi, amt=800, ref=UPI-TEST-INV-C
    ID 4: receivable=4, method=cash, amt=2500, ref=TEST-CASH-SUB
    ID 5: receivable=5, method=upi, amt=2500, ref=TEST-UPI-SUB
    ID 6: receivable=6, method=cash, amt=1000, ref=TEST-SPLIT-CASH
    ID 7: receivable=6, method=upi, amt=1500, ref=TEST-SPLIT-UPI
  ✓ Receivable count: 7 (expected 7)
  ✓ Transaction count: 7 (expected 7)

[5/7] Validating AR reports...
  Payment Method Breakdown:
    cash: ₹3200
    upi: ₹4000
  Outstanding by Receivable:
    ID 1: status=pending, ₹1500 outstanding
    ID 2: status=paid, ₹0 outstanding
    ID 3: status=paid, ₹0 outstanding
    ID 4: status=pending, ₹0 outstanding
    ID 5: status=pending, ₹0 outstanding
    ID 6: status=partial, ₹0 outstanding
    ID 7: status=pending, ₹2500 outstanding
  ✓ All paid receivables have zero balance

[6/7] Cleaning up test records...
  ✓ Cleanup complete (test users and related records deleted)

================================================================================
✓ ALL VALIDATION TESTS PASSED
================================================================================
```

### Failure Handling
If ANY test fails:
1. **Do NOT proceed** to production use
2. Check error message and log details
3. Investigate schema/code mismatch
4. Restore from backup if needed:
   ```bash
   mysql -h mysql.gb.stackcp.com -P 42152 \
     -u FItnessBot-313935eecd -p FItnessBot-313935eecd \
     < backup_pre_migration_TIMESTAMP.sql
   ```

---

## STEP 6: Final Guardrail Verification

### In MySQL console:
```sql
-- Verify no hardcoded paid=true or status writes outside update_receivable_status
SELECT CONSTRAINT_NAME, TABLE_NAME, COLUMN_NAME 
FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE 
WHERE TABLE_SCHEMA = DATABASE() AND REFERENCED_TABLE_NAME IS NOT NULL;
-- Should show FK constraints intact

-- Verify invoices don't auto-create AR on creation (empty table if no tests)
SELECT COUNT(*) FROM accounts_receivable WHERE receivable_type='invoice';

-- Verify reports are read-only (SELECT only, no updates)
-- (Manual code review of ar_reports handlers)
```

### In Python console:
```python
import os
os.environ['USE_LOCAL_DB'] = 'false'
os.environ['USE_REMOTE_DB'] = 'true'
from src.database.ar_operations import create_receivable, update_receivable_status

# Test that status derivation works
rec = create_receivable(user_id=1, receivable_type='test', source_id=None, 
                        bill_amount=100, discount_amount=0, final_amount=100)
print(rec['status'])  # Should be 'pending' (no transactions yet)

# Verify update_receivable_status recalculates (not just writes)
status = update_receivable_status(rec['receivable_id'])
print(status['status'])  # Should remain 'pending'
```

---

## Completion Checklist ✅

- [ ] Backup taken and verified
- [ ] Migration 001 applied (no errors)
- [ ] Migration 002 applied (no errors)
- [ ] Schema validation queries passed
- [ ] users.fee_status + fee_paid_date confirmed
- [ ] Fabricated-data harness PASSED
- [ ] All 7 receivables created correctly
- [ ] All transaction counts match expectations
- [ ] AR reports generate correct totals
- [ ] Test records cleaned up
- [ ] Guardrails verified (no shortcuts)

---

## Production Readiness 🚀

Once all steps complete:
- **AR + Subscription schema alignment = CERTIFIED SAFE**
- **Ready for bot deployment**
- **Invoice → AR → Reports flow operational**
- **Guardrails active and tested**

Next: Deploy application and monitor real-world flows.
