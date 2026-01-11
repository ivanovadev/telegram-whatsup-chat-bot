#!/bin/bash
# Security check script wrapper

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🛡️  Running Security Checker...${NC}"
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Error: python3 is not installed${NC}"
    exit 1
fi

# Run the Python security checker
python3 "$SCRIPT_DIR/check_security.py" "$PROJECT_ROOT"
EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ Security check completed successfully!${NC}"
else
    echo -e "${YELLOW}⚠️  Security check found issues. Please review.${NC}"
fi

exit $EXIT_CODE
