"""WMR (Warn Mute Reply) Command - Senior Mod Only"""

from __future__ import annotations

import logging
from datetime import timedelta

import discord
from discord.ext import commands

import config
from database import Database
from helpers import (
    add_loading_reaction,
    make_embed,
    require_level,
    utcnow,
    parse_duration,
    log_to_modlog_channel,
)

logger = logging.getLogger(__name__)


class WMR(commands.Cog):
    """WMR (Warn Mute Reply) command cog."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @property
    def db(self) -> Database:
        return self.bot.db
    
    @commands.command(name="wmr")
    @commands.guild_only()
    @require_level("senior_mod")
    async def wmr(self, ctx: commands.Context, duration: str, *, reason: str) -> None:
        """Warn and mute a user by replying to their message.
        
        Usage: !wmr <duration> <reason>
        Example: !wmr 1h spamming
        
        This command must be used by replying to the user's message.
        """
        # Check if this is a reply to a message
        if not ctx.message.reference or not ctx.message.reference.message_id:
            embed = make_embed(
                action="error",
                title="❌ Not a Reply",
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
                    title="❌ Invalid User",
                    description="Cannot moderate users outside the server."
                )
                await ctx.send(embed=embed)
                return
            
            member = referenced_msg.author
            
            # Check if bot can moderate this user
            if member.top_role >= ctx.guild.me.top_role:
                embed = make_embed(
                    action="error",
                    title="❌ Cannot Moderate",
                    description="I cannot moderate this user due to role hierarchy."
                )
                await ctx.send(embed=embed)
                return
            
            # Check staff immunity - get the moderation cog
            moderation_cog = self.bot.get_cog("Moderation")
            if moderation_cog and await moderation_cog._blocked_by_staff_immunity(ctx, member):
                return
            
            # Parse duration
            duration_seconds = parse_duration(duration)
            
            if duration_seconds <= 0:
                embed = make_embed(
                    action="error",
                    title="❌ Invalid Duration",
                    description="Duration must be greater than 0."
                )
                await ctx.send(embed=embed)
                return
            
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
            
            # Actually timeout the user
            timeout_until = discord.utils.utcnow() + timedelta(seconds=duration_seconds)
            await member.timeout(timeout_until, reason=f"WMR: {reason}")
            
            # Get guild settings for logging
            guild_settings = await self.db.get_guild_settings(ctx.guild.id, default_prefix=config.DEFAULT_PREFIX)
            
            # Create embed
            embed = make_embed(
                action="wm",
                title="⚠️ User Warned & Muted",
                description=f"**User:** {member.mention}\n**Duration:** {duration}\n**Reason:** {reason}\n**Moderator:** {ctx.author.mention}"
            )
            
            # Add proof information
            message_preview = referenced_msg.content[:100] if referenced_msg.content else "(No content)"
            if len(referenced_msg.content) > 100:
                message_preview += "..."
            
            embed.add_field(
                name="📎 Proof",
                value=f"**Original Message:** [Jump to message]({referenced_msg.jump_url})\n**Message Content:** {message_preview}",
                inline=False
            )
            
            embed.add_field(
                name="🆔 IDs",
                value=f"**Warning ID:** `{warn_id}`\n**Mute ID:** `{mute_id}`",
                inline=True
            )
            
            # Add to modlogs
            await self.db.add_modlog(
                guild_id=ctx.guild.id,
                action_type="wmr",
                user_id=member.id,
                moderator_id=ctx.author.id,
                reason=f"WMR: {reason} | Original message: {referenced_msg.content[:50] if referenced_msg.content else '(no content)'}...",
                message_id=referenced_msg.id
            )
            
            # Log to modlog channel
            await log_to_modlog_channel(
                bot=self.bot,
                guild=ctx.guild,
                settings=guild_settings,
                embed=embed,
                file=None
            )
            
            await ctx.send(embed=embed)
            
            # Try to DM the user
            try:
                dm_embed = make_embed(
                    action="wm",
                    title=f"⚠️ Warning & Mute in {ctx.guild.name}",
                    description=f"You have been warned and muted.\n\n**Reason:** {reason}\n**Duration:** {duration}\n**Moderator:** {ctx.author}\n\n**Your Message:**\n{message_preview}"
                )
                await member.send(embed=dm_embed)
            except Exception:
                pass  # Silently fail if DM fails
            
        except discord.Forbidden:
            embed = make_embed(
                action="error",
                title="❌ Permission Error",
                description="I don't have permission to timeout this user."
            )
            await ctx.send(embed=embed)
        except Exception as e:
            logger.error("WMR error: %s", e, exc_info=True)
            embed = make_embed(
                action="error",
                title="❌ Error",
                description="Failed to warn and mute user. Please check my permissions and try again."
            )
            await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    """Load the WMR cog."""
    await bot.add_cog(WMR(bot))
