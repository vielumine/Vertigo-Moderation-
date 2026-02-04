# 🌙 Luna Discord Bot

A complete, production-ready Discord bot with advanced moderation, AI integration, and shift management system.

## Features

### 🛡️ Moderation
- Warn, mute, kick, ban commands
- Timeout support
- Warn+Mute (wm) combined command
- Staff immunity system
- Undo support for many actions

### 👑 Admin
- Staff flagging system (5-strike termination)
- Channel lockdowns (lock/unlock categories)
- Staff list with flag counts
- Auto-termination at 5 strikes

### ❤️ Helper System
- Tag system with categories
- Helper application button
- Tag creation/editing/deletion (staff only)
- Tag viewing and search (helper+ only)

### 🔧 Utility
- Styled announcements
- Poll creation with buttons
- Word definition (Dictionary API)
- Translation (LibreTranslate API)
- Reminders system
- AI questions (Gemini integration)

### 🤖 AI System
- Gemini AI integration
- AI control panel with toggle buttons
- AI targeting system (owner fun)
- DM responses when enabled
- Multiple personalities (helpful, sarcastic, genz, professional)

### ⏱️ Shift Management
- Real-time shift tracking with GMT+8 calculations
- Break/pause/resume functionality
- AFK detection and auto-pause/end
- Weekly leaderboards
- Quota tracking per role/shift type
- Activity monitoring
- Custom shift types and configurations

### ⚙️ Configuration
- Custom prefix per server
- Helper role setup with application modal
- Lockable categories for lockdowns
- Role-based shift configuration
- Modular command restrictions

### 📋 Logging
- Message delete logging
- Member join/leave logging
- Ban/unban logging
- Webhook support for remote logging

## Setup

### 1. Prerequisites
- Python 3.10 or higher
- A Discord bot token
- A Gemini API key
- Owner Discord user ID

### 2. Installation

```bash
# Clone or download the bot
cd luna

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your values
nano .env  # Or use your preferred editor
```

Required variables:
- `DISCORD_TOKEN`: Your Discord bot token
- `OWNER_ID`: Your Discord user ID (numeric)
- `GEMINI_API_KEY`: Your Google Gemini API key

Optional:
- `WEBHOOK_MODLOG`: Discord webhook URL for mod logs
- `WEBHOOK_JOIN_LEAVE`: Discord webhook URL for join/leave events

### 4. Running the Bot

```bash
python app.py
```

For HiddenCloud hosting:
- Use `app.py` as the entrypoint (not main.py)

## Initial Setup

Once the bot is running and in your server:

1. **Set up basic configuration:**
   ```
   ,setup prefix !
   ,setup member_role @Member
   ,setup staff_role @Staff
   ,setup admin_role @Admin
   ```

2. **Set up channels:**
   ```
   ,setup modlog #modlog
   ,setup mod_channel #mod-commands
   ,setup shift_channel #shifts
   ,setup helper_button #helper-applications
   ,setup helper_role @Helper
   ```

3. **Configure lock categories (for lockdowns):**
   ```
   ,setlockcategories #general #media #games
   ```

4. **Set up shifts:**
   ```
   ,config_roles @Staff regular
   ,config_afk @Staff regular 5m
   ,config_quota @Staff regular 600
   ```

## Commands

### Help
- `,help` - Show help menu with categories
- `,help <category>` - Show commands for a category
- `,info` - Show bot statistics

### Moderation (Staff)
- `,warn <member> <reason>` - Warn a member
- `,mute <member> <duration> <reason>` - Mute a member
- `,unmute <member> [reason]` - Unmute a member
- `,kick <member> [reason]` - Kick a member
- `,ban <member> [reason]` - Ban a member
- `,unban <user_id> [reason]` - Unban a user
- `,timeout <member> <duration> [reason]` - Timeout a member
- `,untimeout <member> [reason]` - Remove timeout
- `,wm <member> <duration> [reason]` - Warn + Mute
- `,warns <member>` - View warns for a member

### Admin
- `,flag <member> [reason]` - Flag a staff member
- `,unflag <member> [reason]` - Clear flags for staff
- `,terminate <member> [reason]` - Terminate staff member
- `,stafflist` - View all staff and flag counts
- `,lockchannels` - Lock categories for member role
- `,unlockchannels` - Unlock categories for member role

### Helpers (Helper+)
- `,tag <category> <title>` - View a tag
- `,tags [category] [search]` - Search tags
- `,tag_create <cat> <title> <desc>` - Create tag (Staff+)
- `,tag_edit <cat> <title> <desc>` - Edit tag (Staff+)
- `,tag_delete <cat> <title>` - Delete tag (Staff+)

### Utility
- `,announce <role> <#channel> <title> <msg>` - Send announcement (Admin)
- `,poll <#channel> [@role] <True/False> "title" "question" "opt1" "opt2"` - Create poll (Admin)
- `,endpoll <message_id>` - End a poll (Admin)
- `,define <word>` - Define a word
- `,translate <word> <from> <to>` - Translate a word
- `,askai <question>` - Ask Luna AI
- `,remindme <text> <duration>` - Set a reminder
- `,reminders` - View your reminders
- `,deleteremind <id>` - Delete a reminder

### AI
- `,aipanel` - Summon AI control panel (Owner)
- `,ai_settings [setting] [value]` - View/change AI settings (Owner)
- `,ai_target <@user>` - Start AI targeting (Owner)
- `,ai_stop <@user>` - Stop AI targeting (Owner)

