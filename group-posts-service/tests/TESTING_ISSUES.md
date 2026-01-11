# Testing Issues & Content Validation Guide

## Current Problems

### 1. Test Script Issues ❌

**Problem:** Tests only verify that commands are SENT, not that they are PROCESSED or that content is GENERATED.

**Evidence:**
```
✅ Command 'status' sent successfully
✅ Successful: 1/1
```

**Reality:** 
- Main service might not be running → No response
- Command might fail → Tests still show "success"
- No validation that content appeared in group
- No validation that bot replied in Saved Messages

### 2. No Response Validation ❌

**Current behavior:**
```python
await client.send_message("me", command)
print(f"✅ Command '{command}' sent successfully")
return True  # Always returns True!
```

**Missing:**
- Check if bot replied
- Check if post appeared in target group
- Verify content quality
- Validate format (emojis, structure, data)

### 3. False Positives ❌

**Test shows success even when:**
- Main service is stopped
- LLM budget exhausted
- API keys invalid
- Group/channel not configured
- Bot has no permissions

### 4. No Content Quality Checks ❌

**What's NOT tested:**
- Weather post format (country blocks, emojis)
- Temperature values are realistic
- Date format is correct
- All 6 cities are included
- Emojis match weather conditions
- No duplicate content
- No LLM hallucinations

### 5. Timing Issues ⏱️

**Problem:** 15 second delay between commands, but:
- Weather with API: 3-5 seconds
- Weather with LLM: 10-15 seconds
- Job posts with LLM: 20-30 seconds
- If LLM is slow, test moves on before content is generated

---

## Required Improvements

### A. Service Health Check

**Before running ANY tests:**
```python
def check_service_running():
    """Check if main service is running and responsive."""
    # Send status command
    # Wait for reply
    # If no reply in 10 seconds → ERROR: "Main service not running"
    # If reply received → Parse and verify service is healthy
```

### B. Response Validation

**For each command:**
```python
async def test_command_with_validation(command, timeout=30):
    """Test command and validate response."""
    # 1. Record time
    # 2. Send command
    # 3. Wait for bot reply (up to timeout)
    # 4. Check bot reply message
    # 5. Check if post appeared in target group
    # 6. Validate post content format
    # 7. Return detailed result
```

### C. Content Validators

**Weather post validator:**
```python
def validate_weather_post(message_text):
    """Validate weather post format and content."""
    checks = {
        "has_header": "🌤️ Weather |" in message_text,
        "has_date": check_date_format(message_text),
        "has_6_cities": count_cities(message_text) == 6,
        "has_emojis": check_weather_emojis(message_text),
        "format_correct": check_country_blocks(message_text),
        "temps_realistic": check_temperature_ranges(message_text)
    }
    return checks
```

**Status command validator:**
```python
def validate_status_response(message_text):
    """Validate status command response."""
    checks = {
        "has_budget": "💰 Budget" in message_text,
        "has_llm_status": "🤖 LLM Status" in message_text,
        "has_post_counts": "📈 Posts Today" in message_text,
        "has_service_info": "✅ Service Running" in message_text
    }
    return checks
```

---

## Content Validation Checklist

### Weather Posts 🌤️

**Format:**
- [ ] Header: `🌤️ Weather | DD Mon YYYY`
- [ ] Date format is correct
- [ ] All 6 cities present (London, Bila Tserkva, Poltava, Bengaluru, Cyprus, Poland)
- [ ] Grouped by country (UK, Ukraine, India, Cyprus, Poland)
- [ ] Each country has weather emoji (☀️☁️🌧️❄️⛈️🌫️⛅)
- [ ] Temperature format: `City: day/night°C`
- [ ] No extra spaces or formatting issues

**Content Quality:**
- [ ] Temperatures are realistic for season and location
- [ ] Weather emojis match typical weather for location
- [ ] No negative temperatures for tropical cities
- [ ] No extreme temperatures (> 50°C or < -40°C)
- [ ] Day temperature > night temperature (usually)

**Example Valid Post:**
```
🌤️ Weather | 11 Jan 2026

☁️ UK
London: 8/3°C

❄️ Ukraine
Bila Tserkva: 6/-1°C
Poltava: 5/-2°C

☀️ India
Bengaluru: 27/15°C

☀️ Cyprus
Cyprus: 17/10°C

☁️ Poland
Poland: 4/-3°C
```

### Status Response 📊

**Required Sections:**
- [ ] Budget section (spent, daily limit, calls, tokens)
- [ ] LLM status (enabled/disabled, model name)
- [ ] Post counts (morning, evening, person, tech)
- [ ] Service info (control chat, target group)

