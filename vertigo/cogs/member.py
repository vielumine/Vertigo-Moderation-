"""Member self-service commands."""

from __future__ import annotations

import logging

import discord
from discord.ext import commands

import config
from database import Database
from helpers import (
    commands_channel_check,
    discord_timestamp,
    get_trial_mod_status,
    get_user_type,
    make_embed,
    require_admin,
    require_level,
    role_level_for_member,
)

logger = logging.getLogger(__name__)


class MemberCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @property
    def db(self) -> Database:
        return self.bot.db  # type: ignore[attr-defined]

    @commands.command(name="mywarns")
    @commands.guild_only()
    @commands_channel_check()
    async def mywarns(self, ctx: commands.Context) -> None:
        rows = await self.db.get_active_warnings(guild_id=ctx.guild.id, user_id=ctx.author.id)  # type: ignore[union-attr]
        if not rows:
            embed = make_embed(action="mywarns", title="⚠️ Your Warnings", description="You have no active warnings.")
            await ctx.send(embed=embed)
            return

        embed = make_embed(action="mywarns", title="⚠️ Your Active Warnings")
        for idx, row in enumerate(rows[:10], start=1):
            expires_str = discord_timestamp(row['expires_at'], 'R')
            embed.add_field(name=f"📍 Warn #{idx}", value=f"📝 Reason: {row['reason']}\n⏱️ Expires: {expires_str}", inline=False)

        await ctx.send(embed=embed)

    @commands.command(name="myavatar")
    @commands.guild_only()
    @commands_channel_check()
    async def myavatar(self, ctx: commands.Context) -> None:
        user = ctx.author
        embed = make_embed(action="myavatar", title="🖼️ Your Avatar")
        embed.set_image(url=user.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.command(name="mybanner")
    @commands.guild_only()
    @commands_channel_check()
    async def mybanner(self, ctx: commands.Context) -> None:
        fetched = await self.bot.fetch_user(ctx.author.id)
        banner_url = fetched.banner.url if fetched.banner else None
        embed = make_embed(action="mybanner", title="🖼️ Your Banner")
        if banner_url:
            embed.set_image(url=banner_url)
            embed.add_field(name="🔗 URL", value=banner_url, inline=False)
        else:
            embed.description = "You have no banner."
        await ctx.send(embed=embed)

    @commands.command(name="myinfo")
    @commands.guild_only()
    @commands_channel_check()
    async def myinfo(self, ctx: commands.Context) -> None:
        """Show your user information including type, trial status, dates, and warnings."""
        if not isinstance(ctx.author, discord.Member):
            return
        await self._send_user_info(ctx, ctx.author, is_self=True)

    async def _send_user_info(self, ctx: commands.Context, member: discord.Member, *, is_self: bool = False) -> None:
        """Build and send user info embed."""
        # Get guild settings
        settings = await self.db.get_guild_settings(ctx.guild.id, default_prefix=config.DEFAULT_PREFIX)  # type: ignore[union-attr]
        trial_mod_roles = await self.db.get_trial_mod_roles(ctx.guild.id)  # type: ignore[union-attr]

        # Get user type and trial status
        user_type = get_user_type(member, settings)
        trial_status = get_trial_mod_status(member, trial_mod_roles)

        # Get warning count
        warnings = await self.db.get_active_warnings(guild_id=ctx.guild.id, user_id=member.id)  # type: ignore[union-attr]
        warning_count = len(warnings)

        # Build embed
        title = "👤 Your Information" if is_self else f"👤 User Information - {member}"
        embed = make_embed(action="myinfo", title=title)
        embed.set_thumbnail(url=member.display_avatar.url)

        # Basic info
        embed.add_field(name="📍 ID", value=str(member.id), inline=True)
        embed.add_field(name="🛡️ User Type", value=user_type, inline=True)

        # Trial status (if applicable)
        if trial_status:
            embed.add_field(name="⭐ Status", value=trial_status, inline=True)

        # Account age and join date using Unix timestamps
        embed.add_field(
            name="📅 Account Created",
            value=discord_timestamp(member.created_at, "f") + f"\n({discord_timestamp(member.created_at, 'R')})",
            inline=False
        )
        if member.joined_at:
            embed.add_field(
                name="📅 Joined Server",
                value=discord_timestamp(member.joined_at, "f") + f"\n({discord_timestamp(member.joined_at, 'R')})",
                inline=False
            )

        # Current warnings
        warning_emoji = "⚠️" if warning_count > 0 else "✅"
        embed.add_field(name=f"{warning_emoji} Current Warnings", value=str(warning_count), inline=True)

        # If viewing another user who is staff, show mod stats
        if not is_self:
            level = role_level_for_member(member, settings, trial_mod_role_ids=trial_mod_roles)
            if level in ("trial_mod", "moderator", "senior_mod", "head_mod", "admin"):
                stats = await self.db.get_mod_stats(ctx.guild.id, member.id)
                total_actions = stats["warns_total"] + stats["mutes_total"] + stats["kicks_total"] + stats["bans_total"]
                embed.add_field(name="📊 Mod Actions (30d)", value=str(total_actions), inline=True)

        # Roles (show on self view, or for others show briefly)
        roles = [r.mention for r in member.roles if r != ctx.guild.default_role]
        if len(roles) > 10:
            roles = roles[:10] + [f"... and {len(roles) - 10} more"]
        embed.add_field(name="📌 Roles", value=", ".join(roles) if roles else "None", inline=False)

        await ctx.send(embed=embed)

    @commands.command(name="checkinfo")
    @commands.guild_only()
    @commands_channel_check()
    @require_level("moderator")
    async def checkinfo(self, ctx: commands.Context, member: discord.Member) -> None:
        """Check information about another user.

        Usage: !checkinfo <user>
        Shows: User type, trial status, join date, account age, current warnings.
        If user is staff, also shows mod stats.
        """
        await self._send_user_info(ctx, member, is_self=False)

    @commands.command(name="myflags")
    @commands.guild_only()
    @commands_channel_check()
    @require_level("trial_mod")
    async def myflags(self, ctx: commands.Context) -> None:
        """Show your staff flags (staff only).

        Shows all active flags with reason and danger points.
        """
        if not isinstance(ctx.author, discord.Member):
            return

        # Get active flags for the staff member
        flags = await self.db.get_active_staff_flags(guild_id=ctx.guild.id, staff_user_id=ctx.author.id)  # type: ignore[union-attr]

        embed = make_embed(action="myflags", title="🚩 Your Staff Flags")
        embed.set_thumbnail(url=ctx.author.display_avatar.url)

        if not flags:
            embed.description = "✅ You have no active flags. Great job!"
            embed.add_field(name="Danger Level", value="🟢 Safe (0/5)", inline=False)
            await ctx.send(embed=embed)
            return

        # Calculate danger level
        danger_level = len(flags)

        # List flags
        for idx, flag in enumerate(flags, start=1):
            expires_str = discord_timestamp(flag["expires_at"], "R")
            embed.add_field(
                name=f"🚩 Flag #{idx}",
                value=f"**Reason:** {flag['reason']}\n**Expires:** {expires_str}",
                inline=False
            )

        # Danger level indicator
        if danger_level >= 5:
            danger_text = f"🔴 CRITICAL ({danger_level}/5) - Auto-termination at 5 flags!"
        elif danger_level >= 3:
            danger_text = f"🟠 Warning ({danger_level}/5)"
        elif danger_level >= 1:
            danger_text = f"🟡 Caution ({danger_level}/5)"
        else:
            danger_text = f"🟢 Safe ({danger_level}/5)"

        embed.add_field(name="⚠️ Danger Level", value=danger_text, inline=False)

        await ctx.send(embed=embed)

    @commands.command(name="checkflags")
    @commands.guild_only()
    @commands_channel_check()
    @require_admin()
    async def checkflags(self, ctx: commands.Context, member: discord.Member) -> None:
        """Check another staff member's flags (admin only).

        Usage: !checkflags <staff_member>
        Shows: All active flags with reason and danger level.
        """
        # Get active flags for the staff member
        flags = await self.db.get_active_staff_flags(guild_id=ctx.guild.id, staff_user_id=member.id)  # type: ignore[union-attr]

        embed = make_embed(action="checkflags", title=f"🚩 Staff Flags - {member}")
        embed.set_thumbnail(url=member.display_avatar.url)

        if not flags:
            embed.description = f"✅ {member.mention} has no active flags."
            embed.add_field(name="Danger Level", value="🟢 Safe (0/5)", inline=False)
            await ctx.send(embed=embed)
            return

        # Calculate danger level
        danger_level = len(flags)

        # List flags
        for idx, flag in enumerate(flags, start=1):
            expires_str = discord_timestamp(flag["expires_at"], "R")
            embed.add_field(
                name=f"🚩 Flag #{idx}",
                value=f"**Reason:** {flag['reason']}\n**Expires:** {expires_str}",
                inline=False
            )

        # Danger level indicator
        if danger_level >= 5:
            danger_text = f"🔴 CRITICAL ({danger_level}/5) - Auto-termination at 5 flags!"
        elif danger_level >= 3:
            danger_text = f"🟠 Warning ({danger_level}/5)"
        elif danger_level >= 1:
            danger_text = f"🟡 Caution ({danger_level}/5)"
        else:
            danger_text = f"🟢 Safe ({danger_level}/5)"

        embed.add_field(name="⚠️ Danger Level", value=danger_text, inline=False)

        await ctx.send(embed=embed)

    @commands.command(name="afk")
    @commands.guild_only()
    async def afk(self, ctx: commands.Context, *, reason: str | None = None) -> None:
        """Set yourself as AFK with an optional reason.

        Usage: !afk [reason]
        """
        if ctx.author.bot:
            return

        await self.db.set_afk(user_id=ctx.author.id, guild_id=ctx.guild.id, reason=reason)

        reason_text = f" - {reason}" if reason else ""
        embed = make_embed(
            action="success",
            title="💤 AFK Status Set",
            description=f"You are now AFK{reason_text}\n\nYou'll be notified of any pings when you return."
        )
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MemberCog(bot))
