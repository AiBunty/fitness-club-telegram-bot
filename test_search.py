#!/usr/bin/env python3
from src.database.user_operations import search_users

# Test search with text
results = search_users('saya', limit=10)
print(f'Search for "saya": {len(results)} results')
for r in results:
    print(f'  - {r.get("full_name")} (ID: {r.get("user_id")})')

# Test search with numeric ID
results2 = search_users('424837855', limit=10)
print(f'\nSearch for ID "424837855": {len(results2)} results')
for r in results2:
    print(f'  - {r.get("full_name")} (ID: {r.get("user_id")})')

# Test empty search
results3 = search_users('xyz123nonexistent', limit=10)
print(f'\nSearch for "xyz123nonexistent": {len(results3)} results')
