# Railway Architecture Update - Single Service Approach

**Date**: November 27, 2025  
**Branch**: `deployment-testing`  
**Status**: ✅ Ready for deployment

---

## 🎯 Key Learning: Shared Filesystem Requirement

Your application has a **critical constraint** that shaped the architecture:

```
Bot writes to CSV/JSON files → Flask reads from same files
```

This requires **instant file synchronization** between processes.

---

## ❌ Why Two-Service Approach Doesn't Work

### Original Plan (Discarded)

```
┌──────────────────┐         ┌──────────────────┐
│  Service A       │         │  Service B       │
│  (Flask)         │◄────────┤  (Telegram Bot)  │
│                  │  HTTP   │                  │
│  File System A   │         │  File System B   │
│  /app/data/      │   ✗     │  /app/data/      │
│  - tokens.json   │ Not Sync│  - tokens.json   │
│  - data.csv      │         │  - data.csv      │
└──────────────────┘         └──────────────────┘
```

**Problems:**

1. ❌ **Separate containers** = Separate filesystems
2. ❌ **Separate volumes** = No instant sync
3. ❌ **Network overhead** for API calls
4. ❌ **Complex setup** (two services, internal networking)
5. ❌ **Higher cost** (two Railway services)
6. ❌ **Data inconsistency** risk

---

## ✅ Correct Approach: Single Service with Background Process

### Current Architecture

```
┌─────────────────────────────────────────┐
│  Railway Service: spatial-acc-bot       │
│                                         │
│  ┌────────────────────────────────┐    │
│  │  Process 1: Telegram Bot       │    │
│  │  (Background)                  │    │
│  │  $ python bot_logger.py &      │    │
│  │                                │    │
│  │  Calls: localhost:8080/api     │    │
│  └────────┬───────────────────────┘    │
│           │                            │
│           │ Shared Filesystem          │
│           ↓                            │
│  ┌────────────────────────────────┐    │
│  │  /app/data/ (Volume)           │    │
│  │  - autodesk_tokens.json        │    │
│  │  - assets_total.csv            │    │
│  │  - categories.csv              │    │
│  │  - custom_fields.csv           │    │
│  │  - site_updates.json           │    │
│  └────────┬───────────────────────┘    │
│           │                            │
│           │ Shared Filesystem          │
│           ↓                            │
│  ┌────────────────────────────────┐    │
│  │  Process 2: Flask Web App      │    │
│  │  (Foreground - Monitored)      │    │
│  │  $ python main.py              │    │
│  │                                │    │
│  │  Listens: 0.0.0.0:8080         │    │
│  └────────────────────────────────┘    │
│                                         │
└─────────────────────────────────────────┘
```

**Benefits:**

1. ✅ **Instant file access** - Both processes see same files
2. ✅ **Localhost communication** - No network latency
3. ✅ **One volume** - Persistent storage shared naturally
4. ✅ **Simpler deployment** - One service, one Procfile
5. ✅ **Lower cost** - Single Railway service
6. ✅ **Easier debugging** - One set of logs

---

## 🔧 The Magic: Background Process with `&`

### Procfile Command

```bash
web: cd telebot && python bot_logger.py & cd root && python main.py
```

### What Happens

```
Step 1: cd telebot
        ↓
Step 2: python bot_logger.py &
        │
        ├──→ Starts bot in BACKGROUND
        │    Bot keeps running
        │    Output → Railway logs
        │
        └──→ Shell continues (& symbol)

Step 3: cd root
        ↓
Step 4: python main.py
        │
        └──→ Starts Flask in FOREGROUND
             Railway monitors this process
             If Flask crashes → auto-restart
```

### Process Monitoring

```
┌─────────────────────────────────┐
│  Railway Container              │
├─────────────────────────────────┤
│                                 │
│  bot_logger.py (PID 123)       │  ← Background, not monitored
│  └─ If crashes silently,       │     Railway won't detect
│     Flask keeps running         │
│                                 │
│  main.py (PID 124)             │  ← Foreground, monitored
│  └─ If crashes,                │     Railway detects
│     Restarts entire container  │     Both processes restart
│                                 │
└─────────────────────────────────┘
```

**Trade-off**: Silent bot failures won't trigger auto-restart. Monitor logs regularly.

---

## 📁 File Sharing Between Processes

### How It Works

Both processes run in the **same container**, so they see the **same filesystem**:

```python
# In telebot/bot_logger.py
SITE_UPDATES_PATH = BASE_DIR / "site_updates.json"

# Writes update
with open(SITE_UPDATES_PATH, 'w') as f:
    json.dump(updates, f)

# In root/app/routes.py (Flask)
@app.route("/api/updates")
def get_updates():
    # Reads same file instantly
    with open("../telebot/site_updates.json") as f:
        return jsonify(json.load(f))
```

### Railway Volume

```
/app/data/  ← Persistent across deployments
├── autodesk_tokens.json    (OAuth tokens)
├── assets_total.csv         (Asset cache)
├── categories.csv           (Categories cache)
├── custom_fields.csv        (Custom fields)
└── output/
    └── *.json               (Generated data)

telebot/
├── site_updates.json        (Bot updates)
└── issue_updates.json       (Issue logs)
```

**Volume Configuration:**

- Mount path: `/app/data`
- Size: 1GB (expandable)
- Persists: tokens, CSVs, caches

---

## 🔄 Code Changes Summary

### 1. Simplified `telebot/bot_logger.py`

