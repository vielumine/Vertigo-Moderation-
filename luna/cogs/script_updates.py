"""Script update panel for managing webhook announcements."""

from __future__ import annotations

import logging

import aiohttp
import discord
from discord.ext import commands

import config
from database import Database, ScriptUpdateSettings
from helpers import is_admin_member, make_embed, parse_id_list, require_admin

logger = logging.getLogger(__name__)


class ScriptUpdatePanelView(discord.ui.View):
    """Panel view for script update settings."""

    def __init__(self, settings: ScriptUpdateSettings, bot: commands.Bot, guild_id: int, timeout: float = 180) -> None:
        super().__init__(timeout=timeout)
        self.settings = settings
        self.bot = bot
        self.guild_id = guild_id
        self.message: discord.Message | None = None
        self.original_author_id: int | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.original_author_id and interaction.user.id != self.original_author_id:
            await interaction.response.send_message("Only the person who opened this panel can use these controls.", ephemeral=True)
            return False
        if interaction.guild is None or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("This panel can only be used in a server.", ephemeral=True)
            return False
        settings = await self.bot.db.get_guild_settings(interaction.guild.id, default_prefix=config.DEFAULT_PREFIX)
        if not is_admin_member(interaction.user, settings):
            await interaction.response.send_message("You don't have permission to use this panel.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Set Webhook", style=discord.ButtonStyle.primary, emoji="🔗")
    async def set_webhook_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        modal = ScriptWebhookModal(self)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Set Roles", style=discord.ButtonStyle.primary, emoji="📌")
    async def set_roles_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        modal = ScriptRolesModal(self)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Send Update", style=discord.ButtonStyle.success, emoji="📝")
    async def send_update_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        modal = ScriptUpdateModal(self)
        await interaction.response.send_modal(modal)

    async def refresh_message(self) -> None:
        if not self.message:
            return
        embed = await self.create_embed()
        await self.message.edit(embed=embed, view=self)

    async def create_embed(self) -> discord.Embed:
        guild = self.bot.get_guild(self.guild_id)
        role_lines = []
        missing_roles = []
        if guild:
            for role_id in self.settings.role_ids:
                role = guild.get_role(role_id)
                if role:
                    role_lines.append(role.mention)
                else:
                    missing_roles.append(str(role_id))

        roles_display = "\n".join(role_lines) if role_lines else "None"
        if missing_roles:
            roles_display += f"\nMissing: {', '.join(missing_roles)}"

        embed = make_embed(
            action="script_update",
            title="📢 Script Update Panel",
            description="Manage script update settings and send announcements.",
        )
        embed.add_field(
            name="Webhook URL",
            value=self.settings.webhook_url or "Not set",
            inline=False,
        )
        embed.add_field(
            name="Webhook Name",
            value=self.settings.webhook_name or "Not set",
            inline=True,
        )
        embed.add_field(
            name="Saved Roles",
            value=roles_display,
            inline=False,
        )
        return embed

    async def add_fire_reaction(self, message: discord.Message, guild: discord.Guild | None = None) -> None:
        guild = message.guild or guild
        if guild is None:
            return
        channel = message.channel
        if not isinstance(channel, discord.abc.GuildChannel):
            resolved_channel = guild.get_channel(message.channel.id)
            if resolved_channel is not None:
                channel = resolved_channel

        guild_member = guild.me or guild.get_member(self.bot.user.id) if self.bot.user else None
        if guild_member is None:
            return
        perms = None
        if isinstance(channel, (discord.TextChannel, discord.Thread)):
            perms = channel.permissions_for(guild_member)
        elif isinstance(channel, discord.abc.GuildChannel):
            perms = channel.permissions_for(guild_member)
        if not perms or not perms.add_reactions:
            return
        try:
            await message.add_reaction("🔥")
        except discord.Forbidden:
            logger.debug("Missing permissions to add 🔥 reaction in channel %s", channel)
        except Exception:
            logger.exception("Failed to add 🔥 reaction")


