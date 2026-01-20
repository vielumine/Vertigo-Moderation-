# Lock/Unlock Channels - Member Role Update

## Summary

Updated `!lockchannels` and `!unlockchannels` commands to use the configured member role instead of @everyone.

## Changes Made

### Previous Behavior
- Commands locked/unlocked channels for @everyone (`ctx.guild.default_role`)
- Would work as long as lock categories were configured

### New Behavior
- Commands now lock/unlock channels for the **member role** configured in `!setup`
- Requires both lock categories AND member role to be configured
- Shows appropriate error messages if member role is not set

## Implementation Details

### lockchannels Command
**New Validation Checks:**
1. Check if lock categories are configured (existing)
2. Check if member role is configured (NEW)
   - Error: "❌ No Member Role - No member role configured. Use !setup to set a member role first."
3. Check if the configured member role still exists (NEW)
   - Error: "❌ Role Not Found - Configured member role no longer exists. Use !setup to update."

**Functionality:**
- Uses `member_role` from guild settings instead of `default_role`
- Sets `send_messages = False` for the member role in all channels within configured categories

### unlockchannels Command
**New Validation Checks:**
1. Check if lock categories are configured (existing)
2. Check if member role is configured (NEW)
   - Error: "❌ No Member Role - No member role configured. Use !setup to set a member role first."
3. Check if the configured member role still exists (NEW)
   - Error: "❌ Role Not Found - Configured member role no longer exists. Use !setup to update."

**Functionality:**
- Uses `member_role` from guild settings instead of `default_role`
- Sets `send_messages = None` (removes override) for the member role in all channels

## Usage Example

### Before (Old System)
```
!lockchannels
→ Locks all configured categories for @everyone
```

### After (New System)
```
# Setup member role first
!setup
→ Set member role to @Member

# Then lock channels
!lockchannels
→ Locks all configured categories for @Member role specifically

# If member role not set
!lockchannels
→ Error: "No member role configured. Use !setup to set a member role first."
```

## Benefits

1. **More Targeted Control**: Lock/unlock specific to member role instead of everyone
2. **Better Permission Management**: Staff/admin roles can still send messages when locked
3. **Clear Error Messages**: Users know exactly what's missing in configuration
4. **Safer Operation**: Won't accidentally lock channels for all roles

## Files Modified

- `vertigo/cogs/admin.py`:
  - Updated `lockchannels` command
  - Updated `unlockchannels` command

## Testing Checklist

- [ ] Test `!lockchannels` with member role configured
  - Verify channels lock for member role only
  - Verify staff can still send messages
- [ ] Test `!unlockchannels` with member role configured
  - Verify channels unlock for member role
- [ ] Test `!lockchannels` without member role configured
  - Should show error message
- [ ] Test `!lockchannels` with deleted member role
  - Should show "role not found" error
- [ ] Test `!unlockchannels` without member role configured
  - Should show error message
- [ ] Verify modlog entries are still created correctly

## Backward Compatibility

⚠️ **Breaking Change**: This is a behavior change from the previous system.

**Migration Notes:**
- Servers that previously used `!lockchannels` must now have a member role configured
- If a member role is already set in `!setup`, the commands will work immediately
- If no member role is set, admins must run `!setup` first

**Recommended Action:**
- Announce the change to server admins
- Remind them to configure member role in `!setup` if not already done
