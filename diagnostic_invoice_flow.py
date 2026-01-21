#!/usr/bin/env python3
"""
Diagnostic script to verify Invoice v2 callback flow is working correctly
Checks:
1. Invoice button is registered with correct callback_data
2. InvoiceV2 ConversationHandler is properly registered
3. Handler patterns don't conflict
4. Admin access check is in place
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def check_invoice_button():
    """Check if invoice button has correct callback_data"""
    print("[✓] Checking Invoice button registration...")
    
    from src.handlers.role_keyboard_handlers import ADMIN_MENU
    
    # Get keyboard buttons
    buttons = []
    for row in ADMIN_MENU.inline_keyboard:
        for btn in row:
            buttons.append((btn.text, btn.callback_data))
    
    invoice_button = next((cb for txt, cb in buttons if "Invoices" in txt), None)
    if invoice_button == "cmd_invoices":
        print(f"   ✅ Invoice button found with correct callback_data: {invoice_button}")
        return True
    else:
        print(f"   ❌ Invoice button NOT found or has wrong callback_data: {invoice_button}")
        return False


def check_invoice_handler():
    """Check if InvoiceV2 ConversationHandler is properly defined"""
    print("[✓] Checking Invoice v2 ConversationHandler...")
    
    from src.invoices_v2.handlers import get_invoice_v2_handler
    
    handler = get_invoice_v2_handler()
    
    # Verify entry points
    entry_patterns = []
    for ep in handler.entry_points:
        if hasattr(ep, 'pattern'):
            entry_patterns.append(ep.pattern)
    
    has_cmd_invoices = any("cmd_invoices" in str(p) for p in entry_patterns)
    if has_cmd_invoices:
        print(f"   ✅ Invoice v2 ConversationHandler has entry pattern for cmd_invoices")
        print(f"      Entry patterns: {entry_patterns}")
        return True
    else:
        print(f"   ❌ Invoice v2 ConversationHandler missing cmd_invoices pattern")
        print(f"      Entry patterns: {entry_patterns}")
        return False


def check_bot_handler_registration():
    """Check if handlers are registered in correct order in src/bot.py"""
    print("[✓] Checking handler registration order in src/bot.py...")
    
    bot_file = project_root / "src" / "bot.py"
    content = bot_file.read_text()
    
    # Find positions of key handlers
    invoice_pos = content.find("get_invoice_v2_handler()")
    generic_pos = content.find("handle_callback_query, \n")
    
    if invoice_pos > 0 and generic_pos > 0:
        if invoice_pos < generic_pos:
            print(f"   ✅ Invoice v2 handler registered BEFORE generic callback handler")
            print(f"      Invoice handler at position {invoice_pos}")
            print(f"      Generic handler at position {generic_pos}")
            return True
        else:
            print(f"   ❌ Invoice v2 handler registered AFTER generic callback handler")
            print(f"      This will prevent invoice callbacks from being processed!")
            return False
    else:
        print(f"   ❌ Could not find handler registrations in bot.py")
        return False


def check_admin_access():
    """Check if invoice handler has admin access verification"""
    print("[✓] Checking admin access control in invoice handler...")
    
    handlers_file = project_root / "src" / "invoices_v2" / "handlers.py"
    content = handlers_file.read_text()
    
    # Find the cmd_invoices_v2 function
    func_start = content.find("async def cmd_invoices_v2")
    if func_start == -1:
        print("   ❌ cmd_invoices_v2 function not found")
        return False
    
    # Find the end of the function (next function definition or end of admin access check)
    func_section = content[func_start:func_start+2000]
    
    has_admin_check = "is_admin" in func_section
    has_query_answer = "query.answer()" in func_section
    
    if has_admin_check:
        print("   ✅ Admin access control found in cmd_invoices_v2")
    else:
        print("   ❌ Admin access control NOT found in cmd_invoices_v2")
    
    if has_query_answer:
        print("   ✅ query.answer() found for immediate response")
    else:
        print("   ⚠️  query.answer() NOT found - may cause telegram loading spinner to hang")
    
    return has_admin_check and has_query_answer


def check_generic_handler_exclusions():
    """Check if generic handler properly excludes invoice patterns"""
    print("[✓] Checking generic handler exclusion patterns...")
    
    bot_file = project_root / "src" / "bot.py"
    content = bot_file.read_text()
    
    # Find the generic callback handler pattern
    handler_pattern_start = content.find('pattern="^(?!')
    if handler_pattern_start == -1:
        print("   ❌ Generic handler pattern not found")
        return False
    
    # Extract the pattern (next ~500 chars should have it)
    pattern_section = content[handler_pattern_start:handler_pattern_start+500]
    pattern_end = pattern_section.find(')"')
    pattern = pattern_section[:pattern_end+1]
    
    print(f"   Pattern: {pattern[:100]}...")
    
    required_exclusions = ["cmd_invoices", "inv2_", "inv_", "manage_", "admin_invoice"]
    found_exclusions = []
    missing_exclusions = []
    
    for exclusion in required_exclusions:
        if exclusion in pattern:
            found_exclusions.append(exclusion)
        else:
            missing_exclusions.append(exclusion)
    
    print(f"   ✅ Found exclusions: {found_exclusions}")
    if missing_exclusions:
        print(f"   ❌ Missing exclusions: {missing_exclusions}")
        return False
    
    return True


def check_logging():
    """Check if invoice handler has proper logging"""
    print("[✓] Checking logging in invoice handler...")
    
    handlers_file = project_root / "src" / "invoices_v2" / "handlers.py"
    content = handlers_file.read_text()
    
    # Check for INVOICE_V2 logs
    has_invoice_logs = "[INVOICE_V2]" in content
    
    if has_invoice_logs:
        # Count invoice logs
        log_count = content.count("[INVOICE_V2]")
        print(f"   ✅ Found {log_count} [INVOICE_V2] log statements")
        return True
    else:
        print("   ❌ No [INVOICE_V2] logging found")
        return False


def main():
    """Run all diagnostics"""
    print("=" * 60)
    print("Invoice v2 Button Diagnostic")
    print("=" * 60)
    print()
    
    checks = [
        check_invoice_button,
        check_invoice_handler,
        check_bot_handler_registration,
        check_admin_access,
        check_generic_handler_exclusions,
        check_logging,
    ]
    
    results = []
    for check in checks:
        try:
            result = check()
            results.append((check.__name__, result))
        except Exception as e:
            print(f"   ❌ Exception: {e}")
            results.append((check.__name__, False))
        print()
    
    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for check_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {check_name}")
    
    print()
    print(f"Result: {passed}/{total} checks passed")
    
    if passed == total:
        print("\n✅ All diagnostic checks passed!")
        print("\nNext steps:")
        print("1. Ensure bot is running: python start_bot.py")
        print("2. Click the Invoices button in Telegram")
        print("3. Check logs for [INVOICE_V2] messages")
        return 0
    else:
        print(f"\n❌ {total - passed} checks failed - please fix the issues above")
        return 1


if __name__ == '__main__':
    sys.exit(main())
