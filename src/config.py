import os
from dotenv import load_dotenv
from pathlib import Path
import logging

# Load .env (do not override system env unless explicitly set)
load_dotenv(override=False)

logger = logging.getLogger(__name__)

# Environment mode flags
USE_LOCAL_DB = os.getenv('USE_LOCAL_DB', 'true').lower() in ('1', 'true', 'yes')
USE_REMOTE_DB = os.getenv('USE_REMOTE_DB', 'false').lower() in ('1', 'true', 'yes')
ENV = os.getenv('ENV', 'local')

if USE_LOCAL_DB and USE_REMOTE_DB:
    raise RuntimeError("Config error: USE_LOCAL_DB and USE_REMOTE_DB cannot both be true")

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN') or ''

# In local/test mode, we still need the bot token to run polling
# Commented out to allow bot to run with local DB
# if USE_LOCAL_DB:
#     TELEGRAM_BOT_TOKEN = ''
SUPER_ADMIN_PASSWORD = os.getenv('SUPER_BOT_PASSWORD', 'ChangeMe123!')
SUPER_ADMIN_USER_ID = os.getenv('SUPER_ADMIN_USER_ID', '0')

# Database config only used when USE_REMOTE_DB is True
DATABASE_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', '3306')),
    'database': os.getenv('DB_NAME', 'fitness_club_db'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASS', os.getenv('DB_PASSWORD', '')),
}

# Data directory and canonical file paths (local-only sources)
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / 'data'
USERS_FILE = str(DATA_DIR / 'users.json')
STORE_ITEMS_FILE = str(DATA_DIR / 'store_items.json')
INVOICES_V2_FILE = str(DATA_DIR / 'invoices_v2.json')

# Geofence for studio check-in (set in .env)
def _to_float(val: str, default: float) -> float:
    try:
        return float(val)
    except Exception:
        return default

GEOFENCE_LAT = _to_float(os.getenv('GEOFENCE_LAT', '0'), 0.0)
GEOFENCE_LNG = _to_float(os.getenv('GEOFENCE_LNG', '0'), 0.0)
GEOFENCE_RADIUS_M = int(os.getenv('GEOFENCE_RADIUS_M', '10'))

# Minimal feature flags and defaults
POINTS_CONFIG = {
    'attendance': 50,
    'weight_log': 10,
    'water_500ml': 5,
    'meal_photo': 15,
    'habits_complete': 20,
}

FEES_CONFIG = {
    'monthly': 500,
    'quarterly': 1200,
    'yearly': 4000,
}

logger.info(f"[CONFIG] mode={'local' if USE_LOCAL_DB else 'remote' if USE_REMOTE_DB else ENV}")
