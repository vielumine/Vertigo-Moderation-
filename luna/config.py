"""Luna Bot configuration.

This module centralizes all bot-wide configuration:
- Embed color theme (lunar purple/blue/dark)
- Environment driven constants (token, owner id, webhook urls, etc.)
- Gemini AI integration
- Stats dashboard configuration

The lunar theme is intentionally used throughout all command cogs.
"""

from __future__ import annotations

import os
from pathlib import Path


# ---------------------------------------------------------------------------
# Core identifiers / env
# ---------------------------------------------------------------------------

BOT_NAME: str = os.getenv("BOT_NAME", "Luna")

DEFAULT_PREFIX: str = os.getenv("DEFAULT_PREFIX", ",")

MAX_STAFF_FLAGS: int = 5

OWNER_ID: int = int(os.getenv("OWNER_ID", "0") or 0)

DATABASE_PATH: str = os.getenv("DATABASE_PATH", "luna.db")

MESSAGE_LOGGER_WEBHOOK: str | None = os.getenv("MESSAGE_LOGGER_WEBHOOK") or None
JOIN_LEAVE_LOGGER_WEBHOOK: str | None = os.getenv("JOIN_LEAVE_LOGGER_WEBHOOK") or None
ROLE_LOGGER_WEBHOOK: str | None = os.getenv("ROLE_LOGGER_WEBHOOK") or None

# ---------------------------------------------------------------------------
# Stats Dashboard Configuration
# ---------------------------------------------------------------------------

TARGET_CHANNEL_ID: int = int(os.getenv("TARGET_CHANNEL_ID", "1459535418990002197") or 1459535418990002197)
API_URL: str = os.getenv("API_URL", "https://halal-worker.vvladut245.workers.dev/")
STATS_DB_FILE: str = os.getenv("STATS_DB_FILE", "stats.db")

# ---------------------------------------------------------------------------
# AI Chatbot Configuration (Gemini + HuggingFace)
# ---------------------------------------------------------------------------

# Gemini AI (Luna's primary)
GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY") or None
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-pro")

# HuggingFace AI (Vertigo compatibility)
HUGGINGFACE_TOKEN: str | None = os.getenv("HUGGINGFACE_TOKEN") or None
HUGGINGFACE_MODEL: str = os.getenv("HUGGINGFACE_MODEL", "HuggingFaceTB/SmolLM3-1.7B-Instruct")

# Common AI settings
AI_ENABLED_BY_DEFAULT: bool = os.getenv("AI_ENABLED_BY_DEFAULT", "true").lower() == "true"
AI_RESPONSE_TIMEOUT: int = int(os.getenv("AI_RESPONSE_TIMEOUT", "5") or 5)
MAX_RESPONSE_LENGTH: int = int(os.getenv("MAX_RESPONSE_LENGTH", "200") or 200)
RATE_LIMIT_SECONDS: int = int(os.getenv("RATE_LIMIT_SECONDS", "5") or 5)

# AI Personality System - Lunar theme personalities
AI_PERSONALITIES = {
    "professional": """You are Luna, a strict and efficient Discord moderation bot.
Always be formal, direct, and professional.
Provide clear, concise answers without casual language.
Focus on accuracy and helpfulness.
Keep responses under 200 characters.""",
    
    "cold": """You are Luna, a cold and calculating Discord bot.
Be blunt, direct, and emotionless.
No pleasantries, just facts.
Keep responses short and to the point.""",
    
    "formal": """You are Luna, a formal Discord assistant.
Maintain professional decorum at all times.
Be polite but distant.
Provide helpful information in a structured manner.""",
    
    "genz": """You are Luna, a fun Discord bot who speaks like Gen-Z users. 
Use phrases like: "fr fr", "no cap", "nah fr", "it's giving", "that's not it chief", 
"periodt", "slay", "that's a vibe", "lowkey", "highkey", "bussin", "ate and left no crumbs".

Be casual, funny, and relatable. Make jokes about random things.
Keep responses short (under 200 characters for Discord).
Sometimes use emojis and meme references.
Be helpful but also funny about it.""",
    
    "funny": """You are Luna, a hilarious Discord bot who loves making people laugh.
Use jokes, puns, and witty responses.
Be playful and lighthearted.
Keep responses entertaining and fun.""",
}

# Roasting personality for AI targeting
AI_ROASTING_PERSONALITY = """You are Luna, a Discord bot with a sharp, witty sense of humor.
Roast the user in a funny, lighthearted way. Be clever and playful, not mean.
Keep it short (under 150 characters) and make it memorable."""


# ---------------------------------------------------------------------------
# Embed colors (Lunar Purple & Blue Theme)
# ---------------------------------------------------------------------------

