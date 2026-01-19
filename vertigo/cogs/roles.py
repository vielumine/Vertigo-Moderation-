"""Role management commands (basic/temp/persistent + mass variants)."""

from __future__ import annotations

import logging

import discord
from discord.ext import commands

from vertigo.database import Database
from vertigo.helpers import (
    attach_gif,
    commands_channel_check,
    extract_id,
    make_embed,
    parse_duration,
    require_level,
    safe_delete,
)

logger = logging.getLogger(__name__)


class RolesCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @property
    def db(self) -> Database:
        return self.bot.db  # type: ignore[attr-defined]

    def _can_manage_role(self, actor: discord.Member, role: discord.Role) -> bool:
        if actor.guild_permissions.administrator:
            return True
        return actor.top_role > role

    @commands.command(name="role")
    @commands.guild_only()
    @commands_channel_check()
    @require_level("moderator")
    async def role(self, ctx: commands.Context, member: discord.Member, role: discord.Role) -> None:
        """Assign a role."""

        if not self._can_manage_role(ctx.author, role):  # type: ignore[arg-type]
            embed = make_embed(action="error", title="Role Hierarchy", description="You can't assign that role.")
            await ctx.send(embed=embed)
            return

        try:
            await member.add_roles(role, reason=f"Role assigned by {ctx.author}")
        except discord.Forbidden:
            embed = make_embed(action="error", title="Missing Permissions", description="I can't assign that role.")
            await ctx.send(embed=embed)
            return

        embed = make_embed(action="role", title="Role Assigned", description=f"Assigned {role.mention} to {member.mention}.")
        embed, file = attach_gif(embed, gif_key="ROLE_ASSIGNED")
        message = await ctx.send(embed=embed, file=file)

        await self.db.add_modlog(
            guild_id=ctx.guild.id,  # type: ignore[union-attr]
            action_type="role_assign",
            user_id=member.id,
            moderator_id=ctx.author.id,
            target_id=role.id,
            reason="Role assigned",
            message_id=message.id,
        )
        await safe_delete(ctx.message)

    @commands.command(name="removerole")
    @commands.guild_only()
    @commands_channel_check()
    @require_level("moderator")
    async def removerole(self, ctx: commands.Context, member: discord.Member, role: discord.Role) -> None:
        """Remove a role."""

        if not self._can_manage_role(ctx.author, role):  # type: ignore[arg-type]
            embed = make_embed(action="error", title="Role Hierarchy", description="You can't remove that role.")
            await ctx.send(embed=embed)
            return

        try:
            await member.remove_roles(role, reason=f"Role removed by {ctx.author}")
        except discord.Forbidden:
            embed = make_embed(action="error", title="Missing Permissions", description="I can't remove that role.")
            await ctx.send(embed=embed)
            return

        embed = make_embed(action="removerole", title="Role Removed", description=f"Removed {role.mention} from {member.mention}.")
        embed, file = attach_gif(embed, gif_key="ROLE_REMOVED")
        message = await ctx.send(embed=embed, file=file)

        await self.db.add_modlog(
            guild_id=ctx.guild.id,  # type: ignore[union-attr]
            action_type="role_remove",
            user_id=member.id,
            moderator_id=ctx.author.id,
            target_id=role.id,
            reason="Role removed",
            message_id=message.id,
        )
        await safe_delete(ctx.message)

    @commands.command(name="temprole")
    @commands.guild_only()
    @commands_channel_check()
    @require_level("moderator")
    async def temprole(self, ctx: commands.Context, member: discord.Member, role: discord.Role, duration: str) -> None:
        """Assign a temporary role."""

        seconds = parse_duration(duration)

        if not self._can_manage_role(ctx.author, role):  # type: ignore[arg-type]
            embed = make_embed(action="error", title="Role Hierarchy", description="You can't assign that role.")
            await ctx.send(embed=embed)
            return

        try:
            await member.add_roles(role, reason=f"Temp role assigned by {ctx.author}")
        except discord.Forbidden:
            embed = make_embed(action="error", title="Missing Permissions", description="I can't assign that role.")
            await ctx.send(embed=embed)
            return

        await self.db.add_temp_role(
            guild_id=ctx.guild.id,  # type: ignore[union-attr]
            user_id=member.id,
            role_id=role.id,
            assigned_by=ctx.author.id,
            duration_seconds=seconds,
        )

        embed = make_embed(
            action="temprole",
            title="Temporary Role Assigned",
            description=f"Assigned {role.mention} to {member.mention} for **{duration}**.",
        )
        embed, file = attach_gif(embed, gif_key="TEMP_ROLE")
        message = await ctx.send(embed=embed, file=file)

        await self.db.add_modlog(
            guild_id=ctx.guild.id,  # type: ignore[union-attr]
            action_type="temp_role",
            user_id=member.id,
            moderator_id=ctx.author.id,
            target_id=role.id,
            reason=f"Temp role for {duration}",
            message_id=message.id,
        )

        await safe_delete(ctx.message)

    @commands.command(name="removetemp")
    @commands.guild_only()
    @commands_channel_check()
    @require_level("moderator")
    async def removetemp(self, ctx: commands.Context, member: discord.Member, role: discord.Role) -> None:
        """Remove a temp role assignment."""

        await self.db.deactivate_temp_role(guild_id=ctx.guild.id, user_id=member.id, role_id=role.id)  # type: ignore[union-attr]
        try:
            if role in member.roles:
                await member.remove_roles(role, reason=f"Temp role removed by {ctx.author}")
        except discord.Forbidden:
            pass

        embed = make_embed(action="removetemp", title="Temp Role Removed", description=f"Removed temp role {role.mention} from {member.mention}.")
        message = await ctx.send(embed=embed)

        await self.db.add_modlog(
            guild_id=ctx.guild.id,  # type: ignore[union-attr]
            action_type="temp_role_removed",
            user_id=member.id,
            moderator_id=ctx.author.id,
            target_id=role.id,
            reason="Temp role removed",
            message_id=message.id,
        )

        await safe_delete(ctx.message)

    @commands.command(name="persistrole")
    @commands.guild_only()
    @commands_channel_check()
    @require_level("senior_mod")
    async def persistrole(self, ctx: commands.Context, member: discord.Member, role: discord.Role) -> None:
        """Assign a persistent role."""

        if not self._can_manage_role(ctx.author, role):  # type: ignore[arg-type]
            embed = make_embed(action="error", title="Role Hierarchy", description="You can't assign that role.")
            await ctx.send(embed=embed)
            return

        try:
            await member.add_roles(role, reason=f"Persistent role assigned by {ctx.author}")
        except discord.Forbidden:
            embed = make_embed(action="error", title="Missing Permissions", description="I can't assign that role.")
            await ctx.send(embed=embed)
            return

        await self.db.add_persistent_role(
            guild_id=ctx.guild.id,  # type: ignore[union-attr]
            user_id=member.id,
            role_id=role.id,
            assigned_by=ctx.author.id,
        )

        embed = make_embed(action="persistrole", title="Persistent Role Assigned", description=f"Assigned persistent {role.mention} to {member.mention}.")
        embed, file = attach_gif(embed, gif_key="PERSIST_ROLE")
        message = await ctx.send(embed=embed, file=file)

        await self.db.add_modlog(
            guild_id=ctx.guild.id,  # type: ignore[union-attr]
            action_type="persist_role",
            user_id=member.id,
            moderator_id=ctx.author.id,
            target_id=role.id,
            reason="Persistent role assigned",
            message_id=message.id,
        )

        await safe_delete(ctx.message)

    @commands.command(name="removepersist")
    @commands.guild_only()
    @commands_channel_check()
    @require_level("senior_mod")
    async def removepersist(self, ctx: commands.Context, member: discord.Member, role: discord.Role) -> None:
        """Remove a persistent role assignment."""

        await self.db.deactivate_persistent_role(guild_id=ctx.guild.id, user_id=member.id, role_id=role.id)  # type: ignore[union-attr]
        try:
            if role in member.roles:
                await member.remove_roles(role, reason=f"Persistent role removed by {ctx.author}")
        except discord.Forbidden:
            pass

        embed = make_embed(action="removepersist", title="Persistent Role Removed", description=f"Removed persistent role {role.mention} from {member.mention}.")
        message = await ctx.send(embed=embed)

        await self.db.add_modlog(
            guild_id=ctx.guild.id,  # type: ignore[union-attr]
            action_type="persist_role_removed",
            user_id=member.id,
            moderator_id=ctx.author.id,
            target_id=role.id,
            reason="Persistent role removed",
            message_id=message.id,
        )

        await safe_delete(ctx.message)

    # ----------------------------- Mass helpers -----------------------------

    def _parse_members(self, ctx: commands.Context, raw: str) -> list[discord.Member]:
        members: list[discord.Member] = []
        for part in raw.split(","):
            part = part.strip()
            if not part:
                continue
            member_id = int(part) if part.isdigit() else extract_id(part)
            if not member_id:
                continue
            member = ctx.guild.get_member(int(member_id))  # type: ignore[union-attr]
            if member:
                members.append(member)
        return members

    async def _mass_role_op(self, ctx: commands.Context, *, members: list[discord.Member], role: discord.Role, add: bool) -> tuple[int, int]:
        ok = 0
        failed = 0
        for m in members:
            try:
                if add:
                    await m.add_roles(role, reason=f"Mass role op by {ctx.author}")
                else:
                    await m.remove_roles(role, reason=f"Mass role op by {ctx.author}")
                ok += 1
            except Exception:
                failed += 1
        return ok, failed

    @commands.command(name="massrole")
    @commands.guild_only()
    @commands_channel_check()
    @require_level("head_mod")
    async def massrole(self, ctx: commands.Context, users: str, role: discord.Role) -> None:
        members = self._parse_members(ctx, users)
        ok, failed = await self._mass_role_op(ctx, members=members, role=role, add=True)
        embed = make_embed(action="massrole", title="Mass Role Results", description=f"Assigned {role.mention}.\nSucceeded: **{ok}**\nFailed: **{failed}**")
        await ctx.send(embed=embed)
        await safe_delete(ctx.message)

    @commands.command(name="massremoverole")
    @commands.guild_only()
    @commands_channel_check()
    @require_level("head_mod")
    async def massremoverole(self, ctx: commands.Context, users: str, role: discord.Role) -> None:
        members = self._parse_members(ctx, users)
        ok, failed = await self._mass_role_op(ctx, members=members, role=role, add=False)
        embed = make_embed(action="massremoverole", title="Mass Remove Role Results", description=f"Removed {role.mention}.\nSucceeded: **{ok}**\nFailed: **{failed}**")
        await ctx.send(embed=embed)
        await safe_delete(ctx.message)

    @commands.command(name="masstemprole")
    @commands.guild_only()
    @commands_channel_check()
    @require_level("head_mod")
    async def masstemprole(self, ctx: commands.Context, users: str, role: discord.Role, duration: str) -> None:
        seconds = parse_duration(duration)
        members = self._parse_members(ctx, users)
        ok = 0
        failed = 0
        for m in members:
            try:
                await m.add_roles(role, reason=f"Mass temp role by {ctx.author}")
                await self.db.add_temp_role(guild_id=ctx.guild.id, user_id=m.id, role_id=role.id, assigned_by=ctx.author.id, duration_seconds=seconds)  # type: ignore[union-attr]
                ok += 1
            except Exception:
                failed += 1
        embed = make_embed(action="masstemprole", title="Mass Temp Role Results", description=f"Assigned {role.mention} for {duration}.\nSucceeded: **{ok}**\nFailed: **{failed}**")
        await ctx.send(embed=embed)
        await safe_delete(ctx.message)

    @commands.command(name="massremovetemp")
    @commands.guild_only()
    @commands_channel_check()
    @require_level("head_mod")
    async def massremovetemp(self, ctx: commands.Context, users: str, role: discord.Role) -> None:
        members = self._parse_members(ctx, users)
        ok = 0
        failed = 0
        for m in members:
            try:
                await self.db.deactivate_temp_role(guild_id=ctx.guild.id, user_id=m.id, role_id=role.id)  # type: ignore[union-attr]
                if role in m.roles:
                    await m.remove_roles(role, reason=f"Mass remove temp by {ctx.author}")
                ok += 1
            except Exception:
                failed += 1
        embed = make_embed(action="massremovetemp", title="Mass Remove Temp Role Results", description=f"Role: {role.mention}\nSucceeded: **{ok}**\nFailed: **{failed}**")
        await ctx.send(embed=embed)
        await safe_delete(ctx.message)

    @commands.command(name="masspersistrole")
    @commands.guild_only()
    @commands_channel_check()
    @require_level("head_mod")
    async def masspersistrole(self, ctx: commands.Context, users: str, role: discord.Role) -> None:
        members = self._parse_members(ctx, users)
        ok = 0
        failed = 0
        for m in members:
            try:
                await m.add_roles(role, reason=f"Mass persist role by {ctx.author}")
                await self.db.add_persistent_role(guild_id=ctx.guild.id, user_id=m.id, role_id=role.id, assigned_by=ctx.author.id)  # type: ignore[union-attr]
                ok += 1
            except Exception:
                failed += 1
        embed = make_embed(action="masspersistrole", title="Mass Persistent Role Results", description=f"Assigned {role.mention}.\nSucceeded: **{ok}**\nFailed: **{failed}**")
        await ctx.send(embed=embed)
        await safe_delete(ctx.message)

    @commands.command(name="massremovepersist")
    @commands.guild_only()
    @commands_channel_check()
    @require_level("head_mod")
    async def massremovepersist(self, ctx: commands.Context, users: str, role: discord.Role) -> None:
        members = self._parse_members(ctx, users)
        ok = 0
        failed = 0
        for m in members:
            try:
                await self.db.deactivate_persistent_role(guild_id=ctx.guild.id, user_id=m.id, role_id=role.id)  # type: ignore[union-attr]
                if role in m.roles:
                    await m.remove_roles(role, reason=f"Mass remove persistent role by {ctx.author}")
                ok += 1
            except Exception:
                failed += 1
        embed = make_embed(action="massremovepersist", title="Mass Remove Persistent Role Results", description=f"Role: {role.mention}\nSucceeded: **{ok}**\nFailed: **{failed}**")
        await ctx.send(embed=embed)
        await safe_delete(ctx.message)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RolesCog(bot))
