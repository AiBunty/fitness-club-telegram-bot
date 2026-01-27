"""
Test Invoice v2 Flow End-to-End
Tests: invoice creation, data persistence, notification generation, PDF generation
"""
import sys
import os
import json
from datetime import datetime
from pathlib import Path

# Add repo to path FIRST to ensure proper imports
sys.path.insert(0, str(Path(__file__).parent))

# Set environment for local testing
os.environ['USE_LOCAL_DB'] = 'false'
os.environ['USE_REMOTE_DB'] = 'true'
os.environ['SKIP_DB_TEST'] = '0'
os.environ['SKIP_SCHEDULING'] = '1'
os.environ['DISABLE_POLLING_FOR_TEST'] = '1'

def test_invoice_operations():
    """Test core invoice operations"""
    print("\n" + "="*80)
    print("TEST 1: Invoice File Operations")
    print("="*80)
    
    from src.invoices_v2.handlers import (
        ensure_invoices_file, load_invoices, save_invoice, save_invoices
    )
    
    # Ensure file exists
    ensure_invoices_file()
    print("✓ Invoices file created/verified")
    
    # Create test invoice
    test_invoice = {
        "user_id": 12345,
        "user_name": "Test User",
        "items": [
            {"name": "Protein Shake", "mrp": 500, "gst": 18, "gst_amount": 90, "total": 590},
            {"name": "Water Bottle", "mrp": 200, "gst": 12, "gst_amount": 24, "total": 224}
        ],
        "items_subtotal": 700,
        "shipping": 50,
        "gst_total": 114,
        "final_total": 864,
        "created_by": 424837855,
        "date": datetime.now().strftime("%Y-%m-%d")
    }
    
    invoice_id = save_invoice(test_invoice)
    print(f"✓ Invoice created: {invoice_id}")
    print(f"  - User: {test_invoice['user_name']} (ID: {test_invoice['user_id']})")
    print(f"  - Items: {len(test_invoice['items'])} items")
    print(f"  - Subtotal: ₹{test_invoice['items_subtotal']}")
    print(f"  - GST: ₹{test_invoice['gst_total']}")
    print(f"  - Final Total: ₹{test_invoice['final_total']}")
    
    # Load and verify
    invoices = load_invoices()
    saved_invoice = next((inv for inv in invoices if inv.get("invoice_id") == invoice_id), None)
    
    if saved_invoice:
        print("✓ Invoice persisted and retrieved from storage")
        print(f"  - Created at: {saved_invoice.get('created_at')}")
    else:
        print("✗ FAILED: Invoice not found in storage")
        return False
    
    return invoice_id


def test_user_search():
    """Test user search functionality"""
    print("\n" + "="*80)
    print("TEST 2: User Search (Database)")
    print("="*80)
    
    from src.invoices_v2.utils import search_users
    
    # Search for admin user
    results = search_users("424837855", limit=10)
    print(f"✓ User search executed, found {len(results)} result(s)")
    
    if results:
        user = results[0]
        print(f"  - Telegram ID: {user.get('telegram_id')}")
        print(f"  - Name: {user.get('first_name')} {user.get('last_name', '').strip()}")
        print(f"  - Phone: {user.get('phone', 'N/A')}")
        return user
    else:
        print("⚠ No users found - database may be empty")
        return None


def test_store_items():
    """Test store item search"""
    print("\n" + "="*80)
    print("TEST 3: Store Item Search")
    print("="*80)
    
    from src.invoices_v2.store import search_item, load_items
    
    items = load_items()
    print(f"✓ Store loaded, total items: {len(items)}")
    
    if items:
        # Show first 3 items
        for i, item in enumerate(items[:3]):
            print(f"\n  Item {i+1}:")
            print(f"    - Serial: {item.get('serial')}")
            print(f"    - Name: {item.get('name')}")
            print(f"    - MRP: ₹{item.get('mrp')}")
            print(f"    - GST: {item.get('gst_percent')}%")
        
        # Test search
        search_results = search_item("protein")
        print(f"\n✓ Search executed: 'protein' -> {len(search_results)} result(s)")
        return items
    else:
        print("⚠ No store items found - store may be empty")
        return None