# Primary Lunar Colors
EMBED_COLOR_DEEP_SPACE = 0x02040B  # Almost black with blue tint
EMBED_COLOR_STARLIGHT_BLUE = 0x7FA9FF  # Light blue
EMBED_COLOR_COSMIC_PURPLE = 0x1B1431  # Dark purple
EMBED_COLOR_LUNAR_GLOW = 0x4A5FF5  # Medium blue-purple

# Contextual Colors
EMBED_COLOR_ERROR = EMBED_COLOR_DEEP_SPACE
EMBED_COLOR_SUCCESS = EMBED_COLOR_STARLIGHT_BLUE


EMBED_COLORS: dict[str, int] = {
    # Primary moderation actions (Cosmic Purple)
    "warn": EMBED_COLOR_COSMIC_PURPLE,
    "mute": EMBED_COLOR_COSMIC_PURPLE,
    "kick": EMBED_COLOR_COSMIC_PURPLE,
    "ban": EMBED_COLOR_DEEP_SPACE,
    "wm": EMBED_COLOR_COSMIC_PURPLE,
    "warn_and_mute": EMBED_COLOR_COSMIC_PURPLE,
    "masskick": EMBED_COLOR_DEEP_SPACE,
    "massban": EMBED_COLOR_DEEP_SPACE,
    "massmute": EMBED_COLOR_COSMIC_PURPLE,
    "imprison": EMBED_COLOR_DEEP_SPACE,
    "terminate": EMBED_COLOR_DEEP_SPACE,
    "flag": EMBED_COLOR_COSMIC_PURPLE,

    # Info/Secondary actions (Starlight Blue)
    "modlogs": EMBED_COLOR_STARLIGHT_BLUE,
    "warnings": EMBED_COLOR_STARLIGHT_BLUE,
    "userinfo": EMBED_COLOR_STARLIGHT_BLUE,
    "serverinfo": EMBED_COLOR_STARLIGHT_BLUE,
    "roleperms": EMBED_COLOR_STARLIGHT_BLUE,
    "stafflist": EMBED_COLOR_STARLIGHT_BLUE,
    "myinfo": EMBED_COLOR_STARLIGHT_BLUE,
    "mywarns": EMBED_COLOR_STARLIGHT_BLUE,
    "checkdur": EMBED_COLOR_STARLIGHT_BLUE,
    "wasbanned": EMBED_COLOR_STARLIGHT_BLUE,
    "ping": EMBED_COLOR_STARLIGHT_BLUE,
    "members": EMBED_COLOR_STARLIGHT_BLUE,
    "checkavatar": EMBED_COLOR_STARLIGHT_BLUE,
    "checkbanner": EMBED_COLOR_STARLIGHT_BLUE,
    "setup": EMBED_COLOR_STARLIGHT_BLUE,
    "adminsetup": EMBED_COLOR_STARLIGHT_BLUE,
    "help": EMBED_COLOR_STARLIGHT_BLUE,
    "adcmd": EMBED_COLOR_STARLIGHT_BLUE,

    # Success/Neutral Actions (Starlight Blue)
    "role": EMBED_COLOR_STARLIGHT_BLUE,
    "removerole": EMBED_COLOR_STARLIGHT_BLUE,
    "unmute": EMBED_COLOR_STARLIGHT_BLUE,
    "unban": EMBED_COLOR_STARLIGHT_BLUE,
    "unlock": EMBED_COLOR_STARLIGHT_BLUE,
    "unhide": EMBED_COLOR_STARLIGHT_BLUE,
    "release": EMBED_COLOR_STARLIGHT_BLUE,
    "delwarn": EMBED_COLOR_STARLIGHT_BLUE,

    # AI Commands (Lunar Glow)
    "ai": EMBED_COLOR_LUNAR_GLOW,
    "ai_settings": EMBED_COLOR_LUNAR_GLOW,
    "toggle_ai": EMBED_COLOR_LUNAR_GLOW,
    "askai": EMBED_COLOR_LUNAR_GLOW,

    # Hierarchy Commands (Starlight Blue)
    "hierarchy": EMBED_COLOR_STARLIGHT_BLUE,
    "promote": EMBED_COLOR_STARLIGHT_BLUE,
    "demote": EMBED_COLOR_STARLIGHT_BLUE,

    # Tags (Starlight Blue)
    "tag": EMBED_COLOR_STARLIGHT_BLUE,
    "tags": EMBED_COLOR_STARLIGHT_BLUE,

    # Shifts (Lunar Glow)
    "shift": EMBED_COLOR_LUNAR_GLOW,
    "shifts": EMBED_COLOR_LUNAR_GLOW,

    # Utility (Starlight Blue)
    "announce": EMBED_COLOR_STARLIGHT_BLUE,
    "poll": EMBED_COLOR_STARLIGHT_BLUE,
    "define": EMBED_COLOR_STARLIGHT_BLUE,
    "translate": EMBED_COLOR_STARLIGHT_BLUE,
    "reminder": EMBED_COLOR_STARLIGHT_BLUE,

    # Stats Dashboard (Lunar Glow)
    "stats": EMBED_COLOR_LUNAR_GLOW,
    "refresh": EMBED_COLOR_LUNAR_GLOW,

    # Bot Management Commands (Starlight Blue)
    "botavatar": EMBED_COLOR_STARLIGHT_BLUE,
    "botbanner": EMBED_COLOR_STARLIGHT_BLUE,
    "botname": EMBED_COLOR_STARLIGHT_BLUE,
    "botstatus": EMBED_COLOR_STARLIGHT_BLUE,
    "botactivity": EMBED_COLOR_STARLIGHT_BLUE,
    "botinfo": EMBED_COLOR_STARLIGHT_BLUE,
    "botreset": EMBED_COLOR_STARLIGHT_BLUE,
    "waketime": EMBED_COLOR_STARLIGHT_BLUE,
    "banguild": EMBED_COLOR_COSMIC_PURPLE,
    "unbanguild": EMBED_COLOR_STARLIGHT_BLUE,
    "checkguild": EMBED_COLOR_STARLIGHT_BLUE,
    "guildlist": EMBED_COLOR_STARLIGHT_BLUE,
    "dmuser": EMBED_COLOR_STARLIGHT_BLUE,

    # Owner Override Commands (Starlight Blue - info/audit commands)
    "overrideaudit": EMBED_COLOR_STARLIGHT_BLUE,
    "overridestats": EMBED_COLOR_STARLIGHT_BLUE,
    "overrideguilds": EMBED_COLOR_STARLIGHT_BLUE,
    "permreport": EMBED_COLOR_STARLIGHT_BLUE,

    # Error messages
    "error": EMBED_COLOR_ERROR,
    "success": EMBED_COLOR_SUCCESS,
}


