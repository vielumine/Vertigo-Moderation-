"""Moderation commands (warn/mute/ban/kick/etc.)."""

from __future__ import annotations

import json
import logging
from datetime import timedelta

import discord
from discord.ext import commands

from vertigo import config
from vertigo.database import Database, GuildSettings
from vertigo.helpers import (
    Page,
    PaginationView,
    attach_gif,
    commands_channel_check,
    extract_id,
    humanize_seconds,
    make_embed,
    notify_owner,
    parse_duration,
    require_level,
    safe_delete,
    safe_dm,
)

logger = logging.getLogger(__name__)


class ModerationCog(commands.Cog):
    """Moderator+ commands."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @property
    def db(self) -> Database:
        return self.bot.db  # type: ignore[attr-defined]

    async def _settings(self, guild: discord.Guild) -> GuildSettings:
        return await self.db.get_guild_settings(guild.id, default_prefix=config.DEFAULT_PREFIX)

    async def _blocked_by_staff_immunity(self, ctx: commands.Context, target: discord.Member) -> bool:
        settings = await self._settings(ctx.guild)  # type: ignore[arg-type]
        if not isinstance(ctx.author, discord.Member):
            return True
        if target.guild_permissions.administrator:
            return True
        staff_ids = set(settings.staff_role_ids + settings.head_mod_role_ids + settings.senior_mod_role_ids + settings.moderator_role_ids)
        is_staff = any(r.id in staff_ids for r in target.roles)
        if is_staff and not (ctx.author.guild_permissions.administrator or any(r.id in settings.admin_role_ids for r in ctx.author.roles)):
            embed = make_embed(action="error", title="❌ Cannot Moderate Staff", description=f"@{target.name} is a staff member, I will not do that.")
            await ctx.send(embed=embed)
            return True
        return False

    # ----------------------------- Basic moderation -----------------------------

    @commands.command(name="warn")
    @commands.guild_only()
    @commands_channel_check()
    @require_level("moderator")
    async def warn(self, ctx: commands.Context, member: discord.Member, *, reason: str) -> None:
        """Warn a member."""

        if await self._blocked_by_staff_immunity(ctx, member):
            return

        settings = await self._settings(ctx.guild)  # type: ignore[arg-type]

        dm_embed = make_embed(
            action="warn",
            title=f"⚠️ You were warned in {ctx.guild.name}",
            description=f"📝 Reason: {reason}",
        )
        await safe_dm(member, embed=dm_embed)

        warn_id = await self.db.add_warning(
            guild_id=ctx.guild.id,  # type: ignore[union-attr]
            user_id=member.id,
            moderator_id=ctx.author.id,
            reason=reason,
            warn_days=settings.warn_duration,
        )

        embed = make_embed(
            action="warn",
            title="⚠️ User Warned",
            description=f"👤 {member.mention} has been warned.\n\n📝 **Reason:** {reason}\n📍 **Warn ID:** `{warn_id}`",
        )
        embed.add_field(name="⏱️ Expires", value=f"In {settings.warn_duration} days", inline=True)
        embed.add_field(name="👮 Moderator", value=ctx.author.mention, inline=True)
        embed, file = attach_gif(embed, gif_key="WARN")

        message = await ctx.send(embed=embed, file=file)
        message_id = message.id

        await self.db.add_modlog(
            guild_id=ctx.guild.id,  # type: ignore[union-attr]
            action_type="warn",
            user_id=member.id,
            moderator_id=ctx.author.id,
            reason=reason,
            message_id=message_id,
        )

        owner_embed = make_embed(
            action="warn",
            title="Staff Action: warn",
            description=f"Guild: **{ctx.guild.name}** (`{ctx.guild.id}`)\nUser: {member} (`{member.id}`)\nModerator: {ctx.author} (`{ctx.author.id}`)\nReason: {reason}",
        )
        await notify_owner(self.bot, embed=owner_embed)

        await safe_delete(ctx.message)

    @commands.command(name="delwarn")
    @commands.guild_only()
    @commands_channel_check()
    @require_level("moderator")
    async def delwarn(self, ctx: commands.Context, member: discord.Member, warn_id: int) -> None:
        """Deactivate a warning by ID."""

        await self.db.deactivate_warning(warn_id=warn_id, guild_id=ctx.guild.id)  # type: ignore[union-attr]

        embed = make_embed(
            action="delwarn",
            title="🗑️ Warning Removed",
            description=f"📍 Removed warning `{warn_id}` for 👤 {member.mention}.",
        )
        embed, file = attach_gif(embed, gif_key="WARN_REMOVED")
        message = await ctx.send(embed=embed, file=file)

        await self.db.add_modlog(
            guild_id=ctx.guild.id,  # type: ignore[union-attr]
            action_type="unwarn",
            user_id=member.id,
            moderator_id=ctx.author.id,
            reason=f"Removed warning {warn_id}",
            message_id=message.id,
        )

        await safe_delete(ctx.message)

    @commands.command(name="warnings")
    @commands.guild_only()
    @commands_channel_check()
    @require_level("moderator")
    async def warnings(self, ctx: commands.Context, member: discord.Member) -> None:
        """List active warnings."""

        rows = await self.db.get_active_warnings(guild_id=ctx.guild.id, user_id=member.id)  # type: ignore[union-attr]
        if not rows:
            embed = make_embed(action="warnings", title="⚠️ Warnings", description=f"No active warnings for 👤 {member.mention}.")
            await ctx.send(embed=embed)
            return

        pages: list[Page] = []
        chunk_size = 5
        for i in range(0, len(rows), chunk_size):
            chunk = rows[i : i + chunk_size]
            embed = make_embed(action="warnings", title=f"⚠️ Active Warnings - {member}")
            for row in chunk:
                mod = f"<@{row['moderator_id']}>" if row["moderator_id"] else "Unknown"
                embed.add_field(
                    name=f"📍 ID {row['id']}",
                    value=f"📝 **Reason:** {row['reason']}\n👮 **Moderator:** {mod}",
                    inline=False,
                )
            pages.append(Page(embed=embed))

        view = PaginationView(pages=pages, author_id=ctx.author.id)
        await ctx.send(embed=pages[0].embed, view=view)

    @commands.command(name="modlogs")
    @commands.guild_only()
    @commands_channel_check()
    @require_level("moderator")
    async def modlogs(self, ctx: commands.Context, member: discord.Member) -> None:
        """Show modlog actions for a user."""

        rows = await self.db.get_modlogs_for_user(ctx.guild.id, member.id, limit=100)  # type: ignore[union-attr]
        if not rows:
            embed = make_embed(action="modlogs", title="📋 Modlogs", description=f"No modlogs for 👤 {member.mention}.")
            await ctx.send(embed=embed)
            return

        pages: list[Page] = []
        chunk_size = 10
        for i in range(0, len(rows), chunk_size):
            chunk = rows[i : i + chunk_size]
            embed = make_embed(action="modlogs", title=f"📋 Modlogs - {member}")
            for row in chunk:
                mod = f"<@{row['moderator_id']}>" if row["moderator_id"] else "Unknown"
                reason = row["reason"] or "(no reason)"
                embed.add_field(
                    name=f"{row['action_type']} | {row['timestamp']}",
                    value=f"👮 Moderator: {mod}\n📝 Reason: {reason}",
                    inline=False,
                )
            pages.append(Page(embed=embed))

        view = PaginationView(pages=pages, author_id=ctx.author.id)
        await ctx.send(embed=pages[0].embed, view=view)

    @commands.command(name="mute")
    @commands.guild_only()
    @commands_channel_check()
    @require_level("moderator")
    async def mute(self, ctx: commands.Context, member: discord.Member, duration: str, *, reason: str = "No reason provided") -> None:
        """Timeout (mute) a user."""

        if await self._blocked_by_staff_immunity(ctx, member):
            return

        seconds = parse_duration(duration)
        until = discord.utils.utcnow() + timedelta(seconds=seconds)

        dm_embed = make_embed(
            action="mute",
            title=f"🔇 You were muted in {ctx.guild.name}",
            description=f"⏱️ Duration: {humanize_seconds(seconds)}\n📝 Reason: {reason}",
        )
        await safe_dm(member, embed=dm_embed)

        try:
            await member.timeout(until, reason=reason)
        except discord.Forbidden:
            embed = make_embed(action="error", title="❌ Missing Permissions", description="I can't timeout that user.")
            await ctx.send(embed=embed)
            return

        await self.db.add_mute(
            guild_id=ctx.guild.id,  # type: ignore[union-attr]
            user_id=member.id,
            moderator_id=ctx.author.id,
            reason=reason,
            duration_seconds=seconds,
        )

        embed = make_embed(
            action="mute",
            title="🔇 User Muted",
            description=f"👤 {member.mention} has been muted for **{humanize_seconds(seconds)}**.\n\n📝 **Reason:** {reason}",
        )
        embed.add_field(name="👮 Moderator", value=ctx.author.mention, inline=True)
        embed, file = attach_gif(embed, gif_key="MUTE")
        message = await ctx.send(embed=embed, file=file)

        await self.db.add_modlog(
            guild_id=ctx.guild.id,  # type: ignore[union-attr]
            action_type="mute",
            user_id=member.id,
            moderator_id=ctx.author.id,
            reason=reason,
            message_id=message.id,
        )

        owner_embed = make_embed(
            action="mute",
            title="Staff Action: mute",
            description=f"Guild: **{ctx.guild.name}** (`{ctx.guild.id}`)\nUser: {member} (`{member.id}`)\nModerator: {ctx.author} (`{ctx.author.id}`)\nDuration: {humanize_seconds(seconds)}\nReason: {reason}",
        )
        await notify_owner(self.bot, embed=owner_embed)

        await safe_delete(ctx.message)

    @commands.command(name="unmute")
    @commands.guild_only()
    @commands_channel_check()
    @require_level("moderator")
    async def unmute(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided") -> None:
        """Remove timeout from a user."""

        dm_embed = make_embed(
            action="unmute",
            title=f"🔊 You were unmuted in {ctx.guild.name}",
            description=f"📝 Reason: {reason}",
        )
        await safe_dm(member, embed=dm_embed)

        try:
            await member.timeout(None, reason=reason)
        except discord.Forbidden:
            embed = make_embed(action="error", title="❌ Missing Permissions", description="I can't untimeout that user.")
            await ctx.send(embed=embed)
            return

        await self.db.deactivate_active_mutes(guild_id=ctx.guild.id, user_id=member.id)  # type: ignore[union-attr]

        embed = make_embed(action="unmute", title="🔊 User Unmuted", description=f"👤 {member.mention} has been unmuted.\n📝 Reason: {reason}")
        embed, file = attach_gif(embed, gif_key="UNMUTE")
        message = await ctx.send(embed=embed, file=file)

        await self.db.add_modlog(
            guild_id=ctx.guild.id,  # type: ignore[union-attr]
            action_type="unmute",
            user_id=member.id,
            moderator_id=ctx.author.id,
            reason=reason,
            message_id=message.id,
        )

        await safe_delete(ctx.message)

    @commands.command(name="kick")
    @commands.guild_only()
    @commands_channel_check()
    @require_level("moderator")
    async def kick(self, ctx: commands.Context, member: discord.Member, *, reason: str) -> None:
        """Kick a member."""

        if await self._blocked_by_staff_immunity(ctx, member):
            return

        dm_embed = make_embed(
            action="kick",
            title=f"👢 You were kicked from {ctx.guild.name}",
            description=f"📝 Reason: {reason}",
        )
        await safe_dm(member, embed=dm_embed)

        try:
            await member.kick(reason=reason)
        except discord.Forbidden:
            embed = make_embed(action="error", title="❌ Missing Permissions", description="I can't kick that user.")
            await ctx.send(embed=embed)
            return

        embed = make_embed(action="kick", title="👢 User Kicked", description=f"Kicked 👤 **{member}**.\n📝 Reason: {reason}")
        embed, file = attach_gif(embed, gif_key="KICK")
        message = await ctx.send(embed=embed, file=file)

        await self.db.add_modlog(
            guild_id=ctx.guild.id,  # type: ignore[union-attr]
            action_type="kick",
            user_id=member.id,
            moderator_id=ctx.author.id,
            reason=reason,
            message_id=message.id,
        )

        await safe_delete(ctx.message)

    @commands.command(name="ban")
    @commands.guild_only()
    @commands_channel_check()
    @require_level("moderator")
    async def ban(self, ctx: commands.Context, member: discord.Member, *, reason: str) -> None:
        """Ban a member."""

        if await self._blocked_by_staff_immunity(ctx, member):
            return

        dm_embed = make_embed(
            action="ban",
            title=f"🚫 You were banned from {ctx.guild.name}",
            description=f"📝 Reason: {reason}",
        )
        await safe_dm(member, embed=dm_embed)

        try:
            await ctx.guild.ban(member, reason=reason, delete_message_days=0)
        except discord.Forbidden:
            embed = make_embed(action="error", title="❌ Missing Permissions", description="I can't ban that user.")
            await ctx.send(embed=embed)
            return

        await self.db.add_ban(guild_id=ctx.guild.id, user_id=member.id, moderator_id=ctx.author.id, reason=reason)  # type: ignore[union-attr]

        embed = make_embed(action="ban", title="🚫 User Banned", description=f"Banned 👤 **{member}**.\n📝 Reason: {reason}")
        embed, file = attach_gif(embed, gif_key="BAN")
        message = await ctx.send(embed=embed, file=file)

        await self.db.add_modlog(
            guild_id=ctx.guild.id,  # type: ignore[union-attr]
            action_type="ban",
            user_id=member.id,
            moderator_id=ctx.author.id,
            reason=reason,
            message_id=message.id,
        )

        await safe_delete(ctx.message)

    @commands.command(name="unban")
    @commands.guild_only()
    @commands_channel_check()
    @require_level("moderator")
    async def unban(self, ctx: commands.Context, user: discord.User, *, reason: str = "No reason provided") -> None:
        """Unban a user."""

        try:
            await ctx.guild.unban(user, reason=reason)
        except discord.NotFound:
            embed = make_embed(action="error", title="❌ Not Banned", description="That user is not banned.")
            await ctx.send(embed=embed)
            return
        except discord.Forbidden:
            embed = make_embed(action="error", title="❌ Missing Permissions", description="I can't unban that user.")
            await ctx.send(embed=embed)
            return

        embed = make_embed(action="unban", title="✅ User Unbanned", description=f"Unbanned 👤 **{user}**.\n📝 Reason: {reason}")
        message = await ctx.send(embed=embed)

        await self.db.add_modlog(
            guild_id=ctx.guild.id,  # type: ignore[union-attr]
            action_type="unban",
            user_id=user.id,
            moderator_id=ctx.author.id,
            reason=reason,
            message_id=message.id,
        )

        await safe_delete(ctx.message)

    # ----------------------------- Senior moderator -----------------------------

    @commands.command(name="wm")
    @commands.guild_only()
    @commands_channel_check()
    @require_level("senior_mod")
    async def wm(self, ctx: commands.Context, member: discord.Member, duration: str, *, reason: str) -> None:
        """Warn + mute in a single command."""

        if await self._blocked_by_staff_immunity(ctx, member):
            return

        settings = await self._settings(ctx.guild)  # type: ignore[arg-type]
        seconds = parse_duration(duration)
        until = discord.utils.utcnow() + timedelta(seconds=seconds)

        dm_embed = make_embed(
            action="wm",
            title=f"⚠️🔇 You were warned and muted in {ctx.guild.name}",
            description=f"⏱️ Duration: {humanize_seconds(seconds)}\n📝 Reason: {reason}",
        )
        await safe_dm(member, embed=dm_embed)

        try:
            await member.timeout(until, reason=reason)
        except discord.Forbidden:
            embed = make_embed(action="error", title="❌ Missing Permissions", description="I can't timeout that user.")
            await ctx.send(embed=embed)
            return

        warn_id = await self.db.add_warning(
            guild_id=ctx.guild.id,  # type: ignore[union-attr]
            user_id=member.id,
            moderator_id=ctx.author.id,
            reason=reason,
            warn_days=settings.warn_duration,
        )
        await self.db.add_mute(
            guild_id=ctx.guild.id,  # type: ignore[union-attr]
            user_id=member.id,
            moderator_id=ctx.author.id,
            reason=reason,
            duration_seconds=seconds,
        )

        embed = make_embed(
            action="wm",
            title="⚠️🔇 Warned & Muted",
            description=(
                f"👤 {member.mention} has been warned and muted.\n\n"
                f"📍 **Warn ID:** `{warn_id}`\n"
                f"⏱️ **Mute Duration:** {humanize_seconds(seconds)}\n"
                f"📝 **Reason:** {reason}"
            ),
        )
        embed, file = attach_gif(embed, gif_key="WARN_AND_MUTE")
        message = await ctx.send(embed=embed, file=file)

        await self.db.add_modlog(
            guild_id=ctx.guild.id,  # type: ignore[union-attr]
            action_type="warn_and_mute",
            user_id=member.id,
            moderator_id=ctx.author.id,
            reason=reason,
            message_id=message.id,
        )

        await safe_delete(ctx.message)

    async def _parse_members_csv(self, ctx: commands.Context, raw: str) -> list[discord.Member]:
        members: list[discord.Member] = []
        for part in raw.split(","):
            part = part.strip()
            if not part:
                continue
            member_id = int(part) if part.isdigit() else extract_id(part)
            if not member_id:
                continue
            m = ctx.guild.get_member(int(member_id))  # type: ignore[union-attr]
            if m:
                members.append(m)
        return members

    @commands.command(name="masskick")
    @commands.guild_only()
    @commands_channel_check()
    @require_level("senior_mod")
    async def masskick(self, ctx: commands.Context, users: str, *, reason: str) -> None:
        """Kick multiple users (comma-separated)."""

        members = await self._parse_members_csv(ctx, users)
        if not members:
            embed = make_embed(action="error", title="❌ No Users", description="Provide a comma-separated list of users.")
            await ctx.send(embed=embed)
            return

        # Add loading reaction for long-running operation
        await add_loading_reaction(ctx.message)

        ok = 0
        failed = 0
        for m in members:
            if await self._blocked_by_staff_immunity(ctx, m):
                failed += 1
                continue
            await safe_dm(m, embed=make_embed(action="masskick", title=f"👢 You were kicked from {ctx.guild.name}", description=f"📝 Reason: {reason}"))
            try:
                await m.kick(reason=reason)
                ok += 1
                await self.db.add_modlog(guild_id=ctx.guild.id, action_type="kick", user_id=m.id, moderator_id=ctx.author.id, reason=reason)
            except Exception:
                failed += 1

        embed = make_embed(action="masskick", title="👢 Mass Kick Results", description=f"✔️ Succeeded: **{ok}**\n❌ Failed: **{failed}**")
        embed, file = attach_gif(embed, gif_key="KICK")
        await ctx.send(embed=embed, file=file)
        await safe_delete(ctx.message)

    @commands.command(name="massban")
    @commands.guild_only()
    @commands_channel_check()
    @require_level("senior_mod")
    async def massban(self, ctx: commands.Context, users: str, *, reason: str) -> None:
        """Ban multiple users (comma-separated)."""

        members = await self._parse_members_csv(ctx, users)
        if not members:
            embed = make_embed(action="error", title="❌ No Users", description="Provide a comma-separated list of users.")
            await ctx.send(embed=embed)
            return

        # Add loading reaction for long-running operation
        await add_loading_reaction(ctx.message)

        ok = 0
        failed = 0
        for m in members:
            if await self._blocked_by_staff_immunity(ctx, m):
                failed += 1
                continue
            await safe_dm(m, embed=make_embed(action="massban", title=f"🚫 You were banned from {ctx.guild.name}", description=f"📝 Reason: {reason}"))
            try:
                await ctx.guild.ban(m, reason=reason, delete_message_days=0)  # type: ignore[union-attr]
                await self.db.add_ban(guild_id=ctx.guild.id, user_id=m.id, moderator_id=ctx.author.id, reason=reason)  # type: ignore[union-attr]
                await self.db.add_modlog(guild_id=ctx.guild.id, action_type="ban", user_id=m.id, moderator_id=ctx.author.id, reason=reason)  # type: ignore[union-attr]
                ok += 1
            except Exception:
                failed += 1

        embed = make_embed(action="massban", title="🚫 Mass Ban Results", description=f"✔️ Succeeded: **{ok}**\n❌ Failed: **{failed}**")
        embed, file = attach_gif(embed, gif_key="BAN")
        await ctx.send(embed=embed, file=file)
        await safe_delete(ctx.message)

    @commands.command(name="massmute")
    @commands.guild_only()
    @commands_channel_check()
    @require_level("senior_mod")
    async def massmute(self, ctx: commands.Context, users: str, duration: str, *, reason: str) -> None:
        """Mute multiple users (comma-separated)."""

        members = await self._parse_members_csv(ctx, users)
        seconds = parse_duration(duration)
        until = discord.utils.utcnow() + timedelta(seconds=seconds)

        # Add loading reaction for long-running operation
        await add_loading_reaction(ctx.message)

        ok = 0
        failed = 0
        for m in members:
            if await self._blocked_by_staff_immunity(ctx, m):
                failed += 1
                continue
            await safe_dm(m, embed=make_embed(action="massmute", title=f"🔇 You were muted in {ctx.guild.name}", description=f"⏱️ Duration: {humanize_seconds(seconds)}\n📝 Reason: {reason}"))
            try:
                await m.timeout(until, reason=reason)
                await self.db.add_mute(guild_id=ctx.guild.id, user_id=m.id, moderator_id=ctx.author.id, reason=reason, duration_seconds=seconds)  # type: ignore[union-attr]
                await self.db.add_modlog(guild_id=ctx.guild.id, action_type="mute", user_id=m.id, moderator_id=ctx.author.id, reason=reason)  # type: ignore[union-attr]
                ok += 1
            except Exception:
                failed += 1

        embed = make_embed(action="massmute", title="🔇 Mass Mute Results", description=f"⏱️ Duration: {humanize_seconds(seconds)}\n✔️ Succeeded: **{ok}**\n❌ Failed: **{failed}**")
        embed, file = attach_gif(embed, gif_key="MUTE")
        await ctx.send(embed=embed, file=file)
        await safe_delete(ctx.message)

    # ----------------------------- Head moderator -----------------------------

    @commands.command(name="imprison")
    @commands.guild_only()
    @commands_channel_check()
    @require_level("head_mod")
    async def imprison(self, ctx: commands.Context, member: discord.Member, *, reason: str) -> None:
        """Remove all roles except @everyone and store them for later release."""

        if await self._blocked_by_staff_immunity(ctx, member):
            return

        stored_role_ids = [r.id for r in member.roles if r != ctx.guild.default_role]
        await self.db.add_imprisonment(guild_id=ctx.guild.id, user_id=member.id, moderator_id=ctx.author.id, role_ids=stored_role_ids)  # type: ignore[union-attr]

        try:
            await member.edit(roles=[], reason=reason)
        except discord.Forbidden:
            embed = make_embed(action="error", title="Missing Permissions", description="I can't edit that user's roles.")
            await ctx.send(embed=embed)
            return

        embed = make_embed(action="imprison", title="User Imprisoned", description=f"Removed all roles from {member.mention}.\nReason: {reason}")
        message = await ctx.send(embed=embed)

        await self.db.add_modlog(guild_id=ctx.guild.id, action_type="imprison", user_id=member.id, moderator_id=ctx.author.id, reason=reason, message_id=message.id)  # type: ignore[union-attr]
        await safe_delete(ctx.message)

    @commands.command(name="release")
    @commands.guild_only()
    @commands_channel_check()
    @require_level("head_mod")
    async def release(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided") -> None:
        """Restore roles stored by !imprison, or add member role."""

        settings = await self._settings(ctx.guild)  # type: ignore[arg-type]
        row = await self.db.get_active_imprisonment(guild_id=ctx.guild.id, user_id=member.id)  # type: ignore[union-attr]
        role_ids: list[int] = []
        if row is not None:
            try:
                parsed = json.loads(row["roles_json"])
                if isinstance(parsed, list):
                    role_ids = [int(v) for v in parsed if str(v).isdigit()]
            except Exception:
                role_ids = []

        roles = []
        for rid in role_ids:
            role = ctx.guild.get_role(int(rid))
            if role is not None:
                roles.append(role)

        if not roles and settings.member_role_id:
            role = ctx.guild.get_role(settings.member_role_id)
            if role:
                roles = [role]

        try:
            await member.edit(roles=roles, reason=reason)
        except discord.Forbidden:
            embed = make_embed(action="error", title="Missing Permissions", description="I can't edit that user's roles.")
            await ctx.send(embed=embed)
            return

        if row is not None:
            await self.db.deactivate_imprisonment(imprison_id=int(row["id"]))

        embed = make_embed(action="release", title="User Released", description=f"Restored roles for {member.mention}.\nReason: {reason}")
        message = await ctx.send(embed=embed)

        await self.db.add_modlog(guild_id=ctx.guild.id, action_type="release", user_id=member.id, moderator_id=ctx.author.id, reason=reason, message_id=message.id)  # type: ignore[union-attr]
        await safe_delete(ctx.message)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ModerationCog(bot))
