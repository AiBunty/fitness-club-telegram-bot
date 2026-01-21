# 🏬 Create Store Item Flow Documentation

## Overview
The Create Store Item flow allows admins to add products to the store catalog with GST (tax) configuration. Items can be added individually or via bulk Excel upload.

---

## Entry Points

### 1. Admin Dashboard
- Admin clicks **"🏬 Store Items"** button
- Bot shows Store Items Master menu
- Handler: `cmd_create_store_items` in [admin_gst_store_handlers.py](src/handlers/admin_gst_store_handlers.py#L91)

### 2. Callback Query
- Callback pattern: `^cmd_create_store_items$`
- Direct access from admin dashboard

---

## Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                  ADMIN DASHBOARD                            │
│         Clicks "🏬 Store Items" button                      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              🏬 Store Items Master                          │
│                                                             │
│  ┌──────────────────────────────────────────────────┐      │
│  │  [➕ Create Item]  ← Manual single item entry    │      │
│  │  [📥 Bulk Upload]  ← Upload Excel file           │      │
│  │  [⬅ Back]          ← Return to dashboard         │      │
│  └──────────────────────────────────────────────────┘      │
└─────────────┬───────────────────────┬───────────────────────┘
              │                       │
       [Create Item]          [Bulk Upload]
              │                       │
              ▼                       ▼
┌─────────────────────────┐  ┌─────────────────────────────┐
│   SINGLE ITEM FLOW      │  │    BULK UPLOAD FLOW         │
└─────────────────────────┘  └─────────────────────────────┘
```

---

## 🔹 Single Item Creation Flow

### State Machine: ConversationHandler

```
START
  │
  ▼
┌─────────────────────────────────────────────────────────────┐
│ STATE: ITEM_NAME                                            │
│ Bot: "Enter Item Name:"                                     │
│ User: Types item name (e.g., "Protein Shake")              │
│ Handler: store_item_name()                                  │
│ Validation: Name cannot be empty                            │
└────────────────────┬────────────────────────────────────────┘
                     │ ✅ Valid name
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ STATE: ITEM_HSN                                             │
│ Bot: "Enter HSN Code:"                                      │
│ User: Types HSN code (e.g., "1001")                         │
│ Handler: store_item_hsn()                                   │
│ Validation: None (optional field)                           │
└────────────────────┬────────────────────────────────────────┘
                     │ ✅ HSN captured
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ STATE: ITEM_MRP                                             │
│ Bot: "Enter MRP:"                                           │
│ User: Types price (e.g., "499.00")                          │
│ Handler: store_item_mrp()                                   │
│ Validation: Must be numeric > 0                             │
│ Error: "❌ MRP must be > 0. Try again:"                    │
└────────────────────┬────────────────────────────────────────┘
                     │ ✅ Valid MRP
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ STATE: ITEM_GST                                             │
│ Bot: "Enter GST % for item (default 18):"                   │
│ User: Types GST percentage (e.g., "18")                     │
│ Handler: store_item_gst()                                   │
│ Validation: Must be 0-100                                   │
│ Error: "❌ GST must be 0–100. Try again:"                  │
└────────────────────┬────────────────────────────────────────┘
                     │ ✅ Valid GST
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ SAVE TO STORE                                               │
│ Function: add_or_update_item()                              │
│ File: src/utils/store_items.py                              │
│                                                             │
│ Data Saved:                                                 │
│   - Serial Number (auto-generated)                          │
│   - Name: "Protein Shake"                                   │
│   - HSN: "1001"                                             │
│   - MRP: 499.00                                             │
│   - GST: 18%                                                │
└────────────────────┬────────────────────────────────────────┘
                     │ ✅ Item saved
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ SUCCESS MESSAGE                                             │
│                                                             │
│ ✅ Item created successfully                                │
│ Serial: 001                                                 │
│ Name: Protein Shake                                         │
└─────────────────────────────────────────────────────────────┘
  │
  ▼
END (ConversationHandler.END)
```

---

## 🔹 Bulk Upload Flow

```
START
  │
  ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 1: Generate Sample Excel                               │
│ Handler: store_bulk_upload_prompt()                         │
│                                                             │
│ Bot generates Excel with format:                            │
│ ┌──────────────┬──────────┬────────┬───────┐              │
│ │ Item Name    │ HSN Code │ MRP    │ GST % │              │
│ ├──────────────┼──────────┼────────┼───────┤              │
│ │ Sample Item  │ 1001     │ 499.00 │ 18    │              │
│ └──────────────┴──────────┴────────┴───────┘              │
│                                                             │
│ Bot sends: store_items_sample.xlsx                          │
│ Bot: "Upload filled Excel file (as attachment)."            │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ STATE: BULK_UPLOAD_AWAIT                                    │
│ User: Uploads filled Excel file as document                 │
│ Handler: handle_uploaded_store_excel()                      │
└────────────────────┬────────────────────────────────────────┘
                     │ 📄 Document received
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 2: Parse Excel                                         │
│                                                             │
│ 1. Download file to memory (BytesIO)                        │
│ 2. Load workbook with openpyxl                              │
│ 3. Read header row (row 0)                                  │
│ 4. Identify columns:                                        │
│    - name_i = index of "Item Name"                          │
│    - hsn_i = index of "HSN Code"                            │
│    - mrp_i = index of "MRP"                                 │
│    - gst_i = index of "GST %"                               │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 3: Process Each Row (rows 1+)                          │
│                                                             │
│ For each row:                                               │
│   ├─ Extract: name, hsn, mrp, gst                           │
│   ├─ Validate:                                              │
│   │   • name not empty                                      │
│   │   • mrp > 0                                             │
│   │   • 0 ≤ gst ≤ 100                                       │
│   │                                                         │
│   ├─ Valid? → Call add_or_update_item()                     │
│   │   ├─ New item? → added += 1                             │
│   │   └─ Existing? → updated += 1                           │
│   │                                                         │
│   └─ Invalid? → skipped += 1                                │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 4: Report Results                                      │
│                                                             │
│ ✅ Bulk upload completed                                    │
│ ✔ Items added: 15                                           │
│ ✏ Items updated: 3                                          │
│ ⚠ Skipped: 2                                                │
└─────────────────────────────────────────────────────────────┘
  │
  ▼
END (ConversationHandler.END)
```

---

## Code Structure

### Conversation States
```python
# Defined in admin_gst_store_handlers.py
ITEM_NAME = 3        # Waiting for item name input
ITEM_HSN = 4         # Waiting for HSN code input
ITEM_MRP = 5         # Waiting for MRP (price) input
ITEM_GST = 6         # Waiting for GST percentage input
BULK_UPLOAD_AWAIT = 7  # Waiting for Excel file upload
```

### Key Handlers

| Handler | Purpose | State Transition |
|---------|---------|------------------|
| `cmd_create_store_items` | Entry point, shows menu | None → END |
| `store_create_item_prompt` | Start single item flow | None → ITEM_NAME |
| `store_item_name` | Capture item name | ITEM_NAME → ITEM_HSN |
| `store_item_hsn` | Capture HSN code | ITEM_HSN → ITEM_MRP |
| `store_item_mrp` | Capture MRP price | ITEM_MRP → ITEM_GST |
| `store_item_gst` | Capture GST %, save item | ITEM_GST → END |
| `store_bulk_upload_prompt` | Send sample Excel | None → BULK_UPLOAD_AWAIT |
| `handle_uploaded_store_excel` | Process bulk upload | BULK_UPLOAD_AWAIT → END |

### Data Storage

**Function**: `add_or_update_item(item_dict)`
**Location**: [src/utils/store_items.py](src/utils/store_items.py)

**Item Structure**:
```python
{
    'serial': '001',           # Auto-generated serial number
    'name': 'Protein Shake',   # Item name
    'hsn': '1001',             # HSN tax code
    'mrp': 499.00,             # Maximum Retail Price
    'gst': 18.0                # GST percentage
}
```

**Storage**: JSON file (location in store_items.py)

---

## Validation Rules

### Item Name (ITEM_NAME)
- ✅ Required field
- ❌ Cannot be empty string
- 🔄 Retry on failure

### HSN Code (ITEM_HSN)
- ✅ Optional field
- 📝 Stored as string
- 🔄 No retry (accepts any input)

### MRP (ITEM_MRP)
- ✅ Required field
- 📊 Must be numeric (float)
- 📈 Must be > 0
- ❌ Error: "❌ MRP must be > 0. Try again:"
- 🔄 Retry on failure

### GST Percentage (ITEM_GST)
- ✅ Required field
- 📊 Must be numeric (float)
- 📉 Range: 0 to 100
- ❌ Error: "❌ GST must be 0–100. Try again:"
- 🔄 Retry on failure
- 🔧 Default: Uses global GST config (from `get_gst_percent()`)

---

## Bulk Upload Excel Format

### Required Columns (Case-insensitive):

| Column Name | Type | Required | Validation |
|-------------|------|----------|------------|
| Item Name | Text | ✅ Yes | Not empty |
| HSN Code | Text | ❌ No | Any string |
| MRP | Number | ✅ Yes | > 0 |
| GST % | Number | ✅ Yes | 0-100 |

### Sample Excel Content:
```
┌──────────────────┬──────────┬────────┬───────┐
│ Item Name        │ HSN Code │ MRP    │ GST % │
├──────────────────┼──────────┼────────┼───────┤
│ Protein Shake    │ 1001     │ 499.00 │ 18    │
│ Energy Bar       │ 1002     │ 50.00  │ 12    │
│ Gym Gloves       │ 2001     │ 299.00 │ 18    │
│ Shaker Bottle    │ 2002     │ 199.00 │ 18    │
└──────────────────┴──────────┴────────┴───────┘
```

### Processing Logic:
1. Skip header row (row 0)
2. Process data rows (row 1+)
3. For each row:
   - Extract values by column index
   - Validate all fields
   - Call `add_or_update_item()`
   - Track: added / updated / skipped
4. Report statistics

---

## Error Handling

### Single Item Creation
```python
try:
    # Parse user input
    mrp = float(update.message.text.strip())
    if mrp <= 0:
        # Validation failed - retry
        await update.message.reply_text("❌ MRP must be > 0. Try again:")
        return ITEM_MRP  # Stay in same state
    # Validation passed - continue
    context.user_data['store_item']['mrp'] = mrp
    return ITEM_GST  # Move to next state
except Exception:
    # Parse error - retry
    await update.message.reply_text("❌ Enter a valid MRP (e.g., 499.00). Try again:")
    return ITEM_MRP
```

### Bulk Upload
```python
try:
    # Process row
    result = add_or_update_item(item_data)
    if result.get('is_new'):
        added += 1
    else:
        updated += 1
except Exception as e:
    # Row failed - log and skip
    logger.warning(f"[STORE_BULK] skipped row: {e}")
    skipped += 1
    continue  # Don't fail entire upload
```

---

## Integration with Invoice System

### Invoice v2 Integration
Items created via this flow are available in the invoice creation system:

1. Admin creates invoice
2. Selects "🔍 Search Store Items"
3. Bot queries store catalog using `find_items(term, limit=10)`
4. Results show items with:
   - Name
   - HSN Code
   - MRP (as rate)
   - GST percentage

**Note**: The `search_store_items()` function in this file is **DEPRECATED**. Invoice v2 uses its own store search mechanism.

---

## ConversationHandler Registration

```python
def get_store_and_gst_handlers():
    """Returns GST and Store conversation handlers"""
    
    store_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(cmd_create_store_items, 
                               pattern='^cmd_create_store_items$'),
            CallbackQueryHandler(store_create_item_prompt, 
                               pattern='^store_create_item$'),
            CallbackQueryHandler(store_bulk_upload_prompt, 
                               pattern='^store_bulk_upload$'),
        ],
        states={
            ITEM_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, 
                             store_item_name)
            ],
            ITEM_HSN: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, 
                             store_item_hsn)
            ],
            ITEM_MRP: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, 
                             store_item_mrp)
            ],
            ITEM_GST: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, 
                             store_item_gst)
            ],
            BULK_UPLOAD_AWAIT: [
                MessageHandler(filters.Document.ALL, 
                             handle_uploaded_store_excel)
            ]
        },
        fallbacks=[],
        per_message=False
    )
    
    return gst_conv, store_conv
