#!/usr/bin/env python3
"""Check current OpenWeatherMap API call count for today."""
import json
from pathlib import Path
from datetime import date

WEATHER_API_DAILY_LIMIT = 10
counter_file = Path("data/weather_api_calls.json")

if counter_file.exists():
    data = json.loads(counter_file.read_text(encoding="utf-8"))
    today = date.today().isoformat()
    
    if data.get("date") == today:
        calls = data.get("calls", 0)
        remaining = WEATHER_API_DAILY_LIMIT - calls
        print(f"📊 OpenWeatherMap API calls today: {calls}/{WEATHER_API_DAILY_LIMIT}")
        print(f"✅ Remaining: {remaining} calls")
        if calls >= WEATHER_API_DAILY_LIMIT:
            print("⚠️  Limit reached! Will use LLM or template.")
    else:
        print(f"📊 OpenWeatherMap API calls today: 0/{WEATHER_API_DAILY_LIMIT}")
        print("✅ All calls available (new day)")
else:
    print(f"📊 OpenWeatherMap API calls today: 0/{WEATHER_API_DAILY_LIMIT}")
    print("✅ All calls available (no calls made today)")
