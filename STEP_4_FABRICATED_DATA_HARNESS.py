#!/usr/bin/env python3
"""
STEP 4: Fabricated-Data Validation Harness
Run AFTER migrations (001, 002) applied and schema validated.

Purpose:
- Seed test users, invoices, subscriptions
- Confirm AR mirroring logic works end-to-end
- Validate payment_lines behavior
- Verify /ar_reports outputs

Test Cases:
  Invoice A: no payment_lines → receivable only, no ar_transactions
  Invoice B: single UPI → 1 ar_transaction (method='upi')
  Invoice C: cash+UPI split → 2 ar_transactions (cash + upi)
  Sub 1: Approval with cash payment_lines → 1 ar_transaction (method='cash')
  Sub 2: Approval with UPI payment_lines → 1 ar_transaction (method='upi')
  Sub 3: Approval with split (cash+upi) → 2 ar_transactions
  Sub 4: Approval with no payment_lines → receivable only, status='pending'

Cleanup:
  - Mark all test records with source_id = 9999 (tag-based)
  - Delete marked records at end
"""

import os
import json
import sys
import datetime
from pathlib import Path

# Force MySQL mode (no SQLite)
os.environ['USE_LOCAL_DB'] = 'false'
os.environ['USE_REMOTE_DB'] = 'true'

import importlib
import src.config as config
importlib.reload(config)

from src.database.connection import execute_query, get_db_cursor
from src.invoices_v2.handlers import ensure_payment_tracking_fields, load_invoices, save_invoices
from src.database.subscription_operations import approve_subscription
from src.database.ar_operations import (
    create_receivable,
    create_transactions,
    get_receivable_by_source,
    update_receivable_status,
)

print(f"\n{'='*80}")
print("STEP 4: FABRICATED-DATA VALIDATION HARNESS")
print(f"{'='*80}")
print(f"Mode: {config.ENV} | USE_REMOTE_DB: {config.USE_REMOTE_DB}")
print(f"Database: {config.DATABASE_CONFIG['host']}:{config.DATABASE_CONFIG['port']}")
print(f"{'='*80}\n")

# Test user IDs (use high numbers to avoid collisions)
TEST_USER_A = 9901
TEST_USER_B = 9902
TEST_ADMIN = 9001
TAG_SOURCE_ID = 9999  # All test records tagged with this

def ensure_test_users():
    """Seed test users into users table."""
    print("[1/7] Ensuring test users exist...")
    users = [
        (TEST_USER_A, 'Test_User_A', '+91-9000-0001', 'unpaid'),
        (TEST_USER_B, 'Test_User_B', '+91-9000-0002', 'unpaid'),
    ]
    for uid, name, phone, fee_status in users:
        try:
            execute_query(
                "INSERT INTO users (user_id, full_name, phone, fee_status) VALUES (%s, %s, %s, %s)",
                (uid, name, phone, fee_status)
            )
            print(f"  ✓ User {uid} ({name}) created")
        except Exception as e:
            if 'duplicate' in str(e).lower():
                print(f"  ✓ User {uid} already exists")
            else:
                print(f"  ✗ Error creating user {uid}: {e}")
                raise