```

---

## Testing

### Manual Test: Single Item Creation
1. Login as admin
2. Open Admin Dashboard
3. Click "🏬 Store Items"
4. Click "➕ Create Item"
5. Enter:
   - Name: "Test Protein"
   - HSN: "1001"
   - MRP: "599"
   - GST: "18"
6. Verify success message with serial number

### Manual Test: Bulk Upload
1. Click "📥 Bulk Upload"
2. Download sample Excel
3. Fill with 5-10 items
4. Upload filled Excel
5. Verify results: added/updated/skipped counts

### Edge Cases
- ✅ Empty name → Retry
- ✅ Negative MRP → Retry
- ✅ GST > 100 → Retry
- ✅ Invalid Excel format → Error message
- ✅ Duplicate items → Updates existing (not error)

---

## Logging

All handlers log actions with `[STORE_CREATE]` or `[STORE_BULK]` prefix:

```python
logger.info("[STORE_CREATE] entering create item flow")
logger.info(f"[STORE_CREATE] state=ITEM_NAME input={name}")
logger.info(f"[STORE_CREATE] item_saved serial={serial} name={item['name']}")
logger.info(f"[STORE_BULK] rows_processed added={added} updated={updated} skipped={skipped}")
```

---

## Summary

**Entry**: Admin Dashboard → Store Items → Create Item / Bulk Upload
**States**: ITEM_NAME → ITEM_HSN → ITEM_MRP → ITEM_GST → END
**Storage**: JSON file via `add_or_update_item()`
**Features**:
- ✅ Step-by-step guided input
- ✅ Validation at each step
- ✅ Bulk upload with Excel
- ✅ Auto-generated serial numbers
- ✅ Duplicate detection (update vs add)
- ✅ GST configuration support

**Used By**: Invoice v2 system for product catalog
