# Luna Discord Bot 🌙

Luna is a comprehensive Discord moderation bot with a lunar purple theme, featuring advanced moderation tools, AI integration via Gemini, shift management, tags system, and more.

## Features

### Core Moderation
- **Warnings System**: Warn users with automatic expiration
- **Mutes**: Temporary and permanent mutes with timeout integration
- **Kicks & Bans**: Standard and mass moderation actions
- **Staff Flagging**: 5-strike system for staff management
- **Moderation Logs**: Complete audit trail of all actions
- **Hierarchy Management**: Role-based permission system

### AI Integration (Gemini)
- **AI Chatbot**: Respond to mentions and DM messages
- **AI Panel**: Interactive settings with buttons
- **AI Targeting**: Owner-only roasting and trolling feature
- **Multiple Personalities**: Professional, cold, formal tones

### Tags System
- **Helper Viewing**: ,tag and ,tags commands (helper+ only)
- **Staff Management**: Create, edit, delete tags (staff+ only)
- **Categories**: Organize tags by category
- **Search**: Find tags quickly by title or category

### Shift Management (GMT+8)
- **Clock In/Out**: Track shifts with GMT+8 timezone
- **AFK Detection**: Automatic warnings for inactive shifts
- **Weekly Quotas**: Track hours logged per week
- **Leaderboards**: View top performers
- **Break Tracking**: Log break time separately

### Stats Dashboard
- **External API**: Fetch execution stats from API
- **Auto-Update**: Background task updates every 5 minutes
- **Channel Renaming**: Auto-rename channel with total count
- **Manual Refresh**: ,refresh command (admin-only)
- **Unix Timestamps**: Relative time display

### Utility Commands
- **Announcements**: ,announce with embeds
- **Polls**: ,poll for quick voting
- **Reminders**: ,remindme with notifications
- **Dictionary**: ,define for word definitions
- **Translation**: ,translate for language translation
- **Ask AI**: ,askai for direct AI queries

### Setup & Configuration
- **,setup**: Configure basic server settings (roles, channels, prefix, warn duration)
- **,adminsetup**: Configure admin settings (flag duration, lock categories, admin roles)
- **Interactive Modals**: User-friendly configuration interface

## Installation

### Requirements
- Python 3.10+
- Discord.py 2.3.0+
- Gemini API Key

### Setup
1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and configure
4. Run the bot: `python app.py`

### Environment Variables
See `.env.example` for all required configuration options.

## Lunar Theme

Luna uses a strict, formal lunar color scheme:
- **Deep Space** (#02040B): Critical actions (ban, terminate)
- **Starlight Blue** (#7FA9FF): Info and success messages
- **Cosmic Purple** (#1B1431): Moderation actions
- **Lunar Glow** (#4A5FF5): AI and special features

## Command Prefix
Default: `,` (customizable per server)

## Permissions

- **Owner Only**: ,help_all, ,extract_dms, ,ai_target, ,ai_stop, ,aipanel
- **Admin**: ,adminsetup, ,refresh, most admin commands
- **Staff+**: ,tag_create, ,tag_edit, ,tag_delete, moderation commands
- **Helper**: ,tag, ,tags (viewing only)
- **Member+**: ,help, ,ping, ,userinfo, etc.

## Key Differences from Vertigo

1. **No GIFs**: Luna uses clean embeds without GIF attachments
2. **Stricter Language**: Formal, professional tone throughout
3. **Lunar Colors**: Purple/blue theme instead of red/gray
4. **Gemini AI**: Uses Google Gemini instead of HuggingFace
5. **New Features**: Tags, shifts, enhanced utilities, stats dashboard
6. **GMT+8 Shifts**: Dedicated shift system for staff tracking

## Support

For issues, feature requests, or questions, please contact the bot owner.

## License

Proprietary - All rights reserved
