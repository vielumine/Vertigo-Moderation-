"""
Luna Bot Hierarchy Cog
Handles role management and permission configuration.
"""

import discord
from discord.ext import commands

from database import (
    get_guild_setting,
    set_guild_setting,
)
from helpers import (
    make_embed,
    is_admin,
)
from config import (
    DEEP_SPACE,
    COLOR_ERROR,
    COLOR_SUCCESS,
)


class Hierarchy(commands.Cog):
    """Hierarchy and role management commands."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setlockcategories(self, ctx: commands.Context, *categories: discord.CategoryChannel):
        """Set the categories to lock during lockdowns."""
        if not await is_admin(ctx.author, ctx.guild):
            await ctx.reply(embed=make_embed(
                title="❌ Insufficient Permissions",
                description="This command requires administrator privileges.",
                color=COLOR_ERROR
            ))
            return
        
        if not categories:
            await ctx.reply(embed=make_embed(
                title="❌ No Categories Provided",
                description="Please provide category channels to lock.\nUsage: `,setlockcategories #category1 #category2`",
                color=COLOR_ERROR
            ))
            return
        
        import json
        category_ids = [cat.id for cat in categories]
        
        await set_guild_setting(ctx.guild.id, "lock_categories", json.dumps(category_ids))
        
        await ctx.reply(embed=make_embed(
            title="✅ Lock Categories Set",
            description=f"Set {len(categories)} category/ies to lock during lockdowns.",
            color=COLOR_SUCCESS,
            fields=[
                ("Categories", "\n".join(cat.name for cat in categories[:5]), False),
            ]
        ))
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def clearlockcategories(self, ctx: commands.Context):
        """Clear all lock categories."""
        if not await is_admin(ctx.author, ctx.guild):
            await ctx.reply(embed=make_embed(
                title="❌ Insufficient Permissions",
                description="This command requires administrator privileges.",
                color=COLOR_ERROR
            ))
            return
        
        await set_guild_setting(ctx.guild.id, "lock_categories", "[]")
        
        await ctx.reply(embed=make_embed(
            title="✅ Lock Categories Cleared",
            description="All lock categories have been cleared.",
            color=COLOR_SUCCESS
        ))
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def viewlockcategories(self, ctx: commands.Context):
        """View currently configured lock categories."""
        lock_categories_str = await get_guild_setting(ctx.guild.id, "lock_categories")
        
        if not lock_categories_str or lock_categories_str == "[]":
            await ctx.reply(embed=make_embed(
                title="📋 Lock Categories",
                description="No lock categories configured.",
                color=DEEP_SPACE
            ))
            return
        
        import json
        try:
            category_ids = json.loads(lock_categories_str)
        except:
            await ctx.reply(embed=make_embed(
                title="❌ Invalid Data",
                description="Lock categories data is corrupted. Contact an administrator.",
                color=COLOR_ERROR
            ))
            return
        
        # Get categories
        categories = []
        for cat_id in category_ids:
            category = ctx.guild.get_channel(cat_id)
            if category and isinstance(category, discord.CategoryChannel):
                categories.append(f"• {category.name} ({cat_id})")
        
        embed = make_embed(
            title="📋 Lock Categories",
            color=DEEP_SPACE,
            fields=[
                ("Categories", "\n".join(categories) if categories else "None found", False),
            ]
        )
        
        await ctx.reply(embed=embed)
    
    @commands.group(name="permissions", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def permissions(self, ctx: commands.Context):
        """View permission configuration."""
        if not await is_admin(ctx.author, ctx.guild):
            await ctx.reply(embed=make_embed(
                title="❌ Insufficient Permissions",
                description="This command requires administrator privileges.",
                color=COLOR_ERROR
            ))
            return
        
        # Get configured roles
        member_role_id = await get_guild_setting(ctx.guild.id, "member_role_id")
        staff_role_id = await get_guild_setting(ctx.guild.id, "staff_role_id")
        admin_role_id = await get_guild_setting(ctx.guild.id, "admin_role_id")
        
        embed = make_embed(
            title="🔐 Permission Configuration",
            color=DEEP_SPACE,
            fields=[
                ("Member Role", f"<@&{member_role_id}>" if member_role_id else "Not set", True),
                ("Staff Role", f"<@&{staff_role_id}>" if staff_role_id else "Not set", True),
                ("Admin Role", f"<@&{admin_role_id}>" if admin_role_id else "Not set", True),
                ("Info", "Use `,setup <role_type> <role>` to update roles.", False),
            ]
        )
        
        await ctx.reply(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Hierarchy(bot))
