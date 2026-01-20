import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
SUPER_ADMIN_PASSWORD = os.getenv('SUPER_ADMIN_PASSWORD', 'ChangeMe123!')
SUPER_ADMIN_USER_ID = os.getenv('SUPER_ADMIN_USER_ID', '0')

DATABASE_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'fitness_club_db'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', '')
}

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

# Geofence for studio check-in (set in .env)
def _to_float(val: str, default: float) -> float:
    try:
        return float(val)
    except Exception:
        return default

GEOFENCE_LAT = _to_float(os.getenv('GEOFENCE_LAT', '0'), 0.0)
GEOFENCE_LNG = _to_float(os.getenv('GEOFENCE_LNG', '0'), 0.0)
GEOFENCE_RADIUS_M = int(os.getenv('GEOFENCE_RADIUS_M', '10'))

# Gym Studio profile defaults (editable via admin settings)
GYM_PROFILE = {
    'name': os.getenv('GYM_NAME', 'Wanis Level Up Studio'),
    'address': os.getenv('GYM_ADDRESS', '101, 1st floor, Padma Vishwa Orchid,\nCricket Ground, opposite Doctor BS Moonje Marg,\nabove Pepperfry Showroom,\nMahatma Nagar, Parijat Nagar,\nNashik, Maharashtra 422005'),
    'phone': os.getenv('GYM_PHONE', '091582 43377'),
    'gst': os.getenv('GYM_GST', ''),
    'logo_url': os.getenv('GYM_LOGO_URL', ''),
    'timings': os.getenv('GYM_TIMINGS', 'Mon–Sat: 6–11 AM, 5–9 PM\nSunday: Closed'),
    'facebook': os.getenv('GYM_FACEBOOK', 'https://www.facebook.com/wanisclublevelup'),
    'instagram': os.getenv('GYM_INSTAGRAM', 'https://www.instagram.com/wanisclub_levelup')
}
