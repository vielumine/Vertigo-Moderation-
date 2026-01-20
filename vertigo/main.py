"""Vertigo bot bootstrap."""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Sequence

import discord
from discord.ext import commands
from dotenv import load_dotenv

from vertigo import config
from vertigo.database import Database
from vertigo.helpers import make_embed

logger = logging.getLogger(__name__)


COGS: Sequence[str] = (
    "vertigo.cogs.logging",
    "vertigo.cogs.background",
    "vertigo.cogs.setup",
    "vertigo.cogs.moderation",
    "vertigo.cogs.roles",
    "vertigo.cogs.channels",
    "vertigo.cogs.cleaning",
    "vertigo.cogs.admin",
    "vertigo.cogs.member",
    "vertigo.cogs.misc",
    "vertigo.cogs.owner",
)


class VertigoBot(commands.Bot):
    db: Database


async def _get_prefix(bot: commands.Bot, message: discord.Message) -> str | list[str]:
    if message.guild is None:
        return config.DEFAULT_PREFIX

    db = getattr(bot, "db", None)
    if db is None:
        return config.DEFAULT_PREFIX

    settings = await db.get_guild_settings(message.guild.id, default_prefix=config.DEFAULT_PREFIX)
    return settings.prefix or config.DEFAULT_PREFIX


def create_bot() -> VertigoBot:
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True
    intents.guilds = True
    intents.messages = True

    bot = VertigoBot(
        command_prefix=_get_prefix,
        intents=intents,
        help_command=None,
        allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False),
    )
    return bot


async def _load_cogs(bot: commands.Bot) -> None:
    for ext in COGS:
        try:
            await bot.load_extension(ext)
            logger.info("Loaded %s", ext)
        except Exception:
            logger.exception("Failed to load extension %s", ext)


def _setup_logging() -> None:
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, level_name, logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


async def main() -> None:
    load_dotenv()
    _setup_logging()

    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_TOKEN is not set")

    bot = create_bot()
    bot.db = Database(config.DATABASE_PATH)
    await bot.db.connect()

    @bot.event
    async def on_ready() -> None:
        logger.info("Logged in as %s (%s)", bot.user, bot.user.id if bot.user else "?")

    @bot.event
    async def on_guild_join(guild: discord.Guild) -> None:
        try:
            if await bot.db.is_guild_blacklisted(guild_id=guild.id):
                await guild.leave()
        except Exception:
            logger.exception("Failed to check guild blacklist")

    @bot.event
    async def on_command_error(ctx: commands.Context, error: commands.CommandError) -> None:
        if isinstance(error, commands.CheckFailure):
            return
        if isinstance(error, commands.MissingRequiredArgument):
            prefix = await _get_prefix(bot, ctx.message)
            if isinstance(prefix, list):
                prefix = prefix[0]
            usage = f"{prefix}{ctx.command.qualified_name} {ctx.command.signature}"
            embed = make_embed(
                action="error",
                title="❌ Missing Arguments",
                description=f"{str(error)}\n\n**Usage:**\n```{usage}```",
            )
            await ctx.send(embed=embed)
            return
        if isinstance(error, commands.BadArgument):
            prefix = await _get_prefix(bot, ctx.message)
            if isinstance(prefix, list):
                prefix = prefix[0]
            usage = f"{prefix}{ctx.command.qualified_name} {ctx.command.signature}"
            embed = make_embed(
                action="error",
                title="❌ Invalid Arguments",
                description=f"{str(error)}\n\n**Usage:**\n```{usage}```",
            )
            await ctx.send(embed=embed)
            return
        if isinstance(error, commands.CommandNotFound):
            return
        logger.exception("Unhandled command error", exc_info=error)
        embed = make_embed(action="error", title="Error", description="An error occurred. Please try again later.")
        await ctx.send(embed=embed)

    await _load_cogs(bot)

    try:
        await bot.start(token)
    finally:
        await bot.db.close()


def run() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    run()
