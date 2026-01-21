@echo off
REM Start the Telegram Bot with automatic restart
REM This script keeps the bot running even if it crashes or exits

cd /d "%~dp0"

set SKIP_FLASK=1
set SKIP_SCHEDULING=1

echo ============================================================
echo Starting Fitness Club Telegram Bot
echo ============================================================
echo.
echo The bot will automatically restart if it exits.
echo Press Ctrl+C to stop the bot completely.
echo.
echo ============================================================
echo.

python run_bot_forever.py

pause
