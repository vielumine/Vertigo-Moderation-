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
    "vertigo.cogs.ai",
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

    @bot.event
    async def on_message(message: discord.Message) -> None:
        """Handle mentions, DMs, and AI responses."""
        # Ignore bot messages
        if message.author.bot:
            return
        
        # Handle DM messages
        if message.guild is None:
            # Check if this is a DM and AI should respond
            try:
                # For DMs, we need to check if AI is enabled for DMs
                # Since we don't have guild context in DMs, we'll need a different approach
                # For now, we'll respond to DMs if the user has a guild with the bot
                # and that guild has AI enabled for DMs
                
                # Check if user has any mutual guilds with AI DM support enabled
                ai_enabled_for_dm = False
                for guild in bot.guilds:
                    try:
                        ai_settings = await bot.db.get_ai_settings(guild.id)
                        if ai_settings.ai_enabled and ai_settings.respond_to_dms:
                            ai_enabled_for_dm = True
                            break
                    except Exception:
                        continue
                
                if ai_enabled_for_dm:
                    from vertigo.helpers import get_ai_response, is_rate_limited, update_rate_limit
                    
                    # Check rate limiting
                    if not is_rate_limited(message.author.id):
                        try:
                            # Get AI response with default personality
                            response = await get_ai_response(message.content, "genz")
                            update_rate_limit(message.author.id)
                            
                            # Send response
                            embed = make_embed(
                                action="ai",
                                title="🤖",
                                description=response
                            )
                            await message.reply(embed=embed)
                        except Exception:
                            # Silently fail for DMs to avoid spam
                            pass
            except Exception:
                # Silently fail for DMs
                pass
            
            # Don't process commands in DMs for this bot
            return
        
        # Handle guild messages (mentions)
        # Check if bot was mentioned
        if bot.user in message.mentions:
            try:
                ai_enabled = await bot.db.get_ai_settings(message.guild.id)
                
                if ai_enabled.ai_enabled and ai_enabled.respond_to_mentions:
                    # Remove the mention to get the actual message content
                    content = message.content
                    for mention in message.mentions:
                        if mention.id == bot.user.id:
                            content = content.replace(f"<@{mention.id}>", "").replace(f"<@!{mention.id}>", "").strip()
                    
                    if content:  # Only respond if there's actual content after removing mention
                        from vertigo.helpers import get_ai_response, is_rate_limited, update_rate_limit
                        
                        # Check rate limiting
                        if not is_rate_limited(message.author.id):
                            try:
                                # Get AI response
                                response = await get_ai_response(content, ai_enabled.ai_personality)
                                update_rate_limit(message.author.id)
                                
                                # Send response
                                embed = make_embed(
                                    action="ai",
                                    title="🤖",
                                    description=response
                                )
                                await message.reply(embed=embed)
                            except Exception:
                                # Silently fail for mentions to avoid spam
                                pass
            except Exception:
                # Silently fail for mentions
                pass
        
        # Process commands normally
        await bot.process_commands(message)

    await _load_cogs(bot)

    try:
        await bot.start(token)
    finally:
        await bot.db.close()


def run() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    run()
