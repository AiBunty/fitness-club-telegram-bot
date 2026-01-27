import asyncio, logging
from types import SimpleNamespace

# Configure logging to print INFO level
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')

from src.utils import access_gate
import src.database.user_operations as uops
import src.utils.auth as auth

# Fake Telegram-like objects
class FakeUser:
    def __init__(self, uid):
        self.id = uid
        self.first_name = "Test"
        self.last_name = "User"
        self.username = "testuser"

class FakeMessage:
    def __init__(self):
        self.chat_id = 123
    async def reply_text(self, text, **kwargs):
        print(f"BOT_MSG: {text}")

class FakeCallbackMessage(FakeMessage):
    async def reply_text(self, text, **kwargs):
        print(f"BOT_CB_MSG: {text}")

class FakeCallbackQuery:
    def __init__(self, user_id, data="cmd_admin_dashboard"):
        self.from_user = FakeUser(user_id)
        self.data = data
        self.message = FakeCallbackMessage()
    async def answer(self, text=None, show_alert=False):
        print(f"CB_ANSWER: text={text} alert={show_alert}")
    async def edit_message_text(self, text, **kwargs):
        print(f"CB_EDIT: {text}")

class FakeUpdate:
    def __init__(self, user_id, is_callback=False, callback_data=None):
        self.effective_user = FakeUser(user_id)
        self.effective_message = FakeMessage()
        self.callback_query = FakeCallbackQuery(user_id, callback_data) if is_callback else None
        self.message = self.effective_message if not is_callback else None

class FakeContext:
    def __init__(self):
        self.user_data = {}
        self.bot = SimpleNamespace()

async def simulate_new_user_block():
    print("\n=== Scenario 1: NEW_USER blocked (local mode) ===")
    # Monkeypatch: no user exists
    uops.user_exists = lambda uid: False
    # Admin check: treat as non-admin
    auth.is_admin_id = lambda uid: False
    # Create fake updates for /store, /menu, and weight logging gate calls
    upd_store = FakeUpdate(user_id=1111, is_callback=False)
    upd_menu = FakeUpdate(user_id=1111, is_callback=False)
    upd_weight = FakeUpdate(user_id=1111, is_callback=False)
    ctx = FakeContext()

    # Call gate directly to mimic each feature entry
    allowed_store = await access_gate.check_access_gate(upd_store, ctx, require_subscription=True)
    print(f"/store allowed? {allowed_store}")
    allowed_menu = await access_gate.check_access_gate(upd_menu, ctx, require_subscription=True)
    print(f"/menu allowed? {allowed_menu}")
    allowed_weight = await access_gate.check_access_gate(upd_weight, ctx, require_subscription=True)
    print(f"/weight allowed? {allowed_weight}")

async def simulate_registered_local_grant():
    print("\n=== Scenario 2: REGISTERED user allowed in LOCAL_DB_MODE ===")
    # Monkeypatch: user exists and get_user returns profile
    uops.user_exists = lambda uid: True
    uops.get_user = lambda uid: { 'user_id': uid, 'full_name': 'Local Test', 'phone': '9999999999' }
    auth.is_admin_id = lambda uid: False

    upd = FakeUpdate(user_id=2222, is_callback=False)
    ctx = FakeContext()

    # Call access gate
    allowed = await access_gate.check_access_gate(upd, ctx, require_subscription=True)
    print(f"Feature allowed? {allowed}")

async def simulate_non_admin_admin_button():
    print("\n=== Scenario 3: Non-admin blocked for admin callback ===")
    # Non-admin
    auth.is_admin_id = lambda uid: False
    from src.handlers.callback_handlers import verify_admin_access
    upd_cb = FakeUpdate(user_id=3333, is_callback=True, callback_data="cmd_admin_dashboard")
    ctx = FakeContext()
    ok = await verify_admin_access(upd_cb, ctx)
    print(f"Admin callback allowed? {ok}")

async def main():
    await simulate_new_user_block()
    await simulate_registered_local_grant()
    await simulate_non_admin_admin_button()

if __name__ == "__main__":
    asyncio.run(main())
