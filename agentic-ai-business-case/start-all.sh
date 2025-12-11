#!/bin/bash

# Start both backend and frontend

echo "Starting AWS Migration Business Case Generator..."

# Create PID file directory
mkdir -p .pids

# Check if services are already running
if [ -f .pids/backend.pid ]; then
    OLD_PID=$(cat .pids/backend.pid)
    if ps -p $OLD_PID > /dev/null 2>&1; then
        echo "⚠ Backend already running (PID: $OLD_PID)"
        echo "Run ./stop-all.sh first to stop existing services"
        exit 1
    fi
fi

# Start backend in background with Gunicorn
echo "Starting backend server with Gunicorn..."
cd ui/backend
source venv/bin/activate
gunicorn -c gunicorn.conf.py app:app > ../../.pids/backend.log 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > ../../.pids/backend.pid
cd ../..

# Wait for backend to start
echo "Waiting for backend to start..."
sleep 3

# Verify backend is running
if ! ps -p $BACKEND_PID > /dev/null 2>&1; then
    echo "✗ Backend failed to start. Check .pids/backend.log for errors"
    exit 1
fi

# Start frontend
echo "Starting frontend server..."
cd ui
npm start > ../.pids/frontend.log 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > ../.pids/frontend.pid
cd ..

echo ""
echo "=========================================="
echo "Services started successfully!"
echo "=========================================="
echo "Backend PID: $BACKEND_PID (saved to .pids/backend.pid)"
echo "Frontend PID: $FRONTEND_PID (saved to .pids/frontend.pid)"
echo ""
echo "Backend log: .pids/backend.log"
echo "Frontend log: .pids/frontend.log"
echo ""
echo "Access the application at: http://localhost:3000"
echo ""
echo "To stop the services, run: ./stop-all.sh"
echo "Or manually: kill $BACKEND_PID $FRONTEND_PID"
echo ""
echo "Services running in background. You can close this terminal."
echo ""
