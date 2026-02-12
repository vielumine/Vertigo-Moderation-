"""Utility commands for Luna - Announce, Poll, Define, Translate, Ask AI, Reminders."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

import config
from database import Database
from helpers import (
    make_embed,
    require_level,
    require_admin,
    safe_delete,
    parse_duration,
    humanize_seconds,
    get_ai_response,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UtilityCog(commands.Cog):
    """Utility commands for server management and helpers."""
    
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
    
    @property
    def db(self) -> Database:
        return self.bot.db  # type: ignore[attr-defined]
    
    @commands.command(name="announce")
    @commands.guild_only()
    @require_admin()
    async def announce(self, ctx: commands.Context, channel: discord.TextChannel, *, message: str) -> None:
        """Send an announcement to a channel (Admin only).
        
        Usage:
        ,announce #channel message
        """
        embed = make_embed(
            action="announce",
            title="📢 Announcement",
            description=message
        )
        embed.set_footer(text=f"Announced by {ctx.author}")
        
        await channel.send(embed=embed)
        
        confirm = make_embed(
            action="success",
            title="✅ Announcement Sent",
            description=f"Message sent to {channel.mention}"
        )
        await ctx.send(embed=confirm)
        await safe_delete(ctx.message)
    
    @commands.command(name="poll")
    @commands.guild_only()
    @require_level("moderator")
    async def poll(self, ctx: commands.Context, *, question: str) -> None:
        """Create a quick yes/no poll (Staff+ only).
        
        Usage:
        ,poll Question here?
        """
        embed = make_embed(
            action="poll",
            title="📊 Poll",
            description=question
        )
        embed.set_footer(text=f"Poll by {ctx.author}")
        
        poll_msg = await ctx.send(embed=embed)
        await poll_msg.add_reaction("✅")
        await poll_msg.add_reaction("❌")
        
        await safe_delete(ctx.message)
    
    @commands.command(name="define")
    @commands.guild_only()
    async def define(self, ctx: commands.Context, *, word: str) -> None:
        """Get AI definition of a word.
        
        Usage:
        ,define word
        """
        try:
            prompt = f"Define the word '{word}' in a concise way (under 150 characters). Be professional and clear."
            definition = await get_ai_response(prompt, "professional")
            
            embed = make_embed(
                action="define",
                title=f"📖 Definition: {word.title()}",
                description=definition
            )
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Define error: {e}")
            embed = make_embed(
                action="error",
                title="❌ Error",
                description="Failed to get definition."
            )
            await ctx.send(embed=embed)
    
    @commands.command(name="askai")
    @commands.guild_only()
    async def askai(self, ctx: commands.Context, *, question: str) -> None:
        """Ask Luna AI a question directly.
        
        Usage:
        ,askai What is Discord?
        """
        try:
            response = await get_ai_response(question, "professional")
            
            embed = make_embed(
                action="askai",
                title="🌙 Luna AI",
                description=response
            )
            await ctx.reply(embed=embed)
            
        except Exception as e:
            logger.error(f"Ask AI error: {e}")
            embed = make_embed(
                action="error",
                title="❌ Error",
                description="Failed to get AI response."
            )
            await ctx.send(embed=embed)
    
    @commands.command(name="remindme")
    @commands.guild_only()
    async def remindme(self, ctx: commands.Context, duration: str, *, text: str) -> None:
        """Set a reminder.
        
        Usage:
        ,remindme 1h Do something
        ,remindme 30m Check on task
        """
        try:
            seconds = parse_duration(duration)
            expiration = utcnow() + timedelta(seconds=seconds)
            
            await self.db.add_reminder(
                user_id=ctx.author.id,
                guild_id=ctx.guild.id,
                text=text,
                expiration_ts=expiration.isoformat()
            )
            
            embed = make_embed(
                action="success",
                title="✅ Reminder Set",
                description=f"I'll remind you in **{humanize_seconds(seconds)}**\n\n**Message:** {text}"
            )
            await ctx.send(embed=embed)
            
        except ValueError:
            embed = make_embed(
                action="error",
                title="❌ Invalid Duration",
                description="Use format: `1h`, `30m`, `1d`, etc."
            )
            await ctx.send(embed=embed)
    
    @commands.command(name="reminders")
    @commands.guild_only()
    async def reminders(self, ctx: commands.Context) -> None:
        """List your active reminders.
        
        Usage:
        ,reminders
        """
        reminders = await self.db.get_active_reminders(ctx.author.id)
        
        if not reminders:
            embed = make_embed(
                action="reminder",
                title="⏰ Your Reminders",
                description="You have no active reminders."
            )
            await ctx.send(embed=embed)
            return
        
        description = ""
        for reminder in reminders:
            description += f"**ID {reminder['id']}** - <t:{int(datetime.fromisoformat(reminder['expiration_ts']).timestamp())}:R>\n"
            description += f"{reminder['text']}\n\n"
        
        embed = make_embed(
            action="reminder",
            title="⏰ Your Active Reminders",
            description=description.strip()
        )
        embed.set_footer(text="Use ,deleteremind <id> to remove a reminder")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="deleteremind", aliases=["delreminder", "removeremind"])
    @commands.guild_only()
    async def deleteremind(self, ctx: commands.Context, reminder_id: int) -> None:
        """Delete a reminder by ID.
        
        Usage:
        ,deleteremind 1
        """
        success = await self.db.delete_reminder(reminder_id, ctx.author.id)
        
        if success:
            embed = make_embed(
                action="success",
                title="✅ Reminder Deleted",
                description=f"Reminder #{reminder_id} has been removed."
            )
        else:
            embed = make_embed(
                action="error",
                title="❌ Not Found",
                description=f"Reminder #{reminder_id} not found or doesn't belong to you."
            )
        
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(UtilityCog(bot))
