"""
Flow State Management - Exclusive Conversational Flow Locking

This module enforces that only ONE conversational flow is active per admin at a time.
All handlers must check if they own the current flow before processing messages.

Flow State Registry:
  active_flows[admin_id] = "INVOICE_CREATE" | "DELETE_USER" | "BAN_USER" | etc. | None

Rules:
  1. Entry handler sets active_flows[admin_id] = FLOW_NAME
  2. All text/callback handlers check active_flows[admin_id] == THIS_FLOW_NAME
  3. If mismatch: ignore message, return None or ConversationHandler.END
  4. On complete/cancel: clear active_flows[admin_id] = None
"""

import logging
from typing import Optional, Dict
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

# Flow name constants
FLOW_DELETE_USER = "DELETE_USER"
FLOW_BAN_USER = "BAN_USER"
FLOW_UNBAN_USER = "UNBAN_USER"
FLOW_INVOICE_CREATE = "INVOICE_CREATE"
FLOW_INVOICE_V2_CREATE = "INVOICE_V2_CREATE"
FLOW_AR_RECORD_PAYMENT = "AR_RECORD_PAYMENT"
FLOW_STORE_ITEM_CREATE = "STORE_ITEM_CREATE"
FLOW_STORE_ITEM_EDIT = "STORE_ITEM_EDIT"
FLOW_BROADCAST = "BROADCAST"
FLOW_PAYMENT_REQUEST = "PAYMENT_REQUEST"

# Global flow registry: admin_id -> active flow name
active_flows: Dict[int, Optional[str]] = {}


def set_active_flow(admin_id: int, flow_name: str) -> None:
    """Set the active flow for an admin"""
    if admin_id in active_flows:
        logger.warning(
            f"[FLOW] admin={admin_id} replacing_flow={active_flows[admin_id]} with_new_flow={flow_name}"
        )
    active_flows[admin_id] = flow_name
    logger.info(f"[FLOW] admin={admin_id} started={flow_name}")


def get_active_flow(admin_id: int) -> Optional[str]:
    """Get the active flow for an admin"""
    return active_flows.get(admin_id)


def is_flow_active(admin_id: int, flow_name: str) -> bool:
    """Check if a specific flow is active for an admin"""
    return active_flows.get(admin_id) == flow_name


def clear_active_flow(admin_id: int, flow_name: Optional[str] = None) -> None:
    """Clear the active flow for an admin (optionally verify it matches expected flow)"""
    current = active_flows.get(admin_id)
    
    if flow_name and current != flow_name:
        logger.warning(
            f"[FLOW] admin={admin_id} clear_mismatch expected={flow_name} actual={current}"
        )
        return
    
    if admin_id in active_flows:
        del active_flows[admin_id]
    logger.info(f"[FLOW] admin={admin_id} cleared flow={flow_name or current}")


def check_flow_ownership(
    admin_id: int, 
    expected_flow: str,
    operation: str = "process_message"
) -> bool:
    """
    Check if admin owns the expected flow. Log if blocked.
    
    Usage:
        if not check_flow_ownership(admin_id, FLOW_INVOICE_CREATE):
            return ConversationHandler.END  # or None, depending on context
    
    Returns:
        True if flow is owned, False if blocked
    """
    current_flow = get_active_flow(admin_id)
    
    if current_flow == expected_flow:
        return True
    
    if current_flow:
        logger.warning(
            f"[FLOW] admin={admin_id} blocked {operation} "
            f"expected={expected_flow} active={current_flow}"
        )
    
    return False


async def guard_flow_ownership(
    admin_id: int,
    expected_flow: str,
    context: ContextTypes.DEFAULT_TYPE,
    update = None
) -> bool:
    """
    Async guard for flow ownership. Can optionally send warning message to user.
    
    Usage in handlers:
        if not await guard_flow_ownership(admin_id, FLOW_INVOICE_CREATE, context, update):
            return ConversationHandler.END
    
    Returns:
        True if flow is owned, False if blocked
    """
    if check_flow_ownership(admin_id, expected_flow):
        return True
    
    current_flow = get_active_flow(admin_id)
    logger.warning(
        f"[FLOW] admin={admin_id} blocked operation "
        f"expected={expected_flow} active={current_flow}"
    )
    
    # Optionally send warning if update provided
    if update and current_flow:
        try:
            if update.callback_query:
                await update.callback_query.answer(
                    f"⚠️ You are in {current_flow} flow. Complete or cancel it first.",
                    show_alert=False
                )
            elif update.message:
                await update.message.reply_text(
                    f"⚠️ You are in {current_flow} flow. Complete or cancel it first."
                )
        except Exception as e:
            logger.error(f"[FLOW] Could not send guard warning: {e}")
    
    return False


def debug_flows() -> str:
    """Get debug info about all active flows"""
    if not active_flows:
        return "[FLOW DEBUG] No active flows"
    
    lines = ["[FLOW DEBUG] Active flows:"]
    for admin_id, flow_name in sorted(active_flows.items()):
        lines.append(f"  admin={admin_id} flow={flow_name}")
    
    return "\n".join(lines)
