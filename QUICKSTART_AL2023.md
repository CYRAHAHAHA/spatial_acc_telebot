# Quick Start Guide - Amazon Linux 2023

This is a streamlined guide for deploying on Amazon Linux 2023 EC2 instances.

## Prerequisites

- Amazon Linux 2023 EC2 instance (t2.small or larger)
- Python 3.9+ (included by default)
- SSH key pair for access
- Autodesk API credentials
- Telegram Bot Token

## Step-by-Step Deployment

### 1. Connect to EC2

```bash
ssh -i your-key.pem ec2-user@your-ec2-ip
```

### 2. Install Dependencies

**Option A: Use Python 3.9 (default on AL2023)**

```bash
sudo dnf update -y
sudo dnf install -y python3 python3-pip git

# Verify Python version
python3 --version  # Should show Python 3.9.x
```

**Option B: Install Python 3.11 (recommended for latest features)**

```bash
sudo dnf update -y
sudo dnf install -y python3.11 python3.11-pip git

# Set Python 3.11 as default
sudo alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
sudo alternatives --set python3 /usr/bin/python3.11

# Verify
python3 --version  # Should show Python 3.11.x
```

> **Note**: The requirements.txt has been configured to work with Python 3.9+. Both options will work.

### 3. Upload or Clone Repository

```bash
# Option A: Clone from git
cd /home/ec2-user
git clone https://github.com/your-repo/spatial_acc_telebot.git
cd spatial_acc_telebot

# Option B: Upload via SCP (from local machine)
# scp -i your-key.pem -r /path/to/spatial_acc_telebot ec2-user@your-ec2-ip:/home/ec2-user/
```

### 4. Set Up Virtual Environment

```bash
python3 -m venv .venv
source .venv/Scripts/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Configure Environment

```bash
# Create .env file in root directory
nano root/.env
```

Add your Autodesk credentials:

```
YR_CLIENT_ID=your_autodesk_client_id
YR_CLIENT_SECRET=your_autodesk_client_secret
YR_REDIRECT_URI=http://your-ec2-public-ip:8080/callback
YR_SCOPES=data:read data:write data:create
YR_PROJECT_ID=your_acc_project_id
```

Save and exit (Ctrl+X, Y, Enter)

### 6. Set Environment Variables

```bash
# Set for current session
export TELEGRAM_TOKEN="your_telegram_bot_token"
export SITE_UPDATES_TOKEN="your-secret-token-here"
export FLASK_BASE="http://localhost:8080"

# Make persistent across reboots
echo 'export TELEGRAM_TOKEN="your_telegram_bot_token"' >> ~/.bashrc
echo 'export SITE_UPDATES_TOKEN="your-secret-token-here"' >> ~/.bashrc
echo 'export FLASK_BASE="http://localhost:8080"' >> ~/.bashrc
source ~/.bashrc
```

### 7. Configure Firewall

```bash
# Start firewalld
sudo systemctl start firewalld
sudo systemctl enable firewalld

# Open port 8080
sudo firewall-cmd --permanent --add-port=8080/tcp
sudo firewall-cmd --reload

# Verify
sudo firewall-cmd --list-ports
```

**Don't forget**: Also add port 8080 to your AWS Security Group inbound rules!

### 8. Start Services

```bash
# Make scripts executable (should already be done)
chmod +x start_all.sh stop_all.sh status.sh

# Start all services
./start_all.sh
```

### 9. Verify Services are Running

```bash
# Check status
./status.sh

