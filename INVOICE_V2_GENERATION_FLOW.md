# 🧾 Invoice v2 Generation Flow

## 📊 Complete Step-by-Step Flow

### Overview
Invoice v2 is a comprehensive conversation-based invoice generation system that allows admins to create detailed invoices for users with store items or custom items, including GST calculation, discounts, and automatic PDF generation.

---

## 🔄 Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         INVOICE v2 FLOW                             │
└─────────────────────────────────────────────────────────────────────┘

┌───────────────┐
│  ENTRY POINT  │
│ Admin Panel   │  Admin clicks "🧾 Invoices"
│  Button       │  → cmd_invoices_v2()
└───────┬───────┘
        │  [Clear previous state]
        │  [Initialize invoice_v2_data]
        ▼
┌──────────────────────────────────────────────────────────────────┐
│  STATE 1: SEARCH_USER                                            │
│  ─────────────────────                                           │
│  Admin enters: Name / Username / Telegram ID                     │
│  → handle_user_search()                                          │
│  → Calls search_users() with fuzzy ILIKE matching               │
│                                                                  │
│  Results Display:                                                │
│  ┌──────────────────────────────────────────────────────┐       │
│  │ Found 3 user(s):                                     │       │
│  │ 1. Sayali (@sayali_fit) - ID: 123456 ✅ Approved    │       │
│  │ 2. Sayansh (@sayansh) - ID: 789012 ⏳ Pending       │       │
│  │ 3. Say Kumar - ID: 345678 ✅ Approved                │       │
│  │                                                      │       │
│  │ [1. Sayali (@sayali_fit) - ID: 123456]  ← Button    │       │
│  │ [2. Sayansh (@sayansh) - ID: 789012]    ← Button    │       │
│  │ [3. Say Kumar - ID: 345678]             ← Button    │       │
│  │ [❌ Cancel]                             ← Button    │       │
│  └──────────────────────────────────────────────────────┘       │
└──────────────────────────────┬───────────────────────────────────┘
                               │ Admin clicks user
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│  STATE 2: SELECT_USER                                            │
│  ──────────────────────                                          │
│  → handle_user_select()                                          │
│  → Saves selected_user to context.user_data                      │
│                                                                  │
│  ✅ Selected: Sayali (@sayali_fit) - ID: 123456                 │
│  Now, add items to invoice:                                      │
│                                                                  │
│  [🔍 Search Store Item]                                          │
│  [✍️ Add Custom Item]                                            │
│  [❌ Cancel Invoice]                                             │
└──────────────────────────────┬───────────────────────────────────┘
                               │
                   ┌───────────┴───────────┐
                   │                       │
         PATH A: Store Item      PATH B: Custom Item
                   │                       │
                   ▼                       ▼
