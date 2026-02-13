"""Shift management system for Luna - GMT+8 timezone tracking."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

import config
from database import Database, GuildSettings
from helpers import (
    calculate_shift_hours,
    extract_id,
    format_shift_time,
    get_gmt8_now,
    get_week_identifier_gmt8,
    is_admin_member,
    make_embed,
    require_admin,
    require_level,
    role_level_for_member,
    safe_delete,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ShiftTypeSelect(discord.ui.Select):
    """Select menu for choosing shift type in the panel."""

    def __init__(self, current_type: str) -> None:
        options = [
            discord.SelectOption(
                label="Helper Shift",
                value="helper",
                emoji="🤝",
                default=current_type == "helper",
            ),
            discord.SelectOption(
                label="Staff Shift",
                value="staff",
                emoji="🛡️",
                default=current_type == "staff",
            ),
        ]
        super().__init__(placeholder="Select shift type", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        if not isinstance(view, ManageShiftView):
            return
        view.shift_type = self.values[0]
        await interaction.response.send_message(
            f"✅ Shift type set to **{self.values[0].title()}**.",
            ephemeral=True,
        )


class ShiftClockOutModal(discord.ui.Modal):
    """Modal for clocking out with optional break time."""

    def __init__(self, cog: "ShiftsCog") -> None:
        super().__init__(title="Clock Out")
        self.cog = cog
        self.break_minutes = discord.ui.TextInput(
            label="Break minutes (optional)",
            placeholder="0",
            required=False,
            max_length=6,
        )
        self.add_item(self.break_minutes)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("❌ This action can only be used in a server.", ephemeral=True)
            return

        try:
            break_minutes = int(self.break_minutes.value.strip() or 0)
        except ValueError:
            await interaction.response.send_message("❌ Break minutes must be a number.", ephemeral=True)
            return

        embed, success = await self.cog._end_shift(interaction.user, interaction.guild, break_minutes)
        await interaction.response.send_message(embed=embed, ephemeral=not success)


class ShiftLeaderboardModal(discord.ui.Modal):
    """Modal for selecting leaderboard type."""

    def __init__(self, cog: "ShiftsCog") -> None:
        super().__init__(title="Shift Leaderboard")
        self.cog = cog
        self.shift_type = discord.ui.TextInput(
            label="Type (helper/staff/all)",
            placeholder="all",
            required=True,
            max_length=10,
        )
        self.add_item(self.shift_type)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        shift_type = self.shift_type.value.strip().lower()
        if shift_type not in {"helper", "staff", "all"}:
            await interaction.response.send_message(
                "❌ Shift type must be helper, staff, or all.",
                ephemeral=True,
            )
            return

        embed = await self.cog._build_leaderboard_embed(interaction.guild, shift_type)
        await interaction.response.send_message(embed=embed)


class ShiftConfigModal(discord.ui.Modal):
    """Modal for configuring shift settings."""

    def __init__(self, cog: "ShiftsCog") -> None:
        super().__init__(title="Shift Configuration")
        self.cog = cog
        self.role_input = discord.ui.TextInput(
            label="Role (mention or ID)",
            placeholder="@Role",
            required=True,
        )
        self.shift_type = discord.ui.TextInput(
            label="Shift type (helper/staff)",
            placeholder="helper",
            required=True,
            max_length=10,
        )
        self.afk_timeout = discord.ui.TextInput(
            label="AFK timeout seconds",
            placeholder="300",
            required=True,
            max_length=6,
        )
        self.weekly_quota = discord.ui.TextInput(
            label="Weekly quota hours",
            placeholder="10",
            required=True,
            max_length=6,
        )
        self.add_item(self.role_input)
        self.add_item(self.shift_type)
        self.add_item(self.afk_timeout)
        self.add_item(self.weekly_quota)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        role_id = extract_id(self.role_input.value)
        if not role_id:
            await interaction.response.send_message("❌ Please provide a valid role mention or ID.", ephemeral=True)
            return

        if not interaction.guild:
            await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
            return

        role = interaction.guild.get_role(role_id)
        if not role:
            await interaction.response.send_message("❌ Role not found in this server.", ephemeral=True)
            return

        shift_type = self.shift_type.value.strip().lower()
        if shift_type not in {"helper", "staff"}:
            await interaction.response.send_message("❌ Shift type must be helper or staff.", ephemeral=True)
            return

        try:
            afk_timeout = int(self.afk_timeout.value.strip())
            weekly_quota = int(self.weekly_quota.value.strip())
        except ValueError:
            await interaction.response.send_message("❌ AFK timeout and weekly quota must be numbers.", ephemeral=True)
            return

        embed = await self.cog._update_shift_config(interaction.guild, role, shift_type, afk_timeout, weekly_quota)
        await interaction.response.send_message(embed=embed, ephemeral=True)


class ManageShiftView(discord.ui.View):
    """Interactive shift management panel."""

    def __init__(self, cog: "ShiftsCog") -> None:
        super().__init__(timeout=300)
        self.cog = cog
        self.shift_type = "helper"
        self.add_item(ShiftTypeSelect(self.shift_type))

    async def _settings(self, interaction: discord.Interaction) -> GuildSettings | None:
        if not interaction.guild:
            return None
        return await self.cog.db.get_guild_settings(interaction.guild.id, default_prefix=config.DEFAULT_PREFIX)

    async def _ensure_staff(self, interaction: discord.Interaction) -> bool:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return False
        settings = await self._settings(interaction)
        if not settings:
            return False
        return role_level_for_member(interaction.user, settings) != "member"

    async def _ensure_admin(self, interaction: discord.Interaction) -> bool:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return False
        settings = await self._settings(interaction)
        if not settings:
            return False
        return is_admin_member(interaction.user, settings)

    async def _deny(self, interaction: discord.Interaction, message: str) -> None:
        await interaction.response.send_message(message, ephemeral=True)

    @discord.ui.button(label="Clock In", style=discord.ButtonStyle.success, emoji="🟢")
    async def clock_in_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not await self._ensure_staff(interaction):
            await self._deny(interaction, "❌ Only staff can manage shifts.")
            return
        embed, success = await self.cog._start_shift(interaction.user, interaction.guild, self.shift_type)
        await interaction.response.send_message(embed=embed, ephemeral=not success)

    @discord.ui.button(label="Clock Out", style=discord.ButtonStyle.primary, emoji="⏹️")
    async def clock_out_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not await self._ensure_staff(interaction):
            await self._deny(interaction, "❌ Only staff can manage shifts.")
            return
        await interaction.response.send_modal(ShiftClockOutModal(self.cog))

    @discord.ui.button(label="My Shifts", style=discord.ButtonStyle.secondary, emoji="🗂️")
    async def my_shifts_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not await self._ensure_staff(interaction):
            await self._deny(interaction, "❌ Only staff can manage shifts.")
            return
        embed = await self.cog._build_my_shifts_embed(interaction.user, interaction.guild, limit=10)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Weekly Quota", style=discord.ButtonStyle.secondary, emoji="📊")
    async def quota_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not await self._ensure_staff(interaction):
            await self._deny(interaction, "❌ Only staff can manage shifts.")
            return
        embed = await self.cog._build_quota_embed(interaction.user, interaction.guild)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Leaderboard", style=discord.ButtonStyle.secondary, emoji="🏆")
    async def leaderboard_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not await self._ensure_admin(interaction):
            await self._deny(interaction, "❌ Only admins can view shift leaderboards.")
            return
        await interaction.response.send_modal(ShiftLeaderboardModal(self.cog))

    @discord.ui.button(label="Configure", style=discord.ButtonStyle.secondary, emoji="⚙️")
    async def configure_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not await self._ensure_admin(interaction):
            await self._deny(interaction, "❌ Only admins can configure shifts.")
            return
        await interaction.response.send_modal(ShiftConfigModal(self.cog))


class ShiftsCog(commands.Cog):
    """Shift management for staff tracking in GMT+8."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @property
    def db(self) -> Database:
        return self.bot.db  # type: ignore[attr-defined]

    async def _start_shift(
        self,
        member: discord.Member,
        guild: discord.Guild,
        shift_type: str,
    ) -> tuple[discord.Embed, bool]:
        shift_type = shift_type.lower().strip()
        if shift_type not in {"helper", "staff"}:
            embed = make_embed(
                action="error",
                title="❌ Invalid Shift Type",
                description="Shift type must be helper or staff.",
            )
            return embed, False

        active = await self.db.get_active_shift(member.id, guild.id)
        if active:
            embed = make_embed(
                action="error",
                title="❌ Already Clocked In",
                description=f"You're already clocked in since <t:{int(datetime.fromisoformat(active['start_ts_utc']).timestamp())}:R>",
            )
            return embed, False

        now_utc = utcnow()
        now_gmt8 = get_gmt8_now()

        shift_id = await self.db.start_shift(
            user_id=member.id,
            guild_id=guild.id,
            shift_type=shift_type,
            start_ts_utc=now_utc.isoformat(),
            start_ts_gmt8=now_gmt8.isoformat(),
        )

        embed = make_embed(
            action="shift",
            title="🌙 Shift Started",
            description=(
                f"**Type:** {shift_type.title()}\n"
                f"**Started:** <t:{int(now_utc.timestamp())}:F>\n"
                f"**GMT+8:** {format_shift_time(now_gmt8)}"
            ),
        )
        embed.set_footer(text=f"Shift ID: {shift_id} | Use the panel to clock out")

        return embed, True

    async def _end_shift(
        self,
        member: discord.Member,
        guild: discord.Guild,
        break_minutes: int,
    ) -> tuple[discord.Embed, bool]:
        active = await self.db.get_active_shift(member.id, guild.id)
        if not active:
            embed = make_embed(
                action="error",
                title="❌ Not Clocked In",
                description="You're not currently clocked in.",
            )
            return embed, False

        now_utc = utcnow()
        now_gmt8 = get_gmt8_now()

        await self.db.end_shift(
            shift_id=active['id'],
            end_ts_utc=now_utc.isoformat(),
            end_ts_gmt8=now_gmt8.isoformat(),
            break_duration=break_minutes,
        )

        start_dt = datetime.fromisoformat(active['start_ts_utc'])
        hours_worked = calculate_shift_hours(start_dt, now_utc, break_minutes)

        week_id = get_week_identifier_gmt8(now_gmt8)
        current_quota = await self.db.get_quota_tracking(
            member.id,
            guild.id,
            active['shift_type'],
            week_id,
        )

        total_hours = (current_quota['hours_logged'] if current_quota else 0) + hours_worked
        quota_met = total_hours >= config.DEFAULT_WEEKLY_QUOTAS.get(active['shift_type'], 10)

        await self.db.update_quota_tracking(
            user_id=member.id,
            guild_id=guild.id,
            shift_type=active['shift_type'],
            week_gmt8=week_id,
            hours_logged=total_hours,
            quota_met=quota_met,
        )

        embed = make_embed(
            action="shift",
            title="🌙 Shift Ended",
            description=(
                f"**Type:** {active['shift_type'].title()}\n"
                f"**Duration:** {hours_worked:.2f} hours\n"
                f"**Break Time:** {break_minutes} minutes\n\n"
                f"**Weekly Total:** {total_hours:.2f}h\n"
                f"**Quota Status:** {'✅ Met' if quota_met else '⚠️ Not Met'}"
            ),
        )
        embed.set_footer(text=f"Shift ID: {active['id']}")

        return embed, True

    async def _build_my_shifts_embed(
        self,
        member: discord.Member,
        guild: discord.Guild,
        limit: int,
    ) -> discord.Embed:
        shifts = await self.db.get_user_shifts(member.id, guild.id, limit)

        if not shifts:
            return make_embed(action="shift", title="🌙 Your Shifts", description="No shifts recorded.")

        description = ""
        for shift in shifts:
            start = datetime.fromisoformat(shift['start_ts_utc'])
            status = shift['status'].title()

            if shift['status'] == 'completed':
                end = datetime.fromisoformat(shift['end_ts_utc'])
                hours = calculate_shift_hours(start, end, shift['break_duration'])
                description += (
                    f"**ID {shift['id']}** - {shift['shift_type'].title()} | {hours:.2f}h | {status}\n"
                    f"<t:{int(start.timestamp())}:f> → <t:{int(end.timestamp())}:f>\n\n"
                )
            else:
                description += (
                    f"**ID {shift['id']}** - {shift['shift_type'].title()} | {status}\n"
                    f"Started: <t:{int(start.timestamp())}:R>\n\n"
                )

        return make_embed(action="shift", title="🌙 Your Recent Shifts", description=description.strip())

    async def _build_quota_embed(self, member: discord.Member, guild: discord.Guild) -> discord.Embed:
        now_gmt8 = get_gmt8_now()
        week_id = get_week_identifier_gmt8(now_gmt8)

        helper_quota = await self.db.get_quota_tracking(
            member.id,
            guild.id,
            "helper",
            week_id,
        )
        staff_quota = await self.db.get_quota_tracking(
            member.id,
            guild.id,
            "staff",
            week_id,
        )

        helper_hours = helper_quota['hours_logged'] if helper_quota else 0
        staff_hours = staff_quota['hours_logged'] if staff_quota else 0

        helper_required = config.DEFAULT_WEEKLY_QUOTAS.get("helper", 10)
        staff_required = config.DEFAULT_WEEKLY_QUOTAS.get("staff", 20)

        description = (
            f"**Week:** {week_id}\n\n"
            f"**Helper Shifts:**\n"
            f"Hours Logged: {helper_hours:.2f}h / {helper_required}h\n"
            f"Status: {'✅ Quota Met' if helper_hours >= helper_required else '⚠️ Below Quota'}\n\n"
            f"**Staff Shifts:**\n"
            f"Hours Logged: {staff_hours:.2f}h / {staff_required}h\n"
            f"Status: {'✅ Quota Met' if staff_hours >= staff_required else '⚠️ Below Quota'}"
        )

        return make_embed(action="shift", title="🌙 Weekly Shift Quota", description=description)

    async def _build_leaderboard_embed(self, guild: discord.Guild, shift_type: str) -> discord.Embed:
        normalized = shift_type.lower()
        if normalized not in {"helper", "staff", "all"}:
            normalized = "all"
        label = "All" if normalized == "all" else normalized.title()
        return make_embed(
            action="shift",
            title=f"🌙 Shift Leaderboard - {label}",
            description=(
                "Leaderboard feature coming soon.\n\n"
                "This will show top performers based on hours logged."
            ),
        )

    async def _update_shift_config(
        self,
        guild: discord.Guild,
        role: discord.Role,
        shift_type: str,
        afk_timeout: int,
        weekly_quota: int,
    ) -> discord.Embed:
        if shift_type not in {"helper", "staff"}:
            return make_embed(
                action="error",
                title="❌ Invalid Shift Type",
                description="Shift type must be helper or staff.",
            )

        await self.db.set_shift_config(
            guild_id=guild.id,
            role_id=role.id,
            shift_type=shift_type,
            afk_timeout=afk_timeout,
            weekly_quota=weekly_quota,
        )

        return make_embed(
            action="success",
            title="✅ Shift Config Updated",
            description=(
                f"**Role:** {role.mention}\n"
                f"**Type:** {shift_type.title()}\n"
                f"**AFK Timeout:** {afk_timeout}s\n"
                f"**Weekly Quota:** {weekly_quota}h"
            ),
        )

    @commands.command(name="manage_shift")
    @commands.guild_only()
    @require_level("moderator")
    async def manage_shift(self, ctx: commands.Context) -> None:
        """Open the shift management panel (Staff+ only).

        Usage:
        ,manage_shift
        """
        embed = make_embed(
            action="shift",
            title="🌙 Shift Management Panel",
            description=(
                "Use the controls below to manage shifts.\n"
                "Select a shift type for clock-ins, then choose an action."
            ),
        )
        view = ManageShiftView(self)
        await ctx.send(embed=embed, view=view)
        await safe_delete(ctx.message)

    @commands.command(name="clockin", aliases=["start_shift", "shiftin"])
    @commands.guild_only()
    @require_level("moderator")
    async def clockin(self, ctx: commands.Context, shift_type: str = "helper") -> None:
        """Clock in to start a shift (Staff+ only).

        Usage:
        ,clockin [helper|staff]
        """
        embed, success = await self._start_shift(ctx.author, ctx.guild, shift_type)
        await ctx.send(embed=embed)
        if success:
            await safe_delete(ctx.message)

    @commands.command(name="clockout", aliases=["end_shift", "shiftout"])
    @commands.guild_only()
    @require_level("moderator")
    async def clockout(self, ctx: commands.Context, break_minutes: int = 0) -> None:
        """Clock out to end your shift (Staff+ only).

        Usage:
        ,clockout [break_minutes]
        """
        embed, success = await self._end_shift(ctx.author, ctx.guild, break_minutes)
        await ctx.send(embed=embed)
        if success:
            await safe_delete(ctx.message)

    @commands.command(name="myshifts")
    @commands.guild_only()
    @require_level("moderator")
    async def myshifts(self, ctx: commands.Context, limit: int = 10) -> None:
        """View your recent shifts (Staff+ only).

        Usage:
        ,myshifts [limit]
        """
        embed = await self._build_my_shifts_embed(ctx.author, ctx.guild, limit)
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
        embed = await self._build_quota_embed(ctx.author, ctx.guild)
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
        embed = await self._build_leaderboard_embed(ctx.guild, shift_type)
        await ctx.send(embed=embed)
        await safe_delete(ctx.message)

    @commands.command(name="shiftconfig")
    @commands.guild_only()
    @require_admin()
    async def shiftconfig(
        self,
        ctx: commands.Context,
        role: discord.Role,
        shift_type: str,
        afk_timeout: int,
        weekly_quota: int,
    ) -> None:
        """Configure shift settings (Admin only).

        Usage:
        ,shiftconfig @role helper 300 10
        """
        embed = await self._update_shift_config(ctx.guild, role, shift_type.lower(), afk_timeout, weekly_quota)
        await ctx.send(embed=embed)
        await safe_delete(ctx.message)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ShiftsCog(bot))
