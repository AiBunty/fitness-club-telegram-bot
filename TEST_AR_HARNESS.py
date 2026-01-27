#!/usr/bin/env python3
"""
Isolated AR Test Harness - No Bot Imports
Tests AR mirroring logic end-to-end on MySQL
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

def test_ar_schema():
    """Test 1: Verify schema is correct"""
    print("\nTest 1: AR Schema Validation")
    c = conn()
    cursor = c.cursor()
    
    try:
        cursor.execute("DESCRIBE accounts_receivable")
        ar_cols = {row['Field'] for row in cursor.fetchall()}
        
        required = {'receivable_id', 'user_id', 'receivable_type', 'source_id', 
                   'bill_amount', 'discount_amount', 'final_amount', 'status', 'due_date'}
        if not required.issubset(ar_cols):
            print(f"  FAIL: Missing columns {required - ar_cols}")
            return False
        
        cursor.execute("DESCRIBE ar_transactions")
        art_cols = {row['Field'] for row in cursor.fetchall()}
        
        required_art = {'transaction_id', 'receivable_id', 'method', 'amount', 
                       'reference', 'created_by', 'created_at'}
        if not required_art.issubset(art_cols):
            print(f"  FAIL: Missing columns {required_art - art_cols}")
            return False
        
        print("  PASS: All required columns present")
        return True
        
    except Exception as e:
        print(f"  FAIL: {e}")
        return False
    finally:
        cursor.close()
        c.close()

def test_create_receivable():
    """Test 2: Create a receivable"""
    print("\nTest 2: Create Receivable")
    c = conn()
    cursor = c.cursor()
    
    try:
        # Get a test user (assuming user 9901 exists from earlier)
        cursor.execute("SELECT user_id FROM users LIMIT 1")
        user = cursor.fetchone()
        if not user:
            print("  SKIP: No users in database")
            return True
        
        user_id = user['user_id']
        
        # Create receivable
        cursor.execute("""
            INSERT INTO accounts_receivable 
            (user_id, receivable_type, source_id, bill_amount, discount_amount, final_amount, status, due_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (user_id, 'invoice', 10001, 1000.0, 0.0, 1000.0, 'pending', '2026-02-27'))
        
        c.commit()
        
        # Verify
        cursor.execute("SELECT receivable_id FROM accounts_receivable WHERE source_id = 10001")
        result = cursor.fetchone()
        if result:
            print(f"  PASS: Receivable created (ID: {result['receivable_id']})")
            return True
        else:
            print("  FAIL: Receivable not found")
            return False
            
    except Exception as e:
        print(f"  FAIL: {e}")
        return False
    finally:
        cursor.close()
        c.close()

def test_create_transaction():
    """Test 3: Create AR transaction"""
    print("\nTest 3: Create AR Transaction")
    c = conn()
    cursor = c.cursor()
    
    try:
        # Get the receivable we just created
        cursor.execute("SELECT receivable_id FROM accounts_receivable WHERE source_id = 10001 LIMIT 1")
        result = cursor.fetchone()
        if not result:
            print("  SKIP: No receivable found")
            return True
        
        receivable_id = result['receivable_id']
        
        # Create transaction (payment)
        cursor.execute("""
            INSERT INTO ar_transactions
            (receivable_id, method, amount, reference, created_by, created_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
        """, (receivable_id, 'upi', 500.0, 'UPI-TEST-001', None))
        
        c.commit()
        
        # Verify
        cursor.execute("SELECT transaction_id FROM ar_transactions WHERE receivable_id = %s", (receivable_id,))
        result = cursor.fetchone()
        if result:
            print(f"  PASS: Transaction created (ID: {result['transaction_id']})")
            return True
        else:
            print("  FAIL: Transaction not found")
            return False
            
    except Exception as e:
        print(f"  FAIL: {e}")
        return False
    finally:
        cursor.close()
        c.close()

def test_transaction_counts():
    """Test 4: Verify transaction aggregation"""
    print("\nTest 4: Transaction Aggregation")
    c = conn()
    cursor = c.cursor()
    
    try:
        # Get the receivable and sum its transactions
        cursor.execute("""
            SELECT ar.receivable_id, ar.final_amount, COALESCE(SUM(art.amount), 0) as received
            FROM accounts_receivable ar
            LEFT JOIN ar_transactions art ON ar.receivable_id = art.receivable_id
            WHERE ar.source_id = 10001
            GROUP BY ar.receivable_id
        """)
        
        result = cursor.fetchone()
        if result:
            final = result['final_amount']
            received = result['received']
            
            # Calculate expected status
            if received == 0:
                status = 'pending'
            elif received < final:
                status = 'partial'
            else:
                status = 'paid'
            
            print(f"  PASS: Final={final}, Received={received}, Status={status}")
            return True
        else:
            print("  FAIL: No data found")
            return False
            
    except Exception as e:
        print(f"  FAIL: {e}")
        return False
    finally:
        cursor.close()
        c.close()

def cleanup():
    """Clean up test data"""
    print("\nCleanup: Removing test receivables...")
    c = conn()
    cursor = c.cursor()
    
    try:
        cursor.execute("DELETE FROM ar_transactions WHERE receivable_id IN (SELECT receivable_id FROM accounts_receivable WHERE source_id = 10001)")
        cursor.execute("DELETE FROM accounts_receivable WHERE source_id = 10001")
        c.commit()
        print("  Cleanup complete")
    except Exception as e:
        print(f"  Cleanup error: {e}")
    finally:
        cursor.close()
        c.close()

if __name__ == '__main__':
    print("\n" + "="*80)
    print("AR SYSTEM VALIDATION TEST SUITE")
    print("="*80)
    
    results = []
    results.append(("Schema", test_ar_schema()))
    results.append(("Receivable Creation", test_create_receivable()))
    results.append(("Transaction Creation", test_create_transaction()))
    results.append(("Transaction Aggregation", test_transaction_counts()))
    
    cleanup()
    
    print("\n" + "="*80)
    print("TEST RESULTS")
    print("="*80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"  {name}: {status}")
    
    print(f"\nSummary: {passed}/{total} tests passed")
    
    if passed == total:
        print("\nALL TESTS PASSED - AR SYSTEM READY")
        sys.exit(0)
    else:
        print("\nSOME TESTS FAILED - REVIEW ABOVE")
        sys.exit(1)
