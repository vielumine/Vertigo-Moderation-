"""Admin-only commands (staff flagging, termination, channel locks, staff list)."""

from __future__ import annotations

import logging
from datetime import timedelta

import discord
from discord.ext import commands

from .. import config
from ..database import Database, GuildSettings
from ..helpers import (
    Page,
    PaginationView,
    add_loading_reaction,
    attach_gif,
    commands_channel_check,
    make_embed,
    notify_owner,
    require_admin,
    safe_delete,
    safe_dm,
)

logger = logging.getLogger(__name__)


class AdminCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @property
    def db(self) -> Database:
        return self.bot.db  # type: ignore[attr-defined]

    async def _settings(self, guild: discord.Guild) -> GuildSettings:
        return await self.db.get_guild_settings(guild.id, default_prefix=config.DEFAULT_PREFIX)

    @commands.command(name="flag")
    @commands.guild_only()
    @commands_channel_check()
    @require_admin()
    async def flag(self, ctx: commands.Context, member: discord.Member, *, reason: str) -> None:
        settings = await self._settings(ctx.guild)  # type: ignore[arg-type]
        flag_id = await self.db.add_staff_flag(
            guild_id=ctx.guild.id,  # type: ignore[union-attr]
            staff_user_id=member.id,
            admin_id=ctx.author.id,
            reason=reason,
            duration_days=settings.flag_duration,
        )
        active = await self.db.get_active_staff_flags(guild_id=ctx.guild.id, staff_user_id=member.id)  # type: ignore[union-attr]
        strike = len(active)

        title = "🚩 Staff Flag"
        if strike >= config.MAX_STAFF_FLAGS:
            title = f"⛔ Auto-Termination - {config.MAX_STAFF_FLAGS} strikes reached"

        embed = make_embed(
            action="flag",
            title=title,
            description=f"👤 Flagged {member.mention}.\n🆔 Strike: **{strike}/{config.MAX_STAFF_FLAGS}**\n📝 Reason: {reason}\n📍 ID: `{flag_id}`",
        )
        if strike >= config.MAX_STAFF_FLAGS:
            embed.add_field(name="⚠️ Warning", value="Auto-termination triggered!", inline=False)
        embed, file = attach_gif(embed, gif_key="STAFF_FLAG")
        message = await ctx.send(embed=embed, file=file)

        await self.db.add_modlog(
            guild_id=ctx.guild.id,  # type: ignore[union-attr]
            action_type="flag",
            user_id=member.id,
            moderator_id=ctx.author.id,
            reason=reason,
            message_id=message.id,
        )

        if strike >= config.MAX_STAFF_FLAGS:
            await self._terminate(ctx, member, reason=f"Auto-terminate: {config.MAX_STAFF_FLAGS} flags - {reason}")
            await safe_dm(ctx.author, embed=make_embed(action="terminate", title="Auto Terminate", description=f"{member} reached {config.MAX_STAFF_FLAGS} strikes and was terminated."))

        await safe_delete(ctx.message)

    @commands.command(name="unflag")
    @commands.guild_only()
    @commands_channel_check()
    @require_admin()
    async def unflag(self, ctx: commands.Context, member: discord.Member, strike_id: int) -> None:
        await self.db.deactivate_staff_flag(guild_id=ctx.guild.id, flag_id=strike_id)  # type: ignore[union-attr]

        active = await self.db.get_active_staff_flags(guild_id=ctx.guild.id, staff_user_id=member.id)  # type: ignore[union-attr]
        strike_count = len(active)

        embed = make_embed(
            action="unflag",
            title="🚩 Flag Removed",
            description=f"📍 Removed flag `{strike_id}` for 👤 {member.mention}.\n📊 Updated Strikes: **{strike_count}/{config.MAX_STAFF_FLAGS}**",
        )
        embed, file = attach_gif(embed, gif_key="STAFF_UNFLAG")
        message = await ctx.send(embed=embed, file=file)

        await self.db.add_modlog(
            guild_id=ctx.guild.id,  # type: ignore[union-attr]
            action_type="unflag",
            user_id=member.id,
            moderator_id=ctx.author.id,
            reason=f"Removed flag {strike_id}",
            message_id=message.id,
        )

        await safe_delete(ctx.message)

    async def _terminate(self, ctx: commands.Context, member: discord.Member, *, reason: str) -> None:
        settings = await self._settings(ctx.guild)  # type: ignore[arg-type]
        staff_ids = set(
            settings.staff_role_ids
            + settings.head_mod_role_ids
            + settings.senior_mod_role_ids
            + settings.moderator_role_ids
        )
        remove_roles = [r for r in member.roles if r.id in staff_ids]
        try:
            if remove_roles:
                await member.remove_roles(*remove_roles, reason=reason)
        except discord.Forbidden:
            pass

        try:
            await member.timeout(discord.utils.utcnow() + timedelta(days=7), reason=reason)
        except discord.Forbidden:
            pass

        await safe_dm(member, embed=make_embed(action="terminate", title=f"You were terminated in {ctx.guild.name}", description=reason))

        await self.db.add_modlog(
            guild_id=ctx.guild.id,  # type: ignore[union-attr]
            action_type="terminate",
            user_id=member.id,
            moderator_id=ctx.author.id,
            reason=reason,
        )

        owner_embed = make_embed(
            action="terminate",
            title="Staff Action: terminate",
            description=f"Guild: **{ctx.guild.name}** (`{ctx.guild.id}`)\nStaff: {member} (`{member.id}`)\nAdmin: {ctx.author} (`{ctx.author.id}`)\nReason: {reason}",
        )
        await notify_owner(self.bot, embed=owner_embed)

    @commands.command(name="terminate")
    @commands.guild_only()
    @commands_channel_check()
    @require_admin()
    async def terminate(self, ctx: commands.Context, member: discord.Member, *, reason: str = "Terminated") -> None:
        embed = make_embed(action="terminate", title="⛔ Terminating...", description=f"👤 Target: {member.mention}")
        await ctx.send(embed=embed)
        await self._terminate(ctx, member, reason=reason)
        confirm = make_embed(action="terminate", title="⛔ Staff Member Terminated", description=f"✅ Terminated 👤 {member.mention}.")
        confirm, file = attach_gif(confirm, gif_key="STAFF_TERMINATE")
        await ctx.send(embed=confirm, file=file)
        await safe_delete(ctx.message)

    @commands.command(name="lockchannels")
    @commands.guild_only()
    @commands_channel_check()
    @require_admin()
    async def lockchannels(self, ctx: commands.Context) -> None:
        settings = await self._settings(ctx.guild)  # type: ignore[arg-type]
        if not settings.lock_categories:
            embed = make_embed(action="error", title="❌ Not Configured", description="No lock categories set. Use !adminsetup.")
            await ctx.send(embed=embed)
            return

        if not settings.member_role_id:
            embed = make_embed(action="error", title="❌ No Member Role", description="No member role configured. Use !setup to set a member role first.")
            await ctx.send(embed=embed)
            return

        member_role = ctx.guild.get_role(settings.member_role_id)  # type: ignore[union-attr]
        if not member_role:
            embed = make_embed(action="error", title="❌ Role Not Found", description="Configured member role no longer exists. Use !setup to update.")
            await ctx.send(embed=embed)
            return

        # Add loading reaction for long-running operation
        await add_loading_reaction(ctx.message)

        ok = 0
        failed = 0
        for cat_id in settings.lock_categories:
            category = ctx.guild.get_channel(cat_id)  # type: ignore[union-attr]
            if not isinstance(category, discord.CategoryChannel):
                continue
            for channel in category.text_channels:
                overwrite = channel.overwrites_for(member_role)
                overwrite.send_messages = False
                try:
                    await channel.set_permissions(member_role, overwrite=overwrite, reason=f"lockchannels by {ctx.author}")
                    ok += 1
                    await self.db.add_modlog(guild_id=ctx.guild.id, action_type="lock", user_id=None, moderator_id=ctx.author.id, target_id=channel.id, reason="lockchannels")  # type: ignore[union-attr]
                except Exception:
                    failed += 1

        embed = make_embed(action="lockchannels", title="🔒 Categories Locked", description=f"✔️ Locked: **{ok}**\n❌ Failed: **{failed}**")
        await ctx.send(embed=embed)

    @commands.command(name="unlockchannels")
    @commands.guild_only()
    @commands_channel_check()
    @require_admin()
    async def unlockchannels(self, ctx: commands.Context) -> None:
        settings = await self._settings(ctx.guild)  # type: ignore[arg-type]
        if not settings.lock_categories:
            embed = make_embed(action="error", title="❌ Not Configured", description="No lock categories set. Use !adminsetup.")
            await ctx.send(embed=embed)
            return

        if not settings.member_role_id:
            embed = make_embed(action="error", title="❌ No Member Role", description="No member role configured. Use !setup to set a member role first.")
            await ctx.send(embed=embed)
            return

        member_role = ctx.guild.get_role(settings.member_role_id)  # type: ignore[union-attr]
        if not member_role:
            embed = make_embed(action="error", title="❌ Role Not Found", description="Configured member role no longer exists. Use !setup to update.")
            await ctx.send(embed=embed)
            return

        # Add loading reaction for long-running operation
        await add_loading_reaction(ctx.message)

        ok = 0
        failed = 0
        for cat_id in settings.lock_categories:
            category = ctx.guild.get_channel(cat_id)  # type: ignore[union-attr]
            if not isinstance(category, discord.CategoryChannel):
                continue
            for channel in category.text_channels:
                overwrite = channel.overwrites_for(member_role)
                overwrite.send_messages = None
                try:
                    await channel.set_permissions(member_role, overwrite=overwrite, reason=f"unlockchannels by {ctx.author}")
                    ok += 1
                    await self.db.add_modlog(guild_id=ctx.guild.id, action_type="unlock", user_id=None, moderator_id=ctx.author.id, target_id=channel.id, reason="unlockchannels")  # type: ignore[union-attr]
                except Exception:
                    failed += 1

        embed = make_embed(action="unlockchannels", title="🔓 Categories Unlocked", description=f"✔️ Unlocked: **{ok}**\n❌ Failed: **{failed}**")
        await ctx.send(embed=embed)

    @commands.command(name="scanacc")
    @commands.guild_only()
    @commands_channel_check()
    @require_admin()
    async def scanacc(self, ctx: commands.Context, member: discord.Member) -> None:
        now = discord.utils.utcnow()
        age_days = (now - member.created_at).days
        embed = make_embed(action="scanacc", title="🔍 Account Scan", description=f"👤 User: {member.mention} ({member.id})")
        embed.add_field(name="📅 Account Age", value=f"{age_days} days", inline=True)
        embed.add_field(name="🆕 New Account (< 7d)", value="Yes" if age_days < 7 else "No", inline=True)

        # very lightweight alt check: same name prefix
        similar = [m for m in ctx.guild.members if m.id != member.id and m.name.lower().startswith(member.name.lower()[:4])]  # type: ignore[union-attr]
        embed.add_field(name="👥 Similar Usernames", value=str(len(similar)), inline=True)
        if age_days < 7 or len(similar) >= 3:
            embed.add_field(name="⚠️ Suspicious", value="Yes", inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="stafflist")
    @commands.guild_only()
    @commands_channel_check()
    @require_admin()
    async def stafflist(self, ctx: commands.Context) -> None:
        settings = await self._settings(ctx.guild)  # type: ignore[arg-type]

        def has(role_ids: list[int], member: discord.Member) -> bool:
            return any(r.id in set(role_ids) for r in member.roles)

        def get_flag_emoji(strike_count: int) -> str:
            if strike_count == 0:
                return ""
            elif strike_count <= 2:
                return "✅"
            elif strike_count == 3:
                return "⚠️"
            elif strike_count == 4:
                return "🟠"
            else:
                return "🔴"

        mods = [m for m in ctx.guild.members if has(settings.moderator_role_ids, m)]  # type: ignore[union-attr]
        seniors = [m for m in ctx.guild.members if has(settings.senior_mod_role_ids, m)]  # type: ignore[union-attr]
        heads = [m for m in ctx.guild.members if has(settings.head_mod_role_ids, m)]  # type: ignore[union-attr]

        entries: list[tuple[str, list[discord.Member]]] = [
            ("Head Moderators", heads),
            ("Senior Moderators", seniors),
            ("Moderators", mods),
        ]

        pages: list[Page] = []
        for title, members in entries:
            embed = make_embed(action="stafflist", title=f"👮 {title}")
            if members:
                lines: list[str] = []
                for m in members[:50]:
                    flags = await self.db.get_active_staff_flags(guild_id=ctx.guild.id, staff_user_id=m.id)  # type: ignore[union-attr]
                    strike_count = len(flags)
                    emoji = get_flag_emoji(strike_count)
                    if strike_count > 0:
                        lines.append(f"👤 {m} (`{m.id}`) - {emoji} 🚩 Flags: **{strike_count}/{config.MAX_STAFF_FLAGS}**")
                    else:
                        lines.append(f"👤 {m} (`{m.id}`)")
                embed.description = "\n".join(lines)
            else:
                embed.description = "None"
            pages.append(Page(embed=embed))

        view = PaginationView(pages=pages, author_id=ctx.author.id)
        await ctx.send(embed=pages[0].embed, view=view)

    @commands.command(name="wasstaff")
    @commands.guild_only()
    @commands_channel_check()
    @require_admin()
    async def wasstaff(self, ctx: commands.Context, user: discord.User) -> None:
        rows = await self.db.get_modlogs_as_moderator(ctx.guild.id, user.id, limit=10)  # type: ignore[union-attr]
        if not rows:
            embed = make_embed(action="wasstaff", title="👮 Staff History", description=f"No staff action record for 👤 **{user}**.")
            await ctx.send(embed=embed)
            return
        embed = make_embed(action="wasstaff", title="👮 Staff History", description=f"Recent actions by 👤 **{user}**:")
        for row in rows:
            embed.add_field(name=row["action_type"], value=row["timestamp"], inline=False)
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AdminCog(bot))
