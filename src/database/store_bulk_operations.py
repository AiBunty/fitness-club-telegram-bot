"""
Robust bulk store items operations with validation and atomic transactions
Implements: Phase 1 Validation + Phase 2 Atomic Update pattern
"""

import json
import logging
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)


async def validate_excel_data(rows: List, header_row_idx: Dict[str, int]) -> Tuple[bool, List, Dict]:
    """
    PHASE 1: Validate all Excel data before any database changes
    
    Args:
        rows: All rows from Excel
        header_row_idx: Dict with 'serial_no', 'item_name', 'hsn_code', 'mrp', 'gst_percent' keys
    
    Returns:
        (is_valid: bool, errors: List[str], data_map: Dict[serial → item_data])
    """
    errors = []
    warnings = []
    data_map = {}  # serial → {name, hsn, mrp, gst, row_num}
    serials_in_file = {}  # Track duplicates within Excel
    
    serial_i = header_row_idx.get('serial_no')
    name_i = header_row_idx.get('item_name')
    hsn_i = header_row_idx.get('hsn_code')
    mrp_i = header_row_idx.get('mrp')
    gst_i = header_row_idx.get('gst_percent')
    
    logger.info("[BULK_VALIDATE] Starting Phase 1 validation...")
    
    for row_idx, row in enumerate(rows[1:], start=2):  # Skip header
        try:
            # Extract serial
            serial_raw = str(row[serial_i]).strip() if serial_i < len(row) and row[serial_i] else ''
            
            if not serial_raw:
                errors.append(f"Row {row_idx}: Serial number is required")
                continue
            
            # Parse serial as integer
            try:
                serial = int(float(serial_raw))
            except (ValueError, TypeError):
                errors.append(f"Row {row_idx}: Serial '{serial_raw}' is not a valid number")
                continue
            
            # CHECK: Duplicate within Excel file
            if serial in serials_in_file:
                errors.append(f"Row {row_idx}: Serial #{serial} appears multiple times (also at row {serials_in_file[serial]})")
                continue
            
            # Extract and validate other fields
            name = str(row[name_i]).strip() if name_i < len(row) and row[name_i] else ''
            hsn = str(row[hsn_i]).strip() if hsn_i < len(row) and row[hsn_i] else ''
            
            if not name:
                errors.append(f"Row {row_idx}: Item Name is required")
                continue
            
            if not hsn:
                errors.append(f"Row {row_idx}: HSN Code is required")
                continue
            
            # Validate numeric fields
            try:
                mrp = float(row[mrp_i]) if mrp_i < len(row) and row[mrp_i] else 0
                gst = float(row[gst_i]) if gst_i < len(row) and row[gst_i] else 18
            except (ValueError, TypeError):
                errors.append(f"Row {row_idx}: MRP and GST must be numeric values")
                continue
            
            # Validate ranges
            if mrp <= 0:
                errors.append(f"Row {row_idx}: MRP must be greater than 0 (got {mrp})")
                continue
            
            if gst < 0 or gst > 100:
                errors.append(f"Row {row_idx}: GST must be between 0-100% (got {gst})")
                continue
            
            # Store validated data
            serials_in_file[serial] = row_idx
            data_map[serial] = {
                'name': name,
                'hsn': hsn,
                'mrp': mrp,
                'gst': gst,
                'row': row_idx
            }
        
        except Exception as e:
            logger.warning(f"[BULK_VALIDATE] Error validating row {row_idx}: {e}")
            errors.append(f"Row {row_idx}: Unexpected error - {str(e)[:50]}")
            continue
    
    is_valid = len(errors) == 0
    logger.info(f"[BULK_VALIDATE] Complete - Valid: {is_valid}, Errors: {len(errors)}, Items: {len(data_map)}")
    
    return is_valid, errors, data_map


