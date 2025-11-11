# EC2 Deployment Guide

This guide walks you through deploying the spatial_acc_telebot application on an AWS EC2 instance.

## Prerequisites

- AWS EC2 instance (Amazon Linux 2023 recommended)
- Python 3.9 or newer installed (Python 3.11+ recommended)
- SSH access to the EC2 instance
- Autodesk API credentials
- Telegram Bot Token

## Step 1: Launch and Configure EC2 Instance

1. Launch an EC2 instance with the following specifications:

   - **Instance Type**: t2.small or larger (minimum 2GB RAM)
   - **OS**: Amazon Linux 2023, Ubuntu 22.04 LTS, or Amazon Linux 2
   - **Storage**: 20GB minimum
   - **Security Group**: Open ports 8080 (or configure behind reverse proxy)

2. SSH into your instance:

   ```bash
   # For Amazon Linux
   ssh -i your-key.pem ec2-user@your-ec2-ip

   # For Ubuntu
   ssh -i your-key.pem ubuntu@your-ec2-ip
   ```

## Step 2: Install Dependencies

### For Amazon Linux 2023 (recommended):

**Option A: Python 3.9 (default)**

```bash
sudo dnf update -y
sudo dnf install -y python3 python3-pip git
python3 --version  # Verify Python 3.9.x
```

**Option B: Python 3.11 (recommended for better performance)**

```bash
sudo dnf update -y
sudo dnf install -y python3.11 python3.11-pip git
sudo alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
sudo alternatives --set python3 /usr/bin/python3.11
python3 --version  # Verify Python 3.11.x
```

### For Ubuntu/Debian:

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git
```

### For Amazon Linux 2:

```bash
sudo yum update -y
sudo yum install -y python3 python3-pip git
```

## Step 3: Clone Repository

```bash
# For Amazon Linux
cd /home/ec2-user
git clone https://github.com/your-repo/spatial_acc_telebot.git
cd spatial_acc_telebot

# For Ubuntu
cd /home/ubuntu
git clone https://github.com/your-repo/spatial_acc_telebot.git
cd spatial_acc_telebot
```

Or upload files using SCP:

```bash
# From your local machine (Amazon Linux)
scp -i your-key.pem -r /path/to/spatial_acc_telebot ec2-user@your-ec2-ip:/home/ec2-user/

# From your local machine (Ubuntu)
scp -i your-key.pem -r /path/to/spatial_acc_telebot ubuntu@your-ec2-ip:/home/ubuntu/
```

## Step 4: Set Up Python Virtual Environment

```bash
python3 -m venv .venv
source .venv/Scripts/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## Step 5: Configure Environment Variables

1. Create the `.env` file:

   ```bash
   nano root/.env
   ```

2. Add your configuration:

   ```
   YR_CLIENT_ID=your_autodesk_client_id
   YR_CLIENT_SECRET=your_autodesk_client_secret
   YR_REDIRECT_URI=http://your-ec2-public-ip:8080/callback
   YR_SCOPES=data:read data:write data:create
   YR_PROJECT_ID=your_acc_project_id
   ```

3. Set environment variables for the session:

   ```bash
   export TELEGRAM_TOKEN="your_telegram_bot_token"
   export SITE_UPDATES_TOKEN="super-secret-token"  # Change this to a secure token
   export FLASK_BASE="http://localhost:8080"
   ```

4. To persist environment variables, add them to `~/.bashrc`:
   ```bash
   echo 'export TELEGRAM_TOKEN="your_telegram_bot_token"' >> ~/.bashrc
   echo 'export SITE_UPDATES_TOKEN="super-secret-token"' >> ~/.bashrc
   echo 'export FLASK_BASE="http://localhost:8080"' >> ~/.bashrc
   source ~/.bashrc
   ```

## Step 6: Test the Application

Run the services manually first to ensure everything works:

```bash
# Make scripts executable (should already be done)
chmod +x start_all.sh stop_all.sh status.sh

# Start all services
./start_all.sh

# Check status
./status.sh

# View logs
tail -f logs/*.log
```

## Step 7: Set Up Systemd Service (Production)

For production deployments, use systemd to manage services and auto-restart on failure/reboot.

1. Copy the service file:

   ```bash
   sudo cp spatial_acc_telebot.service /etc/systemd/system/
   ```

2. Edit the service file with your paths and credentials:

   ```bash
   sudo nano /etc/systemd/system/spatial_acc_telebot.service
   ```

   Update the following fields:

   - `User=ec2-user` (or `ubuntu` for Ubuntu)
   - `Group=ec2-user` (or `ubuntu` for Ubuntu)
   - `WorkingDirectory=/home/ec2-user/spatial_acc_telebot` (adjust path as needed)
   - `Environment="TELEGRAM_TOKEN=your_actual_token"`
   - Update paths in `ExecStart` and `ExecStop` to match your installation directory

