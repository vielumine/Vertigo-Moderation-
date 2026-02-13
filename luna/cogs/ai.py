"""AI Chatbot with professional personality using Gemini API."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

import config
from database import AISettings, Database
from helpers import (
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
    from main import VertigoBot

logger = logging.getLogger(__name__)


class AICog(commands.Cog):
    """AI Chatbot with professional personality."""
    
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
        """Ask the AI a question and get a professional response."""
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
                description=f"Please wait. You can ask another question in {config.RATE_LIMIT_SECONDS} seconds."
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
                title="🌙 Luna AI",
                description=f"**Question:** {question}\n\n**Response:** {response}"
            )

            # Add personality info
            embed.add_field(
                name="🎭 Personality",
                value=ai_settings.ai_personality.title(),
                inline=True
            )

            # Add footer with character count
            embed.set_footer(text=f"Powered by Google Gemini • {len(response)}/{config.MAX_RESPONSE_LENGTH} characters")

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error("AI command error: %s", e)
            embed = make_embed(
                action="error",
                title="AI Error",
                description="The AI is having some issues right now. Please try again later."
            )
            await ctx.send(embed=embed)

    @commands.command(name="ai_settings", aliases=["aisettings", "aipanel"])
    @commands.guild_only()
    @require_admin()
    async def ai_settings(self, ctx: commands.Context) -> None:
        """AI settings panel with interactive buttons (Admin only).

        Usage:
        ,ai_settings
        """
        ai_settings = await self._ai_settings(ctx.guild.id)  # type: ignore[arg-type]

        # Create settings embed
        embed = make_embed(
            action="ai_settings",
            title="🌙 AI Settings Panel",
            description="Configure Luna's AI behavior for this server."
        )

        embed.add_field(
            name="Status",
            value="✅ Enabled" if ai_settings.ai_enabled else "❌ Disabled",
            inline=True
        )
        embed.add_field(
            name="Personality",
            value=ai_settings.ai_personality.title(),
            inline=True
        )
        embed.add_field(
            name="Respond to Mentions",
            value="✅ Yes" if ai_settings.respond_to_mentions else "❌ No",
            inline=True
        )
        embed.add_field(
            name="Respond to DMs",
            value="✅ Yes" if ai_settings.respond_to_dms else "❌ No",
            inline=True
        )
        embed.add_field(
            name="Help with Moderation",
            value="✅ Yes" if ai_settings.help_moderation else "❌ No",
            inline=True
        )

        embed.set_footer(text="Use the buttons below to toggle settings")

        # Create view with buttons
        view = AISettingsView(self.db, ctx.guild.id, ai_settings)

        await ctx.send(embed=embed, view=view)


class AISettingsView(discord.ui.View):
    """Interactive view for AI settings."""

    def __init__(self, db: Database, guild_id: int, settings: AISettings):
        super().__init__(timeout=300)
        self.db = db
        self.guild_id = guild_id
        self.settings = settings

    async def _update_embed(self, interaction: discord.Interaction) -> None:
        """Update the embed with current settings."""
        ai_settings = await self.db.get_ai_settings(self.guild_id)
        self.settings = ai_settings

        embed = make_embed(
            action="ai_settings",
            title="🌙 AI Settings Panel",
            description="Configure Luna's AI behavior for this server."
        )

        embed.add_field(
            name="Status",
            value="✅ Enabled" if ai_settings.ai_enabled else "❌ Disabled",
            inline=True
        )
        embed.add_field(
            name="Personality",
            value=ai_settings.ai_personality.title(),
            inline=True
        )
        embed.add_field(
            name="Respond to Mentions",
            value="✅ Yes" if ai_settings.respond_to_mentions else "❌ No",
            inline=True
        )
        embed.add_field(
            name="Respond to DMs",
            value="✅ Yes" if ai_settings.respond_to_dms else "❌ No",
            inline=True
        )
        embed.add_field(
            name="Help with Moderation",
            value="✅ Yes" if ai_settings.help_moderation else "❌ No",
            inline=True
        )

        embed.set_footer(text="Use the buttons below to toggle settings")

        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Toggle AI", style=discord.ButtonStyle.primary, emoji="🤖")
    async def toggle_ai(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:  # type: ignore[override]
        """Toggle AI enabled/disabled."""
        new_value = not self.settings.ai_enabled
        await self.db.update_ai_settings(self.guild_id, ai_enabled=new_value)
        await self._update_embed(interaction)

    @discord.ui.select(
        placeholder="Select Personality",
        options=[
            discord.SelectOption(label="Professional", value="professional", emoji="💼"),
            discord.SelectOption(label="Cold", value="cold", emoji="❄️"),
            discord.SelectOption(label="Formal", value="formal", emoji="🎩"),
        ],
        min_values=1,
        max_values=1
    )
    async def select_personality(self, interaction: discord.Interaction, select: discord.ui.Select) -> None:
        """Change AI personality."""
        personality = select.values[0]
        await self.db.update_ai_settings(self.guild_id, ai_personality=personality)
        await self._update_embed(interaction)

    @discord.ui.button(label="Mentions", style=discord.ButtonStyle.secondary, emoji="💬")
    async def toggle_mentions(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:  # type: ignore[override]
        """Toggle respond to mentions."""
        new_value = not self.settings.respond_to_mentions
        await self.db.update_ai_settings(self.guild_id, respond_to_mentions=new_value)
        await self._update_embed(interaction)

    @discord.ui.button(label="DMs", style=discord.ButtonStyle.secondary, emoji="📩")
    async def toggle_dms(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:  # type: ignore[override]
        """Toggle respond to DMs."""
        new_value = not self.settings.respond_to_dms
        await self.db.update_ai_settings(self.guild_id, respond_to_dms=new_value)
        await self._update_embed(interaction)

    @discord.ui.button(label="Moderation Help", style=discord.ButtonStyle.secondary, emoji="⚖️")
    async def toggle_moderation(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:  # type: ignore[override]
        """Toggle help with moderation questions."""
        new_value = not self.settings.help_moderation
        await self.db.update_ai_settings(self.guild_id, help_moderation=new_value)
        await self._update_embed(interaction)


async def setup(bot: VertigoBot) -> None:
    """Load the AI cog."""
    await bot.add_cog(AICog(bot))