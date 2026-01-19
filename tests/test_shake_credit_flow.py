import contextlib
import types

import pytest

from src.database import shake_credits_operations as sco


class FakeCursor:
    def __init__(self, avail_before=2, has_row=True):
        self.executed = []
        self._avail = avail_before
        self._has_row = has_row
        self._last = None

    def execute(self, sql, params=None):
        self._last = sql.strip().lower()
        self.executed.append((sql, params))

    def fetchone(self):
        # Emulate responses based on last executed SQL fragment
        if 'for update' in (self._last or '') and 'shake_credits' in (self._last or ''):
            return {'credit_id': 1, 'total_credits': 5, 'used_credits': 0, 'available_credits': self._avail} if self._has_row else None
        if 'coalesce(sum(credit_change)' in (self._last or ''):
            return {'avail': self._avail}
        if self._last and self._last.startswith('update shake_credits'):
            # after deduction
            return {'used_credits': 1, 'available_credits': max(self._avail - 1, 0)}
        return None


@contextlib.contextmanager
def fake_get_db_cursor_factory(avail_before=2, has_row=True):
    cur = FakeCursor(avail_before=avail_before, has_row=has_row)
    yield cur


def test_consume_credit_success(monkeypatch):
    # Arrange: monkeypatch get_db_cursor to return a fake cursor with 2 available credits
    monkeypatch.setattr(sco, 'get_db_cursor', lambda commit=True: fake_get_db_cursor_factory(avail_before=2, has_row=True))

    # Act
    ok = sco.consume_credit(user_id=11111, reason='test consume')

    # Assert
    assert ok is True


def test_consume_credit_no_balance(monkeypatch):
    # Arrange: simulate ledger avail = 0
    monkeypatch.setattr(sco, 'get_db_cursor', lambda commit=True: fake_get_db_cursor_factory(avail_before=0, has_row=True))

    # Act
    ok = sco.consume_credit(user_id=22222, reason='test no balance')

    # Assert
    assert ok is False
