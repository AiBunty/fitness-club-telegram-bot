import json
import os
from typing import Dict, Any

STORE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
INVOICE_FILE = os.path.join(STORE_PATH, 'invoices.json')


def _ensure_store():
    if not os.path.exists(STORE_PATH):
        os.makedirs(STORE_PATH, exist_ok=True)
    if not os.path.exists(INVOICE_FILE):
        with open(INVOICE_FILE, 'w', encoding='utf-8') as f:
            json.dump({}, f)


def save_invoice(invoice_id: int, payload: Dict[str, Any]):
    _ensure_store()
    with open(INVOICE_FILE, 'r+', encoding='utf-8') as f:
        data = json.load(f)
        data[str(invoice_id)] = payload
        f.seek(0)
        json.dump(data, f, indent=2)
        f.truncate()


def load_invoice(invoice_id: int) -> Dict[str, Any]:
    _ensure_store()
    with open(INVOICE_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get(str(invoice_id), {})


def delete_invoice(invoice_id: int):
    _ensure_store()
    with open(INVOICE_FILE, 'r+', encoding='utf-8') as f:
        data = json.load(f)
        if str(invoice_id) in data:
            del data[str(invoice_id)]
            f.seek(0)
            json.dump(data, f, indent=2)
            f.truncate()