3. Enable and start the service:

   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable spatial_acc_telebot
   sudo systemctl start spatial_acc_telebot
   ```

4. Check service status:

   ```bash
   sudo systemctl status spatial_acc_telebot
   ```

5. View logs:

   ```bash
   # Live logs
   sudo journalctl -u spatial_acc_telebot -f

   # Recent logs
   sudo journalctl -u spatial_acc_telebot -n 100
   ```

## Step 8: Configure Firewall

### Amazon Linux 2023/Amazon Linux 2 (firewalld):

```bash
# Check if firewalld is running
sudo systemctl status firewalld

# If not running, start and enable it
sudo systemctl start firewalld
sudo systemctl enable firewalld

# Add port 8080
sudo firewall-cmd --permanent --add-port=8080/tcp
sudo firewall-cmd --reload

# Verify the rule was added
sudo firewall-cmd --list-ports
```

### Ubuntu (UFW):

```bash
sudo ufw allow 8080/tcp
sudo ufw enable
```

### AWS Security Group (Required for all):

Add an inbound rule in your EC2 Security Group:

- Type: Custom TCP
- Port: 8080
- Source: Your IP or 0.0.0.0/0 (for public access)
- Description: Spatial ACC Telebot Web Interface

## Step 9: OAuth Authentication

1. Visit `http://your-ec2-public-ip:8080/authorize` in your browser
2. Log in with your Autodesk account and grant permissions
3. Tokens will be saved to `root/autodesk_tokens.json`

## Step 10: Fetch Initial Data

```bash
# Fetch ACC configuration (creates CSVs)
curl http://localhost:8080/fetch_assets_config

# Fetch all assets (creates assets_total.csv with GUIDs)
curl http://localhost:8080/fetch_all_assets_info
```

## Management Commands

```bash
# Start all services
./start_all.sh

# Stop all services
./stop_all.sh

# Check status
./status.sh

# View logs
tail -f logs/*.log

# Restart services
./stop_all.sh && ./start_all.sh
```

## Troubleshooting

### Services won't start

- Check environment variables: `echo $TELEGRAM_TOKEN`
- Verify `.env` file exists: `ls -la root/.env`
- Check Python dependencies: `pip list`
- View error logs: `cat logs/*.log`

### Port 8080 conflicts

Both Flask Web App and Flask API try to use port 8080. This is intentional - they serve different purposes:

- **Flask Web App** (`root/main.py`): Serves the SPA and ACC integration endpoints
- **Flask API** (`telebot/flask_api.py`): Receives updates from Telegram bot

If you get a port conflict, modify one of them:

1. Edit `telebot/flask_api.py`, change line: `app.run(host="0.0.0.0", port=8081, debug=True)`
2. Update `FLASK_BASE` env var: `export FLASK_BASE="http://localhost:8081"`

### Telegram bot not receiving messages

- Verify bot is added to the group
- Check bot has permission to read messages
- Ensure `TELEGRAM_TOKEN` is set correctly
- View bot logs: `tail -f logs/telegram_bot.log`

### ACC API calls failing

- Check token validity: `curl http://localhost:8080/api/status`
- Re-authenticate if needed: Visit `/authorize`
- Verify project_id is correct in `.env`
- Check CSV files exist: `ls -la root/data/*.csv`

## Nginx Reverse Proxy (Optional)

For production, use Nginx as a reverse proxy:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Auto-Start on Reboot

If using the bash scripts (not systemd), add to crontab:

```bash
crontab -e

# Add this line:
@reboot cd /home/ubuntu/spatial_acc_telebot && /home/ubuntu/spatial_acc_telebot/start_all.sh
```

## Monitoring

Set up basic monitoring:

```bash
# Add to crontab to check status every 5 minutes
*/5 * * * * /home/ubuntu/spatial_acc_telebot/status.sh >> /home/ubuntu/spatial_acc_telebot/logs/monitor.log 2>&1
```

## Backup Important Files

Regularly backup:

- `root/.env` (credentials)
- `root/autodesk_tokens.json` (auth tokens)
- `root/data/*.csv` (cached ACC data)
- `telebot/site_updates.json` (update history)
- `telebot/logs/log_message.jsonl` (message log)

## Security Recommendations

1. **Change default tokens**: Update `SITE_UPDATES_TOKEN` to a strong random value
2. **Restrict access**: Use Security Groups to limit access to port 8080
3. **Use HTTPS**: Set up SSL/TLS with Let's Encrypt
4. **Secure .env**: `chmod 600 root/.env`
5. **Regular updates**: Keep packages updated with `apt update && apt upgrade`
6. **Monitor logs**: Set up log rotation and monitoring
