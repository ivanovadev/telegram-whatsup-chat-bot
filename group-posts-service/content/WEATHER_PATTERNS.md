# Weather Formatting Patterns

Documentation of possible patterns for formatting weather posts.

**Current pattern: #1 (Most Readable)**

---

## Pattern 1: Blocks by Country with Weather Emoji (Currently Used) ✅

**Advantages:**
- Best readability
- Day/Night format is easiest to scan
- Weather emoji shows country conditions
- Clean, informative

**Example:**
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

**Implementation:**
```python
message = f"🌤️ Weather | {date_str}\n\n"

# Group with emoji
by_country = {}
for city_weather in weather_data:
    country = city_weather.get("country", "")
    emoji = city_weather.get("emoji", "☀️")
    if country not in by_country:
        by_country[country] = {"emoji": emoji, "cities": []}
    by_country[country]["cities"].append(city_weather)

for country, data in by_country.items():
    emoji = data["emoji"]
    message += f"{emoji} {country}\n"
    for city_data in data["cities"]:
        city = city_data["city"]
        temp_day = city_data["temp_day"]
        temp_night = city_data["temp_night"]
        message += f"{city}: {temp_day}/{temp_night}°C\n"
    message += "\n"
```

---

## Pattern 2: Compact "Table" View

**Advantages:**
- Everything on one screen
- Quick scanning
- Short country codes

**Example:**
```
🌤️ Weather | 11 Jan 2026
UK · London: 8/3°C
UA · Bila Tserkva: 6/-1°C
UA · Poltava: 5/-2°C
IN · Bengaluru: 27/15°C
CY · Cyprus: 17/10°C
PL · Poland: 4/-3°C
```

**Implementation:**
```python
message = f"🌤️ Weather | {date_str}\n"
for city_weather in weather_data:
    country_code = city_weather.get("country_code", "")
    city = city_weather.get("city", "")
    temp_day = city_weather.get("temp_day", 0)
    temp_night = city_weather.get("temp_night", 0)
    message += f"{country_code} · {city}: {temp_day}/{temp_night}°C\n"
```

---

## Pattern 3: With Average Temperature

**Advantages:**
- Shows average temperature
- Useful for planning

**Disadvantages:**
- avg might be unnecessary noise

**Example:**
```
🌤️ Weather | 11 Jan 2026

UK
London: 8/3°C (avg 5.5)

Ukraine
Bila Tserkva: 6/-1°C (avg 2.5)
Poltava: 5/-2°C (avg 1.5)

India
Bengaluru: 27/15°C (avg 21)
```

**Implementation:**
```python
for city_data in cities:
    city = city_data["city"]
    temp_day = city_data["temp_day"]
    temp_night = city_data["temp_night"]
    temp_avg = city_data["temp_avg"]
    message += f"{city}: {temp_day}/{temp_night}°C (avg {temp_avg})\n"
```

---

## Pattern 4: "Top Contrasts" (Fun Format)

**Advantages:**
- Interesting, attention-grabbing
- Shows extremes

**Example:**
```
🌤️ Weather | 11 Jan 2026
🔥 Warmest: Bengaluru 27/15°C
❄️ Coldest night: Poland -3°C
🌫️ Most mild: Cyprus 17/10°C

All cities
London 8/3 · Bila Tserkva 6/-1 · Poltava 5/-2 · Cyprus 17/10 · Poland 4/-3
```

**Implementation:**
```python
# Find extremes
warmest = max(weather_data, key=lambda x: x["temp_day"])
coldest_night = min(weather_data, key=lambda x: x["temp_night"])
most_mild = min(weather_data, key=lambda x: abs(x["temp_day"] - x["temp_night"]))

message = f"🌤️ Weather | {date_str}\n"
message += f"🔥 Warmest: {warmest['city']} {warmest['temp_day']}/{warmest['temp_night']}°C\n"
message += f"❄️ Coldest night: {coldest_night['city']} {coldest_night['temp_night']}°C\n"
message += f"🌫️ Most mild: {most_mild['city']} {most_mild['temp_day']}/{most_mild['temp_night']}°C\n\n"
message += "All cities\n"
message += " · ".join([f"{c['city']} {c['temp_day']}/{c['temp_night']}" for c in weather_data])
```

---

## Pattern 5: With Flag Emojis

**Advantages:**
- Visually appealing
- Easy to distinguish countries

**Disadvantages:**
- Too many emojis can be "noisy"

**Example:**
```
🌤️ Weather | 11 Jan 2026

🇬🇧 UK
• London 8/3°C

🇺🇦 Ukraine
• Bila Tserkva 6/-1°C
• Poltava 5/-2°C

🇮🇳 India
• Bengaluru 27/15°C

🇨🇾 Cyprus
• Cyprus 17/10°C

🇵🇱 Poland
• Poland 4/-3°C
```

**Implementation:**
```python
country_flags = {
    "UK": "🇬🇧",
    "Ukraine": "🇺🇦", 
    "India": "🇮🇳",
    "Cyprus": "🇨🇾",
    "Poland": "🇵🇱"
}

for country, cities in by_country.items():
    flag = country_flags.get(country, "")
    message += f"{flag} {country}\n"
    for city_data in cities:
        city = city_data["city"]
        temp_day = city_data["temp_day"]
        temp_night = city_data["temp_night"]
        message += f"• {city} {temp_day}/{temp_night}°C\n"
    message += "\n"
```

---

## General Rules (for all patterns)

1. **Consistency**: One format for the entire post
2. **Emoji**: 1-2 maximum, not next to every line
3. **Day/Night**: Format `8/3°C` reads better than `Day: 8°C, Night: 3°C`
4. **Names**: Either country+city everywhere, or only cities
5. **Automation**: If from bot, stick to 1 template always

---

## Switching Patterns

To change the pattern, edit `_format_weather_message()` in `services/channel_handler.py`:

```python
def _format_weather_message(self, content: dict) -> str:
    # Change implementation here
    # See examples above for each pattern
    pass
```

Current implementation: **Pattern 1 (Blocks by Country)**
