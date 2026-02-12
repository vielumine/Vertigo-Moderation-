"""Vertigo Bot configuration.

This module centralizes all bot-wide configuration:
- Embed color theme (red/gray)
- GIF asset mapping for embed thumbnails
- Environment driven constants (token, owner id, webhook urls, etc.)

The red/gray theme is intentionally used throughout all command cogs.
"""

from __future__ import annotations

import os
from pathlib import Path


# ---------------------------------------------------------------------------
# Core identifiers / env
# ---------------------------------------------------------------------------

BOT_NAME: str = os.getenv("BOT_NAME", "Vertigo")

DEFAULT_PREFIX: str = os.getenv("DEFAULT_PREFIX", "!")

MAX_STAFF_FLAGS: int = 5

OWNER_ID: int = int(os.getenv("OWNER_ID", "0") or 0)

DATABASE_PATH: str = os.getenv("DATABASE_PATH", "vertigo.db")

MESSAGE_LOGGER_WEBHOOK: str | None = os.getenv("MESSAGE_LOGGER_WEBHOOK") or None
JOIN_LEAVE_LOGGER_WEBHOOK: str | None = os.getenv("JOIN_LEAVE_LOGGER_WEBHOOK") or None
ROLE_LOGGER_WEBHOOK: str | None = os.getenv("ROLE_LOGGER_WEBHOOK") or None

# ---------------------------------------------------------------------------
# AI Chatbot Configuration
# ---------------------------------------------------------------------------

HUGGINGFACE_TOKEN: str | None = os.getenv("HUGGINGFACE_TOKEN") or None
HUGGINGFACE_MODEL: str = os.getenv("HUGGINGFACE_MODEL", "HuggingFaceTB/SmolLM3-1.7B-Instruct")
AI_ENABLED_BY_DEFAULT: bool = os.getenv("AI_ENABLED_BY_DEFAULT", "true").lower() == "true"
AI_RESPONSE_TIMEOUT: int = int(os.getenv("AI_RESPONSE_TIMEOUT", "5") or 5)
MAX_RESPONSE_LENGTH: int = int(os.getenv("MAX_RESPONSE_LENGTH", "200") or 200)
RATE_LIMIT_SECONDS: int = int(os.getenv("RATE_LIMIT_SECONDS", "5") or 5)

# AI Personality System
AI_PERSONALITIES = {
    "genz": """You are Vertigo, a fun Discord bot who speaks like Gen-Z users. 
Use phrases like: "fr fr", "no cap", "nah fr", "it's giving", "that's not it chief", 
"periodt", "slay", "that's a vibe", "lowkey", "highkey", "bussin", "ate and left no crumbs".

Be casual, funny, and relatable. Make jokes about random things.
Keep responses short (under 200 characters for Discord).
Sometimes use emojis and meme references.
Be helpful but also funny about it.""",
    
    "professional": """You are Vertigo, a helpful Discord bot designed to assist users with their questions and moderation needs.
Always be polite, professional, and helpful.
Provide clear, concise answers.
Be supportive and understanding.""",
    
    "funny": """You are Vertigo, a hilarious Discord bot who loves making people laugh.
Use jokes, puns, and witty responses.
Be playful and lighthearted.
Keep responses entertaining and fun.""",
}


# ---------------------------------------------------------------------------
# Embed colors (Red & Gray Theme)
# ---------------------------------------------------------------------------

# Primary Action Colors
EMBED_COLOR_RED = 0xFF0000
EMBED_COLOR_DARK_RED = 0xCC0000

# Secondary/Info Colors
EMBED_COLOR_GRAY = 0x808080
EMBED_COLOR_LIGHT_GRAY = 0xA9A9A9

# Contextual Colors
EMBED_COLOR_ERROR = EMBED_COLOR_RED
EMBED_COLOR_SUCCESS = EMBED_COLOR_GRAY


