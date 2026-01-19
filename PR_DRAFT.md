PR: Harden DB, ownership-scope fixes, Event Store, monitoring, tests
===============================================================

Summary
-------
- Harden DB connection pool handling to avoid returning closed connections.
- Add Event Store scaffolding: migrations, `events`, `event_registrations`, `revenue`.
- Add `payment_approvals` thin wrappers and refactor handlers to use them.
- Fix ownership-scope leaks (high-priority fixes): corrected `shake_flavors` JOIN, guarded reminder increments, safer scheduled jobs.
- Add lightweight monitoring and diagnostics (`src/utils/monitoring.py`, `tools/run_monitoring_test.py`, `tools/ownership_checks.py`).
- Add non-destructive integration tests for payment approval flows (`tests/integration/test_payment_approvals.py`).

Migrations
----------
- `migrate_events_and_revenue.py` — creates `events`, `event_registrations`, `revenue` (applied to staging).
- Store migration: `migrate_store.py` ensures `store_orders` schema contains `payment_status`.

Tests
-----
- Integration tests added and executed locally in staging env: `tests/integration/test_payment_approvals.py` (2 passed).

Files Changed / Added (high level)
---------------------------------
- src/database/connection.py (pool hardening)
- src/database/event_operations.py (event CRUD + registration workflows)
- src/database/payment_approvals.py (approval wrappers)
- src/handlers/* (refactored to use wrappers)
- src/utils/monitoring.py
- src/utils/scheduled_jobs.py (guarded updates, expiry job)
- migrate_events_and_revenue.py
- tests/integration/test_payment_approvals.py

Notes & Next Steps
------------------
1. Finish remaining ownership-scope low-priority fixes (ledger-authoritative admin deduction updates).
2. Run full verification in staging (smoke tests + scheduled job run-through).
3. Prepare PR for review with this draft as description.

Request
-------
Please review the summary and let me know if you want me to prepare the PR branch and push commits, or if you'd like additional changes before opening the PR.
