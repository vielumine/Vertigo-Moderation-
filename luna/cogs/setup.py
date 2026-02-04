"""
Luna Bot Setup Cog
Handles bot setup, configuration, and helper role assignment.
"""

import discord
from discord.ext import commands
from typing import Optional

from database import (
    get_guild_setting,
    set_guild_setting,
    set_helper_role,
    get_helper_role,
)
from helpers import (
    make_embed,
    get_embed_color,
    is_admin,
    add_loading_reaction,
)
from config import (
    DEEP_SPACE,
    STARLIGHT_BLUE,
    COLOR_ERROR,
    COLOR_SUCCESS,
    PREFIX,
)


class HelperButtonView(discord.ui.View):
    """View with helper assignment button."""
    
    def __init__(self, bot: commands.Bot, guild_id: int):
        super().__init__(timeout=None)
        self.bot = bot
        self.guild_id = guild_id
    
    @discord.ui.button(label="Apply for Helper", style=discord.ButtonStyle.primary, custom_id="helper_application")
    async def apply_helper(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Open modal for helper application."""
        modal = HelperApplicationModal(self.bot, self.guild_id)
        await interaction.response.send_modal(modal)


class HelperApplicationModal(discord.ui.Modal, title="Helper Application"):
    """Modal for helper application."""
    
    experience = discord.ui.TextInput(
        label="Previous Experience",
        placeholder="Describe any moderation experience...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=500
    )
    
    availability = discord.ui.TextInput(
        label="Availability",
        placeholder="When are you typically online?",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=300
    )
    
    def __init__(self, bot: commands.Bot, guild_id: int):
        super().__init__()
        self.bot = bot
        self.guild_id = guild_id
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle application submission."""
        from database import get_guild_setting
        from helpers import log_to_modlog_channel
        
        guild = self.bot.get_guild(self.guild_id)
        if not guild:
            await interaction.response.send_message(
                "❌ Error: Guild not found.",
                ephemeral=True
            )
            return
        
        modlog_channel_id = await get_guild_setting(self.guild_id, "modlog_channel_id")
        if not modlog_channel_id:
            await interaction.response.send_message(
                "❌ Modlog channel not configured. Please contact an administrator.",
                ephemeral=True
            )
            return
        
        # Send application to modlog
        embed = make_embed(
            title="📋 New Helper Application",
            color=STARLIGHT_BLUE,
            fields=[
                ("User", f"{interaction.user.mention} (ID: {interaction.user.id})", False),
                ("Experience", self.experience.value, False),
                ("Availability", self.availability.value, False),
            ]
        )
        
        modlog_channel = guild.get_channel(modlog_channel_id)
        if modlog_channel:
            await modlog_channel.send(embed=embed)
            await interaction.response.send_message(
                "✅ Application submitted successfully. Staff will review it shortly.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "❌ Error: Could not send application.",
                ephemeral=True
            )


class Setup(commands.Cog):
    """Setup and configuration commands."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @commands.group(name="setup", invoke_without_command=True)
    async def setup(self, ctx: commands.Context):
        """Main setup command. Shows current configuration."""
        if not await is_admin(ctx.author, ctx.guild):
            await ctx.reply(embed=make_embed(
                title="❌ Insufficient Permissions",
                description="This command requires administrator privileges.",
                color=COLOR_ERROR
            ))
            return
        
        # Get current settings
        prefix = await get_guild_setting(ctx.guild.id, "prefix")
        modlog_channel = await get_guild_setting(ctx.guild.id, "modlog_channel_id")
        join_leave_channel = await get_guild_setting(ctx.guild.id, "join_leave_channel_id")
        member_role = await get_guild_setting(ctx.guild.id, "member_role_id")
        staff_role = await get_guild_setting(ctx.guild.id, "staff_role_id")
        admin_role = await get_guild_setting(ctx.guild.id, "admin_role_id")
        mod_channel = await get_guild_setting(ctx.guild.id, "mod_channel_id")
        shift_channel = await get_guild_setting(ctx.guild.id, "shift_channel_id")
        helper_button_channel = await get_guild_setting(ctx.guild.id, "helper_button_channel_id")
        lock_categories = await get_guild_setting(ctx.guild.id, "lock_categories")
        
        embed = make_embed(
            title="⚙️ Guild Configuration",
            color=DEEP_SPACE,
            fields=[
                ("Prefix", prefix or PREFIX, True),
                ("Modlog Channel", f"<#{modlog_channel}>" if modlog_channel else "Not set", True),
                ("Join/Leave Channel", f"<#{join_leave_channel}>" if join_leave_channel else "Not set", True),
                ("Member Role", f"<@&{member_role}>" if member_role else "Not set", True),
                ("Staff Role", f"<@&{staff_role}>" if staff_role else "Not set", True),
                ("Admin Role", f"<@&{admin_role}>" if admin_role else "Not set", True),
                ("Mod Channel", f"<#{mod_channel}>" if mod_channel else "Not set", True),
                ("Shift Channel", f"<#{shift_channel}>" if shift_channel else "Not set", True),
                ("Helper Button Channel", f"<#{helper_button_channel}>" if helper_button_channel else "Not set", True),
                ("Lock Categories", lock_categories or "[]", True),
            ]
        )
        
        await ctx.reply(embed=embed)
    
    @setup.command(name="prefix")
    async def set_prefix(self, ctx: commands.Context, new_prefix: str):
        """Set the bot prefix for this guild."""
        if not await is_admin(ctx.author, ctx.guild):
            await ctx.reply(embed=make_embed(
                title="❌ Insufficient Permissions",
                description="This command requires administrator privileges.",
                color=COLOR_ERROR
            ))
            return
        
        await set_guild_setting(ctx.guild.id, "prefix", new_prefix)
        await ctx.reply(embed=make_embed(
            title="✅ Prefix Updated",
            description=f"Command prefix set to `{new_prefix}`",
            color=COLOR_SUCCESS
        ))
    
    @setup.command(name="modlog")
    async def set_modlog(self, ctx: commands.Context, channel: discord.TextChannel):
        """Set the modlog channel."""
        if not await is_admin(ctx.author, ctx.guild):
            await ctx.reply(embed=make_embed(
                title="❌ Insufficient Permissions",
                description="This command requires administrator privileges.",
                color=COLOR_ERROR
            ))
            return
        
        await set_guild_setting(ctx.guild.id, "modlog_channel_id", channel.id)
        await ctx.reply(embed=make_embed(
            title="✅ Modlog Channel Set",
            description=f"Moderation logs will be sent to {channel.mention}",
            color=COLOR_SUCCESS
        ))
    
    @setup.command(name="joinleave")
    async def set_joinleave(self, ctx: commands.Context, channel: discord.TextChannel):
        """Set the join/leave logging channel."""
        if not await is_admin(ctx.author, ctx.guild):
            await ctx.reply(embed=make_embed(
                title="❌ Insufficient Permissions",
                description="This command requires administrator privileges.",
                color=COLOR_ERROR
            ))
            return
        
        await set_guild_setting(ctx.guild.id, "join_leave_channel_id", channel.id)
        await ctx.reply(embed=make_embed(
            title="✅ Join/Leave Channel Set",
            description=f"Join and leave messages will be sent to {channel.mention}",
            color=COLOR_SUCCESS
        ))
    
    @setup.command(name="member_role")
    async def set_member_role(self, ctx: commands.Context, role: discord.Role):
        """Set the member role."""
        if not await is_admin(ctx.author, ctx.guild):
            await ctx.reply(embed=make_embed(
                title="❌ Insufficient Permissions",
                description="This command requires administrator privileges.",
                color=COLOR_ERROR
            ))
            return
        
        await set_guild_setting(ctx.guild.id, "member_role_id", role.id)
        await ctx.reply(embed=make_embed(
            title="✅ Member Role Set",
            description=f"Member role set to {role.mention}",
            color=COLOR_SUCCESS
        ))
    
    @setup.command(name="staff_role")
    async def set_staff_role(self, ctx: commands.Context, role: discord.Role):
        """Set the staff role."""
        if not await is_admin(ctx.author, ctx.guild):
            await ctx.reply(embed=make_embed(
                title="❌ Insufficient Permissions",
                description="This command requires administrator privileges.",
                color=COLOR_ERROR
            ))
            return
        
        await set_guild_setting(ctx.guild.id, "staff_role_id", role.id)
        await ctx.reply(embed=make_embed(
            title="✅ Staff Role Set",
            description=f"Staff role set to {role.mention}",
            color=COLOR_SUCCESS
        ))
    
    @setup.command(name="admin_role")
    async def set_admin_role(self, ctx: commands.Context, role: discord.Role):
        """Set the admin role."""
        if not await is_admin(ctx.author, ctx.guild):
            await ctx.reply(embed=make_embed(
                title="❌ Insufficient Permissions",
                description="This command requires administrator privileges.",
                color=COLOR_ERROR
            ))
            return
        
        await set_guild_setting(ctx.guild.id, "admin_role_id", role.id)
        await ctx.reply(embed=make_embed(
            title="✅ Admin Role Set",
            description=f"Admin role set to {role.mention}",
            color=COLOR_SUCCESS
        ))
    
    @setup.command(name="mod_channel")
    async def set_mod_channel(self, ctx: commands.Context, channel: discord.TextChannel):
        """Set the moderation command channel."""
        if not await is_admin(ctx.author, ctx.guild):
            await ctx.reply(embed=make_embed(
                title="❌ Insufficient Permissions",
                description="This command requires administrator privileges.",
                color=COLOR_ERROR
            ))
            return
        
        await set_guild_setting(ctx.guild.id, "mod_channel_id", channel.id)
        await ctx.reply(embed=make_embed(
            title="✅ Mod Channel Set",
            description=f"Moderation commands restricted to {channel.mention}",
            color=COLOR_SUCCESS
        ))
    
    @setup.command(name="shift_channel")
    async def set_shift_channel(self, ctx: commands.Context, channel: discord.TextChannel):
        """Set the shift command channel."""
        if not await is_admin(ctx.author, ctx.guild):
            await ctx.reply(embed=make_embed(
                title="❌ Insufficient Permissions",
                description="This command requires administrator privileges.",
                color=COLOR_ERROR
            ))
            return
        
        await set_guild_setting(ctx.guild.id, "shift_channel_id", channel.id)
        await ctx.reply(embed=make_embed(
            title="✅ Shift Channel Set",
            description=f"Shift commands restricted to {channel.mention}",
            color=COLOR_SUCCESS
        ))
    
    @setup.command(name="helper_button")
    async def set_helper_button(self, ctx: commands.Context, channel: discord.TextChannel):
        """Set the helper application button channel."""
        if not await is_admin(ctx.author, ctx.guild):
            await ctx.reply(embed=make_embed(
                title="❌ Insufficient Permissions",
                description="This command requires administrator privileges.",
                color=COLOR_ERROR
            ))
            return
        
        await set_guild_setting(ctx.guild.id, "helper_button_channel_id", channel.id)
        
        # Send the button
        view = HelperButtonView(self.bot, ctx.guild.id)
        embed = make_embed(
            title="🌙 Helper Applications",
            description="Click the button below to apply for the helper role.",
            color=STARLIGHT_BLUE
        )
        await channel.send(embed=embed, view=view)
        
        await ctx.reply(embed=make_embed(
            title="✅ Helper Button Sent",
            description=f"Helper application button sent to {channel.mention}",
            color=COLOR_SUCCESS
        ))
    
    @setup.command(name="helper_role")
    async def set_helper_role(self, ctx: commands.Context, role: discord.Role):
        """Set the helper role."""
        if not await is_admin(ctx.author, ctx.guild):
            await ctx.reply(embed=make_embed(
                title="❌ Insufficient Permissions",
                description="This command requires administrator privileges.",
                color=COLOR_ERROR
            ))
            return
        
        await set_helper_role(ctx.guild.id, role.id)
        await ctx.reply(embed=make_embed(
            title="✅ Helper Role Set",
            description=f"Helper role set to {role.mention}",
            color=COLOR_SUCCESS
        ))


async def setup(bot: commands.Bot):
    await bot.add_cog(Setup(bot))
