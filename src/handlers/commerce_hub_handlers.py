"""
Commerce Hub Admin Handlers
Manages subscription plans, PT subscriptions, one-day events, and store products
Includes audit logging for all admin operations
"""

import logging
import json
from datetime import datetime, date
from io import BytesIO
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler
import openpyxl

from src.database.connection import execute_query
from src.database.store_items_operations import add_or_update_item_in_db
from src.database.ar_operations import create_receivable, create_transactions, update_receivable_status
from src.utils.excel_templates import generate_store_product_template, generate_subscription_plan_template
from src.utils.auth import is_admin_id
from src.utils.role_notifications import get_moderator_chat_ids
from src.database.user_operations import get_user

logger = logging.getLogger(__name__)

# Conversation states
MANAGE_MENU, CREATE_PLAN, EDIT_PLAN, DELETE_PLAN, UPLOAD_PRODUCTS = range(5)


# ============ Audit Logging Helpers ============

def log_audit(admin_id: int, entity_type: str, entity_id: int = None, action: str = "create", 
              old_value: dict = None, new_value: dict = None):
    """Log admin action to audit log"""
    try:
        query = """
            INSERT INTO admin_audit_log (admin_id, entity_type, entity_id, action, old_value, new_value)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        execute_query(
            query,
            (admin_id, entity_type, entity_id, action, 
             json.dumps(old_value) if old_value else None, 
             json.dumps(new_value) if new_value else None)
        )
        logger.info(f"Audit logged: {entity_type} {action} by admin {admin_id}")
    except Exception as e:
        logger.error(f"Failed to log audit: {e}")


# ============ Subscription Plan Management ============

async def cmd_manage_subscriptions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: Manage subscription plans"""
    if not is_admin_id(update.effective_user.id):
        await update.message.reply_text("❌ Admin access only.")
        return ConversationHandler.END
    
    keyboard = [
        [InlineKeyboardButton("➕ Create Plan", callback_data="sub_create")],
        [InlineKeyboardButton("📋 List Plans", callback_data="sub_list")],
        [InlineKeyboardButton("✏️ Edit Plan", callback_data="sub_edit")],
        [InlineKeyboardButton("🗑️ Delete Plan", callback_data="sub_delete")],
        [InlineKeyboardButton("⬅️ Back", callback_data="main_menu")],
    ]
    
    await update.message.reply_text(
        "📅 *Manage Subscription Plans*\n\nSelect an option:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    return MANAGE_MENU


async def list_subscription_plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all subscription plans"""
    try:
        plans = execute_query("SELECT * FROM subscription_plans ORDER BY created_at DESC")
        
        if not plans:
            await update.callback_query.message.reply_text("No subscription plans found.")
            return
        
        text = "📅 *Active Subscription Plans:*\n\n"
        for plan in plans:
            status_icon = "✅" if plan['status'] == 'active' else "⏸️"
            ar_icon = "📊" if plan['ar_enabled'] else "❌"
            text += (
                f"{status_icon} **{plan['name']}**\n"
                f"  Duration: {plan['duration_days']} days\n"
                f"  Price: Rs {plan['price']}\n"
                f"  AR Enabled: {ar_icon}\n"
                f"  Created: {plan['created_at'].strftime('%d-%m-%Y')}\n\n"
            )
        
        await update.callback_query.message.reply_text(text, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Failed to list plans: {e}")
        await update.callback_query.message.reply_text(f"❌ Error: {e}")


async def cmd_create_subscription_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create new subscription plan"""
    if not is_admin_id(update.effective_user.id):
        await update.message.reply_text("❌ Admin access only.")
        return ConversationHandler.END
    
    await update.message.reply_text(
        "📅 *Create Subscription Plan*\n\n"
        "Send plan details in this format:\n"
        "`PlanName | 30 | 3000 | Description`\n\n"
        "Format: Name | Duration(days) | Price(Rs) | Description",
        parse_mode='Markdown',
        reply_markup=ReplyKeyboardRemove()
    )
    return CREATE_PLAN


async def process_create_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process subscription plan creation"""
    try:
        parts = update.message.text.split('|')
        if len(parts) < 3:
            await update.message.reply_text("❌ Invalid format. Use: Name | Days | Price | Description")
            return CREATE_PLAN
        
        name = parts[0].strip()
        duration_days = int(parts[1].strip())
        price = float(parts[2].strip())
        description = parts[3].strip() if len(parts) > 3 else ""
        
        admin_id = update.effective_user.id
        
        query = """
            INSERT INTO subscription_plans (name, duration_days, price, description, created_by)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING plan_id, name, price
        """
        result = execute_query(query, (name, duration_days, price, description, admin_id), fetch_one=True)
        
        if result:
            # Log audit
            log_audit(admin_id, 'subscription_plan', result['plan_id'], 'create',
                      new_value={'name': name, 'duration': duration_days, 'price': price})
            
            await update.message.reply_text(
                f"✅ *Subscription Plan Created!*\n\n"
                f"📅 **{result['name']}**\n"
                f"💵 Rs {result['price']}\n"
                f"⏱️ {duration_days} days",
                parse_mode='Markdown'
            )
            
            # Notify all admins
            await notify_admins(
                context,
                f"📅 New subscription plan: {name} (Rs {price}/month)",
                admin_id
            )
        else:
            await update.message.reply_text("❌ Failed to create plan.")
    except Exception as e:
        logger.error(f"Error creating plan: {e}")
        await update.message.reply_text(f"❌ Error: {e}")
    
    return ConversationHandler.END


# ============ Store Products Management ============

async def cmd_manage_store(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: Manage store products"""
    if not is_admin_id(update.effective_user.id):
        await update.message.reply_text("❌ Admin access only.")
        return ConversationHandler.END
    
    keyboard = [
        [InlineKeyboardButton("📥 Download Sample Excel", callback_data="store_download_template")],
        [InlineKeyboardButton("📤 Bulk Upload Products", callback_data="store_bulk_upload")],
        [InlineKeyboardButton("📋 List Products", callback_data="store_list")],
        [InlineKeyboardButton("⬅️ Back", callback_data="main_menu")],
    ]
    
    await update.message.reply_text(
        "🛒 *Manage Store Products*\n\n"
        "Download the sample Excel template, fill in your products, then upload.",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    return MANAGE_MENU


async def download_store_template(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send sample Excel template for store products"""
    try:
        query = update.callback_query
        await query.answer()
        
        template_file = generate_store_product_template()
        if template_file:
            await query.message.reply_document(
                document=template_file,
                filename=f"Store_Items_Template_{date.today()}.xlsx",
                caption="📥 *Store Items Template*\n\n"
                    "Fill in your items and upload via 'Bulk Upload Products'.\n\n"
                    "Columns:\n"
                    "• Item Name\n"
                    "• HSN\n"
                    "• MRP (Maximum Retail Price)\n"
                    "• GST %",
                parse_mode='Markdown'
            )
        else:
            await query.message.reply_text("❌ Failed to generate template.")
    except Exception as e:
        logger.error(f"Error downloading template: {e}")
        await query.message.reply_text(f"❌ Error: {e}")


async def cmd_bulk_upload_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle bulk upload of store products"""
    if not is_admin_id(update.effective_user.id):
        await update.message.reply_text("❌ Admin access only.")
        return ConversationHandler.END
    
    await update.message.reply_text(
        "📤 *Bulk Upload Store Products*\n\n"
        "Send the filled Excel file (.xlsx) with products.",
        parse_mode='Markdown',
        reply_markup=ReplyKeyboardRemove()
    )
    return UPLOAD_PRODUCTS


async def process_product_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process uploaded Excel file with store products"""
    try:
        admin_id = update.effective_user.id
        
        # Download file
        file = await update.message.document.get_file()
        file_bytes = await file.download_as_bytearray()
        
        # Parse Excel
        wb = openpyxl.load_workbook(BytesIO(file_bytes))
        ws = wb.active
        
        # Skip header row, read data rows
        products_data = []
        rows_count = 0
        
        for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            if not row[0]:  # Skip empty rows
                continue
            
            name, hsn, mrp, gst_percent = row[:4]
            
            if not name or not hsn or not mrp:
                await update.message.reply_text(f"❌ Row {row_idx}: Missing Item Name, HSN or MRP")
                return UPLOAD_PRODUCTS
            
            # Validate numeric values
            try:
                mrp = float(mrp)
                gst_percent = float(gst_percent or 18)
            except ValueError:
                await update.message.reply_text(
                    f"❌ Row {row_idx}: MRP and GST must be numeric"
                )
                return UPLOAD_PRODUCTS
            
            products_data.append({
                'name': str(name).strip(),
                'hsn': str(hsn).strip(),
                'mrp': mrp,
                'gst': gst_percent
            })
            rows_count += 1
        
        if not products_data:
            await update.message.reply_text("❌ No valid products found in Excel.")
            return UPLOAD_PRODUCTS
        
        # Insert all products
        inserted = 0
        for product in products_data:
            try:
                result = add_or_update_item_in_db(product)
                if result:
                    inserted += 1
            except Exception as e:
                logger.warning(f"Failed to insert product {product['name']}: {e}")
        
        # Log bulk audit entry
        log_audit(admin_id, 'store_items', None, 'bulk_upload',
                  old_value=None,
                  new_value={'count': inserted, 'products': [p['name'] for p in products_data[:5]]})
        
        await update.message.reply_text(
            f"✅ *Bulk Upload Complete!*\n\n"
            f"📦 Items Uploaded: {inserted}/{rows_count}\n\n"
            f"Store items are now available for invoices and store browsing.",
            parse_mode='Markdown'
        )
        
        # Notify admins
        await notify_admins(
            context,
            f"🛒 Bulk upload: {inserted} store items added",
            admin_id
        )
        
    except Exception as e:
        logger.error(f"Error processing upload: {e}")
        await update.message.reply_text(f"❌ Error: {e}")
    
    return ConversationHandler.END


# ============ PT Subscriptions Management ============

async def cmd_manage_pt_plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: Manage PT subscription plans"""
    if not is_admin_id(update.effective_user.id):
        await update.message.reply_text("❌ Admin access only.")
        return ConversationHandler.END
    
    keyboard = [
        [InlineKeyboardButton("➕ Create PT Plan", callback_data="pt_create")],
        [InlineKeyboardButton("📋 List PT Plans", callback_data="pt_list")],
        [InlineKeyboardButton("✏️ Edit PT Plan", callback_data="pt_edit")],
        [InlineKeyboardButton("⬅️ Back", callback_data="main_menu")],
    ]
    
    await update.message.reply_text(
        "💪 *Manage Personal Training Plans*\n\nSelect an option:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    return MANAGE_MENU


# ============ One-Day Events Management ============

async def cmd_manage_events(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: Manage one-day events"""
    if not is_admin_id(update.effective_user.id):
        await update.message.reply_text("❌ Admin access only.")
        return ConversationHandler.END
    
    keyboard = [
        [InlineKeyboardButton("➕ Create Event", callback_data="event_create")],
        [InlineKeyboardButton("📋 List Events", callback_data="event_list")],
        [InlineKeyboardButton("✏️ Edit Event", callback_data="event_edit")],
        [InlineKeyboardButton("⬅️ Back", callback_data="main_menu")],
    ]
    
    await update.message.reply_text(
        "🎉 *Manage One-Day Events*\n\nSelect an option:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    return MANAGE_MENU


# ============ Helper Functions ============

async def notify_admins(context: ContextTypes.DEFAULT_TYPE, message: str, excludes_admin_id: int = None):
    """Send notification to all admins"""
    try:
        admin_ids = get_moderator_chat_ids(include_staff=False)
        for admin_id in admin_ids:
            if admin_id != excludes_admin_id:
                try:
                    await context.bot.send_message(chat_id=admin_id, text=message, parse_mode='Markdown')
                except Exception as e:
                    logger.debug(f"Could not notify admin {admin_id}: {e}")
    except Exception as e:
        logger.error(f"Error notifying admins: {e}")


# ============ Callback Router Additions ============

async def handle_commerce_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Route commerce hub callbacks"""
    query = update.callback_query
    
    if query.data == "store_download_template":
        await download_store_template(update, context)
    elif query.data == "store_list":
        await list_store_items(update, context)
    elif query.data == "sub_list":
        await list_subscription_plans(update, context)


async def list_store_items(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all store items"""
    try:
        products = execute_query(
            "SELECT serial, name, hsn, mrp, gst FROM store_items ORDER BY name"
        )
        
        if not products:
            await update.callback_query.message.reply_text("No products found.")
            return
        
        text = "🛒 *Active Store Items:*\n\n"
        for product in products:
            text += (
                f"  • {product['name']}\n"
                f"    HSN: {product['hsn']} | MRP: Rs {product['mrp']} | GST: {product['gst']}%\n"
            )
        
        await update.callback_query.message.reply_text(text, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Failed to list products: {e}")
        await update.callback_query.message.reply_text(f"❌ Error: {e}")

async def cmd_user_store(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User: View store products"""
    # Require full access (registered + active subscription)
    try:
        from src.utils.access_gate import check_app_feature_access
        if not await check_app_feature_access(update, context):
            return ConversationHandler.END
    except Exception:
        # Fail safe: if gate fails unexpectedly, block and inform user
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.message.reply_text("❌ Access check failed. Try again later.")
        else:
            await update.message.reply_text("❌ Access check failed. Try again later.")
        return ConversationHandler.END
    # Handle both command and callback contexts
    if update.callback_query:
        await update.callback_query.answer()
        message = update.callback_query.message
    else:
        message = update.message
    
    try:
        products = execute_query(
            "SELECT serial, name, hsn, mrp, gst FROM store_items ORDER BY name"
        )
        
        if not products:
            await message.reply_text("🛒 *Store*\n\nNo products available at the moment. Check back soon!", parse_mode='Markdown')
            return
        
        text = "🛒 *Store Items*\n\n"
        for product in products:
            text += (
                f"• *{product['name']}*\n"
                f"  HSN: {product['hsn']}\n"
                f"  MRP: Rs {product['mrp']} | GST: {product['gst']}%\n\n"
            )
        
        text += "\n💬 Contact admin to purchase products."
        
        await message.reply_text(text, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Failed to load store for user: {e}")
        await message.reply_text("❌ Failed to load store. Please try again later.")