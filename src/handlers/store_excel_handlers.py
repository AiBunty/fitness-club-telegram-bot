"""
Excel bulk upload for store products
Handles bulk creation, updates, and price revisions
"""

import logging
import io
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Document
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from src.database.store_operations import create_or_update_product
from src.utils.auth import is_admin_id

logger = logging.getLogger(__name__)

try:
    import openpyxl
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False
    logger.warning("openpyxl not installed - Excel upload disabled")

# Conversation states
EXCEL_UPLOAD = 1


async def cmd_store_excel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /store_excel command - Upload Excel for bulk product management
    """
    if not is_admin_id(update.effective_user.id):
        await update.message.reply_text("❌ Admin access only.")
        return ConversationHandler.END
    
    if not OPENPYXL_AVAILABLE:
        await update.message.reply_text(
            "❌ Excel support not installed.\n"
            "Install: pip install openpyxl"
        )
        return ConversationHandler.END
    
    text = (
        "📊 *Store Excel Upload*\n\n"
        "Send an Excel file with these columns:\n"
        "1. product_code (unique)\n"
        "2. category\n"
        "3. product_name\n"
        "4. description\n"
        "5. price\n"
        "6. discount_percent\n"
        "7. stock_quantity\n"
        "8. status (ACTIVE/INACTIVE)\n\n"
        "Rules:\n"
        "• product_code is unique key\n"
        "• If product_code exists → UPDATE\n"
        "• If product_code new → CREATE\n"
        "• Upload is idempotent\n\n"
        "📥 Upload your Excel file:"
    )
    
    keyboard = [[InlineKeyboardButton("📥 Download Sample", callback_data="excel_sample")]]
    
    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return EXCEL_UPLOAD


async def handle_excel_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process uploaded Excel file"""
    
    if not update.message.document:
        await update.message.reply_text("❌ Please upload a file")
        return EXCEL_UPLOAD
    
    document = update.message.document
    
    # Check file type
    if not document.file_name.endswith(('.xlsx', '.xls', '.csv')):
        await update.message.reply_text("❌ Please upload Excel file (.xlsx, .xls, .csv)")
        return EXCEL_UPLOAD
    
    admin_id = update.effective_user.id
    
    try:
        # Download file
        file = await context.bot.get_file(document.file_id)
        file_bytes = io.BytesIO()
        await file.download_to_memory(file_bytes)
        file_bytes.seek(0)
        
        # Parse Excel
        workbook = openpyxl.load_workbook(file_bytes)
        sheet = workbook.active
        
        # Expected columns
        expected_columns = {
            1: 'product_code',
            2: 'category',
            3: 'product_name',
            4: 'description',
            5: 'price',
            6: 'discount_percent',
            7: 'stock_quantity',
            8: 'status'
        }
        
        # Read header
        header_row = sheet[1]
        header_map = {}
        for col_num, col_name in expected_columns.items():
            cell = header_row[col_num - 1]
            if cell.value and cell.value.lower().strip() in [col_name, col_name.replace('_', ' '), col_name.replace('_', '-')]:
                header_map[col_num] = col_name
        
        if len(header_map) < len(expected_columns):
            await update.message.reply_text(
                "❌ Excel header mismatch.\n"
                f"Expected columns: {', '.join(expected_columns.values())}"
            )
            return EXCEL_UPLOAD
        
        # Process rows
        success_count = 0
        error_count = 0
        errors = []
        
        for row_num, row in enumerate(sheet.iter_rows(min_row=2, values_only=False), start=2):
            try:
                product_code = row[0].value
                category = row[1].value
                product_name = row[2].value
                description = row[3].value
                price = row[4].value
                discount_percent = row[5].value
                stock_quantity = row[6].value
                status = row[7].value
                
                # Validate required fields
                if not product_code or not category or not product_name or price is None:
                    errors.append(f"Row {row_num}: Missing required fields")
                    error_count += 1
                    continue
                
                # Type conversions
                try:
                    price = float(price)
                    discount_percent = float(discount_percent or 0)
                    stock_quantity = int(stock_quantity or 0)
                    status = (status or 'ACTIVE').upper()
                    
                    if status not in ['ACTIVE', 'INACTIVE']:
                        status = 'ACTIVE'
                except ValueError as e:
                    errors.append(f"Row {row_num}: Invalid data type - {str(e)}")
                    error_count += 1
                    continue
                
                # Create/update product
                result = create_or_update_product(
                    product_code=str(product_code).strip(),
                    category=str(category).strip(),
                    name=str(product_name).strip(),
                    description=str(description or "").strip(),
                    price=price,
                    discount_percent=discount_percent,
                    stock=stock_quantity,
                    status=status
                )
                
                if result:
                    success_count += 1
                else:
                    errors.append(f"Row {row_num}: Failed to upsert product")
                    error_count += 1
            
            except Exception as e:
                logger.error(f"Error processing row {row_num}: {e}")
                errors.append(f"Row {row_num}: {str(e)}")
                error_count += 1
        
        # Send summary
        summary = (
            f"📊 *Excel Upload Summary*\n\n"
            f"✅ Success: {success_count}\n"
            f"❌ Errors: {error_count}\n"
        )
        
        if errors and len(errors) <= 10:
            summary += f"\n📋 Errors:\n" + "\n".join(errors[:10])
        elif errors:
            summary += f"\n📋 First 10 errors:\n" + "\n".join(errors[:10])
            summary += f"\n... and {len(errors) - 10} more errors"
        
        await update.message.reply_text(summary, parse_mode="Markdown")
        
        logger.info(f"Excel upload by admin {admin_id}: {success_count} success, {error_count} errors")
        
        return ConversationHandler.END
    
    except Exception as e:
        logger.error(f"Error processing Excel file: {e}")
        await update.message.reply_text(f"❌ Error processing file: {str(e)}")
        return EXCEL_UPLOAD


