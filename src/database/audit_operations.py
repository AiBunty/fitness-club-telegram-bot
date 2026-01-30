"""
Audit logging operations for tracking all store changes
"""

import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def log_audit(
    user_id: int,
    entity_type: str,
    entity_id: int,
    action: str,
    old_value: Optional[Dict] = None,
    new_value: Optional[Dict] = None,
    description: Optional[str] = None
) -> bool:
    """
    Log an audit entry for store item changes
    
    Args:
        user_id: Admin user ID who made the change
        entity_type: Type of entity (e.g., 'store_items')
        entity_id: ID of the entity
        action: Action performed (e.g., 'bulk_upload_update', 'manual_edit', 'delete')
        old_value: Previous state (dict)
        new_value: New state (dict)
        description: Optional human-readable description
    
    Returns:
        bool: True if logged successfully
    """
    try:
        from src.database.connection import execute_query
        
        query = """
        INSERT INTO audit_log 
        (user_id, entity_type, entity_id, action, old_value, new_value, description, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
        """
        
        old_json = json.dumps(old_value, default=str) if old_value else None
        new_json = json.dumps(new_value, default=str) if new_value else None
        
        execute_query(query, (
            user_id,
            entity_type,
            entity_id,
            action,
            old_json,
            new_json,
            description or f"{action} on {entity_type} #{entity_id}"
        ))
        
        logger.info(f"[AUDIT] {entity_type} #{entity_id} - {action} by user {user_id}")
        return True
    
    except Exception as e:
        logger.error(f"[AUDIT] Failed to log audit entry: {e}")
        return False


def get_audit_history(entity_type: str, entity_id: int, limit: int = 10) -> list:
    """
    Retrieve audit history for an entity
    
    Args:
        entity_type: Type of entity
        entity_id: ID of the entity
        limit: Maximum records to retrieve
    
    Returns:
        List of audit records
    """
    try:
        from src.database.connection import execute_query
        
        query = """
        SELECT id, user_id, action, old_value, new_value, created_at
        FROM audit_log
        WHERE entity_type = %s AND entity_id = %s
        ORDER BY created_at DESC
        LIMIT %s
        """
        
        records = execute_query(query, (entity_type, entity_id, limit))
        logger.info(f"[AUDIT] Retrieved {len(records)} records for {entity_type} #{entity_id}")
        return records or []
    
    except Exception as e:
        logger.error(f"[AUDIT] Failed to retrieve audit history: {e}")
        return []
