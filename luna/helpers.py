"""
Luna Bot Helper Functions
Utility functions for embeds, permissions, parsing, etc.
"""

import discord
from discord.ext import commands
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Callable
from functools import wraps
import re
import google.generativeai as genai

from config import (
    BOT_NAME,
    PREFIX,
    OWNER_ID,
    GEMINI_API_KEY,
    DEEP_SPACE,
    STARLIGHT_BLUE,
    COSMIC_PURPLE,
    COLOR_ERROR,
    COLOR_SUCCESS,
    COLOR_INFO,
    COLOR_WARNING,
    EMBED_COLORS,
    AI_MAX_RESPONSE_LENGTH,
    AI_TIMEOUT_SECONDS,
    SHIFT_GMT_OFFSET,
    ERROR_NO_PERMISSION,
    ERROR_NOT_CONFIGURED,
    ERROR_INVALID_INPUT,
    ERROR_DATABASE_ERROR,
    ERROR_API_ERROR,
    SUCCESS_DEFAULT,
    WEBHOOK_MODLOG,
    WEBHOOK_JOIN_LEAVE,
)


def utcnow() -> int:
    """Get current UTC timestamp."""
    return int(datetime.utcnow().timestamp())


def to_gmt8(utc_timestamp: int) -> int:
    """Convert UTC timestamp to GMT+8 timestamp."""
    return utc_timestamp + (SHIFT_GMT_OFFSET * 3600)


def make_embed(
    title: str = "",
    description: str = "",
    color: int = DEEP_SPACE,
    fields: Optional[List[tuple]] = None,
    footer: Optional[str] = None,
    timestamp: bool = True,
    thumbnail: Optional[str] = None,
    author: Optional[Dict[str, Any]] = None
) -> discord.Embed:
    """Create a Discord embed with Luna theme."""
    embed = discord.Embed(
        title=title,
        description=description,
        color=color
    )
    
    if fields:
        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)
    
    if footer:
        embed.set_footer(text=footer)
    elif timestamp:
        embed.set_footer(text=f"{BOT_NAME} • {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
    
    if author:
        embed.set_author(name=author.get('name', ''), icon_url=author.get('icon_url', ''))
    
    return embed


def parse_duration(duration_str: str) -> Optional[int]:
    """
    Parse duration string to seconds.
    Supports: 1h, 30m, 1d, 1w, 1mo, 1y
    Returns seconds or None if invalid.
    """
    duration_str = duration_str.lower().strip()
    
    patterns = [
        (r'(\d+)y', lambda m: int(m.group(1)) * 31536000),  # years
        (r'(\d+)mo', lambda m: int(m.group(1)) * 2592000),   # months
        (r'(\d+)w', lambda m: int(m.group(1)) * 604800),     # weeks
        (r'(\d+)d', lambda m: int(m.group(1)) * 86400),      # days
        (r'(\d+)h', lambda m: int(m.group(1)) * 3600),       # hours
        (r'(\d+)m', lambda m: int(m.group(1)) * 60),         # minutes
        (r'(\d+)s', lambda m: int(m.group(1))),               # seconds
    ]
    
    total_seconds = 0
    for pattern, calculator in patterns:
        match = re.search(pattern, duration_str)
        if match:
            total_seconds += calculator(match)
    
    return total_seconds if total_seconds > 0 else None


def format_seconds(seconds: int) -> str:
    """Format seconds to human-readable duration (e.g., '1h 30m 15s')."""
    if seconds < 0:
        seconds = 0
    
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 or not parts:
        parts.append(f"{secs}s")
    
    return " ".join(parts)


def humanize_seconds(seconds: int) -> str:
    """Humanize duration with full words."""
    if seconds < 60:
        return f"{seconds} second{'s' if seconds != 1 else ''}"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''}"
    elif seconds < 86400:
        hours = seconds // 3600
        return f"{hours} hour{'s' if hours != 1 else ''}"
    else:
        days = seconds // 86400
        return f"{days} day{'s' if days != 1 else ''}"