def test_invoices():
    """Test invoice → AR mirroring."""
    print("\n[2/7] Testing invoice payment confirmation...")
    
    now = datetime.datetime.now().isoformat()
    
    # Invoice A: no payment_lines
    inv_a = ensure_payment_tracking_fields({
        'invoice_id': f'TEST-INV-A-{TAG_SOURCE_ID}',
        'user_id': TEST_USER_A,
        'user_name': 'Test_User_A',
        'items': [],
        'items_subtotal': 0,
        'shipping': 0,
        'gst_total': 0,
        'final_total': 1500,
        'created_by': TEST_ADMIN,
        'created_at': now,
        'payment_lines': [],  # EMPTY
    })
    
    # Invoice B: single UPI
    inv_b = ensure_payment_tracking_fields({
        'invoice_id': f'TEST-INV-B-{TAG_SOURCE_ID}',
        'user_id': TEST_USER_A,
        'user_name': 'Test_User_A',
        'items': [],
        'items_subtotal': 0,
        'shipping': 0,
        'gst_total': 0,
        'final_total': 1200,
        'created_by': TEST_ADMIN,
        'created_at': now,
        'payment_lines': [
            {'amount': 1200, 'payment_method': 'upi', 'reference': 'UPI-TEST-INV-B', 'confirmed_by_admin_id': None, 'confirmed_at': None}
        ],
    })
    
    # Invoice C: cash+UPI split
    inv_c = ensure_payment_tracking_fields({
        'invoice_id': f'TEST-INV-C-{TAG_SOURCE_ID}',
        'user_id': TEST_USER_A,
        'user_name': 'Test_User_A',
        'items': [],
        'items_subtotal': 0,
        'shipping': 0,
        'gst_total': 0,
        'final_total': 1500,
        'created_by': TEST_ADMIN,
        'created_at': now,
        'payment_lines': [
            {'amount': 700, 'payment_method': 'cash', 'reference': 'CASH-TEST-INV-C', 'confirmed_by_admin_id': None, 'confirmed_at': None},
            {'amount': 800, 'payment_method': 'upi', 'reference': 'UPI-TEST-INV-C', 'confirmed_by_admin_id': None, 'confirmed_at': None}
        ],
    })
    
    def confirm_invoice(invoice):
        """Mirror invoice payment confirmation logic."""
        confirmation_ts = datetime.datetime.now().isoformat()
        invoice = ensure_payment_tracking_fields(dict(invoice))
        user_id = invoice.get('user_id')
        amount = float(invoice.get('final_total', 0))
        due_date = invoice.get('due_date')
        
        try:
            source_id = int(invoice.get('invoice_id').split('-')[-2])
        except Exception:
            source_id = TAG_SOURCE_ID
        
        payment_lines = invoice.get('payment_lines') or []
        pending_lines = []
        for line in payment_lines:
            method = line.get('payment_method') or line.get('method')
            amt = float(line.get('amount', 0)) if isinstance(line, dict) else 0
            if not method or amt <= 0:
                continue
            if line.get('confirmed_at'):
                continue
            pending_lines.append({'method': method, 'amount': amt, 'reference': line.get('reference')})
        
        receivable = {}
        rid = None
        if user_id:
            receivable = get_receivable_by_source('invoice', source_id) if source_id is not None else {}
            if not receivable:
                receivable = create_receivable(
                    user_id=user_id, receivable_type='invoice', source_id=source_id,
                    bill_amount=amount, discount_amount=0.0, final_amount=amount, due_date=due_date
                )
            rid = receivable.get('receivable_id') if receivable else None
            if rid:
                if pending_lines:
                    create_transactions(rid, pending_lines, admin_user_id=TEST_ADMIN)
                update_receivable_status(rid)
                invoice['receivable_id'] = rid
        
        confirmed_amount = 0
        for line in payment_lines:
            method = line.get('payment_method') or line.get('method')
            amt = float(line.get('amount', 0)) if isinstance(line, dict) else 0
            if not method or amt <= 0:
                continue
            if line.get('confirmed_at'):
                confirmed_amount += amt
                continue
            line['confirmed_by_admin_id'] = TEST_ADMIN
            line['confirmed_at'] = confirmation_ts
            confirmed_amount += amt
        
        invoice['paid_amount'] = round(confirmed_amount, 2)
        if invoice['paid_amount'] >= invoice.get('final_total', 0):
            invoice['payment_status'] = 'paid'
        elif invoice['paid_amount'] > 0:
            invoice['payment_status'] = 'partial'
        else:
            invoice['payment_status'] = invoice.get('payment_status', 'pending_verification')
        if invoice['paid_amount'] > 0:
            invoice['paid_at'] = confirmation_ts
            invoice['verified_by'] = TEST_ADMIN
        return invoice
    
    inv_a = confirm_invoice(inv_a)
    inv_b = confirm_invoice(inv_b)
    inv_c = confirm_invoice(inv_c)
    
    print(f"  ✓ Invoice A confirmed (no lines) → receivable_id={inv_a.get('receivable_id')}")
    print(f"  ✓ Invoice B confirmed (1 UPI) → receivable_id={inv_b.get('receivable_id')}")
    print(f"  ✓ Invoice C confirmed (cash+UPI) → receivable_id={inv_c.get('receivable_id')}")
    
    return [inv_a, inv_b, inv_c]

