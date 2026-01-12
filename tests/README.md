# Tests

Directory with tests and code quality checking tools.

## Quick Start 🚀

### Run All Tests (Recommended)

**One command to rule them all:**

```bash
# Run all tests and checks
./tests/run_all.sh
```

This will execute:
- ✅ Security check (`check_security.py`)
- ✅ Code quality & comment analysis (`count_lines.py`)
- ✅ Unit tests for code quality (`test_code_quality.py`)
- ✅ Unit tests for database (`test_db.py`)

**Example output:**

```
╔════════════════════════════════════════════════════════════╗
║         Running All Tests & Quality Checks                ║
╚════════════════════════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
▶ Running: Security Check (check_security.py)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ PASSED: Security Check

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
▶ Running: Code Quality & Comment Analysis (count_lines.py)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ PASSED: Code Quality & Comment Analysis

╔════════════════════════════════════════════════════════════╗
║                     TEST SUMMARY                           ║
╚════════════════════════════════════════════════════════════╝

Total Tests:  4
Passed:       4
Failed:       0

╔════════════════════════════════════════════════════════════╗
║          ✅ ALL TESTS PASSED SUCCESSFULLY! ✅              ║
╚════════════════════════════════════════════════════════════╝
```

---

### Individual Tool Usage

If you need to run a specific tool separately:

#### Security Checker

```bash
# Run security check for entire project
python3 tests/check_security.py

# Check specific directory
python3 tests/check_security.py group-posts-service/
```

**What You'll See:**

✅ **If all good:**
```
✅ All checks passed!
Exit code: 0
```

⚠️ **If issues found:**
```
🔒 SENSITIVE DATA DETECTED
🚨 config.py (2 issues)
   Line 12: [api_key] API_KEY = "sk-ab***"
Exit code: 1
```

### Individual Test Execution

```bash
# Run all unit tests with verbose output
python3 tests/test_db.py -v
python3 tests/test_code_quality.py -v

# Or use run_all.sh to run everything
./tests/run_all.sh
```

## Files

### Test Runner

#### `run_all.sh` - All-in-One Test Runner

Runs all tests and quality checks in one command.

**Usage:**
```bash
./tests/run_all.sh
```

**What it runs:**
1. 🛡️ Security check (`check_security.py`)
2. 📊 Code statistics & comment analysis (`count_lines.py`)
3. ✅ Unit tests for code quality (`test_code_quality.py`)
4. ✅ Unit tests for database (`test_db.py`)

**Exit codes:**
- `0` - All tests passed
- `1` - Some tests failed

---

### Code Quality Tools

#### `count_lines.py` - Code Counter & Comment Analyzer

Count lines of code and check for unnecessary comments.

**Usage:**
```bash
# Basic line counting
python3 tests/count_lines.py

# Check for unnecessary comments
python3 tests/count_lines.py --check-comments

# Detailed file-by-file breakdown
python3 tests/count_lines.py --detailed

# Combine all options
python3 tests/count_lines.py --check-comments --detailed

# Check specific directory
python3 tests/count_lines.py --path group-posts-service/
```

**What it checks:**
- ✅ Total lines, code lines, comments, blank lines
- ✅ Code distribution by file type
- ✅ Code distribution by service
- ⚠️ Unnecessary comments (TODO placeholders, long separators, verbose comments)
- ⚠️ Emoji overuse in comments
- ⚠️ Comments >100 characters

**Example output:**
```
📊 Scanning repository: /Users/iva/chat_bot/telegram-whatsup-chat-bot

📁 Total Files: 142
📝 Total Lines: 15,234
💻 Code Lines: 11,567
💬 Comment Lines: 2,145
⬜ Blank Lines: 1,522
📊 Code Percentage: 75.9%

💬 Comment Quality:
⚠️  Unnecessary Comments: 23

📄 Files with unnecessary comments:
  group-posts-service/content/spider_content.py
    Line 45: # ========== SECTION ==========
    Line 102: # TODO: Replace with actual image analysis
```

### Unit Tests

All tests use Python's built-in `unittest` framework (no external dependencies required).

- `test_db.py` - unit tests for database operations
- `test_code_quality.py` - unit tests for code counter and comment analyzer

**Run individually:**
```bash
# Database tests
python3 tests/test_db.py -v

# Code quality tests
python3 tests/test_code_quality.py -v
```

### Security Tools
- `check_security.py` - 🛡️ script to check for Ukrainian language and sensitive information

## Security Checker

### What It Checks

✅ **Detects Ukrainian language** (Cyrillic) in code files  
✅ **Detects sensitive information**:
   - API keys
   - Tokens
   - Passwords
   - Private keys
   - Phone numbers and emails

🎯 **Result**: Exit code 0 if all good, 1 if issues found

### Detailed Pattern Detection

The script searches for the following types of sensitive data:

- **API Keys**: `api_key`, `apikey`, `api_secret`
- **Tokens**: `token`, `access_token`, `auth_token`
- **Passwords**: `password`, `passwd`, `pwd`
- **Secrets**: `secret`, `secret_key`
- **Telegram Bot Tokens**: format `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`
- **OpenAI Keys**: format `sk-...`
- **AWS Keys**: format `AKIA...`
- **Private Keys**: `-----BEGIN PRIVATE KEY-----`
- **Phone Numbers**: phone numbers in code
- **Email Addresses**: email addresses in code

### Exclusions

**Ignored directories:**
- `venv`, `__pycache__`, `.git`
- `node_modules`, `.pytest_cache`
- `.env`, `dist`, `build`

