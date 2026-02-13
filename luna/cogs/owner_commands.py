"""Owner Commands - Complete command overview for bot owner."""

from __future__ import annotations

import logging

import discord
from discord.ext import commands

import config
from helpers import Page, PaginationView, make_embed, require_owner

logger = logging.getLogger(__name__)


def _chunk_commands(commands: list[str], size: int) -> list[list[str]]:
    return [commands[i : i + size] for i in range(0, len(commands), size)]


def _build_help_all_pages(prefix: str) -> list[Page]:
    sections: list[tuple[str, list[str]]] = [
        (
            "👑 Owner Commands",
            [
                "commands",
                "guilds",
                "dmuser <user> <message>",
                "waketime",
                "banguild <guild_id> [reason]",
                "unbanguild <guild_id>",
                "checkguild <guild_id>",
                "guildlist",
                "nuke [channel]",
                "extract_dms <user> [limit]",
            ],
        ),
        (
            "🤖 AI Targeting Commands",
            [
                "ai_target <user> [notes]",
                "ai_stop <user>",
            ],
        ),
        (
            "🧠 AI Moderation Commands",
            [
                "aiwarn <user> [channel] <reason>",
                "aidelwarn <user> <warn_id> [channel]",
                "aiwarnings <user>",
                "aimodlogs <user>",
                "aimute <user> <duration> [channel] <reason>",
                "aiunmute <user> [channel] [reason]",
                "aikick <user> <reason>",
                "aiban <user> <reason>",
                "aiunban <user> <reason>",
                "aiwm <user> <duration> [channel] <reason>",
                "aimasskick <users,users> <reason>",
                "aimassban <users,users> <reason>",
                "aimassmute <users,users> <duration> <reason>",
                "aiimprison <user> <reason>",
                "airelease <user> [reason]",
                "aiflag <staff_user> <reason>",
                "aitarget <user> [notes]",
                "airemove <user>",
                "blacklist <user> <reason>",
                "unblacklist <user>",
                "seeblacklist",
                "timeoutpanel",
            ],
        ),
        (
            "⚠️ Moderation Commands",
            [
                "warn <user> <reason>",
                "delwarn <user> <warn_id>",
                "warnings <user>",
                "modlogs <user>",
                "mute <user> <duration> [reason]",
                "unmute <user> [reason]",
                "kick <user> <reason>",
                "ban <user> <reason>",
                "unban <user> <reason>",
                "wm <user> <duration> <reason>",
                "wmr <duration> <reason>",
                "masskick <users,users> <reason>",
                "massban <users,users> <reason>",
                "massmute <users,users> <duration> <reason>",
                "imprison <user> <reason>",
                "release <user> [reason]",
            ],
        ),
        (
            "📌 Role Commands",
            [
                "role <user> <role>",
                "removerole <user> <role>",
                "temprole <user> <role> <duration>",
                "removetemp <user> <role>",
                "persistrole <user> <role>",
                "removepersist <user> <role>",
                "massrole <users,users> <role>",
                "massremoverole <users,users> <role>",
                "masstemprole <users,users> <role> <duration>",
                "massremovetemp <users,users> <role>",
                "masspersistrole <users,users> <role>",
                "massremovepersist <users,users> <role>",
            ],
        ),
        (
            "⏱️ Channel Commands",
            [
                "checkslowmode [channel]",
                "setslowmode [channel] <duration>",
                "massslow <channels,channels> <duration>",
                "lock [channel]",
                "unlock [channel]",
                "hide [channel]",
                "unhide [channel]",
                "message <channel> <message>",
                "editmess <message_id> <new_message>",
                "replymess <message_id> <reply>",
                "deletemess <message_id>",
                "reactmess <message_id> <emoji>",
            ],
        ),
        (
            "🧹 Cleaning Commands",
            [
                "clean [amount]",
                "purge <amount>",
                "purgeuser <user> <amount>",
                "purgematch <keyword> <amount>",
            ],
        ),
        (
            "👤 Member Commands",
            [
                "mywarns",
                "myavatar",
                "mybanner",
                "myinfo",
            ],
        ),
        (
            "📋 Miscellaneous Commands",
            [
                "help",
                "adcmd",
                "userinfo <user>",
                "serverinfo",
                "botinfo",
                "checkavatar <user>",
                "checkbanner <user>",
                "members",
                "ping",
                "wasbanned <user>",
                "checkdur <user>",
                "changenick <user> <nickname>",
                "removenick <user>",
                "roleperms <role>",
            ],
        ),
        (
            "🤖 AI Chat Commands",
            [
                "ai <question>",
            ],
        ),
        (
            "🛠️ Utility Commands",
            [
                "announce <channel> <message>",
                "poll <question>",
                "define <word>",
                "askai <question>",
                "remindme <duration> <text>",
                "reminders",
                "deleteremind <id>",
            ],
        ),
        (
            "🕒 Shift Commands",
            [
                "clockin [helper|staff]",
                "clockout [break_minutes]",
                "myshifts [limit]",
                "shiftquota",
                "shiftleaderboard [helper|staff|all]",
                "shiftconfig <role> <type> <afk_timeout> <weekly_quota>",
            ],
        ),
        (
            "📊 Stats Commands",
            [
                "ms [user]",
                "staffstats",
                "set_ms [user]",
                "refresh",
            ],
        ),
        (
            "🏷️ Tag Commands",
            [
                "tag <category> <title>",
                "tags [category]",
                "tag_create <category> <title> <description>",
                "tag_edit <category> <title> <description>",
                "tag_delete <category> <title>",
            ],
        ),
        (
            "📬 Notification Commands",
            [
                "dmnotify status",
                "dmnotify enable",
                "dmnotify disable",
                "dmnotify toggle <type>",
                "dmnotify test [member]",
                "optout",
                "optin",
            ],
        ),
        (
            "🧭 Setup Commands",
            [
                "setup",
                "adminsetup",
            ],
        ),
        (
            "🏛️ Admin Commands",
            [
                "flag <staff_user> <reason>",
                "unflag <staff_user> <strike_id>",
                "terminate <staff_user> [reason]",
                "lockchannels",
                "unlockchannels",
                "scanacc <user>",
                "stafflist",
                "wasstaff <user>",
            ],
        ),
        (
            "📊 Hierarchy Commands",
            [
                "hierarchy",
                "promote <staff>",
                "demote <staff>",
            ],
        ),
        (
            "📈 Promotion Commands",
            [
                "promotion list",
                "promotion review <id> <approve/deny>",
                "promotion analyze <member>",
                "promotion stats <member>",
            ],
        ),
    ]

    pages: list[Page] = []
    for title, commands_list in sections:
        chunks = _chunk_commands(commands_list, 8)
        for chunk_index, chunk in enumerate(chunks, start=1):
            suffix = f" ({chunk_index}/{len(chunks)})" if len(chunks) > 1 else ""
            description = "\n".join(f"`{prefix}{command}`" for command in chunk)
            embed = make_embed(action="owner", title=f"{title}{suffix}", description=description)
            pages.append(Page(embed=embed))

    total_pages = len(pages)
    for index, page in enumerate(pages, start=1):
        page.embed.set_footer(text=f"{config.BOT_NAME} • Page {index}/{total_pages}")

    return pages


