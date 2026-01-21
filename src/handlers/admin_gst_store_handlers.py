import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters
from typing import Dict
from io import BytesIO
from src.utils.gst import load_gst_config, save_gst_config, is_gst_enabled, get_gst_mode, get_gst_percent
from src.utils.store_items import add_or_update_item, load_store_items, find_items

logger = logging.getLogger(__name__)

# GST settings conversation states
GST_TOGGLE, GST_MODE, GST_PERCENT = range(3)

# Store item conversation states
ITEM_NAME, ITEM_HSN, ITEM_MRP, ITEM_GST, BULK_UPLOAD_AWAIT = range(3, 8)


async def cmd_gst_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        message = query.message
    else:
        message = update.message

    cfg = load_gst_config()
    enabled = cfg.get('enabled', False)
    mode = cfg.get('mode', 'exclusive')
    percent = cfg.get('percent', 0)

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("Toggle GST ON", callback_data="gst_toggle_on") if not enabled else InlineKeyboardButton("Toggle GST OFF", callback_data="gst_toggle_off")],
        [InlineKeyboardButton("Mode: Inclusive" if mode=='inclusive' else "Mode: Exclusive", callback_data="gst_change_mode")],
        [InlineKeyboardButton("Edit Percentage", callback_data="gst_edit_percent")],
        [InlineKeyboardButton("⬅ Back", callback_data="admin_dashboard")]
    ])

    text = f"🧾 GST Settings\n\nEnabled: {enabled}\nMode: {mode}\nPercent: {percent}%"
    await message.reply_text(text, reply_markup=kb)
    return ConversationHandler.END


async def gst_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cfg = load_gst_config()
    if query.data == 'gst_toggle_on':
        cfg['enabled'] = True
    else:
        cfg['enabled'] = False
    save_gst_config(cfg)
    await query.edit_message_text(f"✅ GST set to {cfg['enabled']}.")
    return ConversationHandler.END


async def gst_change_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cfg = load_gst_config()
    cfg['mode'] = 'inclusive' if cfg.get('mode') == 'exclusive' else 'exclusive'
    save_gst_config(cfg)
    await query.edit_message_text(f"✅ GST mode changed to {cfg['mode']}")
    return ConversationHandler.END


async def gst_edit_percent_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Enter GST percentage (0-100):")
    return GST_PERCENT


async def gst_edit_percent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        p = float(text)
        if p < 0 or p > 100:
            await update.message.reply_text("❌ GST must be between 0 and 100. Try again:")
            return GST_PERCENT
        cfg = load_gst_config()
        cfg['percent'] = p
        save_gst_config(cfg)
        await update.message.reply_text(f"✅ GST percent set to {p}%")
        return ConversationHandler.END
    except Exception:
        await update.message.reply_text("❌ Enter a valid number (e.g., 18). Try again:")
        return GST_PERCENT


# Store item flows
async def cmd_create_store_items(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        message = query.message
    else:
        message = update.message

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Create Item", callback_data="store_create_item")],
        [InlineKeyboardButton("📥 Bulk Upload", callback_data="store_bulk_upload")],
        [InlineKeyboardButton("⬅ Back", callback_data="admin_dashboard")],
    ])
    await message.reply_text("🏬 Store Items Master\n\nChoose action:", reply_markup=kb)
    return ConversationHandler.END


async def store_create_item_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    logger.info("[STORE_CREATE] entering create item flow")
    await query.edit_message_text("Enter Item Name:")
    return ITEM_NAME


async def store_item_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    logger.info(f"[STORE_CREATE] state=ITEM_NAME input={name}")
    if not name:
        await update.message.reply_text("❌ Name cannot be empty. Try again:")
        return ITEM_NAME
    context.user_data['store_item'] = {'name': name}
    await update.message.reply_text("Enter HSN Code:")
    return ITEM_HSN


async def store_item_hsn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    hsn = update.message.text.strip()
    context.user_data['store_item']['hsn'] = hsn
    await update.message.reply_text("Enter MRP:")
    return ITEM_MRP


async def store_item_mrp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        mrp = float(update.message.text.strip())
        if mrp <= 0:
            await update.message.reply_text("❌ MRP must be > 0. Try again:")
            return ITEM_MRP
        context.user_data['store_item']['mrp'] = mrp
        # default GST from global
        from src.utils.gst import get_gst_percent
        context.user_data['store_item']['gst'] = get_gst_percent()
        await update.message.reply_text(f"Enter GST % for item (default {context.user_data['store_item']['gst']}):")
        return ITEM_GST
    except Exception:
        await update.message.reply_text("❌ Enter a valid MRP (e.g., 499.00). Try again:")
        return ITEM_MRP