# View logs
tail -f logs/*.log

# Or check individual log files
tail -f logs/flask_webapp.log
tail -f logs/flask_api.log
tail -f logs/telegram_bot.log
```

### 10. Authenticate with Autodesk

Open your browser and visit:

```
http://your-ec2-public-ip:8080/authorize
```

Log in with your Autodesk account to authorize the app.

### 11. Fetch Initial Data

```bash
# Fetch ACC configuration (creates CSVs)
curl http://localhost:8080/fetch_assets_config

# Fetch all assets (creates assets_total.csv with GUIDs)
curl http://localhost:8080/fetch_all_assets_info
```

### 12. Test Telegram Integration

Send a test message in your Telegram group:

```
[UPDATE]
Location: Building A, Level 3
Zone / Grid / Area: Grid 5-7, East Wing
Task: Internal Partition Walls
Status: Completed
Remarks: Ready for inspection
GUID: 12345678-1234-1234-1234-123456789012
```

Check the logs to verify it was processed:

```bash
tail -f logs/telegram_bot.log
cat telebot/site_updates.json
```

## Common Commands

```bash
# Start services
./start_all.sh

# Stop services
./stop_all.sh

# Check status
./status.sh

# View all logs
tail -f logs/*.log

# Restart services
./stop_all.sh && ./start_all.sh

# Check if processes are running
ps aux | grep python
```

## Production Setup (Optional but Recommended)

For auto-restart and running on boot, set up systemd:

```bash
# Edit service file with your credentials
nano spatial_acc_telebot.service

# Update these values:
# - User=ec2-user
# - WorkingDirectory=/home/ec2-user/spatial_acc_telebot
# - Environment="TELEGRAM_TOKEN=your_actual_token"

# Install service
sudo cp spatial_acc_telebot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable spatial_acc_telebot
sudo systemctl start spatial_acc_telebot

# Check status
sudo systemctl status spatial_acc_telebot

# View logs
sudo journalctl -u spatial_acc_telebot -f
```

## Troubleshooting

### Python version errors during pip install

If you see errors like:

```
ERROR: Could not find a version that satisfies the requirement click==8.3.0
ERROR: Ignored the following versions that require a different python version
```

**Solution**: Your Python version is too old. Check version and upgrade:

```bash
# Check current version
python3 --version

# If less than 3.9, install Python 3.11
sudo dnf install -y python3.11 python3.11-pip
sudo alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
sudo alternatives --set python3 /usr/bin/python3.11

# Verify
python3 --version

# Recreate virtual environment
deactivate  # if already in venv
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Port 8080 already in use

```bash
# Find process using port 8080
sudo lsof -i :8080

# Kill if needed
sudo kill -9 <PID>
```

### Services not starting

```bash
# Check environment variables
echo $TELEGRAM_TOKEN
echo $SITE_UPDATES_TOKEN

# Check .env file
cat root/.env

# Check Python and dependencies
python3 --version
pip list
```

### Can't access from browser

```bash
# Check AWS Security Group has port 8080 open
# Check firewall
sudo firewall-cmd --list-ports

# Check if service is listening
sudo netstat -tulpn | grep 8080
# or
sudo ss -tulpn | grep 8080
```

### Telegram bot not responding

```bash
# Check bot logs
tail -f logs/telegram_bot.log

# Verify token
echo $TELEGRAM_TOKEN

# Restart bot specifically
./stop_all.sh
./start_all.sh
```

## File Locations

- **Configuration**: `root/.env`
- **Tokens**: `root/autodesk_tokens.json`, `telebot/autodesk_tokens.json`
- **Logs**: `logs/` directory
- **CSV Data**: `root/data/` directory
- **Telegram Updates**: `telebot/site_updates.json`
- **Message Log**: `telebot/logs/log_message.jsonl`

## Security Checklist

- ✅ Changed `SITE_UPDATES_TOKEN` from default value
- ✅ Added AWS Security Group rule for port 8080 (restricted to your IP if possible)
- ✅ Configured firewalld
- ✅ Set proper permissions on .env file: `chmod 600 root/.env`
- ✅ Never commit tokens or credentials to git
- ✅ Consider setting up HTTPS/SSL for production use

## Next Steps

1. Set up a proper domain name and SSL certificate (Let's Encrypt)
2. Configure Nginx as reverse proxy
3. Set up log rotation
4. Configure automated backups
5. Set up monitoring/alerting

For detailed instructions, see `EC2_DEPLOYMENT.md`.
