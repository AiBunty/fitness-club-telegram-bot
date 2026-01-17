"""
UPI QR Code Generation for Subscription Payments
- Generate UPI payment strings
- Create QR codes for UPI payments
"""

import logging
import io
import qrcode
from PIL import Image
import base64

logger = logging.getLogger(__name__)

# UPI ID for gym - CONFIGURE THIS
GYM_UPI_ID = "9158243377@ybl"  # Fitness Club UPI ID
GYM_NAME = "Fitness Club Gym"

# Admin configurable settings (loaded from database)
def get_upi_id() -> str:
    """Get UPI ID from database or config, with fallback to default"""
    try:
        from src.database.connection import execute_query
        result = execute_query(
            "SELECT upi_id FROM gym_settings WHERE id = 1",
            fetch_one=True
        )
        if result and result[0]:
            return result[0]
    except:
        pass
    return GYM_UPI_ID


def get_qr_code_url() -> str:
    """Get custom QR code URL from database, if configured"""
    try:
        from src.database.connection import execute_query
        result = execute_query(
            "SELECT qr_code_url FROM gym_settings WHERE id = 1",
            fetch_one=True
        )
        if result and result[0]:
            return result[0]
    except:
        pass
    return None



def generate_upi_string(amount: float, user_name: str, transaction_ref: str) -> str:
    """Generate UPI string for payment
    Format: upi://pay?pa=UPI_ID&pn=NAME&am=AMOUNT&tn=DESCRIPTION
    """
    try:
        # URL encode special characters
        payee_name = GYM_NAME.replace(" ", "%20")
        user_ref = transaction_ref.replace(" ", "%20")
        
        upi_string = (
            f"upi://pay?"
            f"pa={GYM_UPI_ID}&"
            f"pn={payee_name}&"
            f"am={amount}&"
            f"tn=Gym%20Subscription%20-%20{user_ref}&"
            f"tr={transaction_ref}"
        )
        
        logger.info(f"UPI string generated for amount {amount}")
        return upi_string
    except Exception as e:
        logger.error(f"Error generating UPI string: {e}")
        return None


def generate_upi_qr_code(amount: float, user_name: str, transaction_ref: str) -> bytes:
    """Generate QR code image for UPI payment
    Returns: PNG image bytes
    """
    try:
        upi_string = generate_upi_string(amount, user_name, transaction_ref)
        if not upi_string:
            return None
        
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(upi_string)
        qr.make(fit=True)
        
        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to bytes
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        
        logger.info(f"QR code generated for transaction {transaction_ref}")
        return img_byte_arr.getvalue()
        
    except Exception as e:
        logger.error(f"Error generating QR code: {e}")
        return None


def get_upi_qr_base64(amount: float, user_name: str, transaction_ref: str) -> str:
    """Generate QR code and return as base64 string for inline display"""
    try:
        qr_bytes = generate_upi_qr_code(amount, user_name, transaction_ref)
        if not qr_bytes:
            return None
        
        base64_str = base64.b64encode(qr_bytes).decode('utf-8')
        return base64_str
    except Exception as e:
        logger.error(f"Error encoding QR code to base64: {e}")
        return None
