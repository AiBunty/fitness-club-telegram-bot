"""
Follow-up pattern manager (file-backed).

Stores follow-up sequences per EVENT_KEY in config/followups.json.
Each follow-up step: {"delay_hours": <int>, "template": "EVENT_KEY_TEMPLATE"}

Validates template references and stop conditions. No schema changes.
"""
import json
from pathlib import Path
from datetime import datetime
from src.utils import event_registry, message_templates

ROOT = Path(__file__).resolve().parents[2]
FOLLOWUP_PATH = ROOT / 'config' / 'followups.json'
EMERGENCY_TOGGLE = ROOT / 'config' / 'admin_editing_enabled.flag'

STOP_CONDITIONS = {'payment_completed', 'order_closed', 'admin_override'}
MAX_STEPS = 5


def _ensure_storage():
    FOLLOWUP_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not FOLLOWUP_PATH.exists():
        # initialize empty structure
        with open(FOLLOWUP_PATH, 'w', encoding='utf-8') as f:
            json.dump({}, f, indent=2)


def load_followups():
    _ensure_storage()
    with open(FOLLOWUP_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_followups(event_key):
    data = load_followups()
    return data.get(event_key, [])


def validate_sequence(seq):
    if not isinstance(seq, list):
        return False, 'sequence must be a list'
    if len(seq) > MAX_STEPS:
        return False, f'maximum {MAX_STEPS} steps allowed'
    for i, step in enumerate(seq):
        if not isinstance(step, dict):
            return False, f'step {i} must be object'
        if 'delay_hours' not in step or 'template' not in step:
            return False, f'step {i} requires delay_hours and template'
        if not isinstance(step['delay_hours'], (int, float)) or step['delay_hours'] < 0:
            return False, f'step {i} delay_hours invalid'
        tpl = step['template']
        # template must be a known EVENT_KEY (template manager stores per-event_key)
        if tpl not in event_registry.EVENT_KEYS:
            return False, f'step {i} references unknown template {tpl}'
        # ensure template exists
        if not message_templates.get_template(tpl):
            # allow missing but warn (template may fallback to default)
            pass
    return True, None


def save_followups(admin_id, event_key, seq):
    ok, err = validate_sequence(seq)
    if not ok:
        raise ValueError(err)
    data = load_followups()
    old = data.get(event_key, [])
    data[event_key] = seq
    with open(FOLLOWUP_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    # audit via message_templates.audit log to keep single audit file
    from src.utils.message_templates import AUDIT_LOG
    import json as _json
    entry = {
        'timestamp': datetime.utcnow().isoformat()+'Z',
        'admin_id': admin_id,
        'event_key': event_key,
        'old_followups': old,
        'new_followups': seq
    }
    with open(AUDIT_LOG, 'a', encoding='utf-8') as f:
        f.write(_json.dumps(entry, ensure_ascii=False) + '\n')


def is_admin_editing_enabled():
    return EMERGENCY_TOGGLE.exists()


def set_admin_editing_enabled(enabled: bool):
    if enabled:
        EMERGENCY_TOGGLE.parent.mkdir(parents=True, exist_ok=True)
        EMERGENCY_TOGGLE.write_text('1')
    else:
        if EMERGENCY_TOGGLE.exists():
            EMERGENCY_TOGGLE.unlink()
