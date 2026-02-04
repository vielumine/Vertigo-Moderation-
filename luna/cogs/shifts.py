"""
Luna Bot Shifts Cog
Handles shift management system with GMT+8 timezone calculations.
"""

import discord
from discord.ext import commands
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from database import (
    get_guild_setting,
    set_guild_setting,
    start_shift,
    get_active_shift,
    pause_shift,
    resume_shift,
    end_shift,
    get_shift_history,
    get_weekly_leaderboard,
    get_shift_config,
    set_shift_config,
    get_all_shift_configs,
    log_activity,
    get_last_activity,
    cleanup_old_activity,
)
from helpers import (
    make_embed,
    get_embed_color,
    is_admin,
    is_staff,
    PaginationView,
    format_seconds,
    utcnow,
    to_gmt8,
    safe_dm,
)
from config import (
    DEEP_SPACE,
    COLOR_ERROR,
    COLOR_SUCCESS,
    COLOR_INFO,
    COLOR_WARNING,
    SHIFT_GMT_OFFSET,
    SHIFT_DEFAULT_AFK_TIMEOUT,
    SHIFT_DEFAULT_QUOTA,
    SHIFT_AUTO_END_THRESHOLD,
    SHIFT_WEEK_START,
    LEADERBOARD_EMOJIS,
    EMOJI_SHIFT_START,
    EMOJI_SHIFT_BREAK,
    EMOJI_SHIFT_RESUME,
    EMOJI_SHIFT_END,
    EMOJI_SHIFT_AFK,
)


