"""
Luna Bot Logging Cog
Handles message, member join, and member leave logging.
"""

import discord
from discord.ext import commands

from database import get_guild_setting
from helpers import (
    make_embed,
    get_embed_color,
)
from config import (
    DEEP_SPACE,
    STARLIGHT_BLUE,
    COLOR_WARNING,
    WEBHOOK_JOIN_LEAVE,
)


class Logging(commands.Cog):
    """Event logging handlers."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        """Log deleted messages."""
        if message.author.bot:
            return
        
        if not message.guild:
            return
        
        modlog_channel_id = await get_guild_setting(message.guild.id, "modlog_channel_id")
        if not modlog_channel_id:
            return
        
        channel = self.bot.get_channel(modlog_channel_id)
        if not channel:
            return
        
        # Check if message was deleted by a bot (moderation action)
        if message.author.id == self.bot.user.id:
            return
        
        embed = make_embed(
            title="🗑️ Message Deleted",
            color=COLOR_WARNING,
            fields=[
                ("Author", f"{message.author.mention} (ID: {message.author.id})", True),
                ("Channel", message.channel.mention, True),
                ("Content", message.content or "[No content/Embed]", False),
            ],
            timestamp=True
        )
        
        await channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Log member joins."""
        join_leave_channel_id = await get_guild_setting(member.guild.id, "join_leave_channel_id")
        if join_leave_channel_id:
            channel = member.guild.get_channel(join_leave_channel_id)
            if channel:
                embed = make_embed(
                    title="👋 Member Joined",
                    color=STARLIGHT_BLUE,
                    fields=[
                        ("Member", f"{member.mention} (ID: {member.id})", True),
                        ("Account Created", f"<t:{int(member.created_at.timestamp())}:R>", True),
                        ("Server Members", str(member.guild.member_count), True),
                    ],
                    timestamp=True
                )
                await channel.send(embed=embed)
        
        # Also log to webhook if configured
        if WEBHOOK_JOIN_LEAVE:
            from helpers import log_to_webhook
            embed = make_embed(
                title="👋 Member Joined",
                color=STARLIGHT_BLUE,
                fields=[
                    ("Member", f"{member.mention} (ID: {member.id})", True),
                    ("Server", member.guild.name, True),
                ],
                timestamp=True
            )
            await log_to_webhook(WEBHOOK_JOIN_LEAVE, embed)
    
    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """Log member leaves."""
        join_leave_channel_id = await get_guild_setting(member.guild.id, "join_leave_channel_id")
        if join_leave_channel_id:
            channel = member.guild.get_channel(join_leave_channel_id)
            if channel:
                embed = make_embed(
                    title="👋 Member Left",
                    color=COLOR_WARNING,
                    fields=[
                        ("Member", f"{member.mention} (ID: {member.id})", True),
                        ("Roles", ", ".join(role.mention for role in member.roles if role != member.guild.default_role), False),
                        ("Server Members", str(member.guild.member_count), True),
                    ],
                    timestamp=True
                )
                await channel.send(embed=embed)
        
        # Also log to webhook if configured
        if WEBHOOK_JOIN_LEAVE:
            from helpers import log_to_webhook
            embed = make_embed(
                title="👋 Member Left",
                color=COLOR_WARNING,
                fields=[
                    ("Member", f"{member.mention} (ID: {member.id})", True),
                    ("Server", member.guild.name, True),
                ],
                timestamp=True
            )
            await log_to_webhook(WEBHOOK_JOIN_LEAVE, embed)
    
    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        """Log member bans."""
        modlog_channel_id = await get_guild_setting(guild.id, "modlog_channel_id")
        if not modlog_channel_id:
            return
        
        channel = self.bot.get_channel(modlog_channel_id)
        if not channel:
            return
        
        embed = make_embed(
            title="🔨 Member Banned",
            color=0xFF0000,
            fields=[
                ("User", f"{user.name}#{user.discriminator} (ID: {user.id})", True),
                ("Server", guild.name, True),
            ],
            timestamp=True
        )
        
        await channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        """Log member unbans."""
        modlog_channel_id = await get_guild_setting(guild.id, "modlog_channel_id")
        if not modlog_channel_id:
            return
        
        channel = self.bot.get_channel(modlog_channel_id)
        if not channel:
            return
        
        embed = make_embed(
            title="🔓 Member Unbanned",
            color=0x00FF00,
            fields=[
                ("User", f"{user.name}#{user.discriminator} (ID: {user.id})", True),
                ("Server", guild.name, True),
            ],
            timestamp=True
        )
        
        await channel.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Logging(bot))
