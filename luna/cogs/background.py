"""Background tasks for expiry checks, startup reconciliation, reminders, and stats dashboard."""

from __future__ import annotations

import logging
import aiohttp
import time
from datetime import datetime, timezone

import discord
from discord.ext import commands, tasks

import config
from database import Database
from helpers import make_embed, is_admin_member

logger = logging.getLogger(__name__)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ChannelNameStyleSelect(discord.ui.Select):
    """Select menu for choosing stats channel name style."""

    def __init__(self, current_style: int) -> None:
        options = [
            discord.SelectOption(
                label="Long Name",
                value="long",
                description="🌙total-executions-1234",
                default=current_style == 0,
            ),
            discord.SelectOption(
                label="Short Name",
                value="short",
                description="🌙exec-1234",
                default=current_style == 1,
            ),
        ]
        super().__init__(
            placeholder="Rename channel style",
            options=options,
            min_values=1,
            max_values=1,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        if not isinstance(view, StatsDashboardView):
            return
        await view.handle_style_change(interaction, self.values[0])


class StatsDashboardView(discord.ui.View):
    """Admin controls for the stats dashboard."""

    def __init__(self, cog: "BackgroundTasksCog", show_leaderboards: bool, channel_name_style: int) -> None:
        super().__init__(timeout=None)
        self.cog = cog
        self.show_leaderboards = show_leaderboards
        self.channel_name_style = channel_name_style
        self.add_item(ChannelNameStyleSelect(channel_name_style))
        self.toggle_leaderboards_button.label = "Hide Leaderboards" if show_leaderboards else "Show Leaderboards"

    async def _is_admin(self, interaction: discord.Interaction) -> bool:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return False
        settings = await self.cog.db.get_guild_settings(interaction.guild.id, default_prefix=config.DEFAULT_PREFIX)
        return is_admin_member(interaction.user, settings)

    async def _deny_access(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(
            "❌ Only administrators can use dashboard controls.",
            ephemeral=True,
        )

    @discord.ui.button(label="Refresh Dashboard", style=discord.ButtonStyle.primary, emoji="🔄")
    async def refresh_dashboard_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        if not await self._is_admin(interaction):
            await self._deny_access(interaction)
            return
        await interaction.response.defer(ephemeral=True)
        success = await self.cog.refresh_stats_dashboard()
        if success:
            await interaction.followup.send("✅ Dashboard refreshed.", ephemeral=True)
        else:
            await interaction.followup.send("❌ Failed to refresh the dashboard.", ephemeral=True)

    @discord.ui.button(label="Hide Leaderboards", style=discord.ButtonStyle.secondary, emoji="🏆")
    async def toggle_leaderboards_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        if not await self._is_admin(interaction):
            await self._deny_access(interaction)
            return
        await interaction.response.defer(ephemeral=True)
        new_value = 0 if self.show_leaderboards else 1
        await self.cog.db.stats_set("stats_show_leaderboards", new_value)
        await self.cog.refresh_stats_dashboard()
        status = "shown" if new_value else "hidden"
        await interaction.followup.send(f"✅ Leaderboards {status}.", ephemeral=True)

    async def handle_style_change(self, interaction: discord.Interaction, style: str) -> None:
        if not await self._is_admin(interaction):
            await self._deny_access(interaction)
            return
        await interaction.response.defer(ephemeral=True)
        style_value = 0 if style == "long" else 1
        await self.cog.db.stats_set("stats_channel_name_style", style_value)
        await self.cog.refresh_stats_dashboard(force_rename=True)
        label = "Long" if style_value == 0 else "Short"
        await interaction.followup.send(f"✅ Channel rename style set to {label}.", ephemeral=True)


class BackgroundTasksCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._startup_done = False

        self.warn_expiry_loop.start()
        self.temp_role_expiry_loop.start()
        self.staff_flag_expiry_loop.start()
        self.mute_expiry_loop.start()
        self.ai_rate_limit_cleanup_loop.start()
        self.reminder_check_loop.start()
        self.stats_dashboard_loop.start()
        self.promotion_analysis_loop.start()

    @property
    def db(self) -> Database:
        return self.bot.db  # type: ignore[attr-defined]

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        if self._startup_done:
            return
        self._startup_done = True
        await self._restore_persistent_roles()

    async def _restore_persistent_roles(self) -> None:
        rows = await self.db.get_active_persistent_roles()
        for row in rows:
            guild = self.bot.get_guild(int(row["guild_id"]))
            if guild is None:
                continue
            member = guild.get_member(int(row["user_id"]))
            role = guild.get_role(int(row["role_id"]))
            if member is None or role is None:
                continue
            if role in member.roles:
                continue
            try:
                await member.add_roles(role, reason="Persistent role restore")
            except discord.Forbidden:
                continue
            except Exception:
                logger.exception("Failed to restore persistent role")

    @tasks.loop(minutes=1)
    async def warn_expiry_loop(self) -> None:
        try:
            rows = await self.db.get_expired_warnings(limit=200)
            if not rows:
                return
            ids = [int(r["id"]) for r in rows]
            await self.db.expire_warning_ids(ids)
            for r in rows:
                await self.db.add_modlog(
                    guild_id=int(r["guild_id"]),
                    action_type="warn_expired",
                    user_id=int(r["user_id"]),
                    moderator_id=None,
                    reason="Warning expired",
                )
        except Exception:
            logger.exception("warn_expiry_loop failed")

    @tasks.loop(minutes=1)
    async def temp_role_expiry_loop(self) -> None:
        try:
            rows = await self.db.get_expired_temp_roles(limit=200)
            if not rows:
                return
            ids = [int(r["id"]) for r in rows]
            await self.db.expire_temp_role_ids(ids)

            for r in rows:
                guild = self.bot.get_guild(int(r["guild_id"]))
                if guild is None:
                    continue
                member = guild.get_member(int(r["user_id"]))
                role = guild.get_role(int(r["role_id"]))
                if member and role and role in member.roles:
                    try:
                        await member.remove_roles(role, reason="Temp role expired")
                    except discord.Forbidden:
                        pass
                await self.db.add_modlog(
                    guild_id=int(r["guild_id"]),
                    action_type="temp_role_expired",
                    user_id=int(r["user_id"]),
                    moderator_id=None,
                    target_id=int(r["role_id"]),
                    reason="Temp role expired",
                )
        except Exception:
            logger.exception("temp_role_expiry_loop failed")

    @tasks.loop(minutes=1)
    async def staff_flag_expiry_loop(self) -> None:
        try:
            rows = await self.db.get_expired_staff_flags(limit=200)
            if not rows:
                return
            ids = [int(r["id"]) for r in rows]
            await self.db.expire_staff_flag_ids(ids)
        except Exception:
            logger.exception("staff_flag_expiry_loop failed")

    @tasks.loop(minutes=1)
    async def mute_expiry_loop(self) -> None:
        try:
            rows = await self.db.get_expired_mutes(limit=200)
            if not rows:
                return
            ids = [int(r["id"]) for r in rows]
            await self.db.expire_mute_ids(ids)
        except Exception:
            logger.exception("mute_expiry_loop failed")

    @tasks.loop(minutes=5)
    async def ai_rate_limit_cleanup_loop(self) -> None:
        """Clean up expired rate limit entries."""
        try:
            from helpers import clean_rate_limits
            clean_rate_limits()
        except Exception:
            logger.exception("ai_rate_limit_cleanup_loop failed")

    @tasks.loop(minutes=1)
    async def reminder_check_loop(self) -> None:
        """Check and send expired reminders."""
        try:
            reminders = await self.db.get_expired_reminders()
            if not reminders:
                return
            
            for reminder in reminders:
                user_id = int(reminder['user_id'])
                text = reminder['text']
                
                user = self.bot.get_user(user_id)
                if user:
                    embed = make_embed(
                        action="reminder",
                        title="⏰ Reminder",
                        description=text
                    )
                    try:
                        await user.send(embed=embed)
                    except discord.Forbidden:
                        pass
                
                await self.db.deactivate_reminder(int(reminder['id']))
                
        except Exception:
            logger.exception("reminder_check_loop failed")
    
    async def refresh_stats_dashboard(self, *, force_rename: bool = False) -> bool:
        try:
            await self._update_stats_dashboard(force_rename=force_rename)
            return True
        except Exception:
            logger.exception("stats_dashboard_refresh failed")
            return False

    async def _update_stats_dashboard(self, *, force_rename: bool = False) -> None:
        channel = self.bot.get_channel(config.TARGET_CHANNEL_ID)
        if not channel or not isinstance(channel, discord.TextChannel):
            return

        async with aiohttp.ClientSession() as session:
            async with session.get(config.API_URL, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    logger.error("Stats API returned %s", resp.status)
                    return
                data = await resp.json()

        total_executions = data.get('total_executions', 0)

        prev_daily_start = await self.db.stats_get('daily_start_total', 0)
        prev_weekly_start = await self.db.stats_get('weekly_start_total', 0)
        prev_monthly_start = await self.db.stats_get('monthly_start_total', 0)

        now = utcnow()
        last_daily_reset = await self.db.stats_get('last_daily_reset', 0)
        last_weekly_reset = await self.db.stats_get('last_weekly_reset', 0)
        last_monthly_reset = await self.db.stats_get('last_monthly_reset', 0)

        current_day = now.day
        current_week = now.isocalendar()[1]
        current_month = now.month

        if last_daily_reset != current_day:
            prev_daily_start = total_executions
            await self.db.stats_set('daily_start_total', prev_daily_start)
            await self.db.stats_set('last_daily_reset', current_day)

        if last_weekly_reset != current_week:
            prev_weekly_start = total_executions
            await self.db.stats_set('weekly_start_total', prev_weekly_start)
            await self.db.stats_set('last_weekly_reset', current_week)

        if last_monthly_reset != current_month:
            prev_monthly_start = total_executions
            await self.db.stats_set('monthly_start_total', prev_monthly_start)
            await self.db.stats_set('last_monthly_reset', current_month)

        daily_delta = total_executions - prev_daily_start
        weekly_delta = total_executions - prev_weekly_start
        monthly_delta = total_executions - prev_monthly_start

        await self.db.stats_set('total_executions', total_executions)

        show_leaderboards = bool(await self.db.stats_get('stats_show_leaderboards', 1))
        channel_name_style = await self.db.stats_get('stats_channel_name_style', 0)

        description = (
            f"**Total Executions:** {total_executions:,}\n"
            f"**Daily:** +{daily_delta:,}\n"
            f"**Weekly:** +{weekly_delta:,}\n"
            f"**Monthly:** +{monthly_delta:,}\n"
        )

        if show_leaderboards:
            if data.get('top_games'):
                description += "\n**Top Games:**\n"
                for game in data['top_games'][:5]:
                    description += f"• {game.get('name', 'Unknown')}: {game.get('count', 0):,}\n"
        else:
            description += "\n**Leaderboards:** Hidden"

        embed = make_embed(
            action="stats",
            title="🚀 Script Execution Dashboard",
            description=description.strip()
        )
        embed.set_footer(text=f"Last Update: {int(now.timestamp())}")

        view = StatsDashboardView(self, show_leaderboards, channel_name_style)

        messages = []
        async for msg in channel.history(limit=10):
            if msg.author.id == self.bot.user.id and msg.embeds:
                if '🚀' in msg.embeds[0].title:
                    messages.append(msg)

        if messages:
            await messages[0].edit(embed=embed, view=view)
        else:
            await channel.send(embed=embed, view=view)

        await self._rename_stats_channel(
            channel,
            total_executions=total_executions,
            channel_name_style=channel_name_style,
            force_rename=force_rename,
        )

    async def _rename_stats_channel(
        self,
        channel: discord.TextChannel,
        *,
        total_executions: int,
        channel_name_style: int,
        force_rename: bool,
    ) -> None:
        last_rename = await self.db.stats_get('last_channel_rename', 0)
        if not force_rename and time.time() - last_rename <= 600:
            return

        try:
            new_name = self._format_stats_channel_name(total_executions, channel_name_style)
            await channel.edit(name=new_name)
            await self.db.stats_set('last_channel_rename', int(time.time()))
        except Exception:
            logger.exception("Failed to rename channel")

    @staticmethod
    def _format_stats_channel_name(total_executions: int, channel_name_style: int) -> str:
        if channel_name_style == 1:
            return f"🌙exec-{total_executions}"
        return f"🌙total-executions-{total_executions}"

    @tasks.loop(minutes=5)
    async def stats_dashboard_loop(self) -> None:
        """Update stats dashboard from external API."""
        try:
            await self._update_stats_dashboard()
        except Exception:
            logger.exception("stats_dashboard_loop failed")

    @tasks.loop(hours=24)
    async def promotion_analysis_loop(self) -> None:
        """Analyze staff performance and generate promotion/demotion suggestions daily."""
        try:
            from services.promotion_engine import StaffPromotionEngine
            
            engine = StaffPromotionEngine(self.bot, self.db)
            
            # Analyze staff in all guilds
            for guild in self.bot.guilds:
                try:
                    settings = await self.db.get_guild_settings(guild.id, default_prefix=config.DEFAULT_PREFIX)
                    
                    # Skip if no promotion channel configured
                    if not settings.promotion_channel_id:
                        continue
                    
                    channel = guild.get_channel(settings.promotion_channel_id)
                    if not channel or not isinstance(channel, discord.abc.Messageable):
                        continue
                    
                    # Analyze all staff
                    results = await engine.analyze_all_staff(guild, settings)
                    
                    # Send summary to promotion channel
                    if results["promotions"] or results["warnings"]:
                        summary_embed = make_embed(
                            action="success",
                            title="📈 Daily Staff Performance Analysis",
                            description=f"Analyzed {results['total_staff']} staff members."
                        )
                        summary_embed.add_field(
                            name="📊 Results",
                            value=(
                                f"**Promotion Suggestions:** {len(results['promotions'])}\n"
                                f"**Performance Warnings:** {len(results['warnings'])}"
                            ),
                            inline=False
                        )
                        summary_embed.add_field(
                            name="📋 Review",
                            value=f"Use `{settings.prefix}promotion list` to review pending suggestions.",
                            inline=False
                        )
                        
                        await channel.send(embed=summary_embed)
                        
                        # Send individual suggestion notifications
                        pending_suggestions = await self.db.get_pending_suggestions(guild.id)
                        for suggestion in pending_suggestions[-5:]:  # Only notify about last 5 new ones
                            try:
                                embed = await engine.create_suggestion_embed(suggestion)
                                await channel.send(embed=embed)
                            except Exception:
                                logger.exception(f"Failed to send suggestion embed for suggestion {suggestion['id']}")
                    
                except Exception:
                    logger.exception(f"Promotion analysis failed for guild {guild.id}")
        
        except Exception:
            logger.exception("promotion_analysis_loop failed")

    @warn_expiry_loop.before_loop
    @temp_role_expiry_loop.before_loop
    @staff_flag_expiry_loop.before_loop
    @mute_expiry_loop.before_loop
    @reminder_check_loop.before_loop
    @stats_dashboard_loop.before_loop
    @promotion_analysis_loop.before_loop
    async def _before(self) -> None:
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(BackgroundTasksCog(bot))