def extract_id(input_str: str) -> Optional[int]:
    """
    Extract Discord ID from various formats:
    - User mention: <@123456789>
    - Role mention: <@&123456789>
    - Channel mention: <#123456789>
    - Raw ID: 123456789
    """
    # Try to extract from mention
    mention_match = re.search(r'<@!?(\d+)>', input_str)
    if mention_match:
        return int(mention_match.group(1))
    
    # Try to extract from role mention
    role_match = re.search(r'<@&(\d+)>', input_str)
    if role_match:
        return int(role_match.group(1))
    
    # Try to extract from channel mention
    channel_match = re.search(r'<#(\d+)>', input_str)
    if channel_match:
        return int(channel_match.group(1))
    
    # Try to parse as raw ID
    if input_str.isdigit():
        return int(input_str)
    
    return None


async def safe_dm(user: discord.Member, message: str, embed: Optional[discord.Embed] = None) -> bool:
    """
    Safely send a DM to a user.
    Returns True if successful, False otherwise.
    """
    try:
        if embed:
            await user.send(embed=embed)
        else:
            await user.send(message)
        return True
    except Exception:
        return False


async def safe_delete(message: discord.Message) -> bool:
    """
    Safely delete a message.
    Returns True if successful, False otherwise.
    """
    try:
        await message.delete()
        return True
    except Exception:
        return False


def add_loading_reaction(message: discord.Message) -> Callable:
    """
    Add a loading reaction to a message and return a callback to remove it.
    Usage:
        stop_loading = add_loading_reaction(message)
        # ... do work ...
        stop_loading()
    """
    async def add():
        try:
            await message.add_reaction("⏳")
        except Exception:
            pass
    
    async def remove():
        try:
            await message.remove_reaction("⏳", message.guild.me)
        except Exception:
            pass
    
    import asyncio
    asyncio.create_task(add())
    return remove


def require_admin():
    """Decorator to require admin permissions."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(self, ctx: commands.Context, *args, **kwargs):
            if not await is_admin(ctx.author, ctx.guild):
                await ctx.reply(embed=make_embed(
                    title=ERROR_NO_PERMISSION,
                    description="This command requires administrator privileges.",
                    color=COLOR_ERROR
                ))
                return
            return await func(self, ctx, *args, **kwargs)
        return wrapper
    return decorator


def require_staff():
    """Decorator to require staff role."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(self, ctx: commands.Context, *args, **kwargs):
            if not await is_staff(ctx.author, ctx.guild):
                await ctx.reply(embed=make_embed(
                    title=ERROR_NO_PERMISSION,
                    description="This command requires staff privileges.",
                    color=COLOR_ERROR
                ))
                return
            return await func(self, ctx, *args, **kwargs)
        return wrapper
    return decorator


def require_helper():
    """Decorator to require helper role."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(self, ctx: commands.Context, *args, **kwargs):
            if not await is_helper(ctx.author, ctx.guild):
                await ctx.reply(embed=make_embed(
                    title=ERROR_NO_PERMISSION,
                    description="This command requires helper privileges.",
                    color=COLOR_ERROR
                ))
                return
            return await func(self, ctx, *args, **kwargs)
        return wrapper
    return decorator


def require_owner():
    """Decorator to require bot owner."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(self, ctx: commands.Context, *args, **kwargs):
            if ctx.author.id != OWNER_ID:
                await ctx.reply(embed=make_embed(
                    title=ERROR_NO_PERMISSION,
                    description="This command is restricted to the bot owner.",
                    color=COLOR_ERROR
                ))
                return
            return await func(self, ctx, *args, **kwargs)
        return wrapper
    return decorator


async def is_admin(member: discord.Member, guild: discord.Guild) -> bool:
    """Check if a member is an admin."""
    if not guild:
        return False
    
    # Check if they have admin permission
    if member.guild_permissions.administrator:
        return True
    
    # Check for configured admin role
    from database import get_guild_setting
    admin_role_id = await get_guild_setting(guild.id, "admin_role_id")
    if admin_role_id:
        admin_role = guild.get_role(admin_role_id)
        if admin_role and admin_role in member.roles:
            return True
    
    # Check if they're the owner
    if member == guild.owner:
        return True
    
    return False


