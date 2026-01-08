# 🏋️ Fitness Club Telegram Bot – Quick Start Guide

This guide will help you set up and run your own Fitness Club Telegram Bot, tailored for club management, attendance, points, and more.

---

## 1. Prerequisites
- Python 3.10+
- PostgreSQL 15+
- Git
- Telegram account

## 2. Create Your Telegram Bot
1. Open Telegram and search for [@BotFather](https://t.me/BotFather).
2. Send `/newbot` and follow the prompts to create your bot.
3. Save the API token provided by BotFather.

## 3. Clone the Project
```sh
git clone <your-repo-url>
cd <project-folder>
```

## 4. Install Dependencies
```sh
pip install -r requirements.txt
```

## 5. Configure Environment
1. Copy `.env.example` to `.env` (or create `.env`).
2. Fill in your Telegram bot token and database credentials:
   - `TELEGRAM_TOKEN=...`
   - `DB_HOST=...`
   - `DB_USER=...`
   - `DB_PASSWORD=...`
   - `DB_NAME=fitness_club_db`

## 6. Initialize the Database
- Run the provided SQL schema (see documentation) to create all tables.
- Example (psql):
  ```sh
  psql -U postgres -d fitness_club_db -f schema.sql
  ```

## 7. Run the Bot
```sh
python bot.py
```

## 8. Test the Bot
- Start a chat with your bot on Telegram.
- Try `/start` and follow the registration prompts.
- Test menu buttons, attendance, shake requests, and admin features.

## 9. Deployment
- For production, see deployment options in the documentation:
  - Railway (easy)
  - Heroku
  - VPS (DigitalOcean, AWS, etc.)
- Set up environment variables and database for production.

## 10. Customization
- Edit `config.py` for points, fees, and other settings.
- Modify handlers for custom workflows and messages.
- Extend the database for new features.

---

## Useful Resources
- [README.md] – Project overview & FAQ
- [IMPLEMENTATION_GUIDE_PART1.md] – Setup & database
- [IMPLEMENTATION_GUIDE_PART2.md] – Bot logic & handlers
- [IMPLEMENTATION_GUIDE_PART3.md] – Admin & deployment
- [QUICK_REFERENCE.md] – Commands & troubleshooting

---

## Troubleshooting
- Check logs for errors: `logs/fitness_bot.log`
- Verify database connection and credentials
- Review environment variables
- See documentation for common issues

---

**Enjoy automating your fitness club!** 💪
