"""Tags system for Luna - Helper+ viewing, Staff+ management."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

import config
from database import Database
from helpers import (
    make_embed,
    require_helper,
    require_level,
    safe_delete,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class TagsCog(commands.Cog):
    """Tags system for organized information."""
    
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
    
    @property
    def db(self) -> Database:
        return self.bot.db  # type: ignore[attr-defined]
    
    @commands.command(name="tag")
    @commands.guild_only()
    @require_helper()
    async def view_tag(self, ctx: commands.Context, category: str, *, title: str) -> None:
        """View a specific tag (Helper+ only).
        
        Usage:
        ,tag category_name tag_title
        """
        tag = await self.db.get_tag(
            guild_id=ctx.guild.id,
            category=category.lower(),
            title=title.lower()
        )
        
        if not tag:
            embed = make_embed(
                action="error",
                title="❌ Tag Not Found",
                description=f"No tag found with category `{category}` and title `{title}`."
            )
            await ctx.send(embed=embed)
            return
        
        embed = make_embed(
            action="tag",
            title=f"🌙 {tag['category'].title()} / {tag['title'].title()}",
            description=tag['description']
        )
        embed.add_field(name="Created By", value=f"<@{tag['creator_id']}>", inline=True)
        embed.add_field(name="Created At", value=f"<t:{int(tag['created_at'][:10])}:R>", inline=True)
        
        await ctx.send(embed=embed)
        await safe_delete(ctx.message)
    
    @commands.command(name="tags")
    @commands.guild_only()
    @require_helper()
    async def list_tags(self, ctx: commands.Context, category: str | None = None) -> None:
        """List all tags or tags in a category (Helper+ only).
        
        Usage:
        ,tags [category]
        """
        if category:
            tags = await self.db.get_tags_by_category(ctx.guild.id, category.lower())
            title = f"🌙 Tags in {category.title()}"
        else:
            tags = await self.db.get_all_tags(ctx.guild.id)
            title = "🌙 All Tags"
        
        if not tags:
            embed = make_embed(
                action="tags",
                title=title,
                description="No tags found."
            )
            await ctx.send(embed=embed)
            return
        
        # Group by category
        categories = {}
        for tag in tags:
            cat = tag['category']
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(tag['title'])
        
        description = ""
        for cat, titles in sorted(categories.items()):
            description += f"\n**{cat.title()}**\n"
            description += ", ".join(f"`{t}`" for t in sorted(titles))
            description += "\n"
        
        embed = make_embed(
            action="tags",
            title=title,
            description=description.strip()
        )
        embed.set_footer(text=f"Use ,tag <category> <title> to view a specific tag")
        
        await ctx.send(embed=embed)
        await safe_delete(ctx.message)
    
    @commands.command(name="tag_create", aliases=["createtag"])
    @commands.guild_only()
    @require_level("moderator")
    async def create_tag(self, ctx: commands.Context, category: str, title: str, *, description: str) -> None:
        """Create a new tag (Staff+ only).
        
        Usage:
        ,tag_create category title description
        """
        # Check if tag exists
        existing = await self.db.get_tag(
            guild_id=ctx.guild.id,
            category=category.lower(),
            title=title.lower()
        )
        
        if existing:
            embed = make_embed(
                action="error",
                title="❌ Tag Exists",
                description=f"A tag with category `{category}` and title `{title}` already exists."
            )
            await ctx.send(embed=embed)
            return
        
        # Create tag
        await self.db.create_tag(
            guild_id=ctx.guild.id,
            category=category.lower(),
            title=title.lower(),
            description=description,
            creator_id=ctx.author.id
        )
        
        embed = make_embed(
            action="success",
            title="✅ Tag Created",
            description=f"Created tag `{title}` in category `{category}`."
        )
        await ctx.send(embed=embed)
        await safe_delete(ctx.message)
    
    @commands.command(name="tag_edit", aliases=["edittag"])
    @commands.guild_only()
    @require_level("moderator")
    async def edit_tag(self, ctx: commands.Context, category: str, title: str, *, description: str) -> None:
        """Edit an existing tag (Staff+ only).
        
        Usage:
        ,tag_edit category title new_description
        """
        # Check if tag exists
        existing = await self.db.get_tag(
            guild_id=ctx.guild.id,
            category=category.lower(),
            title=title.lower()
        )
        
        if not existing:
            embed = make_embed(
                action="error",
                title="❌ Tag Not Found",
                description=f"No tag found with category `{category}` and title `{title}`."
            )
            await ctx.send(embed=embed)
            return
        
        # Update tag
        await self.db.update_tag(
            guild_id=ctx.guild.id,
            category=category.lower(),
            title=title.lower(),
            description=description
        )
        
        embed = make_embed(
            action="success",
            title="✅ Tag Updated",
            description=f"Updated tag `{title}` in category `{category}`."
        )
        await ctx.send(embed=embed)
        await safe_delete(ctx.message)
    
    @commands.command(name="tag_delete", aliases=["deletetag", "removetag"])
    @commands.guild_only()
    @require_level("moderator")
    async def delete_tag(self, ctx: commands.Context, category: str, *, title: str) -> None:
        """Delete a tag (Staff+ only).
        
        Usage:
        ,tag_delete category title
        """
        # Check if tag exists
        existing = await self.db.get_tag(
            guild_id=ctx.guild.id,
            category=category.lower(),
            title=title.lower()
        )
        
        if not existing:
            embed = make_embed(
                action="error",
                title="❌ Tag Not Found",
                description=f"No tag found with category `{category}` and title `{title}`."
            )
            await ctx.send(embed=embed)
            return
        
        # Delete tag
        await self.db.delete_tag(
            guild_id=ctx.guild.id,
            category=category.lower(),
            title=title.lower()
        )
        
        embed = make_embed(
            action="success",
            title="✅ Tag Deleted",
            description=f"Deleted tag `{title}` from category `{category}`."
        )
        await ctx.send(embed=embed)
        await safe_delete(ctx.message)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TagsCog(bot))
