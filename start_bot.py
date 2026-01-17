#!/usr/bin/env python3
"""
Startup script that sets up Python path properly and runs the bot
"""

import sys
import os

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Now import and run the bot
from src.bot import main

if __name__ == '__main__':
    main()
