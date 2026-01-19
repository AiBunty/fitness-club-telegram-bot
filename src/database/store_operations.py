"""
Store management operations - Products, Inventory, Orders, Cart
Reuses existing payment logic from subscriptions
"""

import logging
from datetime import datetime
from src.database.connection import execute_query
from src.database.ar_operations import create_receivable, update_receivable_status

logger = logging.getLogger(__name__)

# ================================================================
# PRODUCTS - Store catalog
# ================================================================

def create_or_update_product(product_code: str, category: str, name: str, description: str,
                              price: float, discount_percent: float, stock: int, status: str = 'ACTIVE') -> dict:
    """
    Create or update product by product_code (UPSERT)
    Prevents duplicates using product_code as unique key
    
    Args:
        product_code: Unique product identifier
        category: Product category
        name: Product name
        description: Product description
        price: Price in rupees
        discount_percent: Discount percentage (0-100)
        stock: Stock quantity
        status: ACTIVE or INACTIVE
    
    Returns:
        Product dict or None on error
    """
    try:
        query = """
            INSERT INTO store_products 
            (product_code, category, name, description, price, discount_percent, stock, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (product_code)
            DO UPDATE SET
                category = EXCLUDED.category,
                name = EXCLUDED.name,
                description = EXCLUDED.description,
                price = EXCLUDED.price,
                discount_percent = EXCLUDED.discount_percent,
                stock = EXCLUDED.stock,
                status = EXCLUDED.status,
                updated_at = CURRENT_TIMESTAMP
            RETURNING *
        """
        result = execute_query(query, (product_code, category, name, description, price, discount_percent, stock, status), 
                              fetch_one=True)
        
        if result:
            logger.info(f"Product upserted: {product_code} - {name}")
            return result
        return None
    except Exception as e:
        logger.error(f"Error upserting product {product_code}: {e}")
        return None


def get_products_by_category(category: str) -> list:
    """Get all active products in a category"""
    try:
        query = """
            SELECT * FROM store_products
            WHERE category = %s AND status = 'ACTIVE'
            ORDER BY name
        """
        return execute_query(query, (category,))
    except Exception as e:
        logger.error(f"Error getting products for category {category}: {e}")
        return []


def get_product(product_id: int) -> dict:
    """Get product by ID"""
    try:
        query = "SELECT * FROM store_products WHERE product_id = %s"
        return execute_query(query, (product_id,), fetch_one=True)
    except Exception as e:
        logger.error(f"Error getting product {product_id}: {e}")
        return None


def get_all_categories() -> list:
    """Get all unique categories with at least one active product"""
    try:
        query = """
            SELECT DISTINCT category FROM store_products
            WHERE status = 'ACTIVE'
            ORDER BY category
        """
        results = execute_query(query)
        return [r['category'] for r in results] if results else []
    except Exception as e:
        logger.error(f"Error getting categories: {e}")
        return []


def validate_stock(product_id: int, quantity: int) -> bool:
    """Check if enough stock available"""
    try:
        product = get_product(product_id)
        if not product:
            return False
        return product['stock'] >= quantity
    except Exception as e:
        logger.error(f"Error validating stock: {e}")
        return False


# ================================================================
# CART - User shopping cart (in-memory temporary storage)
# ================================================================
# Note: Cart is temporary and stored in user context, not database
# Persists only until checkout

def validate_cart_item(user_id: int, product_id: int, quantity: int) -> tuple[bool, str]:
    """
    Validate cart item before adding
    
    Returns:
        (is_valid, reason_if_invalid)
    """
    try:
        if quantity <= 0:
            return False, "Quantity must be > 0"
        
        if quantity > 100:  # Arbitrary limit
            return False, "Quantity too high (max 100)"
        
        product = get_product(product_id)
        if not product:
            return False, "Product not found"
        
        if product['status'] != 'ACTIVE':
            return False, "Product not available"
        
        if not validate_stock(product_id, quantity):
            return False, f"Only {product['stock']} in stock"
        
        return True, ""
    except Exception as e:
        logger.error(f"Error validating cart item: {e}")
        return False, "Server error"


# ================================================================
# ORDERS - Checkout & Order Management
# ================================================================

