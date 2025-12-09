# Telegram Bot Setup - Development & Production

This guide explains how to set up **separate Telegram bots** for local development and production deployment.

## Why Two Bots?

When you deploy your bot to Railway, the server runs the bot 24/7. If your team wants to test locally, they can't use the same bot token because:

- Only one instance can run per bot token
- Messages would go to whichever bot responds first
- Local testing would interfere with production

**Solution**: Create two separate Telegram bots - one for development, one for production.

---

## Setup Steps

### 1. Create Your Bots in Telegram

#### Production Bot (for Railway deployment)

1. Open Telegram and search for `@BotFather`
2. Send `/newbot`
3. Choose a name: `YourProject Production Bot`
4. Choose a username: `yourproject_prod_bot` (must end in `_bot`)
5. **Save the token** - this is your `TELEGRAM_TOKEN_PROD`

#### Development Bot (for local testing)

1. Send `/newbot` again to @BotFather
2. Choose a name: `YourProject Dev Bot`
3. Choose a username: `yourproject_dev_bot`
4. **Save the token** - this is your `TELEGRAM_TOKEN`

---

### 2. Configure Local Environment

Edit your `.env` file:

```bash
# Development bot (used when running locally)
TELEGRAM_TOKEN=7971750300:AAEGbhzJnjHxke1hp3J607LRbHztyGwZ5VI

# Production bot (used on Railway - optional for local .env)
TELEGRAM_TOKEN_PROD=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz1234567890
```

**Note**: You don't need to set `TELEGRAM_TOKEN_PROD` in your local `.env` - it's only needed on Railway.

---

### 3. Configure Railway Environment Variables

In your Railway dashboard:

1. Go to your project → **Variables** tab
2. Add these variables:

```
CLIENT_ID=PsUt7TUNScfzXFRxPGBVlTQieKy5u3eePKA7uzkQ5onqVdwB
CLIENT_SECRET=B1o5MjBhvfCgx6QDLG1q3bWYTecTwb1Ec2HBmGRxeBRZAMFj1HGJxuzTknyJtpBC
PROJECT_ID=a824e4c7-7bdb-42e0-a874-6ab45fb74d84
SCOPES=data:read data:write data:create user:read account:read account:write
TELEGRAM_TOKEN=7971750300:AAEGbhzJnjHxke1hp3J607LRbHztyGwZ5VI
TELEGRAM_TOKEN_PROD=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz1234567890  ⬅️ Production token
REDIRECT_URI=https://your-app.up.railway.app/callback
```

---

## How It Works

The bot automatically detects which environment it's running in:

```python
# Priority: TELEGRAM_TOKEN_PROD (if set) > TELEGRAM_TOKEN
token = os.environ.get("TELEGRAM_TOKEN_PROD") or os.environ.get("TELEGRAM_TOKEN")
```

### Local Development

- Looks for `TELEGRAM_TOKEN_PROD` (not set locally)
- Falls back to `TELEGRAM_TOKEN`
- **Uses dev bot** ✅

### Railway Deployment

- Finds `TELEGRAM_TOKEN_PROD` (set in Railway)
- **Uses production bot** ✅

---

## Testing Both Bots

### Test Development Bot (Local)

```bash
# Start locally
bash start_all.sh

# In Telegram, send to @yourproject_dev_bot:
/template
```

### Test Production Bot (Railway)

1. Deploy to Railway
2. In Telegram, send to `@yourproject_prod_bot`:
   ```
   /template
   ```

Both bots will have identical functionality but run independently!

---

## Group Setup

You need to add each bot to the appropriate groups:

### Development Groups

- Add `@yourproject_dev_bot`
- Set project ID: `/setproject a824e4c7-7bdb-42e0-a874-6ab45fb74d84`

### Production Groups

- Add `@yourproject_prod_bot`
- Set project ID: `/setproject a824e4c7-7bdb-42e0-a874-6ab45fb74d84`

---

## Troubleshooting

### "Bot is already running" Error

- Only one instance can run per token
- Make sure local bot is stopped before starting Railway deployment
- Use different tokens for local vs production

### Bot Responds from Wrong Environment

- Check Railway environment variables
- Verify `TELEGRAM_TOKEN_PROD` is set correctly
- Check bot logs to see which token is being used

### Both Bots Respond

- Make sure they're using different tokens
- Check that `TELEGRAM_TOKEN` and `TELEGRAM_TOKEN_PROD` are different values

---

## Summary

✅ **Local Development**: Uses `TELEGRAM_TOKEN` → Dev bot  
✅ **Railway Production**: Uses `TELEGRAM_TOKEN_PROD` → Production bot  
✅ **Team can test locally** while production runs on server  
✅ **No interference** between environments
