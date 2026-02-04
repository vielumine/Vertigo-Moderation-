"""Background tasks for expiry checks, startup reconciliation, reminders, and stats dashboard."""

from __future__ import annotations

import logging
import aiohttp
import time
from datetime import datetime, timezone

import discord
from discord.ext import commands, tasks

import config
from database import Database
from helpers import make_embed

logger = logging.getLogger(__name__)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class BackgroundTasksCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._startup_done = False

        self.warn_expiry_loop.start()
        self.temp_role_expiry_loop.start()
        self.staff_flag_expiry_loop.start()
        self.mute_expiry_loop.start()
        self.ai_rate_limit_cleanup_loop.start()
        self.reminder_check_loop.start()
        self.stats_dashboard_loop.start()

    @property
    def db(self) -> Database:
        return self.bot.db  # type: ignore[attr-defined]

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        if self._startup_done:
            return
        self._startup_done = True
        await self._restore_persistent_roles()

    async def _restore_persistent_roles(self) -> None:
        rows = await self.db.get_active_persistent_roles()
        for row in rows:
            guild = self.bot.get_guild(int(row["guild_id"]))
            if guild is None:
                continue
            member = guild.get_member(int(row["user_id"]))
            role = guild.get_role(int(row["role_id"]))
            if member is None or role is None:
                continue
            if role in member.roles:
                continue
            try:
                await member.add_roles(role, reason="Persistent role restore")
            except discord.Forbidden:
                continue
            except Exception:
                logger.exception("Failed to restore persistent role")

    @tasks.loop(minutes=1)
    async def warn_expiry_loop(self) -> None:
        try:
            rows = await self.db.get_expired_warnings(limit=200)
            if not rows:
                return
            ids = [int(r["id"]) for r in rows]
            await self.db.expire_warning_ids(ids)
            for r in rows:
                await self.db.add_modlog(
                    guild_id=int(r["guild_id"]),
                    action_type="warn_expired",
                    user_id=int(r["user_id"]),
                    moderator_id=None,
                    reason="Warning expired",
                )
        except Exception:
            logger.exception("warn_expiry_loop failed")

    @tasks.loop(minutes=1)
    async def temp_role_expiry_loop(self) -> None:
        try:
            rows = await self.db.get_expired_temp_roles(limit=200)
            if not rows:
                return
            ids = [int(r["id"]) for r in rows]
            await self.db.expire_temp_role_ids(ids)

            for r in rows:
                guild = self.bot.get_guild(int(r["guild_id"]))
                if guild is None:
                    continue
                member = guild.get_member(int(r["user_id"]))
                role = guild.get_role(int(r["role_id"]))
                if member and role and role in member.roles:
                    try:
                        await member.remove_roles(role, reason="Temp role expired")
                    except discord.Forbidden:
                        pass
                await self.db.add_modlog(
                    guild_id=int(r["guild_id"]),
                    action_type="temp_role_expired",
                    user_id=int(r["user_id"]),
                    moderator_id=None,
                    target_id=int(r["role_id"]),
                    reason="Temp role expired",
                )
        except Exception:
            logger.exception("temp_role_expiry_loop failed")

    @tasks.loop(minutes=1)
    async def staff_flag_expiry_loop(self) -> None:
        try:
            rows = await self.db.get_expired_staff_flags(limit=200)
            if not rows:
                return
            ids = [int(r["id"]) for r in rows]
            await self.db.expire_staff_flag_ids(ids)
        except Exception:
            logger.exception("staff_flag_expiry_loop failed")

    @tasks.loop(minutes=1)
    async def mute_expiry_loop(self) -> None:
        try:
            rows = await self.db.get_expired_mutes(limit=200)
            if not rows:
                return
            ids = [int(r["id"]) for r in rows]
            await self.db.expire_mute_ids(ids)
        except Exception:
            logger.exception("mute_expiry_loop failed")

    @tasks.loop(minutes=5)
    async def ai_rate_limit_cleanup_loop(self) -> None:
        """Clean up expired rate limit entries."""
        try:
            from helpers import clean_rate_limits
            clean_rate_limits()
        except Exception:
            logger.exception("ai_rate_limit_cleanup_loop failed")

    @tasks.loop(minutes=1)
    async def reminder_check_loop(self) -> None:
        """Check and send expired reminders."""
        try:
            reminders = await self.db.get_expired_reminders()
            if not reminders:
                return
            
            for reminder in reminders:
                user_id = int(reminder['user_id'])
                text = reminder['text']
                
                user = self.bot.get_user(user_id)
                if user:
                    embed = make_embed(
                        action="reminder",
                        title="⏰ Reminder",
                        description=text
                    )
                    try:
                        await user.send(embed=embed)
                    except discord.Forbidden:
                        pass
                
                await self.db.deactivate_reminder(int(reminder['id']))
                
        except Exception:
            logger.exception("reminder_check_loop failed")
    
    @tasks.loop(minutes=5)
    async def stats_dashboard_loop(self) -> None:
        """Update stats dashboard from external API."""
        try:
            # Get target channel
            channel = self.bot.get_channel(config.TARGET_CHANNEL_ID)
            if not channel or not isinstance(channel, discord.TextChannel):
                return
            
            # Fetch data from API
            async with aiohttp.ClientSession() as session:
                async with session.get(config.API_URL, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status != 200:
                        logger.error(f"Stats API returned {resp.status}")
                        return
                    
                    data = await resp.json()
            
            # Extract total executions
            total_executions = data.get('total_executions', 0)
            
            # Get previous stats from database
            prev_total = await self.db.stats_get('total_executions', 0)
            prev_daily_start = await self.db.stats_get('daily_start_total', 0)
            prev_weekly_start = await self.db.stats_get('weekly_start_total', 0)
            prev_monthly_start = await self.db.stats_get('monthly_start_total', 0)
            
            # Calculate daily/weekly/monthly stats
            now = utcnow()
            last_daily_reset = await self.db.stats_get('last_daily_reset', 0)
            last_weekly_reset = await self.db.stats_get('last_weekly_reset', 0)
            last_monthly_reset = await self.db.stats_get('last_monthly_reset', 0)
            
            current_day = now.day
            current_week = now.isocalendar()[1]
            current_month = now.month
            
            # Reset counters if day/week/month changed
            if last_daily_reset != current_day:
                prev_daily_start = total_executions
                await self.db.stats_set('daily_start_total', prev_daily_start)
                await self.db.stats_set('last_daily_reset', current_day)
            
            if last_weekly_reset != current_week:
                prev_weekly_start = total_executions
                await self.db.stats_set('weekly_start_total', prev_weekly_start)
                await self.db.stats_set('last_weekly_reset', current_week)
            
            if last_monthly_reset != current_month:
                prev_monthly_start = total_executions
                await self.db.stats_set('monthly_start_total', prev_monthly_start)
                await self.db.stats_set('last_monthly_reset', current_month)
            
            # Calculate deltas
            daily_delta = total_executions - prev_daily_start
            weekly_delta = total_executions - prev_weekly_start
            monthly_delta = total_executions - prev_monthly_start
            
            # Update total in database
            await self.db.stats_set('total_executions', total_executions)
            
            # Build embed
            description = f"**Total Executions:** {total_executions:,}\n"
            description += f"**Daily:** +{daily_delta:,}\n"
            description += f"**Weekly:** +{weekly_delta:,}\n"
            description += f"**Monthly:** +{monthly_delta:,}\n\n"
            
            # Add top games if available
            if 'top_games' in data and data['top_games']:
                description += "**Top Games:**\n"
                for game in data['top_games'][:5]:
                    description += f"• {game.get('name', 'Unknown')}: {game.get('count', 0):,}\n"
            
            embed = make_embed(
                action="stats",
                title="🚀 Script Execution Dashboard",
                description=description.strip()
            )
            embed.set_footer(text=f"Last Update: {int(now.timestamp())}")
            
            # Find or create embed message
            messages = []
            async for msg in channel.history(limit=10):
                if msg.author.id == self.bot.user.id and msg.embeds:
                    if '🚀' in msg.embeds[0].title:
                        messages.append(msg)
            
            if messages:
                await messages[0].edit(embed=embed)
            else:
                await channel.send(embed=embed)
            
            # Rename channel (with 10 min cooldown)
            last_rename = await self.db.stats_get('last_channel_rename', 0)
            if time.time() - last_rename > 600:  # 10 minutes
                try:
                    new_name = f"🌙total-execution-{total_executions}"
                    await channel.edit(name=new_name)
                    await self.db.stats_set('last_channel_rename', int(time.time()))
                except Exception as e:
                    logger.error(f"Failed to rename channel: {e}")
            
        except Exception:
            logger.exception("stats_dashboard_loop failed")

    @warn_expiry_loop.before_loop
    @temp_role_expiry_loop.before_loop
    @staff_flag_expiry_loop.before_loop
    @mute_expiry_loop.before_loop
    @reminder_check_loop.before_loop
    @stats_dashboard_loop.before_loop
    async def _before(self) -> None:
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(BackgroundTasksCog(bot))