def create_order(user_id: int, cart_items: list, payment_method: str, notes: str = "") -> dict:
    """
    Create order from cart
    
    Args:
        user_id: User ID
        cart_items: List of {'product_id': int, 'quantity': int, 'unit_price': float}
        payment_method: FULL/PARTIAL/CREDIT/CASH
        notes: Optional order notes
    
    Returns:
        Order dict with order_id, total_amount, etc
    """
    try:
        if not cart_items or len(cart_items) == 0:
            logger.warning(f"Empty cart for user {user_id}")
            return None
        
        # Calculate total
        total_amount = 0
        order_items = []
        
        for item in cart_items:
            product = get_product(item['product_id'])
            if not product:
                logger.warning(f"Product {item['product_id']} not found during checkout")
                return None
            
            # Revalidate stock server-side
            if not validate_stock(item['product_id'], item['quantity']):
                logger.warning(f"Stock validation failed for product {item['product_id']} qty {item['quantity']}")
                return None
            
            # Calculate line total
            discounted_price = product['price'] * (1 - product['discount_percent'] / 100)
            line_total = discounted_price * item['quantity']
            total_amount += line_total
            
            order_items.append({
                'product_id': item['product_id'],
                'quantity': item['quantity'],
                'unit_price': discounted_price,
                'line_total': line_total
            })
        
        # Create order record (status = OPEN)
        order_query = """
            INSERT INTO store_orders 
            (user_id, total_amount, payment_method, payment_status, notes, created_at)
            VALUES (%s, %s, %s, 'OPEN', %s, CURRENT_TIMESTAMP)
            RETURNING order_id, total_amount, created_at
        """
        order = execute_query(order_query, (user_id, total_amount, payment_method, notes), fetch_one=True)
        
        if not order:
            logger.error(f"Failed to create order for user {user_id}")
            return None
        
        order_id = order['order_id']
        
        # Insert order items
        for item in order_items:
            item_query = """
                INSERT INTO store_order_items 
                (order_id, product_id, quantity, unit_price, line_total)
                VALUES (%s, %s, %s, %s, %s)
            """
            execute_query(item_query, (order_id, item['product_id'], item['quantity'], 
                                      item['unit_price'], item['line_total']))
        
        logger.info(f"Order created: order_id={order_id}, user={user_id}, total={total_amount}, method={payment_method}")
        
        return {
            'order_id': order_id,
            'user_id': user_id,
            'total_amount': total_amount,
            'payment_method': payment_method,
            'payment_status': 'OPEN',
            'created_at': order['created_at'],
            'items': order_items
        }
    except Exception as e:
        logger.error(f"Error creating order for user {user_id}: {e}")
        return None


def get_order(order_id: int) -> dict:
    """Get order details"""
    try:
        query = "SELECT * FROM store_orders WHERE order_id = %s"
        return execute_query(query, (order_id,), fetch_one=True)
    except Exception as e:
        logger.error(f"Error getting order {order_id}: {e}")
        return None


def get_user_orders(user_id: int, status_filter: str = None) -> list:
    """Get user's orders, optionally filtered by status"""
    try:
        if status_filter:
            query = """
                SELECT * FROM store_orders
                WHERE user_id = %s AND payment_status = %s
                ORDER BY created_at DESC
            """
            return execute_query(query, (user_id, status_filter))
        else:
            query = """
                SELECT * FROM store_orders
                WHERE user_id = %s
                ORDER BY created_at DESC
            """
            return execute_query(query, (user_id,))
    except Exception as e:
        logger.error(f"Error getting orders for user {user_id}: {e}")
        return []


def get_all_orders(status_filter: str = None) -> list:
    """Get all orders, optionally filtered by status"""
    try:
        if status_filter:
            query = """
                SELECT * FROM store_orders
                WHERE payment_status = %s
                ORDER BY created_at DESC
            """
            return execute_query(query, (status_filter,))
        else:
            query = "SELECT * FROM store_orders ORDER BY created_at DESC"
            return execute_query(query)
    except Exception as e:
        logger.error(f"Error getting all orders: {e}")
        return []


def apply_order_payment(order_id: int, amount: float, payment_method: str, 
                        admin_id: int = None, reference: str = None) -> dict:
    """
    Apply payment to order
    REUSES payment logic from subscriptions
    
    Args:
        order_id: Order ID
        amount: Payment amount
        payment_method: CASH/UPI/BANK_TRANSFER/etc
        admin_id: Admin ID if confirmed by admin
        reference: Payment reference/transaction ID
    
    Returns:
        Updated order dict or None
    """
    try:
        order = get_order(order_id)
        if not order:
            logger.error(f"Order {order_id} not found")
            return None
        
        # Calculate balance after payment
        balance = order['balance'] - amount
        
        # Determine new payment status
        if balance <= 0:
            new_status = 'PAID'
            balance = 0  # No negative balance
        elif order['payment_method'] == 'CREDIT':
            new_status = 'CREDIT'
        else:
            new_status = 'PARTIAL'
        
        # Update order
        update_query = """
            UPDATE store_orders
            SET balance = %s, payment_status = %s, updated_at = CURRENT_TIMESTAMP
            WHERE order_id = %s
            RETURNING *
        """
        updated_order = execute_query(update_query, (balance, new_status, order_id), fetch_one=True)
        
        # Log payment transaction (for audit trail)
        if updated_order:
            log_query = """
                INSERT INTO store_order_payments
                (order_id, amount, payment_method, admin_confirmed, admin_id, reference, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            """
            execute_query(log_query, (order_id, amount, payment_method, admin_id is not None, admin_id, reference))
            
            logger.info(f"Payment applied to order {order_id}: {amount}, status={new_status}")
        
        return updated_order
    except Exception as e:
        logger.error(f"Error applying payment to order {order_id}: {e}")
        return None


