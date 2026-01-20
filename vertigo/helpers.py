"""Helper utilities for Vertigo.

This module contains:
- parsing (durations, ids)
- permission checks based on per-guild settings
- embed / response builders using the red+gray theme
- pagination views for longer command output
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Sequence

import discord
from discord.ext import commands

from vertigo import config
from vertigo.database import GuildSettings

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
    embed.set_thumbnail(url=gif_url)
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