async def batch_update_store_items(
    admin_id: int,
    data_map: Dict,
    dry_run: bool = False
) -> Tuple[bool, Dict, List]:
    """
    PHASE 2: Atomic batch update with transaction
    
    Args:
        admin_id: Admin user ID for audit logging
        data_map: Dict[serial → item_data] from validate_excel_data
        dry_run: If True, validate only without committing
    
    Returns:
        (success: bool, changes_made: Dict[serial → change_info], failed_serials: List[{serial, error}])
    """
    from src.database.connection import execute_query, get_db_connection
    
    changes_made = {}
    failed_serials = []
    
    logger.info(f"[BULK_UPDATE] PHASE 2 START - Mode: {'DRY_RUN' if dry_run else 'COMMIT'}")
    logger.info(f"[BULK_UPDATE] Processing {len(data_map)} items...")
    
    connection = None
    cursor = None
    
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # BEGIN TRANSACTION
        cursor.execute("START TRANSACTION")
        logger.info("[BULK_UPDATE] Transaction started")
        
        for serial, new_data in data_map.items():
            try:
                # Get current data
                cursor.execute(
                    "SELECT name, hsn, mrp, gst FROM store_items WHERE serial = %s",
                    (serial,)
                )
                existing_row = cursor.fetchone()
                
                if not existing_row:
                    failed_serials.append({
                        'serial': serial,
                        'error': 'Serial not found in database'
                    })
                    logger.warning(f"[BULK_UPDATE] Serial #{serial} not found")
                    continue
                
                # Build old data dict
                old_data = {
                    'name': existing_row['name'],
                    'hsn': existing_row['hsn'],
                    'mrp': float(existing_row['mrp']),
                    'gst': float(existing_row['gst'])
                }
                
                # ATOMIC UPDATE: Replace ALL fields
                cursor.execute(
                    """
                    UPDATE store_items 
                    SET name = %s, hsn = %s, mrp = %s, gst = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE serial = %s
                    """,
                    (
                        new_data['name'],
                        new_data['hsn'],
                        new_data['mrp'],
                        new_data['gst'],
                        serial
                    )
                )
                
                # Track what changed
                changes = []
                if old_data['name'] != new_data['name']:
                    changes.append(f"Name: '{old_data['name']}' → '{new_data['name']}'")
                if old_data['hsn'] != new_data['hsn']:
                    changes.append(f"HSN: {old_data['hsn']} → {new_data['hsn']}")
                if float(old_data['mrp']) != float(new_data['mrp']):
                    changes.append(f"MRP: ₹{old_data['mrp']} → ₹{new_data['mrp']}")
                if float(old_data['gst']) != float(new_data['gst']):
                    changes.append(f"GST: {old_data['gst']}% → {new_data['gst']}%")
                
                if changes:
                    changes_made[serial] = {
                        'name': new_data['name'],
                        'changes': changes
                    }
                    logger.info(f"[BULK_UPDATE] Updated #{serial}: {', '.join(changes)}")
                    
                    # Log audit entry (only if not dry run)
                    if not dry_run:
                        cursor.execute(
                            """
                            INSERT INTO audit_log (user_id, entity_type, entity_id, action, old_value, new_value, created_at)
                            VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                            """,
                            (
                                admin_id,
                                'store_items',
                                serial,
                                'bulk_upload_update',
                                json.dumps(old_data, default=str),
                                json.dumps(new_data, default=str)
                            )
                        )
        
        # COMMIT or ROLLBACK
        if dry_run:
            cursor.execute("ROLLBACK")
            logger.info("[BULK_UPDATE] DRY_RUN: Transaction rolled back (no changes committed)")
        else:
            cursor.execute("COMMIT")
            logger.info(f"[BULK_UPDATE] SUCCESS: Transaction committed - {len(changes_made)} items updated")
        
        return True, changes_made, failed_serials
    
    except Exception as e:
        logger.error(f"[BULK_UPDATE] ERROR: {str(e)}")
        if cursor:
            try:
                cursor.execute("ROLLBACK")
                logger.info("[BULK_UPDATE] Transaction rolled back due to error")
            except Exception as rollback_err:
                logger.error(f"[BULK_UPDATE] Rollback failed: {rollback_err}")
        return False, {}, []
    
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
            logger.info("[BULK_UPDATE] Database connection closed")


