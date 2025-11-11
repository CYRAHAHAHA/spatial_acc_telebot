#!/bin/bash
# stop_all.sh - Stop all running components of the spatial_acc_telebot application

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "==============================================="
echo "Stopping spatial_acc_telebot services..."
echo "==============================================="

# Check if PID file exists
if [ ! -f "logs/pids.txt" ]; then
    echo "No PID file found. Services might not be running."
    exit 0
fi

# Read PIDs from file
PIDS=($(cat logs/pids.txt))

if [ ${#PIDS[@]} -eq 0 ]; then
    echo "No PIDs found in file."
    rm -f logs/pids.txt
    exit 0
fi

FLASK_WEBAPP_PID=${PIDS[0]:-}
TELEGRAM_BOT_PID=${PIDS[1]:-}

# Function to stop a process gracefully
stop_process() {
    local PID=$1
    local NAME=$2

    if [ -z "$PID" ]; then
        echo "[$NAME] No PID found, skipping..."
        return
    fi

    if ps -p $PID > /dev/null 2>&1; then
        echo "[$NAME] Stopping process $PID..."
        kill $PID

        # Wait up to 10 seconds for graceful shutdown
        for i in {1..10}; do
            if ! ps -p $PID > /dev/null 2>&1; then
                echo "[$NAME] Stopped successfully"
                return
            fi
            sleep 1
        done

        # Force kill if still running
        if ps -p $PID > /dev/null 2>&1; then
            echo "[$NAME] Force killing process $PID..."
            kill -9 $PID
            echo "[$NAME] Force stopped"
        fi
    else
        echo "[$NAME] Process $PID not running"
    fi
}

# Stop all processes
stop_process "$FLASK_WEBAPP_PID" "Flask Web App"
stop_process "$TELEGRAM_BOT_PID" "Telegram Bot"

# Remove PID file
rm -f logs/pids.txt

echo ""
echo "==============================================="
echo "All services stopped"
echo "==============================================="
