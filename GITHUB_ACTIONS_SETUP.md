# GitHub Actions Deployment Setup

This guide explains how to set up automated deployment to your EC2 instance using GitHub Actions.

## Overview

The GitHub Actions workflow automatically:
1. ✅ Deploys code changes when you push to the `main` branch
2. ✅ Syncs files to EC2 using rsync (excludes venv, logs, etc.)
3. ✅ Creates `.env` file from GitHub Secrets
4. ✅ Updates Python dependencies
5. ✅ Restarts all services (Flask Web App, Flask API, Telegram Bot)
6. ✅ Verifies deployment success

## Prerequisites

- GitHub repository with your code
- EC2 instance with SSH access
- SSH key pair for EC2 instance

## Step 1: Prepare Your EC2 Instance

### 1.1 Initial Setup (One-time)

SSH into your EC2 instance and do initial setup:

```bash
# Connect to EC2
ssh -i your-key.pem ec2-user@your-ec2-ip

# Install dependencies
sudo dnf update -y
sudo dnf install -y python3 python3-pip git rsync

# Create deployment directory
mkdir -p /home/ec2-user/spatial_acc_telebot
cd /home/ec2-user/spatial_acc_telebot

# Configure firewall
sudo systemctl start firewalld
sudo firewall-cmd --permanent --add-port=8080/tcp
sudo firewall-cmd --reload
```

### 1.2 Configure SSH Key for GitHub Actions

The SSH key you use to connect to EC2 will be stored in GitHub Secrets.

```bash
# On your LOCAL machine, view your private key
cat your-key.pem

# Copy the entire output (including -----BEGIN/END----- lines)
```

## Step 2: Configure GitHub Secrets

Go to your GitHub repository → Settings → Secrets and variables → Actions → New repository secret

Add the following secrets:

### Required Secrets

| Secret Name | Description | Example Value |
|------------|-------------|---------------|
| `EC2_SSH_KEY` | Private SSH key for EC2 | Contents of your `.pem` file |
| `EC2_HOST` | EC2 public IP or hostname | `ec2-12-34-56-78.compute.amazonaws.com` or `12.34.56.78` |
| `EC2_USER` | EC2 username | `ec2-user` (for Amazon Linux) |
| `EC2_DEPLOY_PATH` | Deployment directory path | `/home/ec2-user/spatial_acc_telebot` |

### Autodesk Configuration Secrets

| Secret Name | Description | Example Value |
|------------|-------------|---------------|
| `AUTODESK_CLIENT_ID` | Your Autodesk client ID | `abc123xyz...` |
| `AUTODESK_CLIENT_SECRET` | Your Autodesk client secret | `xyz789abc...` |
| `AUTODESK_REDIRECT_URI` | OAuth redirect URI | `http://your-ec2-ip:8080/callback` |
| `AUTODESK_SCOPES` | API scopes | `data:read data:write data:create` |
| `AUTODESK_PROJECT_ID` | ACC Project ID | `b.abc123...` |

### Telegram Configuration Secrets

| Secret Name | Description | Example Value |
|------------|-------------|---------------|
| `TELEGRAM_TOKEN` | Telegram bot token | `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz...` |
| `SITE_UPDATES_TOKEN` | API authentication token | `your-secure-random-token-here` |

## Step 3: How to Add Secrets

### Method 1: GitHub Web UI

1. Go to your repository on GitHub
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Enter the secret name (e.g., `EC2_SSH_KEY`)
5. Paste the secret value
6. Click **Add secret**
7. Repeat for all secrets listed above

### Method 2: GitHub CLI

```bash
# Install GitHub CLI if needed
# https://cli.github.com/

# Authenticate
gh auth login

# Add secrets
gh secret set EC2_SSH_KEY < your-key.pem
gh secret set EC2_HOST -b "your-ec2-ip"
gh secret set EC2_USER -b "ec2-user"
gh secret set EC2_DEPLOY_PATH -b "/home/ec2-user/spatial_acc_telebot"
gh secret set TELEGRAM_TOKEN -b "your-telegram-token"
gh secret set SITE_UPDATES_TOKEN -b "your-site-updates-token"
gh secret set AUTODESK_CLIENT_ID -b "your-client-id"
gh secret set AUTODESK_CLIENT_SECRET -b "your-client-secret"
gh secret set AUTODESK_REDIRECT_URI -b "http://your-ec2-ip:8080/callback"
gh secret set AUTODESK_SCOPES -b "data:read data:write data:create"
gh secret set AUTODESK_PROJECT_ID -b "your-project-id"
```

## Step 4: Verify GitHub Actions Workflow

The workflow file is located at `.github/workflows/deploy.yml`

Key features:
- **Triggers**: Runs on push to `main` branch or manual trigger
- **File sync**: Uses rsync to efficiently sync only changed files
- **Excludes**: Automatically excludes venv, logs, cache files
- **Preserves**: Keeps tokens, CSV data, and logs on server
- **Deployment script**: Runs `deploy_refresh.sh` to update and restart services

