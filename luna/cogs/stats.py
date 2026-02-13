"""Stats - Moderator statistics and rankings for Vertigo."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import discord
from discord.ext import commands

import config
from database import Database, GuildSettings
from helpers import (
    make_embed,
    require_level,
    require_admin,
    is_admin_member,
    role_level_for_member,
    safe_delete,
)

logger = logging.getLogger(__name__)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SetStatsActionSelect(discord.ui.Select):
    """Select menu for choosing action type."""
    
    def __init__(self):
        options = [
            discord.SelectOption(label="Warns", value="warns", emoji="⚠️"),
            discord.SelectOption(label="Mutes", value="mutes", emoji="🔇"),
            discord.SelectOption(label="Kicks", value="kicks", emoji="👢"),
            discord.SelectOption(label="Bans", value="bans", emoji="🔨"),
        ]
        super().__init__(placeholder="Select action type", options=options, min_values=1, max_values=1)
    
    async def callback(self, interaction: discord.Interaction):
        self.view.selected_action = self.values[0]
        await interaction.response.send_message(f"Selected: **{self.values[0].title()}**. Now select the time period:", ephemeral=True)


class SetStatsPeriodSelect(discord.ui.Select):
    """Select menu for choosing time period."""
    
    def __init__(self):
        options = [
            discord.SelectOption(label="Past 7 days", value="7d", emoji="📅"),
            discord.SelectOption(label="Past 14 days", value="14d", emoji="📅"),
            discord.SelectOption(label="Past 30 days", value="30d", emoji="📅"),
            discord.SelectOption(label="Total (all time)", value="total", emoji="🔢"),
        ]
        super().__init__(placeholder="Select time period", options=options, min_values=1, max_values=1)
    
    async def callback(self, interaction: discord.Interaction):
        if not hasattr(self.view, 'selected_action'):
            await interaction.response.send_message("Please select an action type first!", ephemeral=True)
            return
        
        self.view.selected_period = self.values[0]
        
        # Show modal for value input
        modal = SetStatsValueModal(self.view.target_user, self.view.selected_action, self.values[0])
        await interaction.response.send_modal(modal)


class SetStatsValueModal(discord.ui.Modal):
    """Modal for inputting new stat value."""
    
    def __init__(self, target_user: discord.Member, action: str, period: str):
        self.target_user = target_user
        self.action = action
        self.period = period
        
        period_label = {"7d": "Past 7d", "14d": "Past 14d", "30d": "Past 30d", "total": "Total"}[period]
        super().__init__(title=f"Set {action.title()} - {period_label}")
        
        self.value_input = discord.ui.TextInput(
            label=f"New value for {action.title()} ({period_label})",
            placeholder="Enter a number",
            required=True,
            max_length=10
        )
        self.add_item(self.value_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            new_value = int(self.value_input.value)
            if new_value < 0:
                await interaction.response.send_message("❌ Value must be a positive number!", ephemeral=True)
                return
            
            # Update the database
            db = interaction.client.db
            await db.set_mod_stat(
                guild_id=interaction.guild.id,
                user_id=self.target_user.id,
                action_type=self.action,
                period=self.period,
                value=new_value
            )
            
            period_label = {"7d": "Past 7d", "14d": "Past 14d", "30d": "Past 30d", "total": "Total"}[self.period]
            
            embed = make_embed(
                action="success",
                title="✅ Stat Updated",
                description=f"Updated **{self.action.title()}** for {self.target_user.mention}\n**{period_label}:** {new_value}"
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except ValueError:
            await interaction.response.send_message("❌ Please enter a valid number!", ephemeral=True)
        except Exception as e:
            logger.error(f"Failed to set stat: {e}")
            await interaction.response.send_message("❌ Failed to update stat.", ephemeral=True)


class SetStatsView(discord.ui.View):
    """View for setting mod stats."""
    
    def __init__(self, target_user: discord.Member, timeout: float = 180):
        super().__init__(timeout=timeout)
        self.target_user = target_user
        self.selected_action = None
        self.selected_period = None
        
        self.add_item(SetStatsActionSelect())
        self.add_item(SetStatsPeriodSelect())


class StaffStatsFilterView(discord.ui.View):
    """View for filtering staff stats by role."""
    
    def __init__(self, cog, ctx: commands.Context, all_staff: list, timeout: float = 180):
        super().__init__(timeout=timeout)
        self.cog = cog
        self.ctx = ctx
        self.all_staff = all_staff
    
    @discord.ui.button(label="All Staff", style=discord.ButtonStyle.primary, emoji="👥")
    async def all_staff_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        embed = await self.cog._build_staffstats_embed(self.ctx, self.all_staff, "All Staff")
        await interaction.edit_original_response(embed=embed, view=self)
    
    @discord.ui.button(label="Trial Mod", style=discord.ButtonStyle.primary, emoji="🔰")
    async def trial_mod_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        filtered = [s for s in self.all_staff if s['level'] == 'trial_mod']
        embed = await self.cog._build_staffstats_embed(self.ctx, filtered, "Trial Moderators")
        await interaction.edit_original_response(embed=embed, view=self)
    
    @discord.ui.button(label="Moderator", style=discord.ButtonStyle.primary, emoji="🛡️")
    async def moderator_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        filtered = [s for s in self.all_staff if s['level'] == 'moderator']
        embed = await self.cog._build_staffstats_embed(self.ctx, filtered, "Moderators")
        await interaction.edit_original_response(embed=embed, view=self)
    
    @discord.ui.button(label="Senior Mod", style=discord.ButtonStyle.primary, emoji="⭐")
    async def senior_mod_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        filtered = [s for s in self.all_staff if s['level'] == 'senior_mod']
        embed = await self.cog._build_staffstats_embed(self.ctx, filtered, "Senior Moderators")
        await interaction.edit_original_response(embed=embed, view=self)
    
    @discord.ui.button(label="Head Mod", style=discord.ButtonStyle.primary, emoji="👑")
    async def head_mod_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        filtered = [s for s in self.all_staff if s['level'] == 'head_mod']
        embed = await self.cog._build_staffstats_embed(self.ctx, filtered, "Head Moderators")
        await interaction.edit_original_response(embed=embed, view=self)


class StatsCog(commands.Cog):
    """Moderator statistics and rankings."""
    
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
    
    @property
    def db(self) -> Database:
        return self.bot.db  # type: ignore[attr-defined]
    
    async def _settings(self, guild: discord.Guild) -> GuildSettings:
        return await self.db.get_guild_settings(guild.id, default_prefix=config.DEFAULT_PREFIX)
    
    @commands.command(name="ms")
    @commands.guild_only()
    @require_level("moderator")
    async def mod_stats(self, ctx: commands.Context, user: discord.Member | None = None) -> None:
        """Show moderator statistics for a user.
        
        Usage:
        !ms [user]
        """
        if user is None:
            user = ctx.author
        
        if not isinstance(user, discord.Member):
            embed = make_embed(action="error", title="❌ Error", description="User must be a member of this server.")
            await ctx.send(embed=embed)
            return
        
        settings = await self._settings(ctx.guild)
        
        # Get user's role level
        level = role_level_for_member(user, settings)
        level_names = {
            "admin": "Administrator",
            "head_mod": "Head Moderator",
            "senior_mod": "Senior Moderator",
            "moderator": "Moderator",
            "trial_mod": "Trial Moderator",
            "member": "Member"
        }
        
        # Get stats from database
        stats = await self.db.get_mod_stats(ctx.guild.id, user.id)
        
        # Calculate ranking
        all_staff_stats = await self.db.get_all_staff_rankings(ctx.guild.id)
        rank = next((i + 1 for i, s in enumerate(all_staff_stats) if s['user_id'] == user.id), None)
        
        # Build embed
        embed = make_embed(
            action="ms",
            title=f"{user.display_name} Moderator Stats",
            description=f"**Position:** {level_names.get(level, 'Member')}\n**Rankings:** #{rank if rank else 'Unranked'}"
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        
        # Warns section
        embed.add_field(
            name="**Warns**",
            value=f"Past 7d: {stats['warns_7d']}\nPast 14d: {stats['warns_14d']}\nPast 30d: {stats['warns_30d']}\nTotal: {stats['warns_total']}",
            inline=True
        )
        
        # Mutes section
        embed.add_field(
            name="**Mutes**",
            value=f"Past 7d: {stats['mutes_7d']}\nPast 14d: {stats['mutes_14d']}\nPast 30d: {stats['mutes_30d']}\nTotal: {stats['mutes_total']}",
            inline=True
        )
        
        # Kicks section
        embed.add_field(
            name="**Kicks**",
            value=f"Past 7d: {stats['kicks_7d']}\nPast 14d: {stats['kicks_14d']}\nPast 30d: {stats['kicks_30d']}\nTotal: {stats['kicks_total']}",
            inline=True
        )
        
        # Bans section
        embed.add_field(
            name="**Bans**",
            value=f"Past 7d: {stats['bans_7d']}\nPast 14d: {stats['bans_14d']}\nPast 30d: {stats['bans_30d']}\nTotal: {stats['bans_total']}",
            inline=True
        )
        
        # Total stats
        total_7d = stats['warns_7d'] + stats['mutes_7d'] + stats['kicks_7d'] + stats['bans_7d']
        total_14d = stats['warns_14d'] + stats['mutes_14d'] + stats['kicks_14d'] + stats['bans_14d']
        total_30d = stats['warns_30d'] + stats['mutes_30d'] + stats['kicks_30d'] + stats['bans_30d']
        total_all = stats['warns_total'] + stats['mutes_total'] + stats['kicks_total'] + stats['bans_total']
        
        embed.add_field(
            name="**Total Stats**",
            value=f"Total Past 7d: {total_7d}\nTotal Past 14d: {total_14d}\nTotal Past 30d: {total_30d}\nTotal All: {total_all}",
            inline=False
        )
        
        await ctx.send(embed=embed)
        await safe_delete(ctx.message)
    
    @commands.command(name="staffstats")
    @commands.guild_only()
    @require_admin()
    async def staff_stats(self, ctx: commands.Context) -> None:
        """Show all staff ranked by total moderation actions.
        
        Usage:
        !staffstats
        """
        settings = await self._settings(ctx.guild)
        trial_mod_roles = await self.db.get_trial_mod_roles(ctx.guild.id)
        
        # Get all staff members with their stats
        all_staff_stats = await self.db.get_all_staff_rankings(ctx.guild.id)
        
        # Enrich with role level information
        enriched_staff = []
        for stat in all_staff_stats:
            member = ctx.guild.get_member(stat['user_id'])
            if member:
                level = role_level_for_member(member, settings, trial_mod_role_ids=trial_mod_roles)
                enriched_staff.append({
                    'member': member,
                    'total': stat['total'],
                    'level': level
                })
        
        # Sort by role hierarchy, then by total
        level_order = ['head_mod', 'senior_mod', 'moderator', 'trial_mod']
        enriched_staff.sort(key=lambda x: (level_order.index(x['level']) if x['level'] in level_order else 999, -x['total']))
        
        embed = await self._build_staffstats_embed(ctx, enriched_staff, "All Staff")
        view = StaffStatsFilterView(self, ctx, enriched_staff)
        await ctx.send(embed=embed, view=view)
        await safe_delete(ctx.message)
    
    async def _build_staffstats_embed(self, ctx: commands.Context, staff_list: list, title_suffix: str) -> discord.Embed:
        """Build the staff stats embed."""
        embed = make_embed(
            action="staffstats",
            title=f"📊 Staff Statistics - {title_suffix}",
            description="Ranked by total moderation actions"
        )
        
        if not staff_list:
            embed.description = "No staff members found."
            return embed
        
        # Build rankings text
        rankings = []
        for i, staff in enumerate(staff_list[:25], start=1):  # Show top 25
            member = staff['member']
            total = staff['total']
            rankings.append(f"{i}. {member.mention} - **{total}** Total")
        
        embed.description += "\n\n" + "\n".join(rankings)
        return embed
    
    @commands.command(name="set_ms")
    @commands.guild_only()
    @require_admin()
    async def set_mod_stats(self, ctx: commands.Context, user: discord.Member | None = None) -> None:
        """Manually set moderator statistics.
        
        Usage:
        !set_ms [user]
        """
        if user is None:
            user = ctx.author
        
        if not isinstance(user, discord.Member):
            embed = make_embed(action="error", title="❌ Error", description="User must be a member of this server.")
            await ctx.send(embed=embed)
            return
        
        embed = make_embed(
            action="set_ms",
            title="⚙️ Set Moderator Stats",
            description=f"Editing stats for {user.mention}\n\n1️⃣ Select action type\n2️⃣ Select time period\n3️⃣ Enter new value"
        )
        
        view = SetStatsView(user)
        await ctx.send(embed=embed, view=view)
        await safe_delete(ctx.message)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(StatsCog(bot))