async def is_staff(member: discord.Member, guild: discord.Guild) -> bool:
    """Check if a member is staff."""
    if not guild:
        return False
    
    # Admins are also staff
    if await is_admin(member, guild):
        return True
    
    # Check for configured staff role
    from database import get_guild_setting
    staff_role_id = await get_guild_setting(guild.id, "staff_role_id")
    if staff_role_id:
        staff_role = guild.get_role(staff_role_id)
        if staff_role and staff_role in member.roles:
            return True
    
    return False


async def is_helper(member: discord.Member, guild: discord.Guild) -> bool:
    """Check if a member is a helper."""
    if not guild:
        return False
    
    # Staff members can also use helper commands
    if await is_staff(member, guild):
        return True
    
    # Check for configured helper role
    from database import get_helper_role
    helper_role_id = await get_helper_role(guild.id)
    if helper_role_id:
        helper_role = guild.get_role(helper_role_id)
        if helper_role and helper_role in member.roles:
            return True
    
    return False


async def log_to_modlog_channel(guild: discord.Guild, embed: discord.Embed) -> bool:
    """
    Send an embed to the configured modlog channel.
    Returns True if successful.
    """
    from database import get_guild_setting
    
    modlog_channel_id = await get_guild_setting(guild.id, "modlog_channel_id")
    if not modlog_channel_id:
        return False
    
    channel = guild.get_channel(modlog_channel_id)
    if not channel:
        return False
    
    try:
        await channel.send(embed=embed)
        return True
    except Exception:
        return False


async def log_to_webhook(webhook_url: str, embed: discord.Embed) -> bool:
    """
    Send an embed to a webhook.
    Returns True if successful.
    """
    if not webhook_url:
        return False
    
    try:
        webhook = discord.Webhook.from_url(webhook_url, session=discord.utils.get_webhook_session())
        await webhook.send(embed=embed, wait=True)
        return True
    except Exception:
        return False


async def get_gemini_response(prompt: str, personality: str = "helpful") -> str:
    """
    Get a response from Gemini AI.
    personality: 'helpful', 'sarcastic', 'genz', 'professional'
    """
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-pro')
        
        # System prompt based on personality
        system_prompts = {
            "helpful": "You are Luna, a helpful and friendly AI assistant. Be concise and direct.",
            "sarcastic": "You are Luna, a witty and sarcastic AI. Use humor and light roasting.",
            "genz": "You are Luna, a Gen-Z AI. Use slang casually and be chill.",
            "professional": "You are Luna, a professional AI assistant. Be formal and precise.",
        }
        
        system_prompt = system_prompts.get(personality, system_prompts["helpful"])
        full_prompt = f"{system_prompt}\n\n{prompt}"
        
        response = model.generate_content(full_prompt, timeout=AI_TIMEOUT_SECONDS)
        
        if response and hasattr(response, 'text'):
            text = response.text.strip()
            # Truncate if too long
            if len(text) > AI_MAX_RESPONSE_LENGTH:
                text = text[:AI_MAX_RESPONSE_LENGTH-3] + "..."
            return text
        
        return "I apologize, but I couldn't generate a response."
    except Exception as e:
        return f"Error: Unable to connect to AI service."


def generate_roast(target_name: str) -> str:
    """Generate a random roast for AI targeting."""
    roasts = [
        f"{target_name}, your presence is about as useful as a screen door on a submarine.",
        f"Hey {target_name}, I've seen more intelligent life forms in a petri dish.",
        f"{target_name}, if brains were dynamite, you wouldn't have enough to blow your nose.",
        f"{target_name}, you're not stupid, you just have bad luck thinking.",
        f"{target_name}, you're living proof that evolution can go in reverse.",
        f"{target_name}, your keyboard must be confused from all the nonsense you type.",
        f"{target_name}, I'd explain it to you, but I don't have any crayons.",
        f"{target_name}, you bring everyone so much joy... when you leave the room.",
        f"{target_name}, is your keyboard happy? Because you really seem to be typing nonsense.",
        f"{target_name}, you're the reason the gene pool needs a lifeguard.",
    ]
    import random
    return random.choice(roasts)


