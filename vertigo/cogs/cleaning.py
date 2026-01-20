"""Cleaning commands (purge, clean, purgeuser, purgematch)."""

from __future__ import annotations

import logging

import discord
from discord.ext import commands

from vertigo.helpers import commands_channel_check, make_embed, require_level, safe_delete

logger = logging.getLogger(__name__)


class CleaningCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command(name="clean")
    @commands.guild_only()
    @commands_channel_check()
    @require_level("moderator")
    async def clean(self, ctx: commands.Context, amount: int = 50) -> None:
        """Delete the bot's messages only."""

        if amount <= 0:
            amount = 1
        deleted = 0
        async for msg in ctx.channel.history(limit=amount):  # type: ignore[union-attr]
            if msg.author.id == self.bot.user.id:  # type: ignore[union-attr]
                try:
                    await msg.delete()
                    deleted += 1
                except Exception:
                    continue

        embed = make_embed(action="clean", title="🧹 Bot Messages Cleaned", description=f"Deleted **{deleted}** bot messages.")
        await ctx.send(embed=embed, delete_after=5)
        await safe_delete(ctx.message)

    @commands.command(name="purge")
    @commands.guild_only()
    @commands_channel_check()
    @require_level("moderator")
    async def purge(self, ctx: commands.Context, amount: int) -> None:
        """Delete the last N messages."""

        if amount <= 0:
            embed = make_embed(action="error", title="Invalid Amount", description="Amount must be > 0.")
            await ctx.send(embed=embed)
            return

        try:
            deleted = await ctx.channel.purge(limit=amount + 1)  # type: ignore[union-attr]
        except discord.Forbidden:
            embed = make_embed(action="error", title="❌ Missing Permissions", description="I can't delete messages here.")
            await ctx.send(embed=embed)
            return

        embed = make_embed(action="purge", title="🧹 Messages Purged", description=f"Deleted **{len(deleted) - 1}** messages.")
        await ctx.send(embed=embed, delete_after=5)

    @commands.command(name="purgeuser")
    @commands.guild_only()
    @commands_channel_check()
    @require_level("moderator")
    async def purgeuser(self, ctx: commands.Context, member: discord.Member, amount: int) -> None:
        """Delete the user's last N messages."""

        if amount <= 0:
            embed = make_embed(action="error", title="Invalid Amount", description="Amount must be > 0.")
            await ctx.send(embed=embed)
            return

        def check(m: discord.Message) -> bool:
            return m.author.id == member.id

        try:
            deleted = await ctx.channel.purge(limit=amount * 5, check=check)  # type: ignore[union-attr]
        except discord.Forbidden:
            embed = make_embed(action="error", title="❌ Missing Permissions", description="I can't delete messages here.")
            await ctx.send(embed=embed)
            return

        embed = make_embed(action="purgeuser", title="🧹 User Messages Purged", description=f"Deleted **{len(deleted)}** messages from {member.mention}.")
        await ctx.send(embed=embed, delete_after=5)
        await safe_delete(ctx.message)

    @commands.command(name="purgematch")
    @commands.guild_only()
    @commands_channel_check()
    @require_level("moderator")
    async def purgematch(self, ctx: commands.Context, keyword: str, amount: int) -> None:
        """Delete messages containing a keyword."""

        if amount <= 0:
            embed = make_embed(action="error", title="Invalid Amount", description="Amount must be > 0.")
            await ctx.send(embed=embed)
            return

        keyword_lower = keyword.lower()

        def check(m: discord.Message) -> bool:
            return keyword_lower in (m.content or "").lower()

        try:
            deleted = await ctx.channel.purge(limit=amount * 5, check=check)  # type: ignore[union-attr]
        except discord.Forbidden:
            embed = make_embed(action="error", title="❌ Missing Permissions", description="I can't delete messages here.")
            await ctx.send(embed=embed)
            return

        embed = make_embed(action="purgematch", title="🧹 Keyword Purge Complete", description=f"Deleted **{len(deleted)}** messages containing `{keyword}`.")
        await ctx.send(embed=embed, delete_after=5)
        await safe_delete(ctx.message)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(CleaningCog(bot))
