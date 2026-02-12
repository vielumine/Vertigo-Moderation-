"""Staff promotion and performance management commands."""

from __future__ import annotations

import logging

import discord
from discord.ext import commands

import config
from database import Database, GuildSettings
from helpers import (
    Page,
    PaginationView,
    commands_channel_check,
    make_embed,
    require_admin,
    safe_delete,
)

logger = logging.getLogger(__name__)


class PromotionsCog(commands.Cog):
    """Commands for managing staff promotions and performance."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @property
    def db(self) -> Database:
        return self.bot.db  # type: ignore[attr-defined]

    async def _settings(self, guild: discord.Guild) -> GuildSettings:
        return await self.db.get_guild_settings(guild.id, default_prefix=config.DEFAULT_PREFIX)

    @commands.group(name="promotion", aliases=["promo"])
    @commands.guild_only()
    @commands_channel_check()
    @require_admin()
    async def promotion(self, ctx: commands.Context) -> None:
        """Manage staff promotion suggestions."""
        if ctx.invoked_subcommand is None:
            embed = make_embed(
                action="help",
                title="📈 Promotion Management Commands",
                description="Commands for managing automated staff promotion suggestions."
            )
            embed.add_field(
                name="Commands",
                value=(
                    f"`{ctx.prefix}promotion list` - View pending suggestions\n"
                    f"`{ctx.prefix}promotion review <id> <approve/deny>` - Review a suggestion\n"
                    f"`{ctx.prefix}promotion analyze <member>` - Analyze staff member performance\n"
                    f"`{ctx.prefix}promotion stats <member>` - View detailed stats"
                ),
                inline=False
            )
            await ctx.send(embed=embed)

    @promotion.command(name="list")
    async def promotion_list(self, ctx: commands.Context) -> None:
        """List all pending promotion suggestions."""
        suggestions = await self.db.get_pending_suggestions(ctx.guild.id)  # type: ignore[union-attr]

        if not suggestions:
            embed = make_embed(
                action="success",
                title="📈 Promotion Suggestions",
                description="No pending promotion suggestions at this time."
            )
            await ctx.send(embed=embed)
            await safe_delete(ctx.message)
            return

        # Create paginated embeds
        pages: list[Page] = []
        promotions = [s for s in suggestions if s["suggestion_type"] == "promotion"]
        warnings = [s for s in suggestions if s["suggestion_type"] == "demotion_warning"]

        # Promotion suggestions
        if promotions:
            for i in range(0, len(promotions), 3):
                chunk = promotions[i : i + 3]
                embed = make_embed(
                    action="success",
                    title=f"📈 Promotion Suggestions ({len(promotions)} total)"
                )

                for suggestion in chunk:
                    user_id = suggestion["user_id"]
                    current = suggestion["current_role"] or "Unknown"
                    suggested = suggestion["suggested_role"] or "N/A"
                    confidence = suggestion["confidence"]
                    suggestion_id = suggestion["id"]

                    embed.add_field(
                        name=f"ID: {suggestion_id} | <@{user_id}>",
                        value=(
                            f"**Current:** {current.replace('_', ' ').title()}\n"
                            f"**Suggested:** {suggested.replace('_', ' ').title()}\n"
                            f"**Confidence:** {confidence:.1%}"
                        ),
                        inline=False
                    )

                pages.append(Page(embed=embed))

        # Demotion warnings
        if warnings:
            for i in range(0, len(warnings), 3):
                chunk = warnings[i : i + 3]
                embed = make_embed(
                    action="error",
                    title=f"📉 Demotion Warnings ({len(warnings)} total)"
                )

                for suggestion in chunk:
                    user_id = suggestion["user_id"]
                    current = suggestion["current_role"] or "Unknown"
                    confidence = suggestion["confidence"]
                    suggestion_id = suggestion["id"]

                    embed.add_field(
                        name=f"ID: {suggestion_id} | <@{user_id}>",
                        value=(
                            f"**Current Role:** {current.replace('_', ' ').title()}\n"
                            f"**Confidence:** {confidence:.1%}\n"
                            f"**Status:** ⚠️ Underperforming"
                        ),
                        inline=False
                    )

                pages.append(Page(embed=embed))

        if pages:
            view = PaginationView(pages=pages, author_id=ctx.author.id)
            await ctx.send(embed=pages[0].embed, view=view)
        else:
            embed = make_embed(
                action="success",
                title="📈 Promotion Suggestions",
                description="No pending suggestions."
            )
            await ctx.send(embed=embed)

        await safe_delete(ctx.message)

    @promotion.command(name="review")
    async def promotion_review(self, ctx: commands.Context, suggestion_id: int, action: str) -> None:
        """Review a promotion suggestion.
        
        Actions: approve, deny
        """
        action = action.lower()
        if action not in ["approve", "deny", "approved", "denied"]:
            embed = make_embed(
                action="error",
                title="❌ Invalid Action",
                description="Action must be 'approve' or 'deny'."
            )
            await ctx.send(embed=embed)
            return

        # Normalize action
        status = "approved" if action.startswith("approve") else "denied"

        # Get suggestion
        suggestion = await self.db.get_suggestion(suggestion_id)
        if not suggestion:
            embed = make_embed(
                action="error",
                title="❌ Not Found",
                description=f"Suggestion ID {suggestion_id} not found."
            )
            await ctx.send(embed=embed)
            return

        if suggestion["guild_id"] != ctx.guild.id:  # type: ignore[union-attr]
            embed = make_embed(
                action="error",
                title="❌ Not Found",
                description="Suggestion not found in this guild."
            )
            await ctx.send(embed=embed)
            return

        # Update suggestion status
        await self.db.review_suggestion(suggestion_id, ctx.author.id, status)

        icon = "✅" if status == "approved" else "❌"
        embed = make_embed(
            action="success" if status == "approved" else "error",
            title=f"{icon} Suggestion {status.title()}",
            description=f"Promotion suggestion {suggestion_id} has been {status}."
        )

        user_id = suggestion["user_id"]
        suggestion_type = suggestion["suggestion_type"]
        embed.add_field(name="👤 Staff Member", value=f"<@{user_id}>", inline=True)
        embed.add_field(name="📋 Type", value=suggestion_type.replace("_", " ").title(), inline=True)
        embed.add_field(name="👔 Reviewed By", value=ctx.author.mention, inline=True)

        if status == "approved" and suggestion_type == "promotion":
            embed.add_field(
                name="⚠️ Next Steps",
                value="Remember to manually assign the new role to the staff member.",
                inline=False
            )

        await ctx.send(embed=embed)
        await safe_delete(ctx.message)

    @promotion.command(name="analyze")
    async def promotion_analyze(self, ctx: commands.Context, member: discord.Member) -> None:
        """Analyze a staff member's performance and check promotion eligibility."""
        settings = await self._settings(ctx.guild)  # type: ignore[arg-type]

        # Import here to avoid circular dependency
        from services.promotion_engine import StaffPromotionEngine
        engine = StaffPromotionEngine(self.bot, self.db)

        # Get metrics
        try:
            metrics = await engine.analyze_staff_performance(ctx.guild, member, settings)  # type: ignore[arg-type]
        except Exception as e:
            logger.error(f"Error analyzing staff performance: {e}")
            embed = make_embed(
                action="error",
                title="❌ Analysis Failed",
                description="Failed to analyze staff member performance."
            )
            await ctx.send(embed=embed)
            return

        # Create detailed embed
        embed = make_embed(
            action="success",
            title=f"📊 Performance Analysis: {member.display_name}",
            description=f"Detailed performance metrics for {member.mention}"
        )

        # Basic info
        embed.add_field(
            name="👤 Staff Information",
            value=(
                f"**Current Level:** {metrics['current_level'].replace('_', ' ').title()}\n"
                f"**Tenure:** {metrics['tenure_days']} days\n"
                f"**Active Flags:** {metrics['active_flags']}"
            ),
            inline=False
        )

        # Activity metrics
        embed.add_field(
            name="📈 Recent Activity (7 Days)",
            value=(
                f"**Warns:** {metrics['warns_7d']}\n"
                f"**Mutes:** {metrics['mutes_7d']}\n"
                f"**Kicks:** {metrics['kicks_7d']}\n"
                f"**Bans:** {metrics['bans_7d']}\n"
                f"**Total:** {metrics['total_7d']}"
            ),
            inline=True
        )

        embed.add_field(
            name="📈 Monthly Activity (30 Days)",
            value=(
                f"**Warns:** {metrics['warns_30d']}\n"
                f"**Mutes:** {metrics['mutes_30d']}\n"
                f"**Kicks:** {metrics['kicks_30d']}\n"
                f"**Bans:** {metrics['bans_30d']}\n"
                f"**Total:** {metrics['total_30d']}"
            ),
            inline=True
        )

        # Activity score
        activity_score = metrics["activity_score"]
        score_emoji = "🟢" if activity_score >= 0.7 else "🟡" if activity_score >= 0.4 else "🔴"
        embed.add_field(
            name="🎯 Activity Score",
            value=f"{score_emoji} **{activity_score:.2f}** / 1.00",
            inline=False
        )

        # Check promotion eligibility
        current_level = metrics["current_level"]
        if current_level == "moderator":
            eligible, confidence, reason = await engine.check_promotion_eligibility(metrics, "moderator_to_senior")
            if eligible:
                embed.add_field(
                    name="✅ Promotion Eligible",
                    value=f"**To:** Senior Moderator\n**Confidence:** {confidence:.1%}\n{reason}",
                    inline=False
                )
        elif current_level == "senior_mod":
            eligible, confidence, reason = await engine.check_promotion_eligibility(metrics, "senior_to_head")
            if eligible:
                embed.add_field(
                    name="✅ Promotion Eligible",
                    value=f"**To:** Head Moderator\n**Confidence:** {confidence:.1%}\n{reason}",
                    inline=False
                )

        # Check demotion warning
        should_warn, warn_confidence, warn_reason = await engine.check_demotion_warning(metrics)
        if should_warn:
            embed.add_field(
                name="⚠️ Performance Warning",
                value=f"**Confidence:** {warn_confidence:.1%}\n{warn_reason}",
                inline=False
            )

        await ctx.send(embed=embed)
        await safe_delete(ctx.message)

    @promotion.command(name="stats")
    async def promotion_stats(self, ctx: commands.Context, member: discord.Member) -> None:
        """View detailed moderation statistics for a staff member."""
        stats = await self.db.get_mod_stats(ctx.guild.id, member.id)  # type: ignore[union-attr]

        embed = make_embed(
            action="success",
            title=f"📊 Moderation Statistics: {member.display_name}",
            description=f"Detailed statistics for {member.mention}"
        )

        # 7-day stats
        embed.add_field(
            name="📅 Last 7 Days",
            value=(
                f"**Warns:** {stats['warns_7d']}\n"
                f"**Mutes:** {stats['mutes_7d']}\n"
                f"**Kicks:** {stats['kicks_7d']}\n"
                f"**Bans:** {stats['bans_7d']}\n"
                f"**Total:** {stats['warns_7d'] + stats['mutes_7d'] + stats['kicks_7d'] + stats['bans_7d']}"
            ),
            inline=True
        )

        # 14-day stats
        embed.add_field(
            name="📅 Last 14 Days",
            value=(
                f"**Warns:** {stats['warns_14d']}\n"
                f"**Mutes:** {stats['mutes_14d']}\n"
                f"**Kicks:** {stats['kicks_14d']}\n"
                f"**Bans:** {stats['bans_14d']}\n"
                f"**Total:** {stats['warns_14d'] + stats['mutes_14d'] + stats['kicks_14d'] + stats['bans_14d']}"
            ),
            inline=True
        )

        # 30-day stats
        embed.add_field(
            name="📅 Last 30 Days",
            value=(
                f"**Warns:** {stats['warns_30d']}\n"
                f"**Mutes:** {stats['mutes_30d']}\n"
                f"**Kicks:** {stats['kicks_30d']}\n"
                f"**Bans:** {stats['bans_30d']}\n"
                f"**Total:** {stats['warns_30d'] + stats['mutes_30d'] + stats['kicks_30d'] + stats['bans_30d']}"
            ),
            inline=True
        )

        # Total lifetime stats
        embed.add_field(
            name="🏆 All Time",
            value=(
                f"**Warns:** {stats['warns_total']}\n"
                f"**Mutes:** {stats['mutes_total']}\n"
                f"**Kicks:** {stats['kicks_total']}\n"
                f"**Bans:** {stats['bans_total']}\n"
                f"**Total:** {stats['warns_total'] + stats['mutes_total'] + stats['kicks_total'] + stats['bans_total']}"
            ),
            inline=True
        )

        await ctx.send(embed=embed)
        await safe_delete(ctx.message)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PromotionsCog(bot))
