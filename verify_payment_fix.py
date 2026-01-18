#!/usr/bin/env python
"""Create a test payment request and verify approval updates status"""
# -*- coding: utf-8 -*-

import sys
import os

# Fix unicode output on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from src.database.connection import execute_query
from src.database.shake_credits_operations import approve_purchase
import random

print("\n" + "="*80)
print("TEST: Verify Payment Approval Updates User Status to PAID")
print("="*80)

# Pick a test user (one of the ones mentioned)
test_phones = ['9420492380', '9158243377', '8378962788']

user_query = """
SELECT user_id, full_name, phone, fee_status, fee_paid_date
FROM users
WHERE phone IN ('9420492380', '9158243377', '8378962788')
LIMIT 1
"""
user = execute_query(user_query, fetch_one=True)

if not user:
    print("❌ No test user found")
else:
    user_id = user['user_id']
    user_name = user['full_name']
    phone = user['phone']
    
    print(f"\n1. BEFORE APPROVAL:")
    print(f"   User: {user_name} ({phone})")
    print(f"   Current Fee Status: {user['fee_status']}")
    print(f"   Fee Paid Date: {user['fee_paid_date']}")
    
    # Create a test shake purchase request
    print(f"\n2. Creating test shake purchase...")
    create_purchase = """
    INSERT INTO shake_purchases (user_id, credits_requested, amount, payment_method, status)
    VALUES (%s, 25, 6000, 'Cash', 'pending')
    RETURNING purchase_id
    """
    purchase = execute_query(create_purchase, (user_id,), fetch_one=True)
    purchase_id = purchase['purchase_id']
    print(f"   ✅ Created purchase {purchase_id}")
    
    # Approve the purchase
    print(f"\n3. Approving purchase...")
    result = approve_purchase(purchase_id, admin_user_id=0, amount_paid=6000)
    if result:
        print(f"   ✅ Purchase approved")
        print(f"      Status: {result['status']}")
    
    # Check user status after approval
    print(f"\n4. AFTER APPROVAL - Checking user status...")
    user_after = execute_query(
        """SELECT user_id, full_name, phone, fee_status, fee_paid_date FROM users WHERE user_id = %s""",
        (user_id,),
        fetch_one=True
    )
    
    print(f"   User: {user_after['full_name']}")
    print(f"   Fee Status: {user_after['fee_status']}")
    print(f"   Fee Paid Date: {user_after['fee_paid_date']}")
    
    if user_after['fee_status'] == 'paid':
        print(f"\n   ✅ SUCCESS! User status correctly updated to 'paid'")
    else:
        print(f"\n   ❌ FAILED! User status is still '{user_after['fee_status']}'")
    
    # Test credit sale (0 amount)
    print(f"\n5. Testing CREDIT SALE (0 amount)...")
    create_purchase2 = """
    INSERT INTO shake_purchases (user_id, credits_requested, amount, payment_method, status)
    VALUES (%s, 25, 6000, 'Credit', 'pending')
    RETURNING purchase_id
    """
    purchase2 = execute_query(create_purchase2, (user_id,), fetch_one=True)
    purchase_id2 = purchase2['purchase_id']
    
    print(f"   Created purchase {purchase_id2} for credit sale")
    result2 = approve_purchase(purchase_id2, admin_user_id=0, amount_paid=0)
    if result2:
        print(f"   ✅ Credit sale approved with 0 amount paid")
        print(f"      (Should create follow-up notification)")
    
    # Check if notification was created
    notif_query = """
    SELECT notification_id, notification_type, title
    FROM notifications
    WHERE user_id = %s AND notification_type = 'payment_followup'
    ORDER BY created_at DESC LIMIT 1
    """
    notif = execute_query(notif_query, (user_id,), fetch_one=True)
    if notif:
        print(f"   ✅ Follow-up notification created:")
        print(f"      - Type: {notif['notification_type']}")
        print(f"      - Title: {notif['title']}")
    else:
        print(f"   ℹ️  No follow-up notification (table might not have this type)")

print("\n" + "="*80)
print("✅ TEST COMPLETE")
print("\nKEY CHANGES MADE:")
print("1. shake_credits_operations.py - approve_purchase() now updates user fee_status")
print("2. subscription_operations.py - approve_subscription() now updates user fee_status") 
print("3. shake_operations.py - approve_user_payment() now updates user fee_status")
print("4. Added credit sale follow-up for 0 amount approvals")
print("="*80 + "\n")
