#!/bin/bash
# Quick start for AAT services (local, non-Docker)

echo "=== Quick Start AAT Services ==="

# Activate virtual environment
if [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo "Creating virtual environment..."
    python3 -m venv .venv
    source .venv/bin/activate
fi

# Install AAT
pip install -e . -q

# Install dependencies
pip install fastapi uvicorn websockets -q

# Start Cloud Backend
echo "Starting Cloud Backend (port 8000)..."
cd cloud
pip install -r requirements.txt -q
export AWT_SUPABASE_JWT_SECRET="dev-secret"
uvicorn app.main:app --host 0.0.0.0 --port 8000 > /tmp/cloud-backend.log 2>&1 &
BACKEND_PID=$!
cd ..

sleep 3

# Start AAT Dashboard (with correct config path)
echo "Starting AAT Dashboard (port 9500)..."
aat dashboard --host 0.0.0.0 --port 9500 --config .aat/config.yaml > /tmp/aat-dashboard.log 2>&1 &
DASHBOARD_PID=$!

echo ""
echo "=== Services Started ==="
echo "  Cloud Backend:  http://localhost:8000"
echo "  Cloud API Docs: http://localhost:8000/docs"
echo "  AAT Dashboard: http://localhost:9500"
echo ""
echo "Press Ctrl+C to stop"

# Save PIDs for cleanup
echo $BACKEND_PID > /tmp/cloud-backend.pid
echo $DASHBOARD_PID > /tmp/aat-dashboard.pid

# Wait
wait $BACKEND_PID $DASHBOARD_PID
