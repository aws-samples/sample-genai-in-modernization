#!/bin/bash

echo "Stopping AWS Migration Business Case Generator..."

# Stop backend using PID file
if [ -f .backend.pid ]; then
    BACKEND_PID=$(cat .backend.pid)
    if kill -0 $BACKEND_PID 2>/dev/null; then
        kill $BACKEND_PID
        echo "✓ Backend stopped (PID: $BACKEND_PID)"
    else
        echo "⚠ Backend process not running"
    fi
    rm .backend.pid
else
    # Fallback to pkill
    pkill -f "gunicorn.*app:app"
    echo "✓ Backend stopped (using pkill)"
fi

# Stop frontend using PID file
if [ -f .frontend.pid ]; then
    FRONTEND_PID=$(cat .frontend.pid)
    if kill -0 $FRONTEND_PID 2>/dev/null; then
        kill $FRONTEND_PID
        echo "✓ Frontend stopped (PID: $FRONTEND_PID)"
    else
        echo "⚠ Frontend process not running"
    fi
    rm .frontend.pid
else
    # Fallback to pkill
    pkill -f "npm start"
    pkill -f "react-scripts start"
    echo "✓ Frontend stopped (using pkill)"
fi

echo "All services stopped."
