#!/bin/bash

# Script to view agent execution logs

LOG_DIR="../output/logs"

if [ ! -d "$LOG_DIR" ]; then
    echo "No logs directory found at $LOG_DIR"
    exit 1
fi

# Check if any argument is provided
if [ "$1" == "list" ]; then
    echo "Available log files:"
    ls -lht "$LOG_DIR"/*.log 2>/dev/null || echo "No log files found"
elif [ "$1" == "latest" ] || [ -z "$1" ]; then
    # Show the latest log file
    LATEST_LOG=$(ls -t "$LOG_DIR"/*.log 2>/dev/null | head -1)
    if [ -z "$LATEST_LOG" ]; then
        echo "No log files found"
        exit 1
    fi
    echo "Viewing latest log: $LATEST_LOG"
    echo "================================"
    tail -f "$LATEST_LOG"
elif [ "$1" == "all" ]; then
    # Show all content of latest log
    LATEST_LOG=$(ls -t "$LOG_DIR"/*.log 2>/dev/null | head -1)
    if [ -z "$LATEST_LOG" ]; then
        echo "No log files found"
        exit 1
    fi
    echo "Full content of latest log: $LATEST_LOG"
    echo "================================"
    cat "$LATEST_LOG"
else
    # Show specific log file
    if [ -f "$LOG_DIR/$1" ]; then
        echo "Viewing log: $LOG_DIR/$1"
        echo "================================"
        tail -f "$LOG_DIR/$1"
    else
        echo "Log file not found: $LOG_DIR/$1"
        exit 1
    fi
fi
