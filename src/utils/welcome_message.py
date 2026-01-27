"""DB-backed welcome message utilities."""

import logging
from src.database.app_settings_operations import get_app_setting, set_app_setting

logger = logging.getLogger(__name__)

DEFAULT_WELCOME_MESSAGE = (
    "👋 Welcome to Level Up Fitness!\n\n"
    "Track your workouts, log meals, and stay consistent.\n\n"
    "Please register to get started."
)


def get_welcome_message() -> str:
    """Fetch welcome message from DB with safe fallback to default."""
    try:
        msg = get_app_setting('WELCOME_MESSAGE')
        if msg:
            return msg
        # Seed default if missing
        set_app_setting('WELCOME_MESSAGE', DEFAULT_WELCOME_MESSAGE)
    except Exception as e:
        logger.warning(f"[WELCOME] falling back to default: {e}")
    return DEFAULT_WELCOME_MESSAGE


def update_welcome_message(new_message: str) -> None:
    """Persist a new welcome message to DB."""
    set_app_setting('WELCOME_MESSAGE', new_message)