"""Owner-only commands."""

from __future__ import annotations

import asyncio
import logging

import discord
from discord.ext import commands

from vertigo.database import Database
from vertigo.helpers import make_embed, require_owner, safe_dm

logger = logging.getLogger(__name__)


class OwnerCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.start_time = discord.utils.utcnow()

    @property
    def db(self) -> Database:
        return self.bot.db  # type: ignore[attr-defined]

    @commands.command(name="dmuser")
    @require_owner()
    async def dmuser(self, ctx: commands.Context, user: discord.User, *, message: str) -> None:
        await safe_dm(user, content=message)
        embed = make_embed(action="success", title="DM Sent", description=f"Sent a DM to {user}.")
        await ctx.send(embed=embed)

    @commands.command(name="waketime")
    @require_owner()
    async def waketime(self, ctx: commands.Context) -> None:
        delta = discord.utils.utcnow() - self.start_time
        days = delta.days
        hours, rem = divmod(delta.seconds, 3600)
        minutes, _ = divmod(rem, 60)
        embed = make_embed(action="waketime", title="Uptime", description=f"{days} days, {hours} hours, {minutes} minutes")
        await ctx.send(embed=embed)

    @commands.command(name="banguild")
    @require_owner()
    async def banguild(self, ctx: commands.Context, guild_id: int, *, reason: str | None = None) -> None:
        await self.db.blacklist_guild(guild_id=guild_id, reason=reason)
        guild = self.bot.get_guild(guild_id)
        if guild:
            await guild.leave()
        embed = make_embed(action="ban", title="Guild Blacklisted", description=f"Blacklisted guild `{guild_id}`.")
        await ctx.send(embed=embed)

    @commands.command(name="unbanguild")
    @require_owner()
    async def unbanguild(self, ctx: commands.Context, guild_id: int) -> None:
        await self.db.unblacklist_guild(guild_id=guild_id)
        embed = make_embed(action="unban", title="Guild Unblacklisted", description=f"Removed guild `{guild_id}` from blacklist.")
        await ctx.send(embed=embed)

    @commands.command(name="checkguild")
    @require_owner()
    async def checkguild(self, ctx: commands.Context, guild_id: int) -> None:
        guild = self.bot.get_guild(guild_id)
        if not guild:
            embed = make_embed(action="checkguild", title="Guild", description="Bot is not in that guild.")
            await ctx.send(embed=embed)
            return
        embed = make_embed(action="checkguild", title="Guild", description=f"{guild.name} (`{guild.id}`)")
        embed.add_field(name="Members", value=str(guild.member_count or len(guild.members)), inline=True)
        embed.add_field(name="Owner", value=f"{guild.owner} ({guild.owner_id})", inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="guildlist")
    @require_owner()
    async def guildlist(self, ctx: commands.Context) -> None:
        lines = [f"{g.name} (`{g.id}`) - {g.member_count or len(g.members)} members" for g in self.bot.guilds]
        description = "\n".join(lines[:50]) or "None"
        embed = make_embed(action="guildlist", title="Guild List", description=description)
        await ctx.send(embed=embed)

    @commands.command(name="nuke")
    @commands.guild_only()
    @require_owner()
    async def nuke(self, ctx: commands.Context, channel: discord.TextChannel | None = None) -> None:
        channel = channel or ctx.channel  # type: ignore[assignment]
        if not isinstance(channel, discord.TextChannel):
            return

        confirm = await ctx.send("React with ✅ to confirm nuking this channel.")
        await confirm.add_reaction("✅")

        def check(reaction: discord.Reaction, user: discord.User) -> bool:
            return reaction.message.id == confirm.id and str(reaction.emoji) == "✅" and user.id == ctx.author.id

        try:
            await self.bot.wait_for("reaction_add", check=check, timeout=30)
        except asyncio.TimeoutError:
            await confirm.edit(content="Timed out.")
            return

        deleted = 0
        while True:
            batch = await channel.purge(limit=100)
            deleted += len(batch)
            if len(batch) < 100:
                break

        embed = make_embed(action="success", title="Nuke Complete", description=f"Deleted **{deleted}** messages.")
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(OwnerCog(bot))
