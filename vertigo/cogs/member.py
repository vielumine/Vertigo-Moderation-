"""Member self-service commands."""

from __future__ import annotations

import logging

import discord
from discord.ext import commands

from database import Database
from helpers import commands_channel_check, make_embed

logger = logging.getLogger(__name__)


class MemberCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @property
    def db(self) -> Database:
        return self.bot.db  # type: ignore[attr-defined]

    @commands.command(name="mywarns")
    @commands.guild_only()
    @commands_channel_check()
    async def mywarns(self, ctx: commands.Context) -> None:
        rows = await self.db.get_active_warnings(guild_id=ctx.guild.id, user_id=ctx.author.id)  # type: ignore[union-attr]
        if not rows:
            embed = make_embed(action="mywarns", title="⚠️ Your Warnings", description="You have no active warnings.")
            await ctx.send(embed=embed)
            return

        embed = make_embed(action="mywarns", title="⚠️ Your Active Warnings")
        for row in rows[:10]:
            embed.add_field(name=f"📍 ID {row['id']}", value=f"📝 Reason: {row['reason']}\n⏱️ Expires: {row['expires_at']}", inline=False)

        await ctx.send(embed=embed)

    @commands.command(name="myavatar")
    @commands.guild_only()
    @commands_channel_check()
    async def myavatar(self, ctx: commands.Context) -> None:
        user = ctx.author
        embed = make_embed(action="myavatar", title="🖼️ Your Avatar")
        embed.set_image(url=user.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.command(name="mybanner")
    @commands.guild_only()
    @commands_channel_check()
    async def mybanner(self, ctx: commands.Context) -> None:
        fetched = await self.bot.fetch_user(ctx.author.id)
        banner_url = fetched.banner.url if fetched.banner else None
        embed = make_embed(action="mybanner", title="🖼️ Your Banner")
        if banner_url:
            embed.set_image(url=banner_url)
            embed.add_field(name="🔗 URL", value=banner_url, inline=False)
        else:
            embed.description = "You have no banner."
        await ctx.send(embed=embed)

    @commands.command(name="myinfo")
    @commands.guild_only()
    @commands_channel_check()
    async def myinfo(self, ctx: commands.Context) -> None:
        if not isinstance(ctx.author, discord.Member):
            return
        member = ctx.author
        roles = [r.mention for r in member.roles if r != ctx.guild.default_role]
        embed = make_embed(action="myinfo", title="👤 Your Information")
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="📍 ID", value=str(member.id), inline=True)
        embed.add_field(name="📅 Account Created", value=discord.utils.format_dt(member.created_at), inline=False)
        embed.add_field(name="📅 Joined Server", value=discord.utils.format_dt(member.joined_at) if member.joined_at else "Unknown", inline=False)
        embed.add_field(name="📌 Roles", value=", ".join(roles) if roles else "None", inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="afk")
    @commands.guild_only()
    async def afk(self, ctx: commands.Context, *, reason: str | None = None) -> None:
        """Set yourself as AFK with an optional reason.
        
        Usage: !afk [reason]
        """
        await self.db.set_afk(user_id=ctx.author.id, guild_id=ctx.guild.id, reason=reason)
        
        reason_text = f" - {reason}" if reason else ""
        embed = make_embed(
            action="success",
            title="💤 AFK Status Set",
            description=f"You are now AFK{reason_text}\n\nYou'll be notified of any pings when you return."
        )
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MemberCog(bot))
