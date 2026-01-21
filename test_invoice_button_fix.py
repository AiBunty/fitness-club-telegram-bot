#!/usr/bin/env python3
"""
Test script to validate Invoice Button Fix
Verifies:
1. Invoice v2 handler has proper entry point pattern
2. Handler registration order (Invoice BEFORE generic callbacks)
3. Per-chat isolation for 200+ users
4. Immediate query.answer() in entry point
5. Fallback logging for diagnostic
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("=" * 70)
print("🧪 INVOICE BUTTON FIX VALIDATION")
print("=" * 70)

# Test 1: Check entry point has query.answer()
print("\n[Test 1] Checking Invoice v2 entry point has query.answer()...")
handlers_file = project_root / "src" / "invoices_v2" / "handlers.py"
with open(handlers_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Find the cmd_invoices_v2 function
if 'async def cmd_invoices_v2' in content:
    func_start = content.find('async def cmd_invoices_v2')
    func_end = content.find('\n\nasync def', func_start + 1)
    func_content = content[func_start:func_end]
    
    has_query_answer = 'await query.answer()' in func_content
    has_state_clear = 'context.user_data.clear()' in func_content
    has_callback_log = 'callback_data={query.data}' in func_content or 'callback_received' in func_content
    
    print(f"   query.answer() present: {'✅' if has_query_answer else '❌'}")
    print(f"   context.user_data.clear() present: {'✅' if has_state_clear else '❌'}")
    print(f"   Callback logging present: {'✅' if has_callback_log else '❌'}")
    
    test1_pass = has_query_answer and has_state_clear
else:
    print("❌ FAIL: cmd_invoices_v2 function not found")
    test1_pass = False

# Test 2: Check ConversationHandler has per_chat=True
print("\n[Test 2] Checking Invoice v2 handler has per_chat isolation...")
if 'def get_invoice_v2_handler' in content:
    handler_start = content.find('def get_invoice_v2_handler')
    handler_end = content.find('\n\n', handler_start + 1)
    handler_content = content[handler_start:handler_end]
    
    has_per_chat = 'per_chat=True' in handler_content
    has_per_user = 'per_user=True' in handler_content
    has_timeout = 'conversation_timeout=600' in handler_content
    has_entry_pattern = 'pattern="^cmd_invoices$"' in handler_content
    
    print(f"   per_chat=True: {'✅' if has_per_chat else '❌'}")
    print(f"   per_user=True: {'✅' if has_per_user else '❌'}")
    print(f"   conversation_timeout=600: {'✅' if has_timeout else '❌'}")
    print(f"   Entry pattern ^cmd_invoices$: {'✅' if has_entry_pattern else '❌'}")
    
    test2_pass = has_per_chat and has_timeout and has_entry_pattern
else:
    print("❌ FAIL: get_invoice_v2_handler function not found")
    test2_pass = False

# Test 3: Check handler registration order in bot.py
print("\n[Test 3] Checking handler registration order in bot.py...")
bot_file = project_root / "src" / "bot.py"
with open(bot_file, 'r', encoding='utf-8') as f:
    bot_content = f.read()

# Find positions
invoice_pos = bot_content.find('get_invoice_v2_handler()')
gst_store_pos = bot_content.find('get_store_and_gst_handlers()')
generic_callback_pos = bot_content.find('handle_callback_query, pattern="^(?!')

if invoice_pos > 0 and gst_store_pos > 0:
    invoice_before_gst = invoice_pos < gst_store_pos
    print(f"   Invoice BEFORE GST/Store: {'✅' if invoice_before_gst else '❌'}")
else:
    print("❌ FAIL: Could not find handler registrations")
    invoice_before_gst = False

if invoice_pos > 0 and generic_callback_pos > 0:
    invoice_before_generic = invoice_pos < generic_callback_pos
    print(f"   Invoice BEFORE generic callback: {'✅' if invoice_before_generic else '❌'}")
else:
    invoice_before_generic = False

has_registration_log = 'Registering Invoice v2 handler' in bot_content or 'Invoice v2 handlers registered' in bot_content
print(f"   Registration logging present: {'✅' if has_registration_log else '❌'}")

test3_pass = invoice_before_gst and invoice_before_generic

# Test 4: Check button callback_data matches entry pattern
print("\n[Test 4] Checking button callback_data matches handler pattern...")
role_keyboard_file = project_root / "src" / "handlers" / "role_keyboard_handlers.py"
with open(role_keyboard_file, 'r', encoding='utf-8') as f:
    role_content = f.read()

has_invoice_button = 'Invoices' in role_content and 'callback_data="cmd_invoices"' in role_content
print(f"   Invoice button with cmd_invoices: {'✅' if has_invoice_button else '❌'}")

# Check the pattern excludes cmd_invoices from generic handler
generic_pattern_excludes = 'cmd_invoices' in bot_content and 'pattern="^(?!' in bot_content
exclusion_line = None
for line in bot_content.split('\n'):
    if 'handle_callback_query' in line and 'pattern=' in line:
        exclusion_line = line
        break

if exclusion_line:
    excludes_invoice = 'cmd_invoices' in exclusion_line
    print(f"   Generic handler excludes cmd_invoices: {'✅' if excludes_invoice else '❌'}")
else:
    excludes_invoice = False
    print("   Generic handler pattern: ❌ Not found")

test4_pass = has_invoice_button and excludes_invoice

# Test 5: Check fallback logging in callback_handlers
print("\n[Test 5] Checking fallback logging in callback_handlers.py...")
callback_file = project_root / "src" / "handlers" / "callback_handlers.py"
with open(callback_file, 'r', encoding='utf-8') as f:
    callback_content = f.read()

has_fallback = 'CALLBACK_FALLBACK' in callback_content and 'cmd_invoices' in callback_content
has_inv2_check = 'startswith("inv2_")' in callback_content
print(f"   Fallback logging for cmd_invoices: {'✅' if has_fallback else '❌'}")
print(f"   Fallback logging for inv2_: {'✅' if has_inv2_check else '❌'}")

test5_pass = has_fallback and has_inv2_check

# Summary
print("\n" + "=" * 70)
print("📊 VALIDATION SUMMARY")
print("=" * 70)

all_tests_passed = test1_pass and test2_pass and test3_pass and test4_pass and test5_pass

test_results = [
    ("Entry Point (query.answer + clear)", test1_pass),
    ("Per-chat Isolation (per_chat=True)", test2_pass),
    ("Handler Registration Order", test3_pass),
    ("Button Callback Matching", test4_pass),
    ("Fallback Diagnostic Logging", test5_pass)
]

for test_name, passed in test_results:
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"   [{status}] {test_name}")

print("\n" + "=" * 70)
if all_tests_passed:
    print("✅ ALL TESTS PASSED - Invoice button should now work!")
    print("\n📋 Next Steps:")
    print("   1. Restart the bot")
    print("   2. Click 'Admin Panel' → 'Staff' role")
    print("   3. Click '🧾 Invoices' button")
    print("   4. Check logs for [INVOICE_V2] entry_point messages")
    print("   5. Verify no [CALLBACK_FALLBACK] errors")
else:
    print("❌ SOME TESTS FAILED - Review fixes before deployment")

print("\n🔍 Diagnostic Commands:")
print("   # Check if button click is logged:")
print("   grep -i 'INVOICE_V2.*entry_point' bot_output.log")
print("   # Check for callback fallback errors:")
print("   grep -i 'CALLBACK_FALLBACK' bot_output.log")
print("   # Check handler registration:")
print("   grep -i 'Registering Invoice' bot_output.log")

print("\n" + "=" * 70)
