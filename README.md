# README – Fitness Club Telegram Bot

This project is a fully-featured Telegram bot for fitness club management. It includes member registration, attendance, points, shake requests, admin features, and more.

## System Requirements
- Python 3.10+
- PostgreSQL 15+
- Git

## Quick Start
1. Install Python, PostgreSQL, and Git.
2. Create a Telegram bot with BotFather and get the API token.
3. Clone this repository to your computer.
4. Install dependencies: `pip install -r requirements.txt`
5. Set up your `.env` file with your bot token and database credentials.
6. Initialize the database using the provided schema.
7. Run the bot: `python bot.py`

See IMPLEMENTATION_GUIDE_PART1.md for detailed setup instructions.

---

## Documentation
- IMPLEMENTATION_GUIDE_PART1.md – Setup & Foundation
- IMPLEMENTATION_GUIDE_PART2.md – Bot Logic & Handlers
- IMPLEMENTATION_GUIDE_PART3.md – Admin & Deployment
- QUICK_REFERENCE.md – Commands & Troubleshooting

---

## License
Free for fitness clubs. See documentation for details.

---

# Telegram Invoice Generator (Node.js + Telegraf + Puppeteer)

Professional invoice PDF generator for Telegram bot workflows.

## Features
- Modern TAX INVOICE / INVOICE PDF layout
- Matching PAYMENT RECEIPT PDF layout with PAID watermark
- HTML + CSS template rendered via Puppeteer
- Telegram bot commands: /start, /invoice, /receipt
- JSON schema validation for invoice and receipt payloads
- Clean logs and safe temp file cleanup

## Project Structure
```
/src
	bot.js
	config.js
	invoice/
		invoiceTemplate.html
		invoiceStyles.css
		invoiceGenerator.js
		sampleInvoiceData.json
		schema.js
	utils/
		money.js
		validate.js
		logger.js
/tmp (generated at runtime)
package.json
.env.example
README.md
```

## Setup

1) Install dependencies:
```
npm i
```

2) Create .env file from .env.example:
```
cp .env.example .env
```

3) Set your Telegram Bot token in .env:
```
BOT_TOKEN=your_token_here
```

## Run
```
node src/bot.js
```

## Test
- Open Telegram and send /start
- Send /invoice to receive a sample invoice PDF
- Send /receipt to receive a sample payment receipt PDF

## Custom Invoice Flow (Later-Ready)
The /invoice_json command is a stub for admin JSON payloads. You can connect it to:
- Admin dashboard
- JSON payload ingestion
- A form or web UI

## Invoice & Receipt Data Model
See src/invoice/schema.js and src/invoice/sampleInvoiceData.json.

## Notes
- Logo is downloaded at runtime and embedded as base64 to ensure PDF rendering.
- Page format: A4 with print background enabled.
- Clean temporary files are deleted after sending to Telegram.
