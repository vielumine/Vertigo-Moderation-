"""
Luna Bot Owner Cog
Owner-only commands for bot management and AI targeting.
"""

import discord
from discord.ext import commands
import asyncio

from database import (
    add_ai_target,
    remove_ai_target,
    get_active_ai_targets,
)
from helpers import (
    make_embed,
    get_embed_color,
    extract_id,
    is_admin,
    safe_dm,
    extract_dm_conversation,
)
from config import (
    DEEP_SPACE,
    COLOR_ERROR,
    COLOR_SUCCESS,
    COLOR_WARNING,
    OWNER_ID,
    AI_TARGET_CHECK_INTERVAL,
)


class Owner(commands.Cog):
    """Owner-only commands."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.ai_target_tasks = {}  # user_id -> task
    
    def cog_unload(self):
        """Clean up tasks when cog is unloaded."""
        for task in self.ai_target_tasks.values():
            task.cancel()
    
    async def cog_check(self, ctx: commands.Context):
        """Check if user is bot owner."""
        return ctx.author.id == OWNER_ID
    
    @commands.command(name="ai_target")
    async def ai_target(self, ctx: commands.Context, user: discord.Member):
        """Start AI targeting mode on a user."""
        # Add to database
        await add_ai_target(user.id, ctx.guild.id, ctx.author.id)
        
        # Start background task
        if user.id not in self.ai_target_tasks:
            self.ai_target_tasks[user.id] = asyncio.create_task(self._ai_target_loop(user.id, ctx.guild.id))
        
        await ctx.reply(embed=make_embed(
            title="🎯 AI Targeting Started",
            description=f"Luna is now targeting {user.mention}.\nI will roast them and randomly execute moderation actions.",
            color=get_embed_color("ai_target")
        ))
        
        # Send initial roast
        from helpers import generate_roast
        roast = generate_roast(user.name)
        await ctx.send(roast)
    
    @commands.command(name="ai_stop")
    async def ai_stop(self, ctx: commands.Context, user: discord.Member):
        """Stop AI targeting a user."""
        # Remove from database
        await remove_ai_target(user.id, ctx.guild.id)
        
        # Cancel background task
        if user.id in self.ai_target_tasks:
            self.ai_target_tasks[user.id].cancel()
            del self.ai_target_tasks[user.id]
        
        await ctx.reply(embed=make_embed(
            title="✅ AI Targeting Stopped",
            description=f"Stopped targeting {user.mention}.",
            color=get_embed_color("ai_stop")
        ))
    
    @commands.command(name="extract_dms")
    async def extract_dms(self, ctx: commands.Context, user: discord.User):
        """Extract DM conversation with a user and send as file."""
        stop_loading = None
        if ctx.message:
            from helpers import add_loading_reaction
            stop_loading = add_loading_reaction(ctx.message)
        
        # Extract conversation
        content = await extract_dm_conversation(self.bot, user)
        
        if stop_loading:
            stop_loading()
        
        # Create file
        filename = f"dm_conversation_{user.id}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)
        
        # Send file
        file = discord.File(filename)
        await ctx.send(
            content=f"📄 DM conversation with {user.name}#{user.discriminator}:",
            file=file
        )
        
        # Clean up
        import os
        os.remove(filename)
    
    @commands.command(name="commands")
    async def list_commands(self, ctx: commands.Context):
        """List all available commands (owner-only help)."""
        commands_list = []
        
        for cog_name, cog in self.bot.cogs.items():
            cog_commands = []
            for command in cog.get_commands():
                cog_commands.append(f"• `,`{command.name}{command.signature}")
            
            if cog_commands:
                commands_list.append(f"**{cog_name}**\n" + "\n".join(cog_commands))
        
        # Send in chunks to avoid hitting character limit
        for i in range(0, len(commands_list), 5):
            chunk = commands_list[i:i+5]
            embed = make_embed(
                title="📋 All Commands",
                description="\n\n".join(chunk),
                color=DEEP_SPACE
            )
            await ctx.send(embed=embed)
    
    @commands.group(name="blacklist", invoke_without_command=True)
    async def blacklist(self, ctx: commands.Context, user: discord.User, *, reason: str = "No reason provided"):
        """Blacklist a user from using the bot."""
        from database import get_guild_setting
        from datetime import datetime
        
        import aiosqlite
        async with aiosqlite.connect("luna.db") as db:
            await db.execute(
                "INSERT OR REPLACE INTO blacklist (user_id, reason, created_at) VALUES (?, ?, ?)",
                (user.id, reason, int(datetime.utcnow().timestamp()))
            )
            await db.commit()
        
        await ctx.reply(embed=make_embed(
            title=f"🚫 {user.name} Blacklisted",
            description=f"**Reason:** {reason}",
            color=get_embed_color("blacklist")
        ))
    
    @blacklist.command(name="remove")
    async def unblacklist(self, ctx: commands.Context, user: discord.User):
        """Remove a user from the blacklist."""
        import aiosqlite
        async with aiosqlite.connect("luna.db") as db:
            await db.execute(
                "DELETE FROM blacklist WHERE user_id = ?",
                (user.id,)
            )
            await db.commit()
        
        await ctx.reply(embed=make_embed(
            title=f"✅ {user.name} Removed from Blacklist",
            color=get_embed_color("unblacklist")
        ))
    
    @commands.command()
    async def status(self, ctx: commands.Context, *, status: str):
        """Set the bot's status."""
        await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=status))
        await ctx.reply(embed=make_embed(
            title="✅ Status Updated",
            description=f"Bot status set to: `{status}`",
            color=COLOR_SUCCESS
        ))
    
    @commands.command()
    async def servers(self, ctx: commands.Context):
        """List all servers the bot is in."""
        guilds = sorted(self.bot.guilds, key=lambda g: g.member_count, reverse=True)
        
        fields = []
        for guild in guilds[:10]:
            fields.append((
                guild.name,
                f"Members: {guild.member_count}\nID: {guild.id}",
                True
            ))
        
        embed = make_embed(
            title=f"🌐 Bot Servers ({len(self.bot.guilds)})",
            color=DEEP_SPACE,
            fields=fields
        )
        
        await ctx.send(embed=embed)
    
    @commands.command()
    async def leaveserver(self, ctx: commands.Context, guild_id: int):
        """Leave a server by ID."""
        guild = self.bot.get_guild(guild_id)
        if not guild:
            await ctx.reply(embed=make_embed(
                title="❌ Server Not Found",
                description=f"Cannot find server with ID {guild_id}.",
                color=COLOR_ERROR
            ))
            return
        
        await guild.leave()
        await ctx.reply(embed=make_embed(
            title="✅ Left Server",
            description=f"Successfully left {guild.name}.",
            color=COLOR_SUCCESS
        ))
    
    @commands.command()
    async def reload(self, ctx: commands.Context, cog: str):
        """Reload a cog."""
        try:
            await self.bot.reload_extension(f"luna.cogs.{cog}")
            await ctx.reply(embed=make_embed(
                title="✅ Cog Reloaded",
                description=f"Successfully reloaded `{cog}`.",
                color=COLOR_SUCCESS
            ))
        except Exception as e:
            await ctx.reply(embed=make_embed(
                title="❌ Reload Failed",
                description=f"Failed to reload `{cog}`: {str(e)}",
                color=COLOR_ERROR
            ))
    
    @commands.command()
    async def load(self, ctx: commands.Context, cog: str):
        """Load a cog."""
        try:
            await self.bot.load_extension(f"luna.cogs.{cog}")
            await ctx.reply(embed=make_embed(
                title="✅ Cog Loaded",
                description=f"Successfully loaded `{cog}`.",
                color=COLOR_SUCCESS
            ))
        except Exception as e:
            await ctx.reply(embed=make_embed(
                title="❌ Load Failed",
                description=f"Failed to load `{cog}`: {str(e)}",
                color=COLOR_ERROR
            ))
    
    @commands.command()
    async def unload(self, ctx: commands.Context, cog: str):
        """Unload a cog."""
        try:
            await self.bot.unload_extension(f"luna.cogs.{cog}")
            await ctx.reply(embed=make_embed(
                title="✅ Cog Unloaded",
                description=f"Successfully unloaded `{cog}`.",
                color=COLOR_SUCCESS
            ))
        except Exception as e:
            await ctx.reply(embed=make_embed(
                title="❌ Unload Failed",
                description=f"Failed to unload `{cog}`: {str(e)}",
                color=COLOR_ERROR
            ))
    
    async def _ai_target_loop(self, user_id: int, guild_id: int):
        """Background loop for AI targeting."""
        while True:
            try:
                await asyncio.sleep(AI_TARGET_CHECK_INTERVAL)
                
                # Check if still targeting
                targets = await get_active_ai_targets(guild_id)
                if not any(t['user_id'] == user_id for t in targets):
                    break
                
                # Get guild and user
                guild = self.bot.get_guild(guild_id)
                if not guild:
                    break
                
                member = guild.get_member(user_id)
                if not member:
                    break
                
                # Generate roast
                from helpers import generate_roast
                roast = generate_roast(member.name)
                
                # Send roast in a random channel
                text_channels = [c for c in guild.text_channels if c.permissions_for(guild.me).send_messages]
                if text_channels:
                    import random
                    channel = random.choice(text_channels)
                    await channel.send(roast)
                
                # 25% chance to execute moderation action
                import random
                if random.random() < 0.25:
                    action = random.choice(['warn', 'mute', 'timeout'])
                    
                    from database import add_warn, add_mute, get_warn_count
                    from helpers import utcnow, format_seconds
                    from datetime import timedelta
                    
                    if action == 'warn':
                        await add_warn(member.id, guild_id, self.bot.user.id, "AI target roast")
                        warns = await get_warn_count(member.id, guild_id)
                        await channel.send(f"⚠️ {member.mention} has been warned by Luna. Total warns: {warns}")
                    
                    elif action == 'mute':
                        duration = 300  # 5 minutes
                        expires_at = utcnow() + duration
                        await add_mute(member.id, guild_id, self.bot.user.id, "AI target mute", expires_at)
                        await member.timeout(timedelta(seconds=duration), reason="AI target mute")
                        await channel.send(f"🔇 {member.mention} has been muted for 5 minutes by Luna.")
                    
                    elif action == 'timeout':
                        duration = 300  # 5 minutes
                        await member.timeout(timedelta(seconds=duration), reason="AI target timeout")
                        await channel.send(f"⏱️ {member.mention} has been timed out for 5 minutes by Luna.")
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in AI target loop: {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(Owner(bot))
