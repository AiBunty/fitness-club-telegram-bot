"""
Store admin handlers
- Manage products (CRUD)
- Manage orders (view, confirm payments, close)
- Excel bulk upload for products
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, CallbackQueryHandler, MessageHandler, filters

from src.database.store_operations import (
    create_or_update_product, get_all_orders, get_order, close_order
)
from src.database.payment_approvals import approve_store_payment, approve_store_credit
from src.utils.auth import is_admin_id

logger = logging.getLogger(__name__)

# Conversation states
STORE_ADMIN_MENU, ORDERS_VIEW, ORDER_DETAIL, PAYMENT_ACTION = range(4)


async def cmd_store_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /store_admin command - Store management dashboard
    """
    if not is_admin_id(update.effective_user.id):
        await update.message.reply_text("❌ Admin access only.")
        return ConversationHandler.END
    
    admin_id = update.effective_user.id
    
    keyboard = [
        [InlineKeyboardButton("📋 View Orders", callback_data="store_admin_orders")],
        [InlineKeyboardButton("📦 Manage Products", callback_data="store_admin_products")],
        [InlineKeyboardButton("📊 Store Statistics", callback_data="store_admin_stats")],
        [InlineKeyboardButton("❌ Close", callback_data="store_admin_close")]
    ]
    
    await update.message.reply_text(
        "🏪 *Store Admin Dashboard*\n\n"
        "Manage products, orders, and payments",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    
    return STORE_ADMIN_MENU


async def store_admin_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View pending orders"""
    query = update.callback_query
    await query.answer()
    
    # Get orders that need attention (OPEN or PARTIAL)
    open_orders = get_all_orders(status_filter='OPEN')
    partial_orders = get_all_orders(status_filter='PARTIAL')
    credit_orders = get_all_orders(status_filter='CREDIT')
    
    pending_count = len(open_orders or []) + len(partial_orders or []) + len(credit_orders or [])
    
    text = (
        "📋 *Order Management*\n\n"
        f"🔓 Open Orders: {len(open_orders or [])}\n"
        f"🔄 Partial Payment: {len(partial_orders or [])}\n"
        f"🔐 Credit Orders: {len(credit_orders or [])}\n\n"
        f"⚠️  Total Pending: {pending_count}"
    )
    
    keyboard = [
        [InlineKeyboardButton("🔓 View Open", callback_data="store_orders_filter:OPEN")],
        [InlineKeyboardButton("🔄 View Partial", callback_data="store_orders_filter:PARTIAL")],
        [InlineKeyboardButton("🔐 View Credit", callback_data="store_orders_filter:CREDIT")],
        [InlineKeyboardButton("⬅️ Back", callback_data="store_admin_menu")]
    ]
    
    await query.edit_message_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return ORDERS_VIEW


async def store_orders_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View orders by status"""
    query = update.callback_query
    await query.answer()
    
    status = query.data.split(":")[1]
    orders = get_all_orders(status_filter=status)
    
    if not orders or len(orders) == 0:
        await query.edit_message_text(
            f"No {status} orders found.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Back", callback_data="store_admin_orders")]
            ])
        )
        return ORDERS_VIEW
    
    text = f"📋 *{status} Orders* ({len(orders)} total)\n\n"
    
    # Show first 5 orders
    for order in orders[:5]:
        text += f"📦 Order #{order['order_id']}\n"
        text += f"👤 User: {order['user_id']}\n"
        text += f"💰 Total: ₹{order['total_amount']:.2f}\n"
        text += f"💳 Status: {order['payment_status']}\n"
        text += f"📅 Created: {order['created_at'].strftime('%d-%m-%Y')}\n\n"
    
    keyboard = []
    
    # Add buttons for each order
    for order in orders[:3]:
        keyboard.append([InlineKeyboardButton(f"Order #{order['order_id']}", 
                                            callback_data=f"store_order_detail:{order['order_id']}")])
    
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="store_admin_orders")])
    
    await query.edit_message_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return ORDERS_VIEW


