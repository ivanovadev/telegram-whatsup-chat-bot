# Tests

Directory with tests and code quality checking tools.

## Quick Start 🚀

### Security Checker

**One-Line Commands:**

```bash
# Run security check
./tests/check_security.sh

# Or directly with Python
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

### Unit Tests

```bash
# From project root
pytest tests/

# Or specific test
pytest tests/test_db.py
```

## Files

### Unit Tests
- `test_db.py` - unit tests for database

### Security Tools
- `check_security.py` - 🛡️ script to check for Ukrainian language and sensitive information
- `check_security.sh` - shell wrapper for quick launch
- `example_issues.py.example` - 📖 examples of issues detected by the script

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
./tests/check_security.sh && git commit -m "Your message"
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
2. Use pytest fixtures
3. Run tests: `pytest tests/test_your_feature.py`

**Example:**
```python
import pytest

def test_something():
    """Test description."""
    assert True
```

## CI/CD Integration

**GitHub Actions:**
```yaml
test:
  runs-on: ubuntu-latest
  steps:
    - name: Run Tests
      run: pytest tests/
    
    - name: Security Check
      run: python3 tests/check_security.py
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
ls -la tests/check_security.*

# Make executable
chmod +x tests/check_security.py tests/check_security.sh

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
