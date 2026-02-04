"""Shift management system for Luna - GMT+8 timezone tracking."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

import config
from database import Database
from helpers import (
    make_embed,
    require_level,
    require_admin,
    safe_delete,
    get_gmt8_now,
    format_shift_time,
    calculate_shift_hours,
    get_week_identifier_gmt8,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ShiftsCog(commands.Cog):
    """Shift management for staff tracking in GMT+8."""
    
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
    
    @property
    def db(self) -> Database:
        return self.bot.db  # type: ignore[attr-defined]
    
    @commands.command(name="clockin", aliases=["start_shift", "shiftin"])
    @commands.guild_only()
    @require_level("moderator")
    async def clockin(self, ctx: commands.Context, shift_type: str = "helper") -> None:
        """Clock in to start a shift (Staff+ only).
        
        Usage:
        ,clockin [helper|staff]
        """
        # Check if already clocked in
        active = await self.db.get_active_shift(ctx.author.id, ctx.guild.id)
        if active:
            embed = make_embed(
                action="error",
                title="❌ Already Clocked In",
                description=f"You're already clocked in since <t:{int(datetime.fromisoformat(active['start_ts_utc']).timestamp())}:R>"
            )
            await ctx.send(embed=embed)
            return
        
        # Start shift
        now_utc = utcnow()
        now_gmt8 = get_gmt8_now()
        
        shift_id = await self.db.start_shift(
            user_id=ctx.author.id,
            guild_id=ctx.guild.id,
            shift_type=shift_type.lower(),
            start_ts_utc=now_utc.isoformat(),
            start_ts_gmt8=now_gmt8.isoformat()
        )
        
        embed = make_embed(
            action="shift",
            title="🌙 Shift Started",
            description=f"**Type:** {shift_type.title()}\n**Started:** <t:{int(now_utc.timestamp())}:F>\n**GMT+8:** {format_shift_time(now_gmt8)}"
        )
        embed.set_footer(text=f"Shift ID: {shift_id} | Use ,clockout to end your shift")
        
        await ctx.send(embed=embed)
        await safe_delete(ctx.message)
    
    @commands.command(name="clockout", aliases=["end_shift", "shiftout"])
    @commands.guild_only()
    @require_level("moderator")
    async def clockout(self, ctx: commands.Context, break_minutes: int = 0) -> None:
        """Clock out to end your shift (Staff+ only).
        
        Usage:
        ,clockout [break_minutes]
        """
        # Check if clocked in
        active = await self.db.get_active_shift(ctx.author.id, ctx.guild.id)
        if not active:
            embed = make_embed(
                action="error",
                title="❌ Not Clocked In",
                description="You're not currently clocked in."
            )
            await ctx.send(embed=embed)
            return
        
        # End shift
        now_utc = utcnow()
        now_gmt8 = get_gmt8_now()
        
        await self.db.end_shift(
            shift_id=active['id'],
            end_ts_utc=now_utc.isoformat(),
            end_ts_gmt8=now_gmt8.isoformat(),
            break_duration=break_minutes
        )
        
        # Calculate hours
        start_dt = datetime.fromisoformat(active['start_ts_utc'])
        hours_worked = calculate_shift_hours(start_dt, now_utc, break_minutes)
        
        # Update quota tracking
        week_id = get_week_identifier_gmt8(now_gmt8)
        current_quota = await self.db.get_quota_tracking(
            ctx.author.id,
            ctx.guild.id,
            active['shift_type'],
            week_id
        )
        
        total_hours = (current_quota['hours_logged'] if current_quota else 0) + hours_worked
        quota_met = total_hours >= config.DEFAULT_WEEKLY_QUOTAS.get(active['shift_type'], 10)
        
        await self.db.update_quota_tracking(
            user_id=ctx.author.id,
            guild_id=ctx.guild.id,
            shift_type=active['shift_type'],
            week_gmt8=week_id,
            hours_logged=total_hours,
            quota_met=quota_met
        )
        
        embed = make_embed(
            action="shift",
            title="🌙 Shift Ended",
            description=f"**Type:** {active['shift_type'].title()}\n**Duration:** {hours_worked:.2f} hours\n**Break Time:** {break_minutes} minutes\n\n**Weekly Total:** {total_hours:.2f}h\n**Quota Status:** {'✅ Met' if quota_met else '⚠️ Not Met'}"
        )
        embed.set_footer(text=f"Shift ID: {active['id']}")
        
        await ctx.send(embed=embed)
        await safe_delete(ctx.message)
    
    @commands.command(name="myshifts")
    @commands.guild_only()
    @require_level("moderator")
    async def myshifts(self, ctx: commands.Context, limit: int = 10) -> None:
        """View your recent shifts (Staff+ only).
        
        Usage:
        ,myshifts [limit]
        """
        shifts = await self.db.get_user_shifts(ctx.author.id, ctx.guild.id, limit)
        
        if not shifts:
            embed = make_embed(
                action="shift",
                title="🌙 Your Shifts",
                description="No shifts recorded."
            )
            await ctx.send(embed=embed)
            return
        
        description = ""
        for shift in shifts:
            start = datetime.fromisoformat(shift['start_ts_utc'])
            status = shift['status'].title()
            
            if shift['status'] == 'completed':
                end = datetime.fromisoformat(shift['end_ts_utc'])
                hours = calculate_shift_hours(start, end, shift['break_duration'])
                description += f"**ID {shift['id']}** - {shift['shift_type'].title()} | {hours:.2f}h | {status}\n"
                description += f"<t:{int(start.timestamp())}:f> → <t:{int(end.timestamp())}:f>\n\n"
            else:
                description += f"**ID {shift['id']}** - {shift['shift_type'].title()} | {status}\n"
                description += f"Started: <t:{int(start.timestamp())}:R>\n\n"
        
        embed = make_embed(
            action="shift",
            title="🌙 Your Recent Shifts",
            description=description.strip()
        )
        
        await ctx.send(embed=embed)
        await safe_delete(ctx.message)
    
    @commands.command(name="shiftquota")
    @commands.guild_only()
    @require_level("moderator")
    async def shiftquota(self, ctx: commands.Context) -> None:
        """Check your weekly shift quota (Staff+ only).
        
        Usage:
        ,shiftquota
        """
        now_gmt8 = get_gmt8_now()
        week_id = get_week_identifier_gmt8(now_gmt8)
        
        # Get quota for helper and staff
        helper_quota = await self.db.get_quota_tracking(
            ctx.author.id,
            ctx.guild.id,
            "helper",
            week_id
        )
        staff_quota = await self.db.get_quota_tracking(
            ctx.author.id,
            ctx.guild.id,
            "staff",
            week_id
        )
        
        helper_hours = helper_quota['hours_logged'] if helper_quota else 0
        staff_hours = staff_quota['hours_logged'] if staff_quota else 0
        
        helper_required = config.DEFAULT_WEEKLY_QUOTAS.get("helper", 10)
        staff_required = config.DEFAULT_WEEKLY_QUOTAS.get("staff", 20)
        
        description = f"**Week:** {week_id}\n\n"
        description += f"**Helper Shifts:**\n"
        description += f"Hours Logged: {helper_hours:.2f}h / {helper_required}h\n"
        description += f"Status: {'✅ Quota Met' if helper_hours >= helper_required else '⚠️ Below Quota'}\n\n"
        description += f"**Staff Shifts:**\n"
        description += f"Hours Logged: {staff_hours:.2f}h / {staff_required}h\n"
        description += f"Status: {'✅ Quota Met' if staff_hours >= staff_required else '⚠️ Below Quota'}"
        
        embed = make_embed(
            action="shift",
            title="🌙 Weekly Shift Quota",
            description=description
        )
        
        await ctx.send(embed=embed)
        await safe_delete(ctx.message)
    
    @commands.command(name="shiftleaderboard", aliases=["shiftlb"])
    @commands.guild_only()
    @require_admin()
    async def shiftleaderboard(self, ctx: commands.Context, shift_type: str = "all") -> None:
        """View shift leaderboard (Admin only).
        
        Usage:
        ,shiftleaderboard [helper|staff|all]
        """
        # This would require aggregating shift data
        # For simplicity, just showing a placeholder
        embed = make_embed(
            action="shift",
            title="🌙 Shift Leaderboard",
            description="Leaderboard feature coming soon.\n\nThis will show top performers based on hours logged."
        )
        
        await ctx.send(embed=embed)
        await safe_delete(ctx.message)
    
    @commands.command(name="shiftconfig")
    @commands.guild_only()
    @require_admin()
    async def shiftconfig(self, ctx: commands.Context, role: discord.Role, shift_type: str, afk_timeout: int, weekly_quota: int) -> None:
        """Configure shift settings (Admin only).
        
        Usage:
        ,shiftconfig @role helper 300 10
        """
        await self.db.set_shift_config(
            guild_id=ctx.guild.id,
            role_id=role.id,
            shift_type=shift_type.lower(),
            afk_timeout=afk_timeout,
            weekly_quota=weekly_quota
        )
        
        embed = make_embed(
            action="success",
            title="✅ Shift Config Updated",
            description=f"**Role:** {role.mention}\n**Type:** {shift_type.title()}\n**AFK Timeout:** {afk_timeout}s\n**Weekly Quota:** {weekly_quota}h"
        )
        
        await ctx.send(embed=embed)
        await safe_delete(ctx.message)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ShiftsCog(bot))