async def store_item_gst(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        g = float(update.message.text.strip())
        if g < 0 or g > 100:
            await update.message.reply_text("❌ GST must be 0–100. Try again:")
            return ITEM_GST
        item = context.user_data.pop('store_item')
        item['gst'] = g
        
        # Add item with serial number
        result = add_or_update_item({
            'name': item['name'],
            'hsn': item.get('hsn',''),
            'mrp': item['mrp'],
            'gst': item['gst']
        })
        
        # Get serial from result
        serial = result.get('serial', '?')
        logger.info(f"[STORE_CREATE] item_saved serial={serial} name={item['name']}")
        
        await update.message.reply_text(
            f"✅ Item created successfully\n"
            f"Serial: {serial}\n"
            f"Name: {item['name']}"
        )
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"[STORE_CREATE] error saving item: {e}")
        await update.message.reply_text("❌ Enter a valid GST (e.g., 18). Try again:")
        return ITEM_GST


# Bulk upload: send sample excel and accept file upload
async def store_bulk_upload_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    logger.info("[STORE_BULK] entering bulk upload flow")
    # generate simple sample excel
    try:
        import asyncio
        from openpyxl import Workbook
        
        # Wrap Excel generation in thread to prevent blocking
        def generate_sample_excel():
            wb = Workbook()
            ws = wb.active
            ws.append(['Item Name','HSN Code','MRP','GST %'])
            ws.append(['Sample Item','1001', '499.00', '18'])
            bio = BytesIO()
            wb.save(bio)
            bio.seek(0)
            return bio
        
        # Run in separate thread to avoid blocking
        bio = await asyncio.to_thread(generate_sample_excel)
        
        await query.message.reply_document(document=InputFile(bio, filename='store_items_sample.xlsx'))
        await query.message.reply_text('Upload filled Excel file (as attachment).')
        return BULK_UPLOAD_AWAIT  # Stay in conversation to await document
    except Exception as e:
        logger.error(f"[STORE_BULK] failed to send sample Excel: {e}")
        await query.message.reply_text('Could not generate sample Excel. Ensure openpyxl is installed.')
        return ConversationHandler.END


async def handle_uploaded_store_excel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # User uploaded a file (document)
    doc = update.message.document
    if not doc:
        await update.message.reply_text('No file found. Upload the Excel file.')
        return BULK_UPLOAD_AWAIT
    
    logger.info(f"[STORE_BULK] upload_received filename={doc.file_name}")
    
    # Send immediate feedback to admin
    await update.message.reply_text('⏳ Processing file, please wait...')
    
    file = await doc.get_file()
    bio = BytesIO()
    await file.download_to_memory(out=bio)
    bio.seek(0)
    
    try:
        import asyncio
        from openpyxl import load_workbook
        
        # Wrap Excel parsing in thread to prevent blocking
        def parse_excel(bio):
            wb = load_workbook(filename=bio, data_only=True)
            ws = wb.active
            return list(ws.iter_rows(values_only=True))
        
        # Run in separate thread
        rows = await asyncio.to_thread(parse_excel, bio)
        
        if len(rows) < 2:
            await update.message.reply_text('❌ Excel file is empty or has no data rows.')
            return ConversationHandler.END
        
        header = [str(c).strip().lower() if c else '' for c in rows[0]]
        name_i = header.index('item name') if 'item name' in header else 0
        hsn_i = header.index('hsn code') if 'hsn code' in header else 1
        mrp_i = header.index('mrp') if 'mrp' in header else 2
        gst_i = header.index('gst %') if 'gst %' in header else 3
        
        added = 0
        updated = 0
        skipped = 0
        
        for r in rows[1:]:
            try:
                name = str(r[name_i]).strip()
                hsn = str(r[hsn_i]).strip() if hsn_i < len(r) else ''
                mrp = float(r[mrp_i])
                gst = float(r[gst_i])
                
                if not name or mrp <= 0 or gst < 0 or gst > 100:
                    skipped += 1
                    continue
                
                result = add_or_update_item({'name': name, 'hsn': hsn, 'mrp': mrp, 'gst': gst})
                if result.get('is_new'):
                    added += 1
                else:
                    updated += 1
            except Exception as e:
                logger.warning(f"[STORE_BULK] skipped row: {e}")
                skipped += 1
                continue
        
        logger.info(f"[STORE_BULK] rows_processed added={added} updated={updated} skipped={skipped}")
        
        await update.message.reply_text(
            f"✅ Bulk upload completed\n"
            f"✔ Items added: {added}\n"
            f"✏ Items updated: {updated}\n"
            f"⚠ Skipped: {skipped}"
        )
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"[STORE_BULK] error parsing excel: {e}")
        await update.message.reply_text('❌ Failed to parse Excel. Ensure it is a valid .xlsx file with required columns.\n\nPlease upload a valid Excel file or type /cancel to exit.')
        return BULK_UPLOAD_AWAIT


