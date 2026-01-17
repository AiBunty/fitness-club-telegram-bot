#!/usr/bin/env python3
"""
Migration: Add new shake flavors to the menu
Adds: Kulfi, Strawberry, Vanilla, Dutch Chocolate, Mango, Orange Cream, Paan, Rose Kheer, Banana Caramel
"""

import logging
from src.database.connection import execute_query

logger = logging.getLogger(__name__)

# Define the new shake menu items
SHAKE_MENU = [
    ("Kulfi", "Traditional ice cream dessert"),
    ("Strawberry", "Fresh strawberry flavor"),
    ("Vanilla", "Classic vanilla taste"),
    ("Dutch Chocolate", "Rich dark chocolate"),
    ("Mango", "Tropical mango flavor"),
    ("Orange Cream", "Orange with creamy smoothness"),
    ("Paan", "Traditional paan flavor"),
    ("Rose Kheer", "Rose flavored dessert shake"),
    ("Banana Caramel", "Banana with caramel sweetness"),
]

def migrate():
    """Add new shake flavors to database"""
    try:
        print("🔍 Checking existing shake flavors...")
        
        existing = execute_query("SELECT COUNT(*) as count FROM shake_flavors")
        existing_count = existing[0]['count'] if existing else 0
        
        print(f"✅ Currently {existing_count} flavors in database")
        
        # Get existing flavor names
        existing_flavors = execute_query("SELECT name FROM shake_flavors")
        existing_names = {row['name'] for row in existing_flavors} if existing_flavors else set()
        
        print(f"✅ Existing flavors: {existing_names}")
        
        # Add new flavors
        added_count = 0
        for flavor_name, description in SHAKE_MENU:
            if flavor_name in existing_names:
                print(f"⏭️  Skipping {flavor_name} (already exists)")
                continue
            
            insert_query = """
                INSERT INTO shake_flavors (name, is_active)
                VALUES (%s, true)
            """
            execute_query(insert_query, (flavor_name,))
            print(f"✅ Added: {flavor_name}")
            added_count += 1
        
        print()
        print(f"✅ Migration completed!")
        print(f"   - New flavors added: {added_count}")
        print(f"   - Total flavors now: {existing_count + added_count}")
        
        # Show final list
        final_flavors = execute_query("SELECT * FROM shake_flavors WHERE is_active = true ORDER BY name ASC")
        if final_flavors:
            print()
            print("📋 Complete Shake Menu:")
            for i, flavor in enumerate(final_flavors, 1):
                print(f"   {i}. {flavor['name']}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        print(f"❌ Migration failed: {e}")
        return False

if __name__ == "__main__":
    if migrate():
        print("\n✅ Shake menu migration successful!")
    else:
        print("\n❌ Shake menu migration failed!")
