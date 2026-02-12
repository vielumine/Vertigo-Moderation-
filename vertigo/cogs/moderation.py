"""Moderation - Standard moderation commands for Vertigo."""

from __future__ import annotations

import json
import logging
from datetime import timedelta

import discord
from discord.ext import commands

import config
from database import Database, GuildSettings
from helpers import (
    Page,
    PaginationView,
    attach_gif,
    can_bot_act_on,
    can_moderator_act_on,
    commands_channel_check,
    discord_timestamp,
    extract_id,
    humanize_seconds,
    log_to_modlog_channel,
    make_embed,
    notify_owner,
    notify_owner_action,
    parse_duration,
    require_level,
    safe_delete,
    safe_dm,
)

logger = logging.getLogger(__name__)


class ModerationUndoView(discord.ui.View):
    """View for undoing moderation actions."""
    
    def __init__(self, action_type: str, user_id: int, guild_id: int, message_id: int, original_author_id: int, timeout: float = 300):
        super().__init__(timeout=timeout)
        self.action_type = action_type
        self.user_id = user_id
        self.guild_id = guild_id
        self.message_id = message_id
        self.original_author_id = original_author_id
        
        # Remove buttons that don't apply to this action type
        if action_type == "warn":
            self.remove_item(self.undo_mute_button)
            self.remove_item(self.undo_warn_only_button)
            self.remove_item(self.undo_mute_only_button)
            self.remove_item(self.undo_both_button)
            self.remove_item(self.undo_ban_button)
        elif action_type == "mute":
            self.remove_item(self.undo_warn_button)
            self.remove_item(self.undo_warn_only_button)
            self.remove_item(self.undo_mute_only_button)
            self.remove_item(self.undo_both_button)
            self.remove_item(self.undo_ban_button)
        elif action_type == "ban":
            self.remove_item(self.undo_warn_button)
            self.remove_item(self.undo_mute_button)
            self.remove_item(self.undo_warn_only_button)
            self.remove_item(self.undo_mute_only_button)
            self.remove_item(self.undo_both_button)
        elif action_type in ["wm", "wmr"]:
            self.remove_item(self.undo_warn_button)
            self.remove_item(self.undo_mute_button)
            self.remove_item(self.undo_ban_button)
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Only the person who summoned the command can undo actions
        if interaction.user.id != self.original_author_id:
            await interaction.response.send_message("Only the person who performed this action can undo it.", ephemeral=True)
            return False
        return True
    
    @discord.ui.button(label="Undo Warn", style=discord.ButtonStyle.danger, emoji="↩️")
    async def undo_warn_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self._undo_warn(interaction)
    
    @discord.ui.button(label="Undo Mute", style=discord.ButtonStyle.danger, emoji="↩️")
    async def undo_mute_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self._undo_mute(interaction)
    
    @discord.ui.button(label="Undo Warn Only", style=discord.ButtonStyle.danger, emoji="↩️")
    async def undo_warn_only_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self._undo_warn(interaction)
    
    @discord.ui.button(label="Undo Mute Only", style=discord.ButtonStyle.danger, emoji="↩️")
    async def undo_mute_only_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self._undo_mute(interaction)
    
    @discord.ui.button(label="Undo Warn & Mute", style=discord.ButtonStyle.danger, emoji="↩️")
    async def undo_both_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        # We need to defer because we might do multiple responses or it might take time
        await interaction.response.defer(ephemeral=True)
        warn_ok = await self._undo_warn(interaction, respond=False)
        mute_ok = await self._undo_mute(interaction, respond=False)
        
        if warn_ok and mute_ok:
            await interaction.followup.send("✅ Both warn and mute undone successfully.", ephemeral=True)
        elif warn_ok:
            await interaction.followup.send("✅ Warn undone, but mute undo failed or was not found.", ephemeral=True)
        elif mute_ok:
            await interaction.followup.send("✅ Mute undone, but warn undo failed or was not found.", ephemeral=True)
        else:
            await interaction.followup.send("❌ Failed to undo actions.", ephemeral=True)
    
    @discord.ui.button(label="Undo Ban", style=discord.ButtonStyle.danger, emoji="↩️")
    async def undo_ban_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self._undo_ban(interaction)
    
    async def _undo_warn(self, interaction: discord.Interaction, respond: bool = True) -> bool:
        try:
            # Get the most recent warning for this user
            async with interaction.client.db.conn.execute(
                "SELECT id FROM warnings WHERE guild_id = ? AND user_id = ? AND is_active = 1 ORDER BY id DESC LIMIT 1",
                (self.guild_id, self.user_id)
            ) as cursor:
                row = await cursor.fetchone()
                
            if row:
                await interaction.client.db.deactivate_warning(warn_id=row["id"], guild_id=self.guild_id)
                await interaction.client.db.add_modlog(
                    guild_id=self.guild_id,
                    action_type="undo_warn",
                    user_id=self.user_id,
                    moderator_id=interaction.user.id,
                    reason=f"Undo warn (original message: {self.message_id})"
                )

                # Log to modlog channel
                settings = await interaction.client.db.get_guild_settings(self.guild_id, default_prefix=config.DEFAULT_PREFIX)
                log_embed = make_embed(
                    action="unwarn",
                    title="↩️ Moderation Action Undone: Warn",
                    description=f"**Target:** <@{self.user_id}> ({self.user_id})\n**Moderator:** {interaction.user.mention}\n**Original Message ID:** `{self.message_id}`"
                )
                await log_to_modlog_channel(interaction.client, guild=interaction.guild, settings=settings, embed=log_embed, file=None)

                if respond:
                    await interaction.response.send_message("✅ Warn undone successfully.", ephemeral=True)
                return True
            else:
                if respond:
                    await interaction.response.send_message("❌ No active warnings found to undo.", ephemeral=True)
                return False
        except Exception as e:
            logger.error(f"Undo warn error: {e}")
            if respond:
                if not interaction.response.is_done():
                    await interaction.response.send_message("❌ Failed to undo warn.", ephemeral=True)
                else:
                    await interaction.followup.send("❌ Failed to undo warn.", ephemeral=True)
            return False
    
    async def _undo_mute(self, interaction: discord.Interaction, respond: bool = True) -> bool:
        try:
            # Remove timeout
            guild = interaction.guild
            if not guild:
                return False
            member = guild.get_member(self.user_id)
            if member:
                await member.timeout(None, reason="Undo mute")
                await interaction.client.db.deactivate_active_mutes(guild_id=self.guild_id, user_id=self.user_id)
                await interaction.client.db.add_modlog(
                    guild_id=self.guild_id,
                    action_type="undo_mute",
                    user_id=self.user_id,
                    moderator_id=interaction.user.id,
                    reason=f"Undo mute (original message: {self.message_id})"
                )

                # Log to modlog channel
                settings = await interaction.client.db.get_guild_settings(self.guild_id, default_prefix=config.DEFAULT_PREFIX)
                log_embed = make_embed(
                    action="unmute",
                    title="↩️ Moderation Action Undone: Mute",
                    description=f"**Target:** {member.mention} ({member.id})\n**Moderator:** {interaction.user.mention}\n**Original Message ID:** `{self.message_id}`"
                )
                await log_to_modlog_channel(interaction.client, guild=interaction.guild, settings=settings, embed=log_embed, file=None)

                if respond:
                    await interaction.response.send_message("✅ Mute undone successfully.", ephemeral=True)
                return True
            else:
                if respond:
                    await interaction.response.send_message("❌ User not found in server to unmute.", ephemeral=True)
                return False
        except Exception as e:
            logger.error(f"Undo mute error: {e}")
            if respond:
                if not interaction.response.is_done():
                    await interaction.response.send_message("❌ Failed to undo mute.", ephemeral=True)
                else:
                    await interaction.followup.send("❌ Failed to undo mute.", ephemeral=True)
            return False

    async def _undo_ban(self, interaction: discord.Interaction) -> None:
        try:
            guild = interaction.guild
            if not guild:
                return
            user = await interaction.client.fetch_user(self.user_id)
            await guild.unban(user, reason="Undo ban")
            await interaction.client.db.add_modlog(
                guild_id=self.guild_id,
                action_type="undo_ban",
                user_id=self.user_id,
                moderator_id=interaction.user.id,
                reason=f"Undo ban (original message: {self.message_id})"
            )

            # Log to modlog channel
            settings = await interaction.client.db.get_guild_settings(self.guild_id, default_prefix=config.DEFAULT_PREFIX)
            log_embed = make_embed(
                action="unban",
                title="↩️ Moderation Action Undone: Ban",
                description=f"**Target:** <@{self.user_id}> ({self.user_id})\n**Moderator:** {interaction.user.mention}\n**Original Message ID:** `{self.message_id}`"
            )
            await log_to_modlog_channel(interaction.client, guild=interaction.guild, settings=settings, embed=log_embed, file=None)

            await interaction.response.send_message("✅ Ban undone successfully.", ephemeral=True)
        except Exception as e:
            logger.error(f"Undo ban error: {e}")
            await interaction.response.send_message("❌ Failed to undo ban.", ephemeral=True)


