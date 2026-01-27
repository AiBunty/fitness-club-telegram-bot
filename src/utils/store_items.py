import json
from pathlib import Path
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

STORE_PATH = Path(__file__).resolve().parent.parent / 'data' / 'store_items.json'


def load_store_items() -> List[Dict]:
    """Load store items from database (primary) with JSON fallback"""
    try:
        # Try database first
        from src.database.store_items_operations import load_store_items_from_db
        items = load_store_items_from_db()
        if items:
            return items
    except Exception as e:
        logger.warning(f"Database unavailable, using JSON fallback: {e}")
    
    # Fallback to JSON
    try:
        with open(STORE_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
    except Exception:
        pass
    return []


def save_store_items(items: List[Dict]):
    """Save to JSON (legacy backup only - database is primary)"""
    with open(STORE_PATH, 'w', encoding='utf-8') as f:
        json.dump(items, f, indent=2, ensure_ascii=False)


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
    Add new item or update existing item (database-backed)
    Returns: dict with 'serial', 'is_new' keys
    """
    try:
        from src.database.store_items_operations import add_or_update_item_in_db
        return add_or_update_item_in_db(item)
    except Exception as e:
        logger.error(f"Database operation failed, falling back to JSON: {e}")
        # Fallback to JSON-based logic (legacy)
        items = load_store_items()
        name_raw = (item.get('name') or '').strip()
        hsn_raw = str(item.get('hsn') or '').strip()

        # If serial provided, update that serial only
        provided_serial = item.get('serial')
        if provided_serial is not None and str(provided_serial).strip() != '':
            try:
                s = int(provided_serial)
            except Exception:
                raise ValueError('Invalid serial number')

            existing = get_item_by_serial(items, s)
            if existing:
                # Update allowed fields only
                existing.update({
                    'name': name_raw or existing.get('name'),
                    'hsn': hsn_raw or existing.get('hsn'),
                    'mrp': float(item.get('mrp', existing.get('mrp'))),
                    'gst': float(item.get('gst', existing.get('gst'))),
                })
                save_store_items(items)
                return {'serial': s, 'is_new': False, **existing}
            else:
                # Serial provided but not found -> reject
                raise KeyError(f"Serial {s} not found")

        # No serial provided: check name+hsn dup prevention
        dup = find_by_name_hsn(items, name_raw, hsn_raw)
        if dup:
            # Overwrite price/GST, keep serial
            dup['mrp'] = float(item.get('mrp', dup.get('mrp')))
            dup['gst'] = float(item.get('gst', dup.get('gst')))
            save_store_items(items)
            return {'serial': dup.get('serial'), 'is_new': False, **dup}

        # Create new item and assign next serial
        serial = get_next_serial(items)
        new_item = {
            'name': name_raw,
            'hsn': hsn_raw,
            'mrp': float(item.get('mrp', 0)),
            'gst': float(item.get('gst', 0)),
            'serial': serial
        }
        items.append(new_item)
        save_store_items(items)
        return {'serial': serial, 'is_new': True, **new_item}


def find_items(term: str, limit: int = 10) -> List[Dict]:
    """Search items by term (database-backed)"""
    try:
        from src.database.store_items_operations import find_items_from_db
        return find_items_from_db(term, limit)
    except Exception as e:
        logger.warning(f"Database unavailable, using list fallback: {e}")
        # Fallback to list search
        term = term.strip().lower()
        items = load_store_items()
        results = []
        for it in items:
            if term in (it.get('name','').lower()) or term in str(it.get('hsn','')).lower():
                results.append(it)
                if len(results) >= limit:
                    break
        return results
