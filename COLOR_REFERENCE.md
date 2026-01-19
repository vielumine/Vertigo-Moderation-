# Vertigo Bot Color Reference

## Color Values

| Color Name | Hex Value | Decimal Value | Usage |
|------------|-----------|---------------|-------|
| **RED** | `0xFF0000` | `16711680` | Main action color (warns, kicks, mutes) |
| **DARK_RED** | `0xCC0000` | `13369344` | Critical actions (bans, terminations) |
| **GRAY** | `0x808080` | `8421504` | Info/secondary (info commands, settings) |
| **LIGHT_GRAY** | `0xA9A9A9` | `11119017` | Light accents for secondary info |

## Command Categorization

### 🔴 Red Embeds (Main Actions)
Commands that involve standard moderation actions with consequences:
- `!warn` - Warn a user
- `!mute` - Mute a user
- `!kick` - Kick a user
- `!wm` - Warn and mute
- `!massmute` - Mass mute users
- `!flag` - Flag a user
- `!massstrike` - Mass strike users

### 🔴 Dark Red Embeds (Critical Actions)
Commands with severe or permanent consequences:
- `!ban` - Ban a user
- `!masskick` - Mass kick users
- `!massban` - Mass ban users
- `!imprison` - Imprison a user
- `!terminate` - Terminate/permanently ban

### ⚫ Gray Embeds (Information/Neutral)

**Info Commands:**
- `!modlogs` - View moderation logs
- `!warnings` - View warnings
- `!userinfo` - User information
- `!serverinfo` - Server information
- `!roleperms` - Role permissions
- `!stafflist` - Staff list
- `!myinfo` - My information
- `!mywarns` - My warnings
- `!checkdur` - Check duration
- `!wasbanned` - Check if user was banned
- `!ping` - Ping command
- `!members` - Member count
- `!checkavatar` - Check avatar
- `!checkbanner` - Check banner

**Settings Commands:**
- `!setup` - Show setup/settings
- `!adminsetup` - Admin setup/settings

**Neutral Actions:**
- `!role` - Assign role
- `!removerole` - Remove role
- `!unmute` - Unmute user
- `!unban` - Unban user
- `!unlock` - Unlock channel
- `!unhide` - Unhide channel
- `!release` - Release user
- `!delwarn` - Delete warning

### Error & Success Messages
- **Errors:** RED (`0xFF0000`)
- **Success:** GRAY (`0x808080`)

## Implementation Example

```python
import discord
from config import get_embed_color, EMBED_COLOR_RED, EMBED_COLOR_GRAY

# Method 1: Using the helper function
@commands.command()
async def warn(ctx, member: discord.Member, *, reason: str):
    embed = discord.Embed(
        title="⚠️ User Warned",
        description=f"{member.mention} has been warned.\n**Reason:** {reason}",
        color=get_embed_color('warn')
    )
    await ctx.send(embed=embed)

# Method 2: Using constants directly
@commands.command()
async def userinfo(ctx, member: discord.Member):
    embed = discord.Embed(
        title="User Information",
        description=f"Details for {member}",
        color=EMBED_COLOR_GRAY
    )
    embed.add_field(name="ID", value=member.id)
    embed.add_field(name="Joined", value=member.joined_at)
    await ctx.send(embed=embed)

# Error handling
@commands.command()
async def ban(ctx, member: discord.Member, *, reason: str = None):
    if not ctx.author.guild_permissions.ban_members:
        error_embed = discord.Embed(
            title="❌ Error",
            description="You don't have permission to ban members.",
            color=get_embed_color('error')
        )
        await ctx.send(embed=error_embed)
        return
    
    # Success case
    embed = discord.Embed(
        title="🔨 User Banned",
        description=f"{member.mention} has been banned.",
        color=get_embed_color('ban')  # Uses DARK_RED
    )
    if reason:
        embed.add_field(name="Reason", value=reason)
    await ctx.send(embed=embed)
```

## Design Notes

- GIF thumbnails in this repository are designed to work well with red/gray embed backgrounds
- The color scheme provides clear visual distinction between:
  - **Actions** (red tones) vs **Information** (gray tones)
  - **Standard actions** (bright red) vs **Critical actions** (dark red)
- Error messages use red to maintain consistency with action/consequence theme
- Success messages use gray to maintain a neutral, professional appearance
- Light gray (`0xA9A9A9`) is reserved for subtle accents within embeds (footers, separators, etc.)