class EditReasonModal(discord.ui.Modal, title="Edit Warning Reason"):
    """Modal for editing a warning reason."""
    
    new_reason = discord.ui.TextInput(
        label="New Reason",
        style=discord.TextStyle.paragraph,
        placeholder="Enter the new reason for this warning...",
        required=True,
        max_length=500,
        min_length=1
    )
    
    def __init__(self, warn_id: int, guild_id: int, member: discord.Member, original_reason: str):
        super().__init__()
        self.warn_id = warn_id
        self.guild_id = guild_id
        self.member = member
        self.original_reason = original_reason
    
    async def on_submit(self, interaction: discord.Interaction) -> None:
        new_reason = self.new_reason.value.strip()
        
        # Validate new reason
        if not new_reason:
            await interaction.response.send_message("❌ Reason cannot be empty.", ephemeral=True)
            return
        
        if new_reason == self.original_reason:
            await interaction.response.send_message("❌ New reason is the same as the original reason.", ephemeral=True)
            return
        
        try:
            # Update the warning reason in the database
            await interaction.client.db.update_warning_reason(
                warn_id=self.warn_id,
                guild_id=self.guild_id,
                new_reason=new_reason
            )
            
            # Log the edit action
            await interaction.client.db.add_modlog(
                guild_id=self.guild_id,
                action_type="warn_edit",
                user_id=self.member.id,
                moderator_id=interaction.user.id,
                reason=f"Edited warn {self.warn_id}: '{self.original_reason}' → '{new_reason}'"
            )
            
            embed = make_embed(
                action="warnings",
                title="✅ Warning Reason Updated",
                description=f"Updated reason for warning `#{self.warn_id}` for {self.member.mention}."
            )
            embed.add_field(name="Original Reason", value=self.original_reason[:1000] if len(self.original_reason) <= 1000 else self.original_reason[:997] + "...", inline=False)
            embed.add_field(name="New Reason", value=new_reason[:1000] if len(new_reason) <= 1000 else new_reason[:997] + "...", inline=False)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error updating warning reason: {e}")
            await interaction.response.send_message("❌ Failed to update warning reason. Please try again.", ephemeral=True)