### Shifts
**Staff Commands (Staff+):**
- `,myshift` - View your shift status
- `,viewshift <@user>` - View someone's shift
- `,shift_lb` - Weekly leaderboard

**Admin Commands (Admin):**
- `,shift_create <type>` - Create shift type
- `,shift_delete <type>` - Delete shift type
- `,view_shifts` - View all shifts
- `,activity_view` - Activity leaderboard
- `,config_roles <@role> <type>` - Link role to shift
- `,config_afk <@role> <type> <duration>` - Set AFK timeout
- `,config_quota <@role> <type> <minutes>` - Set weekly quota
- `,quota_remove <@role> <type> <minutes>` - Reduce quota
- `,view_settings` - View shift settings
- `,shift_channel <#channel>` - Set shift channel
- `,reset_all` - Reset all settings

### Setup (Admin)
- `,setup` - View configuration
- `,setup prefix <prefix>` - Set prefix
- `,setup modlog <#channel>` - Set modlog channel
- `,setup joinleave <#channel>` - Set join/leave channel
- `,setup member_role <@role>` - Set member role
- `,setup staff_role <@role>` - Set staff role
- `,setup admin_role <@role>` - Set admin role
- `,setup mod_channel <#channel>` - Set mod channel
- `,setup shift_channel <#channel>` - Set shift channel
- `,setup helper_button <#channel>` - Set helper button
- `,setup helper_role <@role>` - Set helper role

### Hierarchy (Admin)
- `,setlockcategories <#cat1> <#cat2>` - Set lock categories
- `,clearlockcategories` - Clear lock categories
- `,viewlockcategories` - View lock categories
- `,permissions` - View permission configuration

### Owner-Only Commands
- `,help_all` - Show all commands in detail
- `,commands` - List all commands
- `,status <status>` - Set bot status
- `,servers` - List all servers
- `,leaveserver <id>` - Leave a server
- `,blacklist <user> [reason]` - Blacklist a user
- `,unblacklist <user>` - Remove from blacklist
- `,reload <cog>` - Reload a cog
- `,load <cog>` - Load a cog
- `,unload <cog>` - Unload a cog
- `,extract_dms <@user>` - Extract DM conversation

## Duration Format

All duration parameters use the following format:
- `1h` = 1 hour
- `30m` = 30 minutes
- `1d` = 1 day
- `1w` = 1 week
- `1mo` = 1 month (30 days)
- `1y` = 1 year

Combine as needed: `1h30m`, `2d6h`, etc.

## Permission System

- **Owner**: Full access to all commands
- **Admin**: Can use admin, setup, hierarchy, moderation, and shift admin commands
- **Staff**: Can use moderation, shift staff, and helper tag commands
- **Helper**: Can only use `,tag` and `,tags` commands to view tags
- **Member**: Can use utility commands (define, translate, askai, reminders)

## Theme & Design

Luna uses a lunar-inspired color palette:
- **Deep Space (#02040B)**: Main background
- **Starlight Blue (#7FA9FF)**: Primary accent
- **Cosmic Purple (#1B1431)**: Secondary accent
- **Midnight Navy (#0D1321)**: Alternative background

The bot features a strict, professional tone with formal language.

## AI Integration

Luna uses Google's Gemini AI for:
- Direct questions (`,askai`)
- Bot mention responses
- DM responses (when enabled)
- AI targeting roasts

Available personalities:
- `helpful`: Friendly and direct
- `sarcastic`: Witty and humorous
- `genz`: Casual with slang
- `professional`: Formal and precise

## Shift System (GMT+8)

The shift management system uses GMT+8 timezone for all calculations:
- Shift start/end timestamps
- Duration calculations
- Weekly quota resets (Monday GMT+8)

Features:
- Real-time tracking
- Break/pause/resume
- AFK detection (auto-pause after timeout)
- Auto-end after 2x AFK timeout
- Weekly leaderboards
- Per-role quotas
- Multiple shift types

## Troubleshooting

### Bot not responding
- Check bot has required permissions
- Verify bot token is correct
- Check `.env` file is properly configured

### Commands not working
- Check you have required permissions
- Verify command is used in correct channel (e.g., mod commands in mod channel)
- Check guild is properly configured (`,setup`)

### Shift system issues
- Ensure shift channel is configured
- Check roles are linked to shift types
- Verify user has correct role
- Check database connection

### AI not responding
- Verify `GEMINI_API_KEY` is set correctly
- Check AI is enabled in settings (`,ai_settings`)
- Verify API key has quota remaining

## Development

### Testing AI Connection
```bash
python test_ai.py
```

### Database Structure
The bot uses SQLite with the following tables:
- `guild_settings` - Server configurations
- `ai_settings` - AI configuration per server
- `helper_role` - Helper role assignments
- `mutes`, `warns`, `bans` - Moderation records
- `staff_flags` - Staff flagging system
- `tags` - Tag system
- `reminders` - User reminders
- `dm_logs` - DM conversation logs
- `blacklist` - User blacklists
- `polls` - Poll data
- `shifts` - Shift records
- `shift_configs` - Shift configurations
- `quota_tracking` - Weekly quota data
- `ai_targets` - AI targeting data
- `activity_logs` - User activity for AFK tracking

## Support

For issues, questions, or feature requests:
- Check the README for common issues
- Review command usage with `,help`
- Contact bot owner for advanced issues

## License

This bot is provided as-is for educational and personal use.

---

**Luna Bot v1.0.0** - A complete, production-ready Discord moderation bot.
