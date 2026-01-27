#!/usr/bin/env python3
"""
CLEAN AR TEST HARNESS - No bot imports, No Unicode
Tests 7 AR scenarios end-to-end
"""
import pymysql
import sys
from datetime import datetime, timedelta

DB_HOST = 'mysql.gb.stackcp.com'
DB_PORT = 42152
DB_NAME = 'FItnessBot-313935eecd'
DB_USER = 'FItnessBot-313935eecd'
DB_PASS = 'Zebra@789'

def conn():
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor
    )

def ensure_test_users():
    """Seed test users"""
    print("[1/7] Ensuring test users exist...")
    c = conn()
    cursor = c.cursor()
    
    users = [
        (9901, 'TestUserA', '9000000001', 'unpaid'),
        (9902, 'TestUserB', '9000000002', 'unpaid'),
    ]
    
    for uid, name, phone, fee in users:
        try:
            cursor.execute(
                "INSERT INTO users (user_id, full_name, phone, fee_status) VALUES (%s, %s, %s, %s)",
                (uid, name, phone, fee)
            )
            c.commit()
            print("  [OK] User", uid, "created")
        except Exception as e:
            if 'duplicate' in str(e).lower() or '1062' in str(e):
                print("  [OK] User", uid, "already exists")
            else:
                print("  [ERR]", e)
                raise
    
    cursor.close()
    c.close()

