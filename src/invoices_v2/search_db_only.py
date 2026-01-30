"""
PART 4: Invoice User Search - Database-Only Implementation

CRITICAL RULES:
✅ ONLY search from users table in database
✅ NO in-memory user_registry fallback
✅ NO JSON file reads
✅ NO message heuristics
✅ Supported searches:
   - Telegram ID (numeric)
   - Username (case-insensitive, with/without @)
   - First name (partial)
   - Last name (partial)
   - Full name (partial)
   - Normalized name (collapsed spaces, lowercase)

If no match found:
  "No users found. Try another name or Telegram ID."

Never respond with:
  ❌ "No items found" (that's for store items, not users!)
"""

import logging
from typing import List, Dict, Optional
from src.database.connection import execute_query

logger = logging.getLogger(__name__)

def search_users_db_only(query: str, limit: int = 10) -> List[Dict]:
    """
    Search users from DATABASE ONLY.
    NO fallback to memory or JSON registry.
    
    Supported search types:
    1. Numeric: Telegram ID exact match
    2. Text: Partial match on name/username (case-insensitive)
    
    Args:
        query: Search term (name, username, or user_id)
        limit: Max results (default 10)
    
    Returns:
        List of user dicts with: user_id, first_name, last_name, full_name, username
        Empty list if no matches
    
    CRITICAL: Returns ONLY DB data, never cached/memory data
    """
    if not query or not query.strip():
        logger.warning("[INVOICE_USER_SEARCH] empty query")
        return []
    
    query = query.strip()
    logger.info(f"[INVOICE_USER_SEARCH] db_only_search query='{query}' limit={limit}")
    
    try:
        # Try numeric search first (Telegram ID)
        if query.isdigit():
            logger.info(f"[INVOICE_USER_SEARCH] numeric_search user_id={query}")
            sql = """
                SELECT 
                    user_id,
                    COALESCE(first_name, '') as first_name,
                    COALESCE(last_name, '') as last_name,
                    COALESCE(full_name, '') as full_name,
                    COALESCE(username, '') as username,
                    is_banned
                FROM users
                WHERE user_id = %s
                LIMIT 1
            """
            results = execute_query(sql, (query,), fetch_one=False)
            
            if results:
                logger.info(f"[INVOICE_USER_SEARCH] numeric_match found user_id={query}")
                return results
            else:
                logger.info(f"[INVOICE_USER_SEARCH] numeric_match NOT_FOUND user_id={query}")
                return []
        
        # Text search: partial match on name or username
        # Strip @ from username if provided
        search_term = query.lstrip('@').lower()
        like_pattern = f"%{search_term}%"
        
        logger.info(f"[INVOICE_USER_SEARCH] text_search term='{search_term}' pattern='{like_pattern}'")
        
        sql = """
            SELECT 
                user_id,
                COALESCE(first_name, '') as first_name,
                COALESCE(last_name, '') as last_name,
                COALESCE(full_name, '') as full_name,
                COALESCE(username, '') as username,
                is_banned
            FROM users
            WHERE 
                LOWER(COALESCE(first_name, '')) LIKE %s
                OR LOWER(COALESCE(last_name, '')) LIKE %s
                OR LOWER(COALESCE(full_name, '')) LIKE %s
                OR LOWER(COALESCE(username, '')) LIKE %s
                OR LOWER(COALESCE(normalized_name, '')) LIKE %s
            ORDER BY 
                CASE 
                    WHEN LOWER(full_name) = %s THEN 0  -- exact match first
                    WHEN LOWER(full_name) LIKE %s THEN 1  -- starts with
                    ELSE 2  -- contains
                END,
                full_name ASC
            LIMIT %s
        """
        
        exact_match = search_term
        starts_with = f"{search_term}%"
        
        results = execute_query(
            sql,
            (like_pattern, like_pattern, like_pattern, like_pattern, like_pattern, exact_match, starts_with, limit),
            fetch_one=False
        )
        
        if results:
            logger.info(f"[INVOICE_USER_SEARCH] text_match found {len(results)} user(s)")
            return results
        else:
            logger.info(f"[INVOICE_USER_SEARCH] text_match NOT_FOUND term='{search_term}'")
            return []
    
    except Exception as e:
        logger.error(f"[INVOICE_USER_SEARCH] error: {e}")
        return []

def format_user_for_display(user: Dict) -> str:
    """Format user for display in invoice search results"""
    first_name = user.get('first_name', '')
    last_name = user.get('last_name', '')
    full_name = user.get('full_name', 'Unknown')
    username = user.get('username', '')
    user_id = user.get('user_id', 'N/A')
    is_banned = user.get('is_banned', False)
    
    # Build display name
    display = full_name or f"{first_name} {last_name}".strip() or "Unknown"
    
    if username:
        display += f" (@{username})"
    
    display += f"\nID: {user_id}"
    
    if is_banned:
        display += " ⛔️ BANNED"
    
    return display

# ============================================================================
# INTEGRATION: Replace search_users in invoices_v2/handlers.py
# ============================================================================
# OLD CODE (with memory fallback):
#     results = search_users(query, limit=10)
#
# NEW CODE (DB-only):
#     results = search_users_db_only(query, limit=10)
#
# Also replace:
#     format_user_display(user) → format_user_for_display(user)
