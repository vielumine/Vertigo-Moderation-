"""Interactive setup system using buttons + modals."""

from __future__ import annotations

import logging

import discord
from discord.ext import commands

import config
from database import Database
from helpers import make_embed, parse_id_list

logger = logging.getLogger(__name__)


class _RolesModal(discord.ui.Modal, title="Set Roles"):
    staff_role_ids = discord.ui.TextInput(label="Staff Role IDs (comma-separated)", required=False, max_length=4000)
    member_role_id = discord.ui.TextInput(label="Member Role ID", required=False, max_length=50)
    head_mod_role_ids = discord.ui.TextInput(label="Head Mod Role IDs (comma-separated)", required=False, max_length=4000)
    senior_mod_role_ids = discord.ui.TextInput(label="Senior Mod Role IDs (comma-separated)", required=False, max_length=4000)
    moderator_role_ids = discord.ui.TextInput(label="Moderator Role IDs (comma-separated)", required=False, max_length=4000)

    def __init__(self, *, db: Database, guild_id: int) -> None:
        super().__init__()
        self.db = db
        self.guild_id = guild_id

    async def on_submit(self, interaction: discord.Interaction) -> None:
        staff = parse_id_list(str(self.staff_role_ids.value))
        head = parse_id_list(str(self.head_mod_role_ids.value))
        senior = parse_id_list(str(self.senior_mod_role_ids.value))
        mods = parse_id_list(str(self.moderator_role_ids.value))

        member_role = None
        if self.member_role_id.value:
            try:
                member_role = int(self.member_role_id.value.strip())
            except ValueError:
                await interaction.response.send_message("Invalid member role id.", ephemeral=True)
                return

        await self.db.update_guild_settings(
            self.guild_id,
            staff_role_ids=staff,
            member_role_id=member_role,
            head_mod_role_ids=head,
            senior_mod_role_ids=senior,
            moderator_role_ids=mods,
        )

        await interaction.response.send_message("Roles updated.", ephemeral=True)


class _ChannelModal(discord.ui.Modal, title="Set Channel"):
    channel_value = discord.ui.TextInput(label="Channel ID or #mention", required=True, max_length=100)

    def __init__(self, *, db: Database, guild_id: int, field: str, label: str) -> None:
        super().__init__(title=label)
        self.db = db
        self.guild_id = guild_id
        self.field = field

    async def on_submit(self, interaction: discord.Interaction) -> None:
        raw = str(self.channel_value.value)
        channel_id = None
        for token in raw.replace("<", " ").replace(">", " ").split():
            if token.startswith("#"):
                token = token[1:]
            if token.isdigit():
                channel_id = int(token)
                break

        if channel_id is None:
            await interaction.response.send_message("Invalid channel.", ephemeral=True)
            return

        guild = interaction.guild
        if guild is None or guild.get_channel(channel_id) is None:
            await interaction.response.send_message("Channel not found in this guild.", ephemeral=True)
            return

        await self.db.update_guild_settings(self.guild_id, **{self.field: channel_id})
        await interaction.response.send_message("Channel updated.", ephemeral=True)


class _WarnDurationModal(discord.ui.Modal, title="Set Warn Duration"):
    days = discord.ui.TextInput(label="Warn Duration (days: 7-30)", required=True, max_length=5)

    def __init__(self, *, db: Database, guild_id: int) -> None:
        super().__init__()
        self.db = db
        self.guild_id = guild_id

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            value = int(self.days.value)
        except ValueError:
            await interaction.response.send_message("Invalid number.", ephemeral=True)
            return
        if value < 7 or value > 30:
            await interaction.response.send_message("Warn duration must be between 7 and 30.", ephemeral=True)
            return
        await self.db.update_guild_settings(self.guild_id, warn_duration=value)
        await interaction.response.send_message("Warn duration updated.", ephemeral=True)


class _PrefixModal(discord.ui.Modal, title="Change Prefix"):
    prefix = discord.ui.TextInput(label="New Prefix (max 5 chars)", required=True, max_length=5)

    def __init__(self, *, db: Database, guild_id: int) -> None:
        super().__init__()
        self.db = db
        self.guild_id = guild_id

    async def on_submit(self, interaction: discord.Interaction) -> None:
        value = self.prefix.value.strip()
        if not value or len(value) > 5:
            await interaction.response.send_message("Invalid prefix.", ephemeral=True)
            return
        await self.db.update_guild_settings(self.guild_id, prefix=value)
        await interaction.response.send_message(f"Prefix updated to `{value}`.", ephemeral=True)


