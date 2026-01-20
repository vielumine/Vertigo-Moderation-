"""
Vertigo Bot - Embed Color Configuration
Red & Gray Theme

This module defines color constants for Discord embed formatting.
Colors are specified in hexadecimal format for Discord's embed color system.
"""

# Primary Action Colors
EMBED_COLOR_RED = 0xFF0000          # 16711680 - Main action color (warns, kicks, mutes)
EMBED_COLOR_DARK_RED = 0xCC0000     # 13369344 - Critical actions (ban, terminate, severe punishments)

# Secondary/Info Colors
EMBED_COLOR_GRAY = 0x808080         # 8421504 - Info/secondary (info commands, settings, neutral actions)
EMBED_COLOR_LIGHT_GRAY = 0xA9A9A9   # 11184810 - Light accents for secondary info

# Contextual Colors
EMBED_COLOR_ERROR = 0xFF0000        # Error messages (red)
EMBED_COLOR_SUCCESS = 0x808080      # Success messages (gray/neutral)


# Color mapping dictionary for easy reference
EMBED_COLORS = {
    # Red embeds (Primary Actions)
    'warn': EMBED_COLOR_RED,
    'mute': EMBED_COLOR_RED,
    'kick': EMBED_COLOR_RED,
    'ban': EMBED_COLOR_DARK_RED,
    'wm': EMBED_COLOR_RED,  # warn + mute
    'masskick': EMBED_COLOR_DARK_RED,
    'massban': EMBED_COLOR_DARK_RED,
    'massmute': EMBED_COLOR_RED,
    'imprison': EMBED_COLOR_DARK_RED,
    'terminate': EMBED_COLOR_DARK_RED,
    'flag': EMBED_COLOR_RED,
    'massstrike': EMBED_COLOR_RED,
    
    # Gray embeds (Info/Secondary)
    'modlogs': EMBED_COLOR_GRAY,
    'warnings': EMBED_COLOR_GRAY,
    'userinfo': EMBED_COLOR_GRAY,
    'serverinfo': EMBED_COLOR_GRAY,
    'roleperms': EMBED_COLOR_GRAY,
    'stafflist': EMBED_COLOR_GRAY,
    'myinfo': EMBED_COLOR_GRAY,
    'mywarns': EMBED_COLOR_GRAY,
    'checkdur': EMBED_COLOR_GRAY,
    'wasbanned': EMBED_COLOR_GRAY,
    'ping': EMBED_COLOR_GRAY,
    'members': EMBED_COLOR_GRAY,
    'checkavatar': EMBED_COLOR_GRAY,
    'checkbanner': EMBED_COLOR_GRAY,
    'setup': EMBED_COLOR_GRAY,
    'adminsetup': EMBED_COLOR_GRAY,
    
    # Success/Neutral Actions (Gray)
    'role': EMBED_COLOR_GRAY,
    'removerole': EMBED_COLOR_GRAY,
    'unmute': EMBED_COLOR_GRAY,
    'unban': EMBED_COLOR_GRAY,
    'unlock': EMBED_COLOR_GRAY,
    'unhide': EMBED_COLOR_GRAY,
    'release': EMBED_COLOR_GRAY,
    'delwarn': EMBED_COLOR_GRAY,
    
    # Error messages
    'error': EMBED_COLOR_ERROR,
    
    # Success messages
    'success': EMBED_COLOR_SUCCESS,
}


def get_embed_color(action_type):
    """
    Get the appropriate embed color for a given action type.
    
    Args:
        action_type (str): The type of action (e.g., 'warn', 'ban', 'userinfo')
    
    Returns:
        int: Hexadecimal color value for Discord embed
    
    Example:
        >>> color = get_embed_color('ban')
        >>> embed = discord.Embed(title="User Banned", color=color)
    """
    return EMBED_COLORS.get(action_type.lower(), EMBED_COLOR_GRAY)


# GIF URLs - Full GitHub links
GIF_URLS = {
    "WARN": "https://raw.githubusercontent.com/vielumine/Vertigo-Moderation-/refs/heads/main/standard.gif",
    "WARN_REMOVED": "https://raw.githubusercontent.com/vielumine/Vertigo-Moderation-/refs/heads/main/standard%20(11).gif",
    "MUTE": "https://raw.githubusercontent.com/vielumine/Vertigo-Moderation-/refs/heads/main/standard%20(1).gif",
    "UNMUTE": "https://raw.githubusercontent.com/vielumine/Vertigo-Moderation-/refs/heads/main/standard%20(12).gif",
    "WARN_AND_MUTE": "https://raw.githubusercontent.com/vielumine/Vertigo-Moderation-/refs/heads/main/standard%20(2).gif",
    "KICK": "https://raw.githubusercontent.com/vielumine/Vertigo-Moderation-/refs/heads/main/standard%20(3).gif",
    "BAN": "https://raw.githubusercontent.com/vielumine/Vertigo-Moderation-/refs/heads/main/standard%20(4).gif",
    "UNBAN": "https://raw.githubusercontent.com/vielumine/Vertigo-Moderation-/refs/heads/main/standard%20(15).gif",
    "STAFF_FLAG": "https://raw.githubusercontent.com/vielumine/Vertigo-Moderation-/refs/heads/main/standard%20(5).gif",
    "STAFF_UNFLAG": "https://raw.githubusercontent.com/vielumine/Vertigo-Moderation-/refs/heads/main/standard%20(13).gif",
    "STAFF_TERMINATE": "https://raw.githubusercontent.com/vielumine/Vertigo-Moderation-/refs/heads/main/standard%20(6).gif",
    "ROLE_ASSIGNED": "https://raw.githubusercontent.com/vielumine/Vertigo-Moderation-/refs/heads/main/standard%20(7).gif",
    "ROLE_REMOVED": "https://raw.githubusercontent.com/vielumine/Vertigo-Moderation-/refs/heads/main/standard%20(8).gif",
    "TEMP_ROLE": "https://raw.githubusercontent.com/vielumine/Vertigo-Moderation-/refs/heads/main/standard%20(10).gif",
    "PERSIST_ROLE": "https://raw.githubusercontent.com/vielumine/Vertigo-Moderation-/refs/heads/main/standard%20(9).gif",
}


# Color usage guidelines
"""
COLOR USAGE GUIDELINES
======================

RED (0xFF0000):
- Standard moderation actions that involve consequences
- Commands: warn, mute, kick, wm, massmute, flag

DARK_RED (0xCC0000):
- Critical/severe actions with permanent or serious consequences
- Commands: ban, masskick, massban, imprison, terminate

GRAY (0x808080):
- Information and lookup commands
- Settings displays
- Neutral actions (unmute, unban, role assignment)
- Commands: modlogs, warnings, userinfo, serverinfo, roleperms, stafflist,
            myinfo, mywarns, checkdur, wasbanned, ping, members, checkavatar,
            checkbanner, setup, adminsetup, role, removerole, unmute, unban,
            unlock, unhide, release, delwarn

LIGHT_GRAY (0xA9A9A9):
- Reserved for lighter accents and secondary information within embeds
- Use for footer text, field separators, or subtle UI elements

ERROR (RED):
- All error messages (insufficient permissions, invalid arguments, etc.)

SUCCESS (GRAY):
- Success confirmations (use neutral gray instead of green)
"""