def apply_order_credit(order_id: int, admin_id: int, due_days: int = 7) -> dict:
    """
    Mark an order as approved on credit terms (no amount received now).
    Creates an AR receivable for the outstanding balance and marks order as CREDIT.

    Args:
        order_id: Order to mark as credit
        admin_id: Admin approving the credit
        due_days: Number of days until due (default 7)

    Returns:
        Updated order dict or None
    """
    try:
        order = get_order(order_id)
        if not order:
            logger.error(f"Order {order_id} not found for credit approval")
            return None

        from datetime import datetime, timedelta
        due_date = (datetime.now() + timedelta(days=due_days)).date()

        # Update order to credit terms
        update_query = """
            UPDATE store_orders
            SET payment_method = 'CREDIT', payment_status = 'CREDIT', payment_approved_by = %s,
                payment_due_date = %s, updated_at = CURRENT_TIMESTAMP
            WHERE order_id = %s
            RETURNING *
        """
        updated = execute_query(update_query, (admin_id, due_date, order_id), fetch_one=True)

        if not updated:
            logger.error(f"Failed to mark order {order_id} as credit")
            return None

        # Create AR receivable for this order so reminders/tracking work
        try:
            create_receivable(
                user_id=updated['user_id'],
                receivable_type='store_order',
                source_id=order_id,
                bill_amount=float(updated['total_amount']),
                discount_amount=0.0,
                final_amount=float(updated['balance'] or updated['total_amount']),
                due_date=str(due_date)
            )
            # Recompute receivable status (creates initial pending/partial/paid state)
            rec = create_receivable
        except Exception as ar_err:
            logger.debug(f"Could not create AR receivable for order {order_id}: {ar_err}")

        logger.info(f"Order {order_id} approved on credit by admin {admin_id}")
        return updated
    except Exception as e:
        logger.error(f"Error applying credit to order {order_id}: {e}")
        return None


def close_order(order_id: int, admin_id: int, reason: str = "") -> bool:
    """
    Close/complete an order
    
    Args:
        order_id: Order ID
        admin_id: Admin who closed it
        reason: Reason for closing
    
    Returns:
        Success status
    """
    try:
        query = """
            UPDATE store_orders
            SET payment_status = 'CLOSED', closed_by = %s, closed_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
            WHERE order_id = %s AND payment_status = 'PAID'
            RETURNING order_id
        """
        result = execute_query(query, (admin_id, order_id), fetch_one=True)
        
        if result:
            logger.info(f"Order {order_id} closed by admin {admin_id}: {reason}")
            return True
        return False
    except Exception as e:
        logger.error(f"Error closing order {order_id}: {e}")
        return False


# ================================================================
# STOCK MANAGEMENT - Update inventory
# ================================================================

def reduce_stock(product_id: int, quantity: int, order_id: int = None) -> bool:
    """
    Reduce stock after order confirmed
    
    Args:
        product_id: Product ID
        quantity: Quantity to reduce
        order_id: Optional order_id for logging
    
    Returns:
        Success status
    """
    try:
        query = """
            UPDATE store_products
            SET stock = stock - %s, updated_at = CURRENT_TIMESTAMP
            WHERE product_id = %s AND stock >= %s
            RETURNING stock
        """
        result = execute_query(query, (quantity, product_id, quantity), fetch_one=True)
        
        if result:
            logger.info(f"Stock reduced for product {product_id}: qty={quantity}, remaining={result['stock']}")
            return True
        else:
            logger.warning(f"Stock reduction failed for product {product_id}: qty={quantity}")
            return False
    except Exception as e:
        logger.error(f"Error reducing stock: {e}")
        return False


def increase_stock(product_id: int, quantity: int, reason: str = "") -> bool:
    """Increase stock (e.g., order cancellation, returned items)"""
    try:
        query = """
            UPDATE store_products
            SET stock = stock + %s, updated_at = CURRENT_TIMESTAMP
            WHERE product_id = %s
            RETURNING stock
        """
        result = execute_query(query, (quantity, product_id), fetch_one=True)
        
        if result:
            logger.info(f"Stock increased for product {product_id}: qty={quantity}, reason={reason}")
            return True
        return False
    except Exception as e:
        logger.error(f"Error increasing stock: {e}")
        return False
