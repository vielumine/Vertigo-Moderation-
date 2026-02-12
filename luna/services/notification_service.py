"""DM Notification Service for moderation actions.

This module handles sending DM notifications to users when they receive
moderation actions (warns, mutes, bans, kicks, flags). It respects user
preferences and guild settings, and logs all delivery attempts.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord

import config
from helpers import make_embed, safe_dm, format_unix_timestamp, utcnow

if TYPE_CHECKING:
    from discord.ext import commands
    from database import Database

logger = logging.getLogger(__name__)


class ModActionNotifier:
    """Handles DM notifications for moderation actions."""

    def __init__(self, bot: commands.Bot, db: Database) -> None:
        self.bot = bot
        self.db = db

    async def should_notify(self, guild_id: int, user_id: int, action_type: str) -> bool:
        """Check if we should send a DM notification."""
        # Check guild settings
        settings = await self.db.get_dm_notification_settings(guild_id)
        if not settings.enabled:
            return False

        # Check action-specific settings
        action_map = {
            "warn": settings.notify_warns,
            "mute": settings.notify_mutes,
            "kick": settings.notify_kicks,
            "ban": settings.notify_bans,
            "flag": settings.notify_flags,
        }

        if action_type not in action_map or not action_map[action_type]:
            return False

        # Check user preferences
        user_wants_dms = await self.db.get_dm_preference(user_id, guild_id)
        return user_wants_dms

    async def send_warn_notification(
        self,
        *,
        user: discord.User | discord.Member,
        guild: discord.Guild,
        reason: str,
        warn_id: int,
        moderator: discord.Member,
        warn_duration: int,
        active_warns_count: int
    ) -> bool:
        """Send a DM notification for a warning."""
        if not await self.should_notify(guild.id, user.id, "warn"):
            return False

        try:
            embed = make_embed(
                action="warn",
                title=f"⚠️ Warning Issued in {guild.name}",
                description=f"You have been warned by a moderator."
            )
            embed.add_field(name="📝 Reason", value=reason, inline=False)
            embed.add_field(name="👮 Moderator", value=moderator.mention, inline=True)
            embed.add_field(name="📊 Active Warnings", value=f"{active_warns_count} warning(s)", inline=True)
            embed.add_field(name="⏱️ Expires", value=f"In {warn_duration} days", inline=True)
            embed.add_field(name="📍 Warning ID", value=f"`{warn_id}`", inline=True)
            
            # Add appeal information
            embed.add_field(
                name="📢 Appeal Process",
                value="If you believe this warning was issued in error, please contact the server administrators.",
                inline=False
            )

            embed.set_footer(text=f"{config.BOT_NAME} • Timestamp")
            embed.timestamp = utcnow()

            await safe_dm(user, embed=embed)
            await self.db.log_dm_notification(
                guild_id=guild.id,
                user_id=user.id,
                action_type="warn",
                success=True
            )
            logger.info(f"Sent warn notification to user {user.id} in guild {guild.id}")
            return True

        except Exception as e:
            logger.error(f"Failed to send warn notification to {user.id}: {e}")
            await self.db.log_dm_notification(
                guild_id=guild.id,
                user_id=user.id,
                action_type="warn",
                success=False,
                reason=str(e)
            )
            return False

    async def send_mute_notification(
        self,
        *,
        user: discord.User | discord.Member,
        guild: discord.Guild,
        reason: str,
        duration: str,
        moderator: discord.Member
    ) -> bool:
        """Send a DM notification for a mute."""
        if not await self.should_notify(guild.id, user.id, "mute"):
            return False

        try:
            embed = make_embed(
                action="mute",
                title=f"🔇 You Have Been Muted in {guild.name}",
                description=f"You have been temporarily muted by a moderator."
            )
            embed.add_field(name="⏱️ Duration", value=duration, inline=True)
            embed.add_field(name="👮 Moderator", value=moderator.mention, inline=True)
            embed.add_field(name="📝 Reason", value=reason, inline=False)
            
            # Add appeal information
            embed.add_field(
                name="📢 Appeal Process",
                value="If you believe this mute was issued in error, you may appeal by contacting a server administrator.",
                inline=False
            )

            embed.set_footer(text=f"{config.BOT_NAME} • Timestamp")
            embed.timestamp = utcnow()

            await safe_dm(user, embed=embed)
            await self.db.log_dm_notification(
                guild_id=guild.id,
                user_id=user.id,
                action_type="mute",
                success=True
            )
            logger.info(f"Sent mute notification to user {user.id} in guild {guild.id}")
            return True

        except Exception as e:
            logger.error(f"Failed to send mute notification to {user.id}: {e}")
            await self.db.log_dm_notification(
                guild_id=guild.id,
                user_id=user.id,
                action_type="mute",
                success=False,
                reason=str(e)
            )
            return False

    async def send_kick_notification(
        self,
        *,
        user: discord.User,
        guild: discord.Guild,
        reason: str,
        moderator: discord.Member
    ) -> bool:
        """Send a DM notification for a kick."""
        if not await self.should_notify(guild.id, user.id, "kick"):
            return False

        try:
            embed = make_embed(
                action="kick",
                title=f"👢 You Have Been Kicked from {guild.name}",
                description=f"You have been removed from the server by a moderator."
            )
            embed.add_field(name="👮 Moderator", value=moderator.mention, inline=True)
            embed.add_field(name="📝 Reason", value=reason, inline=False)
            
            # Add rejoin information
            embed.add_field(
                name="🔗 Rejoining",
                value="You may rejoin the server using an invite link if you wish.",
                inline=False
            )
            
            # Add appeal information
            embed.add_field(
                name="📢 Appeal Process",
                value="If you believe this kick was issued in error, please contact the server administrators before rejoining.",
                inline=False
            )

            embed.set_footer(text=f"{config.BOT_NAME} • Timestamp")
            embed.timestamp = utcnow()

            await safe_dm(user, embed=embed)
            await self.db.log_dm_notification(
                guild_id=guild.id,
                user_id=user.id,
                action_type="kick",
                success=True
            )
            logger.info(f"Sent kick notification to user {user.id} in guild {guild.id}")
            return True

        except Exception as e:
            logger.error(f"Failed to send kick notification to {user.id}: {e}")
            await self.db.log_dm_notification(
                guild_id=guild.id,
                user_id=user.id,
                action_type="kick",
                success=False,
                reason=str(e)
            )
            return False

    async def send_ban_notification(
        self,
        *,
        user: discord.User,
        guild: discord.Guild,
        reason: str,
        moderator: discord.Member
    ) -> bool:
        """Send a DM notification for a ban."""
        if not await self.should_notify(guild.id, user.id, "ban"):
            return False

        try:
            embed = make_embed(
                action="ban",
                title=f"🔨 You Have Been Banned from {guild.name}",
                description=f"You have been permanently banned from the server."
            )
            embed.add_field(name="👮 Moderator", value=moderator.mention, inline=True)
            embed.add_field(name="📝 Reason", value=reason, inline=False)
            
            # Add appeal information
            embed.add_field(
                name="📢 Appeal Process",
                value="If you believe this ban was issued in error, please contact the server administrators to appeal.",
                inline=False
            )

            embed.set_footer(text=f"{config.BOT_NAME} • Timestamp")
            embed.timestamp = utcnow()

            await safe_dm(user, embed=embed)
            await self.db.log_dm_notification(
                guild_id=guild.id,
                user_id=user.id,
                action_type="ban",
                success=True
            )
            logger.info(f"Sent ban notification to user {user.id} in guild {guild.id}")
            return True

        except Exception as e:
            logger.error(f"Failed to send ban notification to {user.id}: {e}")
            await self.db.log_dm_notification(
                guild_id=guild.id,
                user_id=user.id,
                action_type="ban",
                success=False,
                reason=str(e)
            )
            return False

    async def send_flag_notification(
        self,
        *,
        user: discord.User | discord.Member,
        guild: discord.Guild,
        reason: str,
        flag_id: int,
        admin: discord.Member,
        strike_count: int,
        max_strikes: int,
        flag_duration: int
    ) -> bool:
        """Send a DM notification for a staff flag."""
        if not await self.should_notify(guild.id, user.id, "flag"):
            return False

        try:
            if strike_count >= max_strikes:
                embed = make_embed(
                    action="flag",
                    title=f"⛔ Staff Termination in {guild.name}",
                    description=f"You have reached {max_strikes} strikes and have been automatically terminated."
                )
            else:
                embed = make_embed(
                    action="flag",
                    title=f"🚩 Staff Flag Issued in {guild.name}",
                    description=f"You have received a staff flag from an administrator."
                )
            
            embed.add_field(name="📝 Reason", value=reason, inline=False)
            embed.add_field(name="👔 Admin", value=admin.mention, inline=True)
            embed.add_field(name="📊 Strikes", value=f"{strike_count}/{max_strikes}", inline=True)
            embed.add_field(name="📍 Flag ID", value=f"`{flag_id}`", inline=True)
            
            if strike_count < max_strikes:
                embed.add_field(name="⏱️ Expires", value=f"In {flag_duration} days", inline=True)
                
                # Add warning if close to termination
                if strike_count >= max_strikes - 1:
                    embed.add_field(
                        name="⚠️ Warning",
                        value=f"You are one strike away from automatic termination. Please review your performance.",
                        inline=False
                    )
            else:
                embed.add_field(
                    name="⛔ Termination",
                    value="You have been removed from all staff roles and issued a 7-day timeout.",
                    inline=False
                )
            
            # Add appeal information
            embed.add_field(
                name="📢 Appeal Process",
                value="If you believe this flag was issued in error, please contact the server administrators.",
                inline=False
            )

            embed.set_footer(text=f"{config.BOT_NAME} • Timestamp")
            embed.timestamp = utcnow()

            await safe_dm(user, embed=embed)
            await self.db.log_dm_notification(
                guild_id=guild.id,
                user_id=user.id,
                action_type="flag",
                success=True
            )
            logger.info(f"Sent flag notification to user {user.id} in guild {guild.id}")
            return True

        except Exception as e:
            logger.error(f"Failed to send flag notification to {user.id}: {e}")
            await self.db.log_dm_notification(
                guild_id=guild.id,
                user_id=user.id,
                action_type="flag",
                success=False,
                reason=str(e)
            )
            return False