# Store item search API used by invoice flow (DEPRECATED - DO NOT USE)
# This function should NOT be registered as a handler
# It's kept only for legacy compatibility
async def search_store_items(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    DEPRECATED: This should not be called directly.
    Use Invoice v2 store search instead.
    """
    logger.warning("[STORE_SEARCH] DEPRECATED search_store_items called - should not happen!")
    term = update.message.text.strip()
    results = find_items(term, limit=10)
    if not results:
        await update.message.reply_text('No items found. Try another name.')
        return
    for it in results:
        text = f"{it.get('name')}\nHSN: {it.get('hsn','')}\nMRP: ₹{float(it.get('mrp',0)):.2f}\nGST: {it.get('gst',0)}%"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton('Select', callback_data=f"store_select_{it.get('name')}_{it.get('hsn')}")]])
        await update.message.reply_text(text, reply_markup=kb)


async def store_item_select_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    # callback_data format: store_select_<name>_<hsn>
    parts = query.data.split('_', 2)
    if len(parts) < 3:
        await query.edit_message_text('Invalid selection')
        return
    payload = parts[2]
    # payload contains name_hsn combined; split last underscore
    # naive parse: try to find last underscore separating name and hsn
    try:
        raw = query.data[len('store_select_'):]
        # split from right
        name, hsn = raw.rsplit('_', 1)
    except Exception:
        name = raw
        hsn = ''
    # find item
    items = load_store_items()
    chosen = None
    for it in items:
        if it.get('name') == name and str(it.get('hsn','')) == hsn:
            chosen = it
            break
    if not chosen:
        await query.edit_message_text('❌ Item not found')
        return
    # Store selection in conversation context so invoice flow can pick it up
    context.user_data['invoice']['current_item'] = {
        'name': chosen.get('name'),
        'rate': float(chosen.get('mrp',0)),
        'gst': float(chosen.get('gst',0))
    }
    await query.edit_message_text(f"Item selected: {chosen.get('name')}\nRate: ₹{float(chosen.get('mrp',0)):.2f}")
    # Prompt quantity next (invoice flow expects quantity then discount)
    await context.bot.send_message(chat_id=query.from_user.id, text='🔢 Enter quantity:')
    return


async def handle_bulk_upload_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages during bulk upload (user sent text instead of file)"""
    logger.info(f"[STORE_BULK] received text instead of file: {update.message.text}")
    await update.message.reply_text(
        '❌ Please upload a valid Excel file (.xlsx) as a document attachment.\n\n'
        'Tap the 📎 (attachment) icon and select your Excel file.\n\n'
        'Or type /cancel to exit.'
    )
    return BULK_UPLOAD_AWAIT


def get_store_and_gst_handlers():
    from telegram.ext import CallbackQueryHandler
    gst_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(cmd_gst_settings, pattern='^cmd_gst_settings$')],
        states={
            GST_PERCENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, gst_edit_percent)]
        },
        fallbacks=[],
        conversation_timeout=600,  # 10 minutes timeout to prevent stuck states
        per_message=False,
        per_chat=True,  # CRITICAL: Isolate per chat for 200+ users
        per_user=True   # CRITICAL: Isolate per user for admin concurrency
    )

    store_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(cmd_create_store_items, pattern='^cmd_create_store_items$'),
            CallbackQueryHandler(store_create_item_prompt, pattern='^store_create_item$'),
            CallbackQueryHandler(store_bulk_upload_prompt, pattern='^store_bulk_upload$'),
        ],
        states={
            ITEM_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, store_item_name)],
            ITEM_HSN: [MessageHandler(filters.TEXT & ~filters.COMMAND, store_item_hsn)],
            ITEM_MRP: [MessageHandler(filters.TEXT & ~filters.COMMAND, store_item_mrp)],
            ITEM_GST: [MessageHandler(filters.TEXT & ~filters.COMMAND, store_item_gst)],
            BULK_UPLOAD_AWAIT: [
                MessageHandler(filters.Document.ALL, handle_uploaded_store_excel),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_bulk_upload_text)
            ]
        },
        fallbacks=[],
        conversation_timeout=600,  # 10 minutes timeout to prevent stuck states
        per_message=False,
        per_chat=True,  # CRITICAL: Isolate per chat for 200+ users
        per_user=True   # CRITICAL: Isolate per user for admin concurrency
    )

    return gst_conv, store_conv