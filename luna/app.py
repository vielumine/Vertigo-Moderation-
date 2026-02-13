"""Luna bot bootstrap."""

from __future__ import annotations

import asyncio
import logging
import os
import random
from typing import Sequence

import discord
from discord.ext import commands
from dotenv import load_dotenv

import config
from database import Database
from helpers import log_to_modlog_channel, make_embed

logger = logging.getLogger(__name__)


class TimeoutActionView(discord.ui.View):
    """View for timeout alert actions."""
    
    def __init__(self, user_id: int, guild_id: int, alert_message_id: int, original_author_id: int, timeout: float = 300):
        super().__init__(timeout=timeout)
        self.user_id = user_id
        self.guild_id = guild_id
        self.alert_message_id = alert_message_id
        self.original_author_id = original_author_id
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Check if interaction user is admin/mod
        is_mod = any(role.permissions.administrator or role.permissions.moderate_members 
                     for role in interaction.user.roles)
        if not is_mod:
            await interaction.response.send_message("Only administrators and moderators can take actions.", ephemeral=True)
            return False
            
        # If it's a user-initiated alert, only that user can act. 
        # If it's bot-initiated (original_author_id is bot), any mod can act.
        if self.original_author_id != interaction.client.user.id and interaction.user.id != self.original_author_id:
            await interaction.response.send_message("Only the person who sent this alert can take actions.", ephemeral=True)
            return False
            
        return True
    
    @discord.ui.button(label="Unmute", style=discord.ButtonStyle.success, emoji="🔓")
    async def unmute_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        modal = ActionReasonModal("unmute", self.user_id, self.guild_id)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Warn", style=discord.ButtonStyle.secondary, emoji="⚠️")
    async def warn_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        modal = ActionReasonModal("warn", self.user_id, self.guild_id)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Ban", style=discord.ButtonStyle.danger, emoji="🔨")
    async def ban_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        modal = ActionReasonModal("ban", self.user_id, self.guild_id)
        await interaction.response.send_modal(modal)


class ActionReasonModal(discord.ui.Modal):
    """Modal for entering action reason."""
    
    def __init__(self, action_type: str, user_id: int, guild_id: int):
        self.action_type = action_type
        self.user_id = user_id
        self.guild_id = guild_id
        super().__init__(title=f"{action_type.title()} Reason", timeout=300)
        
        self.add_item(discord.ui.TextInput(
            label="Reason",
            placeholder="Enter reason for this action...",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=500
        ))
    
    async def on_submit(self, interaction: discord.Interaction) -> None:
        reason = self.children[0].value
        
        try:
            guild = interaction.guild
            if not guild:
                await interaction.response.send_message("Guild not found.", ephemeral=True)
                return
                
            member = guild.get_member(self.user_id)
            
            if not member:
                await interaction.response.send_message("User not found in server.", ephemeral=True)
                return
            
            # Defer after initial checks
            await interaction.response.defer(ephemeral=True)
            
            if self.action_type == "unmute":
                # Remove timeout
                await member.timeout(None, reason=reason)
                await interaction.followup.send(f"✅ Unmuted {member.mention} - {reason}", ephemeral=True)
                
            elif self.action_type == "warn":
                # Add warning
                await interaction.client.db.add_warning(
                    guild_id=self.guild_id,
                    user_id=self.user_id,
                    moderator_id=interaction.user.id,
                    reason=f"Timeout Alert: {reason}",
                    warn_days=14
                )
                await interaction.followup.send(f"✅ Warned {member.mention} - {reason}", ephemeral=True)
                
            elif self.action_type == "ban":
                # Ban user
                await member.ban(reason=f"Timeout Alert: {reason}")
                await interaction.followup.send(f"✅ Banned {member.mention} - {reason}", ephemeral=True)
            
            # Add to modlogs
            await interaction.client.db.add_modlog(
                guild_id=self.guild_id,
                action_type=f"timeout_alert_{self.action_type}",
                user_id=self.user_id,
                moderator_id=interaction.user.id,
                reason=reason
            )

            # Log to modlog channel
            settings = await interaction.client.db.get_guild_settings(self.guild_id, default_prefix=config.DEFAULT_PREFIX)
            log_embed = make_embed(
                action=self.action_type,
                title=f"🚨 Timeout Alert Action: {self.action_type.title()}",
                description=f"**Target:** {member.mention} ({member.id})\n**Moderator:** {interaction.user.mention}\n**Reason:** {reason}"
            )
            await log_to_modlog_channel(interaction.client, guild=guild, settings=settings, embed=log_embed, file=None)
            
        except Exception as e:
            logger.error(f"Timeout action failed: {e}", exc_info=True)
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message("Failed to perform action.", ephemeral=True)
                else:
                    await interaction.followup.send("Failed to perform action.", ephemeral=True)
            except Exception:
                pass