def test_database_connection():
    """Test database connectivity"""
    print("\n" + "="*80)
    print("TEST 4: Database Connection")
    print("="*80)
    
    from src.database.connection import test_connection
    
    if test_connection():
        print("✓ Database connection successful")
        return True
    else:
        print("✗ Database connection FAILED")
        return False


def test_notifications():
    """Test notification creation"""
    print("\n" + "="*80)
    print("TEST 5: Notification System")
    print("="*80)
    
    try:
        from src.database.notification_operations import create_notification
        
        # Create test notification
        notif = create_notification(
            user_id=12345,
            title="Invoice Generated",
            message="Invoice INV123 for ₹864 has been created. Click to review.",
            notification_type="invoice_generated",
            related_entity_type="invoice",
            related_entity_id="INV123"
        )
        
        if notif:
            print("✓ Notification created successfully")
            print(f"  - Type: {notif.get('notification_type')}")
            print(f"  - Title: {notif.get('title')}")
            print(f"  - User ID: {notif.get('user_id')}")
            return True
        else:
            print("✗ Notification creation returned None")
            return False
    except Exception as e:
        print(f"⚠ Notification test skipped or error: {e}")
        return False


def test_pdf_generation():
    """Test PDF generation"""
    print("\n" + "="*80)
    print("TEST 6: PDF Generation")
    print("="*80)
    
    try:
        from src.invoices_v2.pdf import generate_invoice_pdf
        from io import BytesIO
        
        pdf_data = {
            "invoice_id": "TEST123",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "user_name": "Test User",
            "user_id": 12345,
            "items": [
                {"name": "Protein Shake", "mrp": 500, "gst": 18, "total": 590},
                {"name": "Water Bottle", "mrp": 200, "gst": 12, "total": 224}
            ],
            "items_subtotal": 700,
            "shipping": 50,
            "gst_total": 114,
            "final_total": 864
        }
        
        pdf_buffer = generate_invoice_pdf(pdf_data)
        
        if pdf_buffer and isinstance(pdf_buffer, BytesIO):
            pdf_size = len(pdf_buffer.getvalue())
            print(f"✓ PDF generated successfully")
            print(f"  - Size: {pdf_size:,} bytes")
            print(f"  - Invoice ID: {pdf_data['invoice_id']}")
            return True
        else:
            print("✗ PDF generation failed")
            return False
    except Exception as e:
        print(f"✗ PDF generation error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*15 + "INVOICE v2 FLOW - COMPREHENSIVE TEST" + " "*29 + "║")
    print("╚" + "="*78 + "╝")
    
    results = {}
    
    # Test 1: Database
    results['database'] = test_database_connection()
    
    # Test 2: User Search
    user = test_user_search()
    results['user_search'] = user is not None
    
    # Test 3: Store Items
    items = test_store_items()
    results['store_items'] = items is not None and len(items) > 0
    
    # Test 4: Invoice Operations
    try:
        invoice_id = test_invoice_operations()
        results['invoice_operations'] = invoice_id is not None
    except Exception as e:
        print(f"✗ Invoice operations error: {e}")
        results['invoice_operations'] = False
    
    # Test 5: Notifications
    try:
        results['notifications'] = test_notifications()
    except Exception as e:
        print(f"✗ Notifications error: {e}")
        results['notifications'] = False
    
    # Test 6: PDF Generation
    try:
        results['pdf_generation'] = test_pdf_generation()
    except Exception as e:
        print(f"✗ PDF generation error: {e}")
        results['pdf_generation'] = False
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}  {test_name.replace('_', ' ').title()}")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✅ All tests PASSED! Invoice system is fully operational.")
        return 0
    else:
        print(f"\n⚠ {total - passed} test(s) failed. Check errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
