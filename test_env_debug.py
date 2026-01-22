#!/usr/bin/env python3
import os
import sys

# Check if variables are set BEFORE importing anything
print("=== BEFORE importing config ===")
print(f"DB_HOST: {os.getenv('DB_HOST')}")
print(f"DB_NAME: {os.getenv('DB_NAME')}")

# Now import config which calls load_dotenv
from dotenv import load_dotenv
print("\n=== AFTER calling load_dotenv() ===")
result = load_dotenv(verbose=True)
print(f"Load result: {result}")
print(f"DB_HOST: {os.getenv('DB_HOST')}")
print(f"DB_NAME: {os.getenv('DB_NAME')}")

# Check if it's in os.environ
print("\n=== Checking os.environ directly ===")
print(f"DB_HOST in environ: {'DB_HOST' in os.environ}")
print(f"os.environ['DB_HOST']: {os.environ.get('DB_HOST', 'NOT SET')}")
