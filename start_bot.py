#!/usr/bin/env python3
"""
Startup script that sets up Python path properly and runs the bot
"""

import sys
import os

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Force remote DB mode
os.environ['USE_LOCAL_DB'] = 'false'
os.environ['USE_REMOTE_DB'] = 'true'
os.environ['ENV'] = 'production'

# Now import and run the bot
from src.bot import main

if __name__ == '__main__':
    main(start=True)