async def excel_sample(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Download sample Excel template"""
    query = update.callback_query
    await query.answer()
    
    try:
        # Create sample workbook
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.title = "Products"
        
        # Header
        headers = ['product_code', 'category', 'product_name', 'description', 'price', 'discount_percent', 'stock_quantity', 'status']
        sheet.append(headers)
        
        # Sample data
        samples = [
            ['PROTEIN001', 'Supplements', 'Whey Protein 1kg', 'Premium whey protein powder', 1500, 10, 50, 'ACTIVE'],
            ['CREATINE001', 'Supplements', 'Creatine Monohydrate', '100% pure creatine', 800, 5, 30, 'ACTIVE'],
            ['TOWEL001', 'Accessories', 'Gym Towel', 'Microfiber gym towel', 300, 0, 100, 'ACTIVE'],
        ]
        
        for sample in samples:
            sheet.append(sample)
        
        # Save to bytes
        excel_file = io.BytesIO()
        workbook.save(excel_file)
        excel_file.seek(0)
        
        # Send file
        await query.edit_message_text("📥 Sending sample Excel template...")
        await context.bot.send_document(
            chat_id=query.from_user.id,
            document=excel_file,
            filename="store_products_sample.xlsx",
            caption="📊 Sample template for bulk product upload"
        )
        
    except Exception as e:
        logger.error(f"Error creating sample: {e}")
        await query.edit_message_text(f"❌ Error: {str(e)}")


def get_store_excel_conversation_handler():
    """Return Excel upload conversation handler"""
    return ConversationHandler(
        entry_points=[
            CommandHandler("store_excel", cmd_store_excel),
        ],
        states={
            EXCEL_UPLOAD: [
                MessageHandler(filters.Document.ALL, handle_excel_file),
                CallbackQueryHandler(excel_sample, pattern="^excel_sample$"),
            ],
        },
        fallbacks=[]
    )