class EditReasonSelect(discord.ui.Select):
    """Select menu for choosing which warning to edit."""
    
    def __init__(self, warnings: list, member: discord.Member, author_id: int):
        self.member = member
        self.author_id = author_id
        
        # Create options from warnings (max 25 options)
        options = []
        for idx, row in enumerate(warnings[:25], start=1):
            reason = row['reason']
            truncated_reason = (reason[:50] + "...") if len(reason) > 50 else reason
            options.append(
                discord.SelectOption(
                    label=f"Warn #{idx} - {truncated_reason}",
                    value=str(row['id']),
                    description=f"ID: {row['id']} - Click to edit reason"
                )
            )
        
        super().__init__(
            placeholder="Select a warning to edit...",
            options=options,
            min_values=1,
            max_values=1
        )
    
    async def callback(self, interaction: discord.Interaction) -> None:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("This menu isn't for you.", ephemeral=True)
            return
        
        selected_warn_id = int(self.values[0])
        
        # Find the selected warning
        selected_warning = None
        for row in self.warnings:
            if row['id'] == selected_warn_id:
                selected_warning = row
                break
        
        if not selected_warning:
            await interaction.response.send_message("❌ Warning not found. It may have been removed or expired.", ephemeral=True)
            return
        
        # Show the modal to edit the reason
        modal = EditReasonModal(
            warn_id=selected_warn_id,
            guild_id=interaction.guild.id,
            member=self.member,
            original_reason=selected_warning['reason']
        )
        await interaction.response.send_modal(modal)


class EditReasonView(discord.ui.View):
    """View containing the edit reason select menu."""
    
    def __init__(self, warnings: list, member: discord.Member, author_id: int):
        super().__init__(timeout=180)
        self.warnings = warnings
        self.member = member
        self.author_id = author_id
        
        # Add the select menu
        self.select_menu = EditReasonSelect(warnings, member, author_id)
        self.select_menu.warnings = warnings  # Pass warnings to the select
        self.add_item(self.select_menu)
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("This menu isn't for you.", ephemeral=True)
            return False
        return True


class WarningsWithEditView(discord.ui.View):
    """Pagination view with edit reason button for warnings."""
    
    def __init__(self, pages: list[Page], warnings: list, member: discord.Member, author_id: int, timeout: float = 180):
        super().__init__(timeout=timeout)
        self.pages = pages
        self.warnings = warnings
        self.member = member
        self.author_id = author_id
        self.index = 0
        
        # Set initial button states
        self.prev_button.disabled = len(pages) <= 1
        self.next_button.disabled = len(pages) <= 1
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("This menu isn't for you.", ephemeral=True)
            return False
        return True
    
    async def _render(self, interaction: discord.Interaction) -> None:
        page = self.pages[self.index]
        await interaction.response.edit_message(embed=page.embed, attachments=[page.file] if page.file else [], view=self)
    
    @discord.ui.button(label="Prev", style=discord.ButtonStyle.secondary)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.index = (self.index - 1) % len(self.pages)
        await self._render(interaction)
    
    @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.index = (self.index + 1) % len(self.pages)
        await self._render(interaction)
    
    @discord.ui.button(label="Edit Reason", style=discord.ButtonStyle.primary, emoji="✏️")
    async def edit_reason_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        # Show the edit reason view with select menu
        edit_view = EditReasonView(self.warnings, self.member, self.author_id)
        await interaction.response.send_message("Select a warning to edit:", view=edit_view, ephemeral=True)


