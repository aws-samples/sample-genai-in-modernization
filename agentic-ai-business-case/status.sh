#!/bin/bash

echo "=========================================="
echo "Service Status Check"
echo "=========================================="
echo ""

# Check backend
echo "Backend (Port 5000):"
BACKEND_PORT=$(lsof -ti :5000 2>/dev/null)
if [ ! -z "$BACKEND_PORT" ]; then
    echo "  ✓ Running (PID: $BACKEND_PORT)"
    if [ -f .pids/backend.pid ]; then
        SAVED_PID=$(cat .pids/backend.pid)
        if [ "$BACKEND_PORT" == "$SAVED_PID" ]; then
            echo "  ✓ PID file matches"
        else
            echo "  ⚠ PID file mismatch (saved: $SAVED_PID, actual: $BACKEND_PORT)"
        fi
    else
        echo "  ⚠ No PID file found"
    fi
else
    echo "  ✗ Not running"
    if [ -f .pids/backend.pid ]; then
        echo "  ⚠ Stale PID file exists"
    fi
fi

echo ""

# Check frontend
echo "Frontend (Port 3000):"
FRONTEND_PORT=$(lsof -ti :3000 2>/dev/null)
if [ ! -z "$FRONTEND_PORT" ]; then
    echo "  ✓ Running (PID: $FRONTEND_PORT)"
    if [ -f .pids/frontend.pid ]; then
        SAVED_PID=$(cat .pids/frontend.pid)
        if [ "$FRONTEND_PORT" == "$SAVED_PID" ]; then
            echo "  ✓ PID file matches"
        else
            echo "  ⚠ PID file mismatch (saved: $SAVED_PID, actual: $FRONTEND_PORT)"
        fi
    else
        echo "  ⚠ No PID file found"
    fi
else
    echo "  ✗ Not running"
    if [ -f .pids/frontend.pid ]; then
        echo "  ⚠ Stale PID file exists"
    fi
fi

echo ""

# Check logs
if [ -f .pids/backend.log ]; then
    echo "Backend log: .pids/backend.log (last 5 lines)"
    tail -5 .pids/backend.log | sed 's/^/  /'
    echo ""
fi

if [ -f .pids/frontend.log ]; then
    echo "Frontend log: .pids/frontend.log (last 5 lines)"
    tail -5 .pids/frontend.log | sed 's/^/  /'
    echo ""
fi

echo "=========================================="
echo ""
echo "Commands:"
echo "  ./start-all.sh   - Start services"
echo "  ./stop-all.sh    - Stop services"
echo "  ./status.sh      - Check status (this script)"
echo ""
