"""Notification management commands for administrators."""

from __future__ import annotations

import logging

import discord
from discord.ext import commands

import config
from database import Database
from helpers import commands_channel_check, make_embed, require_admin, safe_delete

logger = logging.getLogger(__name__)


class NotificationsCog(commands.Cog):
    """Commands for managing DM notifications."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @property
    def db(self) -> Database:
        return self.bot.db  # type: ignore[attr-defined]

    @commands.group(name="dmnotify", aliases=["dmn"])
    @commands.guild_only()
    @commands_channel_check()
    @require_admin()
    async def dm_notify(self, ctx: commands.Context) -> None:
        """Manage DM notification settings."""
        if ctx.invoked_subcommand is None:
            embed = make_embed(
                action="help",
                title="📬 DM Notification Commands",
                description="Manage automated DM notifications for moderation actions."
            )
            embed.add_field(
                name="Commands",
                value=(
                    f"`{ctx.prefix}dmnotify status` - View current settings\n"
                    f"`{ctx.prefix}dmnotify enable` - Enable all DM notifications\n"
                    f"`{ctx.prefix}dmnotify disable` - Disable all DM notifications\n"
                    f"`{ctx.prefix}dmnotify toggle <type>` - Toggle specific notification type\n"
                    f"`{ctx.prefix}dmnotify test <member>` - Test DM notification"
                ),
                inline=False
            )
            embed.add_field(
                name="Notification Types",
                value="warns, mutes, kicks, bans, flags",
                inline=False
            )
            await ctx.send(embed=embed)

    @dm_notify.command(name="status")
    async def dm_notify_status(self, ctx: commands.Context) -> None:
        """View DM notification settings."""
        settings = await self.db.get_dm_notification_settings(ctx.guild.id)  # type: ignore[union-attr]

        status_icon = "✅" if settings.enabled else "❌"
        embed = make_embed(
            action="success",
            title=f"📬 DM Notification Settings",
            description=f"**Master Status:** {status_icon} {'Enabled' if settings.enabled else 'Disabled'}"
        )

        notif_status = {
            "Warnings": ("✅" if settings.notify_warns else "❌"),
            "Mutes": ("✅" if settings.notify_mutes else "❌"),
            "Kicks": ("✅" if settings.notify_kicks else "❌"),
            "Bans": ("✅" if settings.notify_bans else "❌"),
            "Staff Flags": ("✅" if settings.notify_flags else "❌"),
        }

        status_text = "\n".join(f"{icon} {name}" for name, icon in notif_status.items())
        embed.add_field(name="📋 Notification Types", value=status_text, inline=False)

        await ctx.send(embed=embed)
        await safe_delete(ctx.message)

    @dm_notify.command(name="enable")
    async def dm_notify_enable(self, ctx: commands.Context) -> None:
        """Enable all DM notifications."""
        await self.db.update_dm_notification_settings(ctx.guild.id, enabled=True)  # type: ignore[union-attr]

        embed = make_embed(
            action="success",
            title="✅ DM Notifications Enabled",
            description="All moderation action DM notifications are now enabled."
        )
        await ctx.send(embed=embed)
        await safe_delete(ctx.message)

    @dm_notify.command(name="disable")
    async def dm_notify_disable(self, ctx: commands.Context) -> None:
        """Disable all DM notifications."""
        await self.db.update_dm_notification_settings(ctx.guild.id, enabled=False)  # type: ignore[union-attr]

        embed = make_embed(
            action="error",
            title="❌ DM Notifications Disabled",
            description="All moderation action DM notifications have been disabled."
        )
        await ctx.send(embed=embed)
        await safe_delete(ctx.message)

    @dm_notify.command(name="toggle")
    async def dm_notify_toggle(self, ctx: commands.Context, notification_type: str) -> None:
        """Toggle a specific notification type.
        
        Types: warns, mutes, kicks, bans, flags
        """
        notification_type = notification_type.lower()
        valid_types = ["warns", "mutes", "kicks", "bans", "flags"]

        if notification_type not in valid_types:
            embed = make_embed(
                action="error",
                title="❌ Invalid Type",
                description=f"Valid types: {', '.join(valid_types)}"
            )
            await ctx.send(embed=embed)
            return

        settings = await self.db.get_dm_notification_settings(ctx.guild.id)  # type: ignore[union-attr]

        # Get current value and toggle
        attr_name = f"notify_{notification_type}"
        current_value = getattr(settings, attr_name)
        new_value = not current_value

        # Update database
        await self.db.update_dm_notification_settings(
            ctx.guild.id,  # type: ignore[union-attr]
            **{attr_name: new_value}
        )

        status = "enabled" if new_value else "disabled"
        icon = "✅" if new_value else "❌"
        embed = make_embed(
            action="success" if new_value else "error",
            title=f"{icon} {notification_type.title()} Notifications {status.title()}",
            description=f"DM notifications for {notification_type} are now {status}."
        )
        await ctx.send(embed=embed)
        await safe_delete(ctx.message)

    @dm_notify.command(name="test")
    async def dm_notify_test(self, ctx: commands.Context, member: discord.Member | None = None) -> None:
        """Test DM notifications by sending a test message.
        
        If no member is specified, sends test to command author.
        """
        target = member or ctx.author

        embed = make_embed(
            action="success",
            title=f"🧪 Test Notification from {ctx.guild.name}",  # type: ignore[union-attr]
            description="This is a test DM notification from the moderation system."
        )
        embed.add_field(
            name="ℹ️ Information",
            value="If you received this message, DM notifications are working correctly.",
            inline=False
        )
        embed.set_footer(text=f"{config.BOT_NAME} • Test")

        try:
            await target.send(embed=embed)
            response_embed = make_embed(
                action="success",
                title="✅ Test Successful",
                description=f"Test notification sent to {target.mention}."
            )
        except discord.Forbidden:
            response_embed = make_embed(
                action="error",
                title="❌ Test Failed",
                description=f"{target.mention} has DMs disabled or has blocked the bot."
            )
        except Exception as e:
            logger.error(f"Test notification error: {e}")
            response_embed = make_embed(
                action="error",
                title="❌ Test Failed",
                description=f"Error sending test notification: {str(e)}"
            )

        await ctx.send(embed=response_embed)
        await safe_delete(ctx.message)

    @commands.command(name="optout")
    @commands.guild_only()
    async def optout(self, ctx: commands.Context) -> None:
        """Opt out of receiving moderation DM notifications."""
        await self.db.set_dm_preference(ctx.author.id, ctx.guild.id, False)  # type: ignore[union-attr]

        embed = make_embed(
            action="success",
            title="✅ Opted Out",
            description="You will no longer receive DM notifications for moderation actions in this server."
        )
        embed.add_field(
            name="ℹ️ Note",
            value=f"You can opt back in anytime using `{ctx.prefix}optin`",
            inline=False
        )
        await ctx.send(embed=embed)

    @commands.command(name="optin")
    @commands.guild_only()
    async def optin(self, ctx: commands.Context) -> None:
        """Opt in to receiving moderation DM notifications."""
        await self.db.set_dm_preference(ctx.author.id, ctx.guild.id, True)  # type: ignore[union-attr]

        embed = make_embed(
            action="success",
            title="✅ Opted In",
            description="You will now receive DM notifications for moderation actions in this server."
        )
        embed.add_field(
            name="ℹ️ Note",
            value=f"You can opt out anytime using `{ctx.prefix}optout`",
            inline=False
        )
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(NotificationsCog(bot))
