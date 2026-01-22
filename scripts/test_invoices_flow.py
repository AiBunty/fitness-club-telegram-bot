import asyncio
import importlib
import sys
import logging
from pathlib import Path

# Suppress most logging from the app (avoid bot logs interfering with test output)
logging.getLogger().setLevel(logging.CRITICAL)

# Capture prints to a dedicated log file to avoid console/log noise
ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'test_run_capture.log'
_logf = open(OUT, 'w', encoding='utf-8')
def print(*args, **kwargs):
    try:
        _logf.write(' '.join(str(a) for a in args) + '\n')
        _logf.flush()
    except Exception:
        pass

sys.path.insert(0, r'c:/Users/ventu/Fitness/fitness-club-telegram-bot')

from types import SimpleNamespace
from src.invoices import handlers
from src.invoices import store as invoice_store

# Monkeypatch auth to treat test admin as admin
import src.utils.auth as auth
auth.is_admin_id = lambda x: True
auth.list_admin_ids = lambda: [999999]

# Monkeypatch invoice user search to return a fake user
import src.invoices.utils as inv_utils
inv_utils.search_users = lambda term: [{'user_id': 424242, 'username': 'tester', 'full_name': 'Automated Tester'}]

class FakeUser:
    def __init__(self, uid):
        self.id = uid

class FakeMessage:
    def __init__(self, text, user_id=999999):
        self.text = text
        self.from_user = SimpleNamespace(id=user_id)
        self.chat_id = user_id
    async def reply_text(self, *args, **kwargs):
        print('[BOT_REPLY]', args[0] if args else '', kwargs.get('reply_markup'))
    async def reply_document(self, *args, **kwargs):
        print('[BOT_REPLY_DOC]')

class FakeCallbackQuery:
    def __init__(self, data, user_id=999999):
        self.data = data
        self.from_user = FakeUser(user_id)
        self.message = SimpleNamespace(chat_id=user_id)
    async def answer(self):
        print('[CQ] answer()')
    async def edit_message_text(self, text, reply_markup=None):
        print('[CQ] edit_message_text:', text)

class FakeBot:
    async def send_document(self, chat_id, document, caption=None):
        print(f'[BOT] send_document to {chat_id} caption={caption}')

async def run_flow():
    context = SimpleNamespace()
    context.user_data = {}
    context.bot = FakeBot()

    # 1. entry point
    cq = FakeCallbackQuery('cmd_invoices', user_id=999999)
    await handlers.invoice_entry(SimpleNamespace(callback_query=cq), context)

    # 2. start create
    cq2 = FakeCallbackQuery('inv_create', user_id=999999)
    await handlers.inv_create_start(SimpleNamespace(callback_query=cq2), context)

    # 3. search user (message)
    msg = FakeMessage('Tester')
    update_msg = SimpleNamespace(message=msg)
    await handlers.handle_user_search(update_msg, context)

    # 4. select user
    cq3 = FakeCallbackQuery('inv_user_424242', user_id=999999)
    await handlers.handle_user_select(SimpleNamespace(callback_query=cq3), context)

    # 5. add item
    msg_name = FakeMessage('Protein Powder')
    await handlers.item_name(SimpleNamespace(message=msg_name), context)
    msg_rate = FakeMessage('1200')
    await handlers.item_rate(SimpleNamespace(message=msg_rate), context)
    msg_qty = FakeMessage('2')
    await handlers.item_qty(SimpleNamespace(message=msg_qty), context)
    msg_disc = FakeMessage('10')
    await handlers.item_disc(SimpleNamespace(message=msg_disc), context)

    # 6. finish items
    cq_fin = FakeCallbackQuery('inv_finish_items', user_id=999999)
    await handlers.item_after_choice(SimpleNamespace(callback_query=cq_fin), context)

    # 7. shipping
    msg_ship = FakeMessage('50')
    await handlers.handle_shipping(SimpleNamespace(message=msg_ship), context)

    # 8. send invoice
    cq_send = FakeCallbackQuery('inv_send', user_id=999999)
    await handlers.handle_send_invoice(SimpleNamespace(callback_query=cq_send), context)

    # Verify saved invoice
    invoices = invoice_store.load_invoices()
    print('Saved invoices count =', len(invoices))
    for k,v in invoices.items():
        print('Invoice:', k, v)

    # 9. Test admin resend
    inv_id = list(invoices.keys())[0]
    cq_resend = FakeCallbackQuery(f'inv_admin_resend_{inv_id}', user_id=999999)
    await handlers.admin_resend_invoice(SimpleNamespace(callback_query=cq_resend), context)

    # 10. Test payment approved hook
    cq_paid = FakeCallbackQuery(f'inv_paid_{inv_id}', user_id=999999)
    await handlers.invoice_payment_approved_hook(SimpleNamespace(callback_query=cq_paid), context)

    # 11. Test admin delete
    cq_del = FakeCallbackQuery(f'inv_admin_delete_{inv_id}', user_id=999999)
    await handlers.admin_delete_invoice(SimpleNamespace(callback_query=cq_del), context)

    invoices2 = invoice_store.load_invoices()
    print('After delete count =', len(invoices2))

if __name__ == '__main__':
    asyncio.run(run_flow())
