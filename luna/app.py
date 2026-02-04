"""
Luna Discord Bot
A complete, production-ready moderation bot with advanced features.
Main entry point for HiddenCloud hosting compatibility.
"""

import os
import sys
import asyncio
from discord.ext import commands

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    BOT_NAME,
    TOKEN,
    PREFIX,
    OWNER_ID,
    DEEP_SPACE,
    STARLIGHT_BLUE,
)
from database import init_database


class LunaBot(commands.Bot):
    """Custom bot class for Luna."""
    
    def __init__(self):
        intents = discord.Intents.all()
        intents.message_content = True
        intents.presences = True
        
        super().__init__(
            command_prefix=self.get_prefix,
            intents=intents,
            help_command=None,
            case_insensitive=True,
            strip_after_prefix=True,
        )
    
    async def get_prefix(self, message: discord.Message):
        """Get custom prefix for a guild."""
        if not message.guild:
            return PREFIX
        
        from database import get_guild_setting
        prefix = await get_guild_setting(message.guild.id, "prefix")
        return prefix or PREFIX
    
    async def setup_hook(self):
        """Load all cogs and initialize database."""
        # Initialize database
        await init_database()
        print("✅ Database initialized")
        
        # Load cogs
        cogs = [
            "luna.cogs.setup",
            "luna.cogs.moderation",
            "luna.cogs.admin",
            "luna.cogs.hierarchy",
            "luna.cogs.logging",
            "luna.cogs.owner",
            "luna.cogs.helpers",
            "luna.cogs.utility",
            "luna.cogs.ai",
            "luna.cogs.shifts",
            "luna.cogs.help",
            "luna.cogs.background",
        ]
        
        for cog in cogs:
            try:
                await self.load_extension(cog)
                print(f"✅ Loaded {cog}")
            except Exception as e:
                print(f"❌ Failed to load {cog}: {e}")
    
    async def on_ready(self):
        """Called when bot is ready."""
        print(f"\n{'='*50}")
        print(f"🌙 {BOT_NAME} is online!")
        print(f"{'='*50}")
        print(f"👤 Logged in as: {self.user.name}#{self.user.discriminator}")
        print(f"🆔 User ID: {self.user.id}")
        print(f"🖥️  Servers: {len(self.guilds)}")
        print(f"👥 Total Members: {sum(g.member_count for g in self.guilds)}")
        print(f"📡 Latency: {round(self.latency * 1000)}ms")
        print(f"{'='*50}\n")
        
        # Set bot status
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f"{PREFIX}help | {len(self.guilds)} servers"
            ),
            status=discord.Status.online
        )
    
    async def on_command_error(self, ctx: commands.Context, error):
        """Global error handler."""
        # Handle missing arguments
        if isinstance(error, commands.MissingRequiredArgument):
            prefix = await self.get_prefix(ctx.message)
            if isinstance(prefix, list):
                prefix = prefix[0]
            
            usage = f"{prefix}{ctx.command.qualified_name} {ctx.command.signature}"
            
            embed = discord.Embed(
                title="❌ Missing Arguments",
                description=f"Missing required argument: `{error.param.name}`\n\n**Usage:**\n```{usage}```",
                color=COLOR_ERROR
            )
            await ctx.reply(embed=embed)
        
        # Handle bad arguments
        elif isinstance(error, commands.BadArgument):
            prefix = await self.get_prefix(ctx.message)
            if isinstance(prefix, list):
                prefix = prefix[0]
            
            usage = f"{prefix}{ctx.command.qualified_name} {ctx.command.signature}"
            
            embed = discord.Embed(
                title="❌ Invalid Argument",
                description=f"{str(error)}\n\n**Usage:**\n```{usage}```",
                color=COLOR_ERROR
            )
            await ctx.reply(embed=embed)
        
        # Handle command not found
        elif isinstance(error, commands.CommandNotFound):
            # Ignore this error
            pass
        
        # Handle missing permissions
        elif isinstance(error, commands.MissingPermissions):
            await ctx.reply(embed=discord.Embed(
                title="❌ Insufficient Permissions",
                description=f"You need: {', '.join(error.missing_permissions)}",
                color=COLOR_ERROR
            ))
        
        # Handle bot missing permissions
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.reply(embed=discord.Embed(
                title="❌ Bot Insufficient Permissions",
                description=f"I need: {', '.join(error.missing_permissions)}",
                color=COLOR_ERROR
            ))
        
        # Handle cooldown
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.reply(embed=discord.Embed(
                title="⏱️ Command on Cooldown",
                description=f"Try again in {error.retry_after:.2f} seconds.",
                color=0xFFA500
            ))
        
        # Handle other errors
        else:
            print(f"Unhandled error in {ctx.command.qualified_name}: {error}")
            await ctx.reply(embed=discord.Embed(
                title="❌ An Error Occurred",
                description=f"An unexpected error occurred. Please try again.",
                color=COLOR_ERROR
            ))


def main():
    """Main entry point."""
    bot = LunaBot()
    
    if not TOKEN:
        print("❌ ERROR: DISCORD_TOKEN not found in environment variables!")
        print("Please set up your .env file with the required variables.")
        sys.exit(1)
    
    bot.run(TOKEN)


if __name__ == "__main__":
    main()