def format_validation_errors(errors: List[str], max_show: int = 10) -> str:
    """Format validation errors for display"""
    msg = "❌ *Validation Failed*\n\n*Errors Found:*\n"
    for err in errors[:max_show]:
        msg += f"• {err}\n"
    if len(errors) > max_show:
        msg += f"\n_...and {len(errors) - max_show} more errors_"
    return msg


def format_update_summary(changes_made: Dict, failed_serials: List, max_show: int = 15) -> str:
    """Format update results for display"""
    summary = (
        f"✅ *Bulk Upload Successful*\n\n"
        f"📊 *Summary:*\n"
        f"• ✏️ Items updated: {len(changes_made)}\n"
        f"• ⚠️ Failed: {len(failed_serials)}\n"
    )
    
    if changes_made:
        summary += f"\n📝 *Changes Made:*\n"
        for serial, change_info in list(changes_made.items())[:max_show]:
            summary += f"• *#{serial}* {change_info['name']}\n"
            for change in change_info['changes'][:3]:  # Show max 3 changes per item
                summary += f"  ◦ {change}\n"
        
        if len(changes_made) > max_show:
            summary += f"\n_...and {len(changes_made) - max_show} more items_"
    
    if failed_serials:
        summary += f"\n\n❌ *Failed Updates:*\n"
        for fail in failed_serials[:5]:
            summary += f"• Serial #{fail['serial']}: {fail['error']}\n"
        if len(failed_serials) > 5:
            summary += f"_...and {len(failed_serials) - 5} more_"
    
    return summary


def get_items_to_delete(excel_serials: List[int]) -> List[Dict]:
    """
    Get all items from database that are NOT in the Excel file.
    These items will be deleted to make Excel the complete source of truth.
    
    Args:
        excel_serials: List of serial numbers from Excel
    
    Returns:
        List of items to be deleted: [{serial, name, hsn, mrp, gst}, ...]
    """
    from src.database.connection import execute_query
    
    try:
        if not excel_serials:
            # If Excel is empty, all database items will be deleted
            query = "SELECT serial, name, hsn, mrp, gst FROM store_items ORDER BY serial"
            items = execute_query(query)
            logger.info(f"[BULK_DELETE] No serials in Excel - will delete all {len(items or [])} database items")
            return items or []
        
        # Get items NOT in Excel file
        placeholders = ','.join(['%s'] * len(excel_serials))
        query = f"SELECT serial, name, hsn, mrp, gst FROM store_items WHERE serial NOT IN ({placeholders}) ORDER BY serial"
        items = execute_query(query, tuple(excel_serials))
        logger.info(f"[BULK_DELETE] Found {len(items or [])} items to delete (not in Excel)")
        return items or []
    
    except Exception as e:
        logger.error(f"[BULK_DELETE] Error getting items to delete: {e}")
        return []


