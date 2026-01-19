# Weight Edit Flow Test Guide

**Purpose**: Test that the weight edit flow now properly sends messages to the user after they enter an edited weight value.

## Architecture Fix Applied

The weight edit flow now uses a **ConversationHandler entry_point** instead of a generic callback handler:

1. When user clicks "Edit Weight" button → `edit_weight` callback triggers
2. `weight_handler` ConversationHandler entry_point with pattern `^edit_weight$` **captures this callback** (not the generic handler)
3. `cmd_weight()` is called with the `edit_weight` callback
4. `cmd_weight()` sends "Edit Your Weight" prompt and returns `WEIGHT_VALUE` state
5. User sends weight (e.g., "84")
6. `get_weight_input()` handler processes the message and sends confirmation
7. Flow ends with `ConversationHandler.END`

### Handler Flow Diagram

```
User clicks "Edit Weight" button
  ↓
edit_weight callback generated
  ↓
weight_handler entry_points matches pattern "^edit_weight$"
  ↓
cmd_weight(update.callback_query) called
  ↓
Sends "Edit Your Weight" prompt + keyboard
Returns WEIGHT_VALUE state
  ↓
User enters "84" (or any valid weight)
  ↓
get_weight_input(update.message) processes input
  ↓
Validates weight (30-300 kg range)
Logs weight to database
Sends confirmation: "✅ Weight Logged Successfully!"
Returns ConversationHandler.END
```

## Test Case 1: Weight Edit with Valid Input

### Prerequisites
- Bot is running
- User has already logged weight today
- User is not blacklisted or unapproved

### Steps
1. Send `/weight` command (or click menu button)
2. Should see: "✅ *Weight Already Logged Today*" with options to Edit or "Come Tomorrow"
3. Click "✏️ Edit Weight" button
4. **Expected**: See "✏️ *Edit Your Weight*" message with current weight and input prompt
5. Enter a valid weight (e.g., `76.5` or `84`)
6. **Expected**: See "✅ *Weight Logged Successfully!*" confirmation with:
   - New weight logged
   - Weight change from yesterday (if available)
   - Points awarded: +10

### Success Criteria
✅ All messages appear in correct order
✅ No errors in logs
✅ Confirmation message appears with updated weight

## Test Case 2: Weight Edit with Invalid Input

### Steps
1. Complete Test Case 1 steps 1-4
2. Enter invalid weight:
   - Non-numeric: `abc` → Should get "Invalid input for weight"
   - Too low: `20` → Should get "Invalid weight. Please enter 30-300 kg"
   - Too high: `400` → Should get "Invalid weight. Please enter 30-300 kg"
3. **Expected**: Error message appears
4. Enter valid weight: `75.5`
5. **Expected**: Confirmation message appears

### Success Criteria
✅ Validation works correctly
✅ User can retry after error
✅ Final confirmation appears

## Test Case 3: Weight Edit with Cancel

### Steps
1. Complete Test Case 1 steps 1-4
2. Click "❌ Cancel" button
3. **Expected**: See "❌ Cancelled." message and exit flow

### Success Criteria
✅ Cancel button works
✅ No weight is logged
✅ Flow ends properly

## Debugging Checklist

If weight edit is still not working:

1. **Check bot logs for errors**
   ```
   Look for:
   - [WEIGHT_EDIT] User {user_id} started editing weight
   - [WEIGHT_INPUT] User {user_id} entered weight: {weight}
   - [WEIGHT_LOGGED] Weight logged successfully
   ```

2. **Verify handler registration**
   - In `src/bot.py`, line 311-314: weight_handler should have `CallbackQueryHandler(cmd_weight, pattern="^edit_weight$")`
   - In `src/bot.py`, line 379: `application.add_handler(weight_handler)` should be registered

3. **Verify pattern exclusion**
   - In `src/bot.py`, line 496: Generic handler pattern should have `|edit_weight|cancel` in negative lookahead
   - Pattern: `^(?!pay_method|admin_approve|admin_reject|sub_|admin_sub_|edit_weight|cancel)`

4. **Check database**
   - Weight should be logged: `SELECT * FROM activity_log WHERE user_id = {user_id} AND DATE(activity_date) = CURRENT_DATE ORDER BY activity_date DESC LIMIT 1;`

5. **Check user_data flag**
   - cmd_weight sets: `context.user_data['weight_edit_mode'] = True`
   - get_weight_input clears: `context.user_data.pop('weight_edit_mode', None)`

## Common Issues & Solutions

### Issue: "Edit Your Weight" prompt appears but no response to user's input
**Solution**: Check if edit_weight callback is being caught by generic handler instead of ConversationHandler
- Verify line 496 pattern includes `|edit_weight|`
- Verify weight_handler entry_point includes edit_weight pattern

### Issue: Confirmation message shows but weight not actually logged
**Solution**: Check database connection
- Run: `python check_users.py`
- Verify database is accessible

### Issue: User gets error "number 1-5" message
**Solution**: This indicates water logging handler is being triggered instead of weight handler
- Indicates handler registration order issue
- Check that weight_handler is registered before water_handler (line 379-380 in bot.py)

## Expected Log Output

When weight edit succeeds, you should see:

```
[WEIGHT_EDIT] User 123456789 started editing weight. Current: 75kg
[WEIGHT_VALUE] User 123456789 entering WEIGHT_VALUE state
[WEIGHT_INPUT] User 123456789 entered weight: 76.5
[WEIGHT_LOGGED] Weight logged: user_id=123456789, weight=76.5, points=+10
```

## Post-Test Verification

After successful weight edit:

1. **Check database**:
   ```sql
   SELECT * FROM activity_log 
   WHERE user_id = {user_id} 
   AND activity_type = 'weight' 
   AND DATE(activity_date) = CURRENT_DATE 
   LIMIT 1;
   ```
   Should show most recent weight entry

2. **Check user points**:
   ```sql
   SELECT user_id, total_points FROM users WHERE user_id = {user_id};
   ```
   Points should have +10 from weight logging

3. **Verify next day**: Tomorrow, weight logging should start fresh (no "Already Logged" message)

---

**Status**: Ready for Testing
**Last Updated**: Current Session
**Next Action**: Run bot and execute test cases above
