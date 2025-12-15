#!/bin/bash

echo "Stopping AWS Migration Business Case Generator..."

# Kill backend (Gunicorn)
if [ -f .pids/backend.pid ]; then
    BACKEND_PID=$(cat .pids/backend.pid)
    if ps -p $BACKEND_PID > /dev/null 2>&1; then
        echo "Stopping Gunicorn master process (PID: $BACKEND_PID)..."
        kill $BACKEND_PID
        sleep 2
    fi
    rm -f .pids/backend.pid
fi

# Kill any remaining Gunicorn processes (workers that didn't stop)
GUNICORN_PIDS=$(pgrep -f "gunicorn.*app:app")
if [ ! -z "$GUNICORN_PIDS" ]; then
    echo "Stopping remaining Gunicorn workers..."
    pkill -f "gunicorn.*app:app"
    sleep 1
    
    # Force kill if still running
    GUNICORN_PIDS=$(pgrep -f "gunicorn.*app:app")
    if [ ! -z "$GUNICORN_PIDS" ]; then
        echo "Force killing stubborn Gunicorn processes..."
        pkill -9 -f "gunicorn.*app:app"
    fi
fi

echo "✓ Backend stopped"

# Kill frontend
if [ -f .pids/frontend.pid ]; then
    FRONTEND_PID=$(cat .pids/frontend.pid)
    if ps -p $FRONTEND_PID > /dev/null 2>&1; then
        echo "Stopping frontend (PID: $FRONTEND_PID)..."
        kill $FRONTEND_PID
        sleep 1
    fi
    rm -f .pids/frontend.pid
fi

# Kill any remaining npm/node processes
pkill -f "npm start"
pkill -f "react-scripts start"

echo "✓ Frontend stopped"

echo "All services stopped."