┌──────────────────────────────┐  ┌──────────────────────────────┐
│ STATE 3a: SEARCH_STORE_ITEM  │  │ STATE 3b: CUSTOM_ITEM_NAME   │
│ ──────────────────────────── │  │ ──────────────────────────── │
│ Admin enters: Name / Serial   │  │ Admin enters: Item name      │
│ → handle_store_search()       │  │ → handle_custom_name()       │
│                              │  │                              │
│ Found 2 item(s):             │  │ ✍️ Enter item name:          │
│ 1. [#1001] Protein Shake |   │  │ → "Consultation Fee"         │
│    ₹499 (GST 18%)           │  │                              │
│ 2. [#1002] Whey Protein |    │  └──────────┬───────────────────┘
│    ₹2499 (GST 18%)          │             │
│                              │             ▼
│ [#1001 - Protein Shake]      │  ┌──────────────────────────────┐
│ [#1002 - Whey Protein]       │  │ STATE 4b: CUSTOM_ITEM_RATE   │
│ [❌ Cancel]                  │  │ ──────────────────────────── │
└──────────┬───────────────────┘  │ Admin enters: Rate amount    │
           │                      │ → handle_custom_rate()       │
           ▼                      │                              │
┌──────────────────────────────┐  │ 💰 Enter item Rate (₹):      │
│ STATE 4a: SELECT_STORE_ITEM  │  │ → "500"                      │
│ ──────────────────────────── │  │ → Auto-applies global GST    │
│ → handle_store_select()      │  └──────────┬───────────────────┘
│ → Auto-fills item data       │             │
│ → Serial, Name, MRP, GST%    │             │
└──────────┬───────────────────┘             │
           │                                 │
           └─────────────┬───────────────────┘
                         │ Both paths merge
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│  STATE 5: ITEM_QUANTITY                                          │
│  ────────────────────                                            │
│  → handle_item_quantity()                                        │
│                                                                  │
│  📦 Item: Protein Shake                                          │
│  Rate: ₹499                                                      │
│  Enter Quantity:                                                 │
│  → "2"                                                           │
└──────────────────────────────┬───────────────────────────────────┘
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│  STATE 6: ITEM_DISCOUNT                                          │
│  ─────────────────────                                           │
│  → handle_item_discount()                                        │
│                                                                  │
│  🏷️ Enter Discount % (0-80):                                     │
│  → "10"                                                          │
│                                                                  │
│  Calculations:                                                   │
│  ─────────────────────────────────────────────────────────────  │
│  Base = Rate × Qty = 499 × 2 = ₹998                            │
│  Discount = Base × 10% = ₹99.80                                │
│  Taxable = Base - Discount = ₹898.20                           │
│  GST Amount = Taxable × 18% ÷ 100 = ₹161.68                    │
│  Line Total = Taxable + GST = ₹1,059.88                        │
└──────────────────────────────┬───────────────────────────────────┘
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│  STATE 7: ITEM_CONFIRM                                           │
│  ────────────────────                                            │
│  → handle_item_confirm()                                         │
│                                                                  │
│  ✅ Item Summary:                                                │
│  ━━━━━━━━━━━━━━━━                                                │
│  Name: Protein Shake                                             │
│  Rate: ₹499                                                      │
│  Qty: 2                                                          │
│  Discount: 10%                                                   │
│  Taxable: ₹898.20                                               │
│  GST: ₹161.68                                                   │
│  Line Total: ₹1,059.88                                          │
│  ━━━━━━━━━━━━━━━━                                                │
│                                                                  │
│  Add more items?                                                 │
│  [➕ Add Another Item] → Back to STATE 3 (ITEM_MODE)            │
│  [➡️ Finish Items]     → Continue to STATE 8                     │
│  [❌ Cancel Invoice]                                             │
└──────────────────────────────┬───────────────────────────────────┘
                               │ Admin clicks "Finish Items"
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│  STATE 8: SHIPPING                                               │
│  ───────────────────                                             │
│  → handle_shipping()                                             │
│                                                                  │
│  🚚 Enter Shipping/Delivery Charge (₹, or 0):                    │
│  → "50"                                                          │
│                                                                  │
│  Total Calculations:                                             │
│  ─────────────────────────────────────────────────────────────  │
│  Items Subtotal = Sum of all line_totals = ₹1,059.88           │
│  Shipping = ₹50.00                                              │
│  GST Total = Sum of all GST amounts = ₹161.68                  │
│  Final Total = Items Subtotal + Shipping = ₹1,109.88           │
└──────────────────────────────┬───────────────────────────────────┘
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│  STATE 9: FINAL_REVIEW                                           │
│  ────────────────────                                            │
│  Shows complete invoice preview                                  │
│                                                                  │
│  📋 Final Invoice Summary                                        │
│  ━━━━━━━━━━━━━━━━                                                │
│  User: Sayali (@sayali_fit) - ID: 123456                        │
│                                                                  │
│  Items:                                                          │
│  1. Protein Shake x2 = ₹1,059.88                                │
│                                                                  │
│  Subtotal: ₹1,059.88                                            │
│  Shipping: ₹50.00                                               │
│  GST Total: ₹161.68                                             │
│  Final Total: ₹1,109.88                                         │
│                                                                  │
│  [📤 Send Invoice]                                               │
│  [❌ Cancel]                                                     │
└──────────────────────────────┬───────────────────────────────────┘
                               │ Admin clicks "Send Invoice"
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│  STATE 10: SEND_INVOICE                                          │
│  ─────────────────────                                           │
│  → handle_send_invoice()                                         │
│                                                                  │
│  1. Generate Invoice ID (UUID): "A7B9C2D4"                       │
│  2. Save to data/invoices_v2.json                                │
│  3. Generate PDF using reportlab                                 │
│     └─ generate_invoice_pdf()                                    │
│        ├─ Header with Invoice ID & Date                          │
│        ├─ User details section                                   │
│        ├─ Items table with GST breakdown                         │
│        ├─ Totals section                                         │
│        └─ Payment buttons embedded                               │
│  4. Send PDF to user via Telegram                                │
│     └─ With action buttons:                                      │
│        [💳 Pay Bill] [❌ Reject Bill]                            │
│  5. Notify admin of success                                      │
│                                                                  │
│  ✅ Admin sees:                                                  │
│  "✅ Invoice A7B9C2D4 sent to Sayali (@sayali_fit)"             │
│                                                                  │
│  ✅ User receives:                                               │
│  PDF: invoice_A7B9C2D4.pdf                                       │
│  Caption: "✅ Invoice Generated                                  │
│           Invoice ID: A7B9C2D4                                   │
│           Total Amount: ₹1,109.88                                │
│           Actions: [💳 Pay Bill] [❌ Reject Bill]"               │
└──────────────────────────────────────────────────────────────────┘

END OF FLOW
```

---

## 📋 Conversation States

| State # | State Name | Purpose | Input Expected |
|---------|------------|---------|----------------|
| 1 | `SEARCH_USER` | Search for user | Text: name/username/ID |
| 2 | `SELECT_USER` | User selection from results | Callback: `inv2_select_user_{index}` |
| 3 | `ITEM_MODE` | Choose item type | Callback: `inv2_search_store` or `inv2_custom_item` |
| 4a | `SEARCH_STORE_ITEM` | Search store items | Text: name/serial |
| 4b | `CUSTOM_ITEM_NAME` | Enter custom item name | Text: item name |
| 5a | `SELECT_STORE_ITEM` | Select store item | Callback: `inv2_select_item_{index}` |
| 5b | `CUSTOM_ITEM_RATE` | Enter custom item rate | Text: numeric amount |
| 6 | `ITEM_QUANTITY` | Enter quantity | Text: numeric quantity |
| 7 | `ITEM_DISCOUNT` | Enter discount % | Text: 0-80 |
| 8 | `ITEM_CONFIRM` | Confirm item addition | Callback: `inv2_item_add_more` or `inv2_items_done` |
| 9 | `SHIPPING` | Enter shipping charge | Text: numeric amount |
| 10 | `FINAL_REVIEW` | Review complete invoice | Callback: `inv2_send` |
| 11 | `SEND_INVOICE` | Generate & send PDF | (Automatic) |

---

## 🔧 Data Structure

### context.user_data Structure

```python
{
    "invoice_v2_data": {
        "selected_user": {
            "telegram_id": 123456,
            "full_name": "Sayali Patil",
            "telegram_username": "sayali_fit",
            "phone": "+919876543210",
            "approval_status": "approved"
        },
        "items": [
            {
                "name": "Protein Shake",
                "serial": "1001",           # Optional (store items only)
                "rate": 499,
                "quantity": 2,
                "discount_percent": 10,
                "gst_percent": 18,
                "base": 998.0,              # rate × quantity
                "discount_amount": 99.80,   # base × discount%
                "taxable": 898.20,          # base - discount
                "gst_amount": 161.68,       # taxable × gst%
                "line_total": 1059.88       # taxable + gst
            }
        ],
        "shipping": 50.0,
        "items_subtotal": 1059.88,
        "gst_total": 161.68,
        "final_total": 1109.88
    },
    "invoice_v2_current_item": {
        # Temporary storage for item being added
        "name": "Protein Shake",
        "rate": 499,
        "quantity": 2,
        "discount_percent": 10,
        "gst_percent": 18
    },
    "invoice_v2_search_results": {
        # Temporary storage for user search results
        0: { user_object },
        1: { user_object },
        2: { user_object }
    },
    "invoice_v2_store_results": {
        # Temporary storage for store item search results
        0: { item_object },
        1: { item_object }
    }
}
```

---

## 💾 Saved Invoice Format (JSON)

**File**: `data/invoices_v2.json`

```json
[
  {
    "invoice_id": "A7B9C2D4",
    "created_at": "2026-01-21T12:30:45.123456",
    "user_id": 123456,
    "user_name": "Sayali (@sayali_fit) - ID: 123456",
    "items": [
      {
        "name": "Protein Shake",
        "serial": "1001",
        "rate": 499,
        "quantity": 2,
        "discount_percent": 10,
        "gst_percent": 18,
        "base": 998.0,
        "discount_amount": 99.80,
        "taxable": 898.20,
        "gst_amount": 161.68,
        "line_total": 1059.88
      }
    ],
    "items_subtotal": 1059.88,
    "shipping": 50.0,
    "gst_total": 161.68,
    "final_total": 1109.88,
    "created_by": 987654321,
    "date": "2026-01-21"
  }
]
```

---

## 🧮 GST Calculation Logic

### Modes

1. **Exclusive Mode** (default):
   ```
   GST = Taxable Amount × GST% ÷ 100
   Total = Taxable Amount + GST
   ```

2. **Inclusive Mode**:
   ```
   GST = Taxable Amount × GST% ÷ (100 + GST%)
   Total = Taxable Amount (already includes GST)
   ```

### Example Calculation

**Item**: Protein Shake  
**Rate**: ₹499  
**Quantity**: 2  
**Discount**: 10%  
**GST**: 18% (Exclusive)

```
Step 1: Base = Rate × Qty
        = 499 × 2 = ₹998.00

Step 2: Discount = Base × Discount%
        = 998 × 10% = ₹99.80

Step 3: Taxable = Base - Discount
        = 998 - 99.80 = ₹898.20

Step 4: GST = Taxable × GST% ÷ 100
        = 898.20 × 18 ÷ 100 = ₹161.68

Step 5: Line Total = Taxable + GST
        = 898.20 + 161.68 = ₹1,059.88
```

---

## 📄 PDF Generation Details

**Library**: ReportLab  
**Function**: `generate_invoice_pdf()` in [src/invoices_v2/pdf.py](src/invoices_v2/pdf.py)

### PDF Sections

1. **Header**
   - Company logo (if available)
   - Invoice ID (large, bold)
   - Date
   - "TAX INVOICE" label

2. **User Details**
   - Name
   - Telegram Username
   - User ID
   - Phone (if available)

3. **Items Table**
   - Columns: Serial, Item Name, Rate, Qty, Discount%, Taxable, GST%, GST Amount, Line Total
   - Row for each item
   - Subtotal row

4. **Totals Section**
   - Items Subtotal
   - Shipping Charge
   - Total GST
   - **Final Total** (bold, large)

5. **Footer**
   - Terms & Conditions
   - Payment instructions
   - Contact information

---

## 🔗 User Actions on Invoice

After receiving the PDF, user can:

### 1. Pay Bill
**Callback**: `inv2_pay_{invoice_id}`  
**Handler**: `handle_pay_bill()` in [src/bot.py](src/bot.py)

**Flow**:
```
User clicks "💳 Pay Bill"
  ↓
Bot sends payment options:
  [💵 Cash]  [💳 UPI]  [💳 Card]
  ↓
User selects payment method
  ↓
Bot requests payment proof (if UPI/Card)
  ↓
User uploads screenshot
  ↓
Admin gets notification for approval
  ↓
Admin approves payment
  ↓
Payment recorded in database
  ↓
User receives confirmation
```

### 2. Reject Bill
**Callback**: `inv2_reject_{invoice_id}`  
**Handler**: `handle_reject_bill()` in [src/bot.py](src/bot.py)

**Flow**:
```
User clicks "❌ Reject Bill"
  ↓
Bot asks for rejection reason
  ↓
User enters reason
  ↓
Admin gets notification with reason
  ↓
Invoice marked as rejected
  ↓
User receives confirmation
```

---

## 🔍 Key Features

### 1. User Search Enhancement
- **Fuzzy matching**: ILIKE with wildcards
- **Multiple search modes**: Name, Username, User ID
- **Approval status display**: ✅ Approved, ⏳ Pending, ❌ Rejected
- **Example**: Searching "say" finds "Sayali", "Sayansh", "Say Kumar"

### 2. Store Item Integration
- **Serial number tracking**: Each item has unique serial
- **Auto-fill item details**: Name, MRP, GST% from store master
- **Search by name or serial**: Flexible search

### 3. Custom Items
- **Manual entry**: For services or non-store items
- **Global GST config**: Uses system GST settings
- **Example use cases**: Consultation fees, training sessions

### 4. Multi-Item Support
- **Add unlimited items**: No limit on items per invoice
- **Individual discounts**: Each item can have different discount
- **Different GST rates**: Each item can have different GST%

### 5. Automatic Calculations
- **Real-time totals**: Calculated as user inputs data
- **GST-aware**: Handles inclusive/exclusive modes
- **Shipping handling**: Added after item totals

---

## 🛠️ Error Handling

| Error Scenario | Handling |
|----------------|----------|
| User not found | "❌ No users found. Try again:" |
| Invalid user selection | "❌ User not found" (with query.answer()) |
| Store item not found | "❌ No items found. Try again:" |
| Invalid rate | "❌ Rate must be > 0. Try again:" |
| Invalid quantity | "❌ Quantity must be > 0. Try again:" |
| Invalid discount | "❌ Discount must be 0-80%. Try again:" |
| Invalid shipping | "❌ Shipping must be ≥ 0. Try again:" |
| Numeric input error | "❌ Invalid amount. Try again:" (with ValueError catch) |
| Admin access denied | "❌ Admin access required" (ConversationHandler.END) |

---

## 📝 Logging

All major actions are logged with `[INVOICE_V2]` prefix:

```python
[INVOICE_V2] entry_point admin=987654321
[INVOICE_V2] search_user_start admin=987654321
[INVOICE_V2] user_search_results count=3
[INVOICE_V2] user_selected admin=987654321 user_id=123456
[INVOICE_V2] store_item_selected serial=1001
[INVOICE_V2] custom_item_name name=Consultation Fee
[INVOICE_V2] item_quantity qty=2
[INVOICE_V2] item_discount discount=10.0%
[INVOICE_V2] item_added name=Protein Shake
[INVOICE_V2] shipping_set shipping=50.0
[INVOICE_V2] invoice_created invoice_id=A7B9C2D4 user_id=123456
[INVOICE_V2] invoice_sent_to_user invoice_id=A7B9C2D4 user_id=123456
```

---

## 🚀 ConversationHandler Configuration

**File**: [src/invoices_v2/handlers.py](src/invoices_v2/handlers.py)

```python
def get_invoice_v2_handler():
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(cmd_invoices_v2, pattern="^cmd_invoices_v2$")
        ],
        states={
            InvoiceV2State.SEARCH_USER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_search)
            ],
            InvoiceV2State.SELECT_USER: [
                CallbackQueryHandler(handle_user_select, pattern="^inv2_select_user_")
            ],
            InvoiceV2State.ITEM_MODE: [
                CallbackQueryHandler(handle_item_mode, pattern="^inv2_(search_store|custom_item|items_done|cancel)$")
            ],
            InvoiceV2State.SEARCH_STORE_ITEM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_store_search)
            ],
            InvoiceV2State.SELECT_STORE_ITEM: [
                CallbackQueryHandler(handle_store_select, pattern="^inv2_(select_item_|cancel)$")
            ],
            InvoiceV2State.CUSTOM_ITEM_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_custom_name)
            ],
            InvoiceV2State.CUSTOM_ITEM_RATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_custom_rate)
            ],
            InvoiceV2State.ITEM_QUANTITY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_item_quantity)
            ],
            InvoiceV2State.ITEM_DISCOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_item_discount)
            ],
            InvoiceV2State.ITEM_CONFIRM: [
                CallbackQueryHandler(handle_item_confirm, pattern="^inv2_(item_add_more|items_done|cancel)$")
            ],
            InvoiceV2State.SHIPPING: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_shipping)
            ],
            InvoiceV2State.FINAL_REVIEW: [
                CallbackQueryHandler(handle_send_invoice, pattern="^inv2_(send|cancel)$")
            ]
        },
        fallbacks=[
            CallbackQueryHandler(handle_cancel, pattern="^inv2_cancel$")
        ],
        conversation_timeout=600,  # 10 minutes
        per_message=False
    )