COGS: Sequence[str] = (
    "cogs.logging",
    "cogs.background",
    "cogs.setup",
    "cogs.moderation",
    "cogs.roles",
    "cogs.channels",
    "cogs.cleaning",
    "cogs.admin",
    "cogs.hierarchy",
    "cogs.member",
    "cogs.misc",
    "cogs.owner",
    "cogs.owner_commands",
    "cogs.stats",
    "cogs.ai",
    "cogs.ai_moderation",
    "cogs.wmr",
    "cogs.helpers",  # Tags system
    "cogs.utility",  # New utility commands
    "cogs.script_updates",  # Script update panel
    "cogs.shifts",   # Shift management
    "cogs.notifications",  # DM notification management
    "cogs.promotions",     # Staff promotion suggestions
)


class LunaBot(commands.Bot):
    db: Database


async def _get_prefix(bot: commands.Bot, message: discord.Message) -> str | list[str]:
    if message.guild is None:
        return config.DEFAULT_PREFIX

    db = getattr(bot, "db", None)
    if db is None:
        return config.DEFAULT_PREFIX

    settings = await db.get_guild_settings(message.guild.id, default_prefix=config.DEFAULT_PREFIX)
    return settings.prefix or config.DEFAULT_PREFIX


def create_bot() -> LunaBot:
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True
    intents.guilds = True
    intents.messages = True

    bot = LunaBot(
        command_prefix=_get_prefix,
        intents=intents,
        help_command=None,
        allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False),
    )
    return bot


async def _load_cogs(bot: commands.Bot) -> None:
    for ext in COGS:
        try:
            await bot.load_extension(ext)
            logger.info("Loaded %s", ext)
        except Exception:
            logger.exception("Failed to load extension %s", ext)


def _setup_logging() -> None:
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, level_name, logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


