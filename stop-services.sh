#!/bin/bash
# Stop AAT services

echo "=== 停止 AAT 服务 ==="

# Stop Cloud Backend
if [ -f /tmp/cloud-backend.pid ]; then
    kill $(cat /tmp/cloud-backend.pid) 2>/dev/null && echo "✓ Cloud Backend 已停止"
    rm /tmp/cloud-backend.pid
fi

# Stop AAT Dashboard
if [ -f /tmp/aat-dashboard.pid ]; then
    kill $(cat /tmp/aat-dashboard.pid) 2>/dev/null && echo "✓ AAT Dashboard 已停止"
    rm /tmp/aat-dashboard.pid
fi

# Cleanup any remaining processes on ports
pkill -f "uvicorn app.main:app" 2>/dev/null
pkill -f "aat dashboard" 2>/dev/null

echo "=== 所有服务已停止 ==="
