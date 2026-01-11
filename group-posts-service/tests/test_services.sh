#!/bin/bash
# Test script wrapper that activates venv and runs test_services.py

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Check for venv in parent directory
if [ ! -d "$SERVICE_DIR/venv" ]; then
    echo "❌ Virtual environment not found in $SERVICE_DIR"
    echo "💡 Run: cd $SERVICE_DIR && python3 -m venv venv"
    exit 1
fi

# Activate venv from parent directory
source "$SERVICE_DIR/venv/bin/activate"

# Install dependencies if needed
if ! python3 -c "import telethon" 2>/dev/null; then
    echo "📦 Installing dependencies..."
    pip install -q -r "$SERVICE_DIR/requirements.txt"
fi

# Run test script
echo "🧪 Running service tests..."
cd "$SCRIPT_DIR" || exit 1
python3 test_services.py "$@"
