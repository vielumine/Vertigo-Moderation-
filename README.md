# Vertigo Bot Assets & Configuration

This repository contains GIF assets and color configuration for the Vertigo Discord bot.

## Contents

### GIF Assets
- `standard.gif` - Main standard GIF
- `standard (1-14).gif` - 14 additional standard GIF variants

These GIFs are designed to work well with the bot's red and gray color theme.

### Color Configuration

The `config.py` file defines the embed color scheme for the Vertigo Bot.

#### Color Scheme

**Primary Colors:**
- **RED** (`0xFF0000` / `16711680`) - Main action color for warns, kicks, mutes
- **DARK_RED** (`0xCC0000` / `13369344`) - Critical actions like bans and terminations
- **GRAY** (`0x808080` / `8421504`) - Info commands, settings, neutral actions
- **LIGHT_GRAY** (`0xA9A9A9` / `11184810`) - Light accents for secondary info

#### Usage

Import the color constants in your bot code:

```python
from config import EMBED_COLOR_RED, EMBED_COLOR_GRAY, get_embed_color

# Direct usage
embed = discord.Embed(title="Warning", color=EMBED_COLOR_RED)

# Using the helper function
color = get_embed_color('ban')
embed = discord.Embed(title="User Banned", color=color)
```

#### Command Color Mapping

**Red Embeds (Actions/Consequences):**
- warn, mute, kick, wm, massmute, flag, massstrike

**Dark Red Embeds (Critical Actions):**
- ban, masskick, massban, imprison, terminate

**Gray Embeds (Info/Neutral):**
- modlogs, warnings, userinfo, serverinfo, roleperms, stafflist
- myinfo, mywarns, checkdur, wasbanned, ping, members
- checkavatar, checkbanner, setup, adminsetup
- role, removerole, unmute, unban, unlock, unhide, release, delwarn

**Errors:** RED  
**Success:** GRAY

## Integration

To use these assets and colors in your Vertigo Bot:

1. Import the color configuration:
   ```python
   from config import EMBED_COLORS, get_embed_color
   ```

2. Apply colors to embeds:
   ```python
   embed = discord.Embed(
       title="User Warned",
       description=f"{user.mention} has been warned.",
       color=get_embed_color('warn')
   )
   ```

3. Reference GIF assets for embed thumbnails (ensure they display well on red/gray backgrounds)

## License

Assets and configuration for Vertigo Bot.