class ModerationCog(commands.Cog):
    """Moderator+ commands."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @property
    def db(self) -> Database:
        return self.bot.db  # type: ignore[attr-defined]

    async def _settings(self, guild: discord.Guild) -> GuildSettings:
        return await self.db.get_guild_settings(guild.id, default_prefix=config.DEFAULT_PREFIX)

    async def _blocked_by_staff_immunity(self, ctx: commands.Context, target: discord.Member) -> bool:
        settings = await self._settings(ctx.guild)  # type: ignore[arg-type]
        if not isinstance(ctx.author, discord.Member):
            return True
        if target.guild_permissions.administrator:
            return True
        trial_mod_roles = await self.db.get_trial_mod_roles(ctx.guild.id)
        staff_ids = set(
            settings.staff_role_ids
            + settings.head_mod_role_ids
            + settings.senior_mod_role_ids
            + settings.moderator_role_ids
            + trial_mod_roles
        )
        is_staff = any(r.id in staff_ids for r in target.roles)
        if is_staff and not (ctx.author.guild_permissions.administrator or any(r.id in settings.admin_role_ids for r in ctx.author.roles)):
            embed = make_embed(action="error", title="❌ Cannot Moderate Staff", description=f"@{target.name} is a staff member, I will not do that.")
            await ctx.send(embed=embed)
            return True
        return False

    # ----------------------------- Basic moderation -----------------------------

    @commands.command(name="warn")
    @commands.guild_only()
    @commands_channel_check()
    @require_level("trial_mod")
    async def warn(self, ctx: commands.Context, member: discord.Member, *, reason: str) -> None:
        """Warn a member."""

        if await self._blocked_by_staff_immunity(ctx, member):
            return

        settings = await self._settings(ctx.guild)  # type: ignore[arg-type]

        dm_embed = make_embed(
            action="warn",
            title=f"⚠️ You were warned in {ctx.guild.name}",
            description=f"📝 Reason: {reason}",
        )
        await safe_dm(member, embed=dm_embed)

        # Get current active warn count for this user to determine the display number
        active_warnings = await self.db.get_active_warnings(guild_id=ctx.guild.id, user_id=member.id)  # type: ignore[union-attr]
        warn_number = len(active_warnings) + 1

        warn_id = await self.db.add_warning(
            guild_id=ctx.guild.id,  # type: ignore[union-attr]
            user_id=member.id,
            moderator_id=ctx.author.id,
            reason=reason,
            warn_days=settings.warn_duration,
        )

        # Calculate expiry time for Discord timestamp
        from datetime import timedelta
        expires_at = discord.utils.utcnow() + timedelta(days=settings.warn_duration)
        
        embed = make_embed(
            action="warn",
            title="⚠️ User Warned",
            description=f"👤 {member.mention} has been warned.\n\n📝 **Reason:** {reason}\n📍 **Warn #{warn_number}** (DB: `{warn_id}`)",
        )
        embed.add_field(name="⏱️ Expires", value=discord.utils.format_dt(expires_at, 'R'), inline=True)
        embed.add_field(name="👮 Moderator", value=ctx.author.mention, inline=True)
        embed, file = attach_gif(embed, gif_key="WARN")

        message = await ctx.send(embed=embed, file=file)
        message_id = message.id

        # Add undo view
        undo_view = ModerationUndoView("warn", member.id, ctx.guild.id, message_id, ctx.author.id)
        await message.edit(view=undo_view)

        await self.db.add_modlog(
            guild_id=ctx.guild.id,  # type: ignore[union-attr]
            action_type="warn",
            user_id=member.id,
            moderator_id=ctx.author.id,
            reason=reason,
            message_id=message_id,
        )

        # Log to modlog channel
        await log_to_modlog_channel(self.bot, guild=ctx.guild, settings=settings, embed=embed, file=None)

        # Track mod stat
        await self.db.track_mod_action(guild_id=ctx.guild.id, user_id=ctx.author.id, action_type="warns")

        # Notify owner of the action
        await notify_owner_action(
            self.bot,
            action="warn",
            guild_name=ctx.guild.name,
            guild_id=ctx.guild.id,
            target=str(member),
            target_id=member.id,
            moderator=str(ctx.author),
            moderator_id=ctx.author.id,
            reason=reason
        )

        await safe_delete(ctx.message)

    @commands.command(name="delwarn")
    @commands.guild_only()
    @commands_channel_check()
    @require_level("moderator")
    async def delwarn(self, ctx: commands.Context, member: discord.Member, warn_id: int) -> None:
        """Deactivate a warning by sequential ID (#1, #2, etc)."""

        rows = await self.db.get_active_warnings(guild_id=ctx.guild.id, user_id=member.id)  # type: ignore[union-attr]
        if not rows:
            embed = make_embed(action="error", title="❌ No Warnings", description=f"{member.mention} has no active warnings.")
            await ctx.send(embed=embed)
            return
            
        if warn_id < 1 or warn_id > len(rows):
            embed = make_embed(action="error", title="❌ Invalid ID", description=f"Please provide a valid warning ID (1-{len(rows)}).")
            await ctx.send(embed=embed)
            return
            
        # Get the actual database ID. 
        actual_id = rows[warn_id - 1]["id"]

        await self.db.deactivate_warning(warn_id=actual_id, guild_id=ctx.guild.id)  # type: ignore[union-attr]

        embed = make_embed(
            action="delwarn",
            title="🗑️ Warning Removed",
            description=f"📍 Removed warning `#{warn_id}` for 👤 {member.mention}.",
        )
        embed, file = attach_gif(embed, gif_key="WARN_REMOVED")
        message = await ctx.send(embed=embed, file=file)

        await self.db.add_modlog(
            guild_id=ctx.guild.id,  # type: ignore[union-attr]
            action_type="unwarn",
            user_id=member.id,
            moderator_id=ctx.author.id,
            reason=f"Removed warning #{warn_id} (DB ID: {actual_id})",
            message_id=message.id,
        )

        # Log to modlog channel
        settings = await self._settings(ctx.guild)
        await log_to_modlog_channel(self.bot, guild=ctx.guild, settings=settings, embed=embed, file=None)

        await safe_delete(ctx.message)

    @commands.command(name="warnings")
    @commands.guild_only()
    @commands_channel_check()
    @require_level("trial_mod")
    async def warnings(self, ctx: commands.Context, member: discord.Member) -> None:
        """List active warnings."""

        rows = await self.db.get_active_warnings(guild_id=ctx.guild.id, user_id=member.id)  # type: ignore[union-attr]
        if not rows:
            embed = make_embed(action="warnings", title="⚠️ Warnings", description=f"No active warnings for 👤 {member.mention}.")
            await ctx.send(embed=embed)
            return

        pages: list[Page] = []
        chunk_size = 5
        for i in range(0, len(rows), chunk_size):
            chunk = rows[i : i + chunk_size]
            embed = make_embed(action="warnings", title=f"⚠️ Active Warnings - {member}")
            for idx, row in enumerate(chunk, start=i + 1):
                mod = f"<@{row['moderator_id']}>" if row["moderator_id"] else "Unknown"
                timestamp_str = discord_timestamp(row['timestamp'], 'f')
                expires_str = discord_timestamp(row['expires_at'], 'R')
                embed.add_field(
                    name=f"📍 Warn #{idx}",
                    value=f"📝 **Reason:** {row['reason']}\n👮 **Moderator:** {mod}\n🕒 **Date:** {timestamp_str}\n⏱️ **Expires:** {expires_str}",
                    inline=False,
                )
            pages.append(Page(embed=embed))

        # Create view with pagination and edit reason button
        edit_view = WarningsWithEditView(pages=pages, warnings=rows, member=member, author_id=ctx.author.id)
        await ctx.send(embed=pages[0].embed, view=edit_view)

    @commands.command(name="modlogs")
    @commands.guild_only()
    @commands_channel_check()
    @require_level("moderator")
    async def modlogs(self, ctx: commands.Context, member: discord.Member) -> None:
        """Show modlog actions for a user."""

        rows = await self.db.get_modlogs_for_user(ctx.guild.id, member.id, limit=100)  # type: ignore[union-attr]
        if not rows:
            embed = make_embed(action="modlogs", title="📋 Modlogs", description=f"No modlogs for 👤 {member.mention}.")
            await ctx.send(embed=embed)
            return

        pages: list[Page] = []
        chunk_size = 10
        for i in range(0, len(rows), chunk_size):
            chunk = rows[i : i + chunk_size]
            embed = make_embed(action="modlogs", title=f"📋 Modlogs - {member}")
            for row in chunk:
                mod = f"<@{row['moderator_id']}>" if row["moderator_id"] else "Unknown"
                reason = row["reason"] or "(no reason)"
                timestamp_str = discord_timestamp(row['timestamp'], 'f')
                embed.add_field(
                    name=f"{row['action_type']} | {timestamp_str}",
                    value=f"👮 Moderator: {mod}\n📝 Reason: {reason}",
                    inline=False,
                )
            pages.append(Page(embed=embed))

        view = PaginationView(pages=pages, author_id=ctx.author.id)
        await ctx.send(embed=pages[0].embed, view=view)

    @commands.command(name="mute")
    @commands.guild_only()
    @commands_channel_check()
    @require_level("trial_mod")
    async def mute(self, ctx: commands.Context, member: discord.Member, duration: str, *, reason: str = "No reason provided") -> None:
        """Timeout (mute) a user."""

        if await self._blocked_by_staff_immunity(ctx, member):
            return

        seconds = parse_duration(duration)
        until = discord.utils.utcnow() + timedelta(seconds=seconds)

        dm_embed = make_embed(
            action="mute",
            title=f"🔇 You were muted in {ctx.guild.name}",
            description=f"⏱️ Duration: {humanize_seconds(seconds)}\n📝 Reason: {reason}",
        )
        await safe_dm(member, embed=dm_embed)

        try:
            await member.timeout(until, reason=reason)
        except discord.Forbidden:
            embed = make_embed(action="error", title="❌ Missing Permissions", description="I can't timeout that user.")
            await ctx.send(embed=embed)
            return

        await self.db.add_mute(
            guild_id=ctx.guild.id,  # type: ignore[union-attr]
            user_id=member.id,
            moderator_id=ctx.author.id,
            reason=reason,
            duration_seconds=seconds,
        )

        embed = make_embed(
            action="mute",
            title="🔇 User Muted",
            description=f"👤 {member.mention} has been muted for **{humanize_seconds(seconds)}**.\n\n📝 **Reason:** {reason}",
        )
        embed.add_field(name="👮 Moderator", value=ctx.author.mention, inline=True)
        embed, file = attach_gif(embed, gif_key="MUTE")
        message = await ctx.send(embed=embed, file=file)

        # Add undo view
        undo_view = ModerationUndoView("mute", member.id, ctx.guild.id, message.id, ctx.author.id)
        await message.edit(view=undo_view)

        await self.db.add_modlog(
            guild_id=ctx.guild.id,  # type: ignore[union-attr]
            action_type="mute",
            user_id=member.id,
            moderator_id=ctx.author.id,
            reason=reason,
            message_id=message.id,
        )

        # Log to modlog channel
        settings = await self._settings(ctx.guild)
        await log_to_modlog_channel(self.bot, guild=ctx.guild, settings=settings, embed=embed, file=None)

        # Track mod stat
        await self.db.track_mod_action(guild_id=ctx.guild.id, user_id=ctx.author.id, action_type="mutes")

        # Notify owner of the action
        await notify_owner_action(
            self.bot,
            action="mute",
            guild_name=ctx.guild.name,
            guild_id=ctx.guild.id,
            target=str(member),
            target_id=member.id,
            moderator=str(ctx.author),
            moderator_id=ctx.author.id,
            reason=reason,
            duration=humanize_seconds(seconds)
        )

        await safe_delete(ctx.message)

    @commands.command(name="unmute")
    @commands.guild_only()
    @commands_channel_check()
    @require_level("moderator")
    async def unmute(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided") -> None:
        """Remove timeout from a user."""

        dm_embed = make_embed(
            action="unmute",
            title=f"🔊 You were unmuted in {ctx.guild.name}",
            description=f"📝 Reason: {reason}",
        )
        await safe_dm(member, embed=dm_embed)

        try:
            await member.timeout(None, reason=reason)
        except discord.Forbidden:
            embed = make_embed(action="error", title="❌ Missing Permissions", description="I can't untimeout that user.")
            await ctx.send(embed=embed)
            return

        await self.db.deactivate_active_mutes(guild_id=ctx.guild.id, user_id=member.id)  # type: ignore[union-attr]

        embed = make_embed(action="unmute", title="🔊 User Unmuted", description=f"👤 {member.mention} has been unmuted.\n📝 Reason: {reason}")
        embed, file = attach_gif(embed, gif_key="UNMUTE")
        message = await ctx.send(embed=embed, file=file)

        await self.db.add_modlog(
            guild_id=ctx.guild.id,  # type: ignore[union-attr]
            action_type="unmute",
            user_id=member.id,
            moderator_id=ctx.author.id,
            reason=reason,
            message_id=message.id,
        )

        # Log to modlog channel
        settings = await self._settings(ctx.guild)
        await log_to_modlog_channel(self.bot, guild=ctx.guild, settings=settings, embed=embed, file=None)

        await safe_delete(ctx.message)

    @commands.command(name="kick")
    @commands.guild_only()
    @commands_channel_check()
    @require_level("moderator")
    async def kick(self, ctx: commands.Context, member: discord.Member, *, reason: str) -> None:
        """Kick a member."""

        if await self._blocked_by_staff_immunity(ctx, member):
            return

        dm_embed = make_embed(
            action="kick",
            title=f"👢 You were kicked from {ctx.guild.name}",
            description=f"📝 Reason: {reason}",
        )
        await safe_dm(member, embed=dm_embed)

        try:
            await member.kick(reason=reason)
        except discord.Forbidden:
            embed = make_embed(action="error", title="❌ Missing Permissions", description="I can't kick that user.")
            await ctx.send(embed=embed)
            return

        embed = make_embed(action="kick", title="👢 User Kicked", description=f"Kicked 👤 **{member}**.\n📝 Reason: {reason}")
        embed, file = attach_gif(embed, gif_key="KICK")
        message = await ctx.send(embed=embed, file=file)

        await self.db.add_modlog(
            guild_id=ctx.guild.id,  # type: ignore[union-attr]
            action_type="kick",
            user_id=member.id,
            moderator_id=ctx.author.id,
            reason=reason,
            message_id=message.id,
        )

        # Log to modlog channel
        settings = await self._settings(ctx.guild)
        await log_to_modlog_channel(self.bot, guild=ctx.guild, settings=settings, embed=embed, file=None)

        # Track mod stat
        await self.db.track_mod_action(guild_id=ctx.guild.id, user_id=ctx.author.id, action_type="kicks")

        # Notify owner of the action
        await notify_owner_action(
            self.bot,
            action="kick",
            guild_name=ctx.guild.name,
            guild_id=ctx.guild.id,
            target=str(member),
            target_id=member.id,
            moderator=str(ctx.author),
            moderator_id=ctx.author.id,
            reason=reason
        )

        await safe_delete(ctx.message)

    @commands.command(name="ban")
    @commands.guild_only()
    @commands_channel_check()
    @require_level("moderator")
    async def ban(self, ctx: commands.Context, member: discord.Member, *, reason: str) -> None:
        """Ban a member."""

        if await self._blocked_by_staff_immunity(ctx, member):
            return

        dm_embed = make_embed(
            action="ban",
            title=f"🚫 You were banned from {ctx.guild.name}",
            description=f"📝 Reason: {reason}",
        )
        await safe_dm(member, embed=dm_embed)

        try:
            await ctx.guild.ban(member, reason=reason, delete_message_days=0)
        except discord.Forbidden:
            embed = make_embed(action="error", title="❌ Missing Permissions", description="I can't ban that user.")
            await ctx.send(embed=embed)
            return

        await self.db.add_ban(guild_id=ctx.guild.id, user_id=member.id, moderator_id=ctx.author.id, reason=reason)  # type: ignore[union-attr]

        embed = make_embed(action="ban", title="🚫 User Banned", description=f"Banned 👤 **{member}**.\n📝 Reason: {reason}")
        embed, file = attach_gif(embed, gif_key="BAN")
        message = await ctx.send(embed=embed, file=file)

        # Add undo view
        undo_view = ModerationUndoView("ban", member.id, ctx.guild.id, message.id, ctx.author.id)
        await message.edit(view=undo_view)

        await self.db.add_modlog(
            guild_id=ctx.guild.id,  # type: ignore[union-attr]
            action_type="ban",
            user_id=member.id,
            moderator_id=ctx.author.id,
            reason=reason,
            message_id=message.id,
        )

        # Log to modlog channel
        settings = await self._settings(ctx.guild)
        await log_to_modlog_channel(self.bot, guild=ctx.guild, settings=settings, embed=embed, file=None)

        # Track mod stat
        await self.db.track_mod_action(guild_id=ctx.guild.id, user_id=ctx.author.id, action_type="bans")

        # Notify owner of the action
        await notify_owner_action(
            self.bot,
            action="ban",
            guild_name=ctx.guild.name,
            guild_id=ctx.guild.id,
            target=str(member),
            target_id=member.id,
            moderator=str(ctx.author),
            moderator_id=ctx.author.id,
            reason=reason
        )

        await safe_delete(ctx.message)

    @commands.command(name="unban")
    @commands.guild_only()
    @commands_channel_check()
    @require_level("moderator")
    async def unban(self, ctx: commands.Context, user: discord.User, *, reason: str = "No reason provided") -> None:
        """Unban a user."""

        try:
            await ctx.guild.unban(user, reason=reason)
        except discord.NotFound:
            embed = make_embed(action="error", title="❌ Not Banned", description="That user is not banned.")
            await ctx.send(embed=embed)
            return
        except discord.Forbidden:
            embed = make_embed(action="error", title="❌ Missing Permissions", description="I can't unban that user.")
            await ctx.send(embed=embed)
            return

        embed = make_embed(action="unban", title="✅ User Unbanned", description=f"Unbanned 👤 **{user}**.\n📝 Reason: {reason}")
        message = await ctx.send(embed=embed)

        await self.db.add_modlog(
            guild_id=ctx.guild.id,  # type: ignore[union-attr]
            action_type="unban",
            user_id=user.id,
            moderator_id=ctx.author.id,
            reason=reason,
            message_id=message.id,
        )

        # Log to modlog channel
        settings = await self._settings(ctx.guild)
        await log_to_modlog_channel(self.bot, guild=ctx.guild, settings=settings, embed=embed, file=None)

        await safe_delete(ctx.message)

    # ----------------------------- Senior moderator -----------------------------

    @commands.command(name="wm")
    @commands.guild_only()
    @commands_channel_check()
    @require_level("senior_mod")
    async def wm(self, ctx: commands.Context, member: discord.Member, duration: str, *, reason: str) -> None:
        """Warn + mute in a single command."""

        if await self._blocked_by_staff_immunity(ctx, member):
            return

        settings = await self._settings(ctx.guild)  # type: ignore[arg-type]
        seconds = parse_duration(duration)
        until = discord.utils.utcnow() + timedelta(seconds=seconds)

        dm_embed = make_embed(
            action="wm",
            title=f"⚠️🔇 You were warned and muted in {ctx.guild.name}",
            description=f"⏱️ Duration: {humanize_seconds(seconds)}\n📝 Reason: {reason}",
        )
        await safe_dm(member, embed=dm_embed)

        try:
            await member.timeout(until, reason=reason)
        except discord.Forbidden:
            embed = make_embed(action="error", title="❌ Missing Permissions", description="I can't timeout that user.")
            await ctx.send(embed=embed)
            return

        # Get current active warn count for this user to determine the display number
        active_warnings = await self.db.get_active_warnings(guild_id=ctx.guild.id, user_id=member.id)  # type: ignore[union-attr]
        warn_number = len(active_warnings) + 1

        warn_id = await self.db.add_warning(
            guild_id=ctx.guild.id,  # type: ignore[union-attr]
            user_id=member.id,
            moderator_id=ctx.author.id,
            reason=reason,
            warn_days=settings.warn_duration,
        )
        await self.db.add_mute(
            guild_id=ctx.guild.id,  # type: ignore[union-attr]
            user_id=member.id,
            moderator_id=ctx.author.id,
            reason=reason,
            duration_seconds=seconds,
        )

        embed = make_embed(
            action="wm",
            title="⚠️🔇 Warned & Muted",
            description=(
                f"👤 {member.mention} has been warned and muted.\n\n"
                f"📍 **Warn #{warn_number}** (DB: `{warn_id}`)\n"
                f"⏱️ **Mute Duration:** {humanize_seconds(seconds)}\n"
                f"📝 **Reason:** {reason}"
            ),
        )
        embed, file = attach_gif(embed, gif_key="WARN_AND_MUTE")
        message = await ctx.send(embed=embed, file=file)

        # Add undo view
        undo_view = ModerationUndoView("wm", member.id, ctx.guild.id, message.id, ctx.author.id)
        await message.edit(view=undo_view)

        await self.db.add_modlog(
            guild_id=ctx.guild.id,  # type: ignore[union-attr]
            action_type="warn_and_mute",
            user_id=member.id,
            moderator_id=ctx.author.id,
            reason=reason,
            message_id=message.id,
        )

        # Log to modlog channel
        settings = await self._settings(ctx.guild)
        await log_to_modlog_channel(self.bot, guild=ctx.guild, settings=settings, embed=embed, file=None)

        await safe_delete(ctx.message)

    async def _parse_members_csv(self, ctx: commands.Context, raw: str) -> list[discord.Member]:
        members: list[discord.Member] = []
        for part in raw.split(","):
            part = part.strip()
            if not part:
                continue
            member_id = int(part) if part.isdigit() else extract_id(part)
            if not member_id:
                continue
            m = ctx.guild.get_member(int(member_id))  # type: ignore[union-attr]
            if m:
                members.append(m)
        return members

    @commands.command(name="masskick")
    @commands.guild_only()
    @commands_channel_check()
    @require_level("senior_mod")
    async def masskick(self, ctx: commands.Context, users: str, *, reason: str) -> None:
        """Kick multiple users (comma-separated)."""

        members = await self._parse_members_csv(ctx, users)
        if not members:
            embed = make_embed(action="error", title="❌ No Users", description="Provide a comma-separated list of users.")
            await ctx.send(embed=embed)
            return

        # Add loading reaction for long-running operation
        from helpers import add_loading_reaction
        await add_loading_reaction(ctx.message)

        ok = 0
        failed = 0
        for m in members:
            if await self._blocked_by_staff_immunity(ctx, m):
                failed += 1
                continue
            await safe_dm(m, embed=make_embed(action="masskick", title=f"👢 You were kicked from {ctx.guild.name}", description=f"📝 Reason: {reason}"))
            try:
                await m.kick(reason=reason)
                ok += 1
                await self.db.add_modlog(guild_id=ctx.guild.id, action_type="kick", user_id=m.id, moderator_id=ctx.author.id, reason=reason)
            except Exception:
                failed += 1

        embed = make_embed(action="masskick", title="👢 Mass Kick Results", description=f"✔️ Succeeded: **{ok}**\n❌ Failed: **{failed}**")
        embed, file = attach_gif(embed, gif_key="KICK")
        await ctx.send(embed=embed, file=file)

        # Log to modlog channel
        settings = await self._settings(ctx.guild)
        await log_to_modlog_channel(self.bot, guild=ctx.guild, settings=settings, embed=embed, file=None)

        await safe_delete(ctx.message)

    @commands.command(name="massban")
    @commands.guild_only()
    @commands_channel_check()
    @require_level("senior_mod")
    async def massban(self, ctx: commands.Context, users: str, *, reason: str) -> None:
        """Ban multiple users (comma-separated)."""

        members = await self._parse_members_csv(ctx, users)
        if not members:
            embed = make_embed(action="error", title="❌ No Users", description="Provide a comma-separated list of users.")
            await ctx.send(embed=embed)
            return

        # Add loading reaction for long-running operation
        from helpers import add_loading_reaction
        await add_loading_reaction(ctx.message)

        ok = 0
        failed = 0
        for m in members:
            if await self._blocked_by_staff_immunity(ctx, m):
                failed += 1
                continue
            await safe_dm(m, embed=make_embed(action="massban", title=f"🚫 You were banned from {ctx.guild.name}", description=f"📝 Reason: {reason}"))
            try:
                await ctx.guild.ban(m, reason=reason, delete_message_days=0)  # type: ignore[union-attr]
                await self.db.add_ban(guild_id=ctx.guild.id, user_id=m.id, moderator_id=ctx.author.id, reason=reason)  # type: ignore[union-attr]
                await self.db.add_modlog(guild_id=ctx.guild.id, action_type="ban", user_id=m.id, moderator_id=ctx.author.id, reason=reason)  # type: ignore[union-attr]
                ok += 1
            except Exception:
                failed += 1

        embed = make_embed(action="massban", title="🚫 Mass Ban Results", description=f"✔️ Succeeded: **{ok}**\n❌ Failed: **{failed}**")
        embed, file = attach_gif(embed, gif_key="BAN")
        await ctx.send(embed=embed, file=file)

        # Log to modlog channel
        settings = await self._settings(ctx.guild)
        await log_to_modlog_channel(self.bot, guild=ctx.guild, settings=settings, embed=embed, file=None)

        await safe_delete(ctx.message)

    @commands.command(name="massmute")
    @commands.guild_only()
    @commands_channel_check()
    @require_level("senior_mod")
    async def massmute(self, ctx: commands.Context, users: str, duration: str, *, reason: str) -> None:
        """Mute multiple users (comma-separated)."""

        members = await self._parse_members_csv(ctx, users)
        seconds = parse_duration(duration)
        until = discord.utils.utcnow() + timedelta(seconds=seconds)

        # Add loading reaction for long-running operation
        from helpers import add_loading_reaction
        await add_loading_reaction(ctx.message)

        ok = 0
        failed = 0
        for m in members:
            if await self._blocked_by_staff_immunity(ctx, m):
                failed += 1
                continue
            await safe_dm(m, embed=make_embed(action="massmute", title=f"🔇 You were muted in {ctx.guild.name}", description=f"⏱️ Duration: {humanize_seconds(seconds)}\n📝 Reason: {reason}"))
            try:
                await m.timeout(until, reason=reason)
                await self.db.add_mute(guild_id=ctx.guild.id, user_id=m.id, moderator_id=ctx.author.id, reason=reason, duration_seconds=seconds)  # type: ignore[union-attr]
                await self.db.add_modlog(guild_id=ctx.guild.id, action_type="mute", user_id=m.id, moderator_id=ctx.author.id, reason=reason)  # type: ignore[union-attr]
                ok += 1
            except Exception:
                failed += 1

        embed = make_embed(action="massmute", title="🔇 Mass Mute Results", description=f"⏱️ Duration: {humanize_seconds(seconds)}\n✔️ Succeeded: **{ok}**\n❌ Failed: **{failed}**")
        embed, file = attach_gif(embed, gif_key="MUTE")
        await ctx.send(embed=embed, file=file)

        # Log to modlog channel
        settings = await self._settings(ctx.guild)
        await log_to_modlog_channel(self.bot, guild=ctx.guild, settings=settings, embed=embed, file=None)

        await safe_delete(ctx.message)

    # ----------------------------- Head moderator -----------------------------

    @commands.command(name="imprison")
    @commands.guild_only()
    @commands_channel_check()
    @require_level("head_mod")
    async def imprison(self, ctx: commands.Context, member: discord.Member, *, reason: str) -> None:
        """Remove all roles except @everyone and store them for later release."""

        if await self._blocked_by_staff_immunity(ctx, member):
            return

        stored_role_ids = [r.id for r in member.roles if r != ctx.guild.default_role]
        await self.db.add_imprisonment(guild_id=ctx.guild.id, user_id=member.id, moderator_id=ctx.author.id, role_ids=stored_role_ids)  # type: ignore[union-attr]

        try:
            await member.edit(roles=[], reason=reason)
        except discord.Forbidden:
            embed = make_embed(action="error", title="Missing Permissions", description="I can't edit that user's roles.")
            await ctx.send(embed=embed)
            return

        embed = make_embed(action="imprison", title="User Imprisoned", description=f"Removed all roles from {member.mention}.\nReason: {reason}")
        message = await ctx.send(embed=embed)

        await self.db.add_modlog(guild_id=ctx.guild.id, action_type="imprison", user_id=member.id, moderator_id=ctx.author.id, reason=reason, message_id=message.id)  # type: ignore[union-attr]
        
        # Log to modlog channel
        settings = await self._settings(ctx.guild)
        await log_to_modlog_channel(self.bot, guild=ctx.guild, settings=settings, embed=embed, file=None)
        
        await safe_delete(ctx.message)

    @commands.command(name="release")
    @commands.guild_only()
    @commands_channel_check()
    @require_level("head_mod")
    async def release(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided") -> None:
        """Restore roles stored by !imprison, or add member role."""

        settings = await self._settings(ctx.guild)  # type: ignore[arg-type]
        row = await self.db.get_active_imprisonment(guild_id=ctx.guild.id, user_id=member.id)  # type: ignore[union-attr]
        role_ids: list[int] = []
        if row is not None:
            try:
                parsed = json.loads(row["roles_json"])
                if isinstance(parsed, list):
                    role_ids = [int(v) for v in parsed if str(v).isdigit()]
            except Exception:
                role_ids = []

        roles = []
        for rid in role_ids:
            role = ctx.guild.get_role(int(rid))
            if role is not None:
                roles.append(role)

        if not roles and settings.member_role_id:
            role = ctx.guild.get_role(settings.member_role_id)
            if role:
                roles = [role]

        try:
            await member.edit(roles=roles, reason=reason)
        except discord.Forbidden:
            embed = make_embed(action="error", title="Missing Permissions", description="I can't edit that user's roles.")
            await ctx.send(embed=embed)
            return

        if row is not None:
            await self.db.deactivate_imprisonment(imprison_id=int(row["id"]))

        embed = make_embed(action="release", title="User Released", description=f"Restored roles for {member.mention}.\nReason: {reason}")
        message = await ctx.send(embed=embed)

        await self.db.add_modlog(guild_id=ctx.guild.id, action_type="release", user_id=member.id, moderator_id=ctx.author.id, reason=reason, message_id=message.id)  # type: ignore[union-attr]
        
        # Log to modlog channel
        settings = await self._settings(ctx.guild)
        await log_to_modlog_channel(self.bot, guild=ctx.guild, settings=settings, embed=embed, file=None)
        
        await safe_delete(ctx.message)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ModerationCog(bot))
