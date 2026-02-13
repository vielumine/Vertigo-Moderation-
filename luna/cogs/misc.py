"""Miscellaneous user-facing commands (info, ping, help, etc.)."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

import discord
from discord.ext import commands

import config
from database import Database
from helpers import (
    Page,
    PaginationView,
    add_loading_reaction,
    commands_channel_check,
    log_to_modlog_channel,
    make_embed,
    require_level,
    safe_delete,
    timed_rest_call,
    humanize_seconds,
)

logger = logging.getLogger(__name__)


def _fmt_dt(dt: datetime | None) -> str:
    if dt is None:
        return "Unknown"
    return discord.utils.format_dt(dt)


def _chunk_commands(commands: list[str], size: int) -> list[list[str]]:
    return [commands[i : i + size] for i in range(0, len(commands), size)]


def _build_help_pages(prefix: str) -> list[Page]:
    sections: list[tuple[str, list[str]]] = [
        (
            "⚠️ Moderation Commands",
            [
                "warn <user> <reason>",
                "delwarn <user> <warn_id>",
                "warnings <user>",
                "modlogs <user>",
                "mute <user> <duration> [reason]",
                "unmute <user> [reason]",
                "kick <user> <reason>",
                "ban <user> <reason>",
                "unban <user> <reason>",
                "wm <user> <duration> <reason>",
                "wmr <duration> <reason>",
                "masskick <users,users> <reason>",
                "massban <users,users> <reason>",
                "massmute <users,users> <duration> <reason>",
                "imprison <user> <reason>",
                "release <user> [reason]",
            ],
        ),
        (
            "📌 Role Commands",
            [
                "role <user> <role>",
                "removerole <user> <role>",
                "temprole <user> <role> <duration>",
                "removetemp <user> <role>",
                "persistrole <user> <role>",
                "removepersist <user> <role>",
                "massrole <users,users> <role>",
                "massremoverole <users,users> <role>",
                "masstemprole <users,users> <role> <duration>",
                "massremovetemp <users,users> <role>",
                "masspersistrole <users,users> <role>",
                "massremovepersist <users,users> <role>",
            ],
        ),
        (
            "⏱️ Channel Commands",
            [
                "checkslowmode [channel]",
                "setslowmode [channel] <duration>",
                "massslow <channels,channels> <duration>",
                "lock [channel]",
                "unlock [channel]",
                "hide [channel]",
                "unhide [channel]",
                "message <channel> <message>",
                "editmess <message_id> <new_message>",
                "replymess <message_id> <reply>",
                "deletemess <message_id>",
                "reactmess <message_id> <emoji>",
            ],
        ),
        (
            "🧹 Cleaning Commands",
            [
                "clean [amount]",
                "purge <amount>",
                "purgeuser <user> <amount>",
                "purgematch <keyword> <amount>",
            ],
        ),
        (
            "👤 Member Commands",
            [
                "mywarns",
                "myavatar",
                "mybanner",
                "myinfo",
            ],
        ),
        (
            "📋 Miscellaneous Commands",
            [
                "userinfo <user>",
                "serverinfo",
                "botinfo",
                "checkavatar <user>",
                "checkbanner <user>",
                "members",
                "ping",
                "wasbanned <user>",
                "checkdur <user>",
                "changenick <user> <nickname>",
                "removenick <user>",
                "roleperms <role>",
            ],
        ),
        (
            "🤖 AI Commands",
            [
                "ai <question>",
                "ai_settings",
                "askai <question>",
            ],
        ),
        (
            "🛠️ Utility Commands",
            [
                "announce <channel> <message>",
                "poll <question>",
                "define <word>",
                "translate <language> <text>",
                "remindme <duration> <text>",
                "reminders",
                "deleteremind <id>",
            ],
        ),
        (
            "🕒 Shift Commands",
            [
                "manage_shift",
            ],
        ),
        (
            "📊 Stats Commands",
            [
                "ms [user]",
                "staffstats",
                "set_ms [user]",
            ],
        ),
        (
            "🏷️ Tag Commands",
            [
                "tag <category> <title>",
                "tags [category]",
                "tag_create <category> <title> <description>",
                "tag_edit <category> <title> <description>",
                "tag_delete <category> <title>",
            ],
        ),
        (
            "📬 Notification Commands",
            [
                "dmnotify status",
                "dmnotify enable",
                "dmnotify disable",
                "dmnotify toggle <type>",
                "dmnotify test [member]",
                "optout",
                "optin",
            ],
        ),
        (
            "🧭 Setup Commands",
            [
                "setup",
                "adminsetup",
            ],
        ),
        (
            "🏛️ Admin Commands",
            [
                "adcmd",
                "flag <staff_user> <reason>",
                "unflag <staff_user> <strike_id>",
                "terminate <staff_user> [reason]",
                "lockchannels",
                "unlockchannels",
                "scanacc <user>",
                "stafflist",
                "wasstaff <user>",
            ],
        ),
        (
            "📊 Hierarchy Commands",
            [
                "hierarchy",
                "promote <staff>",
                "demote <staff>",
            ],
        ),
        (
            "📈 Promotion Commands",
            [
                "promotion list",
                "promotion review <id> <approve/deny>",
                "promotion analyze <member>",
                "promotion stats <member>",
            ],
        ),
    ]

    pages: list[Page] = []
    for title, commands_list in sections:
        chunks = _chunk_commands(commands_list, 8)
        for chunk_index, chunk in enumerate(chunks, start=1):
            suffix = f" ({chunk_index}/{len(chunks)})" if len(chunks) > 1 else ""
            description = "\n".join(f"`{prefix}{command}`" for command in chunk)
            embed = make_embed(action="help", title=f"{title}{suffix}", description=description)
            pages.append(Page(embed=embed))

    total_pages = len(pages)
    for index, page in enumerate(pages, start=1):
        page.embed.set_footer(text=f"{config.BOT_NAME} • Page {index}/{total_pages}")

    return pages


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

    @commands.command(name="botinfo")
    @commands.guild_only()
    @commands_channel_check()
    @require_level("moderator")
    async def botinfo(self, ctx: commands.Context) -> None:
        """Show bot information and statistics."""
        bot_user = ctx.bot.user
        
        # Get bot uptime
        start_time = getattr(self.bot, 'start_time', None)
        if start_time:
            uptime = discord.utils.utcnow() - start_time
            uptime_str = str(uptime).split('.')[0]  # Remove microseconds
        else:
            uptime_str = "Unknown"
        
        # Count guilds and members
        guild_count = len(ctx.bot.guilds)
        total_members = sum(guild.member_count or len(guild.members) for guild in ctx.bot.guilds)
        
        embed = make_embed(
            action="botinfo",
            title=f"🤖 Bot Information - {bot_user.display_name}",
        )
        
        if bot_user.display_avatar:
            embed.set_thumbnail(url=bot_user.display_avatar.url)
        
        embed.add_field(name="📍 Bot ID", value=str(bot_user.id), inline=True)
        embed.add_field(name="🏷️ Tag", value=f"#{bot_user.discriminator}", inline=True)
        embed.add_field(name="📅 Created", value=_fmt_dt(bot_user.created_at), inline=True)
        
        embed.add_field(name="🕐 Uptime", value=uptime_str, inline=True)
        embed.add_field(name="🏰 Servers", value=str(guild_count), inline=True)
        embed.add_field(name="👥 Total Users", value=str(total_members), inline=True)
        
        embed.add_field(name="📦 Library", value="discord.py", inline=True)
        embed.add_field(name="🔧 Prefix", value="!" if not ctx.guild else (await self.db.get_guild_settings(ctx.guild.id, default_prefix=config.DEFAULT_PREFIX)).prefix or "!", inline=True)
        embed.add_field(name="⚙️ Version", value="2.0", inline=True)
        
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
        remaining_str = humanize_seconds(max(0, remaining))
        embed = make_embed(action="checkdur", title="⏱️ Timeout Duration", description=f"Remaining: **{remaining_str}**")
        embed.add_field(name="📅 Ends", value=discord.utils.format_dt(until, style="R"), inline=False)
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

    @commands.command(name="wmr")
    @commands.guild_only()
    @commands_channel_check()
    @require_level("senior_mod")
    async def wmr(self, ctx: commands.Context, duration: str, *, reason: str) -> None:
        """Warn and mute a user by replying to their message."""
        # Check if this is a reply to a message
        if not ctx.message.reference or not ctx.message.reference.message_id:
            embed = make_embed(
                action="error",
                title="Not a Reply",
                description="This command must be used by replying to a user's message."
            )
            await ctx.send(embed=embed)
            return
        
        await add_loading_reaction(ctx.message)
        
        try:
            # Get the referenced message
            referenced_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            
            # Check if the author is a valid member
            if not isinstance(referenced_msg.author, discord.Member):
                embed = make_embed(
                    action="error",
                    title="Invalid User",
                    description="Cannot moderate users outside the server."
                )
                await ctx.send(embed=embed)
                return
            
            member = referenced_msg.author
            
            # Parse duration
            from helpers import parse_duration
            duration_seconds = parse_duration(duration)
            
            # Add warning
            warn_id = await self.db.add_warning(
                guild_id=ctx.guild.id,
                user_id=member.id,
                moderator_id=ctx.author.id,
                reason=f"WMR: {reason}",
                warn_days=14
            )
            
            # Add mute
            mute_id = await self.db.add_mute(
                guild_id=ctx.guild.id,
                user_id=member.id,
                moderator_id=ctx.author.id,
                reason=f"WMR: {reason}",
                duration_seconds=duration_seconds
            )
            
            # Create embed
            embed = make_embed(
                action="wm",
                title="⚠️ User Warned & Muted",
                description=f"**User:** {member.mention}\n**Duration:** {duration}\n**Reason:** {reason}\n**Moderator:** {ctx.author.mention}"
            )
            
            # Add proof information
            embed.add_field(
                name="📎 Proof",
                value=f"**Original Message:** [Jump to message]({referenced_msg.jump_url})\n**Message Content:** {referenced_msg.content[:100]}{'...' if len(referenced_msg.content) > 100 else ''}",
                inline=False
            )
            
            embed.add_field(
                name="⚠️ Warning",
                value=f"**Warning ID:** {warn_id}\n**Mute ID:** {mute_id}",
                inline=True
            )
            
            # Send message with undo view
            message = await ctx.send(embed=embed)
            
            # Add undo view for WMR
            from cogs.moderation import ModerationUndoView
            undo_view = ModerationUndoView("wmr", member.id, ctx.guild.id, message.id, ctx.author.id)
            await message.edit(view=undo_view)
            
            # Add to modlogs
            await self.db.add_modlog(
                guild_id=ctx.guild.id,
                action_type="wmr",
                user_id=member.id,
                moderator_id=ctx.author.id,
                reason=f"WMR: {reason} | Original message: {referenced_msg.content[:50]}...",
                message_id=referenced_msg.id
            )
            
            # Log to modlog channel
            settings = await self.db.get_guild_settings(ctx.guild.id, default_prefix=config.DEFAULT_PREFIX)
            await log_to_modlog_channel(self.bot, guild=ctx.guild, settings=settings, embed=embed, file=None)
            
            # Also log to the original message channel if different
            if ctx.channel.id != referenced_msg.channel.id:
                log_embed = make_embed(
                    action="wm",
                    title="⚠️ Action Taken",
                    description=f"**User:** {member.mention} has been warned and muted.\n**Reason:** {reason}\n**Moderator:** {ctx.author.mention}\n\n**Original message in #{referenced_msg.channel.mention}:**\n{referenced_msg.content[:200]}{'...' if len(referenced_msg.content) > 200 else ''}"
                )
                log_embed.add_field(
                    name="📎 Action Details",
                    value=f"**Duration:** {duration}\n**Warning ID:** {warn_id}\n**Mute ID:** {mute_id}",
                    inline=False
                )
                await ctx.send(embed=log_embed)
            
        except Exception as e:
            logger.error("WMR error: %s", e)
            embed = make_embed(
                action="error",
                title="Error",
                description="Failed to warn and mute user."
            )
            await ctx.send(embed=embed)

    # ----------------------------- Help system -----------------------------

    @commands.command(name="help")
    @commands.guild_only()
    @commands_channel_check()
    async def help(self, ctx: commands.Context) -> None:
        settings = await self.db.get_guild_settings(ctx.guild.id, default_prefix=config.DEFAULT_PREFIX)
        prefix = settings.prefix or config.DEFAULT_PREFIX
        pages = _build_help_pages(prefix)
        view = PaginationView(pages=pages, author_id=ctx.author.id)
        await ctx.send(embed=pages[0].embed, view=view)

    @commands.command(name="adcmd")
    @commands.guild_only()
    @commands_channel_check()
    @require_level("admin")
    async def adcmd(self, ctx: commands.Context) -> None:
        prefix = (await self.db.get_guild_settings(ctx.guild.id, default_prefix=config.DEFAULT_PREFIX)).prefix  # type: ignore[union-attr]
        settings = await self.db.get_guild_settings(ctx.guild.id, default_prefix=config.DEFAULT_PREFIX)  # type: ignore[union-attr]
        embed = make_embed(
            action="adcmd",
            title="Admin Commands",
            description=(
                f"**Staff Flagging ({config.MAX_STAFF_FLAGS}-Strike System)**\n"
                f"`{prefix}flag <staff_user> <reason>` - Flag a staff member\n"
                f"`{prefix}unflag <staff_user> <strike_id>` - Remove a flag\n"
                f"`{prefix}stafflist` - View all staff with strike counts\n"
                f"⚠️ **{config.MAX_STAFF_FLAGS} flags = auto-termination**\n"
                f"📅 Flags expire after {settings.flag_duration} days\n\n"
                f"**Staff Hierarchy Management**\n"
                f"`{prefix}hierarchy` - Open hierarchy management panel\n"
                f"`{prefix}promote <staff>` - Promote staff to next rank\n"
                f"`{prefix}demote <staff>` - Demote staff to previous rank\n\n"
                f"**Other Commands**\n"
                f"`{prefix}terminate <staff_user>` - Manually terminate staff\n"
                f"`{prefix}lockchannels` - Lock all configured categories\n"
                f"`{prefix}unlockchannels` - Unlock all configured categories\n"
                f"`{prefix}timeoutpanel` - Manage prohibited terms and timeout settings\n"
                f"`{prefix}scanacc <user>` - Scan account for suspicious activity\n"
                f"`{prefix}wasstaff <user>` - Check staff history"
            ),
        )
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MiscCog(bot))
