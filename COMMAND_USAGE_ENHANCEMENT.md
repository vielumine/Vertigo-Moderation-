# Command Usage Enhancement - Automatic Usage Display

## Summary

Enhanced the error handling system to automatically show command usage when commands are used incorrectly.

## Changes Made

### File Modified
- `vertigo/main.py` - Enhanced `on_command_error` event handler

### What Changed

#### Before
When a user used a command incorrectly:
```
❌ Missing Arguments
Missing required argument: member
```

#### After
When a user uses a command incorrectly:
```
❌ Missing Arguments
Missing required argument: member

Usage:
!warn <member> <reason>
```

## Types of Errors Handled

### 1. Missing Arguments
**Trigger:** User doesn't provide all required parameters

**Example:**
```
User: !warn
Bot: ❌ Missing Arguments
     Missing required argument: member

     Usage:
     !warn <member> <reason>
```

### 2. Invalid/Bad Arguments
**Trigger:** User provides wrong type of argument (e.g., text instead of user mention)

**Example:**
```
User: !warn notauser spam
Bot: ❌ Invalid Arguments
     Member "notauser" not found.

     Usage:
     !warn <member> <reason>
```

### 3. Command Not Found
**Trigger:** User types a command that doesn't exist

**Behavior:** Silently ignored (no error message shown)

## How It Works

### Error Handler Flow

1. **Check error type**
   - If CheckFailure (permission issues) → Return silently (handled by permission system)
   - If MissingRequiredArgument → Show usage
   - If BadArgument → Show usage
   - If CommandNotFound → Return silently
   - Otherwise → Log error and show generic error message

2. **Get prefix**
   - Dynamically fetches the server's configured prefix
   - Supports custom prefixes per server

3. **Build usage string**
   - Uses command signature from Discord.py
   - Format: `{prefix}{command_name} {signature}`
   - Example: `!warn <member> <reason>`

4. **Show enhanced error**
   - Title indicates error type
   - Description shows what went wrong
   - Usage block shows correct format in code block

## Command Signature Format

Discord.py automatically generates signatures:

| Parameter Type | Display Format | Example |
|---------------|----------------|---------|
| Required | `<parameter>` | `<member>` |
| Optional | `[parameter]` | `[reason]` |
| Variable length | `<parameter...>` | `<reason...>` |
| Keyword-only | `<keyword=value>` | `<duration=1h>` |

## Examples by Command Type

### Simple Command
```
Command: !kick <member> <reason>

Wrong Usage: !kick
Error: Missing required argument: member
Usage: !kick <member> <reason>
```

### Command with Optional Parameters
```
Command: !mute <member> <duration> [reason]

Wrong Usage: !mute @User
Error: Missing required argument: duration
Usage: !mute <member> <duration> [reason]
```

### Command with Multiple Parameters
```
Command: !flag <member> <reason>

Wrong Usage: !flag @User
Error: Missing required argument: reason
Usage: !flag <member> <reason>
```

### Command with Variable Arguments
```
Command: !masskick <users> <reason>

Wrong Usage: !masskick
Error: Missing required argument: users
Usage: !masskick <users> <reason>
```

## Benefits

1. **User-Friendly**: Clear guidance on how to use commands correctly
2. **Self-Service**: Users can see the correct format without asking
3. **Reduces Confusion**: Shows exactly what parameters are needed
4. **Dynamic**: Automatically works with server's custom prefix
5. **Consistent**: All commands use the same error format

## Implementation Details

### Error Types Handled

```python
commands.MissingRequiredArgument  # Missing parameters
commands.BadArgument              # Wrong type/format
commands.CommandNotFound          # Non-existent command
commands.CheckFailure             # Permission issues (silent)
```

### Usage String Construction

```python
prefix = await _get_prefix(bot, ctx.message)
if isinstance(prefix, list):
    prefix = prefix[0]
usage = f"{prefix}{ctx.command.qualified_name} {ctx.command.signature}"
```

### Embed Format

```python
embed = make_embed(
    action="error",
    title="❌ Missing Arguments",  # or "❌ Invalid Arguments"
    description=f"{str(error)}\n\n**Usage:**\n```{usage}```",
)
```

## Testing Checklist

- [ ] Test command with missing arguments
- [ ] Verify usage message shows correct format
- [ ] Test with wrong argument type (e.g., text instead of user)
- [ ] Verify usage shows with custom prefix
- [ ] Test multiple commands to ensure consistency
- [ ] Verify permission errors don't show usage
- [ ] Test commands with optional parameters
- [ ] Test commands with variable arguments

## Example Test Scenarios

### Test 1: Missing Member Parameter
```
Input: !warn
Expected: Shows usage: !warn <member> <reason>
```

### Test 2: Missing Duration Parameter
```
Input: !mute @User
Expected: Shows usage: !mute <member> <duration> [reason]
```

### Test 3: Invalid User Format
```
Input: !kick invaliduser spam
Expected: Shows usage: !kick <member> <reason>
```

### Test 4: Custom Prefix
```
Server prefix: ?
Input: ?warn
Expected: Shows usage: ?warn <member> <reason>
```

## Backward Compatibility

✅ **Fully Backward Compatible**
- Enhanced existing error handler
- No breaking changes
- Improves user experience without changing functionality
- Works with all existing commands automatically

## Future Enhancements

Potential improvements:
1. Add command description in usage message
2. Show examples of correct usage
3. Suggest similar commands when command not found
4. Add multi-language support for error messages
