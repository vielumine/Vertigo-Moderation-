"""
Luna Bot Background Cog
Handles background tasks for reminders, AFK checking, and AI targeting.
"""

import discord
from discord.ext import commands, tasks
import asyncio
from datetime import datetime

from database import (
    get_expired_reminders,
    remove_reminder,
    get_active_shift,
    pause_shift,
    resume_shift,
    end_shift,
    get_shift_config,
    get_last_activity,
    get_active_ai_targets,
    add_staff_flag,
    add_mute,
    add_warn,
)
from helpers import (
    make_embed,
    safe_dm,
    utcnow,
    format_seconds,
    get_gemini_response,
    generate_roast,
)
from config import (
    DEEP_SPACE,
    COLOR_SUCCESS,
    COLOR_WARNING,
    COLOR_ERROR,
    REMINDER_CHECK_INTERVAL,
    SHIFT_GMT_OFFSET,
    SHIFT_AUTO_END_THRESHOLD,
    SHIFT_DEFAULT_AFK_TIMEOUT,
    AI_TARGET_CHECK_INTERVAL,
    AI_TARGET_ACTION_CHANCE,
    EMOJI_SHIFT_BREAK,
    EMOJI_SHIFT_AFK,
    EMOJI_SHIFT_END,
)


class Background(commands.Cog):
    """Background tasks for automated operations."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.reminder_checker.start()
        self.afk_checker.start()
        self.ai_target_task.start()
    
    def cog_unload(self):
        """Cancel tasks on cog unload."""
        self.reminder_checker.cancel()
        self.afk_checker.cancel()
        self.ai_target_task.cancel()
    
    @tasks.loop(seconds=REMINDER_CHECK_INTERVAL)
    async def reminder_checker(self):
        """Check for expired reminders and send notifications."""
        try:
            expired = await get_expired_reminders()
            
            for reminder in expired:
                user = self.bot.get_user(reminder['user_id'])
                if user:
                    embed = make_embed(
                        title="⏰ Reminder!",
                        description=reminder['reminder_text'],
                        color=COLOR_SUCCESS
                    )
                    
                    await safe_dm(user, embed=embed)
                
                # Remove reminder from database
                await remove_reminder(reminder['id'])
                
                # Small delay to avoid rate limiting
                await asyncio.sleep(0.5)
        
        except Exception as e:
            print(f"Error in reminder checker: {e}")
    
    @reminder_checker.before_loop
    async def before_reminder_checker(self):
        """Wait for bot to be ready before starting."""
        await self.bot.wait_until_ready()
    
    @tasks.loop(seconds=60)
    async def afk_checker(self):
        """Check for inactive staff members and auto-pause/end shifts."""
        try:
            for guild in self.bot.guilds:
                # Check active shifts
                from database import get_all_shift_configs
                configs = await get_all_shift_configs(guild.id)
                
                # Get all members with shift configs
                for config in configs:
                    role = guild.get_role(config['role_id'])
                    if not role:
                        continue
                    
                    for member in role.members:
                        # Check if member has active shift
                        shift = await get_active_shift(member.id, guild.id)
                        if not shift or shift['status'] != 'active':
                            continue
                        
                        # Get last activity
                        last_activity = await get_last_activity(member.id, guild.id)
                        if not last_activity:
                            continue
                        
                        # Check if inactive
                        inactive_seconds = utcnow() - last_activity
                        afk_timeout = config.get('afk_timeout', SHIFT_DEFAULT_AFK_TIMEOUT)
                        
                        if inactive_seconds > afk_timeout:
                            # Auto-pause shift
                            await pause_shift(member.id, guild.id)
                            
                            # DM notification
                            embed = make_embed(
                                title=f"{EMOJI_SHIFT_BREAK} Shift Auto-Paused",
                                description=f"You have been inactive for {format_seconds(inactive_seconds)}.\nYour shift has been paused.",
                                color=COLOR_WARNING
                            )
                            await safe_dm(member, embed=embed)
                            
                            # Store break start time
                            import aiosqlite
                            async with aiosqlite.connect("luna.db") as db:
                                await db.execute(
                                    "UPDATE shifts SET break_start = ? WHERE id = ?",
                                    (utcnow(), shift['id'])
                                )
                                await db.commit()
                        
                        # Check for auto-end (2x AFK timeout)
                        elif inactive_seconds > afk_timeout * SHIFT_AUTO_END_THRESHOLD:
                            # Auto-end shift
                            shift_record = await end_shift(member.id, guild.id)
                            
                            if shift_record:
                                # Calculate duration
                                end_time = shift_record.get('end_ts_utc', utcnow())
                                start_time = shift_record.get('start_ts_utc', shift_record['created_at'])
                                duration = end_time - start_time - shift_record.get('break_duration', 0)
                                
                                embed = make_embed(
                                    title=f"{EMOJI_SHIFT_END} Shift Auto-Ended",
                                    description=f"You have been inactive for too long.\nShift duration: {format_seconds(duration)}",
                                    color=COLOR_ERROR
                                )
                                await safe_dm(member, embed=embed)
        
        except Exception as e:
            print(f"Error in AFK checker: {e}")
    
    @afk_checker.before_loop
    async def before_afk_checker(self):
        """Wait for bot to be ready before starting."""
        await self.bot.wait_until_ready()
    
    @tasks.loop(seconds=AI_TARGET_CHECK_INTERVAL)
    async def ai_target_task(self):
        """Check for AI targets and execute actions."""
        try:
            for guild in self.bot.guilds:
                targets = await get_active_ai_targets(guild.id)
                
                for target in targets:
                    user = guild.get_member(target['user_id'])
                    if not user:
                        continue
                    
                    # Check if user is active in the last 5 minutes
                    from database import get_last_activity
                    last_activity = await get_last_activity(user.id, guild.id)
                    if not last_activity or (utcnow() - last_activity) > 300:
                        continue
                    
                    # Generate roast
                    roast = generate_roast(user.name)
                    
                    # Find a channel to send to
                    text_channels = [c for c in guild.text_channels if c.permissions_for(guild.me).send_messages]
                    if not text_channels:
                        continue
                    
                    import random
                    channel = random.choice(text_channels)
                    
                    try:
                        await channel.send(roast)
                    except:
                        pass
                    
                    # 25% chance to execute moderation action
                    if random.random() < AI_TARGET_ACTION_CHANCE:
                        action = random.choice(['warn', 'mute', 'timeout'])
                        
                        if action == 'warn':
                            await add_warn(user.id, guild.id, self.bot.user.id, "AI target roast")
                            try:
                                await channel.send(f"⚠️ {user.mention} has been warned by Luna.")
                            except:
                                pass
                        
                        elif action == 'mute':
                            duration = 300  # 5 minutes
                            expires_at = utcnow() + duration
                            await add_mute(user.id, guild.id, self.bot.user.id, "AI target mute", expires_at)
                            try:
                                from datetime import timedelta
                                await user.timeout(timedelta(seconds=duration), reason="AI target mute")
                                await channel.send(f"🔇 {user.mention} has been muted for 5 minutes by Luna.")
                            except:
                                pass
                        
                        elif action == 'timeout':
                            duration = 300  # 5 minutes
                            try:
                                from datetime import timedelta
                                await user.timeout(timedelta(seconds=duration), reason="AI target timeout")
                                await channel.send(f"⏱️ {user.mention} has been timed out for 5 minutes by Luna.")
                            except:
                                pass
                    
                    # Small delay
                    await asyncio.sleep(2)
        
        except Exception as e:
            print(f"Error in AI target task: {e}")
    
    @ai_target_task.before_loop
    async def before_ai_target_task(self):
        """Wait for bot to be ready before starting."""
        await self.bot.wait_until_ready()
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Handle AI mentions and DMs."""
        if message.author.bot:
            return
        
        # Check for bot mention
        if self.bot.user in message.mentions:
            from database import get_ai_setting
            
            guild_enabled = True
            if message.guild:
                ai_enabled = await get_ai_setting(message.guild.id, "ai_enabled")
                guild_enabled = ai_enabled if ai_enabled is not None else True
            
            if guild_enabled:
                # Remove bot mention from message
                clean_message = message.content.replace(f"<@{self.bot.user.id}>", "").replace(f"<@!{self.bot.user.id}>", "").strip()
                
                if clean_message:
                    # Get AI personality
                    personality = await get_ai_setting(message.guild.id, "personality") if message.guild else "helpful"
                    
                    # Send typing indicator
                    async with message.channel.typing():
                        response = await get_gemini_response(clean_message, personality)
                    
                    embed = make_embed(
                        title="🌙 Luna AI",
                        description=response,
                        color=DEEP_SPACE,
                        author={"name": message.author.display_name, "icon_url": message.author.display_avatar.url}
                    )
                    
                    await message.reply(embed=embed)
        
        # Check for DM
        if not message.guild:
            from database import get_ai_setting, get_guild_setting
            from config import WEBHOOK_MODLOG, OWNER_ID
            
            # DM response check (global setting)
            dm_response_enabled = await get_ai_setting(0, "dm_response_enabled")
            if dm_response_enabled:
                # Get AI personality
                personality = await get_ai_setting(0, "personality") or "helpful"
                
                # Send typing indicator
                async with message.channel.typing():
                    response = await get_gemini_response(message.content, personality)
                
                embed = make_embed(
                    title="🌙 Luna AI",
                    description=response,
                    color=DEEP_SPACE
                )
                
                await message.reply(embed=embed)
            
            # Log DM to modlog webhook
            if WEBHOOK_MODLOG:
                from helpers import log_to_webhook
                embed = make_embed(
                    title="📩 New DM",
                    description=message.content[:500],
                    color=DEEP_SPACE,
                    fields=[
                        ("User", f"{message.author.mention} (ID: {message.author.id})", True),
                        ("Timestamp", f"<t:{utcnow()}:F>", True),
                    ]
                )
                await log_to_webhook(WEBHOOK_MODLOG, embed)
            
            # Forward DM to owner
            owner = self.bot.get_user(OWNER_ID)
            if owner:
                embed = make_embed(
                    title="📩 DM Received",
                    description=message.content[:500],
                    color=DEEP_SPACE,
                    fields=[
                        ("User", f"{message.author}#{message.author.discriminator}", True),
                        ("ID", str(message.author.id), True),
                    ]
                )
                
                if message.attachments:
                    embed.add_field(
                        name="Attachments",
                        value=f"{len(message.attachments)} attachment(s)",
                        inline=False
                    )
                
                await owner.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Background(bot))