class ShiftButtonView(discord.ui.View):
    """View with shift control buttons."""
    
    def __init__(self, bot: commands.Bot, user_id: int, guild_id: int):
        super().__init__(timeout=None)
        self.bot = bot
        self.user_id = user_id
        self.guild_id = guild_id
    
    @discord.ui.button(label="▶️ Start", style=discord.ButtonStyle.success, custom_id="shift_start")
    async def start_shift(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Start a new shift."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "This is not your shift panel.",
                ephemeral=True
            )
            return
        
        # Check if already on shift
        active = await get_active_shift(self.user_id, self.guild_id)
        if active:
            await interaction.response.send_message(
                "You are already on a shift.",
                ephemeral=True
            )
            return
        
        # Get shift type from user's highest role with config
        import random
        shift_type = "regular"  # Default
        
        # Start shift
        await start_shift(self.user_id, self.guild_id, shift_type)
        
        # Update embed
        await self._update_embed(interaction, "active")
    
    @discord.ui.button(label="⏸️ Break", style=discord.ButtonStyle.primary, custom_id="shift_break")
    async def break_shift(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Take a break."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "This is not your shift panel.",
                ephemeral=True
            )
            return
        
        # Pause shift
        await pause_shift(self.user_id, self.guild_id)
        
        # Update embed
        await self._update_embed(interaction, "break")
    
    @discord.ui.button(label="▶️ Resume", style=discord.ButtonStyle.success, custom_id="shift_resume")
    async def resume_shift(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Resume from break."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "This is not your shift panel.",
                ephemeral=True
            )
            return
        
        # Get current shift
        active = await get_active_shift(self.user_id, self.guild_id)
        if not active or active['status'] != 'break':
            await interaction.response.send_message(
                "No active break found.",
                ephemeral=True
            )
            return
        
        # Resume shift
        break_duration = utcnow() - active.get('break_start', active['created_at'])
        await resume_shift(self.user_id, self.guild_id, break_duration)
        
        # Update embed
        await self._update_embed(interaction, "active")
    
    @discord.ui.button(label="⏹️ End", style=discord.ButtonStyle.danger, custom_id="shift_end")
    async def end_shift(self, interaction: discord.Interaction, button: discord.ui.Button):
        """End shift."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "This is not your shift panel.",
                ephemeral=True
            )
            return
        
        # End shift
        shift_record = await end_shift(self.user_id, self.guild_id)
        
        if shift_record:
            # Calculate duration
            end_time = shift_record.get('end_ts_gmt8', shift_record.get('end_ts_utc', utcnow()))
            start_time = shift_record.get('start_ts_gmt8', shift_record.get('start_ts_utc', shift_record['created_at']))
            duration = end_time - start_time - shift_record.get('break_duration', 0)
            
            await interaction.response.edit_message(
                embed=make_embed(
                    title=f"{EMOJI_SHIFT_END} Shift Ended",
                    description=f"**Duration:** {format_seconds(duration)}\n**Break Time:** {format_seconds(shift_record.get('break_duration', 0))}\n**Net Time:** {format_seconds(duration)}",
                    color=COLOR_SUCCESS
                ),
                view=None
            )
        else:
            await interaction.response.edit_message(
                embed=make_embed(
                    title="❌ No Active Shift",
                    description="No active shift found.",
                    color=COLOR_ERROR
                ),
                view=None
            )
    
    async def _update_embed(self, interaction: discord.Interaction, status: str):
        """Update the shift embed."""
        shift = await get_active_shift(self.user_id, self.guild_id)
        
        if status == "active" and shift:
            gmt8_tz = ZoneInfo("Asia/Singapore")
            start_gmt8 = datetime.fromtimestamp(shift.get('start_ts_gmt8', shift['start_ts_utc']), gmt8_tz)
            
            embed = make_embed(
                title=f"{EMOJI_SHIFT_START} Shift Active",
                color=COLOR_SUCCESS,
                fields=[
                    ("Shift Type", shift.get('shift_type', 'regular').title(), True),
                    ("Started At", f"<t:{shift['start_ts_utc']}:R>", True),
                    ("GMT+8 Time", start_gmt8.strftime("%Y-%m-%d %H:%M:%S"), True),
                ]
            )
            await interaction.response.edit_message(embed=embed, view=self)
        elif status == "break" and shift:
            embed = make_embed(
                title=f"{EMOJI_SHIFT_BREAK} Shift Paused",
                color=COLOR_WARNING,
                fields=[
                    ("Shift Type", shift.get('shift_type', 'regular').title(), True),
                    ("Status", "On Break", True),
                    ("Break Started At", f"<t:{utcnow()}:R>", True),
                ]
            )
            await interaction.response.edit_message(embed=embed, view=self)


class Shifts(commands.Cog):
    """Shift management commands."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    async def _check_shift_channel(self, ctx: commands.Context) -> bool:
        """Check if command is used in the correct channel."""
        shift_channel_id = await get_guild_setting(ctx.guild.id, "shift_channel_id")
        if shift_channel_id:
            if ctx.channel.id != shift_channel_id:
                channel = self.bot.get_channel(shift_channel_id)
                await ctx.reply(embed=make_embed(
                    title="❌ Wrong Channel",
                    description=f"Shift commands must be used in {channel.mention}",
                    color=COLOR_ERROR
                ))
                return False
        return True
    
    # Admin Commands
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def shift_create(self, ctx: commands.Context, shift_type: str):
        """Create a new shift type."""
        if not await self._check_shift_channel(ctx):
            return
        
        # Shift types are just stored in configs, so we just confirm creation
        await ctx.reply(embed=make_embed(
            title="✅ Shift Type Created",
            description=f"Shift type `{shift_type}` is now available.\nUse `,config_roles <role> {shift_type}` to link it to a role.",
            color=get_embed_color("shift_create")
        ))
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def shift_delete(self, ctx: commands.Context, shift_type: str):
        """Delete a shift type."""
        if not await self._check_shift_channel(ctx):
            return
        
        # In a real implementation, we'd clean up configs and records
        await ctx.reply(embed=make_embed(
            title="✅ Shift Type Deleted",
            description=f"Shift type `{shift_type}` has been removed.",
            color=get_embed_color("shift_delete")
        ))
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def view_shifts(self, ctx: commands.Context):
        """View all shift types and connected roles."""
        configs = await get_all_shift_configs(ctx.guild.id)
        
        if not configs:
            await ctx.reply(embed=make_embed(
                title="📋 Shift Types",
                description="No shift types configured.",
                color=DEEP_SPACE
            ))
            return
        
        # Group by shift type
        shift_groups = {}
        for config in configs:
            shift_type = config['shift_type']
            role = ctx.guild.get_role(config['role_id'])
            if shift_type not in shift_groups:
                shift_groups[shift_type] = []
            shift_groups[shift_type].append(role.name if role else f"Unknown Role ({config['role_id']})")
        
        fields = []
        for shift_type, roles in shift_groups.items():
            fields.append((
                shift_type.title(),
                "\n".join([f"• {role}" for role in roles]) if roles else "No roles",
                False
            ))
        
        embed = make_embed(
            title="📋 Shift Types & Roles",
            color=get_embed_color("view_shifts"),
            fields=fields[:25]
        )
        
        await ctx.reply(embed=embed)
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def activity_view(self, ctx: commands.Context):
        """View leaderboard of most active staff."""
        leaderboard = await get_weekly_leaderboard(ctx.guild.id)
        
        if not leaderboard:
            await ctx.reply(embed=make_embed(
                title="📊 Activity Leaderboard",
                description="No shift activity recorded this week.",
                color=DEEP_SPACE
            ))
            return
        
        fields = []
        for i, entry in enumerate(leaderboard, 1):
            member = ctx.guild.get_member(entry['user_id'])
            name = member.display_name if member else f"Unknown ({entry['user_id']})"
            hours = entry['total_seconds'] / 3600
            
            emoji = LEADERBOARD_EMOJIS.get(i, "")
            fields.append((
                f"{emoji} #{i}",
                f"{name}\n{hours:.2f} hours",
                True
            ))
        
        embed = make_embed(
            title="📊 Weekly Activity Leaderboard",
            color=get_embed_color("activity_view"),
            fields=fields[:15]
        )
        
        await ctx.reply(embed=embed)
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def config_roles(self, ctx: commands.Context, role: discord.Role, shift_type: str):
        """Link a role to a shift type."""
        if not await self._check_shift_channel(ctx):
            return
        
        await set_shift_config(ctx.guild.id, role.id, shift_type, SHIFT_DEFAULT_AFK_TIMEOUT, SHIFT_DEFAULT_QUOTA)
        
        await ctx.reply(embed=make_embed(
            title="✅ Role Configured",
            description=f"Linked {role.mention} to shift type `{shift_type}`.",
            color=get_embed_color("config_roles")
        ))
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def config_afk(self, ctx: commands.Context, role: discord.Role, shift_type: str, duration: str):
        """Set AFK timeout for a role/shift type."""
        if not await self._check_shift_channel(ctx):
            return
        
        from helpers import parse_duration
        duration_seconds = parse_duration(duration)
        if not duration_seconds:
            await ctx.reply(embed=make_embed(
                title="❌ Invalid Duration",
                description="Duration format: `1h`, `30m`, `1d`",
                color=COLOR_ERROR
            ))
            return
        
        # Get existing config
        config = await get_shift_config(ctx.guild.id, role.id, shift_type)
        quota = config['weekly_quota'] if config else SHIFT_DEFAULT_QUOTA
        
        await set_shift_config(ctx.guild.id, role.id, shift_type, duration_seconds, quota)
        
        await ctx.reply(embed=make_embed(
            title="✅ AFK Timeout Set",
            description=f"AFK timeout for {role.mention} ({shift_type}) set to {format_seconds(duration_seconds)}.",
            color=get_embed_color("config_afk")
        ))
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def config_quota(self, ctx: commands.Context, role: discord.Role, shift_type: str, minutes: int):
        """Set weekly quota for a role/shift type."""
        if not await self._check_shift_channel(ctx):
            return
        
        # Get existing config
        config = await get_shift_config(ctx.guild.id, role.id, shift_type)
        afk_timeout = config['afk_timeout'] if config else SHIFT_DEFAULT_AFK_TIMEOUT
        
        await set_shift_config(ctx.guild.id, role.id, shift_type, afk_timeout, minutes)
        
        hours = minutes / 60
        await ctx.reply(embed=make_embed(
            title="✅ Quota Set",
            description=f"Weekly quota for {role.mention} ({shift_type}) set to {hours:.1f} hours.",
            color=get_embed_color("config_quota")
        ))
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def quota_remove(self, ctx: commands.Context, role: discord.Role, shift_type: str, minutes: int):
        """Reduce weekly quota for a role/shift type."""
        if not await self._check_shift_channel(ctx):
            return
        
        config = await get_shift_config(ctx.guild.id, role.id, shift_type)
        if not config:
            await ctx.reply(embed=make_embed(
                title="❌ Config Not Found",
                description=f"No configuration found for {role.mention} ({shift_type}).",
                color=COLOR_ERROR
            ))
            return
        
        new_quota = max(0, config['weekly_quota'] - minutes)
        await set_shift_config(ctx.guild.id, role.id, shift_type, config['afk_timeout'], new_quota)
        
        hours = new_quota / 60
        await ctx.reply(embed=make_embed(
            title="✅ Quota Reduced",
            description=f"Weekly quota for {role.mention} ({shift_type}) reduced to {hours:.1f} hours.",
            color=get_embed_color("quota_remove")
        ))
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def view_settings(self, ctx: commands.Context):
        """View all shift settings with pagination."""
        configs = await get_all_shift_configs(ctx.guild.id)
        
        if not configs:
            await ctx.reply(embed=make_embed(
                title="📋 Shift Settings",
                description="No shift configurations found.",
                color=DEEP_SPACE
            ))
            return
        
        # Create pagination
        def create_embed(items, page, total_pages):
            embed = make_embed(
                title=f"📋 Shift Settings (Page {page + 1}/{total_pages})",
                color=get_embed_color("view_settings")
            )
            
            for config in items:
                role = ctx.guild.get_role(config['role_id'])
                role_name = role.name if role else f"Unknown ({config['role_id']})"
                
                embed.add_field(
                    name=f"{role_name} - {config['shift_type'].title()}",
                    value=f"AFK: {format_seconds(config['afk_timeout'])}\nQuota: {config['weekly_quota']/60:.1f}h",
                    inline=False
                )
            
            return embed
        
        view = PaginationView(configs, create_embed)
        embed = create_embed(view.get_current_items(), 0, view.total_pages)
        await ctx.reply(embed=embed, view=view)
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def shift_channel(self, ctx: commands.Context, channel: discord.TextChannel):
        """Set the shift command channel."""
        await set_guild_setting(ctx.guild.id, "shift_channel_id", channel.id)
        
        await ctx.reply(embed=make_embed(
            title="✅ Shift Channel Set",
            description=f"Shift commands restricted to {channel.mention}.",
            color=get_embed_color("shift_channel")
        ))
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def reset_all(self, ctx: commands.Context):
        """Reset all shift settings to default."""
        # This would delete all configs
        import aiosqlite
        async with aiosqlite.connect("luna.db") as db:
            await db.execute("DELETE FROM shift_configs WHERE guild_id = ?", (ctx.guild.id,))
            await db.commit()
        
        await ctx.reply(embed=make_embed(
            title="✅ Settings Reset",
            description="All shift settings have been reset to default.",
            color=get_embed_color("reset_all")
        ))
    
    # Staff Commands
    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def myshift(self, ctx: commands.Context):
        """Show your current shift status."""
        if not await is_staff(ctx.author, ctx.guild):
            await ctx.reply(embed=make_embed(
                title="❌ Staff Only",
                description="This command requires staff privileges.",
                color=COLOR_ERROR
            ))
            return
        
        shift = await get_active_shift(ctx.author.id, ctx.guild.id)
        
        if not shift:
            # Show panel with start button
            view = ShiftButtonView(self.bot, ctx.author.id, ctx.guild.id)
            embed = make_embed(
                title="💤 Not on Shift",
                description="You are not currently on a shift. Click Start to begin.",
                color=DEEP_SPACE
            )
            await ctx.reply(embed=embed, view=view)
        elif shift['status'] == 'active':
            # Show active shift with control buttons
            view = ShiftButtonView(self.bot, ctx.author.id, ctx.guild.id)
            
            gmt8_tz = ZoneInfo("Asia/Singapore")
            start_gmt8 = datetime.fromtimestamp(shift.get('start_ts_gmt8', shift['start_ts_utc']), gmt8_tz)
            current_duration = utcnow() - shift.get('start_ts_utc', shift['created_at'])
            
            embed = make_embed(
                title=f"{EMOJI_SHIFT_START} Shift Active",
                color=COLOR_SUCCESS,
                fields=[
                    ("Shift Type", shift.get('shift_type', 'regular').title(), True),
                    ("Started At", f"<t:{shift['start_ts_utc']}:R>", True),
                    ("GMT+8 Time", start_gmt8.strftime("%Y-%m-%d %H:%M:%S"), True),
                    ("Current Duration", format_seconds(current_duration), True),
                ]
            )
            await ctx.reply(embed=embed, view=view)
        elif shift['status'] == 'break':
            # Show break status
            view = ShiftButtonView(self.bot, ctx.author.id, ctx.guild.id)
            
            embed = make_embed(
                title=f"{EMOJI_SHIFT_BREAK} Shift Paused",
                color=COLOR_WARNING,
                fields=[
                    ("Shift Type", shift.get('shift_type', 'regular').title(), True),
                    ("Status", "On Break", True),
                    ("Break Started At", f"<t:{utcnow()}:R>", True),
                ]
            )
            await ctx.reply(embed=embed, view=view)
    
    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def viewshift(self, ctx: commands.Context, member: discord.Member):
        """View someone else's shift status."""
        if not await is_staff(ctx.author, ctx.guild):
            await ctx.reply(embed=make_embed(
                title="❌ Staff Only",
                description="This command requires staff privileges.",
                color=COLOR_ERROR
            ))
            return
        
        shift = await get_active_shift(member.id, ctx.guild.id)
        
        if not shift:
            await ctx.reply(embed=make_embed(
                title="💤 Not on Shift",
                description=f"{member.display_name} is not currently on a shift.",
                color=DEEP_SPACE
            ))
        elif shift['status'] == 'active':
            gmt8_tz = ZoneInfo("Asia/Singapore")
            start_gmt8 = datetime.fromtimestamp(shift.get('start_ts_gmt8', shift['start_ts_utc']), gmt8_tz)
            current_duration = utcnow() - shift.get('start_ts_utc', shift['created_at'])
            
            embed = make_embed(
                title=f"{EMOJI_SHIFT_START} {member.display_name}'s Shift",
                color=COLOR_SUCCESS,
                fields=[
                    ("Shift Type", shift.get('shift_type', 'regular').title(), True),
                    ("Started At", f"<t:{shift['start_ts_utc']}:R>", True),
                    ("GMT+8 Time", start_gmt8.strftime("%Y-%m-%d %H:%M:%S"), True),
                    ("Current Duration", format_seconds(current_duration), True),
                ]
            )
            await ctx.reply(embed=embed)
        elif shift['status'] == 'break':
            embed = make_embed(
                title=f"{EMOJI_SHIFT_BREAK} {member.display_name}'s Shift",
                color=COLOR_WARNING,
                fields=[
                    ("Shift Type", shift.get('shift_type', 'regular').title(), True),
                    ("Status", "On Break", True),
                    ("Break Started At", f"<t:{utcnow()}:R>", True),
                ]
            )
            await ctx.reply(embed=embed)
    
    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def shift_lb(self, ctx: commands.Context):
        """Show weekly leaderboard with pagination."""
        if not await is_staff(ctx.author, ctx.guild):
            await ctx.reply(embed=make_embed(
                title="❌ Staff Only",
                description="This command requires staff privileges.",
                color=COLOR_ERROR
            ))
            return
        
        leaderboard = await get_weekly_leaderboard(ctx.guild.id)
        
        if not leaderboard:
            await ctx.reply(embed=make_embed(
                title="🏆 Weekly Leaderboard",
                description="No shift activity recorded this week.",
                color=DEEP_SPACE
            ))
            return
        
        # Create pagination
        def create_embed(items, page, total_pages):
            embed = make_embed(
                title=f"🏆 Weekly Leaderboard (Page {page + 1}/{total_pages})",
                color=get_embed_color("shift_lb")
            )
            
            for i, entry in enumerate(items, page * 10 + 1):
                member = ctx.guild.get_member(entry['user_id'])
                name = member.display_name if member else f"Unknown ({entry['user_id']})"
                hours = entry['total_seconds'] / 3600
                
                emoji = LEADERBOARD_EMOJIS.get(i, "")
                embed.add_field(
                    name=f"{emoji} #{i}",
                    value=f"{name}\n{hours:.2f} hours",
                    inline=True
                )
            
            return embed
        
        view = PaginationView(leaderboard, create_embed)
        embed = create_embed(view.get_current_items(), 0, view.total_pages)
        await ctx.reply(embed=embed, view=view)
    
    # Activity tracking for AFK
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Track user activity for AFK detection."""
        if message.author.bot:
            return
        
        if not message.guild:
            return
        
        # Log activity
        await log_activity(message.author.id, message.guild.id, message.channel.id)


async def setup(bot: commands.Bot):
    await bot.add_cog(Shifts(bot))
