"""
Luna Bot Help Cog
Handles help commands and bot info.
"""

import discord
from discord.ext import commands

from helpers import (
    make_embed,
    get_embed_color,
    PaginationView,
)
from config import (
    DEEP_SPACE,
    COLOR_ERROR,
    COLOR_INFO,
    STARLIGHT_BLUE,
    COSMIC_PURPLE,
    OWNER_ID,
    PREFIX,
)


class Help(commands.Cog):
    """Help and info commands."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @commands.command()
    async def help(self, ctx: commands.Context, category: str = None):
        """Show help for commands."""
        if category:
            # Show specific category
            await self._show_category_help(ctx, category)
        else:
            # Show main help menu
            await self._show_main_help(ctx)
    
    async def _show_main_help(self, ctx: commands.Context):
        """Show main help menu with categories."""
        embed = make_embed(
            title="🌙 Luna Help",
            description="A complete, production-ready Discord bot with moderation, AI, and shift management.\n\nUse `,help <category>` to view commands in a category.",
            color=DEEP_SPACE,
            fields=[
                ("📢 Categories", "", False),
                ("`moderation`", "Warn, mute, kick, ban, timeout commands", True),
                ("`admin`", "Staff management, flagging, channel locks", True),
                ("`helpers`", "Tag system (helper+ only)", True),
                ("`utility`", "Announce, poll, define, translate, reminders", True),
                ("`ai`", "AI system with Gemini integration", True),
                ("`shifts`", "Shift management system", True),
                ("`setup`", "Bot configuration and setup", True),
                ("`hierarchy`", "Role and permission management", True),
                ("`logging`", "Event logging configuration", True),
                ("", "", False),
                ("👑 Owner Commands", "Use `,help owner` for owner-only commands", False),
                ("ℹ️ Info", "Use `,info` for bot statistics", False),
            ]
        )
        
        await ctx.reply(embed=embed)
    
    async def _show_category_help(self, ctx: commands.Context, category: str):
        """Show help for a specific category."""
        category_lower = category.lower()
        
        commands_map = {
            "moderation": {
                "title": "🛡️ Moderation Commands",
                "commands": [
                    (",warn <member> <reason>", "Warn a member"),
                    (",mute <member> <duration> <reason>", "Mute a member"),
                    (",unmute <member> [reason]", "Unmute a member"),
                    (",kick <member> [reason]", "Kick a member"),
                    (",ban <member> [reason]", "Ban a member"),
                    (",unban <user_id> [reason]", "Unban a user by ID"),
                    (",timeout <member> <duration> [reason]", "Timeout a member"),
                    (",untimeout <member> [reason]", "Remove timeout"),
                    (",wm <member> <duration> [reason]", "Warn + Mute"),
                    (",warns <member>", "View warns for a member"),
                ]
            },
            "admin": {
                "title": "👑 Admin Commands",
                "commands": [
                    (",flag <member> [reason]", "Flag a staff member"),
                    (",unflag <member> [reason]", "Clear flags for staff"),
                    (",terminate <member> [reason]", "Terminate staff member"),
                    (",stafflist", "View all staff and flag counts"),
                    (",lockchannels", "Lock categories for member role"),
                    (",unlockchannels", "Unlock categories for member role"),
                ]
            },
            "helpers": {
                "title": "❤️ Helper Commands (Helper+)",
                "commands": [
                    (",tag <category> <title>", "View a tag"),
                    (",tags [category] [search]", "Search tags"),
                    (",tag_create <cat> <title> <desc>", "Create tag (Staff+)"),
                    (",tag_edit <cat> <title> <desc>", "Edit tag (Staff+)"),
                    (",tag_delete <cat> <title>", "Delete tag (Staff+)"),
                ]
            },
            "utility": {
                "title": "🔧 Utility Commands",
                "commands": [
                    (",announce <role> <#channel> <title> <msg>", "Send announcement"),
                    (",poll <#channel> [@role] <True/False> \"title\" \"question\" \"opt1\" \"opt2\"", "Create poll"),
                    (",endpoll <message_id>", "End a poll"),
                    (",define <word>", "Define a word"),
                    (",translate <word> <from> <to>", "Translate a word"),
                    (",askai <question>", "Ask Luna AI"),
                    (",remindme <text> <duration>", "Set a reminder"),
                    (",reminders", "View your reminders"),
                    (",deleteremind <id>", "Delete a reminder"),
                ]
            },
            "ai": {
                "title": "🤖 AI Commands",
                "commands": [
                    (",aipanel", "Summon AI control panel (Owner)"),
                    (",ai_settings [setting] [value]", "View/change AI settings (Owner)"),
                    (",ai_target <@user>", "Start AI targeting (Owner)"),
                    (",ai_stop <@user>", "Stop AI targeting (Owner)"),
                ]
            },
            "shifts": {
                "title": "⏱️ Shift Commands",
                "commands": [
                    ("Staff Commands (Staff+)", "", True),
                    (",myshift", "View your shift status"),
                    (",viewshift <@user>", "View someone's shift"),
                    (",shift_lb", "Weekly leaderboard"),
                    ("", "", False),
                    ("Admin Commands (Admin)", "", True),
                    (",shift_create <type>", "Create shift type"),
                    (",shift_delete <type>", "Delete shift type"),
                    (",view_shifts", "View all shifts"),
                    (",activity_view", "Activity leaderboard"),
                    (",config_roles <role> <type>", "Link role to shift"),
                    (",config_afk <role> <type> <duration>", "Set AFK timeout"),
                    (",config_quota <role> <type> <minutes>", "Set weekly quota"),
                    (",quota_remove <role> <type> <minutes>", "Reduce quota"),
                    (",view_settings", "View shift settings"),
                    (",shift_channel <#channel>", "Set shift channel"),
                    (",reset_all", "Reset all settings"),
                ]
            },
            "setup": {
                "title": "⚙️ Setup Commands (Admin)",
                "commands": [
                    (",setup", "View configuration"),
                    (",setup prefix <prefix>", "Set prefix"),
                    (",setup modlog <#channel>", "Set modlog channel"),
                    (",setup joinleave <#channel>", "Set join/leave channel"),
                    (",setup member_role <@role>", "Set member role"),
                    (",setup staff_role <@role>", "Set staff role"),
                    (",setup admin_role <@role>", "Set admin role"),
                    (",setup mod_channel <#channel>", "Set mod channel"),
                    (",setup shift_channel <#channel>", "Set shift channel"),
                    (",setup helper_button <#channel>", "Set helper button"),
                    (",setup helper_role <@role>", "Set helper role"),
                ]
            },
            "hierarchy": {
                "title": "🔐 Hierarchy Commands (Admin)",
                "commands": [
                    (",setlockcategories <#cat1> <#cat2>", "Set lock categories"),
                    (",clearlockcategories", "Clear lock categories"),
                    (",viewlockcategories", "View lock categories"),
                    (",permissions", "View permission config"),
                ]
            },
            "logging": {
                "title": "📋 Logging Commands",
                "commands": [
                    ("Logging is automatic once configured.", "Events logged: message delete, join, leave, ban, unban", False),
                ]
            },
            "owner": {
                "title": "👑 Owner-Only Commands",
                "commands": [
                    (",commands", "List all commands"),
                    (",status <status>", "Set bot status"),
                    (",servers", "List all servers"),
                    (",leaveserver <id>", "Leave a server"),
                    (",blacklist <user> [reason]", "Blacklist a user"),
                    (",unblacklist <user>", "Remove from blacklist"),
                    (",reload <cog>", "Reload a cog"),
                    (",load <cog>", "Load a cog"),
                    (",unload <cog>", "Unload a cog"),
                    (",extract_dms <@user>", "Extract DM conversation"),
                ]
            },
        }
        
        if category_lower not in commands_map:
            await ctx.reply(embed=make_embed(
                title="❌ Category Not Found",
                description=f"Category `{category}` not found.\n\nUse `,help` to see all categories.",
                color=COLOR_ERROR
            ))
            return
        
        info = commands_map[category_lower]
        
        # Build embed fields
        fields = []
        for command, description in info['commands']:
            if command == "":
                fields.append(("", description, False))
            elif description == "":
                fields.append((command, "", False))
            else:
                fields.append((f"`{command}`", description, True))
        
        embed = make_embed(
            title=info['title'],
            color=COLOR_INFO,
            fields=fields[:25]  # Discord limit
        )
        
        await ctx.reply(embed=embed)
    
    @commands.command(name="help_all")
    async def help_all(self, ctx: commands.Context):
        """
        Show all commands in detail.
        OWNER ONLY.
        """
        if ctx.author.id != OWNER_ID:
            await ctx.reply(embed=make_embed(
                title="❌ Owner Only",
                description="This command is restricted to the bot owner.",
                color=COLOR_ERROR
            ))
            return
        
        # Create detailed command list
        categories = [
            ("Moderation", [c for c in self.bot.cogs.values() if isinstance(c, self.bot.get_cog("Moderation").__class__)]),
            ("Admin", [c for c in self.bot.cogs.values() if isinstance(c, self.bot.get_cog("Admin").__class__)]),
            ("Helpers", [c for c in self.bot.cogs.values() if isinstance(c, self.bot.get_cog("Helpers").__class__)]),
            ("Utility", [c for c in self.bot.cogs.values() if isinstance(c, self.bot.get_cog("Utility").__class__)]),
            ("AI", [c for c in self.bot.cogs.values() if isinstance(c, self.bot.get_cog("AI").__class__)]),
            ("Shifts", [c for c in self.bot.cogs.values() if isinstance(c, self.bot.get_cog("Shifts").__class__)]),
            ("Setup", [c for c in self.bot.cogs.values() if isinstance(c, self.bot.get_cog("Setup").__class__)]),
            ("Hierarchy", [c for c in self.bot.cogs.values() if isinstance(c, self.bot.get_cog("Hierarchy").__class__)]),
            ("Owner", [c for c in self.bot.cogs.values() if isinstance(c, self.bot.get_cog("Owner").__class__)]),
        ]
        
        # Create pagination
        def create_embed(items, page, total_pages):
            embed = make_embed(
                title=f"📋 All Commands (Page {page + 1}/{total_pages})",
                color=DEEP_SPACE
            )
            
            # Get all commands
            all_commands = []
            for cog_name, cogs in items:
                for cog in cogs:
                    for command in cog.get_commands():
                        if not command.hidden:
                            all_commands.append(f"• {PREFIX}{command.name}{command.signature} - {command.help or 'No description'}")
            
            # Show subset for this page
            start = page * 20
            end = start + 20
            for cmd in all_commands[start:end]:
                parts = cmd.split(" - ", 1)
                embed.add_field(name=parts[0], value=parts[1] if len(parts) > 1 else "", inline=False)
            
            return embed
        
        # Flatten categories for pagination
        flat_items = [(cat, cogs) for cat, cogs in categories for _ in range(1)]
        
        view = PaginationView(flat_items, create_embed)
        embed = create_embed(view.get_current_items(), 0, view.total_pages)
        await ctx.send(embed=embed, view=view)
    
    @commands.command()
    async def info(self, ctx: commands.Context):
        """Show bot statistics and information."""
        guild_count = len(self.bot.guilds)
        member_count = sum(g.member_count for g in self.bot.guilds)
        
        # Get shift stats
        from database import get_weekly_leaderboard
        weekly_hours = 0
        try:
            leaderboard = await get_weekly_leaderboard(ctx.guild.id) if ctx.guild else []
            weekly_hours = sum(entry['total_seconds'] / 3600 for entry in leaderboard)
        except:
            pass
        
        embed = make_embed(
            title="🌙 Luna Bot Information",
            color=STARLIGHT_BLUE,
            fields=[
                ("Version", "1.0.0", True),
                ("Servers", str(guild_count), True),
                ("Total Members", str(member_count), True),
                ("Ping", f"{round(self.bot.latency * 1000)}ms", True),
                ("Owner", f"<@{OWNER_ID}>", True),
                ("Prefix", f"`{PREFIX}`", True),
            ]
        )
        
        if ctx.guild:
            embed.add_field(name="Weekly Shift Hours", value=f"{weekly_hours:.2f}h", inline=False)
        
        await ctx.reply(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Help(bot))
