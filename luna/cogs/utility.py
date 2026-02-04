"""
Luna Bot Utility Cog
Handles utility commands: announce, poll, define, translate, askai, reminders.
"""

import discord
from discord.ext import commands
import aiohttp
import json

from database import (
    create_reminder,
    get_user_reminders,
    delete_reminder,
    get_guild_setting,
)
from helpers import (
    make_embed,
    get_embed_color,
    parse_duration,
    format_seconds,
    get_gemini_response,
    PaginationView,
    utcnow,
    is_admin,
)
from config import (
    DEEP_SPACE,
    COLOR_ERROR,
    COLOR_SUCCESS,
    COLOR_INFO,
    COLOR_WARNING,
)


class PollView(discord.ui.View):
    """View for poll voting."""
    
    def __init__(self, poll_id: int):
        super().__init__(timeout=None)
        self.poll_id = poll_id
    
    @discord.ui.button(label="Option 1", style=discord.ButtonStyle.primary, custom_id="poll_1")
    async def option_1(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("You voted for Option 1!", ephemeral=True)
    
    @discord.ui.button(label="Option 2", style=discord.ButtonStyle.primary, custom_id="poll_2")
    async def option_2(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("You voted for Option 2!", ephemeral=True)
    
    @discord.ui.button(label="Option 3", style=discord.ButtonStyle.primary, custom_id="poll_3")
    async def option_3(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("You voted for Option 3!", ephemeral=True)


class Utility(commands.Cog):
    """Utility commands."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def announce(self, ctx: commands.Context, role: discord.Role, channel: discord.TextChannel, title: str, *, message: str):
        """Send a styled announcement."""
        embed = make_embed(
            title=f"📢 {title}",
            description=message,
            color=get_embed_color("announce"),
            author={"name": ctx.author.display_name, "icon_url": ctx.author.display_avatar.url}
        )
        
        await channel.send(content=role.mention, embed=embed)
        
        await ctx.reply(embed=make_embed(
            title="✅ Announcement Sent",
            description=f"Announcement sent to {channel.mention} with {role.mention}.",
            color=COLOR_SUCCESS
        ))
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def poll(self, ctx: commands.Context, channel: discord.TextChannel, role: Optional[discord.Role] = None, ping: bool = False, title: str = None, *, question: str = None):
        """
        Create a poll with buttons.
        Usage: `,poll #channel @role True/False "Title" "Question" "Option1" "Option2" ...`
        """
        # This is a simplified poll command
        if not title or not question:
            await ctx.reply(embed=make_embed(
                title="❌ Invalid Usage",
                description="Usage: `,poll #channel [@role] [True/False] \"Title\" \"Question\" \"Option1\" \"Option2\" ...`",
                color=COLOR_ERROR
            ))
            return
        
        embed = make_embed(
            title=f"📊 {title}",
            description=f"**Question:** {question}\n\nReact with your choice below!",
            color=get_embed_color("poll")
        )
        
        msg = await channel.send(
            content=f"{role.mention if role and ping else ''}",
            embed=embed
        )
        
        # Add reaction options
        reactions = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
        for reaction in reactions[:3]:
            await msg.add_reaction(reaction)
        
        await ctx.reply(embed=make_embed(
            title="✅ Poll Created",
            description=f"Poll sent to {channel.mention}.",
            color=COLOR_SUCCESS
        ))
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def endpoll(self, ctx: commands.Context, message_id: int):
        """End a poll and show results."""
        try:
            channel = ctx.channel
            message = await channel.fetch_message(message_id)
            
            # Count reactions
            counts = {}
            for reaction in message.reactions:
                if str(reaction.emoji) in ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]:
                    counts[str(reaction.emoji)] = reaction.count - 1  # Subtract bot's reaction
            
            # Build results
            results_text = "\n".join([f"{emoji}: {count} votes" for emoji, count in counts.items()])
            
            embed = make_embed(
                title="📊 Poll Results",
                description=f"**Original Question:** {message.embeds[0].description if message.embeds else 'Unknown'}\n\n{results_text}",
                color=get_embed_color("endpoll")
            )
            
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.reply(embed=make_embed(
                title="❌ Error",
                description=f"Could not fetch poll: {str(e)}",
                color=COLOR_ERROR
            ))
    
    @commands.command()
    async def define(self, ctx: commands.Context, *, word: str):
        """Define a word using a dictionary API."""
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}") as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data:
                            entry = data[0]
                            word_info = entry.get('word', word)
                            meanings = entry.get('meanings', [])
                            
                            if meanings:
                                first_meaning = meanings[0]
                                definition = first_meaning.get('definitions', [{}])[0].get('definition', 'No definition found.')
                                part_of_speech = first_meaning.get('partOfSpeech', 'Unknown')
                                
                                embed = make_embed(
                                    title=f"📖 {word_info.capitalize()}",
                                    description=f"**Part of Speech:** {part_of_speech}\n**Definition:** {definition}",
                                    color=get_embed_color("define")
                                )
                                await ctx.reply(embed=embed)
                            else:
                                await ctx.reply(embed=make_embed(
                                    title="❌ No Definition Found",
                                    description=f"No definition found for `{word}`.",
                                    color=COLOR_ERROR
                                ))
                        else:
                            await ctx.reply(embed=make_embed(
                                title="❌ No Definition Found",
                                description=f"No definition found for `{word}`.",
                                color=COLOR_ERROR
                            ))
                    else:
                        await ctx.reply(embed=make_embed(
                            title="❌ API Error",
                            description=f"Dictionary API returned status {response.status}.",
                            color=COLOR_ERROR
                        ))
            except Exception as e:
                await ctx.reply(embed=make_embed(
                    title="❌ Error",
                    description=f"Error fetching definition: {str(e)}",
                    color=COLOR_ERROR
                ))
    
    @commands.command()
    async def translate(self, ctx: commands.Context, word: str, lang_from: str, lang_to: str):
        """
        Translate a word between languages.
        Languages: en (English), es (Spanish), fr (French), de (German), it (Italian), etc.
        """
        # Using LibreTranslate API (free, no key required for basic usage)
        async with aiohttp.ClientSession() as session:
            try:
                url = "https://libretranslate.com/translate"
                data = {
                    "q": word,
                    "source": lang_from.lower(),
                    "target": lang_to.lower(),
                    "format": "text"
                }
                
                async with session.post(url, json=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        translated_text = result.get('translatedText', word)
                        
                        embed = make_embed(
                            title="🌐 Translation",
                            fields=[
                                ("Original", word, True),
                                ("Translated", translated_text, True),
                                ("From", lang_from.upper(), True),
                                ("To", lang_to.upper(), True),
                            ],
                            color=get_embed_color("translate")
                        )
                        await ctx.reply(embed=embed)
                    else:
                        await ctx.reply(embed=make_embed(
                            title="❌ Translation Error",
                            description=f"Translation API returned status {response.status}.",
                            color=COLOR_ERROR
                        ))
            except Exception as e:
                await ctx.reply(embed=make_embed(
                    title="❌ Error",
                    description=f"Error translating word: {str(e)}",
                    color=COLOR_ERROR
                ))
    
    @commands.command()
    async def askai(self, ctx: commands.Context, *, question: str):
        """Ask Luna AI a question."""
        # Get AI settings
        ai_enabled = await get_guild_setting(ctx.guild.id, "ai_enabled") if ctx.guild else 1
        if not ai_enabled:
            await ctx.reply(embed=make_embed(
                title="❌ AI Disabled",
                description="AI responses are currently disabled in this server.",
                color=COLOR_ERROR
            ))
            return
        
        # Get AI personality
        personality = await get_guild_setting(ctx.guild.id, "personality") if ctx.guild else "helpful"
        
        # Send typing indicator
        async with ctx.typing():
            response = await get_gemini_response(question, personality)
        
        embed = make_embed(
            title=f"🌙 Luna AI",
            description=response,
            color=get_embed_color("askai"),
            author={"name": ctx.author.display_name, "icon_url": ctx.author.display_avatar.url}
        )
        
        await ctx.reply(embed=embed)
    
    @commands.command()
    async def remindme(self, ctx: commands.Context, reminder_text: str, duration: str):
        """Set a reminder for yourself."""
        # Parse duration
        duration_seconds = parse_duration(duration)
        if not duration_seconds:
            await ctx.reply(embed=make_embed(
                title="❌ Invalid Duration",
                description="Duration format: `1h`, `30m`, `1d`, `1w`",
                color=COLOR_ERROR
            ))
            return
        
        expires_at = utcnow() + duration_seconds
        
        # Create reminder
        reminder_id = await create_reminder(ctx.author.id, ctx.guild.id if ctx.guild else 0, reminder_text, expires_at)
        
        await ctx.reply(embed=make_embed(
            title="✅ Reminder Set",
            description=f"I'll remind you: `{reminder_text}`\n**In:** {format_seconds(duration_seconds)}\n**At:** <t:{expires_at}:F>\n**Reminder ID:** {reminder_id}",
            color=get_embed_color("remindme")
        ))
    
    @commands.command()
    async def reminders(self, ctx: commands.Context):
        """View your active reminders."""
        reminders = await get_user_reminders(ctx.author.id)
        
        if not reminders:
            await ctx.reply(embed=make_embed(
                title="📋 Your Reminders",
                description="You have no active reminders.",
                color=COLOR_INFO
            ))
            return
        
        fields = []
        for reminder in reminders:
            fields.append((
                f"ID: {reminder['id']} - <t:{reminder['expires_at']}:R>",
                reminder['reminder_text'][:100],
                False
            ))
        
        embed = make_embed(
            title=f"📋 Your Reminders ({len(reminders)})",
            color=get_embed_color("reminders"),
            fields=fields[:25]  # Discord limit
        )
        
        await ctx.reply(embed=embed)
    
    @commands.command()
    async def deleteremind(self, ctx: commands.Context, reminder_id: int):
        """Delete a reminder by ID."""
        success = await delete_reminder(reminder_id, ctx.author.id)
        
        if success:
            await ctx.reply(embed=make_embed(
                title="✅ Reminder Deleted",
                description=f"Reminder ID {reminder_id} has been deleted.",
                color=get_embed_color("deleteremind")
            ))
        else:
            await ctx.reply(embed=make_embed(
                title="❌ Reminder Not Found",
                description=f"You don't have a reminder with ID {reminder_id}.",
                color=COLOR_ERROR
            ))


async def setup(bot: commands.Bot):
    await bot.add_cog(Utility(bot))
