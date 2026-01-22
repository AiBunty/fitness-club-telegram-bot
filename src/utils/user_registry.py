"""
Lightweight user registry for invoice search fallback.
Populated from incoming messages, not DB.
"""
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional
from src.config import USERS_FILE
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)

REGISTRY_FILE = Path(USERS_FILE)


def load_registry() -> List[Dict]:
    """Load users from JSON registry."""
    if not REGISTRY_FILE.exists():
        return []
    try:
        with open(REGISTRY_FILE, 'r', encoding='utf-8') as f:
            users = json.load(f)
            logger.info(f"[USER_REGISTRY] loaded_users_count={len(users)} path={REGISTRY_FILE}")
            return users
    except Exception as e:
        logger.error(f"[USER_REGISTRY] Error loading: {e}")
        return []


def save_registry(users: List[Dict]) -> None:
    """Save users to JSON registry."""
    try:
        REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(REGISTRY_FILE, 'w', encoding='utf-8') as f:
            json.dump(users, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"[USER_REGISTRY] Error saving: {e}")


def track_user(user_id: int, first_name: str = '', last_name: str = '', 
               username: str = '') -> None:
    """Add or update user in registry when they interact with bot."""
    if not user_id:
        return
    
    users = load_registry()
    
    # Remove @ from username if present
    username = username.lstrip('@').lower() if username else ''
    
    # Build full name
    full_name = (first_name or '').strip()
    if last_name:
        full_name = f"{full_name} {last_name}".strip()
    if not full_name:
        full_name = f"User {user_id}"
    
    # Check if user exists
    existing = next((u for u in users if u.get('user_id') == user_id or u.get('telegram_id') == user_id), None)
    
    if existing:
        # Update existing user
        existing['first_name'] = first_name or existing.get('first_name', '')
        existing['last_name'] = last_name or existing.get('last_name', '')
        existing['username'] = username or existing.get('username', '')
        existing['full_name'] = full_name
    else:
        # Add new user
        users.append({
            'user_id': user_id,
            'telegram_id': user_id,
            'first_name': first_name,
            'last_name': last_name,
            'username': username,
            'full_name': full_name,
            'first_seen': datetime.now().isoformat()
        })
    
    save_registry(users)
    logger.info(f"[USER_REGISTRY] tracked user_id={user_id} name={full_name}")


def search_registry(term: str, limit: int = 10) -> List[Dict]:
    """Search users by name or username."""
    if not term:
        return []
    
    term_lower = term.lower().lstrip('@')
    users = load_registry()
    results = []
    
    for user in users:
        # Check telegram_id (exact)
        if str(user.get('user_id', '')).startswith(term):
            results.append(user)
            continue
        
        # Check username (case-insensitive, with or without @)
        username = user.get('username', '').lower()
        if username and term_lower in username:
            results.append(user)
            continue
        
        # Check full_name (partial, case-insensitive)
        full_name = user.get('full_name', '').lower()
        if term_lower in full_name:
            results.append(user)
            continue
        
        # Check first_name
        first_name = user.get('first_name', '').lower()
        if first_name and term_lower in first_name:
            results.append(user)
            continue
        
        # Check last_name
        last_name = user.get('last_name', '').lower()
        if last_name and term_lower in last_name:
            results.append(user)
            continue
    
    logger.info(f"[USER_SEARCH] query='{term}' total_users_loaded={len(users)} matches_found={len(results[:limit])}")
    return results[:limit]


# Import datetime after function defs to avoid circular imports
from datetime import datetime
