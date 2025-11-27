# Railway Deployment Guide

Complete guide for deploying spatial_acc_telebot on Railway.app for both development testing and production environments.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Quick Start - Dev Mode](#quick-start---dev-mode)
- [Production Deployment](#production-deployment)
- [Architecture](#architecture)
- [Environment Variables](#environment-variables)
- [Persistent Storage](#persistent-storage)
- [Troubleshooting](#troubleshooting)

---

## Overview

Railway.app provides a modern platform-as-a-service (PaaS) for deploying applications with:

- ✅ Automatic HTTPS/SSL
- ✅ Built-in CI/CD from GitHub
- ✅ Environment variable management
- ✅ Volume-based persistent storage
- ✅ Zero-downtime deployments
- ✅ Background process support

This application consists of **two processes running in one service**:

1. **Flask Web App** - OAuth, web UI, API endpoints (foreground process)
2. **Telegram Bot** - Message handler, status updates (background process)

**Key Architecture Decision**: Both processes run in the **same Railway service container** so they can:

- Share the same filesystem (CSV/JSON files)
- Communicate via localhost (no network overhead)
- Use a single persistent volume
- Deploy and scale together

---

## Prerequisites

### Required Accounts & Credentials

- ✅ [Railway account](https://railway.app/) (free tier available)
- ✅ GitHub repository with your code
- ✅ [Autodesk APS](https://aps.autodesk.com/) app credentials
- ✅ Telegram bot token from [@BotFather](https://t.me/botfather)

### Local Development Setup

```bash
# Install Railway CLI (optional, for local testing)
npm i -g @railway/cli

# Or using Homebrew (Mac)
brew install railway
```

---

## Quick Start - Dev Mode

Deploy a test environment on Railway for development and testing.

### Step 1: Create Railway Project

1. Go to [Railway Dashboard](https://railway.app/dashboard)
2. Click **New Project** → **Deploy from GitHub repo**
3. Select your `spatial_acc_telebot` repository
4. Choose branch: `deployment-testing` (for dev) or `main` (for prod)

### Step 2: Configure Service

#### 2.1 Service Settings

- **Service Name**: `spatial-acc-bot`
- **Root Directory**: Leave empty (uses repo root)
- **Start Command**: Railway auto-detects from `Procfile`

The `Procfile` contains:

```
web: cd telebot && python bot_logger.py & cd root && python main.py
```

This command does the magic:

- Starts the Telegram bot in the **background** (`&` symbol)
- Starts Flask web app in the **foreground** (Railway monitors this)
- Both processes share the same container and filesystem

#### 2.2 Add Environment Variables

Click **Variables** tab and add:

```bash
# Autodesk OAuth
CLIENT_ID=your_autodesk_client_id
CLIENT_SECRET=your_autodesk_client_secret
SCOPES=data:read data:write data:create
PROJECT_ID=your_acc_project_id

# Telegram
TELEGRAM_TOKEN=your_telegram_bot_token

# IMPORTANT: Set this AFTER first deployment
# REDIRECT_URI=https://your-app.up.railway.app/callback
```

> **Note**: Leave `REDIRECT_URI` empty for first deployment. Railway will generate a URL, then you'll update this.

#### 2.3 Deploy

Click **Deploy** and wait for build to complete (~2-3 minutes).

**What happens during deployment:**

1. Railway detects Python project
2. Installs dependencies from `requirements.txt`
3. Runs the `Procfile` command:
   - Starts `bot_logger.py` in background
   - Starts `main.py` in foreground
4. Both processes are now running in the same container

### Step 3: Update Autodesk Callback URL

1. After deployment, copy your Railway URL (e.g., `https://spatial-acc-bot-production.up.railway.app`)
2. Go to [Autodesk APS](https://aps.autodesk.com/) → Your App → **General Settings**
3. Add callback URL: `https://your-railway-url/callback`
4. Back in Railway, add variable:
   ```
   REDIRECT_URI=https://your-railway-url/callback
   ```
5. Redeploy (Railway auto-redeploys on env var changes)

### Step 4: Authenticate & Initialize Data

1. Visit `https://your-railway-url/authorize`
2. Login with Autodesk account
3. After successful auth, initialize data:

```bash
# Fetch ACC configuration
curl https://your-railway-url/fetch_assets_config

# Fetch all assets
curl https://your-railway-url/fetch_all_assets_info
```

### Step 5: Verify Both Services Are Running

Check Railway logs to confirm:

```
✅ [Bot] Telegram bot started successfully
✅ [Flask] Running on http://0.0.0.0:8080
```

Send a message to your Telegram bot to verify it's processing updates.

---

## Production Deployment

For production-ready deployment with best practices.

### Production Checklist

- [ ] Use `main` branch (not `deployment-testing`)
- [ ] Enable Railway volume for persistent storage
- [ ] Configure health checks
- [ ] Set up monitoring and alerts
- [ ] Use production Autodesk credentials
- [ ] Secure environment variables (never commit to git)
- [ ] Set up custom domain (optional)

### Step 1: Create Production Project

1. Railway Dashboard → **New Project** → **Deploy from GitHub**
2. Select `main` branch
3. Name: `spatial-acc-bot-production`

### Step 2: Configure Service with Persistent Volume

#### 2.1 Create Service

Same as dev mode, but with additional persistent storage:

#### 2.2 Add Persistent Volume

1. Service Settings → **Volumes** → **+ Add Volume**
2. **Mount Path**: `/app/data`
3. **Size**: 1GB (can increase later)
4. This persists across deployments:
   - `autodesk_tokens.json` (OAuth tokens)
   - CSV configuration files (assets, categories, etc.)
   - Bot update logs (site_updates.json, etc.)

**Why this matters:**

- Without a volume, Railway's filesystem is **ephemeral** (resets on each deploy)
- OAuth tokens would be lost → you'd have to re-authenticate
- CSV caches would be lost → slow startup times

#### 2.3 Environment Variables (Production)

```bash
# Autodesk OAuth
CLIENT_ID=prod_autodesk_client_id
CLIENT_SECRET=prod_autodesk_client_secret
REDIRECT_URI=https://spatial-acc-bot.your-domain.com/callback
SCOPES=data:read data:write data:create
PROJECT_ID=prod_acc_project_id

# Telegram
TELEGRAM_TOKEN=prod_telegram_bot_token

# Railway auto-provides these (don't set):
# PORT
# RAILWAY_ENVIRONMENT
# RAILWAY_PUBLIC_DOMAIN
# RAILWAY_STATIC_URL
```

### Step 3: Health Checks & Monitoring

#### 3.1 Add Health Check Endpoint

Already implemented in `root/app/routes.py`:

```python
@app.route("/health")
def health_check():
    return jsonify({"status": "healthy"}), 200
```

#### 3.2 Configure in Railway

1. Service Settings → **Health Check**
2. **Path**: `/health`
3. **Interval**: 30 seconds
4. **Timeout**: 10 seconds

### Step 5: Custom Domain (Optional)

1. Service Settings → **Domains** → **+ Add Domain**
2. Add your domain: `spatial-acc-bot.your-domain.com`
3. Update DNS:

   - Add CNAME record pointing to Railway URL
   - Railway auto-provisions SSL certificate

4. Update environment variables:

   ```
   REDIRECT_URI=https://spatial-acc-bot.your-domain.com/callback
   ```

5. Update Autodesk APS callback URL

---

## Architecture

### Single-Service Deployment (Simplified & Recommended)

```
┌─────────────────────────────────────────────────────────┐
│                  Railway Project                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Service: spatial-acc-bot                       │   │
│  ├─────────────────────────────────────────────────┤   │
│  │  • Port: $PORT (auto, e.g. 8080)               │   │
│  │  • URL: *.up.railway.app                       │   │
│  │  • Volume: /app/data (1GB)                     │   │
│  │  • Procfile: bot_logger.py & main.py           │   │
│  │                                                 │   │
│  │  Process 1 (Background):                       │   │
│  │    └─ python bot_logger.py                    │   │
│  │       └─ Telegram message handler              │   │
│  │       └─ Calls localhost:8080/update_status    │   │
│  │                                                 │   │
│  │  Process 2 (Foreground):                       │   │
│  │    └─ python main.py (Flask)                  │   │
│  │       └─ Web UI, OAuth, REST API               │   │
│  │                                                 │   │
│  │  Shared Filesystem:                            │   │
│  │    └─ /app/data/autodesk_tokens.json          │   │
│  │    └─ /app/data/*.csv (cached assets)         │   │
│  │    └─ /app/data/output/*.json                 │   │
│  │    └─ telebot/site_updates.json               │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
└─────────────────────────────────────────────────────────┘
         ↓                                    ↑
    Public HTTPS                         Telegram
  (OAuth, Web UI)                        Bot API
         ↓
   Autodesk ACC API
```

**Key Benefits of Single-Service Architecture:**

- ✅ **Shared Filesystem**: Both processes see the same files instantly
- ✅ **Simple Communication**: Bot → Flask via localhost (no network)
- ✅ **One Volume**: Single persistent storage mount point
- ✅ **Easier Management**: One service to monitor and scale
- ✅ **Cost Effective**: Uses one Railway service instead of two

### Data Flow

```
User → Telegram Bot → localhost:8080/update_status → Flask API → ACC API
                            ↓                              ↓
                   site_updates.json              autodesk_tokens.json
                                                         ↓
                                                    /app/data/*.csv
```

---

## Environment Variables

### Required Environment Variables

| Variable         | Required | Description            | Example                            |
| ---------------- | -------- | ---------------------- | ---------------------------------- |
| `CLIENT_ID`      | ✅       | Autodesk client ID     | `abc123xyz...`                     |
| `CLIENT_SECRET`  | ✅       | Autodesk client secret | `secret123...`                     |
| `REDIRECT_URI`   | ✅       | OAuth callback URL     | `https://app.railway.app/callback` |
| `SCOPES`         | ✅       | API scopes             | `data:read data:write data:create` |
| `PROJECT_ID`     | ✅       | ACC project ID         | `b.abc123...`                      |
| `TELEGRAM_TOKEN` | ✅       | Telegram bot token     | `1234:ABCdef...`                   |

### Auto-Injected by Railway (Do Not Set)

| Variable                | Description           | Example                  |
| ----------------------- | --------------------- | ------------------------ |
| `PORT`                  | Railway-assigned port | `8080`                   |
| `RAILWAY_ENVIRONMENT`   | Environment name      | `production`             |
| `RAILWAY_PUBLIC_DOMAIN` | Auto-generated domain | `app.up.railway.app`     |
| `RAILWAY_STATIC_URL`    | Static URL            | `https://...railway.app` |
| `RAILWAY_PROJECT_ID`    | Project ID            | Auto-generated           |
| `RAILWAY_SERVICE_ID`    | Service ID            | Auto-generated           |

---

## Persistent Storage

### What Needs Persistence?

Railway's filesystem is **ephemeral** (reset on each deploy). Use volumes for:

✅ **Must Persist:**

- `autodesk_tokens.json` - OAuth tokens (refresh every 14 days)
- `data/*.csv` - ACC configuration cache
- `root/output/*.json` - Asset data
- `telebot/site_updates.json` - Telegram bot update logs

❌ **Don't Persist:**

- Python cache (`__pycache__`)
- Virtual environments (`.venv`)
- Temporary logs (use Railway's log viewer)

### Volume Setup

1. **Service** → **Settings** → **Volumes** → **+ Add Volume**
2. **Mount Path**: `/app/data`
3. **Size**: Start with 1GB (can increase later)
4. Code automatically detects and uses volume when `RAILWAY_ENVIRONMENT` is set

### How It Works

The code checks for Railway environment:

```python
# In root/app/utils.py
def get_persistent_dir(subdir: str = "") -> Path:
    if os.getenv("RAILWAY_ENVIRONMENT"):
        base = Path("/app/data")  # Railway volume
    else:
        base = Path(__file__).resolve().parents[2] / "data"  # Local
    return base
```

---

## How the Background Process Works

### The Magic `&` Symbol

Railway's Procfile command uses a clever trick to run both processes in one container:

```bash
web: cd telebot && python bot_logger.py & cd root && python main.py
```

**What happens:**

1. **`python bot_logger.py &`** - Starts Telegram bot in **background**

   - The `&` tells Linux "run this and move on, don't wait"
   - Bot continues running in background
   - Output goes to Railway logs

2. **`python main.py`** - Starts Flask in **foreground**
   - Railway monitors this process
   - If Flask crashes, Railway detects and restarts the whole container
   - Both processes restart together

### Why This Order Matters

```
Bot (background) → Flask (foreground)
         ↓              ↓
    Not monitored   Monitored by Railway
         ↓              ↓
  Silent failures  Auto-restart on crash
```

**Trade-off**: If the bot crashes silently, Railway won't detect it (Flask keeps running). Solution: Check logs periodically or add health monitoring.

### Communication Between Processes

Since both run in the same container:

```python
# In telebot/bot_logger.py
API_BASE = "http://localhost:8080"  # Flask is on same machine
API_URL = f"{API_BASE}/update_status"

# No network latency, no separate service needed
```

**Benefits:**

- ✅ Instant communication (localhost)
- ✅ No Railway service networking overhead
- ✅ Shared memory and filesystem
- ✅ Lower cost (one service instead of two)

---

## Troubleshooting

### Common Issues

#### 1. OAuth Callback Error (401/403)

**Symptom**: "Redirect URI mismatch" after login

**Solution**:

1. Check Railway URL matches exactly in Autodesk APS
2. Verify `REDIRECT_URI` env var is set correctly
3. Redeploy after updating env vars

```bash
# Check current Railway URL
railway status

# Verify callback URL
curl https://your-app.railway.app/api/status
```

#### 2. Bot Not Receiving Messages

**Symptom**: Telegram bot doesn't respond or process updates

**Solution**:

1. Check Railway logs - verify bot process started successfully
2. Look for: `[Bot] Telegram bot started successfully`
3. Verify `TELEGRAM_TOKEN` is correct
4. Test bot directly in Telegram

```bash
# View Railway logs
railway logs

# Should see both processes:
# ✅ [Bot] Telegram bot started
# ✅ [Flask] Running on http://0.0.0.0:8080
```

#### 3. Bot Can't Connect to Flask API

**Symptom**: Bot logs show "Connection refused" when updating status

**Solution**:

Since both run in same container, this should never happen. If it does:

1. Check Flask is actually running on port 8080
2. Verify Procfile uses `&` to background the bot
3. Check Railway logs for Flask startup errors

```bash
# Procfile should be:
web: cd telebot && python bot_logger.py & cd root && python main.py

# The & symbol runs bot in background
# Flask starts after and runs in foreground
```

#### 3. Tokens Not Persisting

**Symptom**: Re-authenticate on every deploy

**Solution**:

1. Ensure volume is mounted at `/app/data`
2. Check code uses `get_persistent_dir()` helper
3. Verify volume size isn't full

```bash
# Check volume status in Railway dashboard
# Service → Volumes → Usage
```

#### 4. Port Binding Error

**Symptom**: "Address already in use" or service won't start

**Solution**:

1. Ensure `main.py` uses `PORT` env var
2. Bind to `0.0.0.0`, not `localhost`
3. Check code:

```python
port = int(os.environ.get("PORT", 8080))
app.run(host="0.0.0.0", port=port, debug=False)
```

#### 5. CSV Files Not Loading

**Symptom**: "File not found" errors for CSV files

**Solution**:

1. Run initial data fetch:
   ```bash
   curl https://your-app.railway.app/fetch_assets_config
   curl https://your-app.railway.app/fetch_all_assets_info
   ```
2. Check volume is mounted
3. Verify CSV files exist in `/app/data`

### Debugging Commands

```bash
# View logs
railway logs --service flask-web
railway logs --service telegram-bot

# SSH into service
railway shell --service flask-web

# Check environment variables
railway variables --service flask-web

# Check service status
railway status

# Restart service
railway restart --service flask-web
```

### Railway CLI Testing

Test deployment locally before pushing:

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export PORT=8080
export RAILWAY_ENVIRONMENT=development
export CLIENT_ID=your_id
# ... etc

# Run locally
railway run python root/main.py
```

---

## Migration from EC2

If migrating from EC2 deployment:

1. **Export Data**:

   ```bash
   # On EC2, backup:
   scp -i key.pem ec2-user@host:/path/to/data/*.csv ./backup/
   scp -i key.pem ec2-user@host:/path/to/autodesk_tokens.json ./backup/
   ```

2. **Upload to Railway Volume**:

   ```bash
   # After Railway deployment with volume:
   railway shell --service flask-web
   # Then upload files via Railway dashboard or API
   ```

3. **Update DNS** (if using custom domain)

4. **Update Autodesk APS** callback URL

5. **Test thoroughly** before switching production traffic

---

## Cost Estimation

### Railway Pricing (as of 2024)

**Free Tier:**

- $5 free credits/month
- 2 services: ~$10-15/month

**Hobby Plan:**

- $5/month + usage
- ~$15-25/month for this app (2 services + volume)

**Volume Costs:**

- $0.25/GB/month
- 1GB recommended = $0.25/month

### Total Estimated Cost

- **Dev Environment**: Free tier ($5 credits)
- **Production**: $15-30/month

---

## Security Best Practices

- ✅ Never commit `.env` file to git
- ✅ Use Railway's secret management (not env vars in code)
- ✅ Enable 2FA on Railway account
- ✅ Restrict Autodesk APS app to specific callback URLs
- ✅ Use internal networking between services
- ✅ Regularly rotate Telegram bot token
- ✅ Monitor Railway logs for suspicious activity
- ✅ Use custom domain with Railway's auto-SSL

---

## Next Steps

1. ✅ Deploy dev environment
2. ✅ Test OAuth flow
3. ✅ Test Telegram integration
4. ✅ Verify data persistence
5. ✅ Deploy production with volume
6. ✅ Set up monitoring
7. ✅ Configure custom domain (optional)
8. ✅ Set up CI/CD (Railway auto-deploys from GitHub)

---

## Support & Resources

- [Railway Documentation](https://docs.railway.app/)
- [Railway Discord](https://discord.gg/railway)
- [Autodesk APS Docs](https://aps.autodesk.com/developer/overview)
- [Telegram Bot API](https://core.telegram.org/bots/api)

---

**Last Updated**: November 27, 2025
