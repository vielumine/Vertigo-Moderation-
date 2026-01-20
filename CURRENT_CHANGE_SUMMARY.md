# Current Change: Staff Immunity Error Message Enhancement

## What Changed
Updated the error message shown when a non-admin staff member tries to use moderation commands on another staff member.

## Before
```
Error Title: Protected Target
Error Message: That member is staff and cannot be moderated by non-admins.
```

## After
```
Error Title: ❌ Cannot Moderate Staff
Error Message: @Username is a staff member, I will not do that.
```

## Why This Change?
1. **More user-friendly**: Conversational tone ("I will not do that")
2. **Shows who is protected**: Displays the username clearly
3. **No unwanted pings**: Uses `@Username` format instead of actual mention
4. **Better UX**: More descriptive and helpful

## Technical Details

### File Modified
- `vertigo/cogs/moderation.py`

### Function Updated
- `_blocked_by_staff_immunity(ctx, target)`

### Code Change
```python
# Old
embed = make_embed(
    action="error", 
    title="Protected Target", 
    description="That member is staff and cannot be moderated by non-admins."
)

# New
embed = make_embed(
    action="error", 
    title="❌ Cannot Moderate Staff", 
    description=f"@{target.name} is a staff member, I will not do that."
)
```

## How Staff Immunity Works

### The Protection Rule
- **Staff members CANNOT moderate other staff members**
- **Admins CAN moderate anyone, including staff**

### Who is considered "Staff"?
Anyone with these roles:
- staff_role_ids
- moderator_role_ids
- senior_mod_role_ids
- head_mod_role_ids

### Who is considered "Admin"?
Anyone with:
- Discord administrator permission, OR
- Admin role configured in guild settings (admin_role_ids)

## Example Scenarios

### 1. Moderator tries to warn another Moderator ❌
```
Moderator: !warn @OtherMod spam
Bot: ❌ Cannot Moderate Staff
     @OtherMod is a staff member, I will not do that.
```

### 2. Admin warns a Moderator ✅
```
Admin: !warn @Moderator spam
Bot: ⚠️ User Warned
     👤 @Moderator has been warned.
```

### 3. Moderator warns regular user ✅
```
Moderator: !warn @User spam
Bot: ⚠️ User Warned
     👤 @User has been warned.
```

## Commands Protected

All these commands check staff immunity:
- ✅ !warn - Warn a member
- ✅ !mute - Timeout a member
- ✅ !kick - Kick a member
- ✅ !ban - Ban a member
- ✅ !wm - Warn and mute combined
- ✅ !masskick - Mass kick multiple users
- ✅ !massban - Mass ban multiple users
- ✅ !massmute - Mass mute multiple users
- ✅ !imprison - Imprison a member

## Testing
- [x] Syntax validation passed
- [ ] Test non-admin staff warning another staff member
- [ ] Verify error message shows username correctly
- [ ] Verify username doesn't ping target
- [ ] Test admin can still moderate staff
- [ ] Test regular users can still be moderated

## Deployment
- ✅ No database changes required
- ✅ No configuration changes needed
- ✅ Fully backward compatible
- ✅ Takes effect immediately on bot restart
