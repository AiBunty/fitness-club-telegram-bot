"""
Production smoke test script (safe, opt-in).

This script performs lightweight checks that are useful as a quick production smoke test:
- Verify DB connectivity
- Verify job queue scheduling API can be created
- Optionally (if TELEGRAM_BOT_TOKEN and SUPER_ADMIN_USER_ID are set) send a harmless test message to the super-admin.

USAGE (run on production host with care):
  - Set environment variables appropriately (do NOT run this without perms):
    - RUN_PROD_SMOKE=1
    - TELEGRAM_BOT_TOKEN (optional, only for message send)
    - SUPER_ADMIN_USER_ID (optional)

  python scripts/production_smoke_test.py

The script will exit with non-zero code on failure.
"""
import os
import sys
import logging

from src.database.connection import test_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('smoke')


def main():
    if os.getenv('RUN_PROD_SMOKE', '0') != '1':
        logger.error('RUN_PROD_SMOKE not set to 1 - aborting to avoid accidental production calls')
        sys.exit(2)

    logger.info('Starting production smoke checks')

    # 1) DB connectivity
    ok = test_connection()
    if not ok:
        logger.error('DB connectivity test failed')
        sys.exit(3)
    logger.info('DB connectivity OK')

    # 2) Job queue sanity - instantiate Application.job_queue in dry-run
    try:
        from telegram.ext import Application
        application = Application.builder().token(os.getenv('TELEGRAM_BOT_TOKEN', '')).build()
        jq = application.job_queue
        logger.info('Job queue object created')
        # Clean up application resources
        application.stop()
    except Exception as e:
        logger.error(f'Job queue creation failed: {e}')
        sys.exit(4)

    # 3) Optional: send a harmless message to SUPER_ADMIN_USER_ID if token present
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    admin_id = os.getenv('SUPER_ADMIN_USER_ID')
    if bot_token and admin_id:
        try:
            from telegram import Bot
            b = Bot(token=bot_token)
            b.send_message(chat_id=int(admin_id), text='Smoke test: application & DB connectivity OK (no action taken)')
            logger.info('Sent optional smoke message to super-admin')
        except Exception as e:
            logger.error(f'Failed to send optional telegram message: {e}')
            # Not fatal

    logger.info('Smoke checks completed successfully')


if __name__ == '__main__':
    main()