EMBED_COLORS: dict[str, int] = {
    # Red embeds (Primary Actions)
    "warn": EMBED_COLOR_RED,
    "mute": EMBED_COLOR_RED,
    "kick": EMBED_COLOR_RED,
    "ban": EMBED_COLOR_DARK_RED,
    "wm": EMBED_COLOR_RED,
    "warn_and_mute": EMBED_COLOR_RED,
    "masskick": EMBED_COLOR_DARK_RED,
    "massban": EMBED_COLOR_DARK_RED,
    "massmute": EMBED_COLOR_RED,
    "imprison": EMBED_COLOR_DARK_RED,
    "terminate": EMBED_COLOR_DARK_RED,
    "flag": EMBED_COLOR_RED,

    # Gray embeds (Info/Secondary)
    "modlogs": EMBED_COLOR_GRAY,
    "warnings": EMBED_COLOR_GRAY,
    "userinfo": EMBED_COLOR_GRAY,
    "serverinfo": EMBED_COLOR_GRAY,
    "roleinfo": EMBED_COLOR_GRAY,
    "roleperms": EMBED_COLOR_GRAY,
    "stafflist": EMBED_COLOR_GRAY,
    "myinfo": EMBED_COLOR_GRAY,
    "mywarns": EMBED_COLOR_GRAY,
    "checkinfo": EMBED_COLOR_GRAY,
    "myflags": EMBED_COLOR_GRAY,
    "checkflags": EMBED_COLOR_GRAY,
    "checkdur": EMBED_COLOR_GRAY,
    "wasbanned": EMBED_COLOR_GRAY,
    "ping": EMBED_COLOR_GRAY,
    "members": EMBED_COLOR_GRAY,
    "checkavatar": EMBED_COLOR_GRAY,
    "checkbanner": EMBED_COLOR_GRAY,
    "setup": EMBED_COLOR_GRAY,
    "adminsetup": EMBED_COLOR_GRAY,
    "help": EMBED_COLOR_GRAY,
    "adcmd": EMBED_COLOR_GRAY,

    # Success/Neutral Actions (Gray)
    "role": EMBED_COLOR_GRAY,
    "removerole": EMBED_COLOR_GRAY,
    "unmute": EMBED_COLOR_GRAY,
    "unban": EMBED_COLOR_GRAY,
    "unlock": EMBED_COLOR_GRAY,
    "unhide": EMBED_COLOR_GRAY,
    "release": EMBED_COLOR_GRAY,
    "delwarn": EMBED_COLOR_GRAY,

    # AI Commands (Gray)
    "ai": EMBED_COLOR_GRAY,
    "ai_settings": EMBED_COLOR_GRAY,
    "toggle_ai": EMBED_COLOR_GRAY,

    # Hierarchy Commands (Gray)
    "hierarchy": EMBED_COLOR_GRAY,
    "promote": EMBED_COLOR_GRAY,
    "demote": EMBED_COLOR_GRAY,

    # Bot Management Commands (Gray)
    "botavatar": EMBED_COLOR_GRAY,
    "botbanner": EMBED_COLOR_GRAY,
    "botname": EMBED_COLOR_GRAY,
    "botstatus": EMBED_COLOR_GRAY,
    "botactivity": EMBED_COLOR_GRAY,
    "botinfo": EMBED_COLOR_GRAY,
    "botreset": EMBED_COLOR_GRAY,
    "waketime": EMBED_COLOR_GRAY,
    "banguild": EMBED_COLOR_RED,
    "unbanguild": EMBED_COLOR_GRAY,
    "checkguild": EMBED_COLOR_GRAY,
    "guildlist": EMBED_COLOR_GRAY,
    "dmuser": EMBED_COLOR_GRAY,

    # Owner Override Commands (Gray - info/audit commands)
    "overrideaudit": EMBED_COLOR_GRAY,
    "overridestats": EMBED_COLOR_GRAY,
    "overrideguilds": EMBED_COLOR_GRAY,
    "permreport": EMBED_COLOR_GRAY,

    # Error messages
    "error": EMBED_COLOR_ERROR,
    "success": EMBED_COLOR_SUCCESS,
}


def get_embed_color(action_type: str) -> int:
    """Return an embed color for a given action type."""

    return EMBED_COLORS.get(str(action_type).lower(), EMBED_COLOR_GRAY)


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


# ---------------------------------------------------------------------------
# GIF assets
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

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
