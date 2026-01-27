# MySQL Schema Migration Summary

## 🎯 Objective
Align MySQL schema with application code expectations (ar_operations.py, subscription_operations.py, invoices_v2/handlers.py).

## 🔒 Architecture Locked
- **Database**: MySQL Cloud only (no SQLite/Postgres abstraction)
- **AR Master of Truth**: No implicit payments; status always derived from transactions
- **Invoices**: Touch AR only on payment confirmation, never on creation
- **Reports**: Read-only, based on receivables + transactions

---

## 📋 Migration Files

### `001_fix_ar_schema.sql`
**Recreates**:
- `accounts_receivable` (new columns: receivable_id, receivable_type, source_id, bill_amount, discount_amount, final_amount, created_at, updated_at)
- `ar_transactions` (new columns: receivable_id, method, reference, created_by, created_at)

**Assumptions**:
- Old AR tables data is superseded; not migrated
- `users` table already exists
- Foreign keys: user_id → users, receivable_id → accounts_receivable

**Key Changes**:
| Old | New | Reason |
|-----|-----|--------|
| `ar_id` | `receivable_id` | Application expects `receivable_id` |
| No `receivable_type` | `receivable_type` (enum: invoice, subscription) | Required to link to source entity |
| No `source_id` | `source_id` | Foreign reference to invoice_id or subscription_request_id |
| `amount_due` | `bill_amount`, `discount_amount`, `final_amount` | Supports discount tracking |
| No `created_at/updated_at` | Added both, auto-managed | Audit trail |
| `ar_transactions.user_id` | `ar_transactions.receivable_id` + method, reference, created_by | Normalized to receivable; tracks payment method and admin |
| No `method` in ar_transactions | `method` (enum: cash, upi) | Required for payment_lines mirroring |

**Statuses** (derived from transactions, not hardcoded):
- `pending`: no transactions yet (received = 0)
- `partial`: sum(ar_transactions.amount) < final_amount
- `paid`: sum(ar_transactions.amount) >= final_amount

---

### `002_fix_subscription_schema.sql`
**Recreates**:
- `subscription_requests`
- `subscriptions`
- `subscription_payments`

**Assumptions**:
- Old subscription tables data is superseded
- `users` table already exists
- plan_id is TEXT (plan_30, plan_90, plan_180), not INT
- Foreign keys: user_id → users, request_id → subscription_requests

**Key Changes**:
| Old | New | Reason |
|-----|-----|--------|
| `request_id` → `id` | Standardized PK name | Application code expects `id` |
| `plan_id` (INT) | `plan_id` (VARCHAR) | Code uses string constants (plan_30, etc.) |
| No `amount` | `amount` (DOUBLE) | Required for AR mirroring |
| No `payment_method` | `payment_method` (enum: cash, upi, manual) | Required for approval flows |
| No `approved_at` | `approved_at` (TIMESTAMP NULL) | Audit timestamp |
| No `fee_status` | `fee_status` (VARCHAR) | Optional fee tracking |
| `subscription_id` → `id` | Standardized PK | Consistency |
| No `amount` | `amount` (DOUBLE) | Required for payment tracking |
| No `grace_period_end` | `grace_period_end` (DATETIME) | 7-day grace after expiry |
| `payment_id` → `id` | Standardized PK | Consistency |
| `subscription_id` → `request_id` | FK to subscription_requests | Links payment to approval flow |
| No `user_id` | `user_id` (INT) | Direct link for queries |
| No `reference` | `reference` (VARCHAR) | Payment reference tracking |
| No `paid_at` | `paid_at` (TIMESTAMP NULL) | Audit timestamp |

---

## 🚨 Migration Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Data loss (old AR) | **Backup MySQL before running migrations** |
| Foreign key constraint errors | Drop tables in correct order (child → parent) |
| Existing rows with unsupported plan_id | No existing production subscriptions; safe to recreate |

---

## ✅ Validation Checklist (Post-Migration)

After running both migrations on Cloud MySQL:

### 1. Schema Validation
```sql
-- Verify accounts_receivable columns
DESCRIBE accounts_receivable;
-- Expected: receivable_id, user_id, receivable_type, source_id, bill_amount, discount_amount, final_amount, status, due_date, created_at, updated_at

-- Verify ar_transactions columns
DESCRIBE ar_transactions;
-- Expected: transaction_id, receivable_id, method, amount, reference, created_by, created_at

-- Verify subscription_requests columns
DESCRIBE subscription_requests;
-- Expected: id, user_id, plan_id, amount, payment_method, status, requested_at, approved_at, rejection_reason, fee_status

-- Verify subscriptions columns
DESCRIBE subscriptions;
-- Expected: id, user_id, plan_id, amount, start_date, end_date, status, grace_period_end, created_at, updated_at

-- Verify subscription_payments columns
DESCRIBE subscription_payments;
-- Expected: id, user_id, request_id, amount, payment_method, reference, screenshot_file_id, status, paid_at, created_at
```

### 2. Functional Validation (Using Fabricated Data)
After schema validated, run the checklist (see below).

---

## 🎬 Next Steps

1. **Backup Cloud MySQL** (mandatory)
2. **Execute** `001_fix_ar_schema.sql` on Cloud DB
3. **Execute** `002_fix_subscription_schema.sql` on Cloud DB
4. **Run schema validation** queries above
5. **Run fabricated-data checklist** (once schema confirmed):
   - **Invoice A** (no payment_lines) → receivable only, no transactions
   - **Invoice B** (single UPI) → 1 ar_transactions row
   - **Invoice C** (cash+UPI split) → 2 ar_transactions rows
   - **Subscription Cash** → 1 ar_transactions row (method='cash')
   - **Subscription UPI** → 1 ar_transactions row (method='upi')
   - **Subscription Split** → 2 ar_transactions rows (cash+upi)
   - **Subscription No Lines** → receivable only, no transactions (status='pending')
   - **Verify** /ar_reports totals match sums
   - **Cleanup** marked test records
