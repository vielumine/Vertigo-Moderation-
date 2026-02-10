"""AI Moderation Commands - Owner Only"""

from __future__ import annotations

import logging
import random
import re
from datetime import datetime
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

import config
from database import AITarget, BotBlacklist, Database, TimeoutSettings
from helpers import (
    add_loading_reaction,
    discord_timestamp,
    extract_id,
    log_to_modlog_channel,
    make_embed,
    require_admin,
    require_owner,
    safe_dm,
    utcnow,
)

if TYPE_CHECKING:
    from main import VertigoBot

logger = logging.getLogger(__name__)


class AIModerationCog(commands.Cog):
    """AI Moderation Commands - Owner Only"""
    
    def __init__(self, bot: VertigoBot) -> None:
        self.bot = bot
    
    @property
    def db(self) -> Database:
        return self.bot.db
    
    # ============================
    # AI MODERATION COMMANDS
    # ============================
    
    @commands.command(name="aiwarn")
    @require_owner()
    async def aiwarn(self, ctx: commands.Context, member: discord.Member, *, reason: str) -> None:
        """AI warns a user instead of a moderator."""
        await add_loading_reaction(ctx.message)
        
        try:
            # Add warning
            await self.db.add_warning(
                guild_id=ctx.guild.id,
                user_id=member.id,
                moderator_id=ctx.bot.user.id,  # Bot as moderator
                reason=reason,
                warn_days=14
            )
            
            # Create embed
            embed = make_embed(
                action="warn",
                title="⚠️ User Warned",
                description=f"**User:** {member.mention}\n**Reason:** {reason}\n**Moderator:** Vertigo AI Moderation"
            )
            
            # Add to modlogs
            await self.db.add_modlog(
                guild_id=ctx.guild.id,
                action_type="ai_warn",
                user_id=member.id,
                moderator_id=ctx.bot.user.id,
                reason=reason,
                message_id=ctx.message.id
            )
            
            # Log to modlog channel
            settings = await self.bot.db.get_guild_settings(ctx.guild.id, default_prefix=config.DEFAULT_PREFIX)
            await log_to_modlog_channel(self.bot, guild=ctx.guild, settings=settings, embed=embed, file=None)
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error("AI warn error: %s", e)
            embed = make_embed(
                action="error",
                title="Error",
                description="Failed to warn user."
            )
            await ctx.send(embed=embed)
    
    @commands.command(name="aimute")
    @require_owner()
    async def aimute(self, ctx: commands.Context, member: discord.Member, duration: str, *, reason: str) -> None:
        """AI mutes a user instead of a moderator."""
        await add_loading_reaction(ctx.message)
        
        try:
            from helpers import parse_duration
            duration_seconds = parse_duration(duration)
            
            # Add mute
            await self.db.add_mute(
                guild_id=ctx.guild.id,
                user_id=member.id,
                moderator_id=ctx.bot.user.id,  # Bot as moderator
                reason=reason,
                duration_seconds=duration_seconds
            )
            
            # Create embed
            embed = make_embed(
                action="mute",
                title="🔇 User Muted",
                description=f"**User:** {member.mention}\n**Duration:** {duration}\n**Reason:** {reason}\n**Moderator:** Vertigo AI Moderation"
            )
            
            # Add to modlogs
            await self.db.add_modlog(
                guild_id=ctx.guild.id,
                action_type="ai_mute",
                user_id=member.id,
                moderator_id=ctx.bot.user.id,
                reason=reason,
                message_id=ctx.message.id
            )
            
            # Log to modlog channel
            settings = await self.bot.db.get_guild_settings(ctx.guild.id, default_prefix=config.DEFAULT_PREFIX)
            await log_to_modlog_channel(self.bot, guild=ctx.guild, settings=settings, embed=embed, file=None)
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error("AI mute error: %s", e)
            embed = make_embed(
                action="error",
                title="Error",
                description="Failed to mute user."
            )
            await ctx.send(embed=embed)
    
    @commands.command(name="aikick")
    @require_owner()
    async def aikick(self, ctx: commands.Context, member: discord.Member, *, reason: str) -> None:
        """AI kicks a user instead of a moderator."""
        await add_loading_reaction(ctx.message)
        
        try:
            await member.kick(reason=f"AI Kick: {reason}")
            
            # Create embed
            embed = make_embed(
                action="kick",
                title="👢 User Kicked",
                description=f"**User:** {member.mention}\n**Reason:** {reason}\n**Moderator:** Vertigo AI Moderation"
            )
            
            # Add to modlogs
            await self.db.add_modlog(
                guild_id=ctx.guild.id,
                action_type="ai_kick",
                user_id=member.id,
                moderator_id=ctx.bot.user.id,
                reason=reason,
                message_id=ctx.message.id
            )
            
            # Log to modlog channel
            settings = await self.bot.db.get_guild_settings(ctx.guild.id, default_prefix=config.DEFAULT_PREFIX)
            await log_to_modlog_channel(self.bot, guild=ctx.guild, settings=settings, embed=embed, file=None)
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error("AI kick error: %s", e)
            embed = make_embed(
                action="error",
                title="Error",
                description="Failed to kick user."
            )
            await ctx.send(embed=embed)
    
    @commands.command(name="aiban")
    @require_owner()
    async def aiban(self, ctx: commands.Context, member: discord.Member, *, reason: str) -> None:
        """AI bans a user instead of a moderator."""
        await add_loading_reaction(ctx.message)
        
        try:
            await member.ban(reason=f"AI Ban: {reason}")
            
            # Add to bans table
            await self.db.add_ban(
                guild_id=ctx.guild.id,
                user_id=member.id,
                moderator_id=ctx.bot.user.id,  # Bot as moderator
                reason=reason
            )
            
            # Create embed
            embed = make_embed(
                action="ban",
                title="🔨 User Banned",
                description=f"**User:** {member.mention}\n**Reason:** {reason}\n**Moderator:** Vertigo AI Moderation"
            )
            
            # Add to modlogs
            await self.db.add_modlog(
                guild_id=ctx.guild.id,
                action_type="ai_ban",
                user_id=member.id,
                moderator_id=ctx.bot.user.id,
                reason=reason,
                message_id=ctx.message.id
            )
            
            # Log to modlog channel
            settings = await self.bot.db.get_guild_settings(ctx.guild.id, default_prefix=config.DEFAULT_PREFIX)
            await log_to_modlog_channel(self.bot, guild=ctx.guild, settings=settings, embed=embed, file=None)
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error("AI ban error: %s", e)
            embed = make_embed(
                action="error",
                title="Error",
                description="Failed to ban user."
            )
            await ctx.send(embed=embed)
    
    @commands.command(name="aiflag")
    @require_owner()
    async def aiflag(self, ctx: commands.Context, member: discord.Member, *, reason: str) -> None:
        """AI flags a staff member instead of an admin."""
        await add_loading_reaction(ctx.message)
        
        try:
            # Add staff flag
            await self.db.add_staff_flag(
                guild_id=ctx.guild.id,
                staff_user_id=member.id,
                admin_id=ctx.bot.user.id,  # Bot as admin
                reason=reason,
                duration_days=30
            )
            
            # Get flag count
            active_flags = await self.db.get_active_staff_flags(guild_id=ctx.guild.id, staff_user_id=member.id)
            flag_count = len(active_flags)
            
            # Create embed
            embed = make_embed(
                action="flag",
                title="🚩 Staff Flagged",
                description=f"**Staff:** {member.mention}\n**Reason:** {reason}\n**Admin:** Vertigo AI Moderation\n**Flags:** {flag_count}/5"
            )
            
            # Add to modlogs
            await self.db.add_modlog(
                guild_id=ctx.guild.id,
                action_type="ai_flag",
                user_id=member.id,
                moderator_id=ctx.bot.user.id,
                reason=reason,
                message_id=ctx.message.id
            )
            
            # Log to modlog channel
            settings = await self.bot.db.get_guild_settings(ctx.guild.id, default_prefix=config.DEFAULT_PREFIX)
            await log_to_modlog_channel(self.bot, guild=ctx.guild, settings=settings, embed=embed, file=None)
            
            await ctx.send(embed=embed)
            
            # DM owner for approval if this would trigger termination
            if flag_count >= config.MAX_STAFF_FLAGS:
                owner = await self.bot.fetch_user(config.OWNER_ID)
                if owner:
                    approval_embed = make_embed(
                        action="flag",
                        title="🚩 Flag Approval Required",
                        description=f"**Staff:** {member.mention} ({member.id})\n**Reason:** {reason}\n**Flag Count:** {flag_count}/5\n\nThis will trigger automatic termination. Do you approve?"
                    )
                    approval_embed.add_field(
                        name="Actions",
                        value="React with ✅ to approve termination\nReact with ❌ to cancel",
                        inline=False
                    )
                    
                    approval_msg = await owner.send(embed=approval_embed)
                    await approval_msg.add_reaction("✅")
                    await approval_msg.add_reaction("❌")
            
        except Exception as e:
            logger.error("AI flag error: %s", e)
            embed = make_embed(
                action="error",
                title="Error",
                description="Failed to flag staff member."
            )
            await ctx.send(embed=embed)
    
    # ============================
    # AI TARGETING COMMANDS
    # ============================
    
    @commands.command(name="aitarget")
    @require_owner()
    async def aitarget(self, ctx: commands.Context, target: discord.User, *, notes: str | None = None) -> None:
        """Target a user for AI trolling/roasting."""
        try:
            await self.db.add_ai_target(
                user_id=target.id,
                guild_id=ctx.guild.id,
                target_by=ctx.author.id,
                notes=notes
            )
            
            embed = make_embed(
                action="ai",
                title="🎯 AI Target Set",
                description=f"**Target:** {target.mention}\n**Set by:** {ctx.author.mention}\n**Notes:** {notes or 'None'}"
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error("AI target error: %s", e)
            embed = make_embed(
                action="error",
                title="Error",
                description="Failed to set AI target."
            )
            await ctx.send(embed=embed)
    
    @commands.command(name="airemove")
    @require_owner()
    async def airemove(self, ctx: commands.Context, target: discord.User) -> None:
        """Remove AI targeting from a user."""
        try:
            await self.db.remove_ai_target(user_id=target.id, guild_id=ctx.guild.id)
            
            embed = make_embed(
                action="ai",
                title="🎯 AI Target Removed",
                description=f"**Target:** {target.mention}\n**Removed by:** {ctx.author.mention}"
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error("AI remove error: %s", e)
            embed = make_embed(
                action="error",
                title="Error",
                description="Failed to remove AI target."
            )
            await ctx.send(embed=embed)
    
    # ============================
    # BOT BLACKLIST COMMANDS
    # ============================
    
    @commands.command(name="blacklist")
    @require_owner()
    async def blacklist(self, ctx: commands.Context, target: discord.User, *, reason: str) -> None:
        """Blacklist a user from using the bot."""
        try:
            await self.db.add_to_blacklist(
                user_id=target.id,
                blacklisted_by=ctx.author.id,
                reason=reason
            )
            
            embed = make_embed(
                action="ai",
                title="🚫 User Blacklisted",
                description=f"**User:** {target.mention}\n**Reason:** {reason}\n**Blacklisted by:** {ctx.author.mention}"
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error("Blacklist error: %s", e)
            embed = make_embed(
                action="error",
                title="Error",
                description="Failed to blacklist user."
            )
            await ctx.send(embed=embed)
    
    @commands.command(name="unblacklist")
    @require_owner()
    async def unblacklist(self, ctx: commands.Context, target: discord.User) -> None:
        """Remove a user from bot blacklist."""
        try:
            await self.db.remove_from_blacklist(user_id=target.id)
            
            embed = make_embed(
                action="ai",
                title="✅ User Unblacklisted",
                description=f"**User:** {target.mention}\n**Unblacklisted by:** {ctx.author.mention}"
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error("Unblacklist error: %s", e)
            embed = make_embed(
                action="error",
                title="Error",
                description="Failed to unblacklist user."
            )
            await ctx.send(embed=embed)
    
    @commands.command(name="seeblacklist")
    @require_owner()
    async def seeblacklist(self, ctx: commands.Context) -> None:
        """View all blacklisted users."""
        try:
            blacklist_entries = await self.db.get_all_blacklisted()
            
            if not blacklist_entries:
                embed = make_embed(
                    action="ai",
                    title="📋 Blacklist",
                    description="No users are currently blacklisted."
                )
                await ctx.send(embed=embed)
                return
            
            # Create embed
            embed = make_embed(
                action="ai",
                title="📋 Bot Blacklist",
                description=f"Total blacklisted users: {len(blacklist_entries)}"
            )
            
            # Add entries (limit to 10 per embed)
            for i, entry in enumerate(blacklist_entries[:10]):
                user = self.bot.get_user(entry.user_id)
                username = user.mention if user else f"Unknown User ({entry.user_id})"
                timestamp_str = discord_timestamp(entry.timestamp, "f")
                
                embed.add_field(
                    name=f"Entry {i+1}",
                    value=f"**User:** {username}\n**Reason:** {entry.reason}\n**Date:** {timestamp_str}",
                    inline=False
                )
            
            if len(blacklist_entries) > 10:
                embed.add_field(
                    name="Note",
                    value=f"And {len(blacklist_entries) - 10} more users...",
                    inline=False
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error("See blacklist error: %s", e)
            embed = make_embed(
                action="error",
                title="Error",
                description="Failed to fetch blacklist."
            )
            await ctx.send(embed=embed)
    
    # ============================
    # TIMEOUT PANEL SYSTEM
    # ============================
    
    @commands.command(name="timeoutpanel")
    @require_admin()
    async def timeoutpanel(self, ctx: commands.Context) -> None:
        """Open the timeout panel for managing prohibited terms."""
        try:
            settings = await self.db.get_timeout_settings(ctx.guild.id)
            alert_channel = ctx.guild.get_channel(settings.alert_channel_id) if settings.alert_channel_id else None
            alert_role = ctx.guild.get_role(settings.alert_role_id) if settings.alert_role_id else None
            
            embed = make_embed(
                action="ai",
                title="⏰ Timeout Panel",
                description="Manage prohibited terms and timeout settings"
            )
            
            embed.add_field(
                name="Current Settings",
                value=(
                    f"**Enabled:** {settings.enabled}\n"
                    f"**Phrases:** {len(settings.phrases.split(',')) if settings.phrases else 0}\n"
                    f"**Timeout Duration:** {settings.timeout_duration // 3600}h\n"
                    f"**Alert Channel:** {alert_channel.mention if alert_channel else 'Not set'}\n"
                    f"**Alert Role:** {alert_role.mention if alert_role else 'Not set'}"
                ),
                inline=False
            )
            
            # Create buttons for the panel
            view = TimeoutPanelView(settings, self.bot, ctx.guild.id)
            view.original_author_id = ctx.author.id  # Add this for permission checking
            
            message = await ctx.send(embed=embed, view=view)
            view.message = message
            
        except Exception as e:
            logger.error("Timeout panel error: %s", e)
            embed = make_embed(
                action="error",
                title="Error",
                description="Failed to open timeout panel."
            )
            await ctx.send(embed=embed)


class TimeoutPanelView(discord.ui.View):
    """Timeout panel view with management buttons."""
    
    def __init__(self, settings: TimeoutSettings, bot, guild_id: int, timeout: float = 180):
        super().__init__(timeout=timeout)
        self.settings = settings
        self.bot = bot
        self.guild_id = guild_id
        self.message: discord.Message | None = None
        self.current_page = 0
        self.original_author_id: int | None = None
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Only the person who summoned the panel can interact with it
        if self.original_author_id and interaction.user.id != self.original_author_id:
            await interaction.response.send_message("Only the person who opened this panel can use these controls.", ephemeral=True)
            return False
        return True
    
    @discord.ui.button(label="Add/Remove Phrase", style=discord.ButtonStyle.primary, emoji="📝")
    async def phrase_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        modal = PhraseModal(self.settings)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Add Alert Role", style=discord.ButtonStyle.primary, emoji="🔔")
    async def alert_role_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        modal = AlertRoleModal(self.settings)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Add Alert Channel", style=discord.ButtonStyle.primary, emoji="📢")
    async def alert_channel_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        modal = AlertChannelModal(self.settings)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Set Timeout Duration", style=discord.ButtonStyle.primary, emoji="⏱️")
    async def timeout_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        modal = TimeoutDurationModal(self.settings)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="See Phrases", style=discord.ButtonStyle.secondary, emoji="📋")
    async def see_phrases_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.show_phrases(interaction)
    
    @discord.ui.button(label="Toggle Enable", style=discord.ButtonStyle.success, emoji="✅")
    async def toggle_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        new_enabled = not self.settings.enabled
        await self.bot.db.update_timeout_settings(self.guild_id, enabled=new_enabled)
        self.settings.enabled = new_enabled
        
        embed = await self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="Settings", style=discord.ButtonStyle.secondary, emoji="⚙️")
    async def settings_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        embed = await self.create_embed()
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def show_phrases(self, interaction: discord.Interaction) -> None:
        """Show the phrases in a paginated view."""
        phrases = self.settings.phrases.split(',') if self.settings.phrases else []
        
        if not phrases:
            embed = make_embed(
                action="ai",
                title="📋 Prohibited Phrases",
                description="No phrases configured yet."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Create paginated view
        view = PhrasesView(phrases, self.settings, self.bot, self.guild_id)
        view.original_author_id = self.original_author_id  # Set the original author ID
        await interaction.response.send_message(view=view, ephemeral=True)
    
    async def create_embed(self) -> discord.Embed:
        """Create the main panel embed."""
        guild = self.bot.get_guild(self.guild_id)
        alert_channel = guild.get_channel(self.settings.alert_channel_id) if guild and self.settings.alert_channel_id else None
        alert_role = guild.get_role(self.settings.alert_role_id) if guild and self.settings.alert_role_id else None

        embed = make_embed(
            action="ai",
            title="⏰ Timeout Panel",
            description="Manage prohibited terms and timeout settings"
        )
        
        embed.add_field(
            name="Current Settings",
            value=(
                f"**Enabled:** {self.settings.enabled}\n"
                f"**Phrases:** {len(self.settings.phrases.split(',')) if self.settings.phrases else 0}\n"
                f"**Timeout Duration:** {self.settings.timeout_duration // 3600}h\n"
                f"**Alert Channel:** {alert_channel.mention if alert_channel else 'Not set'}\n"
                f"**Alert Role:** {alert_role.mention if alert_role else 'Not set'}"
            ),
            inline=False
        )
        
        return embed


class PhraseModal(discord.ui.Modal):
    """Modal for adding/removing phrases."""
    
    def __init__(self, settings: TimeoutSettings):
        self.settings = settings
        super().__init__(title="Add/Remove Phrase", timeout=300)
        
        self.add_item(discord.ui.TextInput(
            label="Phrase (comma-separated)",
            placeholder="word1, word2, phrase three",
            style=discord.TextStyle.paragraph,
            required=True
        ))
    
    async def callback(self, interaction: discord.Interaction) -> None:
        try:
            phrase_input = self.children[0].value
            phrases = [p.strip() for p in phrase_input.split(',') if p.strip()]
            
            # Add new phrases to existing ones
            existing_phrases = self.settings.phrases.split(',') if self.settings.phrases else []
            all_phrases = list(set(existing_phrases + phrases))
            
            new_phrases_str = ','.join(all_phrases)
            await interaction.client.db.update_timeout_settings(
                self.settings.guild_id,
                phrases=new_phrases_str
            )
            
            # Update local settings object
            self.settings.phrases = new_phrases_str
            
            embed = make_embed(
                action="ai",
                title="✅ Phrases Updated",
                description=f"Added {len(phrases)} new phrases. Total: {len(all_phrases)}"
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Error updating phrases: {e}")
            embed = make_embed(
                action="error",
                title="Update Failed",
                description=f"Failed to update phrases: {str(e)}"
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)


class AlertRoleModal(discord.ui.Modal):
    """Modal for setting alert role."""
    
    def __init__(self, settings: TimeoutSettings):
        self.settings = settings
        super().__init__(title="Set Alert Role", timeout=300)
        
        self.add_item(discord.ui.TextInput(
            label="Role ID or Mention",
            placeholder="@Moderators or 123456789",
            style=discord.TextStyle.short,
            required=True
        ))
    
    async def callback(self, interaction: discord.Interaction) -> None:
        try:
            role_input = self.children[0].value
            
            # Extract role ID
            role_id = extract_id(role_input)
            if not role_id:
                embed = make_embed(
                    action="error",
                    title="Invalid Role",
                    description="Please provide a valid role mention or ID."
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Verify role exists
            role = interaction.guild.get_role(role_id)
            if not role:
                embed = make_embed(
                    action="error",
                    title="Role Not Found",
                    description=f"Could not find role with ID `{role_id}` in this server."
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            await interaction.client.db.update_timeout_settings(
                self.settings.guild_id,
                alert_role_id=role_id
            )
            
            # Update local settings object
            self.settings.alert_role_id = role_id
            
            embed = make_embed(
                action="ai",
                title="✅ Alert Role Set",
                description=f"Alert role set to {role.mention}"
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Error updating alert role: {e}")
            embed = make_embed(
                action="error",
                title="Update Failed",
                description=f"An unexpected error occurred: {str(e)}"
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)


class AlertChannelModal(discord.ui.Modal):
    """Modal for setting alert channel."""
    
    def __init__(self, settings: TimeoutSettings):
        self.settings = settings
        super().__init__(title="Set Alert Channel", timeout=300)
        
        self.add_item(discord.ui.TextInput(
            label="Channel ID or Mention",
            placeholder="#alerts or 123456789",
            style=discord.TextStyle.short,
            required=True
        ))
    
    async def callback(self, interaction: discord.Interaction) -> None:
        try:
            channel_input = self.children[0].value
            
            # Extract channel ID
            channel_id = extract_id(channel_input)
            if not channel_id:
                embed = make_embed(
                    action="error",
                    title="Invalid Channel",
                    description="Please provide a valid channel mention or ID."
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Verify channel exists
            channel = interaction.guild.get_channel(channel_id)
            if not channel:
                embed = make_embed(
                    action="error",
                    title="Channel Not Found",
                    description=f"Could not find channel with ID `{channel_id}` in this server."
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            if not isinstance(channel, (discord.TextChannel, discord.Thread)):
                embed = make_embed(
                    action="error",
                    title="Invalid Channel Type",
                    description="Alert channel must be a text channel or a thread."
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            await interaction.client.db.update_timeout_settings(
                self.settings.guild_id,
                alert_channel_id=channel_id
            )
            
            # Update local settings object
            self.settings.alert_channel_id = channel_id
            
            embed = make_embed(
                action="ai",
                title="✅ Alert Channel Set",
                description=f"Alert channel set to {channel.mention}"
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Error updating alert channel: {e}")
            embed = make_embed(
                action="error",
                title="Update Failed",
                description=f"An unexpected error occurred: {str(e)}"
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)


class TimeoutDurationModal(discord.ui.Modal):
    """Modal for setting timeout duration."""
    
    def __init__(self, settings: TimeoutSettings):
        self.settings = settings
        super().__init__(title="Set Timeout Duration", timeout=300)
        
        self.add_item(discord.ui.TextInput(
            label="Duration (hours, 15-720)",
            placeholder="24",
            style=discord.TextStyle.short,
            required=True
        ))
    
    async def callback(self, interaction: discord.Interaction) -> None:
        try:
            duration_input = self.children[0].value
            
            try:
                hours = int(duration_input)
                if hours < 15 or hours > 720:
                    raise ValueError("Duration out of range")
                
                duration_seconds = hours * 3600
                
                await interaction.client.db.update_timeout_settings(
                    self.settings.guild_id,
                    timeout_duration=duration_seconds
                )
                
                # Update local settings object
                self.settings.timeout_duration = duration_seconds
                
                embed = make_embed(
                    action="ai",
                    title="✅ Duration Updated",
                    description=f"Timeout duration set to {hours} hours"
                )
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
            except ValueError:
                embed = make_embed(
                    action="error",
                    title="Invalid Duration",
                    description="Please provide a valid duration between 15 and 720 hours."
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Error updating timeout duration: {e}")
            embed = make_embed(
                action="error",
                title="Update Failed",
                description=f"An unexpected error occurred: {str(e)}"
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)


class PhrasesView(discord.ui.View):
    """View for displaying phrases with pagination."""
    
    def __init__(self, phrases: list[str], settings: TimeoutSettings, bot, guild_id: int, timeout: float = 180):
        super().__init__(timeout=timeout)
        self.phrases = phrases
        self.settings = settings
        self.bot = bot
        self.guild_id = guild_id
        self.current_page = 0
        self.phrases_per_page = 5
        self.original_author_id: int | None = None
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Only the person who opened the phrases view can interact with it
        if self.original_author_id and interaction.user.id != self.original_author_id:
            await interaction.response.send_message("Only the person who opened this view can use these controls.", ephemeral=True)
            return False
        return True
    
    async def create_embed(self) -> discord.Embed:
        """Create the phrases list embed."""
        start_idx = self.current_page * self.phrases_per_page
        end_idx = start_idx + self.phrases_per_page
        page_phrases = self.phrases[start_idx:end_idx]
        
        total_pages = (len(self.phrases) + self.phrases_per_page - 1) // self.phrases_per_page
        
        embed = make_embed(
            action="ai",
            title="📋 Prohibited Phrases",
            description=f"Page {self.current_page + 1}/{total_pages} ({len(self.phrases)} total phrases)"
        )
        
        for i, phrase in enumerate(page_phrases, start_idx + 1):
            embed.add_field(
                name=f"Phrase {i}",
                value=f"`{phrase}`",
                inline=False
            )
        
        return embed
    
    @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary, emoji="⏮️")
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if self.current_page > 0:
            self.current_page -= 1
            embed = await self.create_embed()
            await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary, emoji="⏭️")
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        total_pages = (len(self.phrases) + self.phrases_per_page - 1) // self.phrases_per_page
        if self.current_page < total_pages - 1:
            self.current_page += 1
            embed = await self.create_embed()
            await interaction.response.edit_message(embed=embed, view=self)


async def setup(bot: VertigoBot) -> None:
    """Load the AI moderation cog."""
    await bot.add_cog(AIModerationCog(bot))