**Ignored file types:**
- Binary: `.pyc`, `.so`, `.dll`, `.dylib`
- Data: `.db`, `.sqlite`, `.session`
- Media: `.jpg`, `.png`, `.gif`, `.ico`, `.pdf`
- Archives: `.zip`, `.tar`, `.gz`

**Whitelisted files:**
Some files (like `README.md`, test files) may contain examples 
and won't cause errors even if they contain patterns.

Add file to whitelist in the script:
```python
WHITELIST_FILES = {
    'your_file.py',
    # ...
}
```

### Interpreting Results

**Exit Codes:**
- `0` - All good, no sensitive info found
- `1` - Sensitive information found, review needed

**Example Output:**

```
🔍 Scanning directory: /path/to/project
======================================================================

📝 UKRAINIAN LANGUAGE DETECTED:
----------------------------------------------------------------------

📄 README.md (5 occurrences)
   Line 23: Test project for automation...
   Line 45: Usage instructions...
   ... and 3 more

======================================================================

🔒 SENSITIVE DATA DETECTED:
----------------------------------------------------------------------

🚨 app/config.py (2 issues)
   Line 12: [api_key] API_KEY = "sk-ab***"
   Line 34: [token] TOKEN = "12345678***"

======================================================================
❌ TOTAL: 2 sensitive data issue(s) found!
======================================================================

📊 SUMMARY:
----------------------------------------------------------------------
Ukrainian files: 3
Sensitive data issues: 2
======================================================================

⚠️  Please review and fix the issues above.
```

### Quick Fixes

#### Problem: API key in code
```python
# ❌ BAD
API_KEY = "sk-abc123..."

# ✅ GOOD
import os
API_KEY = os.getenv("API_KEY")
```

#### Problem: Ukrainian in code
- If it's documentation - it's OK!
- If it's code comments - consider English
- If it's user messages - move to constants

### What To Do When Issues Found

**Sensitive information detected:**

1. **Check if these are real secrets**
   - Are these real API keys/tokens?
   - Are these test/example values?

2. **If real secrets:**
   - ❌ Remove them from code
   - ✅ Move to `.env` file
   - ✅ Add `.env` to `.gitignore`
   - ⚠️ If already committed - regenerate secrets!

3. **If test data:**
   - Add file to whitelist
   - Or use placeholder values

**Example of safe configuration:**

```python
# ❌ BAD
API_KEY = "sk-abc123def456..."

# ✅ GOOD
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("API_KEY")
```

### Integration Tips

**Pre-commit hook:**
```bash
# Add to .git/hooks/pre-commit
python3 tests/check_security.py || exit 1
```

**Before every commit:**
```bash
./tests/run_all.sh && git commit -m "Your message"
```

**Git Hook (Optional):**
```bash
# .git/hooks/pre-commit
#!/bin/bash
python3 tests/check_security.py
if [ $? -ne 0 ]; then
    echo "❌ Security check failed! Commit aborted."
    exit 1
fi
```

```bash
chmod +x .git/hooks/pre-commit
```

### Extending the Script

**Add new patterns:**

Edit `check_security.py`:

```python
SENSITIVE_PATTERNS = {
    # Add your pattern
    'custom_pattern': r'your_regex_pattern_here',
    # ...
}
```

**Add exclusions:**

```python
SKIP_DIRS = {
    'your_custom_dir',
    # ...
}

WHITELIST_FILES = {
    'your_safe_file.py',
    # ...
}
```

### .gitignore Recommendations

**Important to add to `.gitignore`:**

```gitignore
# Environment files with secrets
.env
.env.local
.env.*.local
*.env

# Session files (may contain tokens)
*.session
*.session-journal

# Database files
*.db
*.sqlite
*.sqlite3

# Logs that might contain sensitive info
*.log
logs/

# Python
__pycache__/
*.pyc
venv/
env/

# IDE files
.vscode/settings.json
.idea/

# OS files
.DS_Store
```

💡 **Check existing `.gitignore`**: Make sure these files are already added!

## Unit Tests

### Adding New Tests

1. Create `test_*.py` file in this directory
2. Use Python's built-in `unittest` framework
3. Run tests: `python3 tests/test_your_feature.py -v`

**Example:**
```python
import unittest

class TestYourFeature(unittest.TestCase):
    """Test cases for your feature."""
    
    def test_something(self):
        """Test description."""
        self.assertTrue(True)

if __name__ == "__main__":
    unittest.main()
```

## CI/CD Integration

**GitHub Actions:**
```yaml
test:
  runs-on: ubuntu-latest
  steps:
    - name: Run All Tests
      run: bash tests/run_all.sh
```

**GitLab CI:**
```yaml
security_check:
  script:
    - python3 tests/check_security.py
```

## Troubleshooting

### "Cannot read file" error
- File may be binary or inaccessible
- This is normal, script will skip it

### False positives
- Add file to whitelist
- Or use comments for explanation

### Script won't run
```bash
# Check permissions
ls -la tests/*.py tests/*.sh

# Make executable
chmod +x tests/run_all.sh

# Check Python
python3 --version
```

## Best Practices

1. 🔄 Run tests before each commit
2. 🛡️ Run security check regularly
3. ✅ All tests must pass before PR
4. 📝 Document complex test cases
5. 🔒 Never commit real secrets even in tests
6. 📚 Use `.env` for configuration
7. 🔑 Regenerate secrets if they got into Git
8. 📋 Check `.gitignore` completeness

---

**Important**: Security checker is a helper tool. It doesn't replace code review 
and manual security checks!

**Remember**: This tool helps find issues, but code review is still essential!
