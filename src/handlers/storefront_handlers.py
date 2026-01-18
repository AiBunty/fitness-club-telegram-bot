"""
User Storefront and Product Browsing
Users can browse and order store products, subscriptions, PT plans, and events
"""

import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from src.database.connection import execute_query
from src.database.ar_operations import create_receivable, create_transactions, update_receivable_status
from src.utils.auth import check_user_approved
from src.database.user_operations import user_exists

logger = logging.getLogger(__name__)

# Conversation states
BROWSE_STORE, SELECT_PRODUCT, CONFIRM_ORDER = range(3)


# ============ Subscription Browsing ============

async def cmd_browse_subscriptions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Browse available subscription plans"""
    # Handle both command and callback contexts
    if update.callback_query:
        await update.callback_query.answer()
        message = update.callback_query.message
        user_id = update.callback_query.from_user.id
    else:
        message = update.message
        user_id = update.message.from_user.id
    
    if not user_exists(user_id):
        await message.reply_text("❌ You must register first. Use /start")
        return ConversationHandler.END
    if not check_user_approved(user_id):
        await message.reply_text("⏳ Registration pending approval.")
        return ConversationHandler.END
    
    try:
        plans = execute_query("""
            SELECT plan_id, name, duration_days, price, description
            FROM subscription_plans
            WHERE status = 'active'
            ORDER BY price ASC
        """)
        
        if not plans:
            await message.reply_text("📭 No subscription plans available.")
            return ConversationHandler.END
        
        text = "📅 *Available Subscription Plans*\n\n"
        keyboard = []
        
        for plan in plans:
            text += (
                f"**{plan['name']}**\n"
                f"⏱️ {plan['duration_days']} days\n"
                f"💵 Rs {plan['price']}\n"
                f"📝 {plan['description'] or 'Premium access'}\n\n"
            )
            keyboard.append([
                InlineKeyboardButton(
                    f"Subscribe - Rs {plan['price']}", 
                    callback_data=f"subscribe_plan_{plan['plan_id']}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="main_menu")])
        
        await message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error browsing subscriptions: {e}")
        await message.reply_text(f"❌ Error: {e}")
    
    return ConversationHandler.END


# ============ PT Plans Browsing ============

async def cmd_browse_pt_plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Browse available PT subscription plans"""
    if update.callback_query:
        await update.callback_query.answer()
        message = update.callback_query.message
        user_id = update.callback_query.from_user.id
    else:
        message = update.message
        user_id = update.message.from_user.id
    
    if not user_exists(user_id):
        await message.reply_text("❌ You must register first. Use /start")
        return ConversationHandler.END
    if not check_user_approved(user_id):
        await message.reply_text("⏳ Registration pending approval.")
        return ConversationHandler.END
    
    try:
        plans = execute_query("""
            SELECT pt_id, name, duration_days, price, description
            FROM pt_subscriptions
            WHERE status = 'active'
            ORDER BY price ASC
        """)
        
        if not plans:
            await message.reply_text("📭 No PT plans available.")
            return ConversationHandler.END
        
        text = "💪 *Available Personal Training Plans*\n\n"
        keyboard = []
        
        for plan in plans:
            text += (
                f"**{plan['name']}**\n"
                f"⏱️ {plan['duration_days']} days\n"
                f"💵 Rs {plan['price']}\n"
                f"📝 {plan['description'] or 'Expert training'}\n\n"
            )
            keyboard.append([
                InlineKeyboardButton(
                    f"Enroll - Rs {plan['price']}", 
                    callback_data=f"enroll_pt_{plan['pt_id']}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="main_menu")])
        
        await message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error browsing PT plans: {e}")
        await message.reply_text(f"❌ Error: {e}")
    
    return ConversationHandler.END


# ============ Events Browsing ============

async def cmd_browse_events(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Browse available one-day events"""
    if update.callback_query:
        await update.callback_query.answer()
        message = update.callback_query.message
        user_id = update.callback_query.from_user.id
    else:
        message = update.message
        user_id = update.message.from_user.id
    
    if not user_exists(user_id):
        await message.reply_text("❌ You must register first. Use /start")
        return ConversationHandler.END
    if not check_user_approved(user_id):
        await message.reply_text("⏳ Registration pending approval.")
        return ConversationHandler.END
    
    try:
        events = execute_query("""
            SELECT event_id, name, event_date, price, description, max_attendees, current_attendees
            FROM one_day_events
            WHERE status = 'active' AND event_date >= CURRENT_DATE
            ORDER BY event_date ASC
        """)
        
        if not events:
            await message.reply_text("📭 No upcoming events.")
            return ConversationHandler.END
        
        text = "🎉 *Upcoming Events*\n\n"
        keyboard = []
        
        for event in events:
            availability = event['max_attendees'] - event['current_attendees'] if event['max_attendees'] else "∞"
            text += (
                f"**{event['name']}**\n"
                f"📅 {event['event_date'].strftime('%d-%m-%Y')}\n"
                f"💵 Rs {event['price']}\n"
                f"👥 {availability} seats available\n"
                f"📝 {event['description'] or 'Join us!'}\n\n"
            )
            keyboard.append([
                InlineKeyboardButton(
                    f"Register - Rs {event['price']}", 
                    callback_data=f"register_event_{event['event_id']}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="main_menu")])
        
        await message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error browsing events: {e}")
        await message.reply_text(f"❌ Error: {e}")
    
    return ConversationHandler.END


# ============ Store Products Browsing ============

async def cmd_browse_store(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Browse store products by category"""
    if update.callback_query:
        await update.callback_query.answer()
        message = update.callback_query.message
        user_id = update.callback_query.from_user.id
    else:
        message = update.message
        user_id = update.message.from_user.id
    
    if not user_exists(user_id):
        await message.reply_text("❌ You must register first. Use /start")
        return ConversationHandler.END
    if not check_user_approved(user_id):
        await message.reply_text("⏳ Registration pending approval.")
        return ConversationHandler.END
    
    try:
        categories = execute_query("""
            SELECT DISTINCT category FROM store_products
            WHERE status = 'active'
            ORDER BY category
        """)
        
        if not categories:
            await message.reply_text("📭 No products available.")
            return ConversationHandler.END
        
        keyboard = []
        for cat in categories:
            keyboard.append([
                InlineKeyboardButton(f"📦 {cat['category']}", callback_data=f"store_cat_{cat['category']}")
            ])
        
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="main_menu")])
        
        await message.reply_text(
            "🛒 *Store Categories*\n\nSelect a category:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error browsing store: {e}")
        await message.reply_text(f"❌ Error: {e}")
    
    return BROWSE_STORE


async def browse_store_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show products in a category"""
    query = update.callback_query
    await query.answer()
    
    category = query.data.split("_", 2)[2]
    user_id = query.from_user.id
    
    try:
        products = execute_query("""
            SELECT product_id, name, description, mrp, discount_percent, final_price, stock
            FROM store_products
            WHERE status = 'active' AND category = %s AND stock > 0
            ORDER BY name
        """, (category,))
        
        if not products:
            await query.message.reply_text(f"📭 No products in {category}.")
            return BROWSE_STORE
        
        text = f"🛒 *{category}*\n\n"
        keyboard = []
        
        for product in products:
            discount_str = f" (-{product['discount_percent']}%)" if product['discount_percent'] > 0 else ""
            text += (
                f"**{product['name']}**\n"
                f"MRP: Rs {product['mrp']}{discount_str}\n"
                f"💵 **Rs {product['final_price']}**\n"
                f"📝 {product['description'][:100] or 'Quality product'}\n"
                f"📦 Stock: {product['stock']}\n\n"
            )
            keyboard.append([
                InlineKeyboardButton(
                    f"Add to Cart - Rs {product['final_price']}", 
                    callback_data=f"add_product_{product['product_id']}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="cmd_browse_store")])
        
        await query.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error browsing category {category}: {e}")
        await query.message.reply_text(f"❌ Error: {e}")
    
    return SELECT_PRODUCT


# ============ Order Processing ============

async def process_product_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process order for store product, subscription, PT, or event"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    try:
        # Determine product type and ID
        if data.startswith("add_product_"):
            product_id = int(data.split("_")[-1])
            product = execute_query(
                "SELECT * FROM store_products WHERE product_id = %s",
                (product_id,),
                fetch_one=True
            )
            if not product:
                await query.message.reply_text("❌ Product not found.")
                return
            
            amount = float(product['final_price'])
            product_name = product['name']
            ar_enabled = product.get('ar_enabled', False)
            
            # Create order record
            order_result = execute_query(
                """INSERT INTO user_product_orders 
                   (user_id, product_id, quantity, unit_price, total_amount)
                   VALUES (%s, %s, 1, %s, %s)
                   RETURNING order_id""",
                (user_id, product_id, amount, amount),
                fetch_one=True
            )
            order_id = order_result['order_id']
            message = f"✅ Order Placed!\n\n📦 {product_name}\n💵 Rs {amount}"
        
        elif data.startswith("subscribe_plan_"):
            plan_id = int(data.split("_")[-1])
            plan = execute_query(
                "SELECT * FROM subscription_plans WHERE plan_id = %s",
                (plan_id,),
                fetch_one=True
            )
            if not plan:
                await query.message.reply_text("❌ Plan not found.")
                return
            
            amount = float(plan['price'])
            product_name = plan['name']
            ar_enabled = plan.get('ar_enabled', True)
            source_type = 'subscription_plan'
            source_id = plan_id
            message = f"✅ Subscription Initiated!\n\n📅 {product_name}\n💵 Rs {amount}\n⏱️ {plan['duration_days']} days"
        
        elif data.startswith("enroll_pt_"):
            pt_id = int(data.split("_")[-1])
            plan = execute_query(
                "SELECT * FROM pt_subscriptions WHERE pt_id = %s",
                (pt_id,),
                fetch_one=True
            )
            if not plan:
                await query.message.reply_text("❌ PT plan not found.")
                return
            
            amount = float(plan['price'])
            product_name = plan['name']
            ar_enabled = plan.get('ar_enabled', True)
            source_type = 'pt_plan'
            source_id = pt_id
            message = f"✅ PT Enrollment Initiated!\n\n💪 {product_name}\n💵 Rs {amount}\n⏱️ {plan['duration_days']} days"
        
        elif data.startswith("register_event_"):
            event_id = int(data.split("_")[-1])
            event = execute_query(
                "SELECT * FROM one_day_events WHERE event_id = %s",
                (event_id,),
                fetch_one=True
            )
            if not event:
                await query.message.reply_text("❌ Event not found.")
                return
            
            amount = float(event['price'])
            product_name = event['name']
            ar_enabled = event.get('ar_enabled', True)
            source_type = 'event'
            source_id = event_id
            
            # Register user
            execute_query(
                "INSERT INTO user_event_registrations (user_id, event_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (user_id, event_id)
            )
            message = f"✅ Event Registration Confirmed!\n\n🎉 {product_name}\n💵 Rs {amount}\n📅 {event['event_date'].strftime('%d-%m-%Y')}"
        
        else:
            await query.message.reply_text("❌ Invalid product type.")
            return
        
        # Create AR receivable if enabled for this product
        if ar_enabled:
            try:
                receivable = create_receivable(
                    user_id=user_id,
                    receivable_type=source_type if 'source_type' in locals() else 'store_product',
                    source_id=source_id if 'source_id' in locals() else order_id if 'order_id' in locals() else None,
                    bill_amount=amount,
                    discount_amount=0.0,
                    final_amount=amount,
                    due_date=None  # Flexible payment date
                )
                
                if receivable and receivable.get('receivable_id'):
                    create_transactions(
                        receivable_id=receivable['receivable_id'],
                        lines=[{
                            'method': 'unknown',
                            'amount': amount,
                            'reference': f'Order: {product_name}'
                        }],
                        admin_user_id=None
                    )
                    update_receivable_status(receivable['receivable_id'])
                    message += "\n\n📊 Added to your AR account for tracking."
            except Exception as ar_err:
                logger.warning(f"Could not create AR for order: {ar_err}")
                message += "\n\n⚠️ Order created (AR tracking pending)"
        
        await query.message.reply_text(message, parse_mode='Markdown')
        
        # Show next action
        await query.message.reply_text(
            "What would you like to do next?\n\n"
            "1️⃣ Contact admin for payment\n"
            "2️⃣ Continue shopping\n"
            "3️⃣ Back to menu",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 My Orders", callback_data="my_orders")],
                [InlineKeyboardButton("🛒 Continue Shopping", callback_data="cmd_browse_store")],
                [InlineKeyboardButton("📱 Main Menu", callback_data="main_menu")]
            ])
        )
        
    except Exception as e:
        logger.error(f"Error processing order: {e}")
        await query.message.reply_text(f"❌ Error: {e}")
    
    return ConversationHandler.END
