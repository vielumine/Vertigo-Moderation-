"""Staff Promotion/Demotion Engine.

This module analyzes staff performance metrics and generates automated
suggestions for promotions and demotions based on activity, consistency,
and quality of moderation actions.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

import discord

import config
from helpers import role_level_for_member, is_staff_member, make_embed, utcnow

if TYPE_CHECKING:
    from discord.ext import commands
    from database import Database, GuildSettings

logger = logging.getLogger(__name__)


class StaffPromotionEngine:
    """Analyzes staff performance and generates promotion/demotion suggestions."""

    # Promotion thresholds (configurable per guild)
    DEFAULT_THRESHOLDS = {
        "moderator_to_senior": {
            "min_actions_7d": 10,
            "min_actions_30d": 40,
            "min_tenure_days": 30,
            "min_activity_score": 0.7,
            "max_flags": 1,
        },
        "senior_to_head": {
            "min_actions_7d": 15,
            "min_actions_30d": 60,
            "min_tenure_days": 60,
            "min_activity_score": 0.8,
            "max_flags": 0,
        },
        "demotion_warning": {
            "max_actions_7d": 3,
            "max_actions_30d": 10,
            "min_activity_score": 0.3,
        },
    }

    def __init__(self, bot: commands.Bot, db: Database) -> None:
        self.bot = bot
        self.db = db

    async def analyze_staff_performance(self, guild: discord.Guild, staff_member: discord.Member, settings: GuildSettings) -> dict:
        """Analyze a staff member's performance and return metrics."""
        # Get mod stats
        stats = await self.db.get_mod_stats(guild.id, staff_member.id)
        
        # Get staff flags
        flags = await self.db.get_active_staff_flags(guild_id=guild.id, staff_user_id=staff_member.id)
        active_flags = len(flags)
        
        # Calculate tenure (approximate based on joined date)
        tenure_days = (utcnow() - staff_member.joined_at).days if staff_member.joined_at else 0
        
        # Calculate activity score (weighted: recent > older)
        total_7d = stats["warns_7d"] + stats["mutes_7d"] + stats["kicks_7d"] + stats["bans_7d"]
        total_30d = stats["warns_30d"] + stats["mutes_30d"] + stats["kicks_30d"] + stats["bans_30d"]
        
        # Activity score: weight recent activity higher
        activity_score = 0.0
        if total_30d > 0:
            recent_ratio = total_7d / max(1, total_30d)
            activity_score = min(1.0, (total_7d * 0.7 + total_30d * 0.3) / 100)
            activity_score *= (0.7 + recent_ratio * 0.3)  # Boost for consistent recent activity
        
        # Get current role level
        current_level = role_level_for_member(staff_member, settings)
        
        return {
            "user_id": staff_member.id,
            "current_level": current_level,
            "tenure_days": tenure_days,
            "active_flags": active_flags,
            "total_7d": total_7d,
            "total_30d": total_30d,
            "warns_7d": stats["warns_7d"],
            "mutes_7d": stats["mutes_7d"],
            "kicks_7d": stats["kicks_7d"],
            "bans_7d": stats["bans_7d"],
            "warns_30d": stats["warns_30d"],
            "mutes_30d": stats["mutes_30d"],
            "kicks_30d": stats["kicks_30d"],
            "bans_30d": stats["bans_30d"],
            "activity_score": activity_score,
        }

    async def check_promotion_eligibility(self, metrics: dict, promotion_type: str) -> tuple[bool, float, str]:
        """Check if staff member is eligible for promotion.
        
        Returns: (eligible, confidence, reason)
        """
        thresholds = self.DEFAULT_THRESHOLDS.get(promotion_type, {})
        if not thresholds:
            return False, 0.0, "Invalid promotion type"
        
        reasons = []
        confidence = 1.0
        
        # Check minimum actions
        if "min_actions_7d" in thresholds:
            if metrics["total_7d"] < thresholds["min_actions_7d"]:
                return False, 0.0, f"Insufficient recent activity: {metrics['total_7d']}/{thresholds['min_actions_7d']} actions in 7 days"
            reasons.append(f"✅ Recent activity: {metrics['total_7d']} actions in 7 days")
        
        if "min_actions_30d" in thresholds:
            if metrics["total_30d"] < thresholds["min_actions_30d"]:
                return False, 0.0, f"Insufficient monthly activity: {metrics['total_30d']}/{thresholds['min_actions_30d']} actions in 30 days"
            reasons.append(f"✅ Monthly activity: {metrics['total_30d']} actions in 30 days")
        
        # Check tenure
        if "min_tenure_days" in thresholds:
            if metrics["tenure_days"] < thresholds["min_tenure_days"]:
                return False, 0.0, f"Insufficient tenure: {metrics['tenure_days']}/{thresholds['min_tenure_days']} days"
            reasons.append(f"✅ Tenure: {metrics['tenure_days']} days")
        
        # Check activity score
        if "min_activity_score" in thresholds:
            if metrics["activity_score"] < thresholds["min_activity_score"]:
                confidence *= 0.7
                reasons.append(f"⚠️ Activity score below ideal: {metrics['activity_score']:.2f}/{thresholds['min_activity_score']}")
            else:
                reasons.append(f"✅ Activity score: {metrics['activity_score']:.2f}")
        
        # Check flags
        if "max_flags" in thresholds:
            if metrics["active_flags"] > thresholds["max_flags"]:
                return False, 0.0, f"Too many active flags: {metrics['active_flags']}/{thresholds['max_flags']}"
            reasons.append(f"✅ Clean record: {metrics['active_flags']} flags")
        
        # Calculate final confidence based on metrics
        confidence *= min(1.0, metrics["activity_score"] * 1.2)
        
        return True, confidence, "\n".join(reasons)

    async def check_demotion_warning(self, metrics: dict) -> tuple[bool, float, str]:
        """Check if staff member should receive a demotion warning.
        
        Returns: (should_warn, confidence, reason)
        """
        thresholds = self.DEFAULT_THRESHOLDS["demotion_warning"]
        reasons = []
        issues = 0
        
        # Check low activity
        if metrics["total_7d"] <= thresholds["max_actions_7d"]:
            reasons.append(f"⚠️ Low recent activity: {metrics['total_7d']} actions in 7 days")
            issues += 1
        
        if metrics["total_30d"] <= thresholds["max_actions_30d"]:
            reasons.append(f"⚠️ Low monthly activity: {metrics['total_30d']} actions in 30 days")
            issues += 1
        
        # Check activity score
        if metrics["activity_score"] < thresholds["min_activity_score"]:
            reasons.append(f"⚠️ Low activity score: {metrics['activity_score']:.2f}")
            issues += 1
        
        # Check flags
        if metrics["active_flags"] >= 2:
            reasons.append(f"⚠️ Multiple active flags: {metrics['active_flags']}")
            issues += 1
        
        if issues >= 2:
            confidence = min(0.95, issues * 0.3)
            return True, confidence, "\n".join(reasons)
        
        return False, 0.0, "Performance within acceptable range"

    async def generate_promotion_suggestion(
        self,
        *,
        guild: discord.Guild,
        staff_member: discord.Member,
        settings: GuildSettings
    ) -> int | None:
        """Generate a promotion suggestion for a staff member.
        
        Returns: suggestion_id if created, None otherwise
        """
        metrics = await self.analyze_staff_performance(guild, staff_member, settings)
        current_level = metrics["current_level"]
        
        # Determine promotion path
        promotion_path = None
        suggested_role = None
        
        if current_level == "moderator":
            promotion_path = "moderator_to_senior"
            suggested_role = "senior_mod"
        elif current_level == "senior_mod":
            promotion_path = "senior_to_head"
            suggested_role = "head_mod"
        else:
            # No promotion path available
            return None
        
        # Check eligibility
        eligible, confidence, reason = await self.check_promotion_eligibility(metrics, promotion_path)
        
        if not eligible or confidence < 0.5:
            logger.debug(f"Staff member {staff_member.id} not eligible for promotion: {reason}")
            return None
        
        # Create suggestion
        metrics_json = json.dumps(metrics)
        suggestion_id = await self.db.add_promotion_suggestion(
            guild_id=guild.id,
            user_id=staff_member.id,
            suggestion_type="promotion",
            current_role=current_level,
            suggested_role=suggested_role,
            confidence=confidence,
            reason=reason,
            metrics=metrics_json
        )
        
        logger.info(f"Generated promotion suggestion {suggestion_id} for {staff_member.id} in {guild.id}")
        return suggestion_id

    async def generate_demotion_warning(
        self,
        *,
        guild: discord.Guild,
        staff_member: discord.Member,
        settings: GuildSettings
    ) -> int | None:
        """Generate a demotion warning for underperforming staff.
        
        Returns: suggestion_id if created, None otherwise
        """
        metrics = await self.analyze_staff_performance(guild, staff_member, settings)
        current_level = metrics["current_level"]
        
        # Check if warning is warranted
        should_warn, confidence, reason = await self.check_demotion_warning(metrics)
        
        if not should_warn or confidence < 0.5:
            return None
        
        # Create suggestion
        metrics_json = json.dumps(metrics)
        suggestion_id = await self.db.add_promotion_suggestion(
            guild_id=guild.id,
            user_id=staff_member.id,
            suggestion_type="demotion_warning",
            current_role=current_level,
            suggested_role=None,
            confidence=confidence,
            reason=reason,
            metrics=metrics_json
        )
        
        logger.info(f"Generated demotion warning {suggestion_id} for {staff_member.id} in {guild.id}")
        return suggestion_id

    async def analyze_all_staff(self, guild: discord.Guild, settings: GuildSettings) -> dict:
        """Analyze all staff members and generate suggestions.
        
        Returns: dict with counts of suggestions generated
        """
        promotions = []
        warnings = []
        
        # Get all staff members
        staff_role_ids = set(
            settings.staff_role_ids +
            settings.moderator_role_ids +
            settings.senior_mod_role_ids +
            settings.head_mod_role_ids
        )
        
        for member in guild.members:
            if member.bot:
                continue
            
            # Check if member has any staff role
            if not any(r.id in staff_role_ids for r in member.roles):
                continue
            
            # Generate promotion suggestion
            promo_id = await self.generate_promotion_suggestion(
                guild=guild,
                staff_member=member,
                settings=settings
            )
            if promo_id:
                promotions.append(promo_id)
            
            # Generate demotion warning (only if no promotion suggested)
            if not promo_id:
                warn_id = await self.generate_demotion_warning(
                    guild=guild,
                    staff_member=member,
                    settings=settings
                )
                if warn_id:
                    warnings.append(warn_id)
        
        logger.info(f"Staff analysis complete for guild {guild.id}: {len(promotions)} promotions, {len(warnings)} warnings")
        
        return {
            "promotions": promotions,
            "warnings": warnings,
            "total_staff": len([m for m in guild.members if any(r.id in staff_role_ids for r in m.roles)]),
        }

    async def create_suggestion_embed(self, suggestion_row) -> discord.Embed:
        """Create an embed for a promotion suggestion."""
        suggestion_type = suggestion_row["suggestion_type"]
        user_id = suggestion_row["user_id"]
        current_role = suggestion_row["current_role"] or "Unknown"
        suggested_role = suggestion_row["suggested_role"] or "N/A"
        confidence = suggestion_row["confidence"]
        reason = suggestion_row["reason"] or "No reason provided"
        timestamp = suggestion_row["timestamp"]
        
        if suggestion_type == "promotion":
            title = f"📈 Promotion Suggestion"
            color = config.EMBED_COLOR_SUCCESS
            description = f"<@{user_id}> is eligible for promotion."
        else:
            title = f"📉 Demotion Warning"
            color = config.EMBED_COLOR_ERROR
            description = f"<@{user_id}> shows declining performance."
        
        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=datetime.fromisoformat(timestamp) if timestamp else utcnow()
        )
        
        embed.add_field(name="👤 Staff Member", value=f"<@{user_id}>", inline=True)
        embed.add_field(name="📊 Current Role", value=current_role.replace("_", " ").title(), inline=True)
        
        if suggestion_type == "promotion":
            embed.add_field(name="🎯 Suggested Role", value=suggested_role.replace("_", " ").title(), inline=True)
        
        embed.add_field(name="🎲 Confidence", value=f"{confidence:.1%}", inline=True)
        embed.add_field(name="📋 Analysis", value=reason, inline=False)
        
        # Parse and display metrics
        try:
            metrics = json.loads(suggestion_row["metrics"] or "{}")
            metrics_text = (
                f"**7-Day Activity:** {metrics.get('total_7d', 0)} actions\n"
                f"**30-Day Activity:** {metrics.get('total_30d', 0)} actions\n"
                f"**Activity Score:** {metrics.get('activity_score', 0):.2f}\n"
                f"**Active Flags:** {metrics.get('active_flags', 0)}\n"
                f"**Tenure:** {metrics.get('tenure_days', 0)} days"
            )
            embed.add_field(name="📈 Metrics", value=metrics_text, inline=False)
        except Exception:
            pass
        
        embed.set_footer(text=f"{config.BOT_NAME} • Suggestion ID: {suggestion_row['id']}")
        
        return embed
