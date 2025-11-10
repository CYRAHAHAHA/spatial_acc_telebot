#!/bin/bash
# status.sh - Check status of all spatial_acc_telebot services

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "==============================================="
echo "spatial_acc_telebot Service Status"
echo "==============================================="

# Check if PID file exists
if [ ! -f "logs/pids.txt" ]; then
    echo "Status: NOT RUNNING (no PID file found)"
    echo ""
    echo "To start services, run: ./start_all.sh"
    exit 0
fi

# Read PIDs from file
PIDS=($(cat logs/pids.txt))

if [ ${#PIDS[@]} -eq 0 ]; then
    echo "Status: NOT RUNNING (empty PID file)"
    rm -f logs/pids.txt
    exit 0
fi

FLASK_WEBAPP_PID=${PIDS[0]:-}
TELEGRAM_BOT_PID=${PIDS[1]:-}

# Function to check process status
check_process() {
    local PID=$1
    local NAME=$2

    if [ -z "$PID" ]; then
        echo "[$NAME] No PID recorded"
        return 1
    fi

    if ps -p $PID > /dev/null 2>&1; then
        # Get process info
        local PROC_INFO=$(ps -p $PID)
        echo "[$NAME] RUNNING (PID: $PID, Uptime: $UPTIME, Memory: $MEM)"
        return 0
    else
        echo "[$NAME] NOT RUNNING (PID $PID is dead)"
        return 1
    fi
}

# Check all processes
RUNNING_COUNT=0

check_process "$FLASK_WEBAPP_PID" "Flask Web App" && ((RUNNING_COUNT++))
check_process "$TELEGRAM_BOT_PID" "Telegram Bot" && ((RUNNING_COUNT++))

echo ""
echo "-----------------------------------------------"
if [ $RUNNING_COUNT -eq 2 ]; then
    echo "Overall Status: ALL SERVICES RUNNING ✓"
elif [ $RUNNING_COUNT -eq 0 ]; then
    echo "Overall Status: ALL SERVICES STOPPED"
    echo "Run ./start_all.sh to start services"
else
    echo "Overall Status: PARTIAL ($RUNNING_COUNT/2 services running) ⚠"
    echo "Consider restarting: ./stop_all.sh && ./start_all.sh"
fi
echo "-----------------------------------------------"
echo ""
echo "Log files:"
echo "  - logs/flask_webapp.log"
echo "  - logs/telegram_bot.log"
echo ""
echo "To view live logs: tail -f logs/*.log"
echo "==============================================="
