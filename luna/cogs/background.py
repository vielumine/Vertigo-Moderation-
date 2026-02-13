"""Background tasks for expiry checks and startup reconciliation."""

from __future__ import annotations

import logging

import discord
from discord.ext import commands, tasks

from database import Database

logger = logging.getLogger(__name__)


class BackgroundTasksCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._startup_done = False

        self.warn_expiry_loop.start()
        self.temp_role_expiry_loop.start()
        self.staff_flag_expiry_loop.start()
        self.mute_expiry_loop.start()
        self.ai_rate_limit_cleanup_loop.start()

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

    @warn_expiry_loop.before_loop
    @temp_role_expiry_loop.before_loop
    @staff_flag_expiry_loop.before_loop
    @mute_expiry_loop.before_loop
    async def _before(self) -> None:
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(BackgroundTasksCog(bot))
