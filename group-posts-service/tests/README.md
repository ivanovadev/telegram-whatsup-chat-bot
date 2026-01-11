# Group Posts Service - Testing Guide

> **⚠️ IMPORTANT:** Current tests only verify that commands are SENT, not that they work!  
> See [PROBLEMS_SUMMARY.md](PROBLEMS_SUMMARY.md) for issues and [TESTING_ISSUES.md](TESTING_ISSUES.md) for detailed analysis.

> **Note:** All test commands should be run from the `tests/` directory.

This directory contains test scripts for the group-posts-service.

## Quick Start

```bash
# Run all tests (14 commands)
./test_services.sh

# Check status only
./test_services.sh status

# Test specific services
./test_services.sh travel news person
```

## Files

### Test Scripts
- **`test_services.py`** - Main test script that sends commands to the bot
- **`test_services.sh`** - Shell wrapper that activates venv and runs tests

### Documentation
- **`README.md`** - This file, testing guide
- **`PROBLEMS_SUMMARY.md`** - Quick summary of test issues ⚠️
- **`TESTING_ISSUES.md`** - Detailed analysis and validation checklist

## Prerequisites

1. **Main service must be running** to process commands
2. Tests will use a separate session file (`session_test.session`) to avoid conflicts
3. Virtual environment (`venv/`) must exist in parent directory (`group-posts-service/`)

## How to Test

### Option 1: Test with Running Service (Recommended)

**Terminal 1 - Start Main Service:**
```bash
cd /Users/iva/chat_bot/telegram-whatsup-chat-bot/group-posts-service
./run.sh
```

**Terminal 2 - Run Tests:**
```bash
cd /Users/iva/chat_bot/telegram-whatsup-chat-bot/group-posts-service/tests
./test_services.sh
```

### Option 2: Test Specific Services

Test only specific commands:
```bash
# Test single service
./test_services.sh travel

# Test multiple services
./test_services.sh travel news person
```

### Option 3: Test All Services

```bash
# Test all 14 services (default)
./test_services.sh
```

## Available Test Commands

1. `status` - Check budget, LLM status, and daily post counts
2. `travel` - Travel post (random morning/evening)
3. `travel morning` - Morning travel post  
4. `news` - News summary (Bloomberg, BBC, Ukrainian Truth)
5. `tech` - Tech device post
6. `person` - Famous person post
7. `ukraine` - Ukraine news (economy, politics, war)
8. `spider` - Spider information post
9. `quote` - Quote of the day
10. `africa` - Africa exploration post
11. `london` - London information post
12. `uk` - UK cities post
13. `job` - Job vacancy post (DevOps/MLOps/SRE)
14. `weather` - Weather forecast for multiple cities

## How Tests Work

1. Tests send commands to your **Saved Messages** ("me")
2. Main service receives these commands via message handler
3. Service generates content and posts to target channel
4. Tests wait 15 seconds between commands to allow processing
5. You can check results in:
   - Your Saved Messages (command confirmations)
   - Target channel (@Travel or configured channel)

## ⚠️ Current Test Limitations

**These tests have significant limitations:**

1. **No Response Validation** - Tests only send commands, don't check if bot replies
2. **False Positives** - Shows "✅ Success" even if main service is not running
3. **No Content Validation** - Doesn't verify post format, quality, or completeness
4. **No Health Checks** - Doesn't verify service is running before testing

**What "Success" Actually Means:**
- ✅ Command message was sent to Telegram
- ❌ NOT that bot processed it
- ❌ NOT that post was created
- ❌ NOT that content is correct

**For reliable testing:**
1. Keep main service running in Terminal 1
2. Watch logs in Terminal 1 for actual processing
3. Manually check Saved Messages for bot replies
4. Manually verify posts in target group

See [PROBLEMS_SUMMARY.md](PROBLEMS_SUMMARY.md) for details and improvement plans.

---

## Important Notes

### LLM Usage
- Tests will use LLM if `LLM_ENABLED=on` in `.env`
- Check budget status before testing: send `status` command to Saved Messages
- Budget limit: $2.00/day by default
- If budget exhausted, services will use template content

### Session Files
- Main service uses: `data/session.session`
- Tests use: `data/session_test.session` (auto-created)
- Both can run simultaneously without conflicts

### Expected Test Duration
- Each command takes 5-15 seconds to process
- Full test suite (14 commands): ~3-5 minutes
- Tests can be interrupted with `Ctrl+C`

## Troubleshooting

### "database is locked" error
- **Solution**: Main service must use different session file (now fixed)
- Tests use `session_test.session`, service uses `session.session`

### No posts appearing
- **Check**: Is main service running in Terminal 1?
- **Check**: Are commands being received? (look for logs)
- **Check**: Is LLM enabled and budget available?

### Budget exhausted
```bash
# Check budget status
./test_services.sh status

# Or send "status" to Saved Messages manually
```

### Only some commands work
- Some services may fail if:
  - External APIs are down (news, weather)
  - Job searches return no results
  - LLM rate limits hit

### Debugging Steps
1. **Check main service is running** in Terminal 1
2. Check logs in Terminal 1 for command processing
3. Verify budget: send `status` to Saved Messages
4. Check LLM is enabled: `LLM_ENABLED=on` in `.env`
5. Verify API keys in `.env`

## Examples

### Check status first:
```bash
./test_services.sh status
```

### Test travel posts only:
```bash
./test_services.sh travel "travel morning"
```

### Test all content generators:
```bash
./test_services.sh person tech spider quote africa london uk
```

### Test news services:
```bash
./test_services.sh news ukraine
```

## CI/CD Integration

For automated testing:
```bash
# Set timeout to prevent hanging
timeout 300 ./test_services.sh

# Exit code: 0 = all passed, non-zero = some failed
```