class OwnerCommandsCog(commands.Cog):
    """Owner-only commands for complete bot management."""
    
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
    
    @commands.command(name="commands", aliases=["cmd", "help_all"])
    @require_owner()
    async def show_all_commands(self, ctx: commands.Context) -> None:
        """Show all available commands organized by category."""
        try:
            prefix = ctx.prefix or config.DEFAULT_PREFIX
            pages = _build_help_all_pages(prefix)
            view = PaginationView(pages=pages, author_id=ctx.author.id)
            await ctx.send(embed=pages[0].embed, view=view)
        except Exception as e:
            logger.error("Commands list error: %s", e)
            embed = make_embed(
                action="error",
                title="Error",
                description="Failed to load command list."
            )
            await ctx.send(embed=embed)
    
    @commands.command(name="guilds")
    @require_owner()
    async def guilds(self, ctx: commands.Context) -> None:
        """List all guilds the bot is in."""
        try:
            if not self.bot.guilds:
                embed = make_embed(
                    action="owner",
                    title="🌐 Connected Guilds",
                    description="Bot is not connected to any guilds."
                )
                await ctx.send(embed=embed)
                return
            
            embed = make_embed(
                action="owner",
                title="🌐 Connected Guilds",
                description=f"Bot is connected to {len(self.bot.guilds)} guilds:"
            )
            
            for guild in self.bot.guilds:
                member_count = guild.member_count if guild.member_count else "Unknown"
                embed.add_field(
                    name=guild.name,
                    value=(
                        f"**ID:** `{guild.id}`\n"
                        f"**Members:** {member_count}\n"
                        f"**Owner:** <@{guild.owner_id}>\n"
                        f"**Created:** {guild.created_at.strftime('%Y-%m-%d')}\n"
                        f"**Joined:** {guild.me.joined_at.strftime('%Y-%m-%d') if guild.me.joined_at else 'Unknown'}"
                    ),
                    inline=True
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error("Guilds list error: %s", e)
            embed = make_embed(
                action="error",
                title="Error",
                description="Failed to load guild list."
            )
            await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    """Load the owner commands cog."""
    await bot.add_cog(OwnerCommandsCog(bot))