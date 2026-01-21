#!/usr/bin/env python3
"""Quick manual test for user search"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from database.user_operations import search_users

# Test 1: Fuzzy search for "say"
print("="*60)
print("Test: Searching for 'say' (should find Sayali, etc.)")
print("="*60)
results = search_users("say", limit=10)
print(f"Found {len(results)} users:")
for u in results:
    print(f"  - {u.get('full_name')} (@{u.get('telegram_username', 'N/A')}) | ID: {u.get('user_id')} | Status: {u.get('approval_status')}")

# Test 2: Search by first char
print("\n" + "="*60)
print("Test: Searching for 'a' (broad search)")
print("="*60)
results = search_users("a", limit=5)
print(f"Found {len(results)} users:")
for u in results:
    print(f"  - {u.get('full_name')} | Status: {u.get('approval_status')}")

print("\n✅ Tests complete!")
