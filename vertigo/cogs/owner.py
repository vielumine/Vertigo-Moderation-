"""Owner-only commands."""

from __future__ import annotations

import asyncio
import logging

import discord
from discord.ext import commands

from database import Database
from helpers import make_embed, require_owner, safe_dm

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
        embed = make_embed(action="success", title="✉️ Direct Message Sent", description=f"Sent a DM to 👤 {user}.")
        await ctx.send(embed=embed)

    @commands.command(name="waketime")
    @require_owner()
    async def waketime(self, ctx: commands.Context) -> None:
        delta = discord.utils.utcnow() - self.start_time
        days = delta.days
        hours, rem = divmod(delta.seconds, 3600)
        minutes, _ = divmod(rem, 60)
        embed = make_embed(action="waketime", title="⏱️ Bot Uptime", description=f"{days} days, {hours} hours, {minutes} minutes")
        await ctx.send(embed=embed)

    @commands.command(name="banguild")
    @require_owner()
    async def banguild(self, ctx: commands.Context, guild_id: int, *, reason: str | None = None) -> None:
        await self.db.blacklist_guild(guild_id=guild_id, reason=reason)
        guild = self.bot.get_guild(guild_id)
        if guild:
            await guild.leave()
        embed = make_embed(action="ban", title="🚫 Guild Banned", description=f"Blacklisted guild `{guild_id}`.")
        await ctx.send(embed=embed)

    @commands.command(name="unbanguild")
    @require_owner()
    async def unbanguild(self, ctx: commands.Context, guild_id: int) -> None:
        await self.db.unblacklist_guild(guild_id=guild_id)
        embed = make_embed(action="unban", title="✅ Guild Unbanned", description=f"Removed guild `{guild_id}` from blacklist.")
        await ctx.send(embed=embed)

    @commands.command(name="checkguild")
    @require_owner()
    async def checkguild(self, ctx: commands.Context, guild_id: int) -> None:
        guild = self.bot.get_guild(guild_id)
        if not guild:
            embed = make_embed(action="checkguild", title="🔍 Guild Check", description="Bot is not in that guild.")
            await ctx.send(embed=embed)
            return
        embed = make_embed(action="checkguild", title="🔍 Guild Check", description=f"{guild.name} (`{guild.id}`)")
        embed.add_field(name="👥 Members", value=str(guild.member_count or len(guild.members)), inline=True)
        embed.add_field(name="👑 Owner", value=f"{guild.owner} ({guild.owner_id})", inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="guildlist")
    @require_owner()
    async def guildlist(self, ctx: commands.Context) -> None:
        lines = [f"{g.name} (`{g.id}`) - {g.member_count or len(g.members)} members" for g in self.bot.guilds]
        description = "\n".join(lines[:50]) or "None"
        embed = make_embed(action="guildlist", title="📍 Guild List", description=description)
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

        # Add loading reaction for long-running operation
        await confirm.add_reaction("🔃")

        deleted = 0
        while True:
           batch = await channel.purge(limit=100)
           deleted += len(batch)
           if len(batch) < 100:
               break

        embed = make_embed(action="success", title="💣 Channel Nuked", description=f"Deleted **{deleted}** messages.")
        await ctx.send(embed=embed)
    
    @commands.command(name="setbotav")
    @require_owner()
    async def set_bot_avatar(self, ctx: commands.Context, url: str | None = None) -> None:
        """Set bot avatar from URL or attachment.
        
        Usage: !setbotav <url> or attach an image
        """
        try:
            if url:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as resp:
                        if resp.status != 200:
                            embed = make_embed(action="error", title="❌ Error", description="Failed to download image from URL.")
                            await ctx.send(embed=embed)
                            return
                        avatar_bytes = await resp.read()
            elif ctx.message.attachments:
                avatar_bytes = await ctx.message.attachments[0].read()
            else:
                embed = make_embed(action="error", title="❌ Error", description="Provide a URL or attach an image.")
                await ctx.send(embed=embed)
                return
            
            await self.bot.user.edit(avatar=avatar_bytes)
            embed = make_embed(action="success", title="✅ Avatar Updated", description="Bot avatar has been updated successfully.")
            await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"Failed to set avatar: {e}")
            embed = make_embed(action="error", title="❌ Error", description=f"Failed to set avatar: {e}")
            await ctx.send(embed=embed)
    
    @commands.command(name="setbotbanner")
    @require_owner()
    async def set_bot_banner(self, ctx: commands.Context, url: str | None = None) -> None:
        """Set bot banner from URL or attachment.
        
        Usage: !setbotbanner <url> or attach an image
        """
        try:
            if url:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as resp:
                        if resp.status != 200:
                            embed = make_embed(action="error", title="❌ Error", description="Failed to download image from URL.")
                            await ctx.send(embed=embed)
                            return
                        banner_bytes = await resp.read()
            elif ctx.message.attachments:
                banner_bytes = await ctx.message.attachments[0].read()
            else:
                embed = make_embed(action="error", title="❌ Error", description="Provide a URL or attach an image.")
                await ctx.send(embed=embed)
                return
            
            await self.bot.user.edit(banner=banner_bytes)
            embed = make_embed(action="success", title="✅ Banner Updated", description="Bot banner has been updated successfully.")
            await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"Failed to set banner: {e}")
            embed = make_embed(action="error", title="❌ Error", description=f"Failed to set banner: {e}")
            await ctx.send(embed=embed)
    
    @commands.command(name="setbotname")
    @require_owner()
    async def set_bot_name(self, ctx: commands.Context, *, name: str) -> None:
        """Set bot's display name.
        
        Usage: !setbotname <name>
        """
        try:
            await self.bot.user.edit(username=name)
            embed = make_embed(action="success", title="✅ Name Updated", description=f"Bot name changed to **{name}**.")
            await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"Failed to set name: {e}")
            embed = make_embed(action="error", title="❌ Error", description=f"Failed to set name: {e}")
            await ctx.send(embed=embed)
    
    @commands.command(name="setstatus")
    @require_owner()
    async def set_status(self, ctx: commands.Context, status: str) -> None:
        """Set bot status.
        
        Usage: !setstatus <online/idle/dnd/invisible>
        """
        status_map = {
            "online": discord.Status.online,
            "idle": discord.Status.idle,
            "dnd": discord.Status.dnd,
            "invisible": discord.Status.invisible
        }
        
        if status.lower() not in status_map:
            embed = make_embed(action="error", title="❌ Invalid Status", description="Valid options: online, idle, dnd, invisible")
            await ctx.send(embed=embed)
            return
        
        try:
            await self.bot.change_presence(status=status_map[status.lower()])
            embed = make_embed(action="success", title="✅ Status Updated", description=f"Status set to **{status}**.")
            await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"Failed to set status: {e}")
            embed = make_embed(action="error", title="❌ Error", description=f"Failed to set status: {e}")
            await ctx.send(embed=embed)
    
    @commands.command(name="setactivity")
    @require_owner()
    async def set_activity(self, ctx: commands.Context, activity_type: str, *, text: str) -> None:
        """Set bot activity.
        
        Usage: !setactivity <playing/watching/listening> <text>
        """
        activity_map = {
            "playing": discord.ActivityType.playing,
            "watching": discord.ActivityType.watching,
            "listening": discord.ActivityType.listening
        }
        
        if activity_type.lower() not in activity_map:
            embed = make_embed(action="error", title="❌ Invalid Activity", description="Valid options: playing, watching, listening")
            await ctx.send(embed=embed)
            return
        
        try:
            activity = discord.Activity(type=activity_map[activity_type.lower()], name=text)
            await self.bot.change_presence(activity=activity)
            embed = make_embed(action="success", title="✅ Activity Updated", description=f"Activity set to **{activity_type} {text}**.")
            await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"Failed to set activity: {e}")
            embed = make_embed(action="error", title="❌ Error", description=f"Failed to set activity: {e}")
            await ctx.send(embed=embed)

    # -------------------------------------------------------------------------
    # Owner Override Audit Commands
    # -------------------------------------------------------------------------

    @commands.command(name="overrideaudit")
    @require_owner()
    async def override_audit(self, ctx: commands.Context, guild_id: int | None = None, limit: int = 20) -> None:
        """View permission override audit logs.
        
        Usage: !overrideaudit [guild_id] [limit]
        """
        try:
            logs = await self.db.get_override_logs(
                guild_id=guild_id,
                limit=min(limit, 100)  # Max 100 entries
            )
            
            if not logs:
                embed = make_embed(
                    action="overrideaudit",
                    title="📋 Override Audit Log",
                    description="No override logs found."
                )
                await ctx.send(embed=embed)
                return
            
            embed = make_embed(
                action="overrideaudit",
                title=f"📋 Override Audit Log ({len(logs)} entries)",
                description="Recent owner immunity overrides:"
            )
            
            for log in logs[:10]:  # Show up to 10 in embed
                guild = self.bot.get_guild(log.guild_id)
                guild_name = guild.name if guild else f"Unknown ({log.guild_id})"
                
                target_str = f"<@{log.target_user_id}>" if log.target_user_id else "N/A"
                
                value = (
                    f"**Guild:** {guild_name}\n"
                    f"**Target:** {target_str}\n"
                    f"**Action:** {log.action_type}\n"
                    f"**Reason:** {log.reason or 'No reason provided'}\n"
                    f"**Time:** {log.timestamp[:19]}"
                )
                
                embed.add_field(
                    name=f"Override #{log.id}",
                    value=value,
                    inline=False
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Failed to get override audit: {e}")
            embed = make_embed(action="error", title="❌ Error", description=f"Failed to retrieve audit logs: {e}")
            await ctx.send(embed=embed)

    @commands.command(name="overridestats")
    @require_owner()
    async def override_stats(self, ctx: commands.Context, days: int = 30) -> None:
        """Show permission override statistics.
        
        Usage: !overridestats [days]
        """
        try:
            stats = await self.db.get_override_stats(days=days)
            
            embed = make_embed(
                action="overridestats",
                title=f"📊 Override Statistics (Past {days} days)",
                description=f"**Total Overrides:** {stats['total']}"
            )
            
            if stats['by_action']:
                action_breakdown = "\n".join(
                    f"• {action}: {count}"
                    for action, count in sorted(stats['by_action'].items(), key=lambda x: x[1], reverse=True)
                )
                embed.add_field(
                    name="By Action Type",
                    value=action_breakdown or "No data",
                    inline=False
                )
            
            if stats['by_executor']:
                executor_breakdown = "\n".join(
                    f"• <@{executor_id}>: {count}"
                    for executor_id, count in sorted(stats['by_executor'].items(), key=lambda x: x[1], reverse=True)
                )
                embed.add_field(
                    name="By Executor",
                    value=executor_breakdown or "No data",
                    inline=False
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Failed to get override stats: {e}")
            embed = make_embed(action="error", title="❌ Error", description=f"Failed to retrieve statistics: {e}")
            await ctx.send(embed=embed)

    @commands.command(name="overrideguilds")
    @require_owner()
    async def override_guilds(self, ctx: commands.Context) -> None:
        """Show guilds with permission overrides.
        
        Usage: !overrideguilds
        """
        try:
            guilds = await self.db.get_guilds_with_overrides()
            
            if not guilds:
                embed = make_embed(
                    action="overrideguilds",
                    title="🏰 Guilds with Overrides",
                    description="No guilds have recorded permission overrides."
                )
                await ctx.send(embed=embed)
                return
            
            lines = []
            for g in guilds[:20]:  # Show top 20
                guild = self.bot.get_guild(g['guild_id'])
                guild_name = guild.name if guild else f"Unknown ({g['guild_id']})"
                lines.append(
                    f"• **{guild_name}** - {g['override_count']} overrides (last: {g['last_override'][:10]})"
                )
            
            embed = make_embed(
                action="overrideguilds",
                title=f"🏰 Guilds with Overrides ({len(guilds)} total)",
                description="\n".join(lines) if lines else "No data"
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Failed to get override guilds: {e}")
            embed = make_embed(action="error", title="❌ Error", description=f"Failed to retrieve guild list: {e}")
            await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(OwnerCog(bot))
