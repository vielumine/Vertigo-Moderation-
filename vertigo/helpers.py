"""Helper utilities for Vertigo.

This module contains:
- parsing (durations, ids)
- permission checks based on per-guild settings
- embed / response builders using the red+gray theme
- pagination views for longer command output
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Sequence

import discord
from huggingface_hub import InferenceClient
from discord.ext import commands

import config
from database import AISettings, GuildSettings

logger = logging.getLogger(__name__)


_ID_RE = re.compile(r"(\d{15,25})")
_DURATION_RE = re.compile(r"^(\d{1,9})([smhd])$", re.IGNORECASE)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def extract_id(value: str) -> int | None:
    """Extract a Discord snowflake from a mention or raw string."""

    match = _ID_RE.search(value)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def parse_id_list(value: str) -> list[int]:
    """Parse comma-separated ids/mentions into a list of ints."""

    out: list[int] = []
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        snowflake = extract_id(part)
        if snowflake is not None:
            out.append(snowflake)
    return out


def parse_duration(value: str) -> int:
    """Parse a duration string into seconds.

    Supports: s, m, h, d.
    """

    value = value.strip().lower()
    match = _DURATION_RE.match(value)
    if not match:
        raise ValueError("Invalid duration format")
    amount = int(match.group(1))
    unit = match.group(2).lower()

    mult = {"s": 1, "m": 60, "h": 3600, "d": 86400}[unit]
    return amount * mult


def humanize_seconds(seconds: int) -> str:
    """Convert seconds to a human readable string."""

    if seconds <= 0:
        return "0s"

    delta = timedelta(seconds=seconds)
    days = delta.days
    hours, rem = divmod(delta.seconds, 3600)
    minutes, secs = divmod(rem, 60)

    parts: list[str] = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if secs or not parts:
        parts.append(f"{secs}s")
    return " ".join(parts)


def is_admin_member(member: discord.Member, settings: GuildSettings) -> bool:
    if member.guild_permissions.administrator:
        return True
    if settings.admin_role_ids and any(r.id in settings.admin_role_ids for r in member.roles):
        return True
    return False


def is_staff_member(member: discord.Member, settings: GuildSettings) -> bool:
    ids = set(settings.staff_role_ids)
    if not ids:
        return False
    return any(r.id in ids for r in member.roles)


def has_any_role(member: discord.Member, role_ids: Sequence[int]) -> bool:
    ids = set(role_ids)
    if not ids:
        return False
    return any(r.id in ids for r in member.roles)


def role_level_for_member(member: discord.Member, settings: GuildSettings) -> str:
    """Return a symbolic permission level."""

    if is_admin_member(member, settings):
        return "admin"
    if has_any_role(member, settings.head_mod_role_ids):
        return "head_mod"
    if has_any_role(member, settings.senior_mod_role_ids):
        return "senior_mod"
    if has_any_role(member, settings.moderator_role_ids) or has_any_role(member, settings.staff_role_ids):
        return "moderator"
    return "member"


async def safe_delete(message: discord.Message) -> None:
    try:
        await message.delete()
    except (discord.Forbidden, discord.NotFound):
        return
    except Exception:
        logger.exception("Failed to delete message")


async def safe_dm(user: discord.abc.User, *, content: str | None = None, embed: discord.Embed | None = None) -> None:
    try:
        await user.send(content=content, embed=embed)
    except discord.Forbidden:
        return
    except Exception:
        logger.exception("Failed to DM user %s", getattr(user, "id", "?"))


async def add_loading_reaction(message: discord.Message) -> None:
    """Add a loading reaction (🔃) to indicate processing."""
    try:
        await message.add_reaction("🔃")
    except Exception:
        logger.debug("Failed to add loading reaction")


def make_embed(*, action: str, title: str, description: str | None = None) -> discord.Embed:
    embed = discord.Embed(
        title=title,
        description=description or "",
        color=config.get_embed_color(action),
        timestamp=utcnow(),
    )
    embed.set_footer(text=config.BOT_NAME)
    return embed


def attach_gif(embed: discord.Embed, *, gif_key: str, filename: str = "action.gif") -> tuple[discord.Embed, discord.File | None]:
    gif_url = config.get_gif_url(gif_key)
    embed.set_image(url=gif_url)
    return embed, None


async def send_embed(
    destination: discord.abc.Messageable,
    *,
    embed: discord.Embed,
    file: discord.File | None = None,
    view: discord.ui.View | None = None,
) -> discord.Message:
    return await destination.send(embed=embed, file=file, view=view)


async def notify_owner(bot: commands.Bot, *, embed: discord.Embed) -> None:
    owner_id = config.OWNER_ID
    if not owner_id:
        return
    try:
        owner = bot.get_user(owner_id) or await bot.fetch_user(owner_id)
    except Exception:
        logger.exception("Failed to fetch owner")
        return
    await safe_dm(owner, embed=embed)


async def log_to_modlog_channel(
    bot: commands.Bot,
    *,
    guild: discord.Guild,
    settings: GuildSettings,
    embed: discord.Embed,
    file: discord.File | None,
) -> int | None:
    if not settings.modlog_channel_id:
        return None
    channel = guild.get_channel(settings.modlog_channel_id)
    if channel is None:
        return None
    if not isinstance(channel, discord.abc.Messageable):
        return None
    try:
        msg = await channel.send(embed=embed, file=file)
    except discord.Forbidden:
        return None
    except Exception:
        logger.exception("Failed to send modlog message")
        return None
    return msg.id


def commands_channel_check() -> commands.Check:
    async def predicate(ctx: commands.Context) -> bool:
        if ctx.guild is None:
            return True
        bot = ctx.bot
        db = getattr(bot, "db", None)
        if db is None:
            return True
        settings: GuildSettings = await db.get_guild_settings(ctx.guild.id, default_prefix=config.DEFAULT_PREFIX)
        if settings.commands_channel_id and ctx.channel.id != settings.commands_channel_id:
            allowed = ctx.guild.get_channel(settings.commands_channel_id)
            ch_mention = allowed.mention if allowed else f"<#{settings.commands_channel_id}>"
            embed = make_embed(action="error", title="Wrong Channel", description=f"Please use commands in {ch_mention}.")
            await ctx.send(embed=embed)
            return False
        return True

    return commands.check(predicate)


def require_level(min_level: str) -> commands.Check:
    levels = {"member": 0, "moderator": 1, "senior_mod": 2, "head_mod": 3, "admin": 4}

    async def predicate(ctx: commands.Context) -> bool:
        if ctx.guild is None or not isinstance(ctx.author, discord.Member):
            return False
        db = getattr(ctx.bot, "db", None)
        if db is None:
            return False
        settings: GuildSettings = await db.get_guild_settings(ctx.guild.id, default_prefix=config.DEFAULT_PREFIX)
        have = role_level_for_member(ctx.author, settings)
        if levels[have] < levels[min_level]:
            embed = make_embed(action="error", title="No Permission", description="You don't have permission to use this command.")
            await ctx.send(embed=embed)
            return False
        return True

    return commands.check(predicate)


def require_admin() -> commands.Check:
    async def predicate(ctx: commands.Context) -> bool:
        if ctx.guild is None or not isinstance(ctx.author, discord.Member):
            return False
        db = getattr(ctx.bot, "db", None)
        if db is None:
            return False
        settings: GuildSettings = await db.get_guild_settings(ctx.guild.id, default_prefix=config.DEFAULT_PREFIX)
        if not is_admin_member(ctx.author, settings):
            embed = make_embed(action="error", title="No Permission", description="You don't have permission to use this command.")
            await ctx.send(embed=embed)
            return False
        return True

    return commands.check(predicate)


def require_owner() -> commands.Check:
    async def predicate(ctx: commands.Context) -> bool:
        return ctx.author.id == config.OWNER_ID if config.OWNER_ID else False

    return commands.check(predicate)


def can_bot_act_on(bot_member: discord.Member, target: discord.Member) -> bool:
    return bot_member.top_role > target.top_role and bot_member.guild_permissions.manage_roles


def can_moderator_act_on(moderator: discord.Member, target: discord.Member) -> bool:
    if moderator.guild_permissions.administrator:
        return True
    return moderator.top_role > target.top_role


@dataclass(slots=True)
class Page:
    embed: discord.Embed
    file: discord.File | None = None


class PaginationView(discord.ui.View):
    """Button-based pagination for embeds."""

    def __init__(self, *, pages: list[Page], author_id: int, timeout: float = 180) -> None:
        super().__init__(timeout=timeout)
        self.pages = pages
        self.author_id = author_id
        self.index = 0

        self.prev_button.disabled = len(pages) <= 1
        self.next_button.disabled = len(pages) <= 1

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user and interaction.user.id != self.author_id:
            await interaction.response.send_message("This menu isn't for you.", ephemeral=True)
            return False
        return True

    async def _render(self, interaction: discord.Interaction) -> None:
        page = self.pages[self.index]
        for i, p in enumerate(self.pages):
            if i == self.index:
                continue
            if p.file is not None:
                try:
                    p.file.close()
                except Exception:
                    pass
        await interaction.response.edit_message(embed=page.embed, attachments=[page.file] if page.file else [], view=self)

    @discord.ui.button(label="Prev", style=discord.ButtonStyle.secondary)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:  # type: ignore[override]
        self.index = (self.index - 1) % len(self.pages)
        await self._render(interaction)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:  # type: ignore[override]
        self.index = (self.index + 1) % len(self.pages)
        await self._render(interaction)


async def timed_rest_call(coro: Any) -> tuple[Any, float]:
    start = time.perf_counter()
    result = await coro
    return result, (time.perf_counter() - start) * 1000.0


# ---------------------------------------------------------------------------
# AI Chatbot Helpers
# ---------------------------------------------------------------------------

# Simple rate limiting storage
_ai_rate_limits: dict[int, float] = {}


def is_rate_limited(user_id: int) -> bool:
    """Check if user is rate limited for AI responses."""
    last_request = _ai_rate_limits.get(user_id, 0)
    return (time.time() - last_request) < config.RATE_LIMIT_SECONDS


def update_rate_limit(user_id: int) -> None:
    """Update user's rate limit timestamp."""
    _ai_rate_limits[user_id] = time.time()


