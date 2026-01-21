"""AI Chatbot with Gen-Z meme personality using HuggingFace Inference API."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from .. import config
from ..database import AISettings, Database
from ..helpers import (
    add_loading_reaction,
    get_ai_response,
    is_ai_enabled_for_guild,
    is_rate_limited,
    make_embed,
    require_admin,
    should_help_with_moderation,
    update_rate_limit,
)

if TYPE_CHECKING:
    from ..main import VertigoBot

logger = logging.getLogger(__name__)


class AIButton(discord.ui.Button):
    """Base class for AI settings buttons."""
    
    def __init__(self, *, label: str, custom_id: str, style: discord.ButtonStyle, emoji: str | None = None):
        super().__init__(label=label, custom_id=custom_id, style=style, emoji=emoji)


class AIButtonView(discord.ui.View):
    """View for AI settings with toggle buttons."""
    
    def __init__(self, ai_settings: AISettings, bot, timeout: float = 180):
        super().__init__(timeout=timeout)
        self.ai_settings = ai_settings
        self.bot = bot
        self.message: discord.Message | None = None
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Only administrators can use these buttons.", ephemeral=True)
            return False
        return True
    
    @discord.ui.button(label="Toggle Mentions", custom_id="ai_toggle_mentions", style=discord.ButtonStyle.secondary, emoji="📣")
    async def toggle_mentions_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        new_value = not self.ai_settings.respond_to_mentions
        await self.update_setting("respond_to_mentions", new_value, interaction, f"Mentions response {'enabled' if new_value else 'disabled'}")
    
    @discord.ui.button(label="Toggle DMs", custom_id="ai_toggle_dms", style=discord.ButtonStyle.secondary, emoji="💬")
    async def toggle_dms_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        new_value = not self.ai_settings.respond_to_dms
        await self.update_setting("respond_to_dms", new_value, interaction, f"DM response {'enabled' if new_value else 'disabled'}")
    
    @discord.ui.button(label="Toggle Moderation", custom_id="ai_toggle_moderation", style=discord.ButtonStyle.secondary, emoji="🛡️")
    async def toggle_moderation_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        new_value = not self.ai_settings.help_moderation
        await self.update_setting("help_moderation", new_value, interaction, f"Moderation help {'enabled' if new_value else 'disabled'}")
    
    async def update_setting(self, setting_name: str, new_value: bool, interaction: discord.Interaction, description: str) -> None:
        """Update a setting and refresh the embed."""
        try:
            db = self.bot.db
            await db.update_ai_settings(interaction.guild.id, **{setting_name: new_value})
            self.ai_settings = await db.get_ai_settings(interaction.guild.id)
            
            embed = await self._create_settings_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        except Exception as e:
            logger.error("Failed to update AI setting: %s", e)
            await interaction.response.send_message("Failed to update setting. Please try again.", ephemeral=True)
    
    async def _create_settings_embed(self) -> discord.Embed:
        """Create the AI settings embed."""
        embed = make_embed(
            action="ai_settings",
            title="⚙️ AI Settings",
            description=f"Configure your AI chatbot settings for {self.ai_settings.guild_id}"
        )
        
        # Get guild name if available
        guild = self.bot.get_guild(self.ai_settings.guild_id)
        if guild:
            embed.description = f"Configure your AI chatbot settings for {guild.name}"
        
        embed.add_field(
            name="✅ AI Enabled",
            value="Yes" if self.ai_settings.ai_enabled else "No",
            inline=True
        )
        embed.add_field(
            name="📣 Respond to Mentions", 
            value="Yes" if self.ai_settings.respond_to_mentions else "No",
            inline=True
        )
        embed.add_field(
            name="💬 Respond to DMs",
            value="Yes" if self.ai_settings.respond_to_dms else "No", 
            inline=True
        )
        embed.add_field(
            name="🛡️ Help Moderation",
            value="Yes" if self.ai_settings.help_moderation else "No",
            inline=True
        )
        embed.add_field(
            name="🎭 Personality",
            value=self.ai_settings.ai_personality.title(),
            inline=True
        )
        
        return embed


class AICog(commands.Cog):
    """AI Chatbot with Gen-Z meme personality."""
    
    def __init__(self, bot: VertigoBot) -> None:
        self.bot = bot
    
    @property
    def db(self) -> Database:
        return self.bot.db
    
    async def _ai_settings(self, guild_id: int) -> AISettings:
        return await self.db.get_ai_settings(guild_id)
    
    @commands.command(name="ai", aliases=["ask"])
    @commands.guild_only()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def ai_command(self, ctx: commands.Context, *, question: str) -> None:
        """Ask the AI a question and get a Gen-Z meme style response."""
        # Check if AI is enabled
        if not await is_ai_enabled_for_guild(ctx.guild.id, self.db):  # type: ignore[arg-type]
            embed = make_embed(
                action="error",
                title="AI Disabled",
                description="AI chatbot is currently disabled in this server."
            )
            await ctx.send(embed=embed)
            return
        
        # Check rate limiting
        if is_rate_limited(ctx.author.id):
            embed = make_embed(
                action="error",
                title="Rate Limited",
                description=f"Take a break! You can ask another question in {config.RATE_LIMIT_SECONDS} seconds."
            )
            await ctx.send(embed=embed)
            return
        
        # Add loading reaction
        await add_loading_reaction(ctx.message)
        
        try:
            # Get AI settings to determine personality
            ai_settings = await self._ai_settings(ctx.guild.id)  # type: ignore[arg-type]
            
            # Check if this is a moderation question
            if ai_settings.help_moderation and should_help_with_moderation(question):
                # For moderation questions, we can provide some guidance
                response = await get_ai_response(f"{question}\n\nNote: This seems like a moderation question. Please refer to server rules or contact moderators.", ai_settings.ai_personality)
            else:
                response = await get_ai_response(question, ai_settings.ai_personality)
            
            # Update rate limit
            update_rate_limit(ctx.author.id)
            
            # Create embed with response
            embed = make_embed(
                action="ai",
                title="🤖 AI Response",
                description=f"**Question:** {question}\n\n**AI Says:** {response}"
            )
            
            # Add personality info
            embed.add_field(
                name="🎭 Personality",
                value=ai_settings.ai_personality.title(),
                inline=True
            )
            
            # Add footer with character count
            embed.set_footer(text=f"Powered by HuggingFace • {len(response)}/{config.MAX_RESPONSE_LENGTH} characters")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error("AI command error: %s", e)
            embed = make_embed(
                action="error",
                title="AI Error",
                description="The AI is having some issues right now. Please try again later."
            )
            await ctx.send(embed=embed)
    
    @commands.command(name="toggle_ai")
    @commands.guild_only()
    @require_admin()
    async def toggle_ai_command(self, ctx: commands.Context, state: str) -> None:
        """Toggle AI on/off for the server."""
        state = state.lower()
        if state not in ["on", "off", "enable", "disable"]:
            embed = make_embed(
                action="error",
                title="Invalid State",
                description="Please specify 'on' or 'off'."
            )
            await ctx.send(embed=embed)
            return
        
        new_state = state in ["on", "enable"]
        
        try:
            await self.db.update_ai_settings(ctx.guild.id, ai_enabled=new_state)  # type: ignore[arg-type]
            
            status_text = "enabled" if new_state else "disabled"
            embed = make_embed(
                action="toggle_ai",
                title="⚙️ AI Status Updated",
                description=f"AI chatbot has been **{status_text}** for this server."
            )
            embed.add_field(
                name="✅ AI Status",
                value="On" if new_state else "Off",
                inline=True
            )
            embed.add_field(
                name="📌 Server",
                value=ctx.guild.name,
                inline=True
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error("Toggle AI error: %s", e)
            embed = make_embed(
                action="error",
                title="Toggle Failed",
                description="Failed to toggle AI status. Please try again."
            )
            await ctx.send(embed=embed)
    
    @commands.command(name="ai_settings")
    @commands.guild_only()
    @require_admin()
    async def ai_settings_command(self, ctx: commands.Context) -> None:
        """View and configure AI settings with interactive buttons."""
        try:
            ai_settings = await self._ai_settings(ctx.guild.id)  # type: ignore[arg-type]
            
            embed = make_embed(
                action="ai_settings",
                title="⚙️ AI Settings",
                description=f"Configure your AI chatbot settings for {ctx.guild.name}"
            )
            
            embed.add_field(
                name="✅ AI Enabled",
                value="Yes" if ai_settings.ai_enabled else "No",
                inline=True
            )
            embed.add_field(
                name="📣 Respond to Mentions",
                value="Yes" if ai_settings.respond_to_mentions else "No",
                inline=True
            )
            embed.add_field(
                name="💬 Respond to DMs",
                value="Yes" if ai_settings.respond_to_dms else "No",
                inline=True
            )
            embed.add_field(
                name="🛡️ Help Moderation",
                value="Yes" if ai_settings.help_moderation else "No",
                inline=True
            )
            embed.add_field(
                name="🎭 Personality",
                value=ai_settings.ai_personality.title(),
                inline=True
            )
            
            embed.add_field(
                name="ℹ️ Help",
                value="Use the buttons below to toggle settings. Only administrators can use these controls.",
                inline=False
            )
            
            # Create view with toggle buttons
            view = AIButtonView(ai_settings, self.bot)
            
            message = await ctx.send(embed=embed, view=view)
            view.message = message
            
        except Exception as e:
            logger.error("AI settings error: %s", e)
            embed = make_embed(
                action="error",
                title="Settings Error",
                description="Failed to load AI settings. Please try again."
            )
            await ctx.send(embed=embed)


async def setup(bot: VertigoBot) -> None:
    """Load the AI cog."""
    await bot.add_cog(AICog(bot))