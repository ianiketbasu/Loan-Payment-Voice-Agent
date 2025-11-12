#!/bin/bash

# Loan Reminder Voice Agent - Startup Script
# This script sets up the environment and starts the FastAPI server

set -e  # Exit on error

echo "Starting Loan Reminder Voice Agent..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Check if requirements are installed by trying to import fastapi
if ! python -c "import fastapi" 2>/dev/null; then
    echo "Installing dependencies from requirements.txt..."
    pip install --upgrade pip
    pip install -r requirements.txt
else
    echo "Dependencies already installed"
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "Warning: .env file not found!"
    echo "Please copy env_template.txt to .env and configure your settings"
    echo ""
    read -p "Do you want to continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Get port from argument or default to 8000
PORT=${1:-8000}

# Start the server
echo "Starting FastAPI server on http://localhost:$PORT"
echo "Press CTRL+C to stop the server"
echo ""

uvicorn main:app --host 0.0.0.0 --port $PORT --reload

