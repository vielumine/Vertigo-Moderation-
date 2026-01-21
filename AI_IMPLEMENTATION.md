# Vertigo AI Chatbot - Implementation Complete! 🤖

## Overview
The AI chatbot feature has been successfully implemented with a **Gen-Z meme personality** using HuggingFace's **completely free** Inference API. No costs, no limits!

## ✅ Features Implemented

### 1. **!ai [question]** - Ask the AI anything
- Get Gen-Z meme style responses with slang like "fr fr", "no cap", "that's bussin"
- Embed with question and AI response
- Character limit: 200 characters for Discord
- Rate limited: 1 request per 5 seconds per user

### 2. **Automatic Mention Responses** (@Vertigo)
- Responds when mentioned in messages
- Quick, casual responses
- Configurable per-server

### 3. **!toggle_ai [on/off]** - Admin only
- Turn AI completely on/off for the server
- Immediate effect

### 4. **!ai_settings** - Admin only with buttons
- Interactive settings panel with toggle buttons
- Configure:
  - ✅ AI Enabled
  - 📣 Respond to Mentions
  - 💬 Respond to DMs  
  - 🛡️ Help Moderation
  - 🎭 Personality (Gen-Z, Professional, Funny)

### 5. **DM Support** (Optional)
- AI responds to DMs if enabled in settings
- Checks all mutual guilds for DM permissions

## 🎭 Gen-Z Personality Examples

**Questions & Responses:**
- "what's your favorite food?" → "fr fr tacos hit different no cap 🌮"
- "why are you so cool?" → "nah fr fr i'm just bussin it's giving main character energy fr 💀"
- "how do i report spam?" → "yo just hit report button it's giving efficient vibes no cap 📝"

**Mention Responses:**
- "@Vertigo yo" → "yo what's good bestie, it's giving conversation energy 👀"
- "@Vertigo you alive?" → "lowkey i'm always here bestie, what's good 🔥"

## 🛠️ Setup Instructions

### 1. Get Free HuggingFace Token
1. Go to https://huggingface.co/
2. Sign up (free)
3. Go to Settings → Access Tokens
4. Create new token (read permissions are enough)
5. Copy the token

### 2. Configure Environment
Add to your `.env` file:
```env
HUGGINGFACE_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the Bot
```bash
python main.py
```

## 🗄️ Database Changes

New table added: `ai_settings`
```sql
CREATE TABLE ai_settings (
    guild_id INTEGER PRIMARY KEY,
    ai_enabled BOOLEAN DEFAULT TRUE,
    ai_personality TEXT DEFAULT 'genz',
    respond_to_mentions BOOLEAN DEFAULT TRUE,
    respond_to_dms BOOLEAN DEFAULT FALSE,
    help_moderation BOOLEAN DEFAULT TRUE
);
```

## 🛡️ Safety Features

### Rate Limiting
- 1 AI request per 5 seconds per user
- Prevents spam abuse

### Response Filtering
- Max 200 characters for Discord
- Automatic truncation at word boundaries
- Removes system prompts/instructions

### Timeout Protection
- 5 second timeout for AI API calls
- Friendly error messages if AI is slow

### Error Handling
- Graceful fallbacks if API fails
- "nah the vibes are off rn, try again bestie 😅"

## 📋 Commands Summary

| Command | Description | Permissions |
|---------|-------------|-------------|
| `!ai [question]` | Ask AI a question | Anyone |
| `!toggle_ai on/off` | Enable/disable AI | Admin only |
| `!ai_settings` | Configure AI settings | Admin only |
| Mention @Vertigo | Auto-respond to mentions | Configurable |

## 🎯 Moderation Integration

When users ask moderation questions:
- "should i report this user?"
- "is this toxic behavior?"
- "what's the rule about spam?"

AI provides helpful guidance while staying in character:
- "yo that's definitely cap behavior, report them fr fr 📝"
- "nah fr that's spam behavior lowkey, give warning first then kick 🚪"

## 🔧 Configuration Options

### Environment Variables
```env
HUGGINGFACE_TOKEN=your_token_here
HUGGINGFACE_MODEL=mistralai/Mistral-7B-Instruct-v0.1
AI_ENABLED_BY_DEFAULT=true
AI_RESPONSE_TIMEOUT=5
MAX_RESPONSE_LENGTH=200
RATE_LIMIT_SECONDS=5
```

### Personality Types
- **genz**: Fun, meme-filled responses (default)
- **professional**: Helpful, formal responses
- **funny**: Comedy-focused responses

## 🚀 Benefits

✅ **100% Free** - Uses HuggingFace's free tier
✅ **Unlimited** - No request limits or costs
✅ **Gen-Z Personality** - Authentic meme language
✅ **Moderation Help** - Assists with server rules
✅ **Configurable** - Per-server settings
✅ **Safe** - Rate limiting and content filtering
✅ **Easy Setup** - One free token needed

## 📝 Usage Examples

### Basic Conversation
```
User: !ai what's the meaning of life
Bot: [🤖 AI Response embed with Gen-Z style answer]
```

### Mention Response
```
User: hey @Vertigo what's good today
Bot: [🤖 Quick casual response]
```

### Admin Settings
```
Admin: !ai_settings
Bot: [Interactive embed with toggle buttons]
```

## 🔮 Future Enhancement Ideas

- **Conversation Memory**: Remember context within sessions
- **Custom Personalities**: Server admins can create custom personas
- **Moderation Rules Integration**: AI knows actual server rules
- **Multi-language Support**: Respond in user's language
- **Voice Integration**: Text-to-speech responses
- **Image Understanding**: Analyze and describe images

## 🎉 Implementation Status

**COMPLETE!** All requested features have been implemented:

✅ Free HuggingFace integration
✅ Gen-Z meme personality
✅ All commands (!ai, !toggle_ai, !ai_settings)
✅ Mention responses
✅ DM support
✅ Rate limiting and safety
✅ Database integration
✅ Interactive settings
✅ Moderation help
✅ Background tasks

The AI chatbot is ready to use! Just add your HuggingFace token and start chatting! 🚀