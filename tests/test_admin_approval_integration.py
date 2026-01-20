import unittest
from types import SimpleNamespace
from unittest.mock import patch, AsyncMock


class FakeQuery:
    def __init__(self, user_id=1, message=None, data=None):
        self.from_user = SimpleNamespace(id=user_id, full_name="Admin")
        self.message = message or SimpleNamespace()
        self.data = data
        self.answered = False
        self.edited_text = None

    async def answer(self, *args, **kwargs):
        self.answered = True

    async def edit_message_text(self, text, *args, **kwargs):
        self.edited_text = text


class FakeMessage:
    def __init__(self, text=None, photo=None):
        self.text = text
        self.photo = photo
        self.replies = []

    async def reply_text(self, text, *args, **kwargs):
        self.replies.append(text)


class FakeBot:
    async def send_message(self, *args, **kwargs):
        return True

    async def send_photo(self, *args, **kwargs):
        return True


class AdminApprovalIntegrationTest(unittest.IsolatedAsyncioTestCase):
    async def test_split_admin_flow_finishes_and_finalizes(self):
        # Setup fake request id and user
        request_id = 9999

        # Prepare fake callback to start split approval
        start_query = FakeQuery(user_id=424, message=FakeMessage(text="start"), data=f"admin_approve_split_upi_{request_id}")
        start_update = SimpleNamespace(callback_query=start_query)

        # Context with mutable user_data and fake bot
        context = SimpleNamespace(user_data={}, bot=FakeBot(), application=None)

        # Patch required DB and helper functions
        with patch('src.handlers.subscription_handlers.is_admin', return_value=True), \
             patch('src.database.subscription_operations.get_subscription_request_details', return_value={'user_id': 123, 'user_name': 'Alice', 'plan_id': 'basic', 'amount': 1500}), \
             patch('src.database.subscription_operations.approve_subscription', return_value=True) as mock_approve, \
             patch('src.database.subscription_operations.get_pending_payment') as mock_get_pending, \
             patch('src.database.subscription_operations.finalize_pending_payment') as mock_finalize, \
             patch('src.database.user_operations.get_user', return_value={'user_id': 123}):

            # Trigger admin start (ask for bill)
            from src.handlers.subscription_handlers import callback_admin_approve_split_upi, handle_admin_enter_bill, handle_admin_enter_upi_received, handle_admin_enter_cash_received, callback_approve_with_date, callback_admin_final_confirm

            await callback_admin_approve_split_upi(start_update, context)

            # Admin enters final bill amount
            bill_msg = SimpleNamespace(text="1000", reply_text=AsyncMock())
            bill_update = SimpleNamespace(message=bill_msg)
            await handle_admin_enter_bill(bill_update, context)

            # Admin enters UPI received
            upi_msg = SimpleNamespace(text="600", reply_text=AsyncMock())
            upi_update = SimpleNamespace(message=upi_msg)
            await handle_admin_enter_upi_received(upi_update, context)

            # Admin enters cash received
            cash_msg = SimpleNamespace(text="400", reply_text=AsyncMock())
            cash_update = SimpleNamespace(message=cash_msg)

            # The handler will import calendar generator from src.utils.calendar_picker; inject a fake module
            import sys, types
            fake_mod = types.ModuleType('src.utils.calendar_picker')
            fake_mod.generate_calendar = lambda: None
            sys.modules['src.utils.calendar_picker'] = fake_mod

            await handle_admin_enter_cash_received(cash_update, context)

            # Simulate selecting date via callback (callback data contains date)
            date_query = FakeQuery(user_id=424, message=FakeMessage(text="date"), data="approve_date_20260120")
            date_update = SimpleNamespace(callback_query=date_query)
            await callback_approve_with_date(date_update, context)

            # Prepare final_confirm callback
            final_query = FakeQuery(user_id=424, message=SimpleNamespace(), data=f"admin_final_confirm_{request_id}")
            final_update = SimpleNamespace(callback_query=final_query)

            # get_pending_payment should be called first for upi then for cash
            mock_get_pending.side_effect = [ {'id': 301, 'reference': 'UPIREF'}, {'id': 302, 'reference': 'CASHREF'} ]

            # Ensure ar_operations.record_payment exists to avoid ImportError during import
            import importlib
            ar_mod = importlib.import_module('src.database.ar_operations')
            setattr(ar_mod, 'record_payment', lambda *a, **k: None)

            await callback_admin_final_confirm(final_update, context)

            # Assertions
            mock_approve.assert_called_once_with(request_id, 1000.0, context.user_data.get('selected_end_date'))
            self.assertEqual(mock_finalize.call_count, 2)
            mock_finalize.assert_any_call(301, reference='UPIREF')
            mock_finalize.assert_any_call(302, reference='CASHREF')


if __name__ == '__main__':
    unittest.main()
