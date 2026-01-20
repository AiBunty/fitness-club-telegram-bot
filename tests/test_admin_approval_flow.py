import unittest
from types import SimpleNamespace
from unittest.mock import patch, AsyncMock


class FakeQuery:
    def __init__(self, user_id=1):
        self.from_user = SimpleNamespace(id=user_id, full_name="Admin")
        self.message = SimpleNamespace()
        self.answered = False
        self.edited_text = None

    async def answer(self, *args, **kwargs):
        self.answered = True

    async def edit_message_text(self, *args, **kwargs):
        self.edited_text = args[0] if args else kwargs.get('text')


class FakeBot:
    async def send_message(self, *args, **kwargs):
        return True

    async def send_photo(self, *args, **kwargs):
        return True


class TestAdminApprovalFlow(unittest.IsolatedAsyncioTestCase):
    async def test_callback_admin_final_confirm_finalizes_pending(self):
        # Prepare fake update and context
        fake_query = FakeQuery(user_id=42)
        fake_update = SimpleNamespace(callback_query=fake_query)

        user_data = {
            'approving_request_id': 1001,
            'approving_request_details': {'user_id': 555, 'user_name': 'Test User', 'plan_id': 'basic'},
            'final_bill_amount': 1000,
            'upi_received': 600,
            'cash_received': 400,
            'selected_end_date': None,
        }

        fake_context = SimpleNamespace(user_data=user_data, bot=FakeBot(), application=None)

        # Patch helpers: is_admin, approve_subscription, get_pending_payment, finalize_pending_payment
        with patch('src.handlers.subscription_handlers.is_admin', return_value=True), \
             patch('src.database.subscription_operations.approve_subscription', return_value=True) as mock_approve, \
             patch('src.database.subscription_operations.get_pending_payment') as mock_get_pending, \
             patch('src.database.subscription_operations.finalize_pending_payment') as mock_finalize, \
             patch('src.database.user_operations.get_user', return_value={'user_id': 555}):

            # get_pending_payment should return two records for upi and cash sequentially
            mock_get_pending.side_effect = [ {'id': 201, 'reference': 'UPIREF'}, {'id': 202, 'reference': 'CASHREF'} ]

            from src.handlers.subscription_handlers import callback_admin_final_confirm

            await callback_admin_final_confirm(fake_update, fake_context)

            # finalize_pending_payment should be called for both pending ids
            self.assertEqual(mock_finalize.call_count, 2)
            mock_finalize.assert_any_call(201, reference='UPIREF', screenshot_file_id=None)
            mock_finalize.assert_any_call(202, reference='CASHREF', screenshot_file_id=None)


if __name__ == '__main__':
    unittest.main()
