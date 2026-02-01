"""Staff hierarchy management system with promotion/demotion commands."""

from __future__ import annotations

import logging

import discord
from discord.ext import commands

import config
from database import Database, GuildSettings
from helpers import (
    commands_channel_check,
    make_embed,
    require_admin,
    safe_delete,
)

logger = logging.getLogger(__name__)


class SetHierarchyModal(discord.ui.Modal):
    """Modal for setting staff hierarchy."""
    
    def __init__(self, cog: HierarchyCog):
        super().__init__(title="Set Staff Hierarchy", timeout=300)
        self.cog = cog
        
        self.add_item(discord.ui.TextInput(
            label="Staff Roles (Highest to Lowest)",
            placeholder="Enter role IDs or mentions, one per line\nExample:\n1234567890\n0987654321",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1000
        ))
    
    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Parse role IDs from input
            role_input = self.children[0].value
            lines = [line.strip() for line in role_input.split('\n') if line.strip()]
            
            role_ids = []
            for line in lines:
                # Extract ID from mention or raw ID
                line = line.strip('<@&>').strip()
                try:
                    role_id = int(line)
                    # Validate role exists
                    role = interaction.guild.get_role(role_id)
                    if role:
                        role_ids.append(role_id)
                    else:
                        await interaction.followup.send(f"❌ Role ID {role_id} not found in server.", ephemeral=True)
                        return
                except ValueError:
                    await interaction.followup.send(f"❌ Invalid role ID: {line}", ephemeral=True)
                    return
            
            if not role_ids:
                await interaction.followup.send("❌ No valid roles provided.", ephemeral=True)
                return
            
            # Save hierarchy
            await self.cog.db.set_staff_hierarchy(interaction.guild.id, role_ids)
            
            # Show confirmation
            role_mentions = [f"<@&{rid}>" for rid in role_ids]
            embed = make_embed(
                action="success",
                title="✅ Staff Hierarchy Set",
                description=f"**Hierarchy (Highest to Lowest):**\n" + "\n".join(f"{i+1}. {role}" for i, role in enumerate(role_mentions))
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error("Error setting hierarchy: %s", e)
            await interaction.followup.send("❌ Failed to set hierarchy.", ephemeral=True)


class SetPromotionChannelModal(discord.ui.Modal):
    """Modal for setting promotion channel."""
    
    def __init__(self, cog: HierarchyCog):
        super().__init__(title="Set Promotion Channel", timeout=300)
        self.cog = cog
        
        self.add_item(discord.ui.TextInput(
            label="Promotion Channel ID or Mention",
            placeholder="Example: 1234567890 or #promotions",
            style=discord.TextStyle.short,
            required=True,
            max_length=100
        ))
    
    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Parse channel ID
            channel_input = self.children[0].value.strip().strip('<#>')
            try:
                channel_id = int(channel_input)
            except ValueError:
                await interaction.followup.send("❌ Invalid channel ID.", ephemeral=True)
                return
            
            # Validate channel exists
            channel = interaction.guild.get_channel(channel_id)
            if not channel:
                await interaction.followup.send("❌ Channel not found in server.", ephemeral=True)
                return
            
            # Save to database
            await self.cog.db.update_guild_settings(interaction.guild.id, promotion_channel_id=channel_id)
            
            # Show confirmation
            embed = make_embed(
                action="success",
                title="✅ Promotion Channel Set",
                description=f"Promotion messages will be sent to <#{channel_id}>"
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error("Error setting promotion channel: %s", e)
            await interaction.followup.send("❌ Failed to set promotion channel.", ephemeral=True)


class HierarchyPanelView(discord.ui.View):
    """View for hierarchy management panel."""
    
    def __init__(self, cog: HierarchyCog):
        super().__init__(timeout=180)
        self.cog = cog
    
    @discord.ui.button(label="Set Staff Hierarchy", style=discord.ButtonStyle.primary, emoji="📋")
    async def set_hierarchy_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        modal = SetHierarchyModal(self.cog)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Set Promotion Channel", style=discord.ButtonStyle.primary, emoji="🔗")
    async def set_channel_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        modal = SetPromotionChannelModal(self.cog)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="See Settings", style=discord.ButtonStyle.secondary, emoji="⚙️")
    async def see_settings_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Get current settings
            hierarchy = await self.cog.db.get_staff_hierarchy(interaction.guild.id)
            settings = await self.cog.db.get_guild_settings(interaction.guild.id, default_prefix=config.DEFAULT_PREFIX)
            
            embed = make_embed(
                action="hierarchy",
                title="⚙️ Hierarchy Settings"
            )
            
            # Show hierarchy
            if hierarchy:
                role_mentions = [f"<@&{rid}>" for rid in hierarchy]
                hierarchy_text = "\n".join(f"{i+1}. {role}" for i, role in enumerate(role_mentions))
                embed.add_field(name="📋 Staff Hierarchy", value=hierarchy_text, inline=False)
            else:
                embed.add_field(name="📋 Staff Hierarchy", value=f"{config.EMBED_COLOR_GRAY} Not configured", inline=False)
            
            # Show promotion channel
            if settings.promotion_channel_id:
                embed.add_field(name="🔗 Promotion Channel", value=f"<#{settings.promotion_channel_id}>", inline=False)
            else:
                embed.add_field(name="🔗 Promotion Channel", value=f"{config.EMBED_COLOR_GRAY} Not configured", inline=False)
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error("Error showing settings: %s", e)
            await interaction.followup.send("❌ Failed to load settings.", ephemeral=True)
    
    @discord.ui.button(label="Preview Message", style=discord.ButtonStyle.secondary, emoji="👀")
    async def preview_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer(ephemeral=True)
        
        try:
            embed = make_embed(
                action="hierarchy",
                title="👀 Preview Promotion Message"
            )
            
            example = f"{interaction.user.mention} Congratulations for being promoted to Admin🔥🎉"
            
            embed.add_field(
                name="📝 Example Format",
                value=example,
                inline=False
            )
            embed.add_field(
                name="ℹ️ Note",
                value="• User will be pinged\n• Role name shown without ping\n• Sent to configured promotion channel",
                inline=False
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error("Error showing preview: %s", e)
            await interaction.followup.send("❌ Failed to show preview.", ephemeral=True)


class HierarchyCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @property
    def db(self) -> Database:
        return self.bot.db  # type: ignore[attr-defined]

    async def _settings(self, guild: discord.Guild) -> GuildSettings:
        return await self.db.get_guild_settings(guild.id, default_prefix=config.DEFAULT_PREFIX)

    @commands.command(name="hierarchy")
    @commands.guild_only()
    @commands_channel_check()
    @require_admin()
    async def hierarchy(self, ctx: commands.Context) -> None:
        """Open the staff hierarchy management panel."""
        
        embed = make_embed(
            action="hierarchy",
            title="📊 Staff Hierarchy Management",
            description=(
                "**Manage staff promotions and demotions**\n\n"
                "Use the buttons below to:\n"
                "📋 Set the staff role hierarchy\n"
                "🔗 Configure promotion announcements channel\n"
                "⚙️ View current settings\n"
                "👀 Preview promotion message format"
            )
        )
        
        view = HierarchyPanelView(self)
        await ctx.send(embed=embed, view=view)
        await safe_delete(ctx.message)

    @commands.command(name="promote")
    @commands.guild_only()
    @commands_channel_check()
    @require_admin()
    async def promote(self, ctx: commands.Context, member: discord.Member) -> None:
        """Promote a staff member to the next rank in hierarchy."""
        
        hierarchy = await self.db.get_staff_hierarchy(ctx.guild.id)
        
        if not hierarchy:
            embed = make_embed(
                action="error",
                title="❌ No Hierarchy Configured",
                description="Use `!hierarchy` to set up the staff hierarchy first."
            )
            await ctx.send(embed=embed)
            return
        
        # Find current role in hierarchy
        current_role_id = None
        current_index = -1
        
        for i, role_id in enumerate(hierarchy):
            if role_id in [r.id for r in member.roles]:
                current_role_id = role_id
                current_index = i
                break
        
        if current_role_id is None:
            embed = make_embed(
                action="error",
                title="❌ Not In Hierarchy",
                description=f"{member.mention} is not in the staff hierarchy."
            )
            await ctx.send(embed=embed)
            return
        
        # Check if already at highest rank
        if current_index == 0:
            embed = make_embed(
                action="error",
                title="❌ Already At Highest Rank",
                description=f"{member.mention} is already at the highest rank in the hierarchy."
            )
            await ctx.send(embed=embed)
            return
        
        # Get next role (higher rank = lower index)
        next_role_id = hierarchy[current_index - 1]
        current_role = ctx.guild.get_role(current_role_id)
        next_role = ctx.guild.get_role(next_role_id)
        
        if not current_role or not next_role:
            embed = make_embed(
                action="error",
                title="❌ Role Not Found",
                description="One of the roles in the hierarchy no longer exists."
            )
            await ctx.send(embed=embed)
            return
        
        try:
            # Remove old role and assign new role
            await member.remove_roles(current_role, reason=f"Promoted by {ctx.author}")
            await member.add_roles(next_role, reason=f"Promoted by {ctx.author}")
            
            # Send confirmation in command channel
            embed = make_embed(
                action="success",
                title="✅ Staff Member Promoted",
                description=f"**Member:** {member.mention}\n**From:** {current_role.name}\n**To:** {next_role.name}\n**By:** {ctx.author.mention}"
            )
            await ctx.send(embed=embed)
            
            # Send promotion message to configured channel
            settings = await self._settings(ctx.guild)
            if settings.promotion_channel_id:
                promo_channel = ctx.guild.get_channel(settings.promotion_channel_id)
                if promo_channel and isinstance(promo_channel, discord.TextChannel):
                    promo_message = f"{member.mention} Congratulations for being promoted to {next_role.name}🔥🎉"
                    await promo_channel.send(promo_message)
            
            # Add to modlog
            await self.db.add_modlog(
                guild_id=ctx.guild.id,
                action_type="promote",
                user_id=member.id,
                moderator_id=ctx.author.id,
                reason=f"Promoted from {current_role.name} to {next_role.name}"
            )
            
            await safe_delete(ctx.message)
            
        except discord.Forbidden:
            embed = make_embed(
                action="error",
                title="❌ Missing Permissions",
                description="I don't have permission to manage these roles."
            )
            await ctx.send(embed=embed)
        except Exception as e:
            logger.error("Error promoting member: %s", e)
            embed = make_embed(
                action="error",
                title="❌ Error",
                description="Failed to promote member."
            )
            await ctx.send(embed=embed)

    @commands.command(name="demote")
    @commands.guild_only()
    @commands_channel_check()
    @require_admin()
    async def demote(self, ctx: commands.Context, member: discord.Member) -> None:
        """Demote a staff member to the previous rank in hierarchy."""
        
        hierarchy = await self.db.get_staff_hierarchy(ctx.guild.id)
        
        if not hierarchy:
            embed = make_embed(
                action="error",
                title="❌ No Hierarchy Configured",
                description="Use `!hierarchy` to set up the staff hierarchy first."
            )
            await ctx.send(embed=embed)
            return
        
        # Find current role in hierarchy
        current_role_id = None
        current_index = -1
        
        for i, role_id in enumerate(hierarchy):
            if role_id in [r.id for r in member.roles]:
                current_role_id = role_id
                current_index = i
                break
        
        if current_role_id is None:
            embed = make_embed(
                action="error",
                title="❌ Not In Hierarchy",
                description=f"{member.mention} is not in the staff hierarchy."
            )
            await ctx.send(embed=embed)
            return
        
        # Check if already at lowest rank
        if current_index == len(hierarchy) - 1:
            embed = make_embed(
                action="error",
                title="❌ Already At Lowest Rank",
                description=f"{member.mention} is already at the lowest rank in the hierarchy."
            )
            await ctx.send(embed=embed)
            return
        
        # Get previous role (lower rank = higher index)
        prev_role_id = hierarchy[current_index + 1]
        current_role = ctx.guild.get_role(current_role_id)
        prev_role = ctx.guild.get_role(prev_role_id)
        
        if not current_role or not prev_role:
            embed = make_embed(
                action="error",
                title="❌ Role Not Found",
                description="One of the roles in the hierarchy no longer exists."
            )
            await ctx.send(embed=embed)
            return
        
        try:
            # Remove old role and assign new role
            await member.remove_roles(current_role, reason=f"Demoted by {ctx.author}")
            await member.add_roles(prev_role, reason=f"Demoted by {ctx.author}")
            
            # Send confirmation in command channel
            embed = make_embed(
                action="success",
                title="✅ Staff Member Demoted",
                description=f"**Member:** {member.mention}\n**From:** {current_role.name}\n**To:** {prev_role.name}\n**By:** {ctx.author.mention}"
            )
            await ctx.send(embed=embed)
            
            # Add to modlog
            await self.db.add_modlog(
                guild_id=ctx.guild.id,
                action_type="demote",
                user_id=member.id,
                moderator_id=ctx.author.id,
                reason=f"Demoted from {current_role.name} to {prev_role.name}"
            )
            
            await safe_delete(ctx.message)
            
        except discord.Forbidden:
            embed = make_embed(
                action="error",
                title="❌ Missing Permissions",
                description="I don't have permission to manage these roles."
            )
            await ctx.send(embed=embed)
        except Exception as e:
            logger.error("Error demoting member: %s", e)
            embed = make_embed(
                action="error",
                title="❌ Error",
                description="Failed to demote member."
            )
            await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(HierarchyCog(bot))