class PaginationView(discord.ui.View):
    """Pagination view for embeds."""
    
    def __init__(self, items: List[Any], create_embed: Callable, timeout: int = 180):
        super().__init__(timeout=timeout)
        self.items = items
        self.create_embed = create_embed
        self.current_page = 0
        self.items_per_page = 10
        self.total_pages = (len(items) + self.items_per_page - 1) // self.items_per_page
        
        # Update button states
        self.update_buttons()
    
    def update_buttons(self):
        """Update button states based on current page."""
        self.first_page.disabled = self.current_page == 0
        self.prev_page.disabled = self.current_page == 0
        self.next_page.disabled = self.current_page >= self.total_pages - 1
        self.last_page.disabled = self.current_page >= self.total_pages - 1
    
    def get_current_items(self):
        """Get items for current page."""
        start = self.current_page * self.items_per_page
        end = start + self.items_per_page
        return self.items[start:end]
    
    @discord.ui.button(label="⏮️", style=discord.ButtonStyle.secondary)
    async def first_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = 0
        self.update_buttons()
        embed = self.create_embed(self.get_current_items(), self.current_page, self.total_pages)
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="◀️", style=discord.ButtonStyle.primary)
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = max(0, self.current_page - 1)
        self.update_buttons()
        embed = self.create_embed(self.get_current_items(), self.current_page, self.total_pages)
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="▶️", style=discord.ButtonStyle.primary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = min(self.total_pages - 1, self.current_page + 1)
        self.update_buttons()
        embed = self.create_embed(self.get_current_items(), self.current_page, self.total_pages)
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="⏭️", style=discord.ButtonStyle.secondary)
    async def last_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = self.total_pages - 1
        self.update_buttons()
        embed = self.create_embed(self.get_current_items(), self.current_page, self.total_pages)
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="🗑️", style=discord.ButtonStyle.danger)
    async def delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.delete_message()


class ReasonModal(discord.ui.Modal, title='Provide Reason'):
    """Modal for entering a reason."""
    
    reason = discord.ui.TextInput(
        label='Reason',
        placeholder='Enter the reason...',
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=500
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()


class TagCreateModal(discord.ui.Modal, title='Create Tag'):
    """Modal for creating a tag."""
    
    category = discord.ui.TextInput(
        label='Category',
        placeholder='e.g., moderation, general, fun',
        style=discord.TextStyle.short,
        required=True,
        max_length=50
    )
    
    title = discord.ui.TextInput(
        label='Title',
        placeholder='Tag title',
        style=discord.TextStyle.short,
        required=True,
        max_length=50
    )
    
    description = discord.ui.TextInput(
        label='Description',
        placeholder='Tag content...',
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=2000
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()


class ShiftNoteModal(discord.ui.Modal, title='Shift Note'):
    """Modal for adding a shift note."""
    
    note = discord.ui.TextInput(
        label='Note',
        placeholder='Enter any notes about this shift...',
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=500
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()


async def extract_dm_conversation(bot: commands.Bot, user: discord.User) -> str:
    """
    Extract DM conversation with a user.
    Returns formatted string with timestamps and messages.
    """
    lines = []
    lines.append(f"DM Conversation with {user.name}#{user.discriminator} (ID: {user.id})")
    lines.append("=" * 60)
    
    try:
        # Fetch DM channel
        dm_channel = user.dm_channel
        if not dm_channel:
            dm_channel = await user.create_dm()
        
        # Fetch message history
        async for message in dm_channel.history(limit=None, oldest_first=True):
            author = message.author
            timestamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")
            
            if author == bot.user:
                prefix = f"[{timestamp}] {BOT_NAME}:"
            else:
                prefix = f"[{timestamp}] {author.name}#{author.discriminator}:"
            
            content = message.content or "[Media/Embed]"
            lines.append(f"{prefix} {content}")
            
            if message.attachments:
                for attachment in message.attachments:
                    lines.append(f"  📎 Attachment: {attachment.url}")
        
        return "\n".join(lines)
    except Exception as e:
        return f"Error extracting DM conversation: {str(e)}"


def get_embed_color(command_name: str) -> int:
    """Get embed color for a command."""
    return EMBED_COLORS.get(command_name, DEEP_SPACE)


async def get_prefix(bot: commands.Bot, message: discord.Message) -> str:
    """Get custom prefix for a guild."""
    if not message.guild:
        return PREFIX
    
    from database import get_guild_setting
    prefix = await get_guild_setting(message.guild.id, "prefix")
    return prefix or PREFIX
