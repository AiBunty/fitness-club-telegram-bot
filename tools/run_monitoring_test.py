"""
Run monitoring checks with lowered thresholds for testing (read-only).

Usage: run with the project's venv Python. This script only reads data.
"""
import json
from datetime import date
from src.utils.monitoring import check_overdue_reminder_spike, check_bulk_expiry_candidates


def main():
    print('Running monitoring checks (test thresholds)...')
    spike = check_overdue_reminder_spike(minutes_window=60, threshold=1)
    print('overdue_reminder_spike:')
    print(json.dumps(spike, default=str, indent=2))

    bulk = check_bulk_expiry_candidates(date.today(), threshold=1)
    print('bulk_expiry_candidates:')
    print(json.dumps(bulk, default=str, indent=2))


if __name__ == '__main__':
    main()