```python
# BEFORE (two-service approach)
API_BASE = os.getenv("FLASK_API_URL", "http://localhost:8080")
API_URL = f"{API_BASE}/update_status"

# AFTER (single-service approach)
API_BASE = "http://localhost:8080"  # Hardcoded - same container
API_URL = f"{API_BASE}/update_status"
```

**Rationale**: No need for environment variable since Flask is always on localhost.

### 2. Updated `Procfile`

```bash
# BEFORE (Flask only)
web: cd root && python main.py

# AFTER (Bot + Flask)
web: cd telebot && python bot_logger.py & cd root && python main.py
```

**Explanation**: The `&` symbol runs bot in background, then Flask starts in foreground.

### 3. Removed `Procfile.bot`

No longer needed - bot runs from main `Procfile` command.

### 4. Updated `.env.example`

```bash
# REMOVED
# FLASK_API_URL=http://flask-web.railway.internal

# Not needed anymore - same container = localhost
```

---

## 🚀 Deployment Workflow

### Step-by-Step

```
1. Push code to GitHub (deployment-testing branch)
   ↓
2. Railway auto-detects changes
   ↓
3. Builds container:
   - Installs Python dependencies
   - Copies all files
   ↓
4. Starts container:
   - Executes Procfile command
   - Bot starts in background (&)
   - Flask starts in foreground
   ↓
5. Railway monitors Flask (main.py)
   - Health checks: GET /health
   - If Flask crashes → restart container
   ↓
6. Both processes running:
   ✅ Bot handling Telegram messages
   ✅ Flask serving web UI + API
   ✅ Both sharing /app/data volume
```

### What Railway Monitors

```
┌──────────────────────────────┐
│  Railway Health Check        │
├──────────────────────────────┤
│                              │
│  GET /health every 30s      │
│  ↓                          │
│  200 OK → Service healthy   │
│  Timeout/Error → Restart    │
│                              │
└──────────────────────────────┘
```

---

## 📊 Comparison: Old vs New Approach

| Aspect               | Two-Service (Discarded) | Single-Service (Current) |
| -------------------- | ----------------------- | ------------------------ |
| **Services**         | 2 (Flask + Bot)         | 1 (Both in one)          |
| **Filesystem**       | Separate ❌             | Shared ✅                |
| **Communication**    | Network/Internal ❌     | Localhost ✅             |
| **Volumes**          | 2 separate ❌           | 1 shared ✅              |
| **Env Vars**         | Complex (FLASK_API_URL) | Simple (no extra vars)   |
| **Cost**             | 2x services             | 1x service               |
| **Setup Complexity** | High ❌                 | Low ✅                   |
| **File Sync**        | Manual/Delayed ❌       | Instant ✅               |
| **Deployment**       | Two separate deploys    | One unified deploy       |
| **Debugging**        | Check both services     | One log stream           |
| **Scaling**          | Independent (complex)   | Together (simple)        |

---

## 🎓 Key Takeaways

### 1. **Platform Constraints Matter**

PythonAnywhere (old) vs Railway (new):

```
PythonAnywhere:
- Shared disk for all processes ✅
- Can run multiple Python scripts
- Files shared by default

Railway:
- Each service = isolated container
- Need explicit file sharing (volumes)
- Must think about process isolation
```

### 2. **The Roommate Method**

"Make processes live together" instead of "connect separate apartments":

```
❌ Separate apartments = Separate filesystems + Network calls
✅ Same apartment = Shared filesystem + Localhost
```

### 3. **Background Process Pattern**

The `&` symbol is Railway's way of running multiple processes:

```bash
command1 & command2
│          │
│          └─ Runs in foreground (monitored)
└─ Runs in background (independent)
```

### 4. **Trade-offs Are OK**

Silent bot failures won't auto-restart → acceptable trade-off for:

- Simpler architecture
- Lower cost
- Instant file sharing
- Easier deployment

**Mitigation**: Monitor Railway logs, add alerting if needed.

---

## ✅ What We Changed

### Files Modified

1. **`Procfile`** - Added background bot process
2. **`telebot/bot_logger.py`** - Simplified to localhost
3. **`.env.example`** - Removed FLASK_API_URL
4. **`RAILWAY_DEPLOYMENT.md`** - Updated architecture docs
5. **`RAILWAY_CHANGES.md`** - Updated summary

### Files Removed

- ~~`Procfile.bot`~~ - No longer needed

### Concepts Updated

- **Architecture**: Two-service → Single-service
- **Communication**: Internal networking → Localhost
- **File Sharing**: Separate volumes → Shared filesystem
- **Deployment**: Complex → Simple

---

## 🚦 Next Steps

1. **Test Locally** (already done ✅)

   ```bash
   .venv/Scripts/python.exe root/main.py
   ```

2. **Deploy to Railway** (pending)

   - Push to GitHub
   - Create Railway project
   - Add environment variables
   - Deploy and monitor logs

3. **Verify Both Processes**

   ```
   Railway Logs should show:
   ✅ [Bot] Telegram bot started successfully
   ✅ [Flask] Running on http://0.0.0.0:8080
   ```

4. **Test End-to-End**
   - Visit Railway URL
   - Complete OAuth flow
   - Send Telegram message
   - Verify status update works

---

**Credit**: Architecture insight from conversation about Railway's "magic" and the `&` background process pattern. This approach leverages Railway's container model while respecting your application's file-sharing requirements.
