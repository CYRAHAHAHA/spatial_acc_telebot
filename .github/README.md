# GitHub Actions Configuration

This directory contains GitHub Actions workflows and templates for automated deployment.

## Files

### `workflows/deploy.yml`
Main deployment workflow that automatically deploys to EC2 when you push to the `main` branch.

**Triggers:**
- Push to `main` branch
- Manual trigger via GitHub Actions UI

**What it does:**
1. Checks out code
2. Configures SSH connection to EC2
3. Creates `.env` file from GitHub Secrets
4. Syncs files to EC2 using rsync
5. Runs `deploy_refresh.sh` on EC2 to restart services
6. Verifies deployment success

### `secrets.template`
Template showing all required GitHub Secrets for the deployment workflow.

**Copy this file and fill in your values, then add to GitHub Secrets.**

### `PULL_REQUEST_TEMPLATE.md`
Template for pull requests to ensure consistent PR descriptions and checklists.

## Quick Setup

### 1. Add GitHub Secrets

Go to: **Repository Settings → Secrets and variables → Actions → New repository secret**

Required secrets:
```
EC2_SSH_KEY          - Your EC2 private key (.pem file contents)
EC2_HOST             - EC2 public IP or hostname
EC2_USER             - ec2-user (for Amazon Linux)
EC2_DEPLOY_PATH      - /home/ec2-user/spatial_acc_telebot
TELEGRAM_TOKEN       - Your Telegram bot token
SITE_UPDATES_TOKEN   - Secure random token for API
AUTODESK_CLIENT_ID   - Autodesk client ID
AUTODESK_CLIENT_SECRET - Autodesk client secret
AUTODESK_REDIRECT_URI - http://your-ec2-ip:8080/callback
AUTODESK_SCOPES      - data:read data:write data:create
AUTODESK_PROJECT_ID  - Your ACC project ID
```

### 2. Prepare EC2 Instance

SSH into EC2 and run initial setup:
```bash
sudo dnf update -y
sudo dnf install -y python3 python3-pip git rsync
mkdir -p /home/ec2-user/spatial_acc_telebot
sudo firewall-cmd --permanent --add-port=8080/tcp
sudo firewall-cmd --reload
```

### 3. Test Deployment

**Option A: Push to main**
```bash
git add .
git commit -m "Test deployment"
git push origin main
```

**Option B: Manual trigger**
1. Go to **Actions** tab
2. Select **Deploy to EC2** workflow
3. Click **Run workflow**

### 4. Monitor Deployment

Go to **Actions** tab → Click on running workflow → Watch logs in real-time

## Deployment Exclusions

The rsync deployment excludes these files/directories (they persist on the server):
- `venv/` - Python virtual environment
- `.git/` - Git repository
- `logs/` - Log files
- `__pycache__/` - Python cache
- `root/autodesk_tokens.json` - Autodesk OAuth tokens
- `telebot/autodesk_tokens.json` - Telegram bot tokens
- `telebot/site_updates.json` - Update history
- `root/data/*.csv` - Generated CSV files

These are preserved across deployments to maintain state.

## Troubleshooting

### Deployment fails with SSH error
- Verify `EC2_SSH_KEY` secret contains the full private key (including BEGIN/END lines)
- Check EC2 Security Group allows SSH (port 22)

### Services don't start after deployment
- Check logs in the workflow's "Run deployment script" step
- SSH to EC2 and run `./status.sh` to see service status
- Check `logs/*.log` files for errors

### Environment variables not set
- Verify all required secrets are added in GitHub
- Check the "Create .env file" step in workflow logs

## Security Notes

- ✅ Never commit the `.env` file (it's in `.gitignore`)
- ✅ Never commit SSH keys or credentials
- ✅ All secrets are stored in GitHub Secrets (encrypted)
- ✅ The `.env` file is created dynamically during deployment
- ✅ Sensitive files are excluded from rsync sync

## Further Documentation

- **`GITHUB_ACTIONS_SETUP.md`** - Complete setup guide
- **`EC2_DEPLOYMENT.md`** - Manual EC2 deployment guide
- **`QUICKSTART_AL2023.md`** - Amazon Linux 2023 quick start

## Workflow Diagram

```
┌──────────────────────┐
│  Push to main        │
└──────────┬───────────┘
           │
┌──────────▼───────────┐
│  Checkout code       │
└──────────┬───────────┘
           │
┌──────────▼───────────┐
│  Configure SSH       │
└──────────┬───────────┘
           │
┌──────────▼───────────┐
│  Create .env from    │
│  GitHub Secrets      │
└──────────┬───────────┘
           │
┌──────────▼───────────┐
│  Rsync to EC2        │
│  (exclude venv, etc) │
└──────────┬───────────┘
           │
┌──────────▼───────────┐
│  Run deploy_refresh  │
│  - Update deps       │
│  - Stop services     │
│  - Start services    │
└──────────┬───────────┘
           │
┌──────────▼───────────┐
│  Verify deployment   │
│  Check status        │
└──────────────────────┘
```
