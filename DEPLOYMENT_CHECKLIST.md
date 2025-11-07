# Deployment Checklist

Use this checklist to ensure everything is properly configured for automated deployment.

## ✅ Prerequisites

- [ ] AWS EC2 instance launched (Amazon Linux 2023 recommended)
- [ ] EC2 instance has public IP address
- [ ] SSH key pair for EC2 access (`.pem` file)
- [ ] GitHub repository created
- [ ] Autodesk API credentials obtained
- [ ] Telegram bot created and token obtained

## ✅ EC2 Instance Setup

- [ ] SSH access verified: `ssh -i your-key.pem ec2-user@your-ec2-ip`
- [ ] System updated: `sudo dnf update -y`
- [ ] Dependencies installed: `sudo dnf install -y python3 python3-pip git rsync`
- [ ] Python version verified: `python3 --version` (should be 3.9+)
- [ ] Deployment directory created: `mkdir -p /home/ec2-user/spatial_acc_telebot`
- [ ] Firewall configured:
  - [ ] Port 8080 opened: `sudo firewall-cmd --permanent --add-port=8080/tcp`
  - [ ] Firewall reloaded: `sudo firewall-cmd --reload`
- [ ] AWS Security Group configured:
  - [ ] Port 22 (SSH) - for GitHub Actions
  - [ ] Port 8080 (HTTP) - for web access

## ✅ GitHub Repository Setup

- [ ] Code pushed to GitHub
- [ ] `.github/workflows/deploy.yml` exists in repository
- [ ] `.gitignore` properly configured (no secrets in repo)
- [ ] Repository secrets configured (see below)

## ✅ GitHub Secrets Configuration

Go to: **Settings → Secrets and variables → Actions → New repository secret**

### EC2 Connection
- [ ] `EC2_SSH_KEY` - Contents of your `.pem` file
- [ ] `EC2_HOST` - EC2 public IP or hostname
- [ ] `EC2_USER` - `ec2-user`
- [ ] `EC2_DEPLOY_PATH` - `/home/ec2-user/spatial_acc_telebot`

### Autodesk Configuration
- [ ] `AUTODESK_CLIENT_ID` - Your Autodesk client ID
- [ ] `AUTODESK_CLIENT_SECRET` - Your Autodesk client secret
- [ ] `AUTODESK_REDIRECT_URI` - `http://your-ec2-ip:8080/callback`
- [ ] `AUTODESK_SCOPES` - `data:read data:write data:create`
- [ ] `AUTODESK_PROJECT_ID` - Your ACC project ID

### Telegram Configuration
- [ ] `TELEGRAM_TOKEN` - Your Telegram bot token
- [ ] `SITE_UPDATES_TOKEN` - Secure random token (generate: `openssl rand -hex 32`)

## ✅ First Deployment

- [ ] Push to main branch or manually trigger workflow
- [ ] Go to **Actions** tab in GitHub
- [ ] Watch deployment workflow progress
- [ ] Verify all steps complete successfully
- [ ] SSH to EC2 and check: `./status.sh`
- [ ] Verify all 3 services are running:
  - [ ] Flask Web App
  - [ ] Flask API Server
  - [ ] Telegram Bot

## ✅ Post-Deployment Verification

- [ ] Web UI accessible: `http://your-ec2-ip:8080`
- [ ] API status endpoint works: `http://your-ec2-ip:8080/api/status`
- [ ] OAuth authentication: Visit `http://your-ec2-ip:8080/authorize` and complete login
- [ ] Tokens saved: Check `root/autodesk_tokens.json` exists on EC2
- [ ] Fetch ACC config: `curl http://localhost:8080/fetch_assets_config`
- [ ] Fetch assets: `curl http://localhost:8080/fetch_all_assets_info`
- [ ] CSV files generated: Check `root/data/*.csv` exists
- [ ] Telegram bot responding: Send test message to group
- [ ] Logs accessible: `tail -f logs/*.log`

## ✅ Telegram Bot Integration

- [ ] Bot added to Telegram group
- [ ] Bot has permission to read messages
- [ ] Test message sent with `[UPDATE]` format
- [ ] Bot responds with "Update logged" or error message
- [ ] Update logged to `telebot/logs/log_message.jsonl`
- [ ] If GUID provided, update sent to Flask API
- [ ] Status updated in ACC (check ACC web interface)

## ✅ Optional Enhancements

- [ ] Set up systemd service for auto-start on reboot
- [ ] Configure Nginx reverse proxy for SSL/HTTPS
- [ ] Set up domain name (Route 53 or other DNS)
- [ ] Configure SSL certificate (Let's Encrypt)
- [ ] Set up log rotation
- [ ] Configure monitoring/alerting
- [ ] Set up automated backups
- [ ] Create staging environment
- [ ] Add deployment notifications (Slack/Discord)

## ✅ Security Hardening

- [ ] Changed `SITE_UPDATES_TOKEN` from default value
- [ ] SSH key permissions: `chmod 600 your-key.pem`
- [ ] `.env` file permissions on EC2: `chmod 600 .env`
- [ ] AWS Security Group restricted (not open to 0.0.0.0/0 if possible)
- [ ] Regular security updates enabled: `sudo dnf update -y` (cron job)
- [ ] Firewall enabled and configured
- [ ] No secrets in git repository (verify with `git log -p`)
- [ ] GitHub Secrets properly configured (not accessible in logs)

## Troubleshooting Commands

If something doesn't work, run these commands on EC2:

```bash
# Check if services are running
./status.sh

# View logs
tail -f logs/*.log

# Check environment variables
cat .env

# Check Python dependencies
source venv/bin/activate
pip list

# Manually restart services
./stop_all.sh && ./start_all.sh

# Check network
sudo netstat -tulpn | grep 8080
curl http://localhost:8080/api/status

# Check firewall
sudo firewall-cmd --list-all

# View systemd logs (if using systemd)
sudo journalctl -u spatial_acc_telebot -f
```

## Quick Reference Links

- **GitHub Actions Setup**: `GITHUB_ACTIONS_SETUP.md`
- **EC2 Deployment**: `EC2_DEPLOYMENT.md`
- **Amazon Linux 2023 Quick Start**: `QUICKSTART_AL2023.md`
- **Python Version Fix**: `PYTHON_VERSION_FIX.md`
- **Architecture Overview**: `CLAUDE.md`

## Support

If you encounter issues:
1. Check the troubleshooting section in `GITHUB_ACTIONS_SETUP.md`
2. Review GitHub Actions workflow logs
3. Check EC2 service logs: `logs/*.log`
4. Verify all secrets are correctly configured
5. Test SSH connection manually: `ssh -i your-key.pem ec2-user@your-ec2-ip`

---

**Last Updated**: $(date)
**Deployment Status**: [ ] Not Started | [ ] In Progress | [ ] Complete
