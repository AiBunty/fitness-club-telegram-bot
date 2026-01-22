"""
Force clear any webhooks and conflicts, then start bot
"""
import os
import sys
import time
import asyncio
from telegram import Bot
from telegram.error import Conflict, TelegramError
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

async def force_clear_webhook():
    """Aggressively clear webhook and pending updates"""
    bot = Bot(token=BOT_TOKEN)
    
    print("🔧 Step 1: Deleting webhook and clearing pending updates...")
    try:
        result = await bot.delete_webhook(drop_pending_updates=True)
        print(f"   ✅ Webhook deleted: {result}")
    except Exception as e:
        print(f"   ⚠️  Error deleting webhook: {e}")
    
    # Try multiple times to ensure it's clear
    for i in range(3):
        await asyncio.sleep(2)
        try:
            await bot.delete_webhook(drop_pending_updates=True)
        except:
            pass
    
    print("\n⏳ Step 2: Waiting 45 seconds for any active getUpdates to timeout...")
    print("   (Telegram's long polling can take 30-40 seconds to expire)")
    
    for remaining in range(45, 0, -5):
        print(f"   ⏰ {remaining} seconds remaining...")
        await asyncio.sleep(5)
    
    print("\n🔍 Step 3: Testing if bot is now available...")
    
    # Try to get updates with very short timeout
    max_tests = 5
    for test_num in range(1, max_tests + 1):
        try:
            print(f"   Test {test_num}/{max_tests}...", end=" ")
            updates = await bot.get_updates(timeout=1, offset=-1)
            print("✅ SUCCESS!")
            return True
        except Conflict as e:
            print(f"❌ Still conflicting")
            if test_num < max_tests:
                print(f"   Waiting 10 more seconds...")
                await asyncio.sleep(10)
        except Exception as e:
            print(f"⚠️  Other error: {e}")
            return False
    
    print("\n❌ Still conflicting after all attempts")
    print("\n🔍 Diagnostic information:")
    print(f"   Bot Token (last 10 chars): ...{BOT_TOKEN[-10:]}")
    print("\n💡 Next steps:")
    print("   1. Go to https://t.me/BotFather")
    print("   2. Send /mybots")
    print("   3. Select your bot")
    print("   4. Click 'API Token' → 'Revoke current token'")
    print("   5. Copy the new token")
    print("   6. Update your .env file with the new token")
    print("   7. Try running this script again")
    
    return False

async def main():
    print("="*60)
    print("🤖 FORCE CLEAR TELEGRAM BOT CONFLICTS")
    print("="*60)
    
    is_clear = await force_clear_webhook()
    
    if is_clear:
        print("\n" + "="*60)
        print("✅ BOT IS READY! STARTING NOW...")
        print("="*60 + "\n")
        
        # Set environment and start bot
        os.environ['SKIP_FLASK'] = '1'
        os.environ['SKIP_SCHEDULING'] = '1'
        
        # Import and run the bot
        sys.path.insert(0, os.path.dirname(__file__))
        import start_bot
        
    else:
        print("\n" + "="*60)
        print("❌ UNABLE TO CLEAR CONFLICT")
        print("="*60)
        sys.exit(1)

if __name__ == '__main__':
    asyncio.run(main())
