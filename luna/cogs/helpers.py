"""
Luna Bot Helpers Cog
Handles helper-only commands: tag viewing and search.
"""

import discord
from discord.ext import commands

from database import (
    get_tag,
    search_tags,
    create_tag,
    delete_tag,
    edit_tag,
)
from helpers import (
    make_embed,
    get_embed_color,
    is_helper,
    is_staff,
    PaginationView,
)
from config import (
    DEEP_SPACE,
    COLOR_ERROR,
    COLOR_SUCCESS,
    COLOR_WARNING,
)


class Helpers(commands.Cog):
    """Helper and tags system commands."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @commands.command(name="tag")
    async def view_tag(self, ctx: commands.Context, category: str, *, title: str = None):
        """
        View a single tag.
        HELPER+ only.
        """
        if not await is_helper(ctx.author, ctx.guild):
            await ctx.reply(embed=make_embed(
                title="❌ Insufficient Permissions",
                description="This command requires helper privileges.",
                color=COLOR_ERROR
            ))
            return
        
        # If title not provided, treat first word as title (this is a common usage)
        if title is None:
            await ctx.reply(embed=make_embed(
                title="❌ Invalid Usage",
                description="Usage: `,tag <category> <title>`",
                color=COLOR_ERROR
            ))
            return
        
        # Get tag
        tag = await get_tag(ctx.guild.id, category, title)
        
        if not tag:
            await ctx.reply(embed=make_embed(
                title="❌ Tag Not Found",
                description=f"No tag found in category `{category}` with title `{title}`.",
                color=COLOR_ERROR
            ))
            return
        
        # Show tag
        embed = make_embed(
            title=f"📄 {category}/{title}",
            description=tag['description'],
            color=get_embed_color("tag"),
            footer=f"Created by <@{tag['creator_id']}>"
        )
        
        await ctx.reply(embed=embed)
    
    @commands.command(name="tags")
    async def list_tags(self, ctx: commands.Context, category: str = None, *, search: str = None):
        """
        List tags with pagination.
        HELPER+ only.
        """
        if not await is_helper(ctx.author, ctx.guild):
            await ctx.reply(embed=make_embed(
                title="❌ Insufficient Permissions",
                description="This command requires helper privileges.",
                color=COLOR_ERROR
            ))
            return
        
        # Search tags
        tags = await search_tags(ctx.guild.id, category, search)
        
        if not tags:
            await ctx.reply(embed=make_embed(
                title="❌ No Tags Found",
                description=f"No tags found matching your criteria.",
                color=COLOR_ERROR
            ))
            return
        
        # Create pagination function
        def create_embed(items, page, total_pages):
            embed = make_embed(
                title=f"📚 Tags ({len(tags)} total)",
                color=get_embed_color("tags"),
                footer=f"Page {page + 1}/{total_pages}"
            )
            
            for tag in items:
                embed.add_field(
                    name=f"{tag['category']}/{tag['title']}",
                    value=tag['description'][:100] + "..." if len(tag['description']) > 100 else tag['description'],
                    inline=False
                )
            
            return embed
        
        view = PaginationView(tags, create_embed)
        embed = create_embed(view.get_current_items(), 0, view.total_pages)
        await ctx.reply(embed=embed, view=view)
    
    @commands.command(name="tag_create")
    @commands.has_permissions(manage_messages=True)
    async def create_tag_cmd(self, ctx: commands.Context, category: str, title: str, *, description: str):
        """
        Create a tag.
        STAFF+ only.
        """
        if not await is_staff(ctx.author, ctx.guild):
            await ctx.reply(embed=make_embed(
                title="❌ Insufficient Permissions",
                description="This command requires staff privileges.",
                color=COLOR_ERROR
            ))
            return
        
        # Create tag
        tag_id = await create_tag(ctx.guild.id, category, title, description, ctx.author.id)
        
        # Log to channel
        await ctx.reply(embed=make_embed(
            title="✅ Tag Created",
            description=f"Tag `{category}/{title}` has been created.\n**Tag ID:** {tag_id}",
            color=get_embed_color("tag_create")
        ))
    
    @commands.command(name="tag_edit")
    @commands.has_permissions(manage_messages=True)
    async def edit_tag_cmd(self, ctx: commands.Context, category: str, title: str, *, new_description: str):
        """
        Edit a tag description.
        STAFF+ only.
        """
        if not await is_staff(ctx.author, ctx.guild):
            await ctx.reply(embed=make_embed(
                title="❌ Insufficient Permissions",
                description="This command requires staff privileges.",
                color=COLOR_ERROR
            ))
            return
        
        # Edit tag
        success = await edit_tag(ctx.guild.id, category, title, new_description)
        
        if success:
            await ctx.reply(embed=make_embed(
                title="✅ Tag Updated",
                description=f"Tag `{category}/{title}` has been updated.",
                color=get_embed_color("tag_edit")
            ))
        else:
            await ctx.reply(embed=make_embed(
                title="❌ Tag Not Found",
                description=f"Tag `{category}/{title}` does not exist.",
                color=COLOR_ERROR
            ))
    
    @commands.command(name="tag_delete")
    @commands.has_permissions(manage_messages=True)
    async def delete_tag_cmd(self, ctx: commands.Context, category: str, title: str):
        """
        Delete a tag.
        STAFF+ only.
        """
        if not await is_staff(ctx.author, ctx.guild):
            await ctx.reply(embed=make_embed(
                title="❌ Insufficient Permissions",
                description="This command requires staff privileges.",
                color=COLOR_ERROR
            ))
            return
        
        # Delete tag
        success = await delete_tag(ctx.guild.id, category, title)
        
        if success:
            await ctx.reply(embed=make_embed(
                title="✅ Tag Deleted",
                description=f"Tag `{category}/{title}` has been deleted.",
                color=get_embed_color("tag_delete")
            ))
        else:
            await ctx.reply(embed=make_embed(
                title="❌ Tag Not Found",
                description=f"Tag `{category}/{title}` does not exist.",
                color=COLOR_ERROR
            ))


async def setup(bot: commands.Bot):
    await bot.add_cog(Helpers(bot))
