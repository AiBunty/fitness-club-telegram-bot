import logging
from typing import List, Dict, Any, Optional, Tuple
from src.config import USE_LOCAL_DB, USE_REMOTE_DB
from src.database.connection import execute_query, get_db_cursor

logger = logging.getLogger(__name__)


def create_receivable(user_id: int, receivable_type: str, source_id: Optional[int], bill_amount: float,
                      discount_amount: float = 0.0, final_amount: Optional[float] = None,
                      due_date: Optional[str] = None) -> Dict[str, Any]:
    """Create an accounts_receivable record and return it."""
    if final_amount is None:
        final_amount = float(bill_amount) - float(discount_amount or 0)
    sql = (
        "INSERT INTO accounts_receivable (user_id, receivable_type, source_id, bill_amount, discount_amount, final_amount, status, due_date) "
        "VALUES (%s, %s, %s, %s, %s, %s, 'pending', %s) RETURNING *"
    )
    row = execute_query(sql, (user_id, receivable_type, source_id, bill_amount, discount_amount, final_amount, due_date), fetch_one=True)
    return row or {}


def create_transactions(receivable_id: int, lines: List[Dict[str, Any]], admin_user_id: Optional[int]) -> int:
    """Insert multiple transaction lines atomically. Returns count inserted."""
    placeholder = '?' if USE_LOCAL_DB and not USE_REMOTE_DB else '%s'
    sql = (
        f"INSERT INTO ar_transactions (receivable_id, method, amount, reference, created_by) "
        f"VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})"
    )
    with get_db_cursor() as cursor:
        for line in lines:
            method = str(line.get('method')).lower()
            amount = float(line.get('amount'))
            reference = line.get('reference')
            cursor.execute(sql, (receivable_id, method, amount, reference, admin_user_id))
        return len(lines)


def sum_received(receivable_id: int) -> float:
    row = execute_query("SELECT COALESCE(SUM(amount),0) AS total FROM ar_transactions WHERE receivable_id=%s", (receivable_id,), fetch_one=True)
    return float(row.get('total', 0)) if row else 0.0


def sum_by_method(receivable_id: int) -> Dict[str, float]:
    rows = execute_query("SELECT method, COALESCE(SUM(amount),0) AS total FROM ar_transactions WHERE receivable_id=%s GROUP BY method", (receivable_id,))
    return {r['method']: float(r['total']) for r in rows or []}


def update_receivable_status(receivable_id: int) -> Dict[str, Any]:
    """Recompute status based on totals and update."""
    rec = execute_query("SELECT final_amount, status FROM accounts_receivable WHERE receivable_id=%s", (receivable_id,), fetch_one=True)
    if not rec:
        return {}
    final_amount = float(rec['final_amount'])
    received = sum_received(receivable_id)
    if received <= 0:
        new_status = 'pending'
    elif received < final_amount:
        new_status = 'partial'
    else:
        new_status = 'paid'
    row = execute_query("UPDATE accounts_receivable SET status=%s, updated_at=CURRENT_TIMESTAMP WHERE receivable_id=%s RETURNING *",
                        (new_status, receivable_id), fetch_one=True)
    return row or {}


def get_overdue_receivables() -> List[Dict[str, Any]]:
    sql = """
        SELECT ar.*, u.full_name, u.user_id AS uid
        FROM accounts_receivable ar
        JOIN users u ON u.user_id = ar.user_id
        WHERE ar.status <> 'paid' AND ar.due_date IS NOT NULL AND ar.due_date < CURRENT_DATE
        ORDER BY ar.due_date ASC
    """
    return execute_query(sql)


def get_receivable_breakdown(receivable_id: int) -> Dict[str, Any]:
    rec = execute_query("SELECT * FROM accounts_receivable WHERE receivable_id=%s", (receivable_id,), fetch_one=True)
    if not rec:
        return {}
    totals = sum_by_method(receivable_id)
    received = sum_received(receivable_id)
    balance = float(rec['final_amount']) - received
    return {
        'receivable': rec,
        'received_total': received,
        'balance': balance,
        'methods': totals,
    }


def get_receivable_by_source(receivable_type: str, source_id: int) -> Dict[str, Any]:
    """Lookup a receivable using the originating entity (e.g., subscription request)."""
    sql = """
        SELECT *
        FROM accounts_receivable
        WHERE receivable_type = %s AND source_id = %s
        ORDER BY created_at DESC
        LIMIT 1
    """
    return execute_query(sql, (receivable_type, source_id), fetch_one=True) or {}