class SetupView(discord.ui.View):
    def __init__(self, *, db: Database, guild_id: int, author_id: int) -> None:
        super().__init__(timeout=300)
        self.db = db
        self.guild_id = guild_id
        self.author_id = author_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not interaction.user or interaction.user.id != self.author_id:
            await interaction.response.send_message("Only the command invoker can use this setup menu.", ephemeral=True)
            return False
        if not isinstance(interaction.user, discord.Member) or not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("You need Administrator permission to configure setup.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="🎯 Set Roles", style=discord.ButtonStyle.secondary)
    async def set_roles(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:  # type: ignore[override]
        await interaction.response.send_modal(_RolesModal(db=self.db, guild_id=self.guild_id))

    @discord.ui.button(label="📜 Set Modlog Channel", style=discord.ButtonStyle.secondary)
    async def set_modlog(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:  # type: ignore[override]
        await interaction.response.send_modal(_ChannelModal(db=self.db, guild_id=self.guild_id, field="modlog_channel_id", label="Set Modlog Channel"))

    @discord.ui.button(label="⏱️ Set Warn Duration", style=discord.ButtonStyle.secondary)
    async def set_warn_duration(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:  # type: ignore[override]
        await interaction.response.send_modal(_WarnDurationModal(db=self.db, guild_id=self.guild_id))

    @discord.ui.button(label="🔧 Change Prefix", style=discord.ButtonStyle.secondary)
    async def set_prefix(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:  # type: ignore[override]
        await interaction.response.send_modal(_PrefixModal(db=self.db, guild_id=self.guild_id))

    @discord.ui.button(label="🛑 Set Commands Channel", style=discord.ButtonStyle.secondary)
    async def set_commands_channel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:  # type: ignore[override]
        await interaction.response.send_modal(_ChannelModal(db=self.db, guild_id=self.guild_id, field="commands_channel_id", label="Set Commands Channel"))

    @discord.ui.button(label="👁️ See Settings", style=discord.ButtonStyle.primary)
    async def see_settings(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:  # type: ignore[override]
        settings = await self.db.get_guild_settings(self.guild_id, default_prefix=config.DEFAULT_PREFIX)
        embed = make_embed(action="setup", title="Current Settings")
        embed.add_field(name="Prefix", value=settings.prefix, inline=True)
        embed.add_field(name="Warn Duration", value=f"{settings.warn_duration} days", inline=True)
        embed.add_field(name="Modlog Channel", value=str(settings.modlog_channel_id or "None"), inline=True)
        embed.add_field(name="Commands Channel", value=str(settings.commands_channel_id or "None"), inline=True)
        embed.add_field(name="Staff Role IDs", value=", ".join(map(str, settings.staff_role_ids)) or "None", inline=False)
        embed.add_field(name="Member Role ID", value=str(settings.member_role_id or "None"), inline=True)
        embed.add_field(name="Head Mod Role IDs", value=", ".join(map(str, settings.head_mod_role_ids)) or "None", inline=False)
        embed.add_field(name="Senior Mod Role IDs", value=", ".join(map(str, settings.senior_mod_role_ids)) or "None", inline=False)
        embed.add_field(name="Moderator Role IDs", value=", ".join(map(str, settings.moderator_role_ids)) or "None", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)


# ----------------------------- Admin setup -----------------------------

class _FlagDurationModal(discord.ui.Modal, title="Set Flag Duration"):
    days = discord.ui.TextInput(label="Flag Duration (days: 30-90)", required=True, max_length=5)

    def __init__(self, *, db: Database, guild_id: int) -> None:
        super().__init__()
        self.db = db
        self.guild_id = guild_id

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            value = int(self.days.value)
        except ValueError:
            await interaction.response.send_message("Invalid number.", ephemeral=True)
            return
        if value < 30 or value > 90:
            await interaction.response.send_message("Flag duration must be between 30 and 90.", ephemeral=True)
            return
        await self.db.update_guild_settings(self.guild_id, flag_duration=value)
        await interaction.response.send_message("Flag duration updated.", ephemeral=True)


class _LockCategoriesModal(discord.ui.Modal, title="Set Lock Categories"):
    category_ids = discord.ui.TextInput(label="Category IDs (comma-separated)", required=False, max_length=4000)

    def __init__(self, *, db: Database, guild_id: int) -> None:
        super().__init__()
        self.db = db
        self.guild_id = guild_id

    async def on_submit(self, interaction: discord.Interaction) -> None:
        values = parse_id_list(str(self.category_ids.value))
        await self.db.update_guild_settings(self.guild_id, lock_categories=values)
        await interaction.response.send_message("Lock categories updated.", ephemeral=True)


class _AdminRolesModal(discord.ui.Modal, title="Add Admin Roles"):
    admin_role_ids = discord.ui.TextInput(label="Admin Role IDs (comma-separated)", required=False, max_length=4000)

    def __init__(self, *, db: Database, guild_id: int) -> None:
        super().__init__()
        self.db = db
        self.guild_id = guild_id

    async def on_submit(self, interaction: discord.Interaction) -> None:
        values = parse_id_list(str(self.admin_role_ids.value))
        await self.db.update_guild_settings(self.guild_id, admin_role_ids=values)
        await interaction.response.send_message("Admin roles updated.", ephemeral=True)


class AdminSetupView(discord.ui.View):
    def __init__(self, *, db: Database, guild_id: int, author_id: int) -> None:
        super().__init__(timeout=300)
        self.db = db
        self.guild_id = guild_id
        self.author_id = author_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not interaction.user or interaction.user.id != self.author_id:
            await interaction.response.send_message("Only the command invoker can use this admin setup menu.", ephemeral=True)
            return False
        if not isinstance(interaction.user, discord.Member):
            return False
        settings = await self.db.get_guild_settings(self.guild_id, default_prefix=config.DEFAULT_PREFIX)
        if not (interaction.user.guild_permissions.administrator or any(r.id in settings.admin_role_ids for r in interaction.user.roles)):
            await interaction.response.send_message("You need an Admin role to use adminsetup.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="⏱️ Set Flag Duration", style=discord.ButtonStyle.secondary)
    async def set_flag_duration(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:  # type: ignore[override]
        await interaction.response.send_modal(_FlagDurationModal(db=self.db, guild_id=self.guild_id))

    @discord.ui.button(label="📂 Set Lock Categories", style=discord.ButtonStyle.secondary)
    async def set_lock_categories(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:  # type: ignore[override]
        await interaction.response.send_modal(_LockCategoriesModal(db=self.db, guild_id=self.guild_id))

    @discord.ui.button(label="👨‍💼 Add Admin Role", style=discord.ButtonStyle.secondary)
    async def add_admin_roles(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:  # type: ignore[override]
        await interaction.response.send_modal(_AdminRolesModal(db=self.db, guild_id=self.guild_id))

    @discord.ui.button(label="👁️ See Settings", style=discord.ButtonStyle.primary)
    async def see_settings(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:  # type: ignore[override]
        settings = await self.db.get_guild_settings(self.guild_id, default_prefix=config.DEFAULT_PREFIX)
        embed = make_embed(action="adminsetup", title="Admin Settings")
        embed.add_field(name="Flag Duration", value=f"{settings.flag_duration} days", inline=True)
        embed.add_field(name="Lock Categories", value=", ".join(map(str, settings.lock_categories)) or "None", inline=False)
        embed.add_field(name="Admin Roles", value=", ".join(map(str, settings.admin_role_ids)) or "None", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)


class SetupCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @property
    def db(self) -> Database:
        return self.bot.db  # type: ignore[attr-defined]

    @commands.command(name="setup")
    @commands.guild_only()
    async def setup_command(self, ctx: commands.Context) -> None:
        if not isinstance(ctx.author, discord.Member) or not ctx.author.guild_permissions.administrator:
            embed = make_embed(action="error", title="No Permission", description="You need Administrator permissions to run setup.")
            await ctx.send(embed=embed)
            return
        await self.db.ensure_guild_settings(ctx.guild.id, default_prefix=config.DEFAULT_PREFIX)  # type: ignore[union-attr]
        view = SetupView(db=self.db, guild_id=ctx.guild.id, author_id=ctx.author.id)  # type: ignore[union-attr]
        embed = make_embed(action="setup", title="🛠️ Setup", description="Use the buttons below to configure the server.")
        await ctx.send(embed=embed, view=view)

    @commands.command(name="adminsetup")
    @commands.guild_only()
    async def adminsetup_command(self, ctx: commands.Context) -> None:
        settings = await self.db.get_guild_settings(ctx.guild.id, default_prefix=config.DEFAULT_PREFIX)  # type: ignore[union-attr]
        if not isinstance(ctx.author, discord.Member) or not (ctx.author.guild_permissions.administrator or any(r.id in settings.admin_role_ids for r in ctx.author.roles)):
            embed = make_embed(action="error", title="❌ No Permission", description="You don't have permission to run adminsetup.")
            await ctx.send(embed=embed)
            return
        view = AdminSetupView(db=self.db, guild_id=ctx.guild.id, author_id=ctx.author.id)  # type: ignore[union-attr]
        embed = make_embed(action="adminsetup", title="🛠️ Admin Setup", description="Admin-only settings.")
        await ctx.send(embed=embed, view=view)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SetupCog(bot))