async def batch_replace_all_store_items(
    admin_id: int,
    data_map: Dict,
    dry_run: bool = False
) -> Tuple[bool, Dict, List, List]:
    """
    PHASE 2 EXTENDED: Atomic batch update + delete for complete replacement.
    Excel becomes the COMPLETE source of truth.
    
    This function:
    1. Updates all items from Excel (creates new if not found)
    2. Deletes all database items NOT in Excel
    3. All as a single atomic transaction (all-or-nothing)
    
    Args:
        admin_id: Admin user ID for audit logging
        data_map: Dict[serial → item_data] from validate_excel_data
        dry_run: If True, validate only without committing
    
    Returns:
        (success: bool, changes_made: Dict, failed_serials: List, deleted_items: List)
    """
    from src.database.connection import get_db_connection
    
    changes_made = {}
    failed_serials = []
    deleted_items = []
    
    logger.info(f"[BULK_REPLACE] PHASE 2 EXTENDED START - Mode: {'DRY_RUN' if dry_run else 'COMMIT'}")
    logger.info(f"[BULK_REPLACE] Excel serials to keep: {sorted(data_map.keys())}")
    
    connection = None
    cursor = None
    
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # BEGIN TRANSACTION
        cursor.execute("START TRANSACTION")
        logger.info("[BULK_REPLACE] Transaction started")
        
        # STEP 1: Update/Create items from Excel
        for serial, new_data in data_map.items():
            try:
                # Get current data
                cursor.execute(
                    "SELECT name, hsn, mrp, gst FROM store_items WHERE serial = %s",
                    (serial,)
                )
                existing_row = cursor.fetchone()
                
                if existing_row:
                    # EXISTING ITEM: Update
                    old_data = {
                        'name': existing_row['name'],
                        'hsn': existing_row['hsn'],
                        'mrp': float(existing_row['mrp']),
                        'gst': float(existing_row['gst'])
                    }
                    
                    cursor.execute(
                        """
                        UPDATE store_items 
                        SET name = %s, hsn = %s, mrp = %s, gst = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE serial = %s
                        """,
                        (
                            new_data['name'],
                            new_data['hsn'],
                            new_data['mrp'],
                            new_data['gst'],
                            serial
                        )
                    )
                    
                    # Track changes
                    changes = []
                    if old_data['name'] != new_data['name']:
                        changes.append(f"Name: '{old_data['name']}' → '{new_data['name']}'")
                    if old_data['hsn'] != new_data['hsn']:
                        changes.append(f"HSN: {old_data['hsn']} → {new_data['hsn']}")
                    if float(old_data['mrp']) != float(new_data['mrp']):
                        changes.append(f"MRP: ₹{old_data['mrp']} → ₹{new_data['mrp']}")
                    if float(old_data['gst']) != float(new_data['gst']):
                        changes.append(f"GST: {old_data['gst']}% → {new_data['gst']}%")
                    
                    if changes:
                        changes_made[serial] = {
                            'name': new_data['name'],
                            'changes': changes
                        }
                        logger.info(f"[BULK_REPLACE] Updated #{serial}: {', '.join(changes)}")
                        
                        # Audit log
                        if not dry_run:
                            cursor.execute(
                                """
                                INSERT INTO audit_log (user_id, entity_type, entity_id, action, old_value, new_value, created_at)
                                VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                                """,
                                (
                                    admin_id,
                                    'store_items',
                                    serial,
                                    'bulk_replace_update',
                                    json.dumps(old_data, default=str),
                                    json.dumps(new_data, default=str)
                                )
                            )
                    else:
                        # No changes but item exists in Excel - log as "kept"
                        changes_made[serial] = {
                            'name': new_data['name'],
                            'changes': ['No changes (kept as-is)']
                        }
                        logger.info(f"[BULK_REPLACE] Kept #{serial}: {new_data['name']} (no changes)")
                else:
                    # NEW ITEM: Insert
                    cursor.execute(
                        """
                        INSERT INTO store_items (serial, name, hsn, mrp, gst)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (
                            serial,
                            new_data['name'],
                            new_data['hsn'],
                            new_data['mrp'],
                            new_data['gst']
                        )
                    )
                    
                    changes_made[serial] = {
                        'name': new_data['name'],
                        'changes': ['New item created']
                    }
                    logger.info(f"[BULK_REPLACE] Created new #{serial}: {new_data['name']}")
                    
                    # Audit log
                    if not dry_run:
                        cursor.execute(
                            """
                            INSERT INTO audit_log (user_id, entity_type, entity_id, action, old_value, new_value, created_at)
                            VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                            """,
                            (
                                admin_id,
                                'store_items',
                                serial,
                                'bulk_replace_create',
                                None,
                                json.dumps(new_data, default=str)
                            )
                        )
            
            except Exception as e:
                logger.error(f"[BULK_REPLACE] Error updating serial {serial}: {e}")
                failed_serials.append({'serial': serial, 'error': str(e)})
        
        # STEP 2: DELETE items NOT in Excel (complete replacement)
        excel_serials = list(data_map.keys())
        items_to_delete = get_items_to_delete(excel_serials)
        
        if items_to_delete:
            logger.info(f"[BULK_REPLACE] Deleting {len(items_to_delete)} items NOT in Excel")
            
            for item in items_to_delete:
                try:
                    serial = item['serial']
                    
                    # Delete the item
                    cursor.execute("DELETE FROM store_items WHERE serial = %s", (serial,))
                    
                    deleted_items.append({
                        'serial': serial,
                        'name': item['name'],
                        'hsn': item['hsn'],
                        'mrp': item['mrp'],
                        'gst': item['gst']
                    })
                    
                    logger.info(f"[BULK_REPLACE] Deleted #{serial}: {item['name']}")
                    
                    # Audit log deletion
                    if not dry_run:
                        cursor.execute(
                            """
                            INSERT INTO audit_log (user_id, entity_type, entity_id, action, old_value, new_value, created_at)
                            VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                            """,
                            (
                                admin_id,
                                'store_items',
                                serial,
                                'bulk_replace_delete',
                                json.dumps({
                                    'name': item['name'],
                                    'hsn': item['hsn'],
                                    'mrp': item['mrp'],
                                    'gst': item['gst']
                                }, default=str),
                                None
                            )
                        )
                
                except Exception as e:
                    logger.error(f"[BULK_REPLACE] Error deleting serial {serial}: {e}")
        
        # COMMIT or ROLLBACK
        if dry_run:
            cursor.execute("ROLLBACK")
            logger.info("[BULK_REPLACE] DRY_RUN: Transaction rolled back")
        else:
            cursor.execute("COMMIT")
            logger.info(f"[BULK_REPLACE] SUCCESS: Committed - {len(changes_made)} items processed, {len(deleted_items)} deleted")
        
        return True, changes_made, failed_serials, deleted_items
    
    except Exception as e:
        logger.error(f"[BULK_REPLACE] ERROR: {str(e)}")
        if cursor:
            try:
                cursor.execute("ROLLBACK")
                logger.info("[BULK_REPLACE] Transaction rolled back due to error")
            except Exception as rollback_err:
                logger.error(f"[BULK_REPLACE] Rollback failed: {rollback_err}")
        return False, {}, [], []
    
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
            logger.info("[BULK_REPLACE] Database connection closed")


def format_replace_all_summary(
    changes_made: Dict,
    failed_serials: List,
    deleted_items: List,
    max_show: int = 10
) -> str:
    """
    Format complete replacement results for display.
    Shows items that were updated/kept and items that were deleted.
    """
    summary = (
        f"✅ *Bulk Replace Complete*\n\n"
        f"📊 *Summary:*\n"
        f"• ✏️ Items kept/updated: {len(changes_made)}\n"
        f"• 🗑️ Items deleted: {len(deleted_items)}\n"
        f"• ⚠️ Failed: {len(failed_serials)}\n"
    )
    
    if deleted_items:
        summary += f"\n🗑️ *Deleted Items (not in Excel):*\n"
        for item in deleted_items[:max_show]:
            summary += f"• ~~#{item['serial']} {item['name']}~~ (HSN: {item['hsn']})\n"
        if len(deleted_items) > max_show:
            summary += f"_...and {len(deleted_items) - max_show} more deleted_\n"
    
    if changes_made:
        summary += f"\n✏️ *Kept/Updated Items:*\n"
        for serial, change_info in list(changes_made.items())[:max_show]:
            summary += f"• *#{serial}* {change_info['name']}\n"
        if len(changes_made) > max_show:
            summary += f"_...and {len(changes_made) - max_show} more items_\n"
    
    if failed_serials:
        summary += f"\n❌ *Failed:*\n"
        for fail in failed_serials[:5]:
            summary += f"• Serial #{fail['serial']}: {fail['error']}\n"
    
    summary += f"\n_✅ Excel is now the complete source of truth._"
    
    return summary
