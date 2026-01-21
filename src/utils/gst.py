import json
from typing import Dict
from pathlib import Path

GST_PATH = Path(__file__).resolve().parent.parent / 'data' / 'gst_config.json'


def load_gst_config() -> Dict:
    try:
        with open(GST_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {"enabled": False, "mode": "exclusive", "percent": 0}


def save_gst_config(cfg: Dict):
    with open(GST_PATH, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=2)


def is_gst_enabled() -> bool:
    return bool(load_gst_config().get('enabled'))


def get_gst_mode() -> str:
    return load_gst_config().get('mode', 'exclusive')


def get_gst_percent() -> float:
    return float(load_gst_config().get('percent', 0) or 0)