def clean_rate_limits() -> None:
    """Clean up old rate limit entries."""
    current_time = time.time()
    expired_users = [
        user_id for user_id, last_request in _ai_rate_limits.items()
        if current_time - last_request > 300  # 5 minutes
    ]
    for user_id in expired_users:
        _ai_rate_limits.pop(user_id, None)


def get_personality_prompt(personality: str = "genz") -> str:
    """Get the system prompt for the specified personality."""
    return config.AI_PERSONALITIES.get(personality, config.AI_PERSONALITIES["genz"])


def truncate_response(text: str, max_length: int = config.MAX_RESPONSE_LENGTH) -> str:
    """Truncate response to fit Discord's character limit."""
    if len(text) <= max_length:
        return text
    
    # Try to truncate at a word boundary
    truncated = text[:max_length-3]
    last_space = truncated.rfind(' ')
    if last_space > max_length * 0.7:  # Only truncate at word if it's reasonable
        truncated = truncated[:last_space]
    
    return truncated + "..."


async def call_huggingface_api(user_message: str, personality: str = "genz") -> str:
    """Call HuggingFace API to get AI response."""
    if not config.HUGGINGFACE_TOKEN:
        raise ValueError("HUGGINGFACE_TOKEN not configured")

    client = InferenceClient(
        model=config.HUGGINGFACE_MODEL,
        token=config.HUGGINGFACE_TOKEN,
        base_url="https://router.huggingface.co/hf-inference",
    )

    system_prompt = get_personality_prompt(personality)
    full_prompt = f"{system_prompt}\n\nUser: {user_message}\nAI:"

    try:
        response = client.text_generation(
            full_prompt,
            max_new_tokens=100,
            temperature=0.8,
            do_sample=True,
            top_p=0.9,
        )

        response_text = response.replace(full_prompt, "").strip()
        return response_text if response_text else "nah fr fr the vibes are off rn, try again bestie 😅"

    except Exception as e:
        logger.error("HuggingFace API error: %s", e)
        return "nah the AI service is down rn, try again later 💀"


