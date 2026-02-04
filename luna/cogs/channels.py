"""Channel management commands (slowmode, lock, messaging utilities)."""

from __future__ import annotations

import logging

import discord
from discord.ext import commands

from helpers import (
    add_loading_reaction,
    commands_channel_check,
    extract_id,
    make_embed,
    parse_duration,
    require_level,
    safe_delete,
)

logger = logging.getLogger(__name__)


class ChannelsCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command(name="checkslowmode")
    @commands.guild_only()
    @commands_channel_check()
    @require_level("moderator")
    async def checkslowmode(self, ctx: commands.Context, channel: discord.TextChannel | None = None) -> None:
        channel = channel or ctx.channel  # type: ignore[assignment]
        if not isinstance(channel, discord.TextChannel):
            return
        delay = channel.slowmode_delay
        value = f"{delay}s" if delay else "None"
        embed = make_embed(action="checkslowmode", title="⏱️ Slowmode Check", description=f"{channel.mention}: **{value}**")
        await ctx.send(embed=embed)

    @commands.command(name="setslowmode")
    @commands.guild_only()
    @commands_channel_check()
    @require_level("senior_mod")
    async def setslowmode(self, ctx: commands.Context, arg1: str, arg2: str | None = None) -> None:
        """Set slowmode.

        Usage:
        - !setslowmode <duration>
        - !setslowmode <channel> <duration>
        """

        channel: discord.TextChannel | None
        duration: str

        if arg2 is None:
            channel = ctx.channel if isinstance(ctx.channel, discord.TextChannel) else None
            duration = arg1
        else:
            channel_id = extract_id(arg1) or (int(arg1) if arg1.isdigit() else None)
            channel = ctx.guild.get_channel(channel_id) if channel_id and ctx.guild else None  # type: ignore[union-attr]
            duration = arg2

        if not isinstance(channel, discord.TextChannel):
            embed = make_embed(action="error", title="Invalid Channel", description="Channel not found.")
            await ctx.send(embed=embed)
            return

        seconds = parse_duration(duration)
        if seconds > 21600:
            embed = make_embed(action="error", title="Too Long", description="Max slowmode is 6 hours (21600s).")
            await ctx.send(embed=embed)
            return

        try:
            await channel.edit(slowmode_delay=seconds, reason=f"Slowmode set by {ctx.author}")
        except discord.Forbidden:
            embed = make_embed(action="error", title="❌ Missing Permissions", description="I can't edit that channel.")
            await ctx.send(embed=embed)
            return

        embed = make_embed(action="setslowmode", title="⏱️ Slowmode Updated", description=f"{channel.mention} slowmode set to **{seconds}s**")
        await ctx.send(embed=embed)
        await safe_delete(ctx.message)

    @commands.command(name="massslow")
    @commands.guild_only()
    @commands_channel_check()
    @require_level("head_mod")
    async def massslow(self, ctx: commands.Context, channels: str, duration: str) -> None:
        seconds = parse_duration(duration)
        if seconds > 21600:
            embed = make_embed(action="error", title="❌ Too Long", description="Max slowmode is 6 hours (21600s).")
            await ctx.send(embed=embed)
            return

        # Add loading reaction for long-running operation
        await add_loading_reaction(ctx.message)

        ok = 0
        failed = 0
        for part in channels.split(","):
            part = part.strip()
            if not part:
                continue
            channel_id = extract_id(part) or (int(part) if part.isdigit() else None)
            if channel_id is None:
                continue
            channel = ctx.guild.get_channel(channel_id)  # type: ignore[union-attr]
            if isinstance(channel, discord.TextChannel):
                try:
                    await channel.edit(slowmode_delay=seconds, reason=f"Mass slowmode by {ctx.author}")
                    ok += 1
                except Exception:
                    failed += 1

        embed = make_embed(action="massslow", title="⏱️ Mass Slowmode Results", description=f"⏱️ Set to **{seconds}s**\n✔️ Succeeded: **{ok}**\n❌ Failed: **{failed}**")
        await ctx.send(embed=embed)
        await safe_delete(ctx.message)

    @commands.command(name="lock")
    @commands.guild_only()
    @commands_channel_check()
    @require_level("head_mod")
    async def lock(self, ctx: commands.Context, channel: discord.TextChannel | None = None) -> None:
        channel = channel or ctx.channel  # type: ignore[assignment]
        if not isinstance(channel, discord.TextChannel):
            return

        overwrite = channel.overwrites_for(ctx.guild.default_role)  # type: ignore[union-attr]
        overwrite.send_messages = False
        try:
            await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite, reason=f"Locked by {ctx.author}")
        except discord.Forbidden:
            embed = make_embed(action="error", title="❌ Missing Permissions", description="I can't lock that channel.")
            await ctx.send(embed=embed)
            return

        embed = make_embed(action="lock", title="🔒 Channel Locked", description=f"Locked {channel.mention}.")
        await ctx.send(embed=embed)

    @commands.command(name="unlock")
    @commands.guild_only()
    @commands_channel_check()
    @require_level("head_mod")
    async def unlock(self, ctx: commands.Context, channel: discord.TextChannel | None = None) -> None:
        channel = channel or ctx.channel  # type: ignore[assignment]
        if not isinstance(channel, discord.TextChannel):
            return

        overwrite = channel.overwrites_for(ctx.guild.default_role)  # type: ignore[union-attr]
        overwrite.send_messages = None
        try:
            await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite, reason=f"Unlocked by {ctx.author}")
        except discord.Forbidden:
            embed = make_embed(action="error", title="❌ Missing Permissions", description="I can't unlock that channel.")
            await ctx.send(embed=embed)
            return

        embed = make_embed(action="unlock", title="🔓 Channel Unlocked", description=f"Unlocked {channel.mention}.")
        await ctx.send(embed=embed)

    @commands.command(name="hide")
    @commands.guild_only()
    @commands_channel_check()
    @require_level("head_mod")
    async def hide(self, ctx: commands.Context, channel: discord.TextChannel | None = None) -> None:
        channel = channel or ctx.channel  # type: ignore[assignment]
        if not isinstance(channel, discord.TextChannel):
            return

        overwrite = channel.overwrites_for(ctx.guild.default_role)  # type: ignore[union-attr]
        overwrite.view_channel = False
        try:
            await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite, reason=f"Hidden by {ctx.author}")
        except discord.Forbidden:
            embed = make_embed(action="error", title="Missing Permissions", description="I can't hide that channel.")
            await ctx.send(embed=embed)
            return

        embed = make_embed(action="hide", title="Channel Hidden", description=f"Hidden {channel.mention}.")
        await ctx.send(embed=embed)

    @commands.command(name="unhide")
    @commands.guild_only()
    @commands_channel_check()
    @require_level("head_mod")
    async def unhide(self, ctx: commands.Context, channel: discord.TextChannel | None = None) -> None:
        channel = channel or ctx.channel  # type: ignore[assignment]
        if not isinstance(channel, discord.TextChannel):
            return

        overwrite = channel.overwrites_for(ctx.guild.default_role)  # type: ignore[union-attr]
        overwrite.view_channel = None
        try:
            await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite, reason=f"Unhidden by {ctx.author}")
        except discord.Forbidden:
            embed = make_embed(action="error", title="Missing Permissions", description="I can't unhide that channel.")
            await ctx.send(embed=embed)
            return

        embed = make_embed(action="unhide", title="Channel Unhidden", description=f"Unhidden {channel.mention}.")
        await ctx.send(embed=embed)

    @commands.command(name="message")
    @commands.guild_only()
    @require_level("head_mod")
    async def message(self, ctx: commands.Context, channel: discord.TextChannel, *, message: str) -> None:
        """Send a plain text message to a channel.
        
        Works anywhere in the server.
        """
        try:
            await channel.send(content=message)
        except discord.Forbidden:
            embed = make_embed(action="error", title="Missing Permissions", description="I can't send messages there.")
            await ctx.send(embed=embed)
            return

        embed = make_embed(action="message", title="Message Sent", description=f"Sent message to {channel.mention}.")
        await ctx.send(embed=embed)
        await safe_delete(ctx.message)

    async def _fetch_message(self, ctx: commands.Context, message_id: int) -> discord.Message | None:
        try:
            return await ctx.channel.fetch_message(message_id)  # type: ignore[union-attr]
        except Exception:
            return None

    @commands.command(name="editmess")
    @commands.guild_only()
    @require_level("head_mod")
    async def editmess(self, ctx: commands.Context, message_id: int, *, new_message: str) -> None:
        """Edit a bot message in the current channel.
        
        Works anywhere in the server.
        """
        msg = await self._fetch_message(ctx, message_id)
        if msg is None or msg.author.id != self.bot.user.id:  # type: ignore[union-attr]
            embed = make_embed(action="error", title="Not Found", description="I can only edit my own messages in this channel.")
            await ctx.send(embed=embed)
            return

        await msg.edit(content=new_message)
        embed = make_embed(action="editmess", title="Message Edited", description=f"Edited message `{message_id}`.")
        await ctx.send(embed=embed)
        await safe_delete(ctx.message)

    @commands.command(name="replymess")
    @commands.guild_only()
    @require_level("head_mod")
    async def replymess(self, ctx: commands.Context, message_id: int, *, reply: str) -> None:
        """Reply to a message in the current channel.
        
        Works anywhere in the server.
        """
        msg = await self._fetch_message(ctx, message_id)
        if msg is None:
            embed = make_embed(action="error", title="Not Found", description="Message not found in this channel.")
            await ctx.send(embed=embed)
            return

        await msg.reply(content=reply, mention_author=True)
        embed = make_embed(action="replymess", title="Replied", description=f"Replied to message `{message_id}`.")
        await ctx.send(embed=embed)
        await safe_delete(ctx.message)

    @commands.command(name="deletemess")
    @commands.guild_only()
    @require_level("head_mod")
    async def deletemess(self, ctx: commands.Context, message_id: int) -> None:
        """Delete a bot message in the current channel.
        
        Works anywhere in the server.
        """
        msg = await self._fetch_message(ctx, message_id)
        if msg is None or msg.author.id != self.bot.user.id:  # type: ignore[union-attr]
            embed = make_embed(action="error", title="Not Found", description="I can only delete my own messages in this channel.")
            await ctx.send(embed=embed)
            return

        await msg.delete()
        embed = make_embed(action="deletemess", title="Message Deleted", description=f"Deleted message `{message_id}`.")
        await ctx.send(embed=embed)
        await safe_delete(ctx.message)

    @commands.command(name="reactmess")
    @commands.guild_only()
    @require_level("head_mod")
    async def reactmess(self, ctx: commands.Context, message_id: int, emoji: str) -> None:
        """React to a message with an emoji.
        
        Works anywhere in the server.
        Usage: !reactmess <message_id> <emoji>
        """
        msg = await self._fetch_message(ctx, message_id)
        if msg is None:
            embed = make_embed(action="error", title="Not Found", description="Message not found in this channel.")
            await ctx.send(embed=embed)
            return

        try:
            await msg.add_reaction(emoji)
            embed = make_embed(action="reactmess", title="✅ Reaction Added", description=f"Added {emoji} to message `{message_id}`.")
            await ctx.send(embed=embed)
            await safe_delete(ctx.message)
        except discord.HTTPException:
            embed = make_embed(action="error", title="❌ Invalid Emoji", description="That emoji is invalid or I don't have access to it.")
            await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ChannelsCog(bot))
