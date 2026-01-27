#!/bin/bash
# Run all tests and checks in tests directory

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DOCKER_DIR="$PROJECT_ROOT/docker"
ANSIBLE_DIR="$PROJECT_ROOT/ansible"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Track results
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Cleanup helper (docker & ansible artefacts)
cleanup_docker_and_ansible() {
    echo -e "${YELLOW}🔄 Cleaning Docker & Ansible artefacts...${NC}"

    # Stop Neo4j stack if running (best-effort)
    if command -v docker &> /dev/null; then
        if [ -f "$DOCKER_DIR/docker-compose.neo4j.yml" ]; then
            (
                cd "$PROJECT_ROOT" && \
                docker compose -f docker/docker-compose.neo4j.yml down >/dev/null 2>&1 || \
                docker-compose -f docker/docker-compose.neo4j.yml down >/dev/null 2>&1 || true
            )
        fi

        # Optionally prune stopped containers with this project name
        docker ps -a --format '{{.Names}}' | grep -E '^telegram-bot-neo4j$' >/dev/null 2>&1 && \
            docker rm -f telegram-bot-neo4j >/dev/null 2>&1 || true
    fi

    # Remove Ansible retry files in project tree
    if [ -d "$ANSIBLE_DIR" ]; then
        find "$ANSIBLE_DIR" -name "*.retry" -type f -delete 2>/dev/null || true
    fi

    # Remove local .ansible cache inside project if present
    if [ -d "$PROJECT_ROOT/.ansible" ]; then
        rm -rf "$PROJECT_ROOT/.ansible"
    fi
}

echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║         Running All Tests & Quality Checks                ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Function to run a test and track results
run_test() {
    local test_name="$1"
    local test_cmd="$2"
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}▶ Running: ${test_name}${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    
    if eval "$test_cmd"; then
        echo ""
        echo -e "${GREEN}✅ PASSED: ${test_name}${NC}"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        echo ""
        echo -e "${RED}❌ FAILED: ${test_name}${NC}"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi
}

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Error: python3 is not installed${NC}"
    exit 1
fi

# 1. Security Check
run_test "Security Check (check_security.py)" \
    "python3 '$SCRIPT_DIR/check_security.py' '$PROJECT_ROOT'"

# 2. Code Quality & Line Count
run_test "Code Quality & Comment Analysis (count_lines.py)" \
    "python3 '$SCRIPT_DIR/count_lines.py' --check-comments"

# 3. Unit Tests - Code Quality
run_test "Unit Tests: Code Quality (test_code_quality.py)" \
    "python3 '$SCRIPT_DIR/test_code_quality.py' -v"

# 4. Unit Tests - Database
if [ -f "$SCRIPT_DIR/test_db.py" ]; then
    run_test "Unit Tests: Database (test_db.py)" \
        "python3 '$SCRIPT_DIR/test_db.py' -v"
fi

# 5. README Check, Auto-Fix, Structure Validation, Structure Update, and Commands Update
run_test "README Validation, Structure & Commands Update (check_readme.py)" \
    "python3 '$SCRIPT_DIR/check_readme.py' --fix --check-structure --update-structure --update-commands"

# 6. Environment Variables Check & Auto-Fix
run_test "Environment Variables Check & Auto-Fix (check_env_vars.py)" \
    "python3 '$SCRIPT_DIR/check_env_vars.py' '$PROJECT_ROOT'"

# 7. Extra Markdown Files Check
run_test "Extra Markdown Check (only README*.md allowed in code dirs)" \
    "python3 '$SCRIPT_DIR/check_extra_markdown.py'"

# Cleanup after all tests
cleanup_docker_and_ansible

# Summary
echo ""
echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                     TEST SUMMARY                           ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "Total Tests:  ${CYAN}${TOTAL_TESTS}${NC}"
echo -e "Passed:       ${GREEN}${PASSED_TESTS}${NC}"
echo -e "Failed:       ${RED}${FAILED_TESTS}${NC}"
echo ""

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║          ✅ ALL TESTS PASSED SUCCESSFULLY! ✅              ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
    exit 0
else
    echo -e "${RED}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║            ⚠️  SOME TESTS FAILED! ⚠️                       ║${NC}"
    echo -e "${RED}╚════════════════════════════════════════════════════════════╝${NC}"
    exit 1
fi
