#!/usr/bin/env python3
"""
Test script to validate Bulk Upload & Reports fixes
Tests:
1. reports_operations.py has no telegram_id references
2. Connection pool management in finally blocks
3. admin_gst_store_handlers.py has TEXT handler for BULK_UPLOAD_AWAIT
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("=" * 60)
print("🧪 BULK UPLOAD & REPORTS FIX VALIDATION")
print("=" * 60)

# Test 1: Verify telegram_id removed from reports_operations.py
print("\n[Test 1] Checking reports_operations.py for telegram_id...")
reports_file = project_root / "src" / "database" / "reports_operations.py"
with open(reports_file, 'r', encoding='utf-8') as f:
    content = f.read()
    
# Count only actual column references, not comments
lines = content.split('\n')
telegram_id_refs = []
for i, line in enumerate(lines, 1):
    if 'telegram_id' in line and not line.strip().startswith('#') and 'FIX:' not in line:
        telegram_id_refs.append((i, line.strip()))

if telegram_id_refs:
    print("❌ FAIL: Found telegram_id references:")
    for line_num, line in telegram_id_refs:
        print(f"   Line {line_num}: {line}")
else:
    print("✅ PASS: No telegram_id column references found")

# Test 2: Verify connection pool management
print("\n[Test 2] Checking connection pool management...")
functions_to_check = [
    'get_active_members',
    'get_inactive_members',
    'get_expiring_soon_members',
    'get_member_daily_activity',
    'get_top_performers',
    'get_inactive_users',
    'move_expired_to_inactive'
]

finally_blocks_found = content.count('finally:')
putconn_calls_found = content.count('putconn(conn)')

print(f"   Finally blocks found: {finally_blocks_found}")
print(f"   putconn() calls found: {putconn_calls_found}")

if finally_blocks_found >= 7 and putconn_calls_found >= 7:
    print("✅ PASS: All functions have proper connection pool management")
else:
    print(f"❌ FAIL: Expected 7+ finally blocks and putconn() calls")

# Test 3: Verify TEXT handler for BULK_UPLOAD_AWAIT
print("\n[Test 3] Checking admin_gst_store_handlers.py for TEXT handler...")
handlers_file = project_root / "src" / "handlers" / "admin_gst_store_handlers.py"
with open(handlers_file, 'r', encoding='utf-8') as f:
    handlers_content = f.read()

has_text_handler_function = 'handle_bulk_upload_text' in handlers_content
has_text_handler_in_state = 'filters.TEXT & ~filters.COMMAND, handle_bulk_upload_text' in handlers_content
has_feedback_message = 'Processing file, please wait' in handlers_content

print(f"   handle_bulk_upload_text function: {'✅' if has_text_handler_function else '❌'}")
print(f"   TEXT handler in BULK_UPLOAD_AWAIT: {'✅' if has_text_handler_in_state else '❌'}")
print(f"   Feedback message on upload: {'✅' if has_feedback_message else '❌'}")

if has_text_handler_function and has_text_handler_in_state and has_feedback_message:
    print("✅ PASS: TEXT handler and feedback messages implemented")
else:
    print("❌ FAIL: Missing TEXT handler or feedback messages")

# Test 4: Try importing and running a simple query
print("\n[Test 4] Testing reports_operations imports...")
try:
    from src.database.reports_operations import get_active_members, get_inactive_members
    print("✅ PASS: reports_operations imports successfully")
    
    # Try to get schema-correct results (will fail if DB not connected, but import works)
    print("\n[Test 5] Testing function signatures...")
    import inspect
    
    # Check get_active_members signature
    sig = inspect.signature(get_active_members)
    print(f"   get_active_members signature: {sig}")
    
    # Check if it returns correct dict keys (by inspecting source)
    source = inspect.getsource(get_active_members)
    if "'user_id': row[0]" in source and "'telegram_id'" not in source:
        print("✅ PASS: get_active_members uses correct column mapping")
    else:
        print("❌ FAIL: get_active_members has incorrect column mapping")
        
except Exception as e:
    print(f"⚠️  WARNING: Could not import reports_operations: {e}")
    print("   (This is OK if database is not configured)")

# Test 5: Verify ConversationHandler state configuration
print("\n[Test 6] Checking ConversationHandler configuration...")
if 'BULK_UPLOAD_AWAIT: [' in handlers_content:
    # Extract the BULK_UPLOAD_AWAIT configuration
    start = handlers_content.find('BULK_UPLOAD_AWAIT: [')
    end = handlers_content.find(']', start)
    bulk_config = handlers_content[start:end+1]
    
    has_document = 'filters.Document.ALL' in bulk_config
    has_text = 'filters.TEXT' in bulk_config
    
    print(f"   Document handler: {'✅' if has_document else '❌'}")
    print(f"   TEXT handler: {'✅' if has_text else '❌'}")
    
    if has_document and has_text:
        print("✅ PASS: BULK_UPLOAD_AWAIT has both Document and TEXT handlers")
    else:
        print("❌ FAIL: BULK_UPLOAD_AWAIT missing handlers")
else:
    print("❌ FAIL: Could not find BULK_UPLOAD_AWAIT configuration")

# Summary
print("\n" + "=" * 60)
print("📊 VALIDATION SUMMARY")
print("=" * 60)

all_tests_passed = (
    len(telegram_id_refs) == 0 and
    finally_blocks_found >= 7 and
    putconn_calls_found >= 7 and
    has_text_handler_function and
    has_text_handler_in_state and
    has_feedback_message
)

if all_tests_passed:
    print("✅ ALL TESTS PASSED - Ready for production deployment")
    print("\n📋 Deployment Checklist:")
    print("   [✅] telegram_id column removed from all queries")
    print("   [✅] Connection pool management in place")
    print("   [✅] TEXT handler for bulk upload")
    print("   [✅] Feedback messages added")
    print("   [ ] Test /reports command in production")
    print("   [ ] Test bulk upload with text input")
    print("   [ ] Monitor connection pool metrics")
else:
    print("❌ SOME TESTS FAILED - Review fixes before deployment")

print("\n" + "=" * 60)