## Step 5: Test the Deployment

### Option 1: Push to Main Branch

```bash
# Make a small change
echo "# Test deployment" >> README.md

# Commit and push
git add .
git commit -m "Test automated deployment"
git push origin main
```

### Option 2: Manual Trigger

1. Go to GitHub → Actions tab
2. Click **Deploy to EC2** workflow
3. Click **Run workflow** → select `main` branch
4. Click **Run workflow** button

## Step 6: Monitor Deployment

1. Go to **Actions** tab in your GitHub repository
2. Click on the running workflow
3. Watch the deployment steps in real-time
4. Check the "Verify deployment" step to see service status

## Deployment Process Flow

```
┌─────────────────────────────────────────────────────────┐
│ 1. GitHub Actions triggers on push to main             │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│ 2. Checkout code and configure SSH                     │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│ 3. Create .env file from GitHub Secrets                │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│ 4. Rsync files to EC2 (excludes venv, logs, etc.)      │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│ 5. Upload .env file to EC2                             │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│ 6. Run deploy_refresh.sh on EC2:                       │
│    - Load environment variables                         │
│    - Update Python virtual environment                  │
│    - Stop existing services                             │
│    - Start all services                                 │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│ 7. Verify deployment success                           │
└─────────────────────────────────────────────────────────┘
```

## Troubleshooting

### Deployment fails with "Permission denied"

**Issue**: SSH key permissions or authentication failure

**Solution**:
```bash
# Verify EC2_SSH_KEY secret contains the full private key
# Including -----BEGIN RSA PRIVATE KEY----- and -----END RSA PRIVATE KEY-----

# Test SSH connection manually
ssh -i your-key.pem ec2-user@your-ec2-ip
```

### Deployment fails at "rsync"

**Issue**: rsync not installed on EC2

**Solution**:
```bash
# SSH into EC2 and install rsync
sudo dnf install -y rsync
```

### Services don't start after deployment

**Issue**: Environment variables not properly set or Python dependencies missing

**Solution**:
```bash
# SSH into EC2
ssh -i your-key.pem ec2-user@your-ec2-ip

# Navigate to deployment directory
cd /home/ec2-user/spatial_acc_telebot

# Check .env file exists and has correct values
cat .env

# Check logs
tail -f logs/*.log

# Manually run deployment script for debugging
./deploy_refresh.sh
```

### GitHub Actions can't connect to EC2

**Issue**: Security Group or firewall blocking SSH

**Solution**:
1. Check AWS Security Group has SSH (port 22) open for GitHub Actions IPs
2. Or open port 22 to 0.0.0.0/0 (less secure but simpler)
3. Verify firewalld allows SSH:
   ```bash
   sudo firewall-cmd --list-all
   ```

## Security Best Practices

1. ✅ **Never commit secrets** to your repository
2. ✅ **Use GitHub Secrets** for all sensitive data
3. ✅ **Restrict EC2 Security Group** to only necessary ports
4. ✅ **Rotate tokens regularly** (update GitHub Secrets when you do)
5. ✅ **Use deploy keys** with minimal permissions if possible
6. ✅ **Monitor deployment logs** for suspicious activity

## Advanced Configuration

### Deploy to Multiple Environments

Create separate workflows for staging/production:

```yaml
# .github/workflows/deploy-staging.yml
on:
  push:
    branches:
      - develop

# Use different secrets: EC2_HOST_STAGING, etc.
```

### Add Deployment Notifications

Add Slack/Discord notifications on deployment success/failure:

```yaml
- name: Notify on failure
  if: failure()
  run: |
    curl -X POST ${{ secrets.SLACK_WEBHOOK }} \
      -H 'Content-Type: application/json' \
      -d '{"text":"Deployment failed!"}'
```

### Rollback on Failure

Keep previous version and rollback if new deployment fails:

```bash
# In deploy_refresh.sh, add backup logic
cp -r /home/ec2-user/spatial_acc_telebot /home/ec2-user/backup-$(date +%Y%m%d-%H%M%S)
```

## Manual Deployment (Fallback)

If GitHub Actions is down, deploy manually:

```bash
# From your local machine
rsync -avz --exclude 'venv/' --exclude '.git/' \
  -e "ssh -i your-key.pem" \
  ./ ec2-user@your-ec2-ip:/home/ec2-user/spatial_acc_telebot/

# SSH and restart
ssh -i your-key.pem ec2-user@your-ec2-ip
cd /home/ec2-user/spatial_acc_telebot
./stop_all.sh && ./start_all.sh
```

## Next Steps

1. ✅ Set up all GitHub Secrets
2. ✅ Push a test commit to trigger deployment
3. ✅ Monitor the Actions tab for deployment progress
4. ✅ Verify services are running on EC2
5. ✅ Set up monitoring/alerting for production

For more information:
- See `QUICKSTART_AL2023.md` for EC2 setup
- See `EC2_DEPLOYMENT.md` for detailed deployment guide
- See GitHub Actions documentation: https://docs.github.com/en/actions
