"""
Luna Bot Configuration
Contains all bot settings, color themes, and constants.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Bot Core Settings
BOT_NAME = "Luna"
PREFIX = ","
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
TOKEN = os.getenv("DISCORD_TOKEN")
DATABASE_PATH = "luna.db"

# Gemini AI Settings
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Webhook URLs (optional)
WEBHOOK_MODLOG = os.getenv("WEBHOOK_MODLOG", "")
WEBHOOK_JOIN_LEAVE = os.getenv("WEBHOOK_JOIN_LEAVE", "")

# Lunar Color Palette
DEEP_SPACE = 0x02040B      # Main background
MIDNIGHT_NAVY = 0x0D1321   # Alternative background
STARLIGHT_BLUE = 0x7FA9FF  # Primary accent
COSMIC_PURPLE = 0x1B1431   # Secondary accent

# Color usage
COLOR_PRIMARY = DEEP_SPACE
COLOR_SUCCESS = STARLIGHT_BLUE
COLOR_WARNING = COSMIC_PURPLE
COLOR_ERROR = 0xFF4444     # Red for errors
COLOR_INFO = MIDNIGHT_NAVY

# Command-specific embed colors
EMBED_COLORS = {
    # Moderation
    "warn": COLOR_SUCCESS,
    "mute": COLOR_SUCCESS,
    "kick": COLOR_ERROR,
    "ban": COLOR_ERROR,
    "timeout": COLOR_WARNING,
    "unwarn": COLOR_SUCCESS,
    "unmute": COLOR_SUCCESS,
    "unban": COLOR_SUCCESS,
    "untimeout": COLOR_SUCCESS,
    
    # Admin
    "flag": COLOR_WARNING,
    "unflag": COLOR_SUCCESS,
    "terminate": COLOR_ERROR,
    "stafflist": COLOR_INFO,
    
    # Helper/Tags
    "tag": COLOR_SUCCESS,
    "tags": COLOR_INFO,
    "tag_create": COLOR_SUCCESS,
    "tag_edit": COLOR_SUCCESS,
    "tag_delete": COLOR_ERROR,
    
    # Utility
    "announce": COLOR_SUCCESS,
    "poll": COLOR_INFO,
    "endpoll": COLOR_WARNING,
    "define": COLOR_INFO,
    "translate": COLOR_INFO,
    "askai": COLOR_SUCCESS,
    "remindme": COLOR_SUCCESS,
    "reminders": COLOR_INFO,
    "deleteremind": COLOR_ERROR,
    
    # AI
    "aipanel": COLOR_INFO,
    "ai_target": COLOR_WARNING,
    "ai_stop": COLOR_SUCCESS,
    "ai_settings": COLOR_INFO,
    
    # Shifts
    "shift_create": COLOR_SUCCESS,
    "shift_delete": COLOR_ERROR,
    "view_shifts": COLOR_INFO,
    "activity_view": COLOR_INFO,
    "config_roles": COLOR_SUCCESS,
    "config_afk": COLOR_SUCCESS,
    "config_quota": COLOR_SUCCESS,
    "quota_remove": COLOR_SUCCESS,
    "view_settings": COLOR_INFO,
    "shift_channel": COLOR_SUCCESS,
    "reset_all": COLOR_WARNING,
    "myshift": COLOR_INFO,
    "viewshift": COLOR_INFO,
    "shift_lb": COLOR_SUCCESS,
    
    # Help
    "help": COLOR_INFO,
    "help_all": COLOR_INFO,
    "info": COLOR_INFO,
    
    # Owner
    "commands": COLOR_INFO,
    "blacklist": COLOR_WARNING,
    "unblacklist": COLOR_SUCCESS,
    "extract_dms": COLOR_WARNING,
}

# Staff flag system
MAX_STAFF_FLAGS = 5

# AI Settings
AI_MAX_RESPONSE_LENGTH = 200
AI_RATE_LIMIT_SECONDS = 5
AI_TIMEOUT_SECONDS = 5
AI_TARGET_ACTION_CHANCE = 0.25  # 25% chance to execute action
AI_TARGET_CHECK_INTERVAL = 45    # Seconds between checks

# Shift Settings
SHIFT_GMT_OFFSET = 8  # GMT+8 for shift calculations
SHIFT_DEFAULT_AFK_TIMEOUT = 300  # 5 minutes
SHIFT_DEFAULT_QUOTA = 600  # 10 hours per week (in minutes)
SHIFT_AUTO_END_THRESHOLD = 2  # End shift after 2x AFK timeout
SHIFT_WEEK_START = 0  # Monday (0 = Monday, 6 = Sunday)

# Reminder Settings
REMINDER_CHECK_INTERVAL = 60  # Check every minute

# Pagination settings
PAGINATION_ITEMS_PER_PAGE = 10
LEADERBOARD_TOP_N = 5

# Error messages
ERROR_NO_PERMISSION = "❌ Insufficient Permissions"
ERROR_NOT_CONFIGURED = "❌ Not Configured"
ERROR_INVALID_INPUT = "❌ Invalid Input"
ERROR_DATABASE_ERROR = "❌ Database Error"
ERROR_API_ERROR = "❌ API Error"

# Success messages
SUCCESS_DEFAULT = "✅ Operation Completed"
SUCCESS_UPDATED = "✅ Updated"
SUCCESS_CREATED = "✅ Created"
SUCCESS_DELETED = "✅ Deleted"

# Time format for Discord timestamps (<t:timestamp:format>)
TIME_RELATIVE = "R"
TIME_SHORT = "f"
TIME_LONG = "F"
TIME_DATE = "D"
TIME_TIME = "T"

# Custom emoji placeholders (will be replaced with server-specific IDs)
EMOJI_SHIFT_START = "🟢"
EMOJI_SHIFT_BREAK = "🟡"
EMOJI_SHIFT_RESUME = "🟢"
EMOJI_SHIFT_END = "🔴"
EMOJI_SHIFT_AFK = "⚠️"

LEADERBOARD_EMOJIS = {
    1: "🥇",
    2: "🥈",
    3: "🥉",
}

# Database table names
TABLE_GUILD_SETTINGS = "guild_settings"
TABLE_AI_SETTINGS = "ai_settings"
TABLE_HELPER_ROLE = "helper_role"
TABLE_MUTE = "mutes"
TABLE_WARN = "warns"
TABLE_BAN = "bans"
TABLE_STAFF_FLAGS = "staff_flags"
TABLE_TAGS = "tags"
TABLE_REMINDERS = "reminders"
TABLE_DM_LOGS = "dm_logs"
TABLE_BLACKLIST = "blacklist"
TABLE_POLLS = "polls"
TABLE_SHIFTS = "shifts"
TABLE_SHIFT_CONFIGS = "shift_configs"
TABLE_QUOTA_TRACKING = "quota_tracking"
TABLE_AI_TARGETS = "ai_targets"
TABLE_ACTIVITY_LOGS = "activity_logs"
