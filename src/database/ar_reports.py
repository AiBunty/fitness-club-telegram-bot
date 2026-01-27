"""
Accounts Receivable reporting utilities (read-only, no side effects).
All functions return plain data structures suitable for inline summaries or exports.
"""
import datetime
from typing import List, Dict, Any

from src.database.connection import execute_query


def _date(dt: datetime.date | datetime.datetime) -> datetime.date:
    return dt.date() if isinstance(dt, datetime.datetime) else dt


def generate_daily_collections(target_date: datetime.date | datetime.datetime) -> List[Dict[str, Any]]:
    day = _date(target_date)
    sql = """
        SELECT t.transaction_id, t.receivable_id, t.method, t.amount, t.reference, t.created_by,
               t.created_at::date AS tx_date,
               ar.receivable_type, ar.source_id, ar.final_amount,
               u.full_name, u.user_id
        FROM ar_transactions t
        JOIN accounts_receivable ar ON ar.receivable_id = t.receivable_id
        JOIN users u ON u.user_id = ar.user_id
        WHERE t.created_at::date = %s
        ORDER BY t.created_at DESC
    """
    return execute_query(sql, (day,), fetch_one=False) or []


def generate_weekly_summary(end_date: datetime.date | datetime.datetime, days: int = 7) -> List[Dict[str, Any]]:
    end_day = _date(end_date)
    start_day = end_day - datetime.timedelta(days=days - 1)
    sql = """
        SELECT t.created_at::date AS tx_date, t.method, COALESCE(SUM(t.amount),0) AS total, COUNT(*) AS count
        FROM ar_transactions t
        WHERE t.created_at::date BETWEEN %s AND %s
        GROUP BY t.created_at::date, t.method
        ORDER BY t.created_at::date DESC, t.method
    """
    return execute_query(sql, (start_day, end_day), fetch_one=False) or []


def generate_payment_method_breakdown(start_date: datetime.date | datetime.datetime,
                                      end_date: datetime.date | datetime.datetime) -> List[Dict[str, Any]]:
    start_day = _date(start_date)
    end_day = _date(end_date)
    sql = """
        SELECT t.method, COALESCE(SUM(t.amount),0) AS total, COUNT(*) AS count
        FROM ar_transactions t
        WHERE t.created_at::date BETWEEN %s AND %s
        GROUP BY t.method
        ORDER BY total DESC
    """
    return execute_query(sql, (start_day, end_day), fetch_one=False) or []


def generate_outstanding(as_of: datetime.date | datetime.datetime) -> List[Dict[str, Any]]:
    day = _date(as_of)
    sql = """
        SELECT ar.receivable_id, ar.user_id, u.full_name, ar.receivable_type, ar.source_id,
               ar.final_amount,
               COALESCE(SUM(t.amount),0) AS received,
               (ar.final_amount - COALESCE(SUM(t.amount),0)) AS balance,
               ar.due_date,
               ar.status
        FROM accounts_receivable ar
        LEFT JOIN ar_transactions t ON t.receivable_id = ar.receivable_id
        JOIN users u ON u.user_id = ar.user_id
        WHERE ar.status IN ('pending','partial') OR (ar.due_date IS NOT NULL AND ar.due_date < %s AND ar.status <> 'paid')
        GROUP BY ar.receivable_id, ar.user_id, u.full_name, ar.receivable_type, ar.source_id, ar.final_amount, ar.due_date, ar.status
        ORDER BY balance DESC
    """
    return execute_query(sql, (day,), fetch_one=False) or []


def generate_aging(as_of: datetime.date | datetime.datetime) -> List[Dict[str, Any]]:
    day = _date(as_of)
    sql = """
        SELECT ar.receivable_id, ar.user_id, u.full_name, ar.receivable_type, ar.source_id,
               ar.final_amount,
               COALESCE(SUM(t.amount),0) AS received,
               (ar.final_amount - COALESCE(SUM(t.amount),0)) AS balance,
               ar.due_date,
               CASE
                   WHEN ar.due_date IS NULL THEN 'no_due'
                   WHEN ar.due_date >= %s THEN 'current'
                   WHEN ar.due_date < %s AND ar.due_date >= %s THEN 'd30'
                   WHEN ar.due_date < %s AND ar.due_date >= %s THEN 'd60'
                   WHEN ar.due_date < %s AND ar.due_date >= %s THEN 'd90'
                   ELSE 'd90_plus'
               END AS bucket
        FROM accounts_receivable ar
        LEFT JOIN ar_transactions t ON t.receivable_id = ar.receivable_id
        JOIN users u ON u.user_id = ar.user_id
        WHERE ar.status <> 'paid'
        GROUP BY ar.receivable_id, ar.user_id, u.full_name, ar.receivable_type, ar.source_id, ar.final_amount, ar.due_date
    """
    d30 = day - datetime.timedelta(days=30)
    d60 = day - datetime.timedelta(days=60)
    d90 = day - datetime.timedelta(days=90)
    d120 = day - datetime.timedelta(days=120)
    return execute_query(sql, (day, day, d30, d30, d60, d60, d90), fetch_one=False) or []


def generate_monthly_collections(year: int, month: int) -> List[Dict[str, Any]]:
    start_day = datetime.date(year, month, 1)
    if month == 12:
        end_day = datetime.date(year + 1, 1, 1) - datetime.timedelta(days=1)
    else:
        end_day = datetime.date(year, month + 1, 1) - datetime.timedelta(days=1)
    sql = """
        SELECT t.created_at::date AS tx_date, t.method, COALESCE(SUM(t.amount),0) AS total, COUNT(*) AS count
        FROM ar_transactions t
        WHERE t.created_at::date BETWEEN %s AND %s
        GROUP BY t.created_at::date, t.method
        ORDER BY t.created_at::date DESC, t.method
    """
    return execute_query(sql, (start_day, end_day), fetch_one=False) or []
