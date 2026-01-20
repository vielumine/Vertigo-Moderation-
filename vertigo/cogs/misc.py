"""Miscellaneous user-facing commands (info, ping, help, etc.)."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

import discord
from discord.ext import commands

from vertigo import config
from vertigo.database import Database
from vertigo.helpers import (
    commands_channel_check,
    make_embed,
    require_level,
    safe_delete,
    timed_rest_call,
)

logger = logging.getLogger(__name__)


def _fmt_dt(dt: datetime | None) -> str:
    if dt is None:
        return "Unknown"
    return discord.utils.format_dt(dt)


class HelpView(discord.ui.View):
    def __init__(self, *, author_id: int, pages: dict[str, discord.Embed]) -> None:
        super().__init__(timeout=180)
        self.author_id = author_id
        self.pages = pages

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user and interaction.user.id != self.author_id:
            await interaction.response.send_message("This menu isn't for you.", ephemeral=True)
            return False
        return True

    async def _show(self, interaction: discord.Interaction, key: str) -> None:
        await interaction.response.edit_message(embed=self.pages[key], view=self)

    @discord.ui.button(label="⚠️ Moderation", style=discord.ButtonStyle.secondary)
    async def moderation(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:  # type: ignore[override]
        await self._show(interaction, "moderation")

    @discord.ui.button(label="📌 Roles", style=discord.ButtonStyle.secondary)
    async def roles(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:  # type: ignore[override]
        await self._show(interaction, "roles")

    @discord.ui.button(label="⏱️ Channels", style=discord.ButtonStyle.secondary)
    async def channels(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:  # type: ignore[override]
        await self._show(interaction, "channels")

    @discord.ui.button(label="📋 Miscellaneous", style=discord.ButtonStyle.secondary)
    async def misc(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:  # type: ignore[override]
        await self._show(interaction, "misc")

    @discord.ui.button(label="🧹 Cleaning", style=discord.ButtonStyle.secondary)
    async def cleaning(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:  # type: ignore[override]
        await self._show(interaction, "cleaning")

    @discord.ui.button(label="👤 Member", style=discord.ButtonStyle.secondary)
    async def member(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:  # type: ignore[override]
        await self._show(interaction, "member")


class MiscCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @property
    def db(self) -> Database:
        return self.bot.db  # type: ignore[attr-defined]

    @commands.command(name="userinfo")
    @commands.guild_only()
    @commands_channel_check()
    @require_level("moderator")
    async def userinfo(self, ctx: commands.Context, member: discord.Member) -> None:
        roles = [r.mention for r in member.roles if r != ctx.guild.default_role]
        embed = make_embed(action="userinfo", title=f"👤 User Information - {member}")
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="📍 ID", value=str(member.id), inline=True)
        embed.add_field(name="🤖 Bot", value="Yes" if member.bot else "No", inline=True)
        embed.add_field(name="📅 Account Created", value=_fmt_dt(member.created_at), inline=False)
        embed.add_field(name="📅 Joined Server", value=_fmt_dt(member.joined_at), inline=False)
        embed.add_field(name="📌 Roles", value=", ".join(roles) if roles else "None", inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="serverinfo")
    @commands.guild_only()
    @commands_channel_check()
    @require_level("moderator")
    async def serverinfo(self, ctx: commands.Context) -> None:
        guild = ctx.guild
        embed = make_embed(action="serverinfo", title=f"🏢 Server Information - {guild.name}")
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        embed.add_field(name="📍 ID", value=str(guild.id), inline=True)
        embed.add_field(name="👑 Owner", value=f"{guild.owner} ({guild.owner_id})", inline=False)
        embed.add_field(name="📅 Created", value=_fmt_dt(guild.created_at), inline=False)
        embed.add_field(name="👥 Members", value=str(guild.member_count or len(guild.members)), inline=True)
        embed.add_field(name="📌 Roles", value=str(len(guild.roles)), inline=True)
        embed.add_field(name="💬 Channels", value=str(len(guild.channels)), inline=True)
        embed.add_field(name="🔒 Verification", value=str(guild.verification_level).title(), inline=True)
        await ctx.send(embed=embed)

    @commands.command(name="checkavatar")
    @commands.guild_only()
    @commands_channel_check()
    @require_level("moderator")
    async def checkavatar(self, ctx: commands.Context, user: discord.User) -> None:
        embed = make_embed(action="checkavatar", title=f"🖼️ User Avatar - {user}")
        embed.set_image(url=user.display_avatar.url)
        embed.add_field(name="🔗 URL", value=user.display_avatar.url, inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="checkbanner")
    @commands.guild_only()
    @commands_channel_check()
    @require_level("moderator")
    async def checkbanner(self, ctx: commands.Context, user: discord.User) -> None:
        fetched = await self.bot.fetch_user(user.id)
        banner_url = fetched.banner.url if fetched.banner else None
        embed = make_embed(action="checkbanner", title=f"🖼️ User Banner - {user}")
        if banner_url:
            embed.set_image(url=banner_url)
            embed.add_field(name="🔗 URL", value=banner_url, inline=False)
        else:
            embed.description = "User has no banner."
        await ctx.send(embed=embed)

    @commands.command(name="members")
    @commands.guild_only()
    @commands_channel_check()
    @require_level("moderator")
    async def members(self, ctx: commands.Context) -> None:
        guild = ctx.guild
        embed = make_embed(action="members", title="👥 Member Count", description=f"Total members: **{guild.member_count or len(guild.members)}**")
        await ctx.send(embed=embed)

    @commands.command(name="roleperms")
    @commands.guild_only()
    @commands_channel_check()
    @require_level("moderator")
    async def roleperms(self, ctx: commands.Context, role: discord.Role) -> None:
        enabled = [name.replace("_", " ").title() for name, value in role.permissions if value]
        embed = make_embed(action="roleperms", title=f"🔐 Role Permissions - {role.name}")
        embed.description = "\n".join(enabled) if enabled else "No enabled permissions."
        await ctx.send(embed=embed)

    @commands.command(name="changenick")
    @commands.guild_only()
    @commands_channel_check()
    @require_level("moderator")
    async def changenick(self, ctx: commands.Context, member: discord.Member, *, nickname: str) -> None:
        if len(nickname) > 32:
            embed = make_embed(action="error", title="❌ Too Long", description="Nickname must be <= 32 characters.")
            await ctx.send(embed=embed)
            return
        try:
            await member.edit(nick=nickname, reason=f"Nick changed by {ctx.author}")
        except discord.Forbidden:
            embed = make_embed(action="error", title="❌ Missing Permissions", description="I can't change that nickname.")
            await ctx.send(embed=embed)
            return
        embed = make_embed(action="changenick", title="🏷️ Nickname Changed", description=f"Changed nickname for 👤 {member.mention}.")
        await ctx.send(embed=embed)
        await safe_delete(ctx.message)

    @commands.command(name="removenick")
    @commands.guild_only()
    @commands_channel_check()
    @require_level("moderator")
    async def removenick(self, ctx: commands.Context, member: discord.Member) -> None:
        try:
            await member.edit(nick=None, reason=f"Nick removed by {ctx.author}")
        except discord.Forbidden:
            embed = make_embed(action="error", title="❌ Missing Permissions", description="I can't remove that nickname.")
            await ctx.send(embed=embed)
            return
        embed = make_embed(action="removenick", title="🏷️ Nickname Removed", description=f"Removed nickname for 👤 {member.mention}.")
        await ctx.send(embed=embed)
        await safe_delete(ctx.message)

    @commands.command(name="wasbanned")
    @commands.guild_only()
    @commands_channel_check()
    @require_level("moderator")
    async def wasbanned(self, ctx: commands.Context, user: discord.User) -> None:
        row = await self.db.get_last_ban(guild_id=ctx.guild.id, user_id=user.id)  # type: ignore[union-attr]
        if row is None:
            embed = make_embed(action="wasbanned", title="📍 Ban History", description=f"No ban record for 👤 **{user}**.")
            await ctx.send(embed=embed)
            return
        embed = make_embed(action="wasbanned", title="📍 Ban History", description=f"👤 **{user}** was banned.")
        embed.add_field(name="📝 Reason", value=row["reason"], inline=False)
        embed.add_field(name="👮 Moderator", value=f"<@{row['moderator_id']}>", inline=True)
        embed.add_field(name="📅 When", value=row["timestamp"], inline=True)
        await ctx.send(embed=embed)

    @commands.command(name="checkdur")
    @commands.guild_only()
    @commands_channel_check()
    @require_level("moderator")
    async def checkdur(self, ctx: commands.Context, member: discord.Member) -> None:
        until = member.communication_disabled_until
        if until is None:
            embed = make_embed(action="checkdur", title="⏱️ Timeout Duration", description="User is not muted.")
            await ctx.send(embed=embed)
            return
        now = discord.utils.utcnow()
        remaining = int((until - now).total_seconds())
        embed = make_embed(action="checkdur", title="⏱️ Timeout Duration", description=f"Remaining: **{max(0, remaining)}s**")
        embed.add_field(name="📅 Ends", value=discord.utils.format_dt(until), inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="ping")
    @commands.guild_only()
    @commands_channel_check()
    async def ping(self, ctx: commands.Context) -> None:
        """Latency information."""

        start = time.perf_counter()
        placeholder = await ctx.send(embed=make_embed(action="ping", title="🏓 Pinging..."))
        message_ping = (time.perf_counter() - start) * 1000.0

        heartbeat = self.bot.latency * 1000.0

        try:
            _, rest_ms = await timed_rest_call(self.bot.fetch_user(self.bot.user.id))  # type: ignore[union-attr]
        except Exception:
            rest_ms = 0.0

        embed = make_embed(action="ping", title="🏓 Bot Ping")
        embed.add_field(name="📧 Message Ping", value=f"{message_ping:.0f} ms", inline=True)
        embed.add_field(name="💓 Heartbeat", value=f"{heartbeat:.0f} ms", inline=True)
        embed.add_field(name="🌐 REST", value=f"{rest_ms:.0f} ms", inline=True)

        await placeholder.edit(embed=embed)

    # ----------------------------- Help system -----------------------------

    @commands.command(name="help")
    @commands.guild_only()
    @commands_channel_check()
    async def help(self, ctx: commands.Context) -> None:
        prefix = (await self.db.get_guild_settings(ctx.guild.id, default_prefix=config.DEFAULT_PREFIX)).prefix  # type: ignore[union-attr]

        pages: dict[str, discord.Embed] = {
            "moderation": make_embed(
                action="help",
                title="📖 Moderation Commands",
                description=(
                    f"`{prefix}warn <user> <reason>`\n"
                    f"`{prefix}delwarn <user> <warn_id>`\n"
                    f"`{prefix}mute <user> <duration> [reason]`\n"
                    f"`{prefix}unmute <user> [reason]`\n"
                    f"`{prefix}kick <user> <reason>`\n"
                    f"`{prefix}ban <user> <reason>`\n"
                    f"`{prefix}unban <user> <reason>`\n"
                    f"`{prefix}warnings <user>`\n"
                    f"`{prefix}modlogs <user>`\n"
                    f"`{prefix}wm <user> <duration> <reason>`\n"
                    f"`{prefix}masskick <users,users> <reason>`\n"
                    f"`{prefix}massban <users,users> <reason>`\n"
                    f"`{prefix}massmute <users,users> <duration> <reason>`\n"
                    f"`{prefix}imprison <user> <reason>`\n"
                    f"`{prefix}release <user> [reason]`"
                ),
            ),
            "roles": make_embed(
                action="help",
                title="Help - Roles",
                description=(
                    f"`{prefix}role <user> <role>`\n"
                    f"`{prefix}removerole <user> <role>`\n"
                    f"`{prefix}temprole <user> <role> <duration>`\n"
                    f"`{prefix}removetemp <user> <role>`\n"
                    f"`{prefix}persistrole <user> <role>`\n"
                    f"`{prefix}removepersist <user> <role>`\n"
                    f"`{prefix}massrole <users,users> <role>`\n"
                    f"`{prefix}massremoverole <users,users> <role>`\n"
                    f"`{prefix}masstemprole <users,users> <role> <duration>`\n"
                    f"`{prefix}massremovetemp <users,users> <role>`\n"
                    f"`{prefix}masspersistrole <users,users> <role>`\n"
                    f"`{prefix}massremovepersist <users,users> <role>`"
                ),
            ),
            "channels": make_embed(
                action="help",
                title="Help - Channels",
                description=(
                    f"`{prefix}checkslowmode [channel]`\n"
                    f"`{prefix}setslowmode [channel] <duration>`\n"
                    f"`{prefix}massslow <channels,channels> <duration>`\n"
                    f"`{prefix}lock [channel]`\n"
                    f"`{prefix}unlock [channel]`\n"
                    f"`{prefix}hide [channel]`\n"
                    f"`{prefix}unhide [channel]`\n"
                    f"`{prefix}message <channel> <message>`\n"
                    f"`{prefix}editmess <message_id> <new_message>`\n"
                    f"`{prefix}replymess <message_id> <reply>`\n"
                    f"`{prefix}deletemess <message_id>`"
                ),
            ),
            "misc": make_embed(
                action="help",
                title="Help - Misc",
                description=(
                    f"`{prefix}userinfo <user>`\n"
                    f"`{prefix}serverinfo`\n"
                    f"`{prefix}checkavatar <user>`\n"
                    f"`{prefix}checkbanner <user>`\n"
                    f"`{prefix}members`\n"
                    f"`{prefix}ping`\n"
                    f"`{prefix}wasbanned <user>`\n"
                    f"`{prefix}checkdur <user>`\n"
                    f"`{prefix}changenick <user> <nickname>`\n"
                    f"`{prefix}removenick <user>`\n"
                    f"`{prefix}roleperms <role>`"
                ),
            ),
            "cleaning": make_embed(
                action="help",
                title="Help - Cleaning",
                description=(
                    f"`{prefix}clean [amount]`\n"
                    f"`{prefix}purge <amount>`\n"
                    f"`{prefix}purgeuser <user> <amount>`\n"
                    f"`{prefix}purgematch <keyword> <amount>`"
                ),
            ),
            "member": make_embed(
                action="help",
                title="Help - Member",
                description=(
                    f"`{prefix}mywarns`\n"
                    f"`{prefix}myavatar`\n"
                    f"`{prefix}mybanner`\n"
                    f"`{prefix}myinfo`\n"
                    f"`{prefix}translate <text> [target_language]`"
                ),
            ),
        }

        view = HelpView(author_id=ctx.author.id, pages=pages)
        await ctx.send(embed=pages["moderation"], view=view)

    @commands.command(name="adcmd")
    @commands.guild_only()
    @commands_channel_check()
    @require_level("admin")
    async def adcmd(self, ctx: commands.Context) -> None:
        prefix = (await self.db.get_guild_settings(ctx.guild.id, default_prefix=config.DEFAULT_PREFIX)).prefix  # type: ignore[union-attr]
        embed = make_embed(
            action="adcmd",
            title="Admin Commands",
            description=(
                f"`{prefix}flag <staff_user> <reason>`\n"
                f"`{prefix}unflag <staff_user> <strike_id>`\n"
                f"`{prefix}terminate <staff_user>`\n"
                f"`{prefix}lockchannels`\n"
                f"`{prefix}unlockchannels`\n"
                f"`{prefix}scanacc <user>`\n"
                f"`{prefix}stafflist`\n"
                f"`{prefix}wasstaff <user>`"
            ),
        )
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MiscCog(bot))
