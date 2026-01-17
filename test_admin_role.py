"""
Test script to verify admin role checking
"""
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from src.database.role_operations import get_user_role, is_admin, is_staff, is_user

USER_ID = 424837855

print("=" * 50)
print("ADMIN ROLE VERIFICATION TEST")
print("=" * 50)
print(f"\nUser ID: {USER_ID}")
print(f"\nRole from database: {get_user_role(USER_ID)}")
print(f"is_admin(): {is_admin(USER_ID)}")
print(f"is_staff(): {is_staff(USER_ID)}")
print(f"is_user(): {is_user(USER_ID)}")

print("\n" + "=" * 50)
if is_admin(USER_ID):
    print("✅ PASS: User has admin access!")
else:
    print("❌ FAIL: User does NOT have admin access!")
print("=" * 50)
