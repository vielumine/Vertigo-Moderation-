# Staff Hierarchy Management System Implementation

## Overview
Implemented a comprehensive admin hierarchy management system with promotion/demotion commands for Vertigo bot.

## Changes Made

### 1. Database Updates (`vertigo/database.py`)
- Added `promotion_channel_id` field to `GuildSettings` dataclass
- Added `promotion_channel_id` column to `guild_settings` table
- Created new `staff_hierarchy` table with `guild_id` and `role_ids` columns
- Added `get_staff_hierarchy()` method to retrieve hierarchy
- Added `set_staff_hierarchy()` method to save hierarchy

### 2. New Hierarchy Cog (`vertigo/cogs/hierarchy.py`)
Created complete hierarchy management system with:

#### Commands:
- `!hierarchy` - Opens interactive admin panel with 4 buttons:
  - **Set Staff Hierarchy** - Modal to input role IDs/mentions (highest to lowest)
  - **Set Promotion Channel** - Modal to configure promotion announcement channel
  - **See Settings** - View current hierarchy and promotion channel configuration
  - **Preview Message** - Show example promotion message format

- `!promote <staff>` - Promotes staff member to next rank
  - Validates staff is in hierarchy
  - Checks if already at highest rank
  - Removes old role, assigns new role
  - Sends promotion message to configured channel
  - Logs to modlog
  - Format: "@User Congratulations for being promoted to RoleName🔥🎉"

- `!demote <staff>` - Demotes staff member to previous rank
  - Validates staff is in hierarchy
  - Checks if already at lowest rank
  - Removes old role, assigns new role
  - Logs to modlog (no public announcement for demotions)

#### Features:
- Full error handling and validation
- Role existence checking
- Permission checks (admin required)
- Interactive UI with modals and buttons
- Celebratory emoji usage (🔥🎉)
- Professional embed design

### 3. Usage Error Message Fix (`vertigo/main.py`)
Changed command usage error format from:
```
❌ Missing Arguments
member is a required argument that is missing.

**Usage:**
!warn <member> <reason>
```

To cleaner format:
```
**Usage**
!warn <member> <reason>
```

Applied to both `MissingRequiredArgument` and `BadArgument` error handlers.

### 4. Info Command Display Fix (`vertigo/cogs/member.py`)
Changed all member info commands to display in channel instead of DM:
- `!myinfo` - Now shows in channel
- `!mywarns` - Now shows in channel
- `!myavatar` - Now shows in channel
- `!mybanner` - Now shows in channel

Removed unused `safe_dm` import.

### 5. Config Updates (`vertigo/config.py`)
Added color mappings for new hierarchy commands:
- `hierarchy`: EMBED_COLOR_GRAY
- `promote`: EMBED_COLOR_GRAY  
- `demote`: EMBED_COLOR_GRAY

### 6. Help System Updates (`vertigo/cogs/misc.py`)
Updated `!adcmd` to include hierarchy management commands:
```
**Staff Hierarchy Management**
!hierarchy - Open hierarchy management panel
!promote <staff> - Promote staff to next rank
!demote <staff> - Demote staff to previous rank
```

### 7. Main Bot Updates (`vertigo/main.py`)
Added `vertigo.cogs.hierarchy` to COGS list for automatic loading.

## Database Schema

### staff_hierarchy table:
```sql
CREATE TABLE IF NOT EXISTS staff_hierarchy (
    guild_id        INTEGER PRIMARY KEY,
    role_ids        TEXT NOT NULL DEFAULT ''
);
```

### guild_settings table addition:
```sql
promotion_channel_id    INTEGER
```

## Usage Examples

### Setup Hierarchy:
1. Admin runs `!hierarchy`
2. Clicks "Set Staff Hierarchy" button
3. Enters role IDs or mentions (one per line, highest to lowest):
   ```
   123456789012345678  (Admin)
   234567890123456789  (Moderator)
   345678901234567890  (Helper)
   ```
4. Clicks "Set Promotion Channel"
5. Enters channel ID or #channel mention

### Promoting Staff:
```
!promote @StaffMember
```
- Removes current role
- Assigns next higher role
- Sends message to promotion channel: "@StaffMember Congratulations for being promoted to Moderator🔥🎉"

### Demoting Staff:
```
!demote @StaffMember
```
- Removes current role
- Assigns next lower role
- Logs action (no public announcement)

## Error Handling

All commands include comprehensive error handling:
- Hierarchy not configured
- User not in hierarchy
- Already at highest/lowest rank
- Role not found (deleted roles)
- Missing permissions
- Invalid role IDs
- Channel not found

## Design Principles

- ✅ Emoji usage for visual appeal
- ✅ Clean, professional embed design
- ✅ Gray color scheme for admin commands
- ✅ Interactive UI with modals
- ✅ Non-destructive (no data loss on errors)
- ✅ Celebratory messages for promotions
- ✅ Discrete handling of demotions
- ✅ Full modlog integration

## Files Modified

1. `/home/engine/project/vertigo/database.py`
2. `/home/engine/project/vertigo/config.py`
3. `/home/engine/project/vertigo/main.py`
4. `/home/engine/project/vertigo/cogs/member.py`
5. `/home/engine/project/vertigo/cogs/misc.py`

## Files Created

1. `/home/engine/project/vertigo/cogs/hierarchy.py`

## Testing Checklist

✅ All files compile without syntax errors
✅ Database schema additions are valid
✅ Config updates are consistent
✅ Main bot loads hierarchy cog
✅ Usage error messages cleaned up
✅ Info commands display in channel
✅ Help system updated

## Notes

- Promotion messages ping the user but show role name without pinging the role
- Demotions are logged but not announced publicly (professional discretion)
- Hierarchy can be reconfigured at any time via the panel
- All database operations use proper async/await patterns
- Role hierarchy is stored as comma-separated role IDs (highest to lowest)
