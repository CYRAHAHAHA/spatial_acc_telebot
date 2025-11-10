#!/bin/bash
# start_all.sh - Start all three components of the spatial_acc_telebot application

# Exit on error
set -e

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Create logs directory if it doesn't exist
mkdir -p logs


# Load repo-level .env
ENV_FILE=".env"
if [ ! -f "$ENV_FILE" ]; then
    echo "ERROR: $ENV_FILE file not found!"
    echo "Please create $ENV_FILE with your Autodesk credentials and bot tokens."
    exit 1
fi

echo "Loading environment variables from $ENV_FILE"
set -a
source "$ENV_FILE"
echo "==============================================="
set +a

# Check if TELEGRAM_TOKEN is set
if [ -z "$TELEGRAM_TOKEN" ]; then
    echo "ERROR: TELEGRAM_TOKEN environment variable not set!"
    echo "Please export TELEGRAM_TOKEN before running this script"
    exit 1
fi

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo "Activating virtual environment..."
    source .venv/Scripts/activate
else
    echo "WARNING: No virtual environment found at ./.venv"
    echo "It's recommended to create one with: python -m venv .venv"
fi

# Check if PID file exists (indicating services might already be running)
if [ -f "logs/pids.txt" ]; then
    echo "WARNING: PID file exists. Services might already be running."
    echo "Run ./stop_all.sh first to stop existing services."
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "==============================================="
echo "Starting spatial_acc_telebot services..."
echo "==============================================="

# Start Flask Web App (root/main.py)
echo "[1/2] Starting Flask Web App and API Server on port 8080..."
cd "$SCRIPT_DIR/root"
nohup python main.py > "$SCRIPT_DIR/logs/flask_webapp.log" 2>&1 &
FLASK_WEBAPP_PID=$!
echo "  → PID: $FLASK_WEBAPP_PID"
cd "$SCRIPT_DIR"

# Wait a bit for Flask to start
sleep 2

# Start Telegram Bot (telebot/bot_logger.py)
echo "[2/2] Starting Telegram Bot..."
cd "$SCRIPT_DIR/telebot"
nohup python bot_logger.py > "$SCRIPT_DIR/logs/telegram_bot.log" 2>&1 &
TELEGRAM_BOT_PID=$!
echo "  → PID: $TELEGRAM_BOT_PID"
cd "$SCRIPT_DIR"

# Save PIDs to file for stop script
echo "$FLASK_WEBAPP_PID" > logs/pids.txt
echo "$TELEGRAM_BOT_PID" >> logs/pids.txt

echo ""
echo "==============================================="
echo "All services started successfully!"
echo "==============================================="
echo "Flask Web App:    PID $FLASK_WEBAPP_PID (http://localhost:8080)"
echo "Telegram Bot:     PID $TELEGRAM_BOT_PID"
echo ""
echo "Log files:"
echo "  - logs/flask_webapp.log"
echo "  - logs/telegram_bot.log"
echo ""
echo "To stop all services, run: ./stop_all.sh"
echo "To check status, run: ./status.sh"
echo "To view logs, run: tail -f logs/*.log"
# print the link for localhost 8080
echo "Access the Flask Web App at: http://localhost:8080"
echo "==============================================="

