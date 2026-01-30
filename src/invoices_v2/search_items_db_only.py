"""
PART 6: Invoice Item Search - Database-Only Implementation

CRITICAL RULES:
✅ ONLY search store_items table - NEVER users table
✅ NO user name matches
✅ NO memory/JSON fallback
✅ Supported searches:
   - Serial number (exact match, numeric)
   - Item name (partial, case-insensitive)

Response MUST show:
   - Serial No
   - Item Name
   - MRP
   - GST %

If no match:
   "No items found. Try another item name or serial number."

NEVER respond with:
   ❌ "No users found" (that's for user search, not items!)
   ❌ User data mixed with item data
"""

import logging
from typing import List, Dict, Optional
from src.database.connection import execute_query

logger = logging.getLogger(__name__)

def _get_store_items_schema() -> Dict[str, bool]:
    """Detect store_items schema columns in the live database."""
    try:
        rows = execute_query(
            "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME='store_items'",
            fetch_one=False
        ) or []
        cols = {r.get('COLUMN_NAME') for r in rows}
        return {
            'has_store_items': bool(cols),
            'has_serial_name': {'serial', 'name', 'mrp', 'gst'}.issubset(cols),
            'has_item_name': {'item_id', 'item_name', 'mrp', 'gst_percent'}.issubset(cols),
            'has_serial_no': 'serial_no' in cols,
            'has_normalized_name': 'normalized_item_name' in cols,
        }
    except Exception as e:
        logger.error(f"[INVOICE_ITEM_SEARCH] schema detect failed: {e}")
        return {
            'has_store_items': False,
            'has_serial_name': False,
            'has_item_name': False,
            'has_serial_no': False,
            'has_normalized_name': False,
        }


def _log_store_items_count():
    try:
        row = execute_query("SELECT COUNT(*) as count FROM store_items", fetch_one=True)
        count = row.get('count') if row else 0
        logger.info(f"[INVOICE_ITEM_SEARCH] store_items_count={count}")
    except Exception as e:
        logger.error(f"[INVOICE_ITEM_SEARCH] count failed: {e}")