class ScriptWebhookModal(discord.ui.Modal):
    """Modal for setting script update webhook."""

    def __init__(self, panel: ScriptUpdatePanelView) -> None:
        super().__init__(title="Set Script Update Webhook", timeout=300)
        self.panel = panel

        self.add_item(discord.ui.TextInput(
            label="Webhook URL",
            placeholder="https://discord.com/api/webhooks/...",
            style=discord.TextStyle.short,
            required=True,
            max_length=200,
        ))
        self.add_item(discord.ui.TextInput(
            label="Webhook Name (optional)",
            placeholder="Luna Script Updates",
            style=discord.TextStyle.short,
            required=False,
            max_length=80,
        ))

    async def on_submit(self, interaction: discord.Interaction) -> None:
        webhook_url = self.children[0].value.strip()
        webhook_name = self.children[1].value.strip() or None

        try:
            async with aiohttp.ClientSession() as session:
                webhook = discord.Webhook.from_url(webhook_url, session=session)
                webhook_data = await webhook.fetch()
                if interaction.guild and webhook_data.guild_id and webhook_data.guild_id != interaction.guild.id:
                    raise ValueError("Webhook does not belong to this server")
                if not webhook_name:
                    webhook_name = webhook_data.name
        except Exception as exc:
            logger.error("Invalid webhook URL: %s", exc)
            embed = make_embed(action="error", title="❌ Invalid Webhook", description="Please provide a valid webhook URL.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await self.panel.bot.db.update_script_update_settings(
            self.panel.guild_id,
            webhook_url=webhook_url,
            webhook_name=webhook_name,
        )
        self.panel.settings = await self.panel.bot.db.get_script_update_settings(self.panel.guild_id)

        embed = make_embed(
            action="script_update",
            title="✅ Webhook Saved",
            description="Script update webhook settings have been updated.",
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        await self.panel.refresh_message()


class ScriptRolesModal(discord.ui.Modal):
    """Modal for setting script update roles."""

    def __init__(self, panel: ScriptUpdatePanelView) -> None:
        super().__init__(title="Set Script Update Roles", timeout=300)
        self.panel = panel

        self.add_item(discord.ui.TextInput(
            label="Role IDs or Mentions",
            placeholder="@Updates, 1234567890",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1000,
        ))

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Guild not found.", ephemeral=True)
            return

        raw_roles = self.children[0].value.replace("\n", ",")
        role_ids = list(dict.fromkeys(parse_id_list(raw_roles)))
        if not role_ids:
            embed = make_embed(action="error", title="❌ Invalid Roles", description="Provide at least one valid role mention or ID.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        valid_roles = []
        invalid_roles = []
        for role_id in role_ids:
            role = interaction.guild.get_role(role_id)
            if role:
                valid_roles.append(role_id)
            else:
                invalid_roles.append(str(role_id))

        if not valid_roles:
            embed = make_embed(action="error", title="❌ Roles Not Found", description="None of the provided roles exist in this server.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await self.panel.bot.db.update_script_update_settings(self.panel.guild_id, role_ids=valid_roles)
        self.panel.settings = await self.panel.bot.db.get_script_update_settings(self.panel.guild_id)

        description = f"Saved {len(valid_roles)} role(s) for script updates."
        if invalid_roles:
            description += f"\nMissing: {', '.join(invalid_roles)}"

        embed = make_embed(action="script_update", title="✅ Roles Saved", description=description)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        await self.panel.refresh_message()


class ScriptUpdateModal(discord.ui.Modal):
    """Modal for sending a script update."""

    def __init__(self, panel: ScriptUpdatePanelView) -> None:
        super().__init__(title="Send Script Update", timeout=300)
        self.panel = panel

        self.add_item(discord.ui.TextInput(
            label="Update Title",
            placeholder="Script Update - Version 2.1",
            style=discord.TextStyle.short,
            required=True,
            max_length=120,
        ))
        self.add_item(discord.ui.TextInput(
            label="Update Details",
            placeholder="Describe the changes...",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1500,
        ))

    async def on_submit(self, interaction: discord.Interaction) -> None:
        settings = await self.panel.bot.db.get_script_update_settings(self.panel.guild_id)
        if not settings.webhook_url:
            embed = make_embed(action="error", title="❌ No Webhook", description="Set a webhook before sending updates.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        title = self.children[0].value
        details = self.children[1].value
        guild = interaction.guild
        role_mentions = []
        if guild:
            for role_id in settings.role_ids:
                role = guild.get_role(role_id)
                if role:
                    role_mentions.append(role.mention)

        content = " ".join(role_mentions) if role_mentions else None

        embed = make_embed(
            action="script_update",
            title=title,
            description=details,
        )

        try:
            async with aiohttp.ClientSession() as session:
                webhook = discord.Webhook.from_url(settings.webhook_url, session=session)
                message = await webhook.send(
                    content=content,
                    embed=embed,
                    username=settings.webhook_name or config.BOT_NAME,
                    wait=True,
                )
                if isinstance(message, discord.Message):
                    await self.panel.add_fire_reaction(message, guild=guild)
        except Exception as exc:
            logger.error("Failed to send script update: %s", exc)
            embed = make_embed(action="error", title="❌ Update Failed", description="Unable to send the script update.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        confirmation = make_embed(
            action="script_update",
            title="✅ Update Sent",
            description="Script update has been posted successfully.",
        )
        await interaction.response.send_message(embed=confirmation, ephemeral=True)


class ScriptUpdatesCog(commands.Cog):
    """Commands for script update panel."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @property
    def db(self) -> Database:
        return self.bot.db  # type: ignore[attr-defined]

    @commands.command(name="scriptpanel")
    @commands.guild_only()
    @require_admin()
    async def script_panel(self, ctx: commands.Context) -> None:
        settings = await self.db.get_script_update_settings(ctx.guild.id)
        view = ScriptUpdatePanelView(settings, self.bot, ctx.guild.id)
        view.original_author_id = ctx.author.id
        embed = await view.create_embed()
        message = await ctx.send(embed=embed, view=view)
        view.message = message


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ScriptUpdatesCog(bot))