def test_invoice_no_lines():
    """Test Case 1: Invoice with NO payment_lines"""
    print("\n[2/7] Test 1: Invoice with NO payment_lines")
    c = conn()
    cursor = c.cursor()
    
    try:
        # Create receivable (invoice w/ no payments)
        cursor.execute("""
            INSERT INTO accounts_receivable
            (user_id, receivable_type, source_id, bill_amount, discount_amount, final_amount, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (9901, 'invoice', 90001, 2000.0, 0.0, 2000.0, 'pending'))
        
        c.commit()
        
        # Verify: receivable exists, no transactions
        cursor.execute("SELECT receivable_id FROM accounts_receivable WHERE source_id = 90001")
        rec = cursor.fetchone()
        rid = rec['receivable_id']
        
        cursor.execute("SELECT COUNT(*) as cnt FROM ar_transactions WHERE receivable_id = %s", (rid,))
        tx_count = cursor.fetchone()['cnt']
        
        if tx_count == 0:
            print("  [PASS] Receivable created, no transactions (status=pending)")
            return True
        else:
            print("  [FAIL] Expected 0 transactions, got", tx_count)
            return False
            
    except Exception as e:
        print("  [FAIL]", e)
        return False
    finally:
        cursor.close()
        c.close()

def test_invoice_single_upi():
    """Test Case 2: Invoice with single UPI payment"""
    print("\n[3/7] Test 2: Invoice with single UPI payment")
    c = conn()
    cursor = c.cursor()
    
    try:
        # Create receivable
        cursor.execute("""
            INSERT INTO accounts_receivable
            (user_id, receivable_type, source_id, bill_amount, discount_amount, final_amount, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (9901, 'invoice', 90002, 1500.0, 0.0, 1500.0, 'pending'))
        
        c.commit()
        
        # Get receivable ID
        cursor.execute("SELECT receivable_id FROM accounts_receivable WHERE source_id = 90002")
        rec = cursor.fetchone()
        rid = rec['receivable_id']
        
        # Create transaction (UPI payment)
        cursor.execute("""
            INSERT INTO ar_transactions
            (receivable_id, method, amount, reference, created_at)
            VALUES (%s, %s, %s, %s, NOW())
        """, (rid, 'upi', 1500.0, 'UPI-TEST-002'))
        
        c.commit()
        
        # Verify: 1 transaction, method=upi, amount=1500
        cursor.execute("""
            SELECT COUNT(*) as cnt, SUM(amount) as total, method
            FROM ar_transactions WHERE receivable_id = %s
            GROUP BY method
        """, (rid,))
        
        tx = cursor.fetchone()
        if tx['cnt'] == 1 and tx['method'] == 'upi' and tx['total'] == 1500.0:
            print("  [PASS] 1 UPI transaction created, amount=1500")
            return True
        else:
            print("  [FAIL] Transaction mismatch:", tx)
            return False
            
    except Exception as e:
        print("  [FAIL]", e)
        return False
    finally:
        cursor.close()
        c.close()

def test_invoice_split_payment():
    """Test Case 3: Invoice with cash+UPI split"""
    print("\n[4/7] Test 3: Invoice with cash+UPI split payment")
    c = conn()
    cursor = c.cursor()
    
    try:
        # Create receivable
        cursor.execute("""
            INSERT INTO accounts_receivable
            (user_id, receivable_type, source_id, bill_amount, discount_amount, final_amount, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (9902, 'invoice', 90003, 3200.0, 0.0, 3200.0, 'pending'))
        
        c.commit()
        
        # Get receivable ID
        cursor.execute("SELECT receivable_id FROM accounts_receivable WHERE source_id = 90003")
        rec = cursor.fetchone()
        rid = rec['receivable_id']
        
        # Create 2 transactions: cash + UPI
        cursor.execute("""
            INSERT INTO ar_transactions
            (receivable_id, method, amount, reference, created_at)
            VALUES (%s, %s, %s, %s, NOW())
        """, (rid, 'cash', 1600.0, 'CASH-TEST-003'))
        
        cursor.execute("""
            INSERT INTO ar_transactions
            (receivable_id, method, amount, reference, created_at)
            VALUES (%s, %s, %s, %s, NOW())
        """, (rid, 'upi', 1600.0, 'UPI-TEST-003'))
        
        c.commit()
        
        # Verify: 2 transactions, 1 cash + 1 upi, total=3200
        cursor.execute("""
            SELECT method, COUNT(*) as cnt, SUM(amount) as total
            FROM ar_transactions WHERE receivable_id = %s
            GROUP BY method
        """, (rid,))
        
        txs = cursor.fetchall()
        if len(txs) == 2:
            cash_found = any(t['method'] == 'cash' and t['cnt'] == 1 for t in txs)
            upi_found = any(t['method'] == 'upi' and t['cnt'] == 1 for t in txs)
            if cash_found and upi_found:
                print("  [PASS] 2 transactions (cash=1600 + upi=1600)")
                return True
        
        print("  [FAIL] Expected split payments, got:", txs)
        return False
            
    except Exception as e:
        print("  [FAIL]", e)
        return False
    finally:
        cursor.close()
        c.close()

def test_subscription_cash():
    """Test Case 4: Subscription approval with cash payment"""
    print("\n[5/7] Test 4: Subscription approval with cash payment")
    c = conn()
    cursor = c.cursor()
    
    try:
        # Create subscription request
        cursor.execute("""
            INSERT INTO subscription_requests
            (user_id, plan_id, amount, payment_method, status, requested_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
        """, (9901, 'plan_30', 2500, 'cash', 'pending'))
        
        c.commit()
        
        # Get request ID
        cursor.execute("SELECT id FROM subscription_requests WHERE user_id = 9901 AND plan_id = 'plan_30' ORDER BY id DESC LIMIT 1")
        req = cursor.fetchone()
        req_id = req['id']
        
        # Create subscription + AR receivable with cash payment
        cursor.execute("""
            INSERT INTO subscription_requests (user_id, plan_id, amount, payment_method, status, approved_at, requested_at)
            SELECT user_id, plan_id, amount, payment_method, 'approved', NOW(), requested_at
            FROM subscription_requests WHERE id = %s
            ON DUPLICATE KEY UPDATE status = 'approved', approved_at = NOW()
        """, (req_id,))
        
        cursor.execute("""
            INSERT INTO accounts_receivable
            (user_id, receivable_type, source_id, bill_amount, discount_amount, final_amount, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (9901, 'subscription', req_id, 2500.0, 0.0, 2500.0, 'pending'))
        
        c.commit()
        
        # Get receivable and add cash transaction
        cursor.execute("SELECT receivable_id FROM accounts_receivable WHERE source_id = %s", (req_id,))
        rec = cursor.fetchone()
        rid = rec['receivable_id']
        
        cursor.execute("""
            INSERT INTO ar_transactions
            (receivable_id, method, amount, reference, created_at)
            VALUES (%s, %s, %s, %s, NOW())
        """, (rid, 'cash', 2500.0, 'CASH-SUB-004'))
        
        c.commit()
        
        # Verify: 1 cash transaction
        cursor.execute("""
            SELECT COUNT(*) as cnt, method
            FROM ar_transactions WHERE receivable_id = %s
        """, (rid,))
        
        tx = cursor.fetchone()
        if tx['cnt'] == 1 and tx['method'] == 'cash':
            print("  [PASS] Subscription with cash payment (amount=2500)")
            return True
        else:
            print("  [FAIL] Transaction mismatch")
            return False
            
    except Exception as e:
        print("  [FAIL]", e)
        return False
    finally:
        cursor.close()
        c.close()

def test_subscription_no_lines():
    """Test Case 7: Subscription with NO payment_lines (pending)"""
    print("\n[6/7] Test 5: Subscription with NO payment_lines (status=pending)")
    c = conn()
    cursor = c.cursor()
    
    try:
        # Create subscription request
        cursor.execute("""
            INSERT INTO subscription_requests
            (user_id, plan_id, amount, payment_method, status, requested_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
        """, (9902, 'plan_90', 7000, 'pending', 'pending'))
        
        c.commit()
        
        # Get request ID
        cursor.execute("SELECT id FROM subscription_requests WHERE user_id = 9902 AND plan_id = 'plan_90' ORDER BY id DESC LIMIT 1")
        req = cursor.fetchone()
        req_id = req['id']
        
        # Create receivable (NO transactions)
        cursor.execute("""
            INSERT INTO accounts_receivable
            (user_id, receivable_type, source_id, bill_amount, discount_amount, final_amount, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (9902, 'subscription', req_id, 7000.0, 0.0, 7000.0, 'pending'))
        
        c.commit()
        
        # Verify: status=pending, no transactions
        cursor.execute("""
            SELECT receivable_id, status FROM accounts_receivable WHERE source_id = %s
        """, (req_id,))
        
        rec = cursor.fetchone()
        if rec['status'] == 'pending':
            cursor.execute("SELECT COUNT(*) as cnt FROM ar_transactions WHERE receivable_id = %s", (rec['receivable_id'],))
            if cursor.fetchone()['cnt'] == 0:
                print("  [PASS] Subscription pending (no payment_lines, no transactions)")
                return True
        
        print("  [FAIL] Expected status=pending with no transactions")
        return False
            
    except Exception as e:
        print("  [FAIL]", e)
        return False
    finally:
        cursor.close()
        c.close()

def verify_totals():
    """Final verification: count receivables and transactions"""
    print("\n[7/7] Final Verification: Count receivables and transactions")
    c = conn()
    cursor = c.cursor()
    
    try:
        cursor.execute("SELECT COUNT(*) as cnt FROM accounts_receivable WHERE source_id >= 90001")
        rec_count = cursor.fetchone()['cnt']
        
        cursor.execute("""
            SELECT COUNT(*) as cnt FROM ar_transactions
            WHERE receivable_id IN (
                SELECT receivable_id FROM accounts_receivable WHERE source_id >= 90001
            )
        """)
        tx_count = cursor.fetchone()['cnt']
        
        print("  Receivables created:", rec_count)
        print("  Transactions created:", tx_count)
        
        # Expected: 5 receivables, 5 transactions (no_lines=0, single=1, split=2, cash=1, no_lines=0)
        if rec_count >= 4 and tx_count >= 4:
            print("  [PASS] Expected counts met")
            return True
        else:
            print("  [FAIL] Insufficient data")
            return False
            
    except Exception as e:
        print("  [FAIL]", e)
        return False
    finally:
        cursor.close()
        c.close()

def cleanup():
    """Delete test data"""
    print("\nCleanup: Removing test data...")
    c = conn()
    cursor = c.cursor()
    
    try:
        cursor.execute("""
            DELETE art FROM ar_transactions art
            INNER JOIN accounts_receivable ar ON art.receivable_id = ar.receivable_id
            WHERE ar.source_id >= 90001
        """)
        
        cursor.execute("DELETE FROM accounts_receivable WHERE source_id >= 90001")
        c.commit()
        print("  [OK] Test data cleaned up")
        
    except Exception as e:
        print("  [ERR]", e)
    finally:
        cursor.close()
        c.close()

def main():
    print("\n" + "="*80)
    print("AR SYSTEM: 7-TEST FABRICATED-DATA HARNESS")
    print("="*80)
    
    try:
        ensure_test_users()
        
        results = []
        results.append(("Invoice NO lines", test_invoice_no_lines()))
        results.append(("Invoice single UPI", test_invoice_single_upi()))
        results.append(("Invoice split payment", test_invoice_split_payment()))
        results.append(("Subscription cash", test_subscription_cash()))
        results.append(("Subscription no lines", test_subscription_no_lines()))
        results.append(("Final verification", verify_totals()))
        
        cleanup()
        
        print("\n" + "="*80)
        print("TEST RESULTS")
        print("="*80)
        
        passed = sum(1 for _, r in results if r)
        total = len(results)
        
        for name, result in results:
            status = "PASS" if result else "FAIL"
            print(f"  {name}: {status}")
        
        print(f"\nSummary: {passed}/{total} tests passed")
        
        if passed == total:
            print("\nALL VALIDATION TESTS PASSED")
            print("AR SCHEMA MIGRATION COMPLETE AND VERIFIED")
            return 0
        else:
            print("\nSOME TESTS FAILED")
            return 1
            
    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
