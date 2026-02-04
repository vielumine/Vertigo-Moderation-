# Luna Bot - Quick Start Guide

## Installation

### 1. Install Dependencies
```bash
cd luna
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your settings
```

**Required Environment Variables:**
- `DISCORD_TOKEN` - Your Discord bot token
- `OWNER_ID` - Your Discord user ID
- `GEMINI_API_KEY` - Google Gemini API key

### 3. Test Gemini AI (Optional)
```bash
python test_ai.py
```

### 4. Run Luna
```bash
python app.py
```

## Initial Server Setup

### 1. Basic Setup (Required)
```
,setup
```
This will open a modal to configure:
- Member role
- Staff roles
- Warning duration
- Modlog channel
- Command prefix

### 2. Admin Setup (Optional)
```
,adminsetup
```
Configure advanced settings:
- Flag duration
- Lock categories
- Admin roles

## Core Features

### Moderation
- `,warn @user reason` - Warn a user
- `,mute @user duration reason` - Mute a user
- `,kick @user reason` - Kick a user
- `,ban @user reason` - Ban a user
- `,wm @user duration reason` - Warn + mute combo

### Tags System (Helper+)
- `,tag category title` - View a tag
- `,tags [category]` - List all tags
- `,tag_create category title description` - Create tag (Staff+)
- `,tag_edit category title description` - Edit tag (Staff+)
- `,tag_delete category title` - Delete tag (Staff+)

### Shift Management (Staff+, GMT+8)
- `,clockin [helper|staff]` - Start shift
- `,clockout [break_minutes]` - End shift
- `,myshifts` - View recent shifts
- `,shiftquota` - Check weekly quota

### Utility Commands
- `,announce #channel message` - Send announcement (Admin)
- `,poll question` - Create yes/no poll (Staff+)
- `,askai question` - Ask Luna AI
- `,define word` - Get word definition
- `,translate language text` - Translate text
- `,remindme 1h task` - Set reminder

### AI Features
- Mention Luna: `@Luna question` - Get AI response
- `,ai question` - Direct AI query
- `,aipanel` - Toggle AI settings (Owner)

### Owner Commands
- `,help_all` - View all commands (Owner only)
- `,ai_target @user` - Enable AI roasting (Owner only)
- `,ai_stop @user` - Stop AI targeting (Owner only)
- `,extract_dms @user` - Extract DM history (Owner only)

## Permissions Hierarchy

1. **Owner** - Full access, AI targeting, DM extraction
2. **Admin** - Configuration, announcements, shift config
3. **Staff+** - Moderation, tag management, shifts
4. **Helper** - Tag viewing only
5. **Members** - Basic commands, AI queries

## Stats Dashboard

Luna automatically updates a stats dashboard from an external API:
- Updates every 5 minutes
- Shows daily/weekly/monthly execution counts
- Auto-renames channel with total count
- Manual refresh with `,refresh` (Admin only)

**Configure in .env:**
```
TARGET_CHANNEL_ID=your_channel_id
API_URL=https://halal-worker.vvladut245.workers.dev/
```

## Troubleshooting

### Bot won't start
- Check DISCORD_TOKEN in .env
- Verify bot has required intents enabled in Discord Developer Portal
- Check logs for errors

### AI not working
- Verify GEMINI_API_KEY is set correctly
- Test with `python test_ai.py`
- Check Gemini API quota and status

### Stats dashboard not updating
- Verify TARGET_CHANNEL_ID is correct
- Check API_URL is accessible
- Look for errors in bot logs

### Commands not working
- Run `,setup` first to configure server
- Check bot has required permissions
- Verify command prefix (default: `,`)

## Support

- Check README.md for detailed documentation
- Review IMPLEMENTATION_SUMMARY.md for technical details
- Check logs in console for error messages

## Next Steps

1. ✅ Complete `,setup` and `,adminsetup`
2. ✅ Test moderation commands
3. ✅ Create initial tags for your server
4. ✅ Configure shift system (if using)
5. ✅ Set up stats dashboard channel
6. ✅ Test AI features
7. ✅ Review and customize embed colors in config.py

## Default Configuration

- **Prefix:** `,` (comma)
- **Theme:** Lunar Purple/Blue
- **AI:** Gemini-pro
- **Timezone (Shifts):** GMT+8
- **Staff Flags:** 5-strike system
- **GIFs:** Disabled (lunar theme)

---

**Need help?** Contact the bot owner or check the comprehensive documentation in README.md.
