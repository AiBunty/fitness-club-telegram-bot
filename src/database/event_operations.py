"""
Event store operations: create/list events, register users, handle paid/free flows
Integrates with AR (`src.database.ar_operations`) to create receivables for paid events.
"""
import logging
from datetime import date
from typing import Optional

from src.database.connection import execute_query
from src.database.ar_operations import create_receivable, update_receivable_status

logger = logging.getLogger(__name__)


def create_event(title: str, description: str, price: float, is_paid: bool,
                 start_date: Optional[date], end_date: Optional[date], capacity: Optional[int], admin_id: int) -> dict:
    try:
        query = """
            INSERT INTO events (title, description, price, is_paid, start_date, end_date, capacity, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """
        row = execute_query(query, (title, description, price, is_paid, start_date, end_date, capacity, admin_id), fetch_one=True)
        logger.info(f"Event created: {title} by admin {admin_id}")
        return row or {}
    except Exception as e:
        logger.error(f"Error creating event: {e}")
        return {}


def get_active_events() -> list:
    try:
        query = """
            SELECT * FROM events
            WHERE status = 'active'
            AND (start_date IS NULL OR start_date <= CURRENT_DATE)
            AND (end_date IS NULL OR end_date >= CURRENT_DATE)
            ORDER BY start_date NULLS LAST, created_at DESC
        """
        return execute_query(query)
    except Exception as e:
        logger.error(f"Error getting active events: {e}")
        return []


def get_event(event_id: int) -> dict:
    try:
        return execute_query("SELECT * FROM events WHERE event_id = %s", (event_id,), fetch_one=True) or {}
    except Exception as e:
        logger.error(f"Error getting event {event_id}: {e}")
        return {}


def register_for_event(user_id: int, event_id: int) -> dict:
    """
    Register a user for an event.
    - If event is free: create confirmed registration
    - If event is paid: create an AR receivable and leave registration pending until payment/approval
    Returns registration row (including receivable_id when created)
    """
    try:
        event = get_event(event_id)
        if not event:
            logger.warning(f"Event {event_id} not found for registration")
            return {}

        if not event.get('is_paid'):
            # Free event: auto-confirm
            query = """
                INSERT INTO event_registrations (event_id, user_id, status)
                VALUES (%s, %s, 'confirmed') RETURNING *
            """
            reg = execute_query(query, (event_id, user_id), fetch_one=True)
            return reg or {}

        # Paid event: create receivable and keep registration pending
        price = float(event.get('price') or 0.0)
        receivable = create_receivable(user_id, 'event', event_id, bill_amount=price, final_amount=price)

        reg_query = """
            INSERT INTO event_registrations (event_id, user_id, status, receivable_id)
            VALUES (%s, %s, 'pending', %s) RETURNING *
        """
        reg = execute_query(reg_query, (event_id, user_id, receivable.get('receivable_id') if receivable else None), fetch_one=True)

        # Optionally notify admin externally (handlers will do that)
        return reg or {}
    except Exception as e:
        logger.error(f"Error registering user {user_id} for event {event_id}: {e}")
        return {}


def confirm_registration(registration_id: int, admin_id: int, record_revenue: bool = True) -> dict:
    """
    Confirm a registration (typically after payment approval). Record revenue when required.
    """
    try:
        reg = execute_query("SELECT * FROM event_registrations WHERE registration_id = %s", (registration_id,), fetch_one=True)
        if not reg:
            return {}

        # Mark as confirmed
        updated = execute_query("UPDATE event_registrations SET status='confirmed', updated_at=NOW() WHERE registration_id=%s RETURNING *",
                                (registration_id,), fetch_one=True)

        # If there was a receivable linked, update its status
        receivable_id = reg.get('receivable_id')
        if receivable_id:
            try:
                update_receivable_status(receivable_id)
            except Exception as e:
                logger.debug(f"Could not update receivable {receivable_id}: {e}")

        # Optionally record revenue (useful when admin approves a paid registration)
        try:
            if record_revenue:
                # Fetch event to get price
                event = get_event(reg.get('event_id'))
                amount = float(event.get('price') or 0.0)
                if amount > 0:
                    insert_sql = "INSERT INTO revenue (source_type, source_id, amount, recorded_by, notes) VALUES (%s, %s, %s, %s, %s) RETURNING *"
                    execute_query(insert_sql, ('event', event.get('event_id'), amount, admin_id, f"Registration {registration_id} confirmed"), fetch_one=True)
                    logger.info(f"Recorded revenue for event {event.get('event_id')} amount {amount}")
        except Exception as e:
            logger.debug(f"Could not record revenue for registration {registration_id}: {e}")

        return updated or {}
    except Exception as e:
        logger.error(f"Error confirming registration {registration_id}: {e}")
        return {}
