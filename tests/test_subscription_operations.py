import unittest
from types import SimpleNamespace

from src.database import subscription_operations as sub_ops


class TestSubscriptionOperations(unittest.TestCase):

    def test_create_split_payment_receivable_success(self):
        # Patch dependent functions
        orig_create = sub_ops.create_receivable
        orig_create_tx = sub_ops.create_transactions
        orig_update = sub_ops.update_receivable_status

        try:
            sub_ops.create_receivable = lambda **kwargs: {'receivable_id': 999}
            sub_ops.create_transactions = lambda receivable_id, lines, admin_user_id=None: True
            sub_ops.update_receivable_status = lambda rid: {'status': 'partial'}

            res = sub_ops.create_split_payment_receivable(1111, 2222, 1000.0, 1500.0)
            self.assertIsNotNone(res)
            self.assertEqual(res.get('receivable_id'), 999)
            self.assertAlmostEqual(res.get('upi_amount'), 1000.0)
            self.assertAlmostEqual(res.get('cash_amount'), 1500.0)
        finally:
            sub_ops.create_receivable = orig_create
            sub_ops.create_transactions = orig_create_tx
            sub_ops.update_receivable_status = orig_update

    def test_record_split_upi_payment_updates(self):
        # Patch get_receivable_by_source and execute_query and update_receivable_status
        orig_get = sub_ops.get_receivable_by_source
        orig_exec = sub_ops.execute_query
        orig_update = sub_ops.update_receivable_status

        try:
            sub_ops.get_receivable_by_source = lambda typ, src: {'receivable_id': 500}
            # Capture update SQL calls
            calls = []
            def fake_execute(sql, params=None, fetch_one=False):
                calls.append((sql, params))
                return None

            sub_ops.execute_query = fake_execute
            sub_ops.update_receivable_status = lambda rid: True

            ok = sub_ops.record_split_upi_payment(1111, 2222, 1000.0, 'REF123')
            self.assertTrue(ok)
            # Ensure update query for ar_transactions was executed
            self.assertTrue(any('UPDATE ar_transactions' in c[0] for c in calls))
        finally:
            sub_ops.get_receivable_by_source = orig_get
            sub_ops.execute_query = orig_exec
            sub_ops.update_receivable_status = orig_update

    def test_record_split_cash_payment_updates(self):
        orig_get = sub_ops.get_receivable_by_source
        orig_exec = sub_ops.execute_query
        orig_update = sub_ops.update_receivable_status

        try:
            sub_ops.get_receivable_by_source = lambda typ, src: {'receivable_id': 600}
            calls = []
            def fake_execute(sql, params=None, fetch_one=False):
                calls.append((sql, params))
                return None

            sub_ops.execute_query = fake_execute
            sub_ops.update_receivable_status = lambda rid: {'status': 'paid'}

            ok = sub_ops.record_split_cash_payment(1111, 2222)
            self.assertTrue(ok)
            self.assertTrue(any('UPDATE ar_transactions' in c[0] for c in calls))
        finally:
            sub_ops.get_receivable_by_source = orig_get
            sub_ops.execute_query = orig_exec
            sub_ops.update_receivable_status = orig_update


if __name__ == '__main__':
    unittest.main()