def search_store_items_db_only(query: str, limit: int = 20) -> List[Dict]:
    """
    Search store items from DATABASE ONLY.
    NO confusion with user search.
    NO fallback to memory.
    
    Supported search:
    1. Numeric: Serial number exact match
    2. Text: Partial match on item_name (case-insensitive)
    
    Args:
        query: Search term (item name or serial number)
        limit: Max results (default 20 since items < users)
    
    Returns:
        List of item dicts: item_id, serial_no, item_name, mrp, gst_percent, is_active
        Empty list if no matches
    
    CRITICAL: Returns ONLY DB data, NEVER user data
    """
    if not query or not query.strip():
        logger.warning("[INVOICE_ITEM_SEARCH] empty query")
        return []
    
    query = query.strip()
    logger.info(f"[INVOICE_ITEM_SEARCH] db_only_search query='{query}' limit={limit}")
    
    try:
        schema = _get_store_items_schema()
        if not schema['has_store_items']:
            logger.error("[INVOICE_ITEM_SEARCH] store_items table not found")
            return []

        _log_store_items_count()

        # Try numeric search first (serial number)
        if query.isdigit():
            logger.info(f"[INVOICE_ITEM_SEARCH] numeric_search serial_no={query}")

            if schema['has_serial_name']:
                sql = """
                    SELECT 
                        serial AS item_id,
                        serial AS serial_no,
                        name AS item_name,
                        mrp,
                        gst AS gst_percent,
                        1 AS is_active
                    FROM store_items
                    WHERE serial = %s
                    LIMIT 1
                """
            else:
                # Fallback: Should not reach here if schema detection works properly
                # But if it does, use the serial/name schema
                sql = """
                    SELECT 
                        serial AS item_id,
                        serial AS serial_no,
                        name AS item_name,
                        mrp,
                        gst AS gst_percent,
                        1 AS is_active
                    FROM store_items
                    WHERE serial = %s
                    LIMIT 1
                """

            results = execute_query(sql, (query,), fetch_one=False)

            if results:
                logger.info(f"[INVOICE_ITEM_SEARCH] numeric_match found serial={query}")
                return results
            logger.info(f"[INVOICE_ITEM_SEARCH] numeric_match NOT_FOUND serial={query}")
            return []

        # Text search: partial match on item_name
        # CRITICAL: Do NOT search users table!
        search_term = query.lower()
        like_pattern = f"%{search_term}%"

        logger.info(f"[INVOICE_ITEM_SEARCH] text_search term='{search_term}'")

        if schema['has_serial_name']:
            sql = """
                SELECT 
                    serial AS item_id,
                    serial AS serial_no,
                    name AS item_name,
                    mrp,
                    gst AS gst_percent,
                    1 AS is_active
                FROM store_items
                WHERE LOWER(name) LIKE %s
                ORDER BY 
                    CASE 
                        WHEN LOWER(name) = %s THEN 0
                        WHEN LOWER(name) LIKE %s THEN 1
                        ELSE 2
                    END,
                    name ASC
                LIMIT %s
            """
            params = (like_pattern, search_term, f"{search_term}%", limit)
        else:
            # Schema not detected - use the serial/name schema (known to exist)
            sql = """
                SELECT 
                    serial AS item_id,
                    serial AS serial_no,
                    name AS item_name,
                    mrp,
                    gst AS gst_percent,
                    1 AS is_active
                FROM store_items
                WHERE LOWER(name) LIKE %s
                ORDER BY 
                    CASE 
                        WHEN LOWER(name) = %s THEN 0
                        WHEN LOWER(name) LIKE %s THEN 1
                        ELSE 2
                    END,
                    name ASC
                LIMIT %s
            """
            params = (like_pattern, search_term, f"{search_term}%", limit)

        results = execute_query(sql, params, fetch_one=False)

        if results:
            logger.info(f"[INVOICE_ITEM_SEARCH] text_match found {len(results)} item(s)")
            return results
        logger.info(f"[INVOICE_ITEM_SEARCH] text_match NOT_FOUND term='{search_term}'")
        return []

    except Exception as e:
        logger.error(f"[INVOICE_ITEM_SEARCH] error: {e}")
        return []

def format_item_for_display(item: Dict) -> str:
    """Format store item for display in invoice item search results"""
    serial_no = item.get('serial_no', 'N/A')
    item_name = item.get('item_name', 'Unknown Item')
    mrp = item.get('mrp', 0)
    gst_percent = item.get('gst_percent', 18.0)
    
    display = (
        f"Serial: {serial_no}\n"
        f"Item: {item_name}\n"
        f"MRP: ₹{mrp:.2f}\n"
        f"GST: {gst_percent}%"
    )
    
    return display

def get_item_details_for_invoice(item: Dict) -> Dict:
    """
    Extract item details for adding to invoice.
    Called when admin selects an item.
    
    Returns dict ready for invoice_items table insert:
    {
        'store_item_id': int,
        'item_name': str,
        'mrp': float,
        'gst_percent': float
    }
    """
    return {
        'store_item_id': item.get('item_id'),
        'item_name': item.get('item_name'),
        'mrp': item.get('mrp'),
        'gst_percent': item.get('gst_percent', 18.0)
    }

# ============================================================================
# CRITICAL DIFFERENCE: Items vs Users
# ============================================================================
"""
INVOICE USER SEARCH:
  Query: name, username, or user_id
  Source: users table
  Result shows: Name, Username, Telegram ID

INVOICE ITEM SEARCH:
  Query: item name or serial number
  Source: store_items table
  Result shows: Serial #, Item Name, Price, GST%

They MUST NEVER be confused in handlers!

If handler gets "No items found" during user search → BUG!
If handler gets "No users found" during item search → BUG!

Each search MUST explicitly state which table it queries.
"""
