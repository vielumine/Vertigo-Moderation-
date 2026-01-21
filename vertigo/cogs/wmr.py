"""WMR (Warn Mute Reply) Command - Senior Mod Only"""

from __future__ import annotations

import logging
from datetime import timedelta

import discord
from discord.ext import commands

from vertigo import config
from vertigo.database import Database
from vertigo.helpers import (
    add_loading_reaction,
    make_embed,
    require_level,
    utcnow,
)

logger = logging.getLogger(__name__)


class WMRCommand:
    """WMR (Warn Mute Reply) command implementation."""
    
    def __init__(self, bot):
        self.bot = bot
    
    @property
    def db(self) -> Database:
        return self.bot.db
    
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
            from vertigo.helpers import parse_duration
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
            
            # Add to modlogs
            await self.db.add_modlog(
                guild_id=ctx.guild.id,
                action_type="wmr",
                user_id=member.id,
                moderator_id=ctx.author.id,
                reason=f"WMR: {reason} | Original message: {referenced_msg.content[:50]}...",
                message_id=referenced_msg.id
            )
            
            await ctx.send(embed=embed)
            
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


def setup_wmr_command(bot):
    """Setup the WMR command."""
    wmr_instance = WMRCommand(bot)
    
    @bot.tree.command(name="wmr", description="Warn and mute a user by replying to their message")
    @commands.guild_only()
    @require_level("senior_mod")
    async def wmr_slash(interaction: discord.Interaction, duration: str, reason: str):
        """Slash command version of WMR."""
        # This would need additional implementation for slash commands
        # For now, we'll use the text command version
        await interaction.response.send_message("Use the text command !wmr by replying to a message.", ephemeral=True)
    
    # Add the method to the bot instance
    bot.wmr = wmr_instance.wmr
    
    return bot


# Register as a command in the misc cog or as a standalone
def register_wmr_command(bot):
    """Register WMR as a text command."""
    from discord.ext.commands import Context
    
    async def wmr_command(ctx: commands.Context, duration: str, *, reason: str) -> None:
        wmr_instance = WMRCommand(bot)
        await wmr_instance.wmr(ctx, duration, reason=reason)
    
    # Add command to bot
    bot.add_command(commands.Command(wmr_command, name="wmr", help="Warn and mute a user by replying to their message"))
    
    return bot