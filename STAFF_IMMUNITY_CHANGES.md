# Staff Immunity System - Enhanced Error Message

## Summary

Updated the staff immunity error message to show the target user's name in a more user-friendly format.

## Changes Made

### Previous Behavior
When a non-admin staff member tried to moderate another staff member:
- Error message: "Protected Target - That member is staff and cannot be moderated by non-admins."

### New Behavior
When a non-admin staff member tries to moderate another staff member:
- Error message: "❌ Cannot Moderate Staff - @Username is a staff member, I will not do that."
- Shows the username with @ prefix (not a ping, just text)
- More conversational and clear

## How It Works

### Staff Immunity Logic
The `_blocked_by_staff_immunity()` function checks:

1. **Is target a staff member?**
   - Checks if target has any of these roles: staff_role_ids, head_mod_role_ids, senior_mod_role_ids, moderator_role_ids

2. **Is executor an administrator?**
   - Checks if command author has:
     - Discord administrator permission, OR
     - Admin role configured in guild settings

3. **Block or Allow?**
   - If target is staff AND executor is NOT admin → **BLOCKED** (show error)
   - If executor is admin → **ALLOWED** (command proceeds)
   - If target is not staff → **ALLOWED** (command proceeds)

## Commands Protected by Staff Immunity

The following commands check staff immunity before executing:

1. **!warn** - Warn a member
2. **!mute** - Timeout (mute) a user
3. **!kick** - Kick a member
4. **!ban** - Ban a member
5. **!wm** - Warn + mute in a single command
6. **!masskick** - Mass kick multiple users
7. **!massban** - Mass ban multiple users
8. **!massmute** - Mass mute multiple users
9. **!imprison** - Imprison a member (special punishment)

## Example Scenarios

### Scenario 1: Moderator tries to warn another Moderator
```
User: !warn @StaffMember spam
Bot: ❌ Cannot Moderate Staff
     @StaffMember is a staff member, I will not do that.
```

### Scenario 2: Admin warns a Moderator
```
User (Admin): !warn @StaffMember spam
Bot: ⚠️ User Warned
     👤 @StaffMember has been warned.
     📝 Reason: spam
```

### Scenario 3: Moderator warns a regular member
```
User: !warn @RegularUser spam
Bot: ⚠️ User Warned
     👤 @RegularUser has been warned.
     📝 Reason: spam
```

## Implementation Details

### File Modified
- `vertigo/cogs/moderation.py` - Updated `_blocked_by_staff_immunity()` function

### Code Change
```python
# Before
embed = make_embed(action="error", title="Protected Target", description="That member is staff and cannot be moderated by non-admins.")

# After
embed = make_embed(action="error", title="❌ Cannot Moderate Staff", description=f"@{target.name} is a staff member, I will not do that.")
```

### Why `@{target.name}` and not `{target.mention}`?
- `target.mention` would actually ping the user (e.g., `<@123456789>`)
- `@{target.name}` shows the username with @ but doesn't ping (e.g., `@Username`)
- This is more user-friendly and less disruptive

## Benefits

1. **Clearer Error Message**: Users immediately understand why the command failed
2. **Shows Target Name**: Confirms which user is protected
3. **More Conversational**: "I will not do that" is friendlier than "cannot be moderated"
4. **No Unwanted Pings**: Uses username display instead of mention

## Backward Compatibility

✅ **Fully Backward Compatible**
- No database changes
- No configuration changes
- Only changes the error message text
- All existing immunity logic remains the same

## Testing Checklist

- [ ] Non-admin staff tries to !warn another staff member → Shows error
- [ ] Non-admin staff tries to !kick another staff member → Shows error
- [ ] Non-admin staff tries to !ban another staff member → Shows error
- [ ] Admin uses !warn on staff member → Works successfully
- [ ] Admin uses !kick on staff member → Works successfully
- [ ] Error message shows correct username
- [ ] Error message doesn't ping the target user
- [ ] Regular users can still be moderated by staff
