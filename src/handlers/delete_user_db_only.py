"""
PART 5: Delete User Search - Database-Only, Flow-Isolated Implementation

CRITICAL RULES:
✅ IDENTICAL to invoice user search (same search logic)
✅ Database-only, no memory fallback
✅ FLOW ISOLATION: DELETE_USER_SEARCH state  
✅ Separate flow from invoice (different ConversationHandler entry)
✅ Owner check: only delete if DELETE_USER flow is active

Flow states:
- DELETE_USER_SEARCH: Admin entering search term
- DELETE_USER_CONFIRM: Admin confirming deletion

If active_flow != DELETE_USER:
  IGNORE input (return ConversationHandler.END)

If search returns no results:
  "No users found. Try another name or Telegram ID."

NEVER accept: item names, invoice data, or anything not related to delete
"""

import logging
from typing import List, Dict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from src.database.connection import execute_query
from src.utils.flow_manager import (
    set_active_flow, clear_active_flow, check_flow_ownership,
    FLOW_DELETE_USER
)

logger = logging.getLogger(__name__)

def search_delete_user_db_only(query: str, limit: int = 10) -> List[Dict]:
    """
    Search users for DELETE USER flow - DATABASE ONLY.
    
    Identical logic to invoice user search:
    - Numeric: exact telegram_id
    - Text: partial match on name/username
    
    Args:
        query: Search term
        limit: Max results
    
    Returns:
        List of user dicts or empty list
    
    NO fallback to memory or JSON registry.
    """
    if not query or not query.strip():
        logger.warning("[DELETE_USER_SEARCH] empty query")
        return []
    
    query = query.strip()
    logger.info(f"[DELETE_USER_SEARCH] db_only_search query='{query}'")
    
    try:
        # Numeric search (telegram_id)
        if query.isdigit():
            logger.info(f"[DELETE_USER_SEARCH] numeric_search user_id={query}")
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
            return results if results else []
        
        # Text search
        search_term = query.lstrip('@').lower()
        like_pattern = f"%{search_term}%"
        
        logger.info(f"[DELETE_USER_SEARCH] text_search term='{search_term}'")
        
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
            ORDER BY full_name ASC
            LIMIT %s
        """
        
        results = execute_query(
            sql,
            (like_pattern, like_pattern, like_pattern, like_pattern, like_pattern, limit),
            fetch_one=False
        )
        
        if results:
            logger.info(f"[DELETE_USER_SEARCH] found {len(results)} user(s)")
        
        return results if results else []
    
    except Exception as e:
        logger.error(f"[DELETE_USER_SEARCH] error: {e}")
        return []

def format_delete_user_for_display(user: Dict) -> str:
    """Format user for delete confirmation dialog"""
    full_name = user.get('full_name', 'Unknown')
    username = user.get('username', '')
    user_id = user.get('user_id', 'N/A')
    is_banned = user.get('is_banned', False)
    
    display = full_name
    if username:
        display += f" (@{username})"
    display += f"\nID: {user_id}"
    if is_banned:
        display += " ⛔️ BANNED"
    
    return display

# ============================================================================
# HANDLER EXAMPLE: How to integrate into delete user flow
# ============================================================================
"""
class DeleteUserState:
    DELETE_USER_SEARCH = 1      # Searching for user
    DELETE_USER_CONFIRM = 2     # Confirming deletion

async def start_delete_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    '''Entry point: Lock DELETE_USER flow'''
    query = update.callback_query
    admin_id = query.from_user.id
    
    await query.answer()
    
    # Lock flow
    set_active_flow(admin_id, FLOW_DELETE_USER)
    logger.info(f"[DELETE_USER] flow_locked admin={admin_id}")
    
    await query.edit_message_text(
        "🔍 Search user by Name, Username, or Telegram ID:\n"
        "(Who do you want to delete?)"
    )
    return DeleteUserState.DELETE_USER_SEARCH

async def handle_delete_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    '''Handle search input - MUST verify flow ownership'''
    admin_id = update.effective_user.id
    
    # Guard: Only process if this is active flow
    if not check_flow_ownership(admin_id, FLOW_DELETE_USER):
        logger.warning(f"[DELETE_USER] flow_mismatch admin={admin_id} rejecting input")
        await update.effective_user.send_message(
            "❌ Please use the Delete User menu to search."
        )
        return ConversationHandler.END
    
    query = update.message.text.strip()
    logger.info(f"[DELETE_USER] search_query admin={admin_id} query='{query}'")
    
    results = search_delete_user_db_only(query, limit=10)
    
    if not results:
        await update.effective_user.send_message(
            "❌ No users found. Try another name or Telegram ID."
        )
        return DeleteUserState.DELETE_USER_SEARCH
    
    # Build selection buttons
    text = f"🗑️ Found {len(results)} user(s). Click to delete:\n\n"
    
    kb = []
    for i, user in enumerate(results):
        display = format_delete_user_for_display(user)
        callback_data = f"delete_confirm_{user['user_id']}"
        kb.append([InlineKeyboardButton(f"🗑️ {display}", callback_data=callback_data)])
        
        # Store in context for confirmation
        if 'delete_results' not in context.user_data:
            context.user_data['delete_results'] = {}
        context.user_data['delete_results'][user['user_id']] = user
    
    kb.append([InlineKeyboardButton("❌ Cancel", callback_data="delete_cancel")])
    
    await update.effective_user.send_message(text, reply_markup=InlineKeyboardMarkup(kb))
    return DeleteUserState.DELETE_USER_CONFIRM

async def handle_delete_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    '''Confirm and execute deletion - MUST verify ownership AND cleanup'''
    query = update.callback_query
    admin_id = query.from_user.id
    
    await query.answer()
    
    # Guard: Verify we still own the flow
    if not check_flow_ownership(admin_id, FLOW_DELETE_USER):
        await query.edit_message_text("❌ Flow expired. Please start over.")
        return ConversationHandler.END
    
    user_id = int(query.data.split('_')[2])
    
    try:
        # Execute deletion from DB
        execute_query(
            "UPDATE users SET is_banned = TRUE WHERE user_id = %s",
            (user_id,)
        )
        
        logger.info(f"[DELETE_USER] user_deleted admin={admin_id} user_id={user_id}")
        
        await query.edit_message_text(
            f"✅ User {user_id} marked as banned/deleted"
        )
        
        # CRITICAL: Clear flow lock on completion
        clear_active_flow(admin_id, FLOW_DELETE_USER)
        
        return ConversationHandler.END
    
    except Exception as e:
        logger.error(f"[DELETE_USER] deletion_error: {e}")
        await query.edit_message_text("❌ Error deleting user. Try again.")
        
        # CRITICAL: Clear lock even on error
        clear_active_flow(admin_id, FLOW_DELETE_USER)
        
        return ConversationHandler.END
"""
