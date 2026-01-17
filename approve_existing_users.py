#!/usr/bin/env python3
"""
Script to approve existing users who are stuck with pending status
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from src.database.connection import execute_query
from src.database.user_operations import approve_user

# User IDs to approve
user_ids_to_approve = [
    7639647487,  # Sameer Anil Bhalerao
    1980219847,  # Dhawal
    1206519616,  # Parin
    6133468540,  # Sayali Sunil Wani
]

print("🔄 Approving existing users...\n")

for user_id in user_ids_to_approve:
    try:
        # Get user info first
        user = execute_query(
            "SELECT full_name, approval_status FROM users WHERE user_id = %s",
            (user_id,),
            fetch_one=True
        )
        
        if not user:
            print(f"❌ User {user_id}: Not found in database")
            continue
        
        print(f"👤 {user['full_name']} (ID: {user_id})")
        print(f"   Current Status: {user['approval_status']}")
        
        if user['approval_status'] == 'approved':
            print(f"   ✅ Already approved")
        else:
            # Approve the user
            approve_user(user_id, 0)  # 0 = system admin
            print(f"   ✅ Status changed to: approved")
        
        print()
    
    except Exception as e:
        print(f"❌ Error processing user {user_id}: {e}\n")

print("✅ All users processed!")

# Verify the changes
print("\n📋 Verification - Current status:")
print("─" * 50)

for user_id in user_ids_to_approve:
    try:
        user = execute_query(
            "SELECT full_name, approval_status FROM users WHERE user_id = %s",
            (user_id,),
            fetch_one=True
        )
        
        if user:
            status_icon = "✅" if user['approval_status'] == 'approved' else "❌"
            print(f"{status_icon} {user['full_name']}: {user['approval_status']}")
    except Exception as e:
        print(f"Error verifying {user_id}: {e}")

print("\n✅ Script complete! Users should now be able to access the app.")
print("⏱️  They may need to send /start or /menu to refresh their session.")
