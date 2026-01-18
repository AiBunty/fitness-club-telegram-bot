#!/usr/bin/env python3
"""
Diagnostic script to check subscription status
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from src.database.connection import execute_query
from src.database.subscription_operations import is_subscription_active, get_user_subscription

# Check the 4 approved users
user_ids = [
    7639647487,  # Sameer
    1980219847,  # Dhawal
    1206519616,  # Parin
    6133468540,  # Sayali
]

print("🔍 SUBSCRIPTION DIAGNOSTIC CHECK")
print("=" * 70)

for user_id in user_ids:
    print(f"\n👤 User ID: {user_id}")
    print("-" * 70)
    
    try:
        # Get user info
        user = execute_query(
            "SELECT full_name, approval_status FROM users WHERE user_id = %s",
            (user_id,),
            fetch_one=True
        )
        
        if user:
            print(f"   Name: {user['full_name']}")
            print(f"   Approval Status: {user['approval_status']}")
        
        # Check subscription
        sub = execute_query(
            "SELECT * FROM subscriptions WHERE user_id = %s ORDER BY id DESC LIMIT 1",
            (user_id,),
            fetch_one=True
        )
        
        if not sub:
            print(f"   ❌ NO SUBSCRIPTION RECORD FOUND")
        else:
            print(f"   ✅ Subscription Found:")
            print(f"      ID: {sub['id']}")
            print(f"      Status: {sub['status']}")
            print(f"      Plan ID: {sub['plan_id']}")
            print(f"      Amount: Rs. {sub['amount']}")
            print(f"      Start Date: {sub['start_date']}")
            print(f"      End Date: {sub['end_date']}")
            print(f"      Grace Period End: {sub['grace_period_end']}")
            
            # Check if it's active
            now = datetime.now()
            print(f"\n   📅 Date Analysis:")
            print(f"      Current Time: {now}")
            print(f"      End Date: {sub['end_date']}")
            print(f"      Now <= End Date?: {now <= sub['end_date']}")
            print(f"      Status Check: {sub['status']} == 'active'? {sub['status'] == 'active'}")
            
            # Final check
            is_active = is_subscription_active(user_id)
            print(f"\n   🎯 is_subscription_active() result: {is_active}")
        
        # Check pending subscription requests
        pending_req = execute_query(
            "SELECT * FROM subscription_requests WHERE user_id = %s ORDER BY id DESC LIMIT 1",
            (user_id,),
            fetch_one=True
        )
        
        if pending_req:
            print(f"\n   📋 Latest Subscription Request:")
            print(f"      Request ID: {pending_req['id']}")
            print(f"      Status: {pending_req['status']}")
            print(f"      Amount: Rs. {pending_req['amount']}")
            print(f"      Created: {pending_req['created_at']}")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")

print("\n" + "=" * 70)
print("✅ Diagnostic complete!")
