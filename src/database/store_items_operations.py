"""
Store items database operations for invoices
Handles store catalog CRUD operations
"""

import logging
from typing import List, Dict, Optional
from src.database.connection import execute_query

logger = logging.getLogger(__name__)

def load_store_items_from_db() -> List[Dict]:
    """Load all store items from database"""
    try:
        query = """
        SELECT serial, name, hsn, mrp, gst, created_at, updated_at
        FROM store_items
        ORDER BY serial
        """
        items = execute_query(query)
        return items if items else []
    except Exception as e:
        logger.error(f"Error loading store items from DB: {e}")
        return []


def get_item_by_serial_from_db(serial: int) -> Optional[Dict]:
    """Get item by serial number"""
    try:
        query = "SELECT * FROM store_items WHERE serial = %s"
        return execute_query(query, (serial,), fetch_one=True)
    except Exception as e:
        logger.error(f"Error getting item by serial {serial}: {e}")
        return None


def find_by_name_hsn_from_db(name: str, hsn: str) -> Optional[Dict]:
    """Find item by name and HSN combination"""
    try:
        query = """
        SELECT * FROM store_items
        WHERE LOWER(name) = LOWER(%s) AND hsn = %s
        """
        return execute_query(query, (name.strip(), hsn.strip()), fetch_one=True)
    except Exception as e:
        logger.error(f"Error finding item by name/HSN: {e}")
        return None


def add_or_update_item_in_db(item: Dict) -> Dict:
    """
    Add new item or update existing item in database
    Returns: dict with 'serial', 'is_new' keys
    """
    try:
        name_raw = (item.get('name') or '').strip()
        hsn_raw = str(item.get('hsn') or '').strip()
        mrp = float(item.get('mrp', 0))
        gst = float(item.get('gst', 18.0))
        
        # If serial provided, update that serial only
        provided_serial = item.get('serial')
        if provided_serial is not None and str(provided_serial).strip() != '':
            serial = int(provided_serial)
            
            # Check if serial exists
            existing = get_item_by_serial_from_db(serial)
            if existing:
                # Update existing item
                query1 = """
                UPDATE store_items
                SET name = %s, hsn = %s, mrp = %s, gst = %s, updated_at = CURRENT_TIMESTAMP
                WHERE serial = %s
                """
                execute_query(query1, (name_raw, hsn_raw, mrp, gst, serial))
                
                # Get the updated result
                query2 = "SELECT * FROM store_items WHERE serial = %s"
                result = execute_query(query2, (serial,), fetch_one=True)
                if result:
                    result['is_new'] = False
                    return result
            else:
                # Serial not found
                raise KeyError(f"Serial {serial} not found")
        
        # No serial provided: check name+hsn for duplicates
        dup = find_by_name_hsn_from_db(name_raw, hsn_raw)
        if dup:
            # Update price/GST of existing item
            query1 = """
            UPDATE store_items
            SET mrp = %s, gst = %s, updated_at = CURRENT_TIMESTAMP
            WHERE serial = %s
            """
            execute_query(query1, (mrp, gst, dup['serial']))
            
            # Get the updated result
            query2 = "SELECT * FROM store_items WHERE serial = %s"
            result = execute_query(query2, (dup['serial'],), fetch_one=True)
            if result:
                result['is_new'] = False
                return result
        
        # Create new item
        query1 = """
        INSERT INTO store_items (name, hsn, mrp, gst)
        VALUES (%s, %s, %s, %s)
        """
        execute_query(query1, (name_raw, hsn_raw, mrp, gst))
        
        # Get the created item
        query2 = "SELECT * FROM store_items WHERE name = %s AND hsn = %s ORDER BY serial DESC LIMIT 1"
        result = execute_query(query2, (name_raw, hsn_raw), fetch_one=True)
        if result:
            result['is_new'] = True
            return result
        
        raise Exception("Failed to create item")
        
    except Exception as e:
        logger.error(f"Error adding/updating item in DB: {e}")
        raise


def find_items_from_db(term: str, limit: int = 10) -> List[Dict]:
    """Search items by name or HSN"""
    try:
        term_lower = term.strip().lower()
        query = """
        SELECT * FROM store_items
        WHERE LOWER(name) LIKE %s OR LOWER(hsn) LIKE %s
        ORDER BY name
        LIMIT %s
        """
        search_term = f"%{term_lower}%"
        return execute_query(query, (search_term, search_term, limit))
    except Exception as e:
        logger.error(f"Error finding items in DB: {e}")
        return []


def delete_item_from_db(serial: int) -> bool:
    """Delete item by serial number"""
    try:
        query = "DELETE FROM store_items WHERE serial = %s"
        execute_query(query, (serial,))
        logger.info(f"Deleted item with serial {serial}")
        return True
    except Exception as e:
        logger.error(f"Error deleting item {serial}: {e}")
        return False


def search_items_by_name_from_db(name: str) -> List[Dict]:
    """Search items by name (partial match)"""
    try:
        query = """
        SELECT * FROM store_items
        WHERE LOWER(name) LIKE %s
        ORDER BY name
        LIMIT 20
        """
        return execute_query(query, (f"%{name.lower()}%",))
    except Exception as e:
        logger.error(f"Error searching items by name: {e}")
        return []
