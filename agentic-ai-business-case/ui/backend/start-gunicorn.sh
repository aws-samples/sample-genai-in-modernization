#!/bin/bash

# Start backend with Gunicorn (production mode)

echo "Starting AWS Migration Business Case API with Gunicorn..."

# Activate virtual environment
source venv/bin/activate

# Set production environment
export FLASK_ENV=production
export FLASK_DEBUG=false

# Optional: Configure Gunicorn settings via environment variables
# export GUNICORN_WORKERS=4
# export GUNICORN_BIND=127.0.0.1:5000
# export GUNICORN_LOG_LEVEL=info

# Start Gunicorn
echo "Starting Gunicorn server..."
echo "Workers: ${GUNICORN_WORKERS:-auto}"
echo "Bind: ${GUNICORN_BIND:-127.0.0.1:5000}"
echo ""

gunicorn -c gunicorn.conf.py app:app
