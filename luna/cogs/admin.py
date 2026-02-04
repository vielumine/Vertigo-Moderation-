"""
Luna Bot Admin Cog
Handles staff management, flagging, termination, and channel locks.
"""

import discord
from discord.ext import commands
from datetime import timedelta

from database import (
    get_guild_setting,
    add_staff_flag,
    get_active_flags,
    get_all_staff_flags,
    clear_staff_flags,
    get_active_mute,
    remove_mute,
)
from helpers import (
    make_embed,
    get_embed_color,
    parse_duration,
    format_seconds,
    safe_dm,
    add_loading_reaction,
    log_to_modlog_channel,
    is_staff,
    is_admin,
    utcnow,
)
from config import (
    DEEP_SPACE,
    COLOR_ERROR,
    COLOR_SUCCESS,
    COLOR_WARNING,
    MAX_STAFF_FLAGS,
)


class Admin(commands.Cog):
    """Admin commands for staff management."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    async def _check_mod_channel(self, ctx: commands.Context) -> bool:
        """Check if command is used in the correct channel."""
        mod_channel_id = await get_guild_setting(ctx.guild.id, "mod_channel_id")
        if mod_channel_id:
            if ctx.channel.id != mod_channel_id:
                channel = self.bot.get_channel(mod_channel_id)
                await ctx.reply(embed=make_embed(
                    title="❌ Wrong Channel",
                    description=f"Admin commands must be used in {channel.mention}",
                    color=COLOR_ERROR
                ))
                return False
        return True
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def flag(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
        """Flag a staff member."""
        if not await self._check_mod_channel(ctx):
            return
        
        if not await is_staff(member, ctx.guild):
            await ctx.reply(embed=make_embed(
                title="❌ Not a Staff Member",
                description=f"{member.mention} is not a staff member.",
                color=COLOR_ERROR
            ))
            return
        
        stop_loading = add_loading_reaction(ctx.message)
        
        # Add flag (30 days default)
        expires_at = utcnow() + (30 * 24 * 3600)  # 30 days
        flag_id = await add_staff_flag(member.id, ctx.guild.id, ctx.author.id, reason, expires_at)
        
        # Get active flags count
        active_flags = await get_active_flags(member.id, ctx.guild.id)
        
        stop_loading()
        
        # Check if auto-termination needed
        if active_flags >= MAX_STAFF_FLAGS:
            # Terminate staff
            await self._terminate_staff(ctx, member, f"Auto-termination: Reached {MAX_STAFF_FLAGS} flags")
        else:
            # Log to modlog
            log_embed = make_embed(
                title="🚩 Staff Flagged",
                color=get_embed_color("flag"),
                fields=[
                    ("Staff Member", f"{member.mention} (ID: {member.id})", True),
                    ("Flagger", ctx.author.mention, True),
                    ("Reason", reason, True),
                    ("Active Flags", f"{active_flags}/{MAX_STAFF_FLAGS}", True),
                    ("Expires", f"<t:{expires_at}:R>", True),
                ],
                timestamp=True
            )
            await log_to_modlog_channel(ctx.guild, log_embed)
            
            # Reply
            await ctx.reply(embed=make_embed(
                title=f"🚩 {member.name} Flagged",
                description=f"**Reason:** {reason}\n**Active Flags:** {active_flags}/{MAX_STAFF_FLAGS}\n**Expires:** <t:{expires_at}:R>",
                color=get_embed_color("flag")
            ))
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def unflag(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
        """Clear all flags for a staff member."""
        if not await self._check_mod_channel(ctx):
            return
        
        stop_loading = add_loading_reaction(ctx.message)
        
        await clear_staff_flags(member.id, ctx.guild.id)
        
        stop_loading()
        
        # Log to modlog
        log_embed = make_embed(
            title="✅ Flags Cleared",
            color=get_embed_color("unflag"),
            fields=[
                ("Staff Member", f"{member.mention} (ID: {member.id})", True),
                ("Admin", ctx.author.mention, True),
                ("Reason", reason, True),
            ],
            timestamp=True
        )
        await log_to_modlog_channel(ctx.guild, log_embed)
        
        # Reply
        await ctx.reply(embed=make_embed(
            title=f"✅ {member.name}'s Flags Cleared",
            description=f"**Reason:** {reason}",
            color=get_embed_color("unflag")
        ))
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def terminate(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
        """Terminate a staff member."""
        if not await self._check_mod_channel(ctx):
            return
        
        stop_loading = add_loading_reaction(ctx.message)
        
        await self._terminate_staff(ctx, member, reason)
        
        stop_loading()
    
    async def _terminate_staff(self, ctx: commands.Context, member: discord.Member, reason: str):
        """Internal method to terminate staff."""
        # Get staff role
        from database import get_guild_setting
        staff_role_id = await get_guild_setting(ctx.guild.id, "staff_role_id")
        if staff_role_id:
            staff_role = ctx.guild.get_role(staff_role_id)
            if staff_role:
                await member.remove_roles(staff_role, reason=reason)
        
        # Clear flags
        await clear_staff_flags(member.id, ctx.guild.id)
        
        # Timeout for 1 week
        timeout_duration = timedelta(days=7)
        await member.timeout(timeout_duration, reason=reason)
        
        # Send DM
        await safe_dm(member, embed=make_embed(
            title=f"🚨 Terminated from {ctx.guild.name}",
            description=f"You have been terminated from staff by {ctx.author.mention}.\n**Reason:** {reason}\nYou have been timed out for 7 days.",
            color=COLOR_ERROR
        ))
        
        # Log to modlog
        log_embed = make_embed(
            title="🚨 Staff Terminated",
            color=get_embed_color("terminate"),
            fields=[
                ("Staff Member", f"{member.mention} (ID: {member.id})", True),
                ("Admin", ctx.author.mention, True),
                ("Reason", reason, True),
                ("Timeout Duration", "7 days", True),
            ],
            timestamp=True
        )
        await log_to_modlog_channel(ctx.guild, log_embed)
        
        # Reply
        await ctx.reply(embed=make_embed(
            title=f"🚨 {member.name} Terminated",
            description=f"**Reason:** {reason}\nStaff role removed. Member timed out for 7 days.",
            color=get_embed_color("terminate")
        ))
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def stafflist(self, ctx: commands.Context):
        """View all staff members and their flag counts."""
        stop_loading = add_loading_reaction(ctx.message)
        
        # Get all staff with flags
        flagged_staff = await get_all_staff_flags(ctx.guild.id)
        
        # Get staff role
        from database import get_guild_setting
        staff_role_id = await get_guild_setting(ctx.guild.id, "staff_role_id")
        staff_role = ctx.guild.get_role(staff_role_id) if staff_role_id else None
        
        # Get all staff members
        if staff_role:
            all_staff = staff_role.members
        else:
            await ctx.reply(embed=make_embed(
                title="❌ Staff Role Not Configured",
                description="Use `,setup staff_role` to configure the staff role.",
                color=COLOR_ERROR
            ))
            return
        
        # Build flag count dictionary
        flag_counts = {f['user_id']: f['flag_count'] for f in flagged_staff}
        
        # Build embed fields
        fields = []
        for staff in all_staff:
            flag_count = flag_counts.get(staff.id, 0)
            
            # Determine emoji based on flag count
            if flag_count == 0:
                emoji = ""
            elif flag_count <= 2:
                emoji = "✅"
            elif flag_count == 3:
                emoji = "⚠️"
            elif flag_count == 4:
                emoji = "🟠"
            else:
                emoji = "🔴"
            
            fields.append((
                f"{emoji} {staff.display_name}",
                f"Flags: {flag_count}/{MAX_STAFF_FLAGS}",
                True
            ))
        
        stop_loading()
        
        # Create embed with pagination if needed
        if fields:
            embed = make_embed(
                title="📋 Staff List",
                color=DEEP_SPACE,
                fields=fields[:25]  # Discord limit
            )
            await ctx.reply(embed=embed)
        else:
            await ctx.reply(embed=make_embed(
                title="📋 Staff List",
                description="No staff members found.",
                color=DEEP_SPACE
            ))
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def lockchannels(self, ctx: commands.Context):
        """Lock all configured categories for the member role."""
        stop_loading = add_loading_reaction(ctx.message)
        
        # Get lock categories
        lock_categories_str = await get_guild_setting(ctx.guild.id, "lock_categories")
        if not lock_categories_str or lock_categories_str == "[]":
            await ctx.reply(embed=make_embed(
                title="❌ No Lock Categories",
                description="No lock categories configured. Use `,setup` to configure.",
                color=COLOR_ERROR
            ))
            return
        
        import json
        try:
            lock_categories = json.loads(lock_categories_str)
        except:
            await ctx.reply(embed=make_embed(
                title="❌ Invalid Categories",
                description="Lock categories data is corrupted. Contact an administrator.",
                color=COLOR_ERROR
            ))
            return
        
        # Get member role
        member_role_id = await get_guild_setting(ctx.guild.id, "member_role_id")
        if not member_role_id:
            await ctx.reply(embed=make_embed(
                title="❌ No Member Role",
                description="No member role configured. Use `,setup member_role` to configure.",
                color=COLOR_ERROR
            ))
            return
        
        member_role = ctx.guild.get_role(member_role_id)
        if not member_role:
            await ctx.reply(embed=make_embed(
                title="❌ Invalid Member Role",
                description="Configured member role no longer exists. Use `,setup member_role` to update.",
                color=COLOR_ERROR
            ))
            return
        
        # Lock channels
        locked_count = 0
        for category_id in lock_categories:
            category = ctx.guild.get_channel(category_id)
            if category and isinstance(category, discord.CategoryChannel):
                for channel in category.channels:
                    await channel.set_permissions(member_role, send_messages=False)
                    locked_count += 1
        
        stop_loading()
        
        # Log to modlog
        log_embed = make_embed(
            title="🔒 Channels Locked",
            color=COLOR_WARNING,
            fields=[
                ("Channels Locked", str(locked_count), True),
                ("Categories", str(len(lock_categories)), True),
                ("Admin", ctx.author.mention, True),
            ],
            timestamp=True
        )
        await log_to_modlog_channel(ctx.guild, log_embed)
        
        # Reply
        await ctx.reply(embed=make_embed(
            title="🔒 Channels Locked",
            description=f"Locked {locked_count} channel(s) across {len(lock_categories)} category/ies for the member role.",
            color=COLOR_WARNING
        ))
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def unlockchannels(self, ctx: commands.Context):
        """Unlock all configured categories for the member role."""
        stop_loading = add_loading_reaction(ctx.message)
        
        # Get lock categories
        lock_categories_str = await get_guild_setting(ctx.guild.id, "lock_categories")
        if not lock_categories_str or lock_categories_str == "[]":
            await ctx.reply(embed=make_embed(
                title="❌ No Lock Categories",
                description="No lock categories configured. Use `,setup` to configure.",
                color=COLOR_ERROR
            ))
            return
        
        import json
        try:
            lock_categories = json.loads(lock_categories_str)
        except:
            await ctx.reply(embed=make_embed(
                title="❌ Invalid Categories",
                description="Lock categories data is corrupted. Contact an administrator.",
                color=COLOR_ERROR
            ))
            return
        
        # Get member role
        member_role_id = await get_guild_setting(ctx.guild.id, "member_role_id")
        if not member_role_id:
            await ctx.reply(embed=make_embed(
                title="❌ No Member Role",
                description="No member role configured. Use `,setup member_role` to configure.",
                color=COLOR_ERROR
            ))
            return
        
        member_role = ctx.guild.get_role(member_role_id)
        if not member_role:
            await ctx.reply(embed=make_embed(
                title="❌ Invalid Member Role",
                description="Configured member role no longer exists. Use `,setup member_role` to update.",
                color=COLOR_ERROR
            ))
            return
        
        # Unlock channels
        unlocked_count = 0
        for category_id in lock_categories:
            category = ctx.guild.get_channel(category_id)
            if category and isinstance(category, discord.CategoryChannel):
                for channel in category.channels:
                    await channel.set_permissions(member_role, overwrite=None)
                    unlocked_count += 1
        
        stop_loading()
        
        # Log to modlog
        log_embed = make_embed(
            title="🔓 Channels Unlocked",
            color=COLOR_SUCCESS,
            fields=[
                ("Channels Unlocked", str(unlocked_count), True),
                ("Categories", str(len(lock_categories)), True),
                ("Admin", ctx.author.mention, True),
            ],
            timestamp=True
        )
        await log_to_modlog_channel(ctx.guild, log_embed)
        
        # Reply
        await ctx.reply(embed=make_embed(
            title="🔓 Channels Unlocked",
            description=f"Unlocked {unlocked_count} channel(s) across {len(lock_categories)} category/ies for the member role.",
            color=COLOR_SUCCESS
        ))


async def setup(bot: commands.Bot):
    await bot.add_cog(Admin(bot))
