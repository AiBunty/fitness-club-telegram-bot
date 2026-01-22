#!/usr/bin/env python3
"""
Bot launcher script that keeps restarting the bot when it exits.
This is a workaround for python-telegram-bot v21 which runs polling once and exits.
"""

import subprocess
import sys
import time
import os
import logging

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def run_bot_with_restart():
    """Run the bot with automatic restart on exit."""
    
    attempt = 0
    max_attempts = 1000  # Essentially unlimited
    
    # Environment variables to pass to bot
    env_vars = os.environ.copy()
    env_vars['SKIP_SCHEDULING'] = '1'
    env_vars['SKIP_FLASK'] = '1'
    env_vars['PYTHONUNBUFFERED'] = '1'
    
    logger.info("=" * 60)
    logger.info("BOT LAUNCHER - Starting bot with automatic restart")
    logger.info("=" * 60)
    logger.info("")
    
    while attempt < max_attempts:
        attempt += 1
        
        logger.info(f"[BOT LAUNCHER] Starting attempt {attempt}...")
        
        try:
            # Run the bot  
            proc = subprocess.Popen(
                [sys.executable, 'start_bot.py'],
                cwd=os.path.dirname(os.path.abspath(__file__)),
                env=env_vars,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1  # Line buffered
            )
            
            logger.info(f"[BOT LAUNCHER] Bot process started with PID {proc.pid}")
            
            # Wait for process to complete
            returncode = proc.wait()
            
            logger.info(f"[BOT LAUNCHER] Bot exited with code {returncode}")
            
            # Restart delay
            logger.info("[BOT LAUNCHER] Restarting in 3 seconds...")
            time.sleep(3)
            
        except KeyboardInterrupt:
            logger.info("[BOT LAUNCHER] Interrupted by user (Ctrl+C)")
            sys.exit(0)
        except Exception as e:
            logger.error(f"[BOT LAUNCHER] Error running bot: {type(e).__name__}: {e}")
            logger.info("[BOT LAUNCHER] Restarting in 5 seconds...")
            time.sleep(5)
    
    logger.error(f"[BOT LAUNCHER] Max attempts ({max_attempts}) reached - shutting down")

if __name__ == '__main__':
    run_bot_with_restart()
