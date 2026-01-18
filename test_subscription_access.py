"""Test that approved users can now access menu with subscriptions"""
import sys
sys.path.insert(0, '/root/fitness-club-telegram-bot')

from src.database.subscription_operations import is_subscription_active
from src.database.user_operations import get_user_by_id

# Test users
test_users = [
    (7639647487, "Sameer Anil Bhalerao"),  # No subscription yet
    (1980219847, "Dhawal"),                 # Should have active subscription
    (1206519616, "Parin"),                  # Should have active subscription
    (6133468540, "Sayali Sunil Wani"),     # Should have active subscription
]

print("🔍 TESTING SUBSCRIPTION ACCESS FOR APPROVED USERS")
print("=" * 60)

for user_id, name in test_users:
    print(f"\n👤 {name} (ID: {user_id})")
    print("-" * 60)
    
    # Check user approval status
    user = get_user_by_id(user_id)
    if user:
        print(f"   ✓ Approval Status: {user['approval_status']}")
        print(f"   ✓ User Found: {user['full_name']}")
        
        # Check subscription status
        is_active = is_subscription_active(user_id)
        if is_active:
            print(f"   ✅ SUBSCRIPTION ACTIVE - User can access menu")
        else:
            print(f"   ❌ SUBSCRIPTION INACTIVE - User gets 'subscription expired'")
    else:
        print(f"   ❌ User not found in database")

print("\n" + "=" * 60)
print("✅ Subscription access test complete!")
