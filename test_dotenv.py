#!/usr/bin/env python3
import os
from dotenv import load_dotenv

print(f"Current working directory: {os.getcwd()}")
print(f".env file exists: {os.path.exists('.env')}")
print(f".env absolute path: {os.path.abspath('.env')}")

# Try loading explicitly
result = load_dotenv('.env')
print(f"load_dotenv result: {result}")

print(f"\nDB_HOST from os.getenv: {os.getenv('DB_HOST')}")
print(f"DB_USER from os.getenv: {os.getenv('DB_USER')}")
print(f"DB_NAME from os.getenv: {os.getenv('DB_NAME')}")
