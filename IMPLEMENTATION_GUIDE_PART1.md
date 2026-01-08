# IMPLEMENTATION_GUIDE_PART1 – Setup & Foundation

## 1. Install Prerequisites
- Python 3.10+
- PostgreSQL 15+
- Git

## 2. Create Telegram Bot
- Use @BotFather on Telegram
- Run /newbot and follow instructions
- Save the API token

## 3. Project Structure
- Clone the repository to your computer
- Review the folder structure

## 4. Environment Configuration
- Copy `.env.example` to `.env`
- Fill in your Telegram token and database credentials

## 5. Database Setup
- Use the provided SQL schema to create all tables
- Example: `psql -U postgres -d fitness_club_db -f schema.sql`
- Verify tables are created

## 6. Test Database Connection
- Run `python test_db.py` to verify connection

---

Continue to IMPLEMENTATION_GUIDE_PART2.md for bot logic and handlers.
