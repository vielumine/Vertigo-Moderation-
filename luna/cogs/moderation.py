"""
Luna Bot Moderation Cog
Handles all moderation commands: warn, mute, kick, ban, timeout, etc.
"""

import discord
from discord.ext import commands
from datetime import datetime, timedelta
from typing import Optional

from database import (
    add_warn,
    get_warn_count,
    add_mute,
    get_active_mute,
    remove_mute,
    add_staff_flag,
    get_active_flags,
    get_user_warns,
)
from helpers import (
    make_embed,
    get_embed_color,
    parse_duration,
    format_seconds,
    safe_dm,
    add_loading_reaction,
    log_to_modlog_channel,
    utcnow,
    is_staff,
    is_admin,
    get_prefix,
)
from config import (
    DEEP_SPACE,
    STARLIGHT_BLUE,
    COLOR_ERROR,
    COLOR_SUCCESS,
    COLOR_WARNING,
    MAX_STAFF_FLAGS,
    PREFIX,
)


class Moderation(commands.Cog):
    """Moderation commands."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    async def _blocked_by_staff_immunity(self, moderator: discord.Member, target: discord.Member, guild: discord.Guild) -> bool:
        """Check if command is blocked by staff immunity."""
        if await is_staff(target, guild) and not await is_admin(moderator, guild):
            return True
        return False
    
    async def _check_mod_channel(self, ctx: commands.Context) -> bool:
        """Check if command is used in the correct channel."""
        from database import get_guild_setting
        
        mod_channel_id = await get_guild_setting(ctx.guild.id, "mod_channel_id")
        if mod_channel_id:
            if ctx.channel.id != mod_channel_id:
                channel = self.bot.get_channel(mod_channel_id)
                await ctx.reply(embed=make_embed(
                    title="❌ Wrong Channel",
                    description=f"Moderation commands must be used in {channel.mention}",
                    color=COLOR_ERROR
                ))
                return False
        return True
    
    @commands.command()
    @commands.has_permissions(moderate_members=True)
    async def warn(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
        """Warn a member."""
        if not await self._check_mod_channel(ctx):
            return
        
        if await self._blocked_by_staff_immunity(ctx.author, member, ctx.guild):
            await ctx.reply(embed=make_embed(
                title="❌ Cannot Moderate Staff",
                description=f"@{member.name} is a staff member, I will not do that.",
                color=COLOR_ERROR
            ))
            return
        
        stop_loading = add_loading_reaction(ctx.message)
        
        # Add warn to database
        warn_id = await add_warn(member.id, ctx.guild.id, ctx.author.id, reason)
        warn_count = await get_warn_count(member.id, ctx.guild.id)
        
        stop_loading()
        
        # Send DM to user
        dm_sent = await safe_dm(member, embed=make_embed(
            title=f"⚠️ Warning in {ctx.guild.name}",
            description=f"You have been warned by {ctx.author.mention}.\n**Reason:** {reason}",
            color=COLOR_WARNING
        ))
        
        # Log to modlog
        log_embed = make_embed(
            title="⚠️ Member Warned",
            color=get_embed_color("warn"),
            fields=[
                ("User", f"{member.mention} (ID: {member.id})", True),
                ("Moderator", ctx.author.mention, True),
                ("Reason", reason, True),
                ("Total Warns", str(warn_count), True),
                ("DM Sent", "✅ Yes" if dm_sent else "❌ No", True),
            ],
            timestamp=True
        )
        await log_to_modlog_channel(ctx.guild, log_embed)
        
        # Reply to moderator
        await ctx.reply(embed=make_embed(
            title=f"⚠️ {member.name} Warned",
            description=f"**Warn ID:** {warn_id}\n**Reason:** {reason}\n**Total Warns:** {warn_count}",
            color=get_embed_color("warn"),
            footer=f"DM sent: {'✅ Yes' if dm_sent else '❌ No'}"
        ))
    
    @commands.command()
    @commands.has_permissions(moderate_members=True)
    async def mute(self, ctx: commands.Context, member: discord.Member, duration: str, *, reason: str = "No reason provided"):
        """Mute a member for a duration."""
        if not await self._check_mod_channel(ctx):
            return
        
        if await self._blocked_by_staff_immunity(ctx.author, member, ctx.guild):
            await ctx.reply(embed=make_embed(
                title="❌ Cannot Moderate Staff",
                description=f"@{member.name} is a staff member, I will not do that.",
                color=COLOR_ERROR
            ))
            return
        
        stop_loading = add_loading_reaction(ctx.message)
        
        # Parse duration
        duration_seconds = parse_duration(duration)
        if not duration_seconds:
            stop_loading()
            await ctx.reply(embed=make_embed(
                title="❌ Invalid Duration",
                description="Duration format: `1h`, `30m`, `1d`, `1w`",
                color=COLOR_ERROR
            ))
            return
        
        expires_at = utcnow() + duration_seconds
        
        # Add mute to database
        await add_mute(member.id, ctx.guild.id, ctx.author.id, reason, expires_at)
        
        # Apply mute timeout
        timeout_duration = timedelta(seconds=duration_seconds)
        await member.timeout(timeout_duration, reason=reason)
        
        stop_loading()
        
        # Send DM to user
        dm_sent = await safe_dm(member, embed=make_embed(
            title=f"🔇 Muted in {ctx.guild.name}",
            description=f"You have been muted by {ctx.author.mention}.\n**Duration:** {format_seconds(duration_seconds)}\n**Reason:** {reason}",
            color=COLOR_WARNING
        ))
        
        # Log to modlog
        log_embed = make_embed(
            title="🔇 Member Muted",
            color=get_embed_color("mute"),
            fields=[
                ("User", f"{member.mention} (ID: {member.id})", True),
                ("Moderator", ctx.author.mention, True),
                ("Duration", format_seconds(duration_seconds), True),
                ("Expires", f"<t:{expires_at}:R>", True),
                ("Reason", reason, True),
                ("DM Sent", "✅ Yes" if dm_sent else "❌ No", True),
            ],
            timestamp=True
        )
        await log_to_modlog_channel(ctx.guild, log_embed)
        
        # Reply to moderator
        await ctx.reply(embed=make_embed(
            title=f"🔇 {member.name} Muted",
            description=f"**Duration:** {format_seconds(duration_seconds)}\n**Expires:** <t:{expires_at}:R>\n**Reason:** {reason}",
            color=get_embed_color("mute"),
            footer=f"DM sent: {'✅ Yes' if dm_sent else '❌ No'}"
        ))
    
    @commands.command()
    @commands.has_permissions(moderate_members=True)
    async def unmute(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
        """Unmute a member."""
        if not await self._check_mod_channel(ctx):
            return
        
        stop_loading = add_loading_reaction(ctx.message)
        
        # Remove from database
        await remove_mute(member.id, ctx.guild.id)
        
        # Remove timeout
        await member.remove_timeout(reason=reason)
        
        stop_loading()
        
        # Send DM to user
        dm_sent = await safe_dm(member, embed=make_embed(
            title=f"🔊 Unmuted in {ctx.guild.name}",
            description=f"You have been unmuted by {ctx.author.mention}.\n**Reason:** {reason}",
            color=COLOR_SUCCESS
        ))
        
        # Log to modlog
        log_embed = make_embed(
            title="🔊 Member Unmuted",
            color=get_embed_color("unmute"),
            fields=[
                ("User", f"{member.mention} (ID: {member.id})", True),
                ("Moderator", ctx.author.mention, True),
                ("Reason", reason, True),
                ("DM Sent", "✅ Yes" if dm_sent else "❌ No", True),
            ],
            timestamp=True
        )
        await log_to_modlog_channel(ctx.guild, log_embed)
        
        # Reply
        await ctx.reply(embed=make_embed(
            title=f"🔊 {member.name} Unmuted",
            description=f"**Reason:** {reason}",
            color=get_embed_color("unmute"),
            footer=f"DM sent: {'✅ Yes' if dm_sent else '❌ No'}"
        ))
    
    @commands.command()
    @commands.has_permissions(moderate_members=True)
    async def kick(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
        """Kick a member."""
        if not await self._check_mod_channel(ctx):
            return
        
        if await self._blocked_by_staff_immunity(ctx.author, member, ctx.guild):
            await ctx.reply(embed=make_embed(
                title="❌ Cannot Moderate Staff",
                description=f"@{member.name} is a staff member, I will not do that.",
                color=COLOR_ERROR
            ))
            return
        
        stop_loading = add_loading_reaction(ctx.message)
        
        # Try to DM before kicking
        dm_sent = await safe_dm(member, embed=make_embed(
            title=f"👢 Kicked from {ctx.guild.name}",
            description=f"You have been kicked by {ctx.author.mention}.\n**Reason:** {reason}",
            color=COLOR_ERROR
        ))
        
        # Kick member
        await member.kick(reason=reason)
        
        stop_loading()
        
        # Log to modlog
        log_embed = make_embed(
            title="👢 Member Kicked",
            color=get_embed_color("kick"),
            fields=[
                ("User", f"{member.mention} (ID: {member.id})", True),
                ("Moderator", ctx.author.mention, True),
                ("Reason", reason, True),
                ("DM Sent", "✅ Yes" if dm_sent else "❌ No", True),
            ],
            timestamp=True
        )
        await log_to_modlog_channel(ctx.guild, log_embed)
        
        # Reply
        await ctx.reply(embed=make_embed(
            title=f"👢 {member.name} Kicked",
            description=f"**Reason:** {reason}",
            color=get_embed_color("kick"),
            footer=f"DM sent: {'✅ Yes' if dm_sent else '❌ No'}"
        ))
    
    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
        """Ban a member."""
        if not await self._check_mod_channel(ctx):
            return
        
        if await self._blocked_by_staff_immunity(ctx.author, member, ctx.guild):
            await ctx.reply(embed=make_embed(
                title="❌ Cannot Moderate Staff",
                description=f"@{member.name} is a staff member, I will not do that.",
                color=COLOR_ERROR
            ))
            return
        
        stop_loading = add_loading_reaction(ctx.message)
        
        # Try to DM before banning
        dm_sent = await safe_dm(member, embed=make_embed(
            title=f"🔨 Banned from {ctx.guild.name}",
            description=f"You have been banned by {ctx.author.mention}.\n**Reason:** {reason}",
            color=COLOR_ERROR
        ))
        
        # Ban member
        await member.ban(reason=reason)
        
        stop_loading()
        
        # Log to modlog
        log_embed = make_embed(
            title="🔨 Member Banned",
            color=get_embed_color("ban"),
            fields=[
                ("User", f"{member.mention} (ID: {member.id})", True),
                ("Moderator", ctx.author.mention, True),
                ("Reason", reason, True),
                ("DM Sent", "✅ Yes" if dm_sent else "❌ No", True),
            ],
            timestamp=True
        )
        await log_to_modlog_channel(ctx.guild, log_embed)
        
        # Reply
        await ctx.reply(embed=make_embed(
            title=f"🔨 {member.name} Banned",
            description=f"**Reason:** {reason}",
            color=get_embed_color("ban"),
            footer=f"DM sent: {'✅ Yes' if dm_sent else '❌ No'}"
        ))
    
    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx: commands.Context, user_id: int, *, reason: str = "No reason provided"):
        """Unban a user by ID."""
        stop_loading = add_loading_reaction(ctx.message)
        
        try:
            # Get ban entry
            ban_entry = await ctx.guild.fetch_ban(discord.Object(id=user_id))
            
            # Unban
            await ctx.guild.unban(discord.Object(id=user_id), reason=reason)
            
            stop_loading()
            
            # Log to modlog
            log_embed = make_embed(
                title="🔓 User Unbanned",
                color=get_embed_color("unban"),
                fields=[
                    ("User ID", str(user_id), True),
                    ("Username", ban_entry.user.name, True),
                    ("Moderator", ctx.author.mention, True),
                    ("Reason", reason, True),
                ],
                timestamp=True
            )
            await log_to_modlog_channel(ctx.guild, log_embed)
            
            # Reply
            await ctx.reply(embed=make_embed(
                title=f"🔓 {ban_entry.user.name} Unbanned",
                description=f"**User ID:** {user_id}\n**Reason:** {reason}",
                color=get_embed_color("unban")
            ))
        except discord.NotFound:
            stop_loading()
            await ctx.reply(embed=make_embed(
                title="❌ Ban Not Found",
                description=f"User {user_id} is not banned.",
                color=COLOR_ERROR
            ))
    
    @commands.command()
    @commands.has_permissions(moderate_members=True)
    async def timeout(self, ctx: commands.Context, member: discord.Member, duration: str, *, reason: str = "No reason provided"):
        """Timeout a member for a duration."""
        if not await self._check_mod_channel(ctx):
            return
        
        if await self._blocked_by_staff_immunity(ctx.author, member, ctx.guild):
            await ctx.reply(embed=make_embed(
                title="❌ Cannot Moderate Staff",
                description=f"@{member.name} is a staff member, I will not do that.",
                color=COLOR_ERROR
            ))
            return
        
        stop_loading = add_loading_reaction(ctx.message)
        
        # Parse duration
        duration_seconds = parse_duration(duration)
        if not duration_seconds:
            stop_loading()
            await ctx.reply(embed=make_embed(
                title="❌ Invalid Duration",
                description="Duration format: `1h`, `30m`, `1d`, `1w`",
                color=COLOR_ERROR
            ))
            return
        
        timeout_duration = timedelta(seconds=duration_seconds)
        await member.timeout(timeout_duration, reason=reason)
        
        expires_at = utcnow() + duration_seconds
        
        stop_loading()
        
        # Send DM to user
        dm_sent = await safe_dm(member, embed=make_embed(
            title=f"⏱️ Timed out in {ctx.guild.name}",
            description=f"You have been timed out by {ctx.author.mention}.\n**Duration:** {format_seconds(duration_seconds)}\n**Reason:** {reason}",
            color=COLOR_WARNING
        ))
        
        # Log to modlog
        log_embed = make_embed(
            title="⏱️ Member Timed Out",
            color=get_embed_color("timeout"),
            fields=[
                ("User", f"{member.mention} (ID: {member.id})", True),
                ("Moderator", ctx.author.mention, True),
                ("Duration", format_seconds(duration_seconds), True),
                ("Expires", f"<t:{expires_at}:R>", True),
                ("Reason", reason, True),
                ("DM Sent", "✅ Yes" if dm_sent else "❌ No", True),
            ],
            timestamp=True
        )
        await log_to_modlog_channel(ctx.guild, log_embed)
        
        # Reply
        await ctx.reply(embed=make_embed(
            title=f"⏱️ {member.name} Timed Out",
            description=f"**Duration:** {format_seconds(duration_seconds)}\n**Expires:** <t:{expires_at}:R>\n**Reason:** {reason}",
            color=get_embed_color("timeout"),
            footer=f"DM sent: {'✅ Yes' if dm_sent else '❌ No'}"
        ))
    
    @commands.command()
    @commands.has_permissions(moderate_members=True)
    async def untimeout(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
        """Remove timeout from a member."""
        if not await self._check_mod_channel(ctx):
            return
        
        stop_loading = add_loading_reaction(ctx.message)
        
        await member.remove_timeout(reason=reason)
        
        stop_loading()
        
        # Send DM to user
        dm_sent = await safe_dm(member, embed=make_embed(
            title=f"⏰ Timeout Removed in {ctx.guild.name}",
            description=f"Your timeout has been removed by {ctx.author.mention}.\n**Reason:** {reason}",
            color=COLOR_SUCCESS
        ))
        
        # Log to modlog
        log_embed = make_embed(
            title="⏰ Timeout Removed",
            color=get_embed_color("untimeout"),
            fields=[
                ("User", f"{member.mention} (ID: {member.id})", True),
                ("Moderator", ctx.author.mention, True),
                ("Reason", reason, True),
                ("DM Sent", "✅ Yes" if dm_sent else "❌ No", True),
            ],
            timestamp=True
        )
        await log_to_modlog_channel(ctx.guild, log_embed)
        
        # Reply
        await ctx.reply(embed=make_embed(
            title=f"⏰ {member.name} Timeout Removed",
            description=f"**Reason:** {reason}",
            color=get_embed_color("untimeout"),
            footer=f"DM sent: {'✅ Yes' if dm_sent else '❌ No'}"
        ))
    
    @commands.command()
    @commands.has_permissions(moderate_members=True)
    async def wm(self, ctx: commands.Context, member: discord.Member, duration: str, *, reason: str = "No reason provided"):
        """Warn and mute a member (warn+mute)."""
        if not await self._check_mod_channel(ctx):
            return
        
        if await self._blocked_by_staff_immunity(ctx.author, member, ctx.guild):
            await ctx.reply(embed=make_embed(
                title="❌ Cannot Moderate Staff",
                description=f"@{member.name} is a staff member, I will not do that.",
                color=COLOR_ERROR
            ))
            return
        
        stop_loading = add_loading_reaction(ctx.message)
        
        # Parse duration
        duration_seconds = parse_duration(duration)
        if not duration_seconds:
            stop_loading()
            await ctx.reply(embed=make_embed(
                title="❌ Invalid Duration",
                description="Duration format: `1h`, `30m`, `1d`, `1w`",
                color=COLOR_ERROR
            ))
            return
        
        expires_at = utcnow() + duration_seconds
        
        # Add warn
        warn_id = await add_warn(member.id, ctx.guild.id, ctx.author.id, reason)
        warn_count = await get_warn_count(member.id, ctx.guild.id)
        
        # Add mute
        await add_mute(member.id, ctx.guild.id, ctx.author.id, reason, expires_at)
        
        # Apply timeout
        timeout_duration = timedelta(seconds=duration_seconds)
        await member.timeout(timeout_duration, reason=reason)
        
        stop_loading()
        
        # Send DM to user
        dm_sent = await safe_dm(member, embed=make_embed(
            title=f"⚠️🔇 Warn & Mute in {ctx.guild.name}",
            description=f"You have been warned and muted by {ctx.author.mention}.\n**Duration:** {format_seconds(duration_seconds)}\n**Reason:** {reason}",
            color=COLOR_WARNING
        ))
        
        # Log to modlog
        log_embed = make_embed(
            title="⚠️🔇 Warn & Mute",
            color=COLOR_WARNING,
            fields=[
                ("User", f"{member.mention} (ID: {member.id})", True),
                ("Moderator", ctx.author.mention, True),
                ("Duration", format_seconds(duration_seconds), True),
                ("Expires", f"<t:{expires_at}:R>", True),
                ("Reason", reason, True),
                ("Total Warns", str(warn_count), True),
                ("DM Sent", "✅ Yes" if dm_sent else "❌ No", True),
            ],
            timestamp=True
        )
        await log_to_modlog_channel(ctx.guild, log_embed)
        
        # Reply
        await ctx.reply(embed=make_embed(
            title=f"⚠️🔇 {member.name} Warned & Muted",
            description=f"**Duration:** {format_seconds(duration_seconds)}\n**Expires:** <t:{expires_at}:R>\n**Reason:** {reason}\n**Total Warns:** {warn_count}",
            color=COLOR_WARNING,
            footer=f"DM sent: {'✅ Yes' if dm_sent else '❌ No'}"
        ))
    
    @commands.command()
    @commands.has_permissions(moderate_members=True)
    async def warns(self, ctx: commands.Context, member: discord.Member):
        """View all warns for a member."""
        warns = await get_user_warns(member.id, ctx.guild.id)
        
        if not warns:
            await ctx.reply(embed=make_embed(
                title=f"📋 {member.name}'s Warns",
                description="No warns found.",
                color=DEEP_SPACE
            ))
            return
        
        # Build fields for warns
        warn_fields = []
        for warn in warns[:10]:  # Show last 10 warns
            warn_fields.append((
                f"Warn #{warn['id']} - <t:{warn['created_at']}:R>",
                f"**By:** <@{warn['moderator_id']}>\n**Reason:** {warn['reason']}",
                False
            ))
        
        embed = make_embed(
            title=f"📋 {member.name}'s Warns",
            description=f"Total: {len(warns)} warn(s)",
            color=DEEP_SPACE,
            fields=warn_fields[:25]  # Discord limit
        )
        
        await ctx.reply(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))
