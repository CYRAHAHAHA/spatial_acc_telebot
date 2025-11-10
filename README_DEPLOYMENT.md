# Spatial ACC Telegram Bot - Deployment Guide

Complete automation solution for deploying to Amazon Linux 2023 EC2 instances using GitHub Actions.

## 🚀 Quick Start (3 Steps)

### 1. Set Up GitHub Secrets
```bash
# Go to: Repository Settings → Secrets and variables → Actions
# Add 11 secrets (see .github/secrets.template for full list)
```

### 2. Prepare EC2 Instance
```bash
ssh -i your-key.pem ec2-user@your-ec2-ip
sudo dnf update -y
sudo dnf install -y python3 python3-pip git rsync
mkdir -p /home/ec2-user/spatial_acc_telebot
sudo firewall-cmd --permanent --add-port=8080/tcp
sudo firewall-cmd --reload
```

### 3. Deploy
```bash
# Push to main branch
git push origin main

# Or trigger manually from GitHub Actions tab
```

That's it! GitHub Actions handles everything else.

## 📁 Documentation Index

### Getting Started
- **`QUICKSTART_AL2023.md`** - 5-minute setup guide for Amazon Linux 2023
- **`DEPLOYMENT_CHECKLIST.md`** - Complete checklist for deployment
- **`PYTHON_VERSION_FIX.md`** - Fix Python compatibility issues

### Deployment
- **`GITHUB_ACTIONS_SETUP.md`** - Configure automated GitHub Actions deployment
- **`EC2_DEPLOYMENT.md`** - Comprehensive manual deployment guide
- **`.github/secrets.template`** - Template for GitHub Secrets

### Architecture & Development
- **`CLAUDE.md`** - Codebase architecture and development guide
- **`README.md`** - Original project documentation

## 🔧 What Gets Deployed

### Included in Deployment
✅ All Python code (`.py` files)
✅ Requirements file (`requirements.txt`)
✅ Configuration templates
✅ Deployment scripts (`start_all.sh`, etc.)
✅ Static files (SPA frontend)

### Excluded from Deployment (Preserved on Server)
❌ Virtual environment (`venv/`)
❌ Log files (`logs/`)
❌ OAuth tokens (`autodesk_tokens.json`)
❌ Generated CSVs (`root/data/*.csv`)
❌ Update history (`telebot/site_updates.json`)

## 🔐 Required Secrets

Add these 11 secrets to GitHub:

### EC2 Connection (4)
```
EC2_SSH_KEY          # Your .pem file contents
EC2_HOST             # EC2 IP or hostname
EC2_USER             # ec2-user
EC2_DEPLOY_PATH      # /home/ec2-user/spatial_acc_telebot
```

### Autodesk API (5)
```
AUTODESK_CLIENT_ID
AUTODESK_CLIENT_SECRET
AUTODESK_REDIRECT_URI    # http://your-ec2-ip:8080/callback
AUTODESK_SCOPES          # data:read data:write data:create
AUTODESK_PROJECT_ID
```

### Telegram (2)
```
TELEGRAM_TOKEN
SITE_UPDATES_TOKEN       # Random secure token
```

## 🎯 Deployment Flow

```
Push to main
    ↓
GitHub Actions triggers
    ↓
Checkout code
    ↓
Create .env from secrets
    ↓
Rsync to EC2
    ↓
Run deploy_refresh.sh:
  • Update dependencies
  • Stop services
  • Start services
    ↓
Verify deployment
    ↓
Done! ✅
```

## 📜 Management Scripts

```bash
# Start all 3 services
./start_all.sh

# Check status
./status.sh

# Stop all services
./stop_all.sh

# Deployment refresh (used by GitHub Actions)
./deploy_refresh.sh

# View logs
tail -f logs/*.log
```

## 🔍 Verify Deployment

After deployment, check:

1. **Services Running**:
   ```bash
   ssh -i your-key.pem ec2-user@your-ec2-ip
   cd /home/ec2-user/spatial_acc_telebot
   ./status.sh
   ```

2. **Web UI**: `http://your-ec2-ip:8080`

3. **API Status**: `http://your-ec2-ip:8080/api/status`

4. **Logs**: `tail -f logs/*.log`

## 🐛 Troubleshooting

### GitHub Actions fails
→ Check workflow logs in Actions tab
→ Verify all 11 secrets are set
→ Test SSH: `ssh -i your-key.pem ec2-user@your-ec2-ip`

### Services don't start
→ SSH to EC2 and run `./status.sh`
→ Check logs: `tail -f logs/*.log`
→ Verify .env file: `cat .env`

### Python dependency errors
→ See `PYTHON_VERSION_FIX.md`
→ Upgrade to Python 3.11 if needed

### Port 8080 conflicts
→ See `QUICKSTART_AL2023.md` troubleshooting section

## 📊 Architecture

```
┌─────────────────────────────────────────────┐
│  GitHub Repository                          │
│  • Push to main triggers deployment         │
└────────────────┬────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────┐
│  GitHub Actions                             │
│  • Builds .env from secrets                 │
│  • Syncs code to EC2                        │
│  • Runs deploy_refresh.sh                   │
└────────────────┬────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────┐
│  EC2 Instance (Amazon Linux 2023)           │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │  Flask Web App (port 8080)          │   │
│  │  • SPA frontend                      │   │
│  │  • ACC API integration              │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │  Flask API Server (port 8080)       │   │
│  │  • Receives updates from Telegram   │   │
│  │  • Updates ACC via API              │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │  Telegram Bot                       │   │
│  │  • Listens for [UPDATE] messages    │   │
│  │  • Parses and validates             │   │
│  │  • Sends to Flask API               │   │
│  └─────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

## 🔒 Security Best Practices

✅ Never commit secrets to git
✅ Use GitHub Secrets for all credentials
✅ Restrict AWS Security Groups
✅ Keep `.env` in `.gitignore`
✅ Use strong random token for `SITE_UPDATES_TOKEN`
✅ Regularly update dependencies
✅ Monitor deployment logs

## 📞 Support & Resources

- **Setup Issues**: Check `GITHUB_ACTIONS_SETUP.md` troubleshooting
- **EC2 Issues**: See `EC2_DEPLOYMENT.md`
- **Python Issues**: See `PYTHON_VERSION_FIX.md`
- **Architecture**: See `CLAUDE.md`

## 🎓 Learning Path

1. **Day 1**: Read `QUICKSTART_AL2023.md` → Deploy manually
2. **Day 2**: Read `GITHUB_ACTIONS_SETUP.md` → Set up automation
3. **Day 3**: Read `CLAUDE.md` → Understand architecture
4. **Day 4**: Test full workflow → Make a code change and push

## 🚦 Current Status

- [x] Codebase documentation (`CLAUDE.md`)
- [x] Manual deployment scripts
- [x] GitHub Actions workflow
- [x] Comprehensive guides
- [x] Python 3.9+ compatibility
- [x] Security hardening
- [ ] Your deployment! (Follow `DEPLOYMENT_CHECKLIST.md`)

---

**Ready to deploy?** Start with `DEPLOYMENT_CHECKLIST.md` and follow along step by step!
