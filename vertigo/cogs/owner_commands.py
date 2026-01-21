"""Owner Commands - Complete command overview for bot owner."""

from __future__ import annotations

import logging

import discord
from discord.ext import commands

from .. import config
from ..helpers import make_embed, require_owner

logger = logging.getLogger(__name__)


class OwnerCommandsCog(commands.Cog):
    """Owner-only commands for complete bot management."""
    
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
    
    @commands.command(name="commands", aliases=["cmd", "help_all"])
    @require_owner()
    async def commands(self, ctx: commands.Context) -> None:
        """Show all available commands organized by category."""
        try:
            # Create the main embed
            embed = make_embed(
                action="owner",
                title="📋 Vertigo Bot - Complete Command List",
                description="All available commands organized by permission level and category."
            )
            
            embed.add_field(
                name="🔧 Owner Only Commands",
                value=(
                    "**AI Moderation:**\n"
                    "`!aiwarn`, `!aimute`, `!aikick`, `!aiban`, `!aiflag`\n"
                    "`!aitarget`, `!airemove`\n"
                    "`!blacklist`, `!unblacklist`, `!seeblacklist`\n"
                    "`!timeoutpanel`\n\n"
                    "**AI Chatbot:**\n"
                    "`!ai`, `!toggle_ai`, `!ai_settings`\n\n"
                    "**Owner Management:**\n"
                    "`!commands`, `!blacklist`, `!guilds`\n"
                    "`!eval`, `!restart` (if implemented)"
                ),
                inline=False
            )
            
            embed.add_field(
                name="👑 Administrator Commands",
                value=(
                    "**Staff Management:**\n"
                    "`!flag`, `!unflag`, `!terminate`, `!stafflist`\n"
                    "`!adminsetup`, `!lockchannels`, `!unlockchannels`\n\n"
                    "**Moderation:**\n"
                    "`!warn`, `!mute`, `!kick`, `!ban`\n"
                    "`!wm`, `!wmr` (with undo buttons)\n"
                    "`!masskick`, `!massban`, `!massmute`\n"
                    "`!imprison`, `!release`\n\n"
                    "**Role Management:**\n"
                    "`!role`, `!removerole`\n"
                    "`!temprole`, `!removetemp`\n"
                    "`!persistrole`, `!removepersist`\n\n"
                    "**Channel Management:**\n"
                    "`!checkslowmode`, `!setslowmode`\n"
                    "`!massslow`, `!lockchannels`, `!unlockchannels`\n\n"
                    "**Information:**\n"
                    "`!setup`, `!adminsetup`, `!members`"
                ),
                inline=False
            )
            
            embed.add_field(
                name="🛡️ Senior Moderator Commands",
                value=(
                    "**Enhanced Moderation:**\n"
                    "`!wm` (warn + mute)\n"
                    "`!wmr` (reply-based warn + mute)\n"
                    "`!masskick`, `!massban`, `!massmute`\n"
                    "`!massrole`, `!massremoverole`\n"
                    "`!masstemprole`, `!massremovetemp`\n"
                    "`!masspersistrole`, `!massremovepersist`\n\n"
                    "**Role Management:**\n"
                    "`!temprole`, `!removetemp`\n"
                    "`!persistrole`, `!removepersist`\n\n"
                    "**Advanced Moderation:**\n"
                    "`!imprison`, `!release`"
                ),
                inline=False
            )
            
            embed.add_field(
                name="👮 Moderator Commands",
                value=(
                    "**Basic Moderation:**\n"
                    "`!warn`, `!delwarn`\n"
                    "`!mute`, `!unmute`\n"
                    "`!kick`, `!ban`, `!unban`\n\n"
                    "**Information:**\n"
                    "`!warnings`, `!modlogs`\n"
                    "`!userinfo`, `!serverinfo`\n"
                    "`!checkavatar`, `!checkbanner`\n\n"
                    "**Role Management:**\n"
                    "`!role`, `!removerole`\n\n"
                    "**Channel Info:**\n"
                    "`!checkslowmode`"
                ),
                inline=False
            )
            
            embed.add_field(
                name="👤 Everyone Commands",
                value=(
                    "**Information:**\n"
                    "`!help`, `!ping`\n"
                    "`!myinfo`, `!mywarns`\n\n"
                    "**AI Chatbot:**\n"
                    "`!ai` (if enabled)\n"
                    "Mentions: `@Vertigo` (if enabled)\n\n"
                    "**Server Info:**\n"
                    "`!serverinfo`, `!members`"
                ),
                inline=False
            )
            
            embed.add_field(
                name="🔧 Setup & Configuration",
                value=(
                    "**Server Setup:**\n"
                    "`!setup` - Configure basic server settings\n"
                    "`!adminsetup` - Configure admin settings\n\n"
                    "**AI Configuration:**\n"
                    "`!ai_settings` - Configure AI chatbot\n"
                    "`!toggle_ai` - Enable/disable AI\n\n"
                    "**Timeout System:**\n"
                    "`!timeoutpanel` - Manage prohibited terms\n\n"
                    "**Channel Configuration:**\n"
                    "`!lockchannels`, `!unlockchannels`"
                ),
                inline=False
            )
            
            embed.add_field(
                name="🎮 AI Features",
                value=(
                    "**AI Chatbot:**\n"
                    "`!ai [question]` - Ask AI anything\n"
                    "Mentions work automatically\n\n"
                    "**AI Moderation:**\n"
                    "`!aitarget` - Target users for AI roasting\n"
                    "`!aiflag` - Flag staff with AI approval\n\n"
                    "**AI Settings:**\n"
                    "Three personalities: Gen-Z, Professional, Funny\n"
                    "Rate limited and safety features included\n\n"
                    "**Targeting System:**\n"
                    "30% chance to roast targeted users\n"
                    "10% chance for fake moderation actions"
                ),
                inline=False
            )
            
            embed.add_field(
                name="⚠️ Important Notes",
                value=(
                    "**Undo Buttons:**\n"
                    "• Only work for 5 minutes\n"
                    "• Only the person who performed the action can use them\n"
                    "• All undo actions are logged to modlogs\n\n"
                    "**AI Safety:**\n"
                    "• Rate limited (1 request per 5 seconds)\n"
                    "• Character limit (200 chars)\n"
                    "• Content filtering and timeout protection\n\n"
                    "**Timeout System:**\n"
                    "• Staff are immune (all configured roles)\n"
                    "• Real-time phrase detection\n"
                    "• Alert system with action buttons\n\n"
                    "**Blacklist System:**\n"
                    "• Completely blocks bot usage\n"
                    "• Works even for administrators\n"
                    "• Only removable by bot owner"
                ),
                inline=False
            )
            
            # Add footer with bot info
            embed.set_footer(
                text=f"{config.BOT_NAME} v2.0 | "
                      f"Prefix: ! | "
                      f"Owner: <@{config.OWNER_ID}> | "
                      f"Use !help for basic commands"
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error("Commands list error: %s", e)
            embed = make_embed(
                action="error",
                title="Error",
                description="Failed to load command list."
            )
            await ctx.send(embed=embed)
    
    @commands.command(name="guilds")
    @require_owner()
    async def guilds(self, ctx: commands.Context) -> None:
        """List all guilds the bot is in."""
        try:
            if not self.bot.guilds:
                embed = make_embed(
                    action="owner",
                    title="🌐 Connected Guilds",
                    description="Bot is not connected to any guilds."
                )
                await ctx.send(embed=embed)
                return
            
            embed = make_embed(
                action="owner",
                title="🌐 Connected Guilds",
                description=f"Bot is connected to {len(self.bot.guilds)} guilds:"
            )
            
            for guild in self.bot.guilds:
                member_count = guild.member_count if guild.member_count else "Unknown"
                embed.add_field(
                    name=guild.name,
                    value=(
                        f"**ID:** `{guild.id}`\n"
                        f"**Members:** {member_count}\n"
                        f"**Owner:** <@{guild.owner_id}>\n"
                        f"**Created:** {guild.created_at.strftime('%Y-%m-%d')}\n"
                        f"**Joined:** {guild.me.joined_at.strftime('%Y-%m-%d') if guild.me.joined_at else 'Unknown'}"
                    ),
                    inline=True
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error("Guilds list error: %s", e)
            embed = make_embed(
                action="error",
                title="Error",
                description="Failed to load guild list."
            )
            await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    """Load the owner commands cog."""
    await bot.add_cog(OwnerCommandsCog(bot))