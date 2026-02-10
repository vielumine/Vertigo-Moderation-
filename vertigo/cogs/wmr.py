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
    notify_owner_action,
    require_level,
    utcnow,
    parse_duration,
    log_to_modlog_channel,
    safe_delete,
    humanize_seconds,
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
            
            # Get current active warn count for this user to determine the display number
            active_warnings = await self.db.get_active_warnings(guild_id=ctx.guild.id, user_id=member.id)
            warn_number = len(active_warnings) + 1
            
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
                name="🆔 Warn ID",
                value=f"**Warn #{warn_number}** (DB: `{warn_id}`)",
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
            
            # Track mod stat
            await self.db.track_mod_action(guild_id=ctx.guild.id, user_id=ctx.author.id, action_type="warns")
            await self.db.track_mod_action(guild_id=ctx.guild.id, user_id=ctx.author.id, action_type="mutes")
            
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
            
            # Delete both messages (staff command and original user message)
            try:
                await safe_delete(ctx.message)
            except Exception:
                logger.debug("Failed to delete staff command message")
            
            try:
                await safe_delete(referenced_msg)
            except Exception:
                logger.debug("Failed to delete original user message")
            
            # Notify owner of the action
            await notify_owner_action(
                self.bot,
                action="wmr",
                guild_name=ctx.guild.name,
                guild_id=ctx.guild.id,
                target=str(member),
                target_id=member.id,
                moderator=str(ctx.author),
                moderator_id=ctx.author.id,
                reason=f"WMR: {reason}",
                duration=humanize_seconds(duration_seconds),
                extra_info=f"Original message: {message_preview}"
            )
            
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
