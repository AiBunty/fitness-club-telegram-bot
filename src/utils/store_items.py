import json
from pathlib import Path
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

STORE_PATH = Path(__file__).resolve().parent.parent / 'data' / 'store_items.json'


def load_store_items() -> List[Dict]:
    """Load store items from database only (single source of truth)"""
    try:
        from src.database.store_items_operations import load_store_items_from_db
        items = load_store_items_from_db()
        return items if items else []
    except Exception as e:
        logger.error(f"Error loading store items from database: {e}")
        raise


def save_store_items(items: List[Dict]):
    """Deprecated: Use database operations instead. Keeping for compatibility only."""
    logger.warning("save_store_items() is deprecated - use database operations via store_items_operations.py")
    # No-op: all writes should go to database


def get_next_serial(items: List[Dict]) -> int:
    """Get next serial number"""
    if not items:
        return 1
    return max(item.get("serial", 0) for item in items) + 1


def get_item_by_serial(items: List[Dict], serial: int) -> Optional[Dict]:
    """Get item by serial from database"""
    try:
        from src.database.store_items_operations import get_item_by_serial_from_db
        return get_item_by_serial_from_db(serial)
    except Exception as e:
        logger.warning(f"Database unavailable, using list fallback: {e}")
        # Fallback to list search
        for it in items:
            if int(it.get('serial', 0)) == int(serial):
                return it
        return None


def find_by_name_hsn(items: List[Dict], name: str, hsn: str) -> Optional[Dict]:
    name_norm = (name or '').strip().lower()
    hsn_norm = str(hsn or '').strip()
    for it in items:
        if (it.get('name','').strip().lower() == name_norm) and (str(it.get('hsn','')).strip() == hsn_norm):
            return it
    return None


def add_or_update_item(item: Dict) -> Dict:
    """
    Add new item or update existing item (database-backed only)
    Returns: dict with 'serial', 'is_new' keys
    """
    from src.database.store_items_operations import add_or_update_item_in_db
    return add_or_update_item_in_db(item)


def find_items(term: str, limit: int = 10) -> List[Dict]:
    """Search items by term (database-backed only)"""
    from src.database.store_items_operations import find_items_from_db
    return find_items_from_db(term, limit)
