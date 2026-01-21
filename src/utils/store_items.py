import json
from pathlib import Path
from typing import List, Dict, Optional

STORE_PATH = Path(__file__).resolve().parent.parent / 'data' / 'store_items.json'


def load_store_items() -> List[Dict]:
    try:
        with open(STORE_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
    except Exception:
        pass
    return []


def save_store_items(items: List[Dict]):
    with open(STORE_PATH, 'w', encoding='utf-8') as f:
        json.dump(items, f, indent=2, ensure_ascii=False)


def get_next_serial(items: List[Dict]) -> int:
    """Get next serial number"""
    if not items:
        return 1
    return max(item.get("serial", 0) for item in items) + 1


def add_or_update_item(item: Dict) -> Dict:
    """
    Add new item or update existing item.
    Returns: dict with 'serial', 'is_new' keys
    """
    items = load_store_items()
    # Identify by name + hsn
    name = item.get('name','').strip().lower()
    hsn = str(item.get('hsn','')).strip()
    
    # Check if item exists
    for i, it in enumerate(items):
        if it.get('name','').strip().lower() == name and str(it.get('hsn','')).strip() == hsn:
            # Update existing item (preserve serial)
            serial = it.get('serial')
            if not serial:
                serial = get_next_serial(items)
                it['serial'] = serial
            items[i].update(item)
            items[i]['serial'] = serial  # Ensure serial is preserved
            save_store_items(items)
            return {'serial': serial, 'is_new': False, **items[i]}
    
    # Add new item with auto serial
    serial = get_next_serial(items)
    item['serial'] = serial
    items.append(item)
    save_store_items(items)
    return {'serial': serial, 'is_new': True, **item}


def find_items(term: str, limit: int = 10) -> List[Dict]:
    term = term.strip().lower()
    items = load_store_items()
    results = []
    for it in items:
        if term in (it.get('name','').lower()) or term in str(it.get('hsn','')).lower():
            results.append(it)
            if len(results) >= limit:
                break
    return results
