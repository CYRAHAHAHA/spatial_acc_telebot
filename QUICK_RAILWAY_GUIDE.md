# Quick Reference: Railway Single-Service Deployment

## 🎯 The Core Insight

**Problem**: Your app needs Flask and Telegram bot to share CSV/JSON files instantly.

**Solution**: Run both processes in **ONE** Railway service container using the `&` background process trick.

---

## ✅ What Changed

### Before (Complex Two-Service Plan)

```
Railway Service 1: Flask       Railway Service 2: Bot
├─ Port: 8080                  ├─ No port
├─ Volume: /app/data          ├─ Volume: /app/data (separate)
└─ Env: CLIENT_ID, ...        └─ Env: FLASK_API_URL=internal

❌ Two filesystems (sync issues)
❌ Network calls between services
❌ Complex internal networking setup
❌ Double the cost
```

### After (Simple Single-Service)

```
Railway Service: spatial-acc-bot
├─ Process 1: python bot_logger.py & (background)
├─ Process 2: python main.py        (foreground)
├─ Port: 8080
├─ Volume: /app/data (shared!)
└─ Env: CLIENT_ID, SECRET, ...

✅ One filesystem (instant sharing)
✅ Localhost communication (fast)
✅ Simple setup
✅ Half the cost
```

---

## 🔑 Key Files Changed

| File                       | What Changed                                 |
| -------------------------- | -------------------------------------------- |
| **Procfile**               | Added `&` to run bot in background           |
| **bot_logger.py**          | Hardcoded `localhost:8080` (was env var)     |
| **.env.example**           | Removed `FLASK_API_URL` (not needed)         |
| **RAILWAY_DEPLOYMENT.md**  | Updated architecture diagram + instructions  |
| **RAILWAY_CHANGES.md**     | Updated summary with single-service approach |
| **ARCHITECTURE_UPDATE.md** | New doc explaining the change                |

---

## 🚀 How to Deploy

### 1. Push to Railway

```bash
git add .
git commit -m "Railway single-service deployment ready"
git push origin deployment-testing
```

### 2. Create Railway Project

1. Go to https://railway.app/dashboard
2. **New Project** → **Deploy from GitHub**
3. Select: `spatial_acc_telebot` repo
4. Branch: `deployment-testing`

### 3. Add Environment Variables

```bash
CLIENT_ID=<your_autodesk_client_id>
CLIENT_SECRET=<your_autodesk_client_secret>
PROJECT_ID=<your_acc_project_id>
SCOPES=data:read data:write data:create
TELEGRAM_TOKEN=<your_telegram_bot_token>
# REDIRECT_URI will be set after first deploy
```

### 4. Deploy

- Click **Deploy**
- Wait 2-3 minutes

### 5. Check Logs

Look for both processes starting:

```
✅ [Bot] Telegram bot started successfully
✅ [Flask] Running on http://0.0.0.0:8080
```

### 6. Complete OAuth Setup

1. Copy Railway URL (e.g., `https://yourapp.up.railway.app`)
2. Update Autodesk APS callback: `https://yourapp.up.railway.app/callback`
3. Add Railway env var: `REDIRECT_URI=https://yourapp.up.railway.app/callback`
4. Railway auto-redeploys

### 7. Initialize Data

```bash
curl https://yourapp.up.railway.app/fetch_assets_config
curl https://yourapp.up.railway.app/fetch_all_assets_info
```

### 8. Test Bot

Send a message to your Telegram bot → should see status update!

---

## 📦 Add Persistent Volume (Important!)

Without this, tokens/data are lost on each deploy:

1. Railway Dashboard → Your Service
2. **Settings** → **Volumes** → **+ New Volume**
3. **Mount Path**: `/app/data`
4. **Size**: 1GB

Files that will persist:

- `autodesk_tokens.json` (OAuth tokens)
- `*.csv` (asset caches)
- `output/*.json` (generated data)

---

## 🔍 Verify It's Working

### Check Both Processes

```bash
# Railway logs should show:
[Bot] Telegram bot started successfully
[Flask] * Running on http://0.0.0.0:8080
```

### Test Flask

```bash
curl https://yourapp.up.railway.app/health
# Should return: {"status": "healthy"}
```

### Test Bot

1. Send message to Telegram bot
2. Check Railway logs for API call:
   ```
   POST /update_status
   ```

### Test File Sharing

1. Bot updates `site_updates.json`
2. Flask reads it instantly
3. Both see same file (same container!)

---

## 🐛 Troubleshooting

### Bot Not Starting

**Check**: Railway logs for errors in `bot_logger.py`
**Fix**: Verify `TELEGRAM_TOKEN` is correct

### Flask Not Starting

**Check**: Railway logs for errors in `main.py`
**Fix**: Verify all required env vars are set

### Tokens Lost After Deploy

**Check**: Volume is mounted at `/app/data`
**Fix**: Add volume (see above)

### OAuth Callback Fails

**Check**: `REDIRECT_URI` matches Railway URL exactly
**Fix**: Update both Autodesk APS and Railway env var

---

## 📚 Read More

- **RAILWAY_DEPLOYMENT.md** - Complete deployment guide
- **ARCHITECTURE_UPDATE.md** - Why we chose single-service
- **RAILWAY_CHANGES.md** - All code changes summary
- **.env.example** - Environment variables template

---

## ✨ What's Great About This Setup

1. **Simpler**: One service vs two
2. **Cheaper**: One Railway service instead of two
3. **Faster**: Localhost (no network) between processes
4. **Reliable**: Shared filesystem (no sync issues)
5. **Railway-native**: Uses `&` background process pattern
6. **Backwards compatible**: Works locally AND on Railway

---

**Date**: November 27, 2025  
**Branch**: `deployment-testing`  
**Status**: ✅ Ready for Railway deployment

**Next**: Push to GitHub and deploy to Railway! 🚀
