import logging
from typing import List, Set
from src.config import SUPER_ADMIN_USER_ID
from src.database.role_operations import list_admins, list_staff

logger = logging.getLogger(__name__)

def get_moderator_chat_ids(include_staff: bool = True) -> List[int]:
    """Return unique chat IDs for super admin, admins, and optionally staff."""
    ids: Set[int] = set()
    if SUPER_ADMIN_USER_ID:
        try:
            ids.add(int(SUPER_ADMIN_USER_ID))
        except (TypeError, ValueError):
            logger.warning("SUPER_ADMIN_USER_ID is not a valid integer")

    for admin in list_admins() or []:
        if admin.get("user_id"):
            ids.add(int(admin["user_id"]))

    if include_staff:
        for staff in list_staff() or []:
            if staff.get("user_id"):
                ids.add(int(staff["user_id"]))

    return list(ids)