def get_embed_color(action_type: str) -> int:
    """Return an embed color for a given action type."""
    return EMBED_COLORS.get(str(action_type).lower(), EMBED_COLOR_STARLIGHT_BLUE)


# ---------------------------------------------------------------------------
# GIF URLs (from Vertigo)
# ---------------------------------------------------------------------------

# GIF URLs - Full GitHub links
GIF_URLS: dict[str, str] = {
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


def get_gif_url(gif_key: str) -> str:
    """Return a full URL to a GIF asset.
    
    These assets are hosted on GitHub and can be used directly in embed thumbnails.
    """
    return GIF_URLS.get(gif_key.upper(), GIF_URLS["WARN"])


# Local GIF assets (optional - for file attachments)
_GIF_FILES = {
    "DEFAULT": "standard.gif",
    "WARN": "standard.gif",
    "WARN_REMOVED": "standard (1).gif",
    "MUTE": "standard (2).gif",
    "UNMUTE": "standard (3).gif",
    "BAN": "standard (4).gif",
    "KICK": "standard (5).gif",
    "WARN_AND_MUTE": "standard (6).gif",
    "ROLE_ASSIGNED": "standard (7).gif",
    "ROLE_REMOVED": "standard (8).gif",
    "TEMP_ROLE": "standard (9).gif",
    "PERSIST_ROLE": "standard (10).gif",
    "STAFF_FLAG": "standard (11).gif",
    "STAFF_UNFLAG": "standard (12).gif",
    "STAFF_TERMINATE": "standard (13).gif",
    "GENERIC": "standard (14).gif",
}


def get_gif_path(key: str) -> Path:
    """Return a local filesystem path to a GIF asset.

    These assets are shipped in the repository and can be sent as attachments.
    """
    filename = _GIF_FILES.get(key.upper(), _GIF_FILES["DEFAULT"])
    return PROJECT_ROOT / filename


# ---------------------------------------------------------------------------
# Shift Management (GMT+8)
# ---------------------------------------------------------------------------

# Shift timezone (GMT+8 for shift tracking only)
SHIFT_TIMEZONE_OFFSET = 8  # GMT+8

# Default shift durations (in hours)
DEFAULT_SHIFT_DURATIONS = {
    "helper": 2,
    "staff": 4,
}

# AFK timeouts (in seconds)
DEFAULT_AFK_TIMEOUTS = {
    "helper": 300,  # 5 minutes
    "staff": 600,   # 10 minutes
}

# Weekly quotas (in hours)
DEFAULT_WEEKLY_QUOTAS = {
    "helper": 10,
    "staff": 20,
}


# ---------------------------------------------------------------------------
# Project root
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]
