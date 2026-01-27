# Store Bulk Upload - Skipped Rows Remedy

**What happened**
- Bulk upload result: `New items added: 0`, `Items updated: 1`, `Rows skipped: 3`.
- The uploaded sheet (screenshot) shows Serial No cells containing both the serial and the item name text (e.g., `"1 Herbalife Fromula 1 Chocolat"`).
- In the parser (`src/handlers/admin_gst_store_handlers.py`), the Serial No column must be **numeric-only** (or blank). If the cell has any letters or combined text, parsing `int(serial)` fails and the row is skipped.

**Why rows were skipped**
1) Serial column not numeric (text combined with name) → parser cannot convert to int → row skipped.
2) If Serial is missing but HSN/Name are blank, the row is skipped.
3) If MRP or GST are non-numeric/empty, the row is skipped.

**How to upload correctly**
- Keep columns exactly as the sample: `Serial No | Item Name | HSN Code | MRP | GST %`.
- Serial No rules:
  - For **new items**: leave Serial No **blank**.
  - For **updates**: put the existing serial number only (numeric). Do not type the name in this cell.
- Item Name: plain text only (do not prefix with serial).
- HSN Code: numeric/string allowed, but keep it in its own column.
- MRP and GST %: must be numeric cells (no commas, no text). Example: `1800` or `1800.00`, GST `18`.
- Save as `.xlsx` (not CSV). Do not use merged cells.

**Quick fix for your sheet (per screenshot)**
- Move the product names out of the Serial No column into the Item Name column.
- Keep Serial No cells as: 1, 2, 3, 4 (or blank if you want them created as new items).
- Ensure HSN Code 21069099, MRP 1800/2200, GST 18 stay numeric.
- Re-upload after this correction; all rows should process.

**Reference**
- Parser logic: `src/handlers/admin_gst_store_handlers.py` (bulk upload section uses `int(serial)`; invalid serials are skipped).
- Current store demo data: `data/store_items.json` (10 Herbalife items preloaded for testing).
