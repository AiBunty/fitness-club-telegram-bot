"""
Invoice v2 - Utilities (User Search, GST Config, etc.)
"""
import json
import os
from typing import Dict, List, Optional


USERS_FILE = None
GST_CONFIG_FILE = "data/gst_config.json"
# user_registry removed - database is single source of truth


def ensure_gst_config():
    """Ensure GST config exists"""
    os.makedirs("data", exist_ok=True)
    if not os.path.exists(GST_CONFIG_FILE):
        config = {
            "enabled": False,
            "mode": "exclusive",  # exclusive or inclusive
            "percent": 18
        }
        with open(GST_CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)


def get_gst_config() -> Dict:
    """Get GST configuration"""
    ensure_gst_config()
    try:
        with open(GST_CONFIG_FILE, "r") as f:
            return json.load(f)
    except:
        return {"enabled": False, "mode": "exclusive", "percent": 18}


def load_users() -> List[Dict]:
    """Load user registry - DATABASE ONLY"""
    # Database is single source of truth
    try:
        from src.database.user_operations import get_all_users
        return get_all_users() or []
    except Exception:
        return []


def search_users(query: str, limit: int = 10) -> List[Dict]:
    """
    Search users by name, username, or telegram_id
    - Partial, case-insensitive match on name/username
    - Exact numeric match on telegram_id
    
    Searches the DATABASE first (primary source of truth)
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"[INVOICE] user_search term='{query}'")
    
    # Try database first (primary source)
    try:
        from src.database.user_operations import get_all_users
        all_users = get_all_users()
        
        if all_users:
            logger.info(f"[INVOICE_SEARCH] Found {len(all_users)} users from database")
            # Convert DB format to search format for compatibility
            formatted_users = []
            for u in all_users:
                # Parse full_name into first/last for compatibility
                full_name = u.get('full_name', '')
                name_parts = full_name.split(' ', 1)
                user_id = u.get('user_id')  # user_id IS the Telegram ID
                
                formatted_users.append({
                    'telegram_id': user_id,  # For backward compatibility in code
                    'user_id': user_id,       # Primary field
                    'first_name': name_parts[0] if name_parts else '',
                    'last_name': name_parts[1] if len(name_parts) > 1 else '',
                    'full_name': full_name,
                    'username': u.get('telegram_username', ''),
                    'phone': u.get('phone', ''),
                    'role': u.get('role', 'member'),
                    'fee_status': u.get('fee_status', 'unpaid')
                })
            return _filter_users(formatted_users, query, limit)
    except Exception as e:
        logger.error(f"[INVOICE_SEARCH] Database search failed: {e}")
        return []

    # No fallback - database is single source of truth
    return []


def _filter_users(users: List[Dict], query: str, limit: int) -> List[Dict]:
    """Filter users by query term"""
    if not query or not users:
        return []
    
    query_lower = query.lower().lstrip('@')
    results = []
    
    for user in users:
        # Exact match on telegram_id (numeric search)
        if str(user.get('telegram_id', '')).startswith(query):
            results.append(user)
            continue
        
        # Match on full_name (handles "S J" type names)
        full_name = str(user.get('full_name', '')).lower()
        if query_lower in full_name:
            results.append(user)
            continue
        
        # Partial match on first_name
        first_name = str(user.get('first_name', '')).lower()
        if query_lower in first_name:
            results.append(user)
            continue
        
        # Partial match on last_name
        last_name = str(user.get('last_name', '')).lower()
        if query_lower in last_name:
            results.append(user)
            continue
        
        # Partial match on phone
        phone = str(user.get('phone', '')).replace(' ', '')
        if query in phone:
            results.append(user)
            continue
        
        # Partial match on username
        username = str(user.get('username', '')).lower().lstrip('@')
        if query_lower in username:
            results.append(user)
            continue
    
    return results[:limit]


def format_user_display(user: Dict) -> str:
    """Format user info for display"""
    first = user.get("first_name", "")
    last = user.get("last_name", "")
    username = user.get("username", "")
    uid = user.get("telegram_id") or user.get('user_id') or "?"
    
    name = f"{first} {last}".strip()
    user_str = f"@{username}" if username else str(uid)
    
    return f"{name} ({user_str})"


def calculate_gst(base_amount: float, include_gst: bool = True) -> Dict:
    """
    Calculate GST based on config
    Returns: {taxable, gst_amount, total}
    
    include_gst: If True, base_amount already includes GST (inclusive mode)
                 If False, GST is added on top (exclusive mode)
    """
    config = get_gst_config()
    
    if not config.get("enabled"):
        return {
            "taxable": base_amount,
            "gst_amount": 0.0,
            "total": base_amount
        }
    
    gst_percent = float(config.get("percent", 18)) / 100
    
    if config.get("mode") == "inclusive":
        # GST already in amount, extract it
        gst_amount = base_amount * gst_percent / (1 + gst_percent)
        taxable = base_amount - gst_amount
    else:
        # GST not in amount, add on top (exclusive)
        taxable = base_amount
        gst_amount = base_amount * gst_percent
    
    return {
        "taxable": round(taxable, 2),
        "gst_amount": round(gst_amount, 2),
        "total": round(base_amount if config.get("mode") == "inclusive" else base_amount + gst_amount, 2)
    }
