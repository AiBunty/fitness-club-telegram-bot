"""
Simple file-backed message template manager.
- Stores templates in `config/message_templates.json` (created if missing)
- Validates placeholders against `event_registry.ALLOWED_PLACEHOLDERS`
- Appends audit entries to `logs/message_template_audit.log`

This is intentionally file-backed to avoid DB schema changes.
"""
import json
import os
import time
from datetime import datetime
from pathlib import Path
from src.utils import event_registry

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_PATH = ROOT / 'config' / 'message_templates.json'
AUDIT_LOG = ROOT / 'logs' / 'message_template_audit.log'


def _ensure_storage():
    TEMPLATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not TEMPLATE_PATH.exists():
        # initialize with defaults
        data = {}
        for k in event_registry.EVENT_KEYS:
            data[k] = {
                'enabled': True,
                'text': event_registry.DEFAULT_TEMPLATES.get(k, ''),
                'buttons': []
            }
        with open(TEMPLATE_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)


def load_templates():
    _ensure_storage()
    with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_template(event_key):
    templates = load_templates()
    return templates.get(event_key)


def _validate_placeholders(event_key, text):
    # Find {{placeholder}} tokens
    toks = set()
    i = 0
    while True:
        a = text.find('{{', i)
        if a == -1:
            break
        b = text.find('}}', a)
        if b == -1:
            break
        key = text[a+2:b].strip()
        if key:
            toks.add(key)
        i = b+2

    allowed = event_registry.ALLOWED_PLACEHOLDERS.get(event_key, set())
    # tokens must be subset of allowed; unknown tokens are rejected
    unknown = toks - allowed
    if unknown:
        return False, unknown
    return True, toks


def save_template(admin_id, event_key, new_text=None, enabled=None, buttons=None):
    _ensure_storage()
    templates = load_templates()
    if event_key not in templates:
        raise ValueError('Unknown event_key')

    old = templates[event_key].copy()

    if new_text is not None:
        ok, info = _validate_placeholders(event_key, new_text)
        if not ok:
            raise ValueError(f"Unknown placeholders: {info}")
        templates[event_key]['text'] = new_text

    if enabled is not None:
        templates[event_key]['enabled'] = bool(enabled)

    if buttons is not None:
        # simple validation: list of dicts with text and callback_data
        if not isinstance(buttons, list):
            raise ValueError('buttons must be a list')
        templates[event_key]['buttons'] = buttons

    with open(TEMPLATE_PATH, 'w', encoding='utf-8') as f:
        json.dump(templates, f, indent=2, ensure_ascii=False)

    # Audit log
    entry = {
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'admin_id': admin_id,
        'event_key': event_key,
        'old': old,
        'new': templates[event_key]
    }
    with open(AUDIT_LOG, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')


def tail_audit(limit=50):
    _ensure_storage()
    if not AUDIT_LOG.exists():
        return []
    lines = []
    with open(AUDIT_LOG, 'r', encoding='utf-8') as f:
        for l in f:
            l = l.strip()
            if l:
                try:
                    lines.append(json.loads(l))
                except Exception:
                    # skip malformed
                    pass
    return lines[-limit:]

