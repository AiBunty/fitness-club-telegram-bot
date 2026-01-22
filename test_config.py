#!/usr/bin/env python3
from src.config import DATABASE_CONFIG

print("DATABASE_CONFIG loaded:")
for key, value in DATABASE_CONFIG.items():
    if key == 'password':
        print(f"  {key}: ***REDACTED***")
    else:
        print(f"  {key}: {value}")
