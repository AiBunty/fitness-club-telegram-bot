# QR Attendance System - Deployment Checklist ✅

## Pre-Deployment Verification

### 1. Files Created (8 new files)
- [x] `src/web/__init__.py` - Web package init
- [x] `src/web/app.py` - Flask app with endpoints (500+ lines)
- [x] `src/utils/attendance_tokens.py` - Token manager (140 lines)
- [x] `src/utils/geofence.py` - Geofence validator (65 lines)
- [x] `src/utils/attendance_eligibility.py` - Eligibility checker (70 lines)
- [x] `src/utils/admin_notifications.py` - Admin notifier (180 lines)
- [x] `migrate_qr_attendance.py` - Database migration (50 lines)
- [x] `QR_ATTENDANCE_IMPLEMENTATION.md` - Full documentation
- [x] `QR_ATTENDANCE_QUICKSTART.md` - Setup guide

### 2. Files Modified (4 files)
- [x] `src/bot.py` - Added Flask integration + 3 command imports + 3 handlers
- [x] `src/handlers/admin_handlers.py` - Added 3 admin commands (300+ lines)
- [x] `schema.sql` - Added `attendance_overrides` table + indexes
- [x] `requirements.txt` - Added 4 new dependencies

## Setup Steps

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```
**Expected output**: Installs Flask, waitress, qrcode, reportlab

**Verification**:
```bash
pip list | grep -E "Flask|waitress|qrcode|reportlab"
# Should show:
# Flask==3.0.0
# waitress==2.1.2
# qrcode (pil)
# reportlab==4.0.7
```

### Step 2: Apply Database Migration
```bash
python migrate_qr_attendance.py
```
**Expected output**: `✅ Migration successful: attendance_overrides table created`

**Verification**:
```bash
psql -U postgres -d fitness_bot -c "SELECT * FROM attendance_overrides LIMIT 1;"
# Should return empty table (no error)
```

### Step 3: Update Environment Variables (if needed)
Check `src/config.py`:
```python
TELEGRAM_BOT_TOKEN = "your_token"
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "fitness_bot"
DB_USER = "postgres"
DB_PASSWORD = "password"
```

### Step 4: Start Bot with Flask
```bash
python start_bot.py
```

**Expected startup logs**:
```
Testing database connection...
Database OK! Starting bot...
Telegram app reference set for admin notifications
Flask app created for QR attendance
Starting Flask web server on :5000...
Flask thread started
Bot starting...
Running polling with allowed_updates: ['message', 'callback_query']
```

## Post-Deployment Verification

### Test 1: Flask Health Check
```bash
curl http://localhost:5000/health
```
**Expected response**:
```json
{"status":"ok","timestamp":"2026-01-18T12:00:00.000000"}
```

### Test 2: QR Page Load
Open in browser: `http://localhost:5000/qr/attendance?user_id=123456`

**Expected result**:
- Page loads with "🏋️ Gym Check-In" heading
- Location info visible: "19.996429, 73.754282"
- "📍 Start Check-In with GPS" button present
- GPS permission request works on click

### Test 3: Token Generation
```bash
curl -X POST http://localhost:5000/api/token/generate \
  -H "Content-Type: application/json" \
  -d '{"user_id": 123456}'
```

**Expected response**:
```json
{"success":true,"token":"abc123def456...","expires_in":120}
```

### Test 4: Attendance Verification (Success)
```bash
# First, generate token
TOKEN=$(curl -s -X POST http://localhost:5000/api/token/generate \
  -H "Content-Type: application/json" \
  -d '{"user_id": 123456}' | jq -r '.token')

# Then verify with gym coordinates
curl -X POST http://localhost:5000/api/attendance/verify \
  -H "Content-Type: application/json" \
  -d "{
    \"token\": \"$TOKEN\",
    \"user_lat\": 19.996429,
    \"user_lon\": 73.754282
  }"
```

**Expected response**:
```json
{"success":true,"distance_m":0.0,"message":"✅ Check-in successful! (0m from gym)"}
```

### Test 5: Attendance Verification (Outside Geofence)
```bash
TOKEN=$(curl -s -X POST http://localhost:5000/api/token/generate \
  -H "Content-Type: application/json" \
  -d '{"user_id": 123456}' | jq -r '.token')

curl -X POST http://localhost:5000/api/attendance/verify \
  -H "Content-Type: application/json" \
  -d "{
    \"token\": \"$TOKEN\",
    \"user_lat\": 20.0,
    \"user_lon\": 73.5
  }"
```

**Expected response**:
```json
{"success":false,"reason":"OUTSIDE_GEOFENCE","distance_m":40.5}
```

### Test 6: Token Expiry
```bash
# Generate token
TOKEN=$(curl -s -X POST http://localhost:5000/api/token/generate \
  -H "Content-Type: application/json" \
  -d '{"user_id": 123456}' | jq -r '.token')

# Wait 121 seconds
sleep 121

# Try to use expired token
curl -X POST http://localhost:5000/api/attendance/verify \
  -H "Content-Type: application/json" \
  -d "{
    \"token\": \"$TOKEN\",
    \"user_lat\": 19.996429,
    \"user_lon\": 73.754282
  }"
```

**Expected response**:
```json
{"success":false,"reason":"TOKEN_EXPIRED","distance_m":null}
```

### Test 7: Admin Commands
In Telegram (as admin):
```
/qr_attendance_link 123456
```
**Expected response**:
```
🔗 QR Attendance Link

Send this link to user 123456:

http://your-domain:5000/qr/attendance?user_id=123456

User scans QR code, grants GPS permission, marks attendance
```

### Test 8: Admin Override
In Telegram (as admin):
```
/override_attendance 123456 Location issue
```

