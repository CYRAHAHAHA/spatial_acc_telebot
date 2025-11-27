# Railway Deployment - Changes Summary

## ✅ Completed Changes (deployment-testing branch)

### 📄 New Documentation Files Created

1. **RAILWAY_DEPLOYMENT.md** - Complete Railway deployment guide

   - Quick start for dev environment
   - Production deployment with volumes
   - Single-service architecture (Flask + Bot in one container)
   - Background process explanation (the magic `&` symbol)
   - Environment variables reference
   - Troubleshooting guide

2. **.env.example** - Environment variable template
   - All required Railway variables documented
   - Removed FLASK_API_URL (not needed - same container)
   - Clear setup instructions
   - Security notes

### 🔧 New Configuration Files Created

1. **Procfile** - Single service running both processes:

   ```
   web: cd telebot && python bot_logger.py & cd root && python main.py
   ```

   - Bot runs in **background** (`&` symbol)
   - Flask runs in **foreground** (Railway monitors this)
   - Both share same filesystem and communicate via localhost

2. **railway.json** - Railway deployment configuration
3. **nixpacks.toml** - Custom build configuration
4. **Procfile.bot** - ~~DEPRECATED~~ (no longer needed with single-service approach)

### 💻 Code Changes Made

#### 1. `root/main.py` - Dynamic Port Binding

- ✅ Reads `PORT` from environment (Railway auto-assigns)
- ✅ Binds to `0.0.0.0` instead of localhost
- ✅ Railway-aware logging (stdout vs file)
- ✅ Environment detection and logging

**Before:**

```python
app.run(port=8080, debug=False)
```

**After:**

```python
port = int(os.environ.get("PORT", 8080))
app.run(host="0.0.0.0", port=port, debug=False)
```

#### 2. `root/app/config.py` - Dynamic Configuration

- ✅ Railway environment detection
- ✅ Dynamic redirect URI (uses Railway domains)
- ✅ Removed REDIRECT_URI from required vars (auto-generated)
- ✅ `.env` file optional on Railway (uses env vars)

**Key Changes:**

```python
def _get_redirect_uri(self) -> str:
    # Auto-detects Railway domain and builds callback URL
    if self.railway_public_domain:
        return f"https://{self.railway_public_domain}/callback"
```

#### 3. `root/app/utils.py` - Persistent Storage

- ✅ Added `get_persistent_dir()` helper
- ✅ Railway-aware paths (`/app/data` volume vs local)
- ✅ Updated `get_data_dir()` to use persistent storage
- ✅ Updated `get_output_dir()` for Railway
- ✅ Added `get_token_file_path()` for token persistence

**Key Changes:**

```python
def get_persistent_dir(subdir: str = "") -> Path:
    if os.getenv("RAILWAY_ENVIRONMENT"):
        return Path("/app/data")  # Railway volume
    else:
        return Path(__file__).resolve().parents[2] / "data"
```

#### 4. `root/app/authentication.py` - Token Persistence

- ✅ Uses persistent path for `autodesk_tokens.json`
- ✅ Stores tokens in `/app/data/` on Railway
- ✅ Local development unchanged

**Key Changes:**

```python
if os.getenv("RAILWAY_ENVIRONMENT"):
    self.token_file = str(Path("/app/data") / "autodesk_tokens.json")
```

#### 5. `telebot/bot_logger.py` - Simplified API Communication

- ✅ **SIMPLIFIED**: Hardcoded to localhost (same container)
- ✅ No need for `FLASK_API_URL` environment variable
- ✅ Both processes share same container, communicate locally

**Key Changes:**

```python
# BEFORE (complex, two-service approach):
API_BASE = os.getenv("FLASK_API_URL", "http://localhost:8080")

# AFTER (simple, single-service approach):
API_BASE = "http://localhost:8080"
```

**Why the change:**

- Both processes run in same container
- No need for environment variable configuration
- Always use localhost (faster, simpler)

#### 6. `root/app/routes.py` - Health Check

- ✅ Added `/health` endpoint for Railway monitoring
- ✅ Returns service status and environment info

---

## 🎯 Architecture Decision: Why Single-Service?

**Previously Planned**: Two separate Railway services

- ❌ Flask service + Bot service = separate containers
- ❌ Needed internal networking or public URLs
- ❌ Complex volume syncing
- ❌ Higher cost (two services)

**Current Approach**: Single service with background process

- ✅ Both run in **same container**
- ✅ Share **same filesystem** naturally
- ✅ Communicate via **localhost** (no network)
- ✅ **One volume** = instant file sharing
- ✅ **Lower cost** = one Railway service
- ✅ **Simpler to manage** = one deployment

**The Magic**: `Procfile` command

```bash
web: cd telebot && python bot_logger.py & cd root && python main.py
```

