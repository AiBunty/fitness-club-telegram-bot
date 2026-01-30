"""
Invoice v2 - Store Item Management with Serial Numbers
DEPRECATED: This module uses JSON files. Use src.database.store_items_operations for database-backed operations instead.
Legacy fallback only - do not use in new code.
"""
import json
import os
from typing import Dict, List, Optional


STORE_ITEMS_FILE = "data/store_items.json"


def ensure_store_file():
    """Ensure store items file exists"""
    os.makedirs("data", exist_ok=True)
    if not os.path.exists(STORE_ITEMS_FILE):
        with open(STORE_ITEMS_FILE, "w") as f:
            json.dump([], f, indent=2)


def load_items() -> List[Dict]:
    """Load all store items"""
    ensure_store_file()
    try:
        with open(STORE_ITEMS_FILE, "r") as f:
            return json.load(f)
    except:
        return []


def save_items(items: List[Dict]):
    """Save store items"""
    ensure_store_file()
    with open(STORE_ITEMS_FILE, "w") as f:
        json.dump(items, f, indent=2)


def get_next_serial() -> int:
    """Get next serial number"""
    items = load_items()
    if not items:
        return 1
    return max(item.get("serial", 0) for item in items) + 1


def add_item(name: str, hsn: str, mrp: float, gst_percent: float) -> Dict:
    """Add new store item with auto-incremented serial"""
    items = load_items()
    
    serial = get_next_serial()
    item = {
        "serial": serial,
        "name": name,
        "hsn": hsn,
        "mrp": float(mrp),
        "gst_percent": float(gst_percent)
    }
    
    items.append(item)
    save_items(items)
    return item


def search_by_serial(serial: int) -> Optional[Dict]:
    """Find item by serial number"""
    items = load_items()
    for item in items:
        if item.get("serial") == serial:
            return item
    return None


def search_by_name(name: str) -> List[Dict]:
    """Find items by name (partial, case-insensitive)"""
    items = load_items()
    name_lower = name.lower()
    return [item for item in items if name_lower in item.get("name", "").lower()]


def search_item(query: str) -> List[Dict]:
    """
    Search by serial (if numeric) or by name
    Returns: List of matching items
    """
    try:
        serial = int(query)
        item = search_by_serial(serial)
        return [item] if item else []
    except ValueError:
        return search_by_name(query)