**Expected response**:
```
✅ Attendance Overridden

👤 Member: [Name]
📝 Reason: Location issue
🆔 Request ID: [id]
```

### Test 9: QR Code Download
In Telegram (as admin):
```
/download_qr_code
```

**Expected result**:
- PDF file downloaded: `gym_attendance_qr.pdf`
- A4 size with gym location and QR code
- Ready to print

### Test 10: Admin Notifications
1. As user: Access `/qr/attendance?user_id=123456` and mark attendance
2. Admin should receive message:
```
✅ Attendance Marked

👤 User: [User Name]
📍 Distance: 5.2m from gym
⏰ Time: 2026-01-18T12:00:00
```

## Database Verification

### Check attendance_overrides table
```bash
psql -U postgres -d fitness_bot << EOF
\dt attendance_overrides
SELECT column_name, data_type FROM information_schema.columns 
WHERE table_name = 'attendance_overrides' ORDER BY ordinal_position;
\di *attendance_overrides*
EOF
```

**Expected output**:
```
                 Table "public.attendance_overrides"
   Column   |            Type             | Collation | Nullable
-----------+-----------------------------+-----------+----------
 override_id | integer                    |           | not null
 user_id   | bigint                      |           | not null
 admin_id  | bigint                      |           | not null
 reason    | text                        |           | not null
 created_at| timestamp without time zone |           | not null
```

### Test override logging
```bash
# In Telegram as admin
/override_attendance 123456 Test reason

# Then check database
psql -U postgres -d fitness_bot -c "SELECT * FROM attendance_overrides ORDER BY created_at DESC LIMIT 1;"
```

**Expected**: Row with user_id=123456, reason='Test reason', timestamp

## Troubleshooting

### Issue: "Address already in use" (port 5000)
```bash
# Find process using port 5000
lsof -i :5000

# Kill it
kill -9 <PID>

# Or use different port (modify app.py if needed)
```

### Issue: Flask not starting
**Check logs**:
```bash
tail -f logs/bot.log | grep -i flask
```

**Common causes**:
- Missing dependencies: `pip install -r requirements.txt`
- Port 5000 in use: Use lsof as above
- Import error: Check all Python syntax

### Issue: Database migration failed
```bash
# Check if PostgreSQL is running
psql -U postgres -c "SELECT version();"

# Check if fitness_bot database exists
psql -U postgres -c "\l" | grep fitness_bot

# Re-run migration
python migrate_qr_attendance.py
```

### Issue: Token always invalid
**Check**:
1. System time correct: `date`
2. Token TTL: 120 seconds (must use within this time)
3. Token format: Should be 32-character hex
4. Check logs for token store errors: `grep -i token logs/bot.log`

### Issue: Geofence not working
**Check**:
1. Gym coordinates: 19.996429, 73.754282
2. GPS accuracy: Response shows actual distance
3. Radius: Default 10m (check in Flask app if modified)
4. Test with known distance:
```bash
# 40m away - should fail
curl -X POST http://localhost:5000/api/attendance/verify \
  -H "Content-Type: application/json" \
  -d "{\"token\": \"...\", \"user_lat\": 20.0, \"user_lon\": 73.5}"
```

### Issue: Admin notifications not received
**Check**:
1. Admin ID in database: `SELECT user_id FROM users WHERE role='admin';`
2. Telegram bot can send messages: Check bot privacy settings
3. Job queue running: `grep -i "job_queue\|notification" logs/bot.log`

## Production Checklist

Before going live:
- [ ] All 10 tests passing
- [ ] Database migration completed
- [ ] Dependencies installed
- [ ] Bot starting without errors
- [ ] Flask accessible on port 5000
- [ ] Admin commands working
- [ ] Notifications being sent
- [ ] QR PDF downloads working
- [ ] Logs being written
- [ ] Backup of database created

## Rollback Plan

If issues arise:
1. **Stop bot**: `Ctrl+C` (or kill process)
2. **Revert database** (if needed):
   ```bash
   psql -U postgres -d fitness_bot -c "DROP TABLE IF EXISTS attendance_overrides CASCADE;"
   ```
3. **Revert code** (if needed):
   ```bash
   git checkout HEAD -- src/bot.py src/handlers/admin_handlers.py requirements.txt schema.sql
   rm -rf src/web/
   rm -f src/utils/attendance_tokens.py src/utils/geofence.py src/utils/attendance_eligibility.py src/utils/admin_notifications.py
   ```
4. **Restart bot**:
   ```bash
   pip install -r requirements.txt
   python start_bot.py
   ```

## Monitoring

### Key Metrics to Watch
1. **Token generation rate** - Should be ~1 token per user check-in
2. **Token expiry rate** - Should be low (users complete check-in within 120s)
3. **Geofence rejection rate** - Monitor for GPS accuracy issues
4. **Admin notification lag** - Should be <1 second
5. **Flask uptime** - Should be 100% (restart with bot)

### Log Monitoring
```bash
# Watch for errors
tail -f logs/bot.log | grep -i error

# Watch for QR attendance activities
tail -f logs/bot.log | grep -i "qr\|attendance\|geofence"

# Watch Flask startup
tail -f logs/bot.log | grep -i "flask\|port 5000"
```

## Support Contacts

For issues:
1. Check logs: `tail -f logs/bot.log`
2. Verify endpoints: `curl http://localhost:5000/health`
3. Test database: `psql -U postgres -d fitness_bot -c "SELECT COUNT(*) FROM users;"`
4. Review implementation docs: `QR_ATTENDANCE_IMPLEMENTATION.md`

---

**Deployment Date**: [DATE]
**Deployed By**: [YOUR NAME]
**Status**: ✅ READY
**Last Updated**: 2026-01-18
