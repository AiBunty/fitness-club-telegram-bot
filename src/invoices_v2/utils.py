"""
Invoice v2 - Utilities (User Search, GST Config, etc.)
"""
import json
import os
from typing import Dict, List, Optional


USERS_FILE = "data/users.json"
GST_CONFIG_FILE = "data/gst_config.json"


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
    """Load user registry"""
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except:
        return []


def search_users(query: str, limit: int = 10) -> List[Dict]:
    """
    Search users by name, username, or telegram_id
    - Partial, case-insensitive match on name/username
    - Exact numeric match on telegram_id
    """
    users = load_users()
    
    # Try exact telegram_id match first
    try:
        user_id = int(query)
        for user in users:
            if user.get("telegram_id") == user_id:
                return [user]
    except ValueError:
        pass
    
    # Text search: name/username (case-insensitive)
    query_lower = query.lower()
    results = []
    
    for user in users:
        # Check first_name
        if query_lower in user.get("first_name", "").lower():
            results.append(user)
            continue
        
        # Check last_name
        if query_lower in user.get("last_name", "").lower():
            results.append(user)
            continue
        
        # Check full_name
        if query_lower in user.get("full_name", "").lower():
            results.append(user)
            continue
        
        # Check username (strip @)
        username = user.get("username", "").lstrip("@").lower()
        if query_lower in username:
            results.append(user)
            continue
    
    return results[:limit]


def format_user_display(user: Dict) -> str:
    """Format user info for display"""
    first = user.get("first_name", "")
    last = user.get("last_name", "")
    username = user.get("username", "")
    uid = user.get("telegram_id", "?")
    
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