async def store_order_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View order details and payment options"""
    query = update.callback_query
    await query.answer()
    
    order_id = int(query.data.split(":")[1])
    order = get_order(order_id)
    
    if not order:
        await query.answer("❌ Order not found", show_alert=True)
        return ORDERS_VIEW
    
    context.user_data['current_order_id'] = order_id
    
    text = (
        f"📦 *Order #{order_id} Details*\n\n"
        f"👤 User ID: {order['user_id']}\n"
        f"💰 Total: ₹{order['total_amount']:.2f}\n"
        f"💳 Payment Method: {order['payment_method']}\n"
        f"📊 Status: {order['payment_status']}\n"
        f"📅 Created: {order['created_at'].strftime('%d-%m-%Y %H:%M')}\n"
    )
    
    if order['balance']:
        text += f"\n💸 Remaining Balance: ₹{order['balance']:.2f}"
    
    keyboard = [
        [InlineKeyboardButton("💰 Record Payment", callback_data="store_order_payment")],
        [InlineKeyboardButton("✅ Close Order", callback_data="store_order_close")],
        [InlineKeyboardButton("⬅️ Back", callback_data="store_admin_orders")]
    ]
    
    await query.edit_message_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return ORDER_DETAIL


async def store_order_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Record payment for order"""
    query = update.callback_query
    await query.answer()
    
    order_id = context.user_data.get('current_order_id')
    order = get_order(order_id)
    
    if not order:
        await query.answer("❌ Order not found", show_alert=True)
        return ORDER_DETAIL
    
    keyboard = [
        [InlineKeyboardButton("💳 UPI/Card", callback_data="store_payment_method:UPI")],
        [InlineKeyboardButton("🏦 Bank Transfer", callback_data="store_payment_method:BANK")],
        [InlineKeyboardButton("💵 Cash (Confirmed)", callback_data="store_payment_method:CASH")],
        [InlineKeyboardButton("⬅️ Back", callback_data=f"store_order_detail:{order_id}")]
    ]
    
    await query.edit_message_text(
        f"💰 *Record Payment for Order #{order_id}*\n\n"
        f"Remaining: ₹{order['balance'] or order['total_amount']:.2f}\n\n"
        f"Select payment method:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return PAYMENT_ACTION


async def store_payment_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ask for payment amount"""
    query = update.callback_query
    await query.answer()
    
    payment_method = query.data.split(":")[1]
    context.user_data['payment_method'] = payment_method
    
    order_id = context.user_data.get('current_order_id')
    order = get_order(order_id)
    
    await query.edit_message_text(
        f"💰 *Enter Payment Amount*\n\n"
        f"Order #{order_id}\n"
        f"Remaining: ₹{order['balance'] or order['total_amount']:.2f}\n\n"
        f"Reply with the amount in rupees (e.g., 500)",
        parse_mode="Markdown"
    )
    
    return PAYMENT_ACTION


async def store_close(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Close admin dashboard"""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Store admin dashboard closed.")
    return ConversationHandler.END


def get_store_admin_conversation_handler():
    """Return store admin conversation handler"""
    return ConversationHandler(
        entry_points=[
            CommandHandler("store_admin", cmd_store_admin),
        ],
        states={
            STORE_ADMIN_MENU: [
                CallbackQueryHandler(store_admin_orders, pattern="^store_admin_orders$"),
                CallbackQueryHandler(store_close, pattern="^store_admin_close$"),
            ],
            ORDERS_VIEW: [
                CallbackQueryHandler(store_admin_orders, pattern="^store_admin_orders$"),
                CallbackQueryHandler(store_orders_filter, pattern="^store_orders_filter:"),
                CallbackQueryHandler(store_order_detail, pattern="^store_order_detail:"),
            ],
            ORDER_DETAIL: [
                CallbackQueryHandler(store_order_payment, pattern="^store_order_payment$"),
                CallbackQueryHandler(store_orders_filter, pattern="^store_orders_filter:"),
            ],
            PAYMENT_ACTION: [
                CallbackQueryHandler(store_payment_method, pattern="^store_payment_method:"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, _handle_payment_amount),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(store_close, pattern="^store_admin_close$")
        ]
    )


async def _handle_payment_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle payment amount input"""
    try:
        amount = float(update.message.text)

        # Accept zero as a special-case: admin approves credit sale (no cash received now)
        if amount < 0:
            await update.message.reply_text("❌ Amount must be >= 0")
            return PAYMENT_ACTION
        
        order_id = context.user_data.get('current_order_id')
        payment_method = context.user_data.get('payment_method', 'OTHER')
        admin_id = update.effective_user.id
        
        order = get_order(order_id)
        if not order:
            await update.message.reply_text("❌ Order not found")
            return PAYMENT_ACTION
        
        # Special-case: zero amount => treat as credit approval
        if amount == 0:
            result = approve_store_credit(order_id, admin_id)

            if result:
                await update.message.reply_text(
                    f"✅ Order approved on CREDIT terms\n\n"
                    f"Order #{order_id}\n"
                    f"Total: ₹{result['total_amount']:.2f}\n"
                    f"Balance: ₹{result['balance'] or result['total_amount']:.2f}\n"
                    f"Due Date: {result.get('payment_due_date')}",
                    parse_mode="Markdown"
                )
                # Schedule payment reminders for credit approval (idempotent)
                try:
                    user_id = order['user_id']
                    if context and getattr(context, 'application', None):
                        from src.utils.event_dispatcher import schedule_followups
                        schedule_followups(context.application, user_id, 'PAYMENT_REMINDER_1', {'order_id': order_id, 'amount': result.get('balance'), 'name': ''})
                except Exception:
                    logger.debug('Could not schedule follow-ups for credit-approved order')
            else:
                await update.message.reply_text("❌ Failed to approve order on credit")

        else:
            # Apply payment
            result = approve_store_payment(order_id, amount, payment_method,
                                           admin_id=admin_id, reference=f"Admin payment by {admin_id}")

            if result:
                await update.message.reply_text(
                    f"✅ Payment recorded\n\n"
                    f"Order #{order_id}\n"
                    f"Amount: ₹{amount:.2f}\n"
                    f"Status: {result['payment_status']}\n"
                    f"Remaining: ₹{result['balance']:.2f}",
                    parse_mode="Markdown"
                )
                # Notify the order owner that payment has been recorded
                try:
                    user_id = order['user_id']
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=(
                            f"💳 *Payment Received*\n\n"
                            f"📦 Order ID: #{order_id}\n"
                            f"💰 Amount Recorded: ₹{amount:.2f}\n"
                            f"📊 Status: {result['payment_status']}\n"
                            f"🔎 Remaining: ₹{result['balance']:.2f}\n\n"
                            "If this was a mistake, contact the admin."
                        ),
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    logger.debug(f"Could not notify user {order.get('user_id')} about payment {order_id}: {e}")
                # If balance remains, schedule payment reminders (idempotent)
                try:
                    if result.get('balance', 0) and context and getattr(context, 'application', None):
                        from src.utils.event_dispatcher import schedule_followups
                        schedule_followups(context.application, user_id, 'PAYMENT_REMINDER_1', {'order_id': order_id, 'amount': result.get('balance'), 'name': ''})
                except Exception:
                    logger.debug('Could not schedule payment follow-ups after applying payment')
            else:
                await update.message.reply_text("❌ Failed to record payment")
        
        return ConversationHandler.END
    
    except ValueError:
        await update.message.reply_text("❌ Invalid amount. Use format: 500.50")
        return PAYMENT_ACTION
    except Exception as e:
        logger.error(f"Error handling payment: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")
        return PAYMENT_ACTION
