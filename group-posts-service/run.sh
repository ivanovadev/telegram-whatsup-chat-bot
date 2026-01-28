#!/bin/bash
# Run script for group-posts-service

cd "$(dirname "$0")"

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found!"
    echo "📋 Copy .env.example to .env and configure it:"
    echo "   cp .env.example .env"
    echo "   # Then edit .env with your credentials"
    exit 1
fi

# Check if venv exists, create if not
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies (rerun when requirements.txt changes)
if [ ! -f "venv/.installed" ] || [ "requirements.txt" -nt "venv/.installed" ]; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
    touch venv/.installed
fi

# Create data directory if it doesn't exist
mkdir -p data

# Run the service
echo "Starting group-posts-service..."
python -m app.main
