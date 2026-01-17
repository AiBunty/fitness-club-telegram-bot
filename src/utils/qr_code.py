import qrcode
import io
import logging

logger = logging.getLogger(__name__)


def generate_gym_qr_code(user_id: int, full_name: str, phone: str) -> io.BytesIO:
    """
    Generate a QR code for gym login verification.
    Format: user_id|full_name|phone (can be scanned by staff)
    """
    try:
        data = f"{user_id}|{full_name}|{phone}"
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=2,
        )
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to bytes
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        logger.info(f"Generated QR code for user {user_id}")
        return img_bytes
    except Exception as e:
        logger.error(f"Failed to generate QR code: {e}")
        return None


def generate_qr_data_string(user_id: int, full_name: str, phone: str) -> str:
    """Return the data string embedded in QR code."""
    return f"{user_id}|{full_name}|{phone}"


def generate_bot_link_qr(bot_username: str, payload: str = "studio_checkin", out_path: str | None = None) -> io.BytesIO:
    """Generate a QR that opens the bot with a start payload for studio check-in."""
    try:
        link = f"https://t.me/{bot_username}?start={payload}"
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=2,
        )
        qr.add_data(link)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        if out_path:
            with open(out_path, 'wb') as f:
                f.write(img_bytes.getvalue())
        logger.info(f"Generated bot link QR for {bot_username} payload={payload}")
        return img_bytes
    except Exception as e:
        logger.error(f"Failed to generate bot link QR: {e}")
        return None
