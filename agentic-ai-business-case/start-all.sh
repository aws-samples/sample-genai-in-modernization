#!/bin/bash

# Start both backend and frontend

echo "Starting AWS Migration Business Case Generator..."

# Start backend in background
echo "Starting backend server..."
cd ui/backend
source venv/bin/activate
nohup gunicorn -c gunicorn.conf.py app:app > ../../logs/backend.log 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > ../../.backend.pid
cd ../..

# Wait for backend to start
sleep 3

# Start frontend in background
echo "Starting frontend server..."
cd ui
nohup npm start > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > ../.frontend.pid
cd ..

echo ""
echo "=========================================="
echo "Services started successfully!"
echo "=========================================="
echo "Backend PID: $BACKEND_PID (saved to .backend.pid)"
echo "Frontend PID: $FRONTEND_PID (saved to .frontend.pid)"
echo ""
echo "Backend logs: logs/backend.log"
echo "Frontend logs: logs/frontend.log"
echo ""
echo "Access the application at: http://localhost:3000"
echo ""
echo "To stop the services, run: ./stop-all.sh"
echo ""
