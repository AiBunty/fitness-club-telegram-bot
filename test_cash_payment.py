#!/usr/bin/env python3
"""Test cash payment notification flow"""

import asyncio
from src.database.subscription_operations import (
    create_subscription_request, SUBSCRIPTION_PLANS
)
from src.handlers.admin_handlers import get_admin_ids

def test_cash_flow():
    print("Testing cash payment flow...\n")
    
    # Test 1: Get admin IDs
    print("1️⃣  Getting admin IDs...")
    admin_ids = get_admin_ids()
    print(f"   Admin IDs: {admin_ids}\n")
    
    if not admin_ids:
        print("   ⚠️  NO ADMINS FOUND! This is why no message is being sent.\n")
        print("   Solution: Set up an admin user first using set_admin_role.py")
        return
    
    # Test 2: Create subscription request
    print("2️⃣  Creating subscription request...")
    test_user_id = 1234567890
    test_plan_id = "plan_30"
    plan = SUBSCRIPTION_PLANS[test_plan_id]
    
    sub_request = create_subscription_request(
        test_user_id, 
        test_plan_id, 
        plan['amount'], 
        'cash'
    )
    print(f"   Subscription request created: {sub_request}\n")
    
    if sub_request:
        print("✅ Cash payment flow setup is correct")
        print("✅ Admin ID is configured")
        print("✅ Subscription request is created")
        print("\n📌 The message SHOULD be sent to admin when cash payment is selected in Telegram")
    else:
        print("❌ Failed to create subscription request")

if __name__ == "__main__":
    test_cash_flow()