def test_subscriptions():
    """Test subscription approvals with various payment_lines."""
    print("\n[3/7] Testing subscription approvals...")
    
    # Create subscription requests
    reqs = []
    for i, method in enumerate(['cash', 'upi', 'split', 'none']):
        r = execute_query(
            "INSERT INTO subscription_requests (user_id, plan_id, amount, payment_method, status, requested_at) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id, user_id, plan_id, amount, status",
            (TEST_USER_B, 'plan_30', 2500, method, 'pending', datetime.datetime.now()),
            fetch_one=True
        )
        reqs.append(r)
    
    # Approval 1: Cash
    approve_subscription(
        reqs[0]['id'],
        amount=2500,
        end_date=datetime.datetime.now() + datetime.timedelta(days=30),
        payment_lines=[{'method': 'cash', 'amount': 2500, 'reference': 'TEST-CASH-SUB'}],
        admin_user_id=TEST_ADMIN
    )
    print(f"  ✓ Subscription 1 approved (cash) → request_id={reqs[0]['id']}")
    
    # Approval 2: UPI
    approve_subscription(
        reqs[1]['id'],
        amount=2500,
        end_date=datetime.datetime.now() + datetime.timedelta(days=30),
        payment_lines=[{'method': 'upi', 'amount': 2500, 'reference': 'TEST-UPI-SUB'}],
        admin_user_id=TEST_ADMIN
    )
    print(f"  ✓ Subscription 2 approved (UPI) → request_id={reqs[1]['id']}")
    
    # Approval 3: Split (cash+UPI)
    approve_subscription(
        reqs[2]['id'],
        amount=2500,
        end_date=datetime.datetime.now() + datetime.timedelta(days=30),
        payment_lines=[
            {'method': 'cash', 'amount': 1000, 'reference': 'TEST-SPLIT-CASH'},
            {'method': 'upi', 'amount': 1500, 'reference': 'TEST-SPLIT-UPI'}
        ],
        admin_user_id=TEST_ADMIN
    )
    print(f"  ✓ Subscription 3 approved (split) → request_id={reqs[2]['id']}")
    
    # Approval 4: No payment_lines
    approve_subscription(
        reqs[3]['id'],
        amount=2500,
        end_date=datetime.datetime.now() + datetime.timedelta(days=30),
        payment_lines=[],  # EMPTY
        admin_user_id=TEST_ADMIN
    )
    print(f"  ✓ Subscription 4 approved (no lines) → request_id={reqs[3]['id']}")

def validate_ar_data():
    """Validate AR tables match expectations."""
    print("\n[4/7] Validating AR data...")
    
    receivables = execute_query(
        "SELECT receivable_id, receivable_type, source_id, user_id, final_amount, status FROM accounts_receivable ORDER BY receivable_id"
    )
    transactions = execute_query(
        "SELECT transaction_id, receivable_id, method, amount, reference FROM ar_transactions ORDER BY receivable_id, transaction_id"
    )
    
    print(f"\n  Receivables ({len(receivables)}):")
    for r in receivables:
        print(f"    ID {r['receivable_id']}: type={r['receivable_type']}, source={r['source_id']}, user={r['user_id']}, amt={r['final_amount']}, status={r['status']}")
    
    print(f"\n  Transactions ({len(transactions)}):")
    for t in transactions:
        print(f"    ID {t['transaction_id']}: receivable={t['receivable_id']}, method={t['method']}, amt={t['amount']}, ref={t['reference']}")
    
    # Validate counts
    invoices_with_txn = len([r for r in receivables if r['receivable_type'] == 'invoice' and r['source_id'] != TAG_SOURCE_ID and r['source_id'] != 9999 or (r['source_id'] == TAG_SOURCE_ID or '9999' in str(r['source_id']))])
    subs_with_txn = len([r for r in receivables if r['receivable_type'] == 'subscription'])
    
    # Expected:
    # - Invoice A: 1 receivable, 0 transactions (status='pending')
    # - Invoice B: 1 receivable, 1 transaction (status='paid')
    # - Invoice C: 1 receivable, 2 transactions (status='paid')
    # - Sub1: 1 receivable, 1 transaction (cash)
    # - Sub2: 1 receivable, 1 transaction (upi)
    # - Sub3: 1 receivable, 2 transactions (split)
    # - Sub4: 1 receivable, 0 transactions (status='pending')
    
    expected_receivables = 7
    expected_transactions = 0 + 1 + 2 + 1 + 1 + 2 + 0  # 7
    
    assert len(receivables) == expected_receivables, f"Expected {expected_receivables} receivables, got {len(receivables)}"
    assert len(transactions) == expected_transactions, f"Expected {expected_transactions} transactions, got {len(transactions)}"
    
    print(f"\n  ✓ Receivable count: {len(receivables)} (expected {expected_receivables})")
    print(f"  ✓ Transaction count: {len(transactions)} (expected {expected_transactions})")

