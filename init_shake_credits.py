#!/usr/bin/env python3
"""
Initialize shake credits for all existing users.
"""

import sys
from src.database.connection import execute_query
from src.database.shake_credits_operations import init_user_credits

def initialize_all_users():
    """Initialize shake credits for all registered users."""
    try:
        # Get all users
        query = "SELECT user_id FROM users"
        users = execute_query(query)
        
        if not users:
            print("No users found.")
            return
        
        print(f"Found {len(users)} users. Initializing shake credits...")
        
        initialized = 0
        already_exists = 0
        failed = 0
        
        for user in users:
            user_id = user.get('user_id') if isinstance(user, dict) else user[0]
            try:
                # Check if user already has shake credits
                existing = execute_query(
                    "SELECT credit_id FROM shake_credits WHERE user_id = %s",
                    (user_id,),
                    fetch_one=True
                )
                
                if not existing:
                    init_user_credits(user_id)
                    initialized += 1
                    print(f"✓ Initialized credits for user {user_id}")
                else:
                    already_exists += 1
            except Exception as e:
                failed += 1
                print(f"✗ Failed to initialize user {user_id}: {e}")
        
        print(f"\n✅ Initialization complete!")
        print(f"   Initialized: {initialized}")
        print(f"   Already had credits: {already_exists}")
        print(f"   Failed: {failed}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    initialize_all_users()
