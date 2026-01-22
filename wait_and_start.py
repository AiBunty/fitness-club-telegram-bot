"""
Wait for Telegram conflict to clear and start bot
"""
import os
import sys
import time
import asyncio
from telegram import Bot
from telegram.error import Conflict

# Load environment
from dotenv import load_dotenv
load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')

async def check_bot_availability():
    """Check if bot can connect without conflict"""
    bot = Bot(token=BOT_TOKEN)
    try:
        # Try to get updates
        await bot.get_updates(timeout=1)
        return True
    except Conflict:
        return False
    except Exception as e:
        print(f"Other error: {e}")
        return False
    finally:
        # Clean up
        try:
            await bot.delete_webhook(drop_pending_updates=True)
        except:
            pass

async def wait_for_clearance():
    """Wait until bot is available"""
    print("🔍 Checking if bot is available...")
    
    max_attempts = 20  # 20 attempts = ~3 minutes
    attempt = 0
    
    while attempt < max_attempts:
        attempt += 1
        print(f"\n⏳ Attempt {attempt}/{max_attempts}...")
        
        available = await check_bot_availability()
        
        if available:
            print("\n✅ Bot is available! No conflict detected.")
            print("🚀 Starting bot now...\n")
            return True
        else:
            print(f"❌ Still conflicting. Waiting 10 seconds...")
            await asyncio.sleep(10)
    
    print("\n⚠️  Timeout: Bot still conflicting after 3+ minutes")
    print("💡 Possible causes:")
    print("   - Another bot instance running on a server/VPS")
    print("   - Bot deployed on a cloud platform")
    print("   - Long-running getUpdates from another source")
    return False

async def main():
    """Main entry point"""
    is_available = await wait_for_clearance()
    
    if is_available:
        # Start the actual bot
        print("="*50)
        os.system('python start_bot.py')
    else:
        print("\n🛑 Cannot start bot due to persistent conflict")
        sys.exit(1)

if __name__ == '__main__':
    asyncio.run(main())
