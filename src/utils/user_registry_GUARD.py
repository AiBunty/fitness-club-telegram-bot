"""
Guard stub to prevent accidental imports of user_registry.

This module was removed as part of migration to database-only mode.
If this error is triggered, there is still legacy code trying to import
user_registry functions.

Database is the ONLY source of truth for user data.
Use src.database.user_operations for all user queries.
"""

raise RuntimeError(
    "user_registry.py is REMOVED. Database is the only source of truth. "
    "Use src.database.user_operations instead."
)
