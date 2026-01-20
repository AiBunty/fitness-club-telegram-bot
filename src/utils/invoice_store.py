import json
import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

STORE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
INVOICE_FILE = os.path.join(STORE_PATH, 'invoices.json')


def _ensure_store():
    try:
        if not os.path.exists(STORE_PATH):
            os.makedirs(STORE_PATH, exist_ok=True)
        if not os.path.exists(INVOICE_FILE):
            with open(INVOICE_FILE, 'w', encoding='utf-8') as f:
                json.dump({}, f)
    except Exception as e:
        logger.error(f"Failed ensuring invoice store: {e}")


def save_invoice(invoice_id: int, payload: Dict[str, Any]):
    _ensure_store()
    try:
        with open(INVOICE_FILE, 'r+', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except Exception:
                data = {}
            data[str(invoice_id)] = payload
            f.seek(0)
            json.dump(data, f, indent=2)
            f.truncate()
    except Exception as e:
        logger.error(f"Error saving invoice {invoice_id}: {e}")


def load_invoice(invoice_id: int) -> Dict[str, Any]:
    _ensure_store()
    try:
        with open(INVOICE_FILE, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                return data.get(str(invoice_id), {})
            except Exception as e:
                logger.error(f"Error reading invoice file: {e}")
                return {}
    except Exception as e:
        logger.error(f"Error loading invoice {invoice_id}: {e}")
        return {}


def delete_invoice(invoice_id: int):
    _ensure_store()
    try:
        with open(INVOICE_FILE, 'r+', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except Exception:
                data = {}
            if str(invoice_id) in data:
                del data[str(invoice_id)]
                f.seek(0)
                json.dump(data, f, indent=2)
                f.truncate()
    except Exception as e:
        logger.error(f"Error deleting invoice {invoice_id}: {e}")