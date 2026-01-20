# Staff Flag System Update - 3 Strikes to 5 Strikes

## Summary

Updated the staff flag system from 3 strikes to 5 strikes before auto-termination.

## Changes Made

### 1. Configuration (`vertigo/config.py`)
- **Added** `MAX_STAFF_FLAGS = 5` constant to centralize the strike limit

### 2. Admin Commands (`vertigo/cogs/admin.py`)

#### Flag Command (`!flag`)
- Updated strike display from "X/3" to "X/5"
- Changed auto-termination threshold from `>= 3` to `>= config.MAX_STAFF_FLAGS`
- Updated embed title to show "⛔ Auto-Termination - 5 strikes reached" when limit reached
- Added warning field when auto-termination is triggered
- Updated DM notification to mention "5 flags" instead of "3 flags"
- Fixed missing import: Added `add_loading_reaction` to imports from helpers

#### Unflag Command (`!unflag`)
- Updated to show strike count after removal
- Displays "Updated Strikes: X/5" in the embed

#### Stafflist Command (`!stafflist`)
- **Enhanced** to display strike counts for each staff member
- Added color-coded emoji system:
  - No flags: No emoji
  - 1-2 strikes: ✅ Green status
  - 3 strikes: ⚠️ Yellow warning
  - 4 strikes: 🟠 Orange critical
  - 5+ strikes: 🔴 Red (auto-terminated)
- Format: `👤 Moderator Name (ID) - {emoji} 🚩 Flags: X/5`

### 3. Help Documentation (`vertigo/cogs/misc.py`)

#### Admin Commands Help (`!adcmd`)
- Updated to prominently feature the 5-strike system
- Added section header: "Staff Flagging (5-Strike System)"
- Added warning: "⚠️ **5 flags = auto-termination**"
- Added information about flag expiration
- Improved formatting with better organization

## Backward Compatibility

✅ **No database migration required**
- Existing flags in the database are unaffected
- Staff members with 3-4 existing flags will not be auto-terminated until reaching 5
- All existing data remains valid

## Testing Recommendations

1. Test flagging a staff member and verify "X/5" display
2. Test flagging a staff member 5 times to trigger auto-termination
3. Verify auto-termination includes:
   - Role removal
   - 1-week timeout
   - DM to staff member
   - DM to admin who triggered it
   - Modlog entry
4. Test unflag command and verify updated strike count display
5. Test stafflist command with staff members at different strike levels
6. Verify color-coded emojis appear correctly in stafflist
7. Test adcmd help command displays updated documentation

## Files Modified

- `vertigo/config.py` - Added MAX_STAFF_FLAGS constant
- `vertigo/cogs/admin.py` - Updated flag, unflag, and stafflist commands
- `vertigo/cogs/misc.py` - Updated adcmd help documentation

## No Changes Required

- `vertigo/database.py` - Database schema and queries remain unchanged
- `vertigo/cogs/background.py` - Flag expiration logic remains unchanged
- Flag expiration duration is still controlled by guild settings (default 30 days)
