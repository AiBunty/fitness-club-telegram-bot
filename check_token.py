from dotenv import load_dotenv
import os

load_dotenv()
token = os.getenv('BOT_TOKEN')

if token:
    print(f"✅ Token found")
    print(f"   Length: {len(token)}")
    print(f"   Format OK: {':' in token}")
    print(f"   Last 10 chars: ...{token[-10:]}")
else:
    print("❌ BOT_TOKEN not found in environment")
    print("\nChecking .env file...")
    
    try:
        with open('.env', 'r') as f:
            lines = f.readlines()
            for line in lines:
                if line.startswith('BOT_TOKEN'):
                    print(f"Found in .env: {line.strip()[:30]}...")
    except:
        print("⚠️  Could not read .env file")