async def get_ai_response(user_message: str, personality: str = "genz") -> str:
    """Get AI response with proper formatting and safety."""
    try:
        response = await call_huggingface_api(user_message, personality)
        
        # Clean up the response
        response = response.strip()
        
        # Remove any system prompts or instructions that might have leaked
        response = re.sub(r"(You are|User:|AI:|Human:|Assistant:).*$", "", response, flags=re.MULTILINE)
        response = response.strip()
        
        # Ensure response is not empty
        if not response:
            response = "nah i got nothing rn, try asking something else 💭"
        
        # Truncate if needed
        response = truncate_response(response)
        
        return response
        
    except Exception as e:
        logger.error("AI response error: %s", e)
        return "nah the AI vibes are off rn, try again later 😅"


async def is_ai_enabled_for_guild(guild_id: int, db) -> bool:
    """Check if AI is enabled for the guild."""
    try:
        ai_settings = await db.get_ai_settings(guild_id)
        return ai_settings.ai_enabled
    except Exception:
        # If there's an error, default to enabled
        return True


async def is_ai_enabled_for_dms(guild_id: int, db) -> bool:
    """Check if AI is enabled for DMs in the guild."""
    try:
        ai_settings = await db.get_ai_settings(guild_id)
        return ai_settings.respond_to_dms and ai_settings.ai_enabled
    except Exception:
        return False


def should_help_with_moderation(message_content: str) -> bool:
    """Check if the message appears to be asking for moderation help."""
    moderation_keywords = [
        "report", "spam", "toxic", "rule", "break", "warn", "ban", "kick", 
        "mute", "punishment", "behavior", "abuse", "harassment", "inappropriate"
    ]
    message_lower = message_content.lower()
    return any(keyword in message_lower for keyword in moderation_keywords)