- `&` symbol = run bot in background
- Flask runs in foreground (Railway monitors this)
- Both processes share container resources

---

## 🧪 Testing Results

All code changes tested locally:

- ✅ Config loads correctly
- ✅ Railway detection works (returns False locally)
- ✅ Redirect URI defaults to localhost:8080/callback
- ✅ Port configuration works (defaults to 8080)
- ✅ Persistent directory paths work correctly
- ✅ Token file path resolves correctly
- ✅ Bot communicates with Flask via localhost

---

## 📋 Railway Deployment Checklist

### Dev Environment (Quick Start)

- [ ] Create Railway account
- [ ] Create new project from GitHub
- [ ] Select `deployment-testing` branch
- [ ] Add environment variables (CLIENT_ID, CLIENT_SECRET, etc.)
- [ ] Deploy service (Railway auto-detects Procfile)
- [ ] Wait for both processes to start:
  - ✅ `[Bot] Telegram bot started successfully`
  - ✅ `[Flask] Running on http://0.0.0.0:8080`
- [ ] Copy Railway URL
- [ ] Update Autodesk APS callback URL
- [ ] Set REDIRECT_URI in Railway environment variables
- [ ] Redeploy
- [ ] Visit `/authorize` to authenticate
- [ ] Run `/fetch_assets_config` and `/fetch_all_assets_info`
- [ ] Test Telegram bot by sending a message

### Production Environment

- [ ] Switch to `main` branch
- [ ] Create Railway service
- [ ] Add persistent volume mounted at `/app/data` (1GB)
- [ ] Set production environment variables
- [ ] Configure health checks (path: `/health`)
- [ ] Set up custom domain (optional)
- [ ] Test OAuth flow end-to-end
- [ ] Verify data persists across redeployments
- [ ] Monitor Railway logs for both processes

---

## 🔑 Required Environment Variables

### Single Railway Service (Flask + Bot)

```bash
CLIENT_ID=<autodesk_client_id>
CLIENT_SECRET=<autodesk_client_secret>
SCOPES=data:read data:write data:create
PROJECT_ID=<acc_project_id>
TELEGRAM_TOKEN=<telegram_bot_token>
# REDIRECT_URI is auto-generated, or set manually after first deploy
```

**Removed Variables:**

- ~~`FLASK_API_URL`~~ - Not needed (same container, use localhost)

---

## 📦 File Persistence (Railway Volumes)

**Must Persist:**

- `/app/data/autodesk_tokens.json` - OAuth tokens
- `/app/data/*.csv` - ACC configuration cache
- `/app/data/output/*.json` - Asset data
- `telebot/site_updates.json` - Bot update logs

**Volume Setup:**

- Mount path: `/app/data`
- Size: 1GB recommended

---

## 🚀 Deployment Commands

```bash
# Local testing with Railway environment
railway run python root/main.py

# Deploy to Railway
git push origin deployment-testing

# View logs
railway logs --service flask-web

# Check status
railway status
```

---

## 📚 Documentation Structure

```
spatial_acc_telebot/
├── RAILWAY_DEPLOYMENT.md       ← Main Railway guide
├── .env.example                ← Environment variables template
├── Procfile                    ← Flask web service
├── Procfile.bot                ← Telegram bot service
├── railway.json                ← Railway configuration
├── nixpacks.toml               ← Build configuration
│
├── root/
│   ├── main.py                 ← ✅ Updated (dynamic port)
│   └── app/
│       ├── config.py           ← ✅ Updated (dynamic redirect URI)
│       ├── authentication.py   ← ✅ Updated (persistent tokens)
│       ├── utils.py            ← ✅ Updated (Railway volumes)
│       └── routes.py           ← ✅ Updated (health check)
│
└── telebot/
    └── bot_logger.py           ← ✅ Updated (dynamic API URL)
```

---

## 🔄 Migration from EC2

Old EC2 deployment docs moved to `docs/legacy/` (optional):

- EC2_DEPLOYMENT.md
- GITHUB_ACTIONS_SETUP.md
- QUICKSTART_AL2023.md
- PYTHON_VERSION_FIX.md

These are no longer needed for Railway deployment.

---

## ✨ Next Steps

1. **Test Deployment**:

   - Push to `deployment-testing` branch
   - Deploy to Railway
   - Test OAuth flow
   - Verify Telegram bot integration

2. **Production Deployment**:

   - Merge to `main` branch
   - Deploy production services
   - Set up volumes
   - Configure custom domain

3. **Cleanup** (optional):
   - Archive old EC2 documentation
   - Update main README.md
   - Add Railway badge

---

**Date**: November 27, 2025  
**Branch**: deployment-testing  
**Status**: ✅ Ready for Railway deployment
