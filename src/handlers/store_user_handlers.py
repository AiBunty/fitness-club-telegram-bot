"""
Store handlers - User side
- Browse products by category
- Add/remove cart items
- Checkout and order creation
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, CallbackQueryHandler

from src.database.store_operations import (
    get_all_categories, get_products_by_category, get_product,
    validate_cart_item, create_order
)
from src.utils.role_notifications import get_moderator_chat_ids
from src.database.user_operations import get_user
from src.utils.auth import is_admin_id
from src.utils.callback_utils import safe_answer_callback_query

logger = logging.getLogger(__name__)

# Conversation states
STORE_BROWSING, SELECTING_CATEGORY, VIEWING_PRODUCT, CART_REVIEW, CHECKOUT_METHOD = range(5)


async def cmd_store(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /store command - Open store (handles both command and callback)
    """
    user_id = update.effective_user.id
    user = get_user(user_id)
    
    if not user:
        # Handle both message and callback contexts
        msg = update.message or (update.callback_query.message if update.callback_query else None)
        if msg:
            await msg.reply_text("❌ Please register first: /start")
        return ConversationHandler.END
    
    # Answer callback if this is a callback query
    if update.callback_query:
        await update.callback_query.answer()
    
    # Initialize cart in user context if not exists
    if 'store_cart' not in context.user_data:
        context.user_data['store_cart'] = {}
    
    # Show category selection
    categories = get_all_categories()
    
    if not categories:
        msg = update.message or (update.callback_query.message if update.callback_query else None)
        if msg:
            await msg.reply_text("❌ Store is empty. No products available.")
        return ConversationHandler.END
    
    keyboard = [[InlineKeyboardButton(cat, callback_data=f"store_cat:{cat}")] for cat in categories]
    keyboard.append([InlineKeyboardButton("🛒 View Cart", callback_data="store_cart")])
    keyboard.append([InlineKeyboardButton("❌ Close", callback_data="store_close")])
    
    msg_text = (
        "🏪 *Store - Select Category*\n\n"
        "Choose a category to browse products:"
    )
    
    # Use message or callback_query.message depending on context
    if update.callback_query:
        await update.callback_query.message.edit_text(
            msg_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            msg_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    
    return SELECTING_CATEGORY


async def store_select_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Category selected - show products"""
    query = update.callback_query
    await query.answer()
    
    category = query.data.split(":")[1]
    products = get_products_by_category(category)
    
    if not products:
        await query.edit_message_text("❌ No products in this category.")
        return SELECTING_CATEGORY
    
    # Show first product
    context.user_data['store_products'] = products
    context.user_data['store_category'] = category
    context.user_data['store_product_index'] = 0
    
    await _show_product(query, context, 0)
    return VIEWING_PRODUCT


async def _show_product(query_or_message, context: ContextTypes.DEFAULT_TYPE, index: int):
    """Display a product with add to cart button"""
    products = context.user_data.get('store_products', [])
    
    if index >= len(products):
        index = len(products) - 1
    
    product = products[index]
    context.user_data['store_product_index'] = index
    
    discounted_price = product['price'] * (1 - product['discount_percent'] / 100)
    
    text = (
        f"🛍️ *{product['name']}*\n\n"
        f"📝 {product['description']}\n\n"
        f"💰 Price: ₹{product['price']:.2f}"
    )
    
    if product['discount_percent'] > 0:
        text += f" → *₹{discounted_price:.2f}* (-{product['discount_percent']}%)"
    
    text += f"\n\n📦 Stock: {product['stock']} available"
    
    if product['stock'] <= 0:
        text += " ⛔ Out of stock"
    
    keyboard = []
    
    # Add to cart button (if in stock)
    if product['stock'] > 0:
        keyboard.append([
            InlineKeyboardButton("➕ Add to Cart (1)", callback_data=f"store_add:{product['product_id']}:1")
        ])
    
    # Navigation
    prev_idx = index - 1
    next_idx = index + 1
    nav = []
    if prev_idx >= 0:
        nav.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"store_prod:{prev_idx}"))
    if next_idx < len(products):
        nav.append(InlineKeyboardButton("Next ➡️", callback_data=f"store_prod:{next_idx}"))
    
    if nav:
        keyboard.append(nav)
    
    # Cart and back
    keyboard.append([
        InlineKeyboardButton("🛒 View Cart", callback_data="store_cart"),
        InlineKeyboardButton("🏪 Back", callback_data="store_back")
    ])
    
    if hasattr(query_or_message, 'edit_message_text'):
        await query_or_message.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    else:
        await query_or_message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )


async def store_add_to_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add product to cart"""
    query = update.callback_query
    
    parts = query.data.split(":")
    product_id = int(parts[1])
    quantity = int(parts[2])
    
    # Validate
    is_valid, reason = validate_cart_item(query.from_user.id, product_id, quantity)
    if not is_valid:
        await query.answer(f"❌ {reason}", show_alert=True)
        return VIEWING_PRODUCT
    
    # Add to cart
    cart = context.user_data.get('store_cart', {})
    if product_id not in cart:
        cart[product_id] = 0
    
    cart[product_id] += quantity
    context.user_data['store_cart'] = cart
    
    product = get_product(product_id)
    await query.answer(f"✅ Added {quantity}x {product['name']} to cart!", show_alert=False)
    
    # Refresh product view
    index = context.user_data.get('store_product_index', 0)
    await _show_product(query, context, index)
    
    return VIEWING_PRODUCT


async def store_view_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View shopping cart"""
    query = update.callback_query
    await query.answer()
    
    cart = context.user_data.get('store_cart', {})
    
    if not cart or len(cart) == 0:
        await query.edit_message_text(
            "🛒 *Your Cart is Empty!*\n\n"
            "Add products to your cart by browsing the store.\n\n"
            "Tap '🏪 Back to Store' to continue shopping.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏪 Back to Store", callback_data="store_back")]
            ])
        )
        return CART_REVIEW
    
    # Calculate total
    cart_text = "🛒 *Your Shopping Cart*\n\n"
    total = 0
    
    item_buttons = []
    for product_id, qty in cart.items():
        product = get_product(product_id)
        if product:
            discounted_price = product['price'] * (1 - product['discount_percent'] / 100)
            line_total = discounted_price * qty
            total += line_total
            cart_text += (
                f"• *{product['name']}*  \n"
                f"   Quantity: {qty}  |  Price: ₹{discounted_price:.2f}  |  Subtotal: ₹{line_total:.2f}\n"
            )
            # Add quantity adjustment buttons
            item_buttons.append([
                InlineKeyboardButton("➖", callback_data=f"cart_dec:{product_id}"),
                InlineKeyboardButton(f"{qty}", callback_data="noop"),
                InlineKeyboardButton("➕", callback_data=f"cart_inc:{product_id}"),
                InlineKeyboardButton("❌ Remove", callback_data=f"cart_remove:{product_id}")
            ])
            cart_text += "\n"
    cart_text += f"\n*Total: ₹{total:.2f}*\n\n"
    cart_text += (
        "You can adjust quantities with ➖/➕, remove items with ❌, or proceed to checkout.\n"
        "Tap 'Continue Shopping' to add more products."
    )
    keyboard = item_buttons
    keyboard.append([InlineKeyboardButton("💳 Checkout", callback_data="store_checkout")])
    keyboard.append([InlineKeyboardButton("🗑️ Clear Cart", callback_data="store_clear_cart")])
    keyboard.append([InlineKeyboardButton("🏪 Continue Shopping", callback_data="store_back")])
    await query.edit_message_text(
        cart_text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CART_REVIEW

async def cart_inc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    product_id = int(query.data.split(":")[1])
    cart = context.user_data.get('store_cart', {})
    cart[product_id] = cart.get(product_id, 1) + 1
    context.user_data['store_cart'] = cart
    await query.answer("Increased quantity.", show_alert=False)
    await store_view_cart(update, context)
    return CART_REVIEW

async def cart_dec(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    product_id = int(query.data.split(":")[1])
    cart = context.user_data.get('store_cart', {})
    if cart.get(product_id, 0) > 1:
        cart[product_id] -= 1
    else:
        cart.pop(product_id, None)
    context.user_data['store_cart'] = cart
    await query.answer("Decreased quantity.", show_alert=False)
    await store_view_cart(update, context)
    return CART_REVIEW

async def cart_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    product_id = int(query.data.split(":")[1])
    cart = context.user_data.get('store_cart', {})
    cart.pop(product_id, None)
    context.user_data['store_cart'] = cart
    await query.answer("Item removed from cart.", show_alert=False)
    await store_view_cart(update, context)
    return CART_REVIEW

async def store_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start checkout - select payment method"""
    query = update.callback_query
    await query.answer()
    
    cart = context.user_data.get('store_cart', {})
    
    if not cart or len(cart) == 0:
        await query.answer("❌ Cart is empty!", show_alert=True)
        return CART_REVIEW
    
    keyboard = [
        [InlineKeyboardButton("💰 Full Payment", callback_data="store_pay:FULL")],
        [InlineKeyboardButton("🏦 Partial Payment", callback_data="store_pay:PARTIAL")],
        [InlineKeyboardButton("🔄 Credit / Pay Later", callback_data="store_pay:CREDIT")],
        [InlineKeyboardButton("🏪 Back", callback_data="store_cart")]
    ]
    
    await query.edit_message_text(
        "💳 *Checkout - Select Payment Method*\n\n"
        "How would you like to pay?",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    
    return CHECKOUT_METHOD


async def store_process_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process checkout with selected payment method"""
    query = update.callback_query
    await query.answer()
    
    payment_method = query.data.split(":")[1]
    user_id = query.from_user.id
    cart = context.user_data.get('store_cart', {})
    
    # Build cart items for order
    cart_items = []
    for product_id, quantity in cart.items():
        product = get_product(product_id)
        if product:
            discounted_price = product['price'] * (1 - product['discount_percent'] / 100)
            cart_items.append({
                'product_id': product_id,
                'quantity': quantity,
                'unit_price': discounted_price
            })
    
    # Create order
    order = create_order(user_id, cart_items, payment_method, notes="")
    
    if not order:
        await query.edit_message_text("❌ Failed to create order. Try again.")
        return CHECKOUT_METHOD
    
    # Clear cart after successful order
    context.user_data['store_cart'] = {}
    
    order_text = (
        f"✅ *Order Created*\n\n"
        f"📦 Order ID: {order['order_id']}\n"
        f"💰 Total: ₹{order['total_amount']:.2f}\n"
        f"💳 Payment Method: {payment_method}\n\n"
    )
    
    if payment_method == 'FULL':
        order_text += "Awaiting payment confirmation."
    elif payment_method == 'PARTIAL':
        order_text += "Please provide partial payment amount via admin."
    elif payment_method == 'CREDIT':
        order_text += "Credit order created. Payment reminder will be sent."
    
    order_text += "\n\nAdmin will review and confirm your order."
    
    keyboard = [[InlineKeyboardButton("🏪 Continue Shopping", callback_data="store_start")]]
    
    await query.edit_message_text(
        order_text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    # Notify admins for new orders so they can review and act (Full / Partial / Credit)
    try:
        notify_methods = ('FULL', 'PARTIAL', 'CREDIT')
        if payment_method in notify_methods:
            admin_ids = get_moderator_chat_ids(include_staff=False)

            # Build admin-facing message depending on payment method
            if payment_method == 'CREDIT':
                admin_message_header = "🛒 *New Credit Order*"
                admin_message_body = "⚠️ Payment Terms: *Credit / Pay Later*\n\nOpen the order to record payment or set credit terms."
            elif payment_method == 'PARTIAL':
                admin_message_header = "🛒 *New Partial-Payment Order*"
                admin_message_body = "⚠️ Payment Terms: *Partial Payment*\n\nOpen the order to record partial payment or follow up."
            else:
                admin_message_header = "🛒 *New Full-Payment Order*"
                admin_message_body = "ℹ️ Payment Method: *Full Payment*\n\nOpen the order to confirm payment receipt."

            admin_message = (
                f"{admin_message_header}\n\n"
                f"📦 Order ID: #{order['order_id']}\n"
                f"👤 User: {order['user_id']}\n"
                f"💰 Total: ₹{order['total_amount']:.2f}\n\n"
                f"{admin_message_body}"
            )

            from telegram import InlineKeyboardButton, InlineKeyboardMarkup

            buttons = [[InlineKeyboardButton("🔎 Open Order", callback_data=f"store_order_detail:{order['order_id']}")]]

            for admin_id in admin_ids:
                try:
                    await query.bot.send_message(
                        chat_id=admin_id,
                        text=admin_message,
                        parse_mode='Markdown',
                        reply_markup=InlineKeyboardMarkup(buttons)
                    )
                except Exception as e:
                    logger.debug(f"Could not notify admin {admin_id} about order {order['order_id']}: {e}")
    except Exception as e:
        logger.error(f"Error notifying admins about order {order.get('order_id')}: {e}")

    return ConversationHandler.END


async def store_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Back to category selection"""
    query = update.callback_query
    await query.answer()
    
    await cmd_store(update, context)
    return SELECTING_CATEGORY


async def store_clear_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear cart"""
    query = update.callback_query
    
    context.user_data['store_cart'] = {}
    
    await query.answer("🗑️ Cart cleared", show_alert=False)
    await query.edit_message_text("🛒 *Cart is now Empty*\n\nWould you like to continue shopping?",
                                  parse_mode="Markdown",
                                  reply_markup=InlineKeyboardMarkup([
                                      [InlineKeyboardButton("🏪 Back to Store", callback_data="store_back")]
                                  ]))
    
    return CART_REVIEW


async def store_close(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Close store"""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Store closed. Use /store to reopen.")
    return ConversationHandler.END


def get_store_conversation_handler():
    """Return store conversation handler"""
    return ConversationHandler(
        entry_points=[
            CommandHandler("store", cmd_store),
            CallbackQueryHandler(store_select_category, pattern="^store_cat:"),
        ],
        states={
            SELECTING_CATEGORY: [
                CallbackQueryHandler(store_select_category, pattern="^store_cat:"),
                CallbackQueryHandler(store_view_cart, pattern="^store_cart$"),
                CallbackQueryHandler(store_close, pattern="^store_close$"),
            ],
            VIEWING_PRODUCT: [
                CallbackQueryHandler(store_add_to_cart, pattern="^store_add:"),
                CallbackQueryHandler(_store_show_product_handler, pattern="^store_prod:"),
                CallbackQueryHandler(store_view_cart, pattern="^store_cart$"),
                CallbackQueryHandler(store_back, pattern="^store_back$"),
            ],
            CART_REVIEW: [
                CallbackQueryHandler(store_checkout, pattern="^store_checkout$"),
                CallbackQueryHandler(store_clear_cart, pattern="^store_clear_cart$"),
                CallbackQueryHandler(store_back, pattern="^store_back$"),
                CallbackQueryHandler(cart_inc, pattern="^cart_inc:"),
                CallbackQueryHandler(cart_dec, pattern="^cart_dec:"),
                CallbackQueryHandler(cart_remove, pattern="^cart_remove:"),
            ],
            CHECKOUT_METHOD: [
                CallbackQueryHandler(store_process_payment, pattern="^store_pay:"),
                CallbackQueryHandler(store_view_cart, pattern="^store_cart$"),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(store_close, pattern="^store_close$")
        ]
    )


async def _store_show_product_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle product navigation"""
    query = update.callback_query
    await query.answer()
    
    index = int(query.data.split(":")[1])
    await _show_product(query, context, index)