```

---

## 🔄 State Management

### Context Clearing
- **Entry point**: Clears all previous invoice data
- **On cancel**: Removes invoice_v2_data from context
- **On completion**: Data persists until next invoice creation

### State Transitions
- **Forward flow**: User progresses through states linearly
- **Add more items**: Loops back to ITEM_MODE from ITEM_CONFIRM
- **Cancel anytime**: Returns to ConversationHandler.END

---

## 📚 Related Files

| File | Purpose |
|------|---------|
| [src/invoices_v2/handlers.py](src/invoices_v2/handlers.py) | Main conversation handlers |
| [src/invoices_v2/state.py](src/invoices_v2/state.py) | State enum definitions |
| [src/invoices_v2/store.py](src/invoices_v2/store.py) | Store item search functions |
| [src/invoices_v2/utils.py](src/invoices_v2/utils.py) | User search, GST config, formatting |
| [src/invoices_v2/pdf.py](src/invoices_v2/pdf.py) | PDF generation with reportlab |
| [data/invoices_v2.json](data/invoices_v2.json) | Invoice storage |
| [src/bot.py](src/bot.py) | Pay/Reject callback handlers |

---

## 🎯 Usage Example

**Complete flow from admin perspective**:

1. Admin clicks "🧾 Invoices" in Admin Panel
2. Bot asks "Search user by Name, Username, or Telegram ID:"
3. Admin types "sayali"
4. Bot shows 3 results with buttons
5. Admin clicks user button
6. Bot confirms "✅ Selected: Sayali" with item options
7. Admin clicks "🔍 Search Store Item"
8. Admin types "protein"
9. Bot shows 2 protein products
10. Admin clicks "Protein Shake"
11. Bot asks "Enter Quantity:" → Admin types "2"
12. Bot asks "Enter Discount %:" → Admin types "10"
13. Bot shows item summary with "➕ Add Another Item" or "➡️ Finish Items"
14. Admin clicks "Finish Items"
15. Bot asks "Enter Shipping:" → Admin types "50"
16. Bot shows final review with "📤 Send Invoice"
17. Admin clicks "Send Invoice"
18. PDF generated and sent to user
19. Admin sees "✅ Invoice A7B9C2D4 sent to Sayali"

**Total time**: ~2-3 minutes for experienced admin

---

## 🔐 Security & Validation

- ✅ **Admin-only access**: `is_admin()` check at entry point
- ✅ **Input validation**: All numeric inputs validated (rate, qty, discount, shipping)
- ✅ **Discount cap**: Max 80% to prevent abuse
- ✅ **Positive values**: All amounts must be > 0 (except shipping ≥ 0)
- ✅ **State isolation**: Each conversation uses separate context.user_data
- ✅ **Timeout protection**: 10-minute conversation timeout

---

**Status**: ✅ **Production Ready**  
**Last Updated**: 2026-01-21  
**Version**: Invoice v2  
