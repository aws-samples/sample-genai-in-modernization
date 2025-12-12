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
    if [ -f .backend.pid ]; then
        SAVED_PID=$(cat .backend.pid)
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
    if [ -f .backend.pid ]; then
        echo "  ⚠ Stale PID file exists"
    fi
fi

echo ""

# Check frontend
echo "Frontend (Port 3000):"
FRONTEND_PORT=$(lsof -ti :3000 2>/dev/null)
if [ ! -z "$FRONTEND_PORT" ]; then
    echo "  ✓ Running (PID: $FRONTEND_PORT)"
    if [ -f .frontend.pid ]; then
        SAVED_PID=$(cat .frontend.pid)
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
    if [ -f .frontend.pid ]; then
        echo "  ⚠ Stale PID file exists"
    fi
fi

echo ""

# Check logs
if [ -f logs/backend.log ]; then
    echo "Backend log: logs/backend.log (last 5 lines)"
    tail -5 logs/backend.log | sed 's/^/  /'
    echo ""
fi

if [ -f logs/frontend.log ]; then
    echo "Frontend log: logs/frontend.log (last 5 lines)"
    tail -5 logs/frontend.log | sed 's/^/  /'
    echo ""
fi

echo "=========================================="
echo ""
echo "Commands:"
echo "  ./start-all.sh   - Start services"
echo "  ./stop-all.sh    - Stop services"
echo "  ./status.sh      - Check status (this script)"
echo ""
echo "Logs:"
echo "  tail -f logs/backend.log   - Watch backend logs"
echo "  tail -f logs/frontend.log  - Watch frontend logs"
echo ""
