#!/bin/bash
# Count lines of code in the telegram-whatsup-chat-bot repository
#
# This script analyzes the codebase and provides statistics about:
# - Total lines of code
# - Lines by file type (Python, Markdown, Shell, etc.)
# - Lines by service/directory
#
# Usage:
#   ./count_lines.sh
#   ./count_lines.sh --detailed

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Directories to exclude
EXCLUDE_DIRS="venv __pycache__ .git node_modules .pytest_cache .mypy_cache dist build .tox htmlcov .coverage"

# Get repository root (where this script is located)
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Temporary files for counting
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

PYTHON_FILE="$TEMP_DIR/python.txt"
MARKDOWN_FILE="$TEMP_DIR/markdown.txt"
SHELL_FILE="$TEMP_DIR/shell.txt"
JSON_FILE="$TEMP_DIR/json.txt"
YAML_FILE="$TEMP_DIR/yaml.txt"
TEXT_FILE="$TEMP_DIR/text.txt"
CONFIG_FILE="$TEMP_DIR/config.txt"

# Function to check if directory should be excluded
should_exclude() {
    local path="$1"
    for exclude_dir in $EXCLUDE_DIRS; do
        if [[ "$path" == *"/$exclude_dir/"* ]] || [[ "$path" == *"/$exclude_dir" ]]; then
            return 0
        fi
    done
    return 1
}

# Function to count lines in a file
count_file_lines() {
    local file="$1"
    if [ -f "$file" ]; then
        wc -l < "$file" 2>/dev/null || echo "0"
    else
        echo "0"
    fi
}

echo -e "${CYAN}📊 Scanning repository: $REPO_ROOT${NC}"
echo -e "${YELLOW}🚫 Excluding: $EXCLUDE_DIRS${NC}"
echo ""

# Find and categorize files
echo -e "${BLUE}🔍 Finding files...${NC}"

# Python files
find "$REPO_ROOT" -type f -name "*.py" 2>/dev/null | while read file; do
    if ! should_exclude "$file"; then
        echo "$file" >> "$PYTHON_FILE"
    fi
done

# Markdown files
find "$REPO_ROOT" -type f -name "*.md" 2>/dev/null | while read file; do
    if ! should_exclude "$file"; then
        echo "$file" >> "$MARKDOWN_FILE"
    fi
done

# Shell files
find "$REPO_ROOT" -type f -name "*.sh" 2>/dev/null | while read file; do
    if ! should_exclude "$file"; then
        echo "$file" >> "$SHELL_FILE"
    fi
done

# JSON files
find "$REPO_ROOT" -type f -name "*.json" 2>/dev/null | while read file; do
    if ! should_exclude "$file"; then
        echo "$file" >> "$JSON_FILE"
    fi
done

# YAML files
find "$REPO_ROOT" -type f \( -name "*.yaml" -o -name "*.yml" \) 2>/dev/null | while read file; do
    if ! should_exclude "$file"; then
        echo "$file" >> "$YAML_FILE"
    fi
done

# Text files
find "$REPO_ROOT" -type f -name "*.txt" 2>/dev/null | while read file; do
    if ! should_exclude "$file"; then
        echo "$file" >> "$TEXT_FILE"
    fi
done

# Config files
find "$REPO_ROOT" -type f \( -name "*.env" -o -name "*.ini" -o -name "*.cfg" \) 2>/dev/null | while read file; do
    if ! should_exclude "$file"; then
        echo "$file" >> "$CONFIG_FILE"
    fi
done

# Count lines for each file type
count_lines_for_type() {
    local file_list="$1"
    local total=0
    
    if [ -f "$file_list" ]; then
        while IFS= read -r file; do
            if [ -f "$file" ]; then
                lines=$(wc -l < "$file" 2>/dev/null || echo "0")
                total=$((total + lines))
            fi
        done < "$file_list"
    fi
    
    echo "$total"
}

count_files_for_type() {
    local file_list="$1"
    if [ -f "$file_list" ]; then
        wc -l < "$file_list" 2>/dev/null || echo "0"
    else
        echo "0"
    fi
}

# Calculate statistics
PYTHON_FILES=$(count_files_for_type "$PYTHON_FILE")
PYTHON_LINES=$(count_lines_for_type "$PYTHON_FILE")

MARKDOWN_FILES=$(count_files_for_type "$MARKDOWN_FILE")
MARKDOWN_LINES=$(count_lines_for_type "$MARKDOWN_FILE")

SHELL_FILES=$(count_files_for_type "$SHELL_FILE")
SHELL_LINES=$(count_lines_for_type "$SHELL_FILE")

JSON_FILES=$(count_files_for_type "$JSON_FILE")
JSON_LINES=$(count_lines_for_type "$JSON_FILE")

YAML_FILES=$(count_files_for_type "$YAML_FILE")
YAML_LINES=$(count_lines_for_type "$YAML_FILE")

TEXT_FILES=$(count_files_for_type "$TEXT_FILE")
TEXT_LINES=$(count_lines_for_type "$TEXT_FILE")

CONFIG_FILES=$(count_files_for_type "$CONFIG_FILE")
CONFIG_LINES=$(count_lines_for_type "$CONFIG_FILE")

TOTAL_FILES=$((PYTHON_FILES + MARKDOWN_FILES + SHELL_FILES + JSON_FILES + YAML_FILES + TEXT_FILES + CONFIG_FILES))
TOTAL_LINES=$((PYTHON_LINES + MARKDOWN_LINES + SHELL_LINES + JSON_LINES + YAML_LINES + TEXT_LINES + CONFIG_LINES))

# Print summary
echo ""
echo "============================================================"
echo -e "${GREEN}📈 CODE STATISTICS SUMMARY${NC}"
echo "============================================================"
echo ""
printf "📁 Total Files: %'d\n" $TOTAL_FILES
printf "📝 Total Lines: %'d\n" $TOTAL_LINES
echo ""
echo "============================================================"
