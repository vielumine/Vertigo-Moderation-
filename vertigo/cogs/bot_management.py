"""Bot Management Cog - Owner-only bot customization commands."""

from __future__ import annotations

import logging

import aiohttp
import discord
from discord.ext import commands

from database import Database
from helpers import make_embed, require_owner

logger = logging.getLogger(__name__)


class BotManagementCog(commands.Cog):
    """Owner-only commands for customizing bot appearance and presence."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._startup_done = False

    @property
    def db(self) -> Database:
        return self.bot.db  # type: ignore[attr-defined]

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """Restore bot customization settings on startup."""
        if self._startup_done:
            return
        self._startup_done = True

        try:
            settings = await self.db.get_bot_settings()
            logger.info("Restoring bot customization settings...")

            # Restore name if set
            if settings.custom_name and self.bot.user:
                try:
                    current_name = self.bot.user.name
                    if current_name != settings.custom_name:
                        await self.bot.user.edit(username=settings.custom_name)
                        logger.info(f"Restored bot name to: {settings.custom_name}")
                except Exception as e:
                    logger.error(f"Failed to restore bot name: {e}")

            # Restore status and activity
            status_map = {
                "online": discord.Status.online,
                "idle": discord.Status.idle,
                "dnd": discord.Status.dnd,
                "invisible": discord.Status.invisible,
            }
            activity_map = {
                "playing": discord.ActivityType.playing,
                "watching": discord.ActivityType.watching,
                "listening": discord.ActivityType.listening,
            }

            status = status_map.get(settings.status_type.lower()) if settings.status_type else None
            activity = None
            if settings.activity_type and settings.activity_text:
                act_type = activity_map.get(settings.activity_type.lower())
                if act_type:
                    activity = discord.Activity(type=act_type, name=settings.activity_text)

            if status or activity:
                await self.bot.change_presence(status=status, activity=activity)
                logger.info(f"Restored bot presence: status={settings.status_type}, activity={settings.activity_type} {settings.activity_text}")

        except Exception:
            logger.exception("Failed to restore bot customization settings")

    @commands.command(name="botavatar")
    @require_owner()
    async def bot_avatar(self, ctx: commands.Context, url: str | None = None) -> None:
        """Change bot avatar from URL or attachment.

        Usage: !botavatar <url> or attach an image
        """
        try:
            avatar_bytes = None

            if url:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as resp:
                        if resp.status != 200:
                            embed = make_embed(action="error", title="❌ Error", description="Failed to download image from URL.")
                            await ctx.send(embed=embed)
                            return
                        avatar_bytes = await resp.read()
            elif ctx.message.attachments:
                avatar_bytes = await ctx.message.attachments[0].read()
            else:
                embed = make_embed(action="error", title="❌ Error", description="Provide a URL or attach an image.")
                await ctx.send(embed=embed)
                return

            # Apply avatar
            await self.bot.user.edit(avatar=avatar_bytes)  # type: ignore[union-attr]

            # Store URL in database (if provided) for persistence
            await self.db.update_bot_settings(avatar_url=url or None)

            embed = make_embed(action="botavatar", title="✅ Avatar Updated", description="Bot avatar has been updated successfully.")
            await ctx.send(embed=embed)

        except discord.HTTPException as e:
            logger.error(f"Failed to set avatar: {e}")
            embed = make_embed(action="error", title="❌ Error", description=f"Failed to set avatar: {e.text if hasattr(e, 'text') else str(e)}")
            await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"Failed to set avatar: {e}")
            embed = make_embed(action="error", title="❌ Error", description=f"Failed to set avatar: {e}")
            await ctx.send(embed=embed)

    @commands.command(name="botbanner")
    @require_owner()
    async def bot_banner(self, ctx: commands.Context, url: str | None = None) -> None:
        """Change bot banner from URL or attachment.

        Usage: !botbanner <url> or attach an image
        """
        try:
            banner_bytes = None

            if url:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as resp:
                        if resp.status != 200:
                            embed = make_embed(action="error", title="❌ Error", description="Failed to download image from URL.")
                            await ctx.send(embed=embed)
                            return
                        banner_bytes = await resp.read()
            elif ctx.message.attachments:
                banner_bytes = await ctx.message.attachments[0].read()
            else:
                embed = make_embed(action="error", title="❌ Error", description="Provide a URL or attach an image.")
                await ctx.send(embed=embed)
                return

            # Apply banner
            await self.bot.user.edit(banner=banner_bytes)  # type: ignore[union-attr]

            # Store URL in database (if provided) for persistence
            await self.db.update_bot_settings(banner_url=url or None)

            embed = make_embed(action="botbanner", title="✅ Banner Updated", description="Bot banner has been updated successfully.")
            await ctx.send(embed=embed)

        except discord.HTTPException as e:
            logger.error(f"Failed to set banner: {e}")
            embed = make_embed(action="error", title="❌ Error", description=f"Failed to set banner: {e.text if hasattr(e, 'text') else str(e)}")
            await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"Failed to set banner: {e}")
            embed = make_embed(action="error", title="❌ Error", description=f"Failed to set banner: {e}")
            await ctx.send(embed=embed)

    @commands.command(name="botname")
    @require_owner()
    async def bot_name(self, ctx: commands.Context, *, name: str) -> None:
        """Change bot's display name.

        Usage: !botname <name>
        """
        try:
            if len(name) < 2 or len(name) > 32:
                embed = make_embed(action="error", title="❌ Invalid Name", description="Bot name must be between 2 and 32 characters.")
                await ctx.send(embed=embed)
                return

            await self.bot.user.edit(username=name)  # type: ignore[union-attr]
            await self.db.update_bot_settings(custom_name=name)

            embed = make_embed(action="botname", title="✅ Name Updated", description=f"Bot name changed to **{name}**.")
            await ctx.send(embed=embed)

        except discord.HTTPException as e:
            logger.error(f"Failed to set name: {e}")
            embed = make_embed(action="error", title="❌ Error", description=f"Failed to set name: {e.text if hasattr(e, 'text') else str(e)}")
            await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"Failed to set name: {e}")
            embed = make_embed(action="error", title="❌ Error", description=f"Failed to set name: {e}")
            await ctx.send(embed=embed)

    @commands.command(name="botstatus")
    @require_owner()
    async def bot_status(self, ctx: commands.Context, status: str) -> None:
        """Change bot status/presence.

        Usage: !botstatus <online/idle/dnd/invisible>
        """
        status_map = {
            "online": discord.Status.online,
            "idle": discord.Status.idle,
            "dnd": discord.Status.dnd,
            "invisible": discord.Status.invisible
        }

        if status.lower() not in status_map:
            embed = make_embed(action="error", title="❌ Invalid Status", description="Valid options: online, idle, dnd, invisible")
            await ctx.send(embed=embed)
            return

        try:
            await self.bot.change_presence(status=status_map[status.lower()])
            await self.db.update_bot_settings(status_type=status.lower())

            embed = make_embed(action="botstatus", title="✅ Status Updated", description=f"Status set to **{status}**.")
            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Failed to set status: {e}")
            embed = make_embed(action="error", title="❌ Error", description=f"Failed to set status: {e}")
            await ctx.send(embed=embed)

    @commands.command(name="botactivity")
    @require_owner()
    async def bot_activity(self, ctx: commands.Context, activity_type: str, *, text: str) -> None:
        """Change bot activity.

        Usage: !botactivity <playing/watching/listening> <text>
        """
        activity_map = {
            "playing": discord.ActivityType.playing,
            "watching": discord.ActivityType.watching,
            "listening": discord.ActivityType.listening
        }

        if activity_type.lower() not in activity_map:
            embed = make_embed(action="error", title="❌ Invalid Activity", description="Valid options: playing, watching, listening")
            await ctx.send(embed=embed)
            return

        try:
            activity = discord.Activity(type=activity_map[activity_type.lower()], name=text)
            await self.bot.change_presence(activity=activity)
            await self.db.update_bot_settings(activity_type=activity_type.lower(), activity_text=text)

            embed = make_embed(action="botactivity", title="✅ Activity Updated", description=f"Activity set to **{activity_type} {text}**.")
            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Failed to set activity: {e}")
            embed = make_embed(action="error", title="❌ Error", description=f"Failed to set activity: {e}")
            await ctx.send(embed=embed)

    @commands.command(name="botinfo")
    @require_owner()
    async def bot_info(self, ctx: commands.Context) -> None:
        """Display current bot customization settings."""
        try:
            settings = await self.db.get_bot_settings()

            embed = make_embed(action="botinfo", title="🤖 Bot Customization Settings", description="")

            # Current bot info
            if self.bot.user:
                embed.add_field(name="👤 Current Name", value=self.bot.user.name, inline=True)
                embed.add_field(name="🆔 Bot ID", value=str(self.bot.user.id), inline=True)

            # Customization settings
            embed.add_field(name="🖼️ Custom Avatar", value="✅ Set" if settings.avatar_url else "❌ Default", inline=True)
            embed.add_field(name="🎨 Custom Banner", value="✅ Set" if settings.banner_url else "❌ Default", inline=True)
            embed.add_field(name="📝 Custom Name", value=f"**{settings.custom_name}**" if settings.custom_name else "❌ Default", inline=False)

            # Status
            status_emoji = {
                "online": "🟢",
                "idle": "🌙",
                "dnd": "⛔",
                "invisible": "⚫",
            }
            status_display = f"{status_emoji.get(settings.status_type, '❓')} {settings.status_type.title()}" if settings.status_type else "❌ Default"
            embed.add_field(name="📊 Status", value=status_display, inline=True)

            # Activity
            if settings.activity_type and settings.activity_text:
                activity_emoji = {
                    "playing": "🎮",
                    "watching": "👀",
                    "listening": "🎧",
                }
                activity_display = f"{activity_emoji.get(settings.activity_type, '📺')} **{settings.activity_type.title()}** {settings.activity_text}"
                embed.add_field(name="🎯 Activity", value=activity_display, inline=True)
            else:
                embed.add_field(name="🎯 Activity", value="❌ Default", inline=True)

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Failed to get bot info: {e}")
            embed = make_embed(action="error", title="❌ Error", description=f"Failed to retrieve bot info: {e}")
            await ctx.send(embed=embed)

    @commands.command(name="botreset")
    @require_owner()
    async def bot_reset(self, ctx: commands.Context) -> None:
        """Reset all bot customization to defaults.

        This will reset custom name, status, and activity to their defaults.
        Avatar and banner URLs will be cleared from the database (but the current images will remain until manually changed).
        """
        try:
            # Clear database settings
            await self.db.reset_bot_settings()

            # Reset name to default
            await self.bot.user.edit(username="Vertigo")  # type: ignore[union-attr]

            # Reset status and activity to default
            await self.bot.change_presence(status=discord.Status.online, activity=None)

            embed = make_embed(action="botreset", title="🔄 Bot Reset Complete", description="All bot customization settings have been reset to defaults.\n\n**Reset:**\n- Name → Vertigo\n- Status → Online\n- Activity → None\n- Database settings cleared\n\n**Note:** Avatar and banner images remain unchanged until you manually update them.")
            await ctx.send(embed=embed)

        except discord.HTTPException as e:
            logger.error(f"Failed to reset bot: {e}")
            embed = make_embed(action="error", title="❌ Error", description=f"Failed to reset bot: {e.text if hasattr(e, 'text') else str(e)}")
            await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"Failed to reset bot: {e}")
            embed = make_embed(action="error", title="❌ Error", description=f"Failed to reset bot: {e}")
            await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(BotManagementCog(bot))
