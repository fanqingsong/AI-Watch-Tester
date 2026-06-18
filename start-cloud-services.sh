#!/bin/bash
# Quick start script for AAT services (non-Docker)

set -e

echo "=== Starting AAT Services ==="

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Install AAT in development mode
echo "Installing AAT..."
pip install -e . --quiet

# Install cloud dependencies
echo "Installing cloud dependencies..."
pip install -r cloud/requirements.txt --quiet

# Install dashboard dependencies
echo "Installing dashboard dependencies..."
pip install fastapi uvicorn websockets --quiet

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "=== Stopping services ==="
    kill $CLOUD_BACKEND_PID 2>/dev/null || true
    kill $DASHBOARD_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    wait
    echo "All services stopped"
}

trap cleanup EXIT INT TERM

# Start Cloud Backend
echo "Starting Cloud Backend on port 8000..."
cd cloud
export AWT_SUPABASE_JWT_SECRET="dev-secret-key"
export AWT_DATABASE_URL="sqlite+aiosqlite:///./awt_cloud.db"
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
CLOUD_BACKEND_PID=$!
cd ..

# Wait for backend to start
sleep 3

# Start AAT Dashboard
echo "Starting AAT Dashboard on port 9500..."
aat dashboard --host 0.0.0.0 --port 9500 &
DASHBOARD_PID=$!

# Wait for dashboard to start
sleep 3

# Start Cloud Frontend (if node_modules exists)
if [ -d "cloud/frontend/node_modules" ]; then
    echo "Starting Cloud Frontend on port 3000..."
    cd cloud/frontend
    export NEXT_PUBLIC_API_URL="http://localhost:8000"
    npm run dev &
    FRONTEND_PID=$!
    cd ..
else
    echo "Frontend dependencies not installed. Run: cd cloud/frontend && npm install"
    FRONTEND_PID=""
fi

echo ""
echo "=== Services Started ==="
echo "  AAT Dashboard:  http://localhost:9500"
echo "  Cloud Backend:  http://localhost:8000"
echo "  Cloud API Docs: http://localhost:8000/docs"
if [ -n "$FRONTEND_PID" ]; then
    echo "  Cloud Frontend: http://localhost:3000"
fi
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for any process to exit
wait
