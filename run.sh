#!/bin/bash

# Script to run Telegram Userbot
# Loads environment variables from .env file

set -e  # Stop on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting Telegram Userbot${NC}"

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${RED}❌ Error: .env file not found!${NC}"
    echo -e "${YELLOW}💡 Create .env file based on .env.example${NC}"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d .venv ]; then
    echo -e "${YELLOW}⚠️  Virtual environment not found. Creating...${NC}"
    python3 -m venv .venv
    echo -e "${GREEN}✅ Virtual environment created${NC}"
fi

# Activate virtual environment
echo -e "${GREEN}📦 Activating virtual environment...${NC}"
source .venv/bin/activate

# Check if dependencies are installed
if ! python -c "import telethon" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Dependencies not installed. Installing...${NC}"
    pip install -r requirements.txt
    echo -e "${GREEN}✅ Dependencies installed${NC}"
fi

# Load environment variables from .env
echo -e "${GREEN}📝 Loading environment variables from .env...${NC}"

# Function to load .env file (ignores comments and empty lines)
load_env() {
    if [ -f .env ]; then
        # Read .env file line by line
        while IFS= read -r line || [ -n "$line" ]; do
            # Skip comments and empty lines
            if [[ "$line" =~ ^[[:space:]]*# ]] || [[ -z "${line// }" ]]; then
                continue
            fi
            # Export variable (remove spaces around)
            export "$line"
        done < .env
    fi
}

# Load variables
load_env

# Check required variables
if [ -z "$TG_API_ID" ] || [ -z "$TG_API_HASH" ]; then
    echo -e "${RED}❌ Error: TG_API_ID or TG_API_HASH not set in .env${NC}"
    echo -e "${YELLOW}💡 Check .env file and make sure variables are set${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Environment variables loaded${NC}"
echo -e "${GREEN}   TG_API_ID: ${TG_API_ID}${NC}"
echo -e "${GREEN}   CONTROL_CHAT_ID: ${CONTROL_CHAT_ID}${NC}"
echo -e "${GREEN}   BUSY_MODE: ${BUSY_MODE}${NC}"
echo -e "${GREEN}🔌 Starting bot...${NC}"
echo ""

# Start bot
python -m app.main
