"""
Invoice Report Generation Module
Provides database operations for generating invoice reports by date range
"""

from datetime import datetime, timedelta
from src.database.connection import execute_query


def get_invoices_by_date_range(start_date, end_date):
    """
    Fetch all invoices within a date range with full details
    
    Args:
        start_date: datetime object for start of range
        end_date: datetime object for end of range
        
    Returns:
        List of invoice dicts with customer details and totals
    """
    query = """
    SELECT 
        i.invoice_id,
        i.user_id,
        u.full_name,
        u.phone,
        COUNT(DISTINCT ii.item_id) as items_count,
        i.items_subtotal,
        i.gst_total,
        i.shipping,
        i.final_total,
        i.status,
        DATE(i.created_at) as created_date,
        DATE(i.paid_at) as paid_date
    FROM invoices i
    LEFT JOIN users u ON i.user_id = u.user_id
    LEFT JOIN invoice_items ii ON i.invoice_id = ii.invoice_id
    WHERE DATE(i.created_at) BETWEEN %s AND %s
    GROUP BY i.invoice_id
    ORDER BY i.created_at DESC
    """
    
    invoices = execute_query(
        query,
        (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')),
        fetch_one=False
    )
    
    return invoices or []


def get_invoice_summary(start_date, end_date):
    """
    Get summary statistics for invoices in date range
    
    Args:
        start_date: datetime object for start of range
        end_date: datetime object for end of range
        
    Returns:
        Dict with summary statistics
    """
    query = """
    SELECT 
        COUNT(DISTINCT i.invoice_id) as total_invoices,
        SUM(i.final_total) as total_amount,
        SUM(CASE WHEN i.status = 'paid' THEN i.final_total ELSE 0 END) as paid_amount,
        SUM(CASE WHEN i.status != 'paid' THEN i.final_total ELSE 0 END) as pending_amount,
        COUNT(DISTINCT i.user_id) as unique_customers,
        AVG(i.final_total) as avg_invoice_amount
    FROM invoices i
    WHERE DATE(i.created_at) BETWEEN %s AND %s
    """
    
    result = execute_query(
        query,
        (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')),
        fetch_one=True
    )
    
    if result:
        return {
            'total_invoices': result.get('total_invoices') or 0,
            'total_amount': float(result.get('total_amount') or 0),
            'paid_amount': float(result.get('paid_amount') or 0),
            'pending_amount': float(result.get('pending_amount') or 0),
            'unique_customers': result.get('unique_customers') or 0,
            'avg_invoice_amount': float(result.get('avg_invoice_amount') or 0)
        }
    
    return {
        'total_invoices': 0,
        'total_amount': 0.0,
        'paid_amount': 0.0,
        'pending_amount': 0.0,
        'unique_customers': 0,
        'avg_invoice_amount': 0.0
    }


def get_monthly_invoices(year, month):
    """Get invoices for a specific month"""
    start = datetime(year, month, 1)
    if month == 12:
        end = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        end = datetime(year, month + 1, 1) - timedelta(days=1)
    
    return get_invoices_by_date_range(start, end)


def get_monthly_summary(year, month):
    """Get summary for a specific month"""
    start = datetime(year, month, 1)
    if month == 12:
        end = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        end = datetime(year, month + 1, 1) - timedelta(days=1)
    
    return get_invoice_summary(start, end)


def get_quarterly_invoices(year, quarter):
    """Get invoices for a specific quarter (1-4)"""
    start_month = (quarter - 1) * 3 + 1
    start = datetime(year, start_month, 1)
    
    if quarter == 4:
        end = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        end = datetime(year, start_month + 3, 1) - timedelta(days=1)
    
    return get_invoices_by_date_range(start, end)


def get_quarterly_summary(year, quarter):
    """Get summary for a specific quarter"""
    start_month = (quarter - 1) * 3 + 1
    start = datetime(year, start_month, 1)
    
    if quarter == 4:
        end = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        end = datetime(year, start_month + 3, 1) - timedelta(days=1)
    
    return get_invoice_summary(start, end)


def get_six_month_invoices(year, half):
    """Get invoices for first or second half of year (1 or 2)"""
    if half == 1:
        start = datetime(year, 1, 1)
        end = datetime(year, 6, 30)
    else:
        start = datetime(year, 7, 1)
        end = datetime(year, 12, 31)
    
    return get_invoices_by_date_range(start, end)


def get_six_month_summary(year, half):
    """Get summary for first or second half of year"""
    if half == 1:
        start = datetime(year, 1, 1)
        end = datetime(year, 6, 30)
    else:
        start = datetime(year, 7, 1)
        end = datetime(year, 12, 31)
    
    return get_invoice_summary(start, end)


def get_yearly_invoices(year):
    """Get invoices for entire year"""
    start = datetime(year, 1, 1)
    end = datetime(year, 12, 31)
    
    return get_invoices_by_date_range(start, end)


def get_yearly_summary(year):
    """Get summary for entire year"""
    start = datetime(year, 1, 1)
    end = datetime(year, 12, 31)
    
    return get_invoice_summary(start, end)


def get_custom_date_range_invoices(start_date, end_date):
    """
    Get invoices for custom date range with validation
    
    Args:
        start_date: datetime object
        end_date: datetime object
        
    Returns:
        Tuple (success, invoices, error_message)
    """
    # Auto-swap if reversed
    if start_date > end_date:
        start_date, end_date = end_date, start_date
    
    # Validate date range (max 730 days / 2 years)
    days_diff = (end_date - start_date).days
    if days_diff > 730:
        return False, [], "Date range cannot exceed 2 years (730 days)"
    
    invoices = get_invoices_by_date_range(start_date, end_date)
    return True, invoices, None


def get_custom_date_range_summary(start_date, end_date):
    """
    Get summary for custom date range with validation
    
    Args:
        start_date: datetime object
        end_date: datetime object
        
    Returns:
        Tuple (success, summary, error_message)
    """
    # Auto-swap if reversed
    if start_date > end_date:
        start_date, end_date = end_date, start_date
    
    # Validate date range (max 730 days / 2 years)
    days_diff = (end_date - start_date).days
    if days_diff > 730:
        return False, {}, "Date range cannot exceed 2 years (730 days)"
    
    summary = get_invoice_summary(start_date, end_date)
    return True, summary, None