def validate_ar_reports():
    """Validate /ar_reports outputs."""
    print("\n[5/7] Validating AR reports...")
    
    # Totals by method
    method_totals = execute_query(
        "SELECT method, SUM(amount) as total FROM ar_transactions GROUP BY method ORDER BY method"
    )
    print(f"\n  Payment Method Breakdown:")
    for row in method_totals:
        print(f"    {row['method']}: ₹{row['total']}")
    
    # Outstanding
    outstanding = execute_query(
        "SELECT receivable_id, status, final_amount, (final_amount - COALESCE((SELECT SUM(amount) FROM ar_transactions t WHERE t.receivable_id=ar.receivable_id),0)) AS balance FROM accounts_receivable ar ORDER BY receivable_id"
    )
    print(f"\n  Outstanding by Receivable:")
    for row in outstanding:
        print(f"    ID {row['receivable_id']}: status={row['status']}, ₹{row['balance']} outstanding")
    
    # Verify no paid items have balance
    for row in outstanding:
        if row['status'] == 'paid':
            assert row['balance'] == 0, f"Receivable {row['receivable_id']} marked paid but has balance ₹{row['balance']}"
    print(f"  ✓ All paid receivables have zero balance")

def cleanup_test_records():
    """Delete all test records (tag-based)."""
    print("\n[6/7] Cleaning up test records...")
    
    # Delete subscription tables (child → parent)
    sub_del = execute_query("DELETE FROM subscription_payments WHERE user_id IN (%s, %s)", (TEST_USER_A, TEST_USER_B))
    sub_del = execute_query("DELETE FROM subscriptions WHERE user_id IN (%s, %s)", (TEST_USER_A, TEST_USER_B))
    sub_del = execute_query("DELETE FROM subscription_requests WHERE user_id IN (%s, %s)", (TEST_USER_A, TEST_USER_B))
    
    # Delete AR tables (child → parent)
    art_del = execute_query("DELETE FROM ar_transactions WHERE receivable_id IN (SELECT receivable_id FROM accounts_receivable WHERE user_id IN (%s, %s))", (TEST_USER_A, TEST_USER_B))
    ar_del = execute_query("DELETE FROM accounts_receivable WHERE user_id IN (%s, %s)", (TEST_USER_A, TEST_USER_B))
    
    # Delete users
    user_del = execute_query("DELETE FROM users WHERE user_id IN (%s, %s)", (TEST_USER_A, TEST_USER_B))
    
    print(f"  ✓ Cleanup complete (test users and related records deleted)")

def main():
    try:
        ensure_test_users()
        invoices = test_invoices()
        test_subscriptions()
        validate_ar_data()
        validate_ar_reports()
        cleanup_test_records()
        
        print(f"\n{'='*80}")
        print("✓ ALL VALIDATION TESTS PASSED")
        print(f"{'='*80}\n")
        return 0
    except AssertionError as e:
        print(f"\n✗ VALIDATION FAILED: {e}\n")
        return 1
    except Exception as e:
        print(f"\n✗ ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
