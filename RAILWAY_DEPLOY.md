# Railway Deployment Guide

## 🚀 Deploy to Railway in 5 Minutes

### Step 1: Get Your Bot Token
1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Send `/newbot` and follow the instructions
3. Copy your bot token (looks like: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`)

### Step 2: Push to GitHub
```bash
# Add all files to git
git add .

# Commit changes
git commit -m "Fix bot with comprehensive logging and working HF Spaces integration

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"

# Push to your GitHub repository
git push origin main
```

### Step 3: Deploy on Railway
1. Go to [railway.app](https://railway.app)
2. Sign in with GitHub
3. Click "New Project" → "Deploy from GitHub repo"
4. Select this repository
5. Railway will automatically detect Python and deploy

### Step 4: Set Environment Variables
In Railway dashboard:
1. Go to your project → "Variables" tab
2. Add these environment variables:

```
BOT_TOKEN = your_bot_token_here
DEBUG = false
```

**Important:**
- ✅ Only need `BOT_TOKEN` - no HuggingFace API key needed!
- ✅ Using public HF Spaces (completely free)
- ✅ Set `DEBUG=false` for production (reduce logs)

### Step 5: Deploy!
Railway will automatically:
- ✅ Install dependencies from `requirements.txt`
- ✅ Run `python bot.py` (from Procfile)
- ✅ Start your bot
- ✅ Keep it running 24/7

## 📊 Monitoring Your Bot

### Check Logs
In Railway dashboard:
1. Go to "Deployments" tab
2. Click on latest deployment
3. View real-time logs

### What to Look For:
```
[OK] Using public HuggingFace Spaces (no API token required)
🤖 AI Roleplay Bot started successfully!
📊 Database: bot_data.db
🌐 HuggingFace Spaces: ['text', 'image', 'video']
Bot is now running and polling for updates
```

### Database Storage
- Railway provides persistent storage automatically
- SQLite database (`bot_data.db`) will persist between deployments
- All user interactions and analytics are saved

## 🚨 Troubleshooting

### Bot Not Starting?
1. Check Railway logs for errors
2. Verify `BOT_TOKEN` is set correctly
3. Make sure token is from a fresh bot (regenerate if shared publicly)

### "Conflict: terminated by other getUpdates request"
- Stop any local bot instances
- Only one bot instance can run per token

### HuggingFace Spaces Not Working?
- No action needed - using public spaces (no token required)
- Spaces might take 1-2 minutes to "wake up" on first use
- Check logs for "Space is loading" messages

## 💰 Cost
- **Railway:** Free tier provides 512MB RAM, $5/month after 500 hours
- **HuggingFace:** Free public spaces (no API costs)
- **Total estimated cost:** $0-5/month depending on usage

## 🔄 Updates
To update your bot:
```bash
# Make changes to code
git add .
git commit -m "Update bot features"
git push origin main
```
Railway will automatically redeploy!

## 📈 Features Available
✅ **Character roleplay** - Multiple AI personalities
✅ **Text generation** - AI conversations
✅ **Image generation** - Character portraits and scenes
✅ **Video generation** - Character animations (experimental)
✅ **Comprehensive logging** - Track all interactions
✅ **Database analytics** - Usage statistics via `/stats`
✅ **Custom characters** - Users can create their own

Your bot is production-ready with full logging and monitoring! 🎉