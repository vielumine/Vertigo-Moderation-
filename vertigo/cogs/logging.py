"""Event logging via webhooks + owner DM forwarding."""

from __future__ import annotations

import logging
from typing import Iterable

import aiohttp
import discord
from discord.ext import commands

import config
from helpers import make_embed, notify_owner

logger = logging.getLogger(__name__)


class CopyIdView(discord.ui.View):
    def __init__(self, *, user_id: int | None = None, message_id: int | None = None) -> None:
        super().__init__(timeout=600)
        self.user_id = user_id
        self.message_id = message_id

        if user_id is None:
            self.copy_user_id.disabled = True
        if message_id is None:
            self.copy_message_id.disabled = True

    @discord.ui.button(label="Copy User ID", style=discord.ButtonStyle.secondary)
    async def copy_user_id(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:  # type: ignore[override]
        await interaction.response.send_message(str(self.user_id), ephemeral=True)

    @discord.ui.button(label="Copy Message ID", style=discord.ButtonStyle.secondary)
    async def copy_message_id(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:  # type: ignore[override]
        await interaction.response.send_message(str(self.message_id), ephemeral=True)


class LoggingCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.session: aiohttp.ClientSession | None = None
        self.message_webhook: discord.Webhook | None = None
        self.join_leave_webhook: discord.Webhook | None = None
        self.role_webhook: discord.Webhook | None = None

    async def cog_load(self) -> None:
        self.session = aiohttp.ClientSession()
        if config.MESSAGE_LOGGER_WEBHOOK:
            self.message_webhook = discord.Webhook.from_url(config.MESSAGE_LOGGER_WEBHOOK, session=self.session)
        if config.JOIN_LEAVE_LOGGER_WEBHOOK:
            self.join_leave_webhook = discord.Webhook.from_url(config.JOIN_LEAVE_LOGGER_WEBHOOK, session=self.session)
        if config.ROLE_LOGGER_WEBHOOK:
            self.role_webhook = discord.Webhook.from_url(config.ROLE_LOGGER_WEBHOOK, session=self.session)

    async def cog_unload(self) -> None:
        if self.session:
            await self.session.close()
            self.session = None

    async def _send_webhook(self, webhook: discord.Webhook | None, *, embed: discord.Embed, view: discord.ui.View | None = None) -> None:
        if webhook is None:
            return
        try:
            await webhook.send(embed=embed, view=view, username=config.BOT_NAME)
        except Exception:
            logger.exception("Failed to send webhook")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return

        if message.guild is None:
            # DM forwarding to owner
            if config.OWNER_ID and message.author.id != config.OWNER_ID:
                embed = make_embed(
                    action="dm",
                    title="DM Forward",
                    description=f"From: {message.author} (`{message.author.id}`)\nContent: {message.content or '(no content)'}",
                )
                if message.attachments:
                    embed.add_field(name="Attachments", value="\n".join(a.url for a in message.attachments)[:1024], inline=False)
                await notify_owner(self.bot, embed=embed)
            return

        return

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        if after.guild is None or after.author.bot:
            return
        if before.content == after.content:
            return

        embed = make_embed(
            action="message_edit",
            title="Message Edited",
            description=(
                f"Author: {after.author} (`{after.author.id}`)\n"
                f"Channel: {after.channel.mention}\n"
                f"Message ID: `{after.id}`"
            ),
        )
        embed.add_field(name="Before", value=(before.content or "(empty)")[:1024], inline=False)
        embed.add_field(name="After", value=(after.content or "(empty)")[:1024], inline=False)
        if after.attachments:
            embed.add_field(name="Attachments", value="\n".join(a.url for a in after.attachments)[:1024], inline=False)

        view = CopyIdView(user_id=after.author.id, message_id=after.id)
        await self._send_webhook(self.message_webhook, embed=embed, view=view)

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message) -> None:
        if message.guild is None or message.author.bot:
            return

        embed = make_embed(
            action="message_delete",
            title="Message Deleted",
            description=(
                f"Author: {message.author} (`{message.author.id}`)\n"
                f"Channel: {message.channel.mention}\n"
                f"Message ID: `{message.id}`"
            ),
        )
        embed.add_field(name="Content", value=(message.content or "(empty)")[:1024], inline=False)
        if message.attachments:
            embed.add_field(name="Attachments", value="\n".join(a.url for a in message.attachments)[:1024], inline=False)

        view = CopyIdView(user_id=message.author.id, message_id=message.id)
        await self._send_webhook(self.message_webhook, embed=embed, view=view)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        embed = make_embed(
            action="join",
            title="Member Joined",
            description=f"{member} (`{member.id}`)",
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Account Created", value=discord.utils.format_dt(member.created_at), inline=False)
        roles = [r.name for r in member.roles if r != member.guild.default_role]
        embed.add_field(name="Roles", value=", ".join(roles) if roles else "None", inline=False)
        await self._send_webhook(self.join_leave_webhook, embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        embed = make_embed(
            action="leave",
            title="Member Left",
            description=f"{member} (`{member.id}`)",
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Account Created", value=discord.utils.format_dt(member.created_at), inline=False)
        if member.joined_at:
            embed.add_field(name="Joined", value=discord.utils.format_dt(member.joined_at), inline=False)
        await self._send_webhook(self.join_leave_webhook, embed=embed)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
        if before.roles == after.roles:
            return
        added = [r for r in after.roles if r not in before.roles and r != after.guild.default_role]
        removed = [r for r in before.roles if r not in after.roles and r != after.guild.default_role]
        if not added and not removed:
            return

        embed = make_embed(
            action="role_update",
            title="Roles Updated",
            description=f"Member: {after} (`{after.id}`)",
        )
        if added:
            embed.add_field(name="Added", value=", ".join(r.name for r in added)[:1024], inline=False)
        if removed:
            embed.add_field(name="Removed", value=", ".join(r.name for r in removed)[:1024], inline=False)

        await self._send_webhook(self.role_webhook, embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(LoggingCog(bot))
