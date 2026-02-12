"""AI Chatbot with Gen-Z meme personality using HuggingFace Inference API."""

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


async def setup(bot: VertigoBot) -> None:
    """Load the AI cog."""
    await bot.add_cog(AICog(bot))