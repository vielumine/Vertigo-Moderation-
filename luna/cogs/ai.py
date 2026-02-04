"""
Luna Bot AI Cog
Handles AI system with Gemini integration and AI panel.
"""

import discord
from discord.ext import commands

from database import (
    get_ai_setting,
    set_ai_setting,
)
from helpers import (
    make_embed,
    get_embed_color,
    is_admin,
    get_gemini_response,
    utcnow,
)
from config import (
    DEEP_SPACE,
    COLOR_SUCCESS,
    COLOR_INFO,
    COLOR_WARNING,
    COLOR_ERROR,
)


class AIPanelView(discord.ui.View):
    """View for AI control panel."""
    
    def __init__(self, bot: commands.Bot, guild_id: int):
        super().__init__(timeout=None)
        self.bot = bot
        self.guild_id = guild_id
    
    async def _update_panel(self, interaction: discord.Interaction):
        """Update the AI panel with current settings."""
        ai_enabled = await get_ai_setting(self.guild_id, "ai_enabled")
        moderation_enabled = await get_ai_setting(self.guild_id, "moderation_enabled")
        dm_response_enabled = await get_ai_setting(self.guild_id, "dm_response_enabled")
        
        # Update button labels/colors
        self.toggle_ai.label = "AI: ON" if ai_enabled else "AI: OFF"
        self.toggle_ai.style = discord.ButtonStyle.success if ai_enabled else discord.ButtonStyle.secondary
        
        self.toggle_moderation.label = "Moderation: ON" if moderation_enabled else "Moderation: OFF"
        self.toggle_moderation.style = discord.ButtonStyle.success if moderation_enabled else discord.ButtonStyle.secondary
        
        self.toggle_dm.label = "DM Response: ON" if dm_response_enabled else "DM Response: OFF"
        self.toggle_dm.style = discord.ButtonStyle.success if dm_response_enabled else discord.ButtonStyle.secondary
        
        # Update embed
        embed = make_embed(
            title="🌙 Luna AI Control Panel",
            color=COLOR_INFO,
            fields=[
                ("AI Status", "✅ Enabled" if ai_enabled else "❌ Disabled", True),
                ("Moderation Helper", "✅ Enabled" if moderation_enabled else "❌ Disabled", True),
                ("DM Response", "✅ Enabled" if dm_response_enabled else "❌ Disabled", True),
            ],
            footer="Use the buttons below to toggle settings"
        )
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="AI: ON", style=discord.ButtonStyle.success)
    async def toggle_ai(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Toggle AI on/off."""
        if not await is_admin(interaction.user, interaction.guild):
            await interaction.response.send_message(
                embed=make_embed(
                    title="❌ Insufficient Permissions",
                    description="This requires administrator privileges.",
                    color=COLOR_ERROR
                ),
                ephemeral=True
            )
            return
        
        current = await get_ai_setting(self.guild_id, "ai_enabled")
        await set_ai_setting(self.guild_id, "ai_enabled", 0 if current else 1)
        
        await self._update_panel(interaction)
    
    @discord.ui.button(label="Moderation: ON", style=discord.ButtonStyle.success)
    async def toggle_moderation(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Toggle moderation helper on/off."""
        if not await is_admin(interaction.user, interaction.guild):
            await interaction.response.send_message(
                embed=make_embed(
                    title="❌ Insufficient Permissions",
                    description="This requires administrator privileges.",
                    color=COLOR_ERROR
                ),
                ephemeral=True
            )
            return
        
        current = await get_ai_setting(self.guild_id, "moderation_enabled")
        await set_ai_setting(self.guild_id, "moderation_enabled", 0 if current else 1)
        
        await self._update_panel(interaction)
    
    @discord.ui.button(label="DM Response: ON", style=discord.ButtonStyle.success)
    async def toggle_dm(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Toggle DM response on/off."""
        if not await is_admin(interaction.user, interaction.guild):
            await interaction.response.send_message(
                embed=make_embed(
                    title="❌ Insufficient Permissions",
                    description="This requires administrator privileges.",
                    color=COLOR_ERROR
                ),
                ephemeral=True
            )
            return
        
        current = await get_ai_setting(self.guild_id, "dm_response_enabled")
        await set_ai_setting(self.guild_id, "dm_response_enabled", 0 if current else 1)
        
        await self._update_panel(interaction)
    
    @discord.ui.button(label="📊 View Settings", style=discord.ButtonStyle.primary)
    async def view_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        """View detailed AI settings."""
        ai_enabled = await get_ai_setting(self.guild_id, "ai_enabled")
        moderation_enabled = await get_ai_setting(self.guild_id, "moderation_enabled")
        dm_response_enabled = await get_ai_setting(self.guild_id, "dm_response_enabled")
        personality = await get_ai_setting(self.guild_id, "personality")
        
        embed = make_embed(
            title="🌙 AI Settings Details",
            color=COLOR_INFO,
            fields=[
                ("AI Enabled", "✅ Yes" if ai_enabled else "❌ No", True),
                ("Moderation Helper", "✅ Yes" if moderation_enabled else "❌ No", True),
                ("DM Response", "✅ Yes" if dm_response_enabled else "❌ No", True),
                ("Personality", personality or "helpful", True),
            ],
            footer="Available personalities: helpful, sarcastic, genz, professional"
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="🔄 Refresh", style=discord.ButtonStyle.secondary)
    async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Refresh the panel."""
        await self._update_panel(interaction)


class AI(commands.Cog):
    """AI system commands."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def aipanel(self, ctx: commands.Context):
        """
        Summon the AI control panel.
        OWNER ONLY.
        """
        # Verify owner
        from config import OWNER_ID
        if ctx.author.id != OWNER_ID:
            await ctx.reply(embed=make_embed(
                title="❌ Owner Only",
                description="This command is restricted to the bot owner.",
                color=COLOR_ERROR
            ))
            return
        
        # Create panel
        view = AIPanelView(self.bot, ctx.guild.id)
        
        # Get current settings
        ai_enabled = await get_ai_setting(ctx.guild.id, "ai_enabled")
        moderation_enabled = await get_ai_setting(ctx.guild.id, "moderation_enabled")
        dm_response_enabled = await get_ai_setting(ctx.guild.id, "dm_response_enabled")
        
        embed = make_embed(
            title="🌙 Luna AI Control Panel",
            color=COLOR_INFO,
            fields=[
                ("AI Status", "✅ Enabled" if ai_enabled else "❌ Disabled", True),
                ("Moderation Helper", "✅ Enabled" if moderation_enabled else "❌ Disabled", True),
                ("DM Response", "✅ Enabled" if dm_response_enabled else "❌ Disabled", True),
            ],
            footer="Use the buttons below to toggle settings"
        )
        
        await ctx.reply(embed=embed, view=view)
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def ai_settings(self, ctx: commands.Context, setting: str = None, value: str = None):
        """View or change AI settings."""
        from config import OWNER_ID
        if ctx.author.id != OWNER_ID:
            await ctx.reply(embed=make_embed(
                title="❌ Owner Only",
                description="This command is restricted to the bot owner.",
                color=COLOR_ERROR
            ))
            return
        
        # View settings
        if not setting:
            ai_enabled = await get_ai_setting(ctx.guild.id, "ai_enabled")
            moderation_enabled = await get_ai_setting(ctx.guild.id, "moderation_enabled")
            dm_response_enabled = await get_ai_setting(ctx.guild.id, "dm_response_enabled")
            personality = await get_ai_setting(ctx.guild.id, "personality")
            
            embed = make_embed(
                title="🌙 AI Settings",
                color=COLOR_INFO,
                fields=[
                    ("AI Enabled", "✅ Yes" if ai_enabled else "❌ No", True),
                    ("Moderation Helper", "✅ Yes" if moderation_enabled else "❌ No", True),
                    ("DM Response", "✅ Yes" if dm_response_enabled else "❌ No", True),
                    ("Personality", personality or "helpful", True),
                ],
                footer="Usage: `,ai_settings <setting> <value>`"
            )
            
            await ctx.reply(embed=embed)
            return
        
        # Change setting
        setting_lower = setting.lower()
        
        if setting_lower in ["ai_enabled", "ai", "enabled"]:
            if value.lower() in ["true", "yes", "on", "1"]:
                await set_ai_setting(ctx.guild.id, "ai_enabled", 1)
                await ctx.reply(embed=make_embed(
                    title="✅ AI Enabled",
                    color=COLOR_SUCCESS
                ))
            elif value.lower() in ["false", "no", "off", "0"]:
                await set_ai_setting(ctx.guild.id, "ai_enabled", 0)
                await ctx.reply(embed=make_embed(
                    title="✅ AI Disabled",
                    color=COLOR_SUCCESS
                ))
            else:
                await ctx.reply(embed=make_embed(
                    title="❌ Invalid Value",
                    description="Use: true/false, yes/no, on/off, or 1/0",
                    color=COLOR_ERROR
                ))
        
        elif setting_lower in ["moderation", "mod", "moderation_enabled"]:
            if value.lower() in ["true", "yes", "on", "1"]:
                await set_ai_setting(ctx.guild.id, "moderation_enabled", 1)
                await ctx.reply(embed=make_embed(
                    title="✅ Moderation Helper Enabled",
                    color=COLOR_SUCCESS
                ))
            elif value.lower() in ["false", "no", "off", "0"]:
                await set_ai_setting(ctx.guild.id, "moderation_enabled", 0)
                await ctx.reply(embed=make_embed(
                    title="✅ Moderation Helper Disabled",
                    color=COLOR_SUCCESS
                ))
            else:
                await ctx.reply(embed=make_embed(
                    title="❌ Invalid Value",
                    description="Use: true/false, yes/no, on/off, or 1/0",
                    color=COLOR_ERROR
                ))
        
        elif setting_lower in ["dm", "dm_response", "dm_enabled"]:
            if value.lower() in ["true", "yes", "on", "1"]:
                await set_ai_setting(ctx.guild.id, "dm_response_enabled", 1)
                await ctx.reply(embed=make_embed(
                    title="✅ DM Response Enabled",
                    color=COLOR_SUCCESS
                ))
            elif value.lower() in ["false", "no", "off", "0"]:
                await set_ai_setting(ctx.guild.id, "dm_response_enabled", 0)
                await ctx.reply(embed=make_embed(
                    title="✅ DM Response Disabled",
                    color=COLOR_SUCCESS
                ))
            else:
                await ctx.reply(embed=make_embed(
                    title="❌ Invalid Value",
                    description="Use: true/false, yes/no, on/off, or 1/0",
                    color=COLOR_ERROR
                ))
        
        elif setting_lower in ["personality", "persona"]:
            valid_personalities = ["helpful", "sarcastic", "genz", "professional"]
            if value.lower() in valid_personalities:
                await set_ai_setting(ctx.guild.id, "personality", value.lower())
                await ctx.reply(embed=make_embed(
                    title="✅ Personality Updated",
                    description=f"Personality set to: `{value.lower()}`",
                    color=COLOR_SUCCESS
                ))
            else:
                await ctx.reply(embed=make_embed(
                    title="❌ Invalid Personality",
                    description=f"Valid personalities: {', '.join(valid_personalities)}",
                    color=COLOR_ERROR
                ))
        
        else:
            await ctx.reply(embed=make_embed(
                title="❌ Invalid Setting",
                description="Valid settings: ai_enabled, moderation_enabled, dm_response_enabled, personality",
                color=COLOR_ERROR
            ))


async def setup(bot: commands.Bot):
    await bot.add_cog(AI(bot))
