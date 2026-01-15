#!/usr/bin/env python3
"""Test script to check if OpenWeatherMap API is working correctly."""
import os
import sys
import requests

# Try to load dotenv if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not required

def test_weather_api():
    """Test OpenWeatherMap API for London."""
    api_key = os.getenv("OPENWEATHER_API_KEY", "")
    
    if not api_key:
        print("❌ OPENWEATHER_API_KEY not set in .env file!")
        print("💡 Add: OPENWEATHER_API_KEY=your_key_here")
        print("💡 Or set environment variable: export OPENWEATHER_API_KEY=your_key")
        return
    
    print(f"✅ API key found (length: {len(api_key)})")
    print(f"🔑 First 10 chars: {api_key[:10]}...")
    print()
    
    # Test London with One Call API 3.0
    # London coordinates
    lat = 51.5074
    lon = -0.1278
    
    url = "https://api.openweathermap.org/data/3.0/onecall"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": api_key,
        "units": "metric"
    }
    
    try:
        print(f"🌤️ Fetching weather for London using One Call API 3.0...")
        print(f"📡 URL: {url}")
        print(f"📋 Params: lat={lat}, lon={lon}, units={params['units']}")
        print()
        
        response = requests.get(url, params=params, timeout=10.0)
        
        print(f"📊 Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            # One Call API 3.0 structure
            current = data.get("current", {})
            daily = data.get("daily", [])
            
            temp_current = current.get("temp", 0)
            feels_like = current.get("feels_like", 0)
            
            # Get today's forecast
            today_forecast = daily[0] if daily else {}
            temp_max = today_forecast.get("temp", {}).get("max", temp_current)
            temp_min = today_forecast.get("temp", {}).get("min", temp_current)
            
            weather_main = current.get("weather", [{}])[0].get("main", "")
            weather_desc = current.get("weather", [{}])[0].get("description", "")
            
            print("✅ SUCCESS! Weather data received from One Call API 3.0:")
            print(f"   🌡️  Current: {round(temp_current)}°C")
            print(f"   🌡️  Feels like: {round(feels_like)}°C")
            print(f"   📈 Max: {round(temp_max)}°C")
            print(f"   📉 Min: {round(temp_min)}°C")
            print(f"   ☁️  Condition: {weather_main}")
            print(f"   📝 Description: {weather_desc}")
            print()
            print("✅ One Call API 3.0 is working correctly!")
            print()
            print("💡 Subscription info:")
            print("   - First 1,000 calls/day: FREE")
            print("   - Default limit: 2,000 calls/day")
            print("   - Check usage: Personal account > OneCall statistics")
        else:
            print(f"❌ API returned error: {response.status_code}")
            print(f"📄 Response: {response.text[:500]}")
            if response.status_code == 401:
                print("💡 API key may not be activated yet!")
                print("   Activation can take several minutes after subscription.")
                print("   Wait a few minutes and try again.")
            elif response.status_code == 429:
                print("💡 Rate limit reached!")
                print("   Check your daily limit in account settings.")
            elif response.status_code == 403:
                print("💡 API key doesn't have access to One Call API 3.0!")
                print("   Check your subscription status.")
                
    except requests.exceptions.RequestException as e:
        print(f"❌ HTTP error: {e}")
        if hasattr(e, 'response') and e.response is not None:
            if e.response.status_code == 401:
                print("💡 This usually means invalid API key!")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_weather_api()
