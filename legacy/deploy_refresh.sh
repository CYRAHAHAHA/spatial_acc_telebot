#!/bin/bash
# deploy_refresh.sh - Refresh application after deployment from GitHub Actions

set -e

echo "========================================"
echo "Starting deployment refresh..."
echo "========================================"

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "[1/5] Checking environment..."

# Load environment variables from .env
if [ -f ".env" ]; then
    echo "  ✓ Loading .env file"
    set -a
    source .env
    set +a
else
    echo "  ✗ ERROR: .env file not found!"
    exit 1
fi

# Verify critical environment variables
if [ -z "$TELEGRAM_TOKEN" ]; then
    echo "  ✗ ERROR: TELEGRAM_TOKEN not set!"
    exit 1
fi
echo "  ✓ TELEGRAM_TOKEN is set"

echo "[2/5] Setting up Python virtual environment..."

# Check if venv exists
if [ -d ".venv" ]; then
    echo "  ✓ Virtual environment exists"
else
    echo "  → Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate venv
source .venv/Scripts/activate

# Upgrade pip and install/update dependencies
echo "  → Updating dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

echo "  ✓ Dependencies updated"

echo "[3/5] Stopping existing services..."

# Stop existing services if running
if [ -f "logs/pids.txt" ]; then
    ./stop_all.sh
    echo "  ✓ Stopped existing services"
else
    echo "  → No running services found"
fi

# Wait a moment for services to fully stop
sleep 2

echo "[4/5] Starting services..."

# Start all services
./start_all.sh

echo "[5/5] Verifying deployment..."

# Wait for services to start
sleep 3

# Check status
./status.sh

echo ""
echo "========================================"
echo "Deployment refresh complete!"
echo "========================================"
echo ""
echo "Next steps:"
echo "1. Verify services: ./status.sh"
echo "2. View logs: tail -f logs/*.log"
echo "3. Test endpoints:"
echo "   - Web UI: http://your-server:8080"
echo "   - API Status: http://your-server:8080/api/status"
echo "========================================"
