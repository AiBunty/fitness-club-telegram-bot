import os
from dotenv import load_dotenv
from src.utils.qr_code import generate_bot_link_qr

load_dotenv()
BOT_USERNAME = os.getenv("BOT_USERNAME", "your_bot_username_here")
PAYLOAD = "studio_checkin"
OUTPUT = "studio_checkin_qr.png"

def main():
    qr_bytes = generate_bot_link_qr(BOT_USERNAME, PAYLOAD, out_path=OUTPUT)
    if qr_bytes:
        print(f"✅ Generated QR for https://t.me/{BOT_USERNAME}?start={PAYLOAD} -> {OUTPUT}")
    else:
        print("❌ Failed to generate QR")

if __name__ == "__main__":
    main()