**Example Valid Response:**
```
📊 Group Posts Service Status

💰 Budget
Spent today: $0.05
Daily budget: $2.00
Calls today: 3
Tokens used: 1250

🤖 LLM Status
✅ Enabled and available
Model: gpt-4o-mini

📈 Posts Today
🌍 Morning travel: 1
🚀 Evening travel: 1
👤 Person: 1
🔧 Tech: 1

✅ Service Running
Control chat: me
Target: @Travel
```

### Travel Posts 🚀

**Morning post:**
- [ ] Header with emoji and "Morning Travel"
- [ ] 3 countries
- [ ] Morning drink for each country
- [ ] Activities list
- [ ] Interesting fact
- [ ] Photo from Unsplash

**Evening post:**
- [ ] Header with emoji and "Evening Travel"
- [ ] 3 countries
- [ ] Signature dish for each country
- [ ] Dish ingredients
- [ ] Activities list
- [ ] Interesting fact
- [ ] Photo from Unsplash

### Person Posts 👤

**Required:**
- [ ] Person name and title
- [ ] Birth year (or birth-death years)
- [ ] Main contribution
- [ ] Photo
- [ ] Is alive flag (2/3 alive, 1/3 deceased over 3 posts)
- [ ] Is electrical flag (1/3 electrical over 3 posts)

### Job Posts 💼

**Required:**
- [ ] 3 different job postings
- [ ] City: London
- [ ] Area: Canary Wharf
- [ ] Job titles: DevOps/MLOps/SRE/System Engineer
- [ ] Salary >= £60,000
- [ ] Company rating > 4
- [ ] Valid LinkedIn URL
- [ ] NOT remote
- [ ] AI-related (must have AI keywords in description)
- [ ] NOT FAANG, banks, or AI-only companies

---

## Test Result Format

**Current (BAD):**
```
✅ Command 'weather' sent successfully
✅ Successful: 1/1
```

**Proposed (GOOD):**
```
[1/14] Testing: 'weather'
------------------------------------------------------------
📤 Sent command: 'weather'
⏳ Waiting for response...
✅ Bot replied in 3.2s
✅ Post appeared in group
📋 Content validation:
   ✅ Format correct
   ✅ All 6 cities present
   ✅ Weather emojis present
   ✅ Temperatures realistic
   ✅ Date format correct
⏱️  Total time: 8.5s

Result: ✅ PASS
```

**If validation fails:**
```
[1/14] Testing: 'weather'
------------------------------------------------------------
📤 Sent command: 'weather'
⏳ Waiting for response...
✅ Bot replied in 3.2s
✅ Post appeared in group
📋 Content validation:
   ✅ Format correct
   ❌ Missing city: Poland
   ✅ Weather emojis present
   ❌ Temperature unrealistic: Bengaluru: -5/10°C (tropical city with freezing temps!)
   ✅ Date format correct
⏱️  Total time: 8.5s

Result: ❌ FAIL (2 checks failed)
```

---

## Implementation Priority

### Phase 1: Critical ⚠️
1. Add service health check before running tests
2. Add response waiting (check if bot replied)
3. Add basic content validation (format, required fields)

### Phase 2: Important 📊
4. Add timing measurements
5. Add detailed validation per content type
6. Add content quality checks (realistic values)

### Phase 3: Nice to Have ✨
7. Add screenshot/photo validation
8. Add link validation (URLs work)
9. Add duplicate content detection
10. Add performance benchmarking

---

## Usage

### Manual Testing Checklist

**Before running automated tests:**
1. [ ] Main service is running in Terminal 1
2. [ ] `.env` file is configured
3. [ ] LLM budget is available (`status` command)
4. [ ] Target group is configured
5. [ ] Bot has admin permissions in group

**When running test:**
1. [ ] Check Terminal 1 for logs (command received?)
2. [ ] Check Saved Messages (bot replied?)
3. [ ] Check target group (post appeared?)
4. [ ] Verify post format matches spec
5. [ ] Verify content quality (realistic data)

**If test fails:**
1. Check main service logs in Terminal 1
2. Check if command was received
3. Check if there are errors in processing
4. Check LLM budget status
5. Check API keys are valid
6. Verify group/channel configuration

---

## Known Issues to Fix

1. **Test shows success even when service is down** → Add health check
2. **No validation of bot response** → Add response listener
3. **No validation of post content** → Add format validators
4. **Fixed 15s delay insufficient for slow LLM** → Add dynamic waiting
5. **No way to verify post appeared in group** → Add group message checker
6. **Can't distinguish between send failure and processing failure** → Add detailed status codes
7. **No retry mechanism for flaky API calls** → Add retry logic
8. **No logging of validation failures** → Add detailed failure logs

---

## Next Steps

1. Create `validators.py` with content validation functions
2. Update `test_services.py` to use validators
3. Add response waiting mechanism
4. Add health check before tests
5. Add detailed test result reporting
6. Document expected format for each post type
