import json
from pathlib import Path
from typing import Dict, List
from src.config import DATA_DIR
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

INVOICES_PATH = Path(DATA_DIR) / 'invoices.json'


def load_invoices() -> Dict:
    if not INVOICES_PATH.exists():
        return {}
    try:
        with open(INVOICES_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"[INVOICE] failed to load invoices: {e}")
        return {}


def save_invoices(data: Dict) -> None:
    try:
        INVOICES_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(INVOICES_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"[INVOICE] invoice_store_saved count={len(data)} path={INVOICES_PATH}")
    except Exception as e:
        logger.error(f"[INVOICE] failed to save invoices: {e}")


def _next_invoice_id(invoices: Dict) -> str:
    # Invoice ids like INV-0001
    existing = list(invoices.keys())
    nums = [int(k.split('-')[-1]) for k in existing if k.startswith('INV-') and k.split('-')[-1].isdigit()]
    next_n = (max(nums) + 1) if nums else 1
    return f"INV-{next_n:04d}"


def create_invoice(payload: Dict) -> Dict:
    invoices = load_invoices()
    inv_id = _next_invoice_id(invoices)
    now = datetime.utcnow().isoformat()
    invoice = {
        'invoice_id': inv_id,
        'user_id': payload.get('user_id'),
        'items': payload.get('items', []),
        'subtotal': float(payload.get('subtotal', 0)),
        'gst': float(payload.get('gst', 0)),
        'shipping': float(payload.get('shipping', 0)),
        'total': float(payload.get('total', 0)),
        'status': 'pending',
        'created_at': now,
        'paid_at': None
    }
    invoices[inv_id] = invoice
    save_invoices(invoices)
    logger.info(f"[INVOICE] invoice_saved id={inv_id} user_id={invoice.get('user_id')}")
    return invoice


def mark_invoice_paid(invoice_id: str) -> bool:
    invoices = load_invoices()
    inv = invoices.get(invoice_id)
    if not inv:
        return False
    inv['status'] = 'paid'
    inv['paid_at'] = datetime.utcnow().isoformat()
    save_invoices(invoices)
    logger.info(f"[INVOICE] invoice_paid id={invoice_id}")
    return True


def get_invoice(invoice_id: str) -> Dict:
    invoices = load_invoices()
    return invoices.get(invoice_id)


def delete_invoice(invoice_id: str) -> bool:
    invoices = load_invoices()
    if invoice_id in invoices:
        del invoices[invoice_id]
        save_invoices(invoices)
        logger.info(f"[INVOICE] invoice_deleted id={invoice_id}")
        return True
    return False


def mark_invoice_rejected(invoice_id: str) -> bool:
    invoices = load_invoices()
    inv = invoices.get(invoice_id)
    if not inv:
        return False
    inv['status'] = 'rejected'
    save_invoices(invoices)
    logger.info(f"[INVOICE] invoice_rejected id={invoice_id}")
    return True
