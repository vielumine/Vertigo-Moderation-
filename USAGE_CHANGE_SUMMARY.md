# Current Change: Automatic Command Usage Display

## What Changed
Enhanced the global error handler to automatically show command usage when users make mistakes.

## Before
```
User: !warn
Bot: Missing Arguments
     Missing required argument: member
```

## After
```
User: !warn
Bot: ❌ Missing Arguments
     Missing required argument: member
     
     Usage:
     !warn <member> <reason>
```

## Why This Change?
1. **Better UX**: Users instantly know how to fix their mistake
2. **Self-service**: No need to ask for help or check documentation
3. **Consistent**: Works the same for all commands automatically
4. **Smart**: Shows the server's custom prefix if configured

## Technical Details

### File Modified
- `vertigo/main.py`

### Function Updated
- `on_command_error` event handler

### Code Changes

#### Missing Arguments Handler
```python
# Added
prefix = await _get_prefix(bot, ctx.message)
if isinstance(prefix, list):
    prefix = prefix[0]
usage = f"{prefix}{ctx.command.qualified_name} {ctx.command.signature}"

# Enhanced embed
embed = make_embed(
    action="error",
    title="❌ Missing Arguments",
    description=f"{str(error)}\n\n**Usage:**\n```{usage}```",
)
```

#### Bad Arguments Handler
```python
# Same as above but with different title
title="❌ Invalid Arguments"
```

## Error Types Handled

### 1. Missing Required Argument
**When:** User forgets to provide a required parameter

**Example:**
```
!warn             → Missing: member and reason
!mute @User       → Missing: duration
!kick @User       → Missing: reason
```

**Response:**
Shows which argument is missing + full usage

### 2. Bad Argument (Invalid Type)
**When:** User provides wrong type (e.g., text instead of user)

**Example:**
```
!warn notauser spam    → "notauser" is not a valid member
!mute @User 5x spam    → "5x" is not a valid duration
```

**Response:**
Shows what's wrong + full usage

### 3. Command Not Found
**When:** User types non-existent command

**Behavior:** Silently ignored (no error message)

**Reason:** Avoids spam from typos

## Command Signature Format

Discord.py automatically generates signatures from function parameters:

| Type | Display | Example |
|------|---------|---------|
| Required | `<name>` | `<member>` |
| Optional | `[name]` | `[reason]` |
| Variable | `<name...>` | `<users...>` |

## Real Examples

### Example 1: Warn Command
```
Function: warn(member: discord.Member, *, reason: str)
Signature: !warn <member> <reason>

User: !warn
Error: Missing required argument: member
Usage: !warn <member> <reason>
```

### Example 2: Mute Command
```
Function: mute(member: discord.Member, duration: str, *, reason: str = "No reason")
Signature: !mute <member> <duration> [reason]

User: !mute @User
Error: Missing required argument: duration
Usage: !mute <member> <duration> [reason]
```

### Example 3: Custom Prefix
```
Server prefix: ?

User: ?warn
Error: Missing required argument: member
Usage: ?warn <member> <reason>  ← Shows custom prefix!
```

## Benefits

1. **Automatic**: Works for all commands without extra code
2. **Accurate**: Shows exactly what parameters are needed
3. **Dynamic**: Adapts to server's custom prefix
4. **Clear**: Code block makes usage easy to read
5. **Helpful**: Shows both error and solution

## Commands Affected

✅ **ALL COMMANDS** automatically benefit:

- **Moderation:** !warn, !mute, !kick, !ban, !wm, etc.
- **Admin:** !flag, !unflag, !terminate, !lockchannels, etc.
- **Roles:** !role, !removerole, !temprole, etc.
- **Channels:** !lock, !unlock, !hide, !unhide, etc.
- **Misc:** All info and utility commands

## Testing Examples

### Test 1: Missing Member
```bash
Input: !warn
Expected: Shows "Missing required argument: member" + usage
```

### Test 2: Missing Duration
```bash
Input: !mute @User
Expected: Shows "Missing required argument: duration" + usage
```

### Test 3: Invalid User
```bash
Input: !warn invalidtext spam
Expected: Shows "Member 'invalidtext' not found" + usage
```

### Test 4: Custom Prefix
```bash
Server: Prefix set to "?"
Input: ?kick
Expected: Shows "Usage: ?kick <member> <reason>"
```

### Test 5: Optional Parameters
```bash
Function: command(required, [optional])
Input: !command value
Expected: Works (optional parameter not required in usage display)
```

## Implementation Notes

### Error Handler Priority
1. CheckFailure → Silent (permission issues handled elsewhere)
2. MissingRequiredArgument → Show usage
3. BadArgument → Show usage
4. CommandNotFound → Silent
5. Other → Log and show generic error

### Prefix Handling
```python
prefix = await _get_prefix(bot, ctx.message)
if isinstance(prefix, list):
    prefix = prefix[0]  # Get first prefix if multiple
```

### Usage String Construction
```python
usage = f"{prefix}{ctx.command.qualified_name} {ctx.command.signature}"
# Example: "!warn <member> <reason>"
```

## Deployment
- ✅ No database changes
- ✅ No configuration needed
- ✅ Fully backward compatible
- ✅ Works immediately on bot restart
- ✅ No breaking changes

## Future Enhancements
Potential improvements:
- Add command descriptions
- Show examples of correct usage
- Suggest similar commands if command not found
- Multi-language support
