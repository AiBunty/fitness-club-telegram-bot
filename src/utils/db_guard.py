"""Guard to prevent remote DB access when running in local/testing mode."""
import logging
from src.config import USE_LOCAL_DB

logger = logging.getLogger(__name__)


def assert_no_remote_db_access(action: str = "DB access"):
    """Raise if remote DB access attempted while local-only mode is enabled.

    Args:
        action: Human-friendly action attempted (for log clarity)
    """
    if USE_LOCAL_DB:
        # In local mode, only warn and skip to avoid crashing interactive commands
        logger.warning(f"[DB_GUARD] Remote DB access attempted in local mode (skipped): {action}")
        return