async def main() -> None:
    load_dotenv()
    _setup_logging()

    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_TOKEN is not set")

    bot = create_bot()
    bot.db = Database(config.DATABASE_PATH)
    bot.start_time = discord.utils.utcnow()
    await bot.db.connect()

    @bot.event
    async def on_ready() -> None:
        logger.info("Logged in as %s (%s)", bot.user, bot.user.id if bot.user else "?")

    @bot.event
    async def on_guild_join(guild: discord.Guild) -> None:
        try:
            if await bot.db.is_guild_blacklisted(guild_id=guild.id):
                await guild.leave()
        except Exception:
            logger.exception("Failed to check guild blacklist")

    @bot.event
    async def on_command_error(ctx: commands.Context, error: commands.CommandError) -> None:
        if isinstance(error, commands.CheckFailure):
            return
        if isinstance(error, commands.MissingRequiredArgument):
            prefix = await _get_prefix(bot, ctx.message)
            if isinstance(prefix, list):
                prefix = prefix[0]
            usage = f"{prefix}{ctx.command.qualified_name} {ctx.command.signature}"
            embed = make_embed(
                action="error",
                title="⚠️ Usage",
                description=usage,
            )
            await ctx.send(embed=embed)
            return
        if isinstance(error, commands.BadArgument):
            prefix = await _get_prefix(bot, ctx.message)
            if isinstance(prefix, list):
                prefix = prefix[0]
            usage = f"{prefix}{ctx.command.qualified_name} {ctx.command.signature}"
            embed = make_embed(
                action="error",
                title="⚠️ Usage",
                description=usage,
            )
            await ctx.send(embed=embed)
            return
        if isinstance(error, commands.CommandNotFound):
            return
        logger.exception("Unhandled command error", exc_info=error)
        embed = make_embed(action="error", title="Error", description="An error occurred. Please try again later.")
        await ctx.send(embed=embed)

    @bot.event
    async def on_message(message: discord.Message) -> None:
        """Handle mentions, DMs, AI responses, and blacklist checks."""
        # Check if user is blacklisted first
        if await bot.db.is_blacklisted(user_id=message.author.id):
            if message.content.startswith(await _get_prefix(bot, message)):
                # Send cold "No" response to blacklisted users trying to use commands
                await message.channel.send("No.")
            return
        
        # Ignore bot messages
        if message.author.bot:
            return
        
        # Handle DM messages
        if message.guild is None:
            # Forward DM to owner
            from helpers import notify_owner
            owner_embed = make_embed(
                action="dm_forward",
                title="📥 New DM Received",
                description=f"**From:** {message.author} (`{message.author.id}`)\n\n**Content:**\n{message.content}"
            )
            if message.attachments:
                owner_embed.add_field(name="Attachments", value=f"{len(message.attachments)} attachment(s)")
                
            await notify_owner(bot, embed=owner_embed)
            
            # Check if this is a DM and AI should respond
            try:
                # For DMs, we need to check if AI is enabled for DMs
                # Since we don't have guild context in DMs, we'll need a different approach
                # For now, we'll respond to DMs if the user has a guild with the bot
                # and that guild has AI enabled for DMs
                
                # Check if user has any mutual guilds with AI DM support enabled
                ai_enabled_for_dm = False
                for guild in bot.guilds:
                    try:
                        ai_settings = await bot.db.get_ai_settings(guild.id)
                        if ai_settings.ai_enabled and ai_settings.respond_to_dms:
                            ai_enabled_for_dm = True
                            break
                    except Exception:
                        continue
                
                if ai_enabled_for_dm:
                    from helpers import get_ai_response, is_rate_limited, update_rate_limit
                    
                    # Check rate limiting
                    if not is_rate_limited(message.author.id):
                        try:
                            # Get AI response with default personality
                            response = await get_ai_response(message.content, "genz")
                            update_rate_limit(message.author.id)
                            
                            # Send response
                            embed = make_embed(
                                action="ai",
                                title="🤖",
                                description=response
                            )
                            await message.reply(embed=embed)
                        except Exception:
                            # Silently fail for DMs to avoid spam
                            pass
            except Exception:
                # Silently fail for DMs
                pass
            
            # Don't process commands in DMs for this bot
            return
        
        # Handle guild messages (mentions and AI targeting)
        guild_id = message.guild.id
        
        # Check for timeout system violations
        try:
            timeout_settings = await bot.db.get_timeout_settings(guild_id)
            if timeout_settings.enabled and timeout_settings.phrases:
                # Check if message contains prohibited phrases
                message_lower = message.content.lower()
                phrases = [p.strip().lower() for p in timeout_settings.phrases.split(',') if p.strip()]
                
                matched_phrase = None
                for phrase in phrases:
                    if phrase in message_lower:
                        matched_phrase = phrase
                        break
                
                if matched_phrase:
                    # Get guild settings to check for staff immunity
                    guild_settings = await bot.db.get_guild_settings(guild_id, default_prefix=config.DEFAULT_PREFIX)
                    member = message.author
                    
                    # Check if user is staff (immune to timeout system)
                    is_staff = False
                    if isinstance(member, discord.Member):
                        staff_role_ids = set(guild_settings.staff_role_ids + guild_settings.head_mod_role_ids + 
                                          guild_settings.senior_mod_role_ids + guild_settings.moderator_role_ids + guild_settings.admin_role_ids)
                        is_staff = any(role.id in staff_role_ids for role in member.roles)
                    
                    if not is_staff:
                        # Take timeout action
                        try:
                            # Timeout the user
                            timeout_duration = discord.utils.utcnow() + discord.utils.parse_time_unit(timeout_settings.timeout_duration, convert=True)
                            await member.timeout(timeout_duration, reason=f"Timeout: Used prohibited term '{matched_phrase}'")
                            
                            # Delete the violating message
                            await message.delete()
                            
                            # Send confirmation in the channel where violation occurred
                            confirm_embed = make_embed(
                                action="timeout",
                                title="⏰ Timeout Issued",
                                description=f"**{member.mention}** has been timed out for using a prohibited term.\n**Term:** `{matched_phrase}`\n**Duration:** {timeout_settings.timeout_duration // 3600}h"
                            )
                            await message.channel.send(embed=confirm_embed)
                            
                            # Send detailed alert to alert channel
                            if timeout_settings.alert_channel_id:
                                alert_channel = bot.get_guild(guild_id).get_channel(timeout_settings.alert_channel_id)
                                if alert_channel:
                                    alert_embed = make_embed(
                                        action="timeout",
                                        title="🚨 Prohibited Term Detected",
                                        description=f"**User:** {member.mention} ({member.id})\n**Channel:** {message.channel.mention}\n**Term Matched:** `{matched_phrase}`\n**Original Message:**\n{message.content[:500]}{'...' if len(message.content) > 500 else ''}"
                                    )
                                    
                                    alert_embed.add_field(
                                        name="📅 Details",
                                        value=f"**Timeout Duration:** {timeout_settings.timeout_duration // 3600}h\n**Staff Member:** No\n**Action Taken:** Timeout + Message Deletion",
                                        inline=False
                                    )
                                    
                                    alert_message = await alert_channel.send(
                                        content=f"<@&{timeout_settings.alert_role_id}>" if timeout_settings.alert_role_id else None,
                                        embed=alert_embed
                                    )
                                    
                                    # Add action buttons to alert
                                    view = TimeoutActionView(member.id, guild_id, alert_message.id, bot.user.id)
                                    await alert_message.edit(view=view)
                                    
                                    # Add to modlogs
                                    await bot.db.add_modlog(
                                        guild_id=guild_id,
                                        action_type="timeout_violation",
                                        user_id=member.id,
                                        moderator_id=bot.user.id,
                                        reason=f"Used prohibited term: {matched_phrase}",
                                        message_id=message.id
                                    )
                                    
                                    # Log to modlog channel
                                    await log_to_modlog_channel(bot, guild=bot.get_guild(guild_id), settings=guild_settings, embed=alert_embed, file=None)
                                    
                        except Exception as e:
                            logger.error(f"Timeout action failed: {e}")
        except Exception:
            # Silently fail for timeout system
            pass
        
        # Check if user is AI targeted for trolling/roasting
        ai_target = await bot.db.get_ai_target(user_id=message.author.id, guild_id=guild_id)
        if ai_target and random.random() < 0.3:  # 30% chance for AI actions
            try:
                from helpers import get_ai_response
                
                # Generate roasting response
                roast_prompt = f"Roast this user in a funny, lighthearted way: {message.content}"
                roast_response = await get_ai_response(roast_prompt, "funny")
                
                # Sometimes do fake moderation actions
                if random.random() < 0.1:  # 10% chance for fake actions
                    fake_actions = [
                        f"🤖 *fake warns* {message.author.mention} - your message was a bit sus fr fr",
                        f"🤖 *fake mutes* {message.author.mention} - taking a break from being problematic 💀",
                        f"🤖 *fake ban* {message.author.mention} - you've been absolutely cooked 🔥"
                    ]
                    roast_response = random.choice(fake_actions)
                
                embed = make_embed(
                    action="ai",
                    title="🤖 AI Targeting",
                    description=roast_response
                )
                
                await message.channel.send(embed=embed)
                
            except Exception:
                # Silently fail for AI targeting
                pass
        
        # Check if bot was mentioned
        if bot.user in message.mentions:
            try:
                ai_enabled = await bot.db.get_ai_settings(message.guild.id)
                
                if ai_enabled.ai_enabled and ai_enabled.respond_to_mentions:
                    # Remove the mention to get the actual message content
                    content = message.content
                    for mention in message.mentions:
                        if mention.id == bot.user.id:
                            content = content.replace(f"<@{mention.id}>", "").replace(f"<@!{mention.id}>", "").strip()
                    
                    if content:  # Only respond if there's actual content after removing mention
                        from helpers import get_ai_response, is_rate_limited, update_rate_limit
                        
                        # Check rate limiting
                        if not is_rate_limited(message.author.id):
                            try:
                                # Get AI response
                                response = await get_ai_response(content, ai_enabled.ai_personality)
                                update_rate_limit(message.author.id)
                                
                                # Send response
                                embed = make_embed(
                                    action="ai",
                                    title="🤖",
                                    description=response
                                )
                                await message.reply(embed=embed)
                            except Exception:
                                # Silently fail for mentions to avoid spam
                                pass
            except Exception:
                # Silently fail for mentions
                pass
        
        # Process commands normally
        await bot.process_commands(message)

    await _load_cogs(bot)

    try:
        await bot.start(token)
    finally:
        await bot.db.close()


def run() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    run()
