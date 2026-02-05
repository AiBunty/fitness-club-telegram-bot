#!/usr/bin/env python3
"""Normalize invoice records to include telegram_id and keep user_id in sync.

- If telegram_id missing, set from user_id.
- If user_id missing, set from telegram_id.
- Ensure both are ints where possible.

This script updates data/invoices_v2.json in-place.
"""
import json
import os
from typing import Any

INVOICES_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "invoices_v2.json")


def _to_int(value: Any):
    try:
        ivalue = int(value)
        return ivalue if ivalue > 0 else None
    except Exception:
        return None


def main():
    if not os.path.exists(INVOICES_FILE):
        print(f"No invoices file found at {INVOICES_FILE}")
        return

    with open(INVOICES_FILE, "r", encoding="utf-8") as f:
        invoices = json.load(f) or []

    updated = 0
    for inv in invoices:
        user_id = _to_int(inv.get("user_id"))
        telegram_id = _to_int(inv.get("telegram_id"))

        if not telegram_id and user_id:
            inv["telegram_id"] = user_id
            updated += 1
        elif not user_id and telegram_id:
            inv["user_id"] = telegram_id
            updated += 1
        elif telegram_id and user_id and telegram_id != user_id:
            # Prefer telegram_id as source of truth
            inv["user_id"] = telegram_id
            updated += 1

    with open(INVOICES_FILE, "w", encoding="utf-8") as f:
        json.dump(invoices, f, indent=2)

    print(f"Updated invoices: {updated}")


if __name__ == "__main__":
    main()
