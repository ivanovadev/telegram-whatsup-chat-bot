"""Generate content for weather posts."""
import os
import logging
import json
from pathlib import Path
from typing import Dict, Optional, List
from openai import OpenAI
from datetime import datetime, date
import httpx

logger = logging.getLogger(__name__)

# One Call API 3.0: First 1,000 calls/day free, then charged
# Default limit: 2,000 calls/day (can be changed in account settings)
# We set conservative limit to avoid charges
WEATHER_API_DAILY_LIMIT = 10  # Conservative limit (you can increase if needed)


class WeatherContentGenerator:
    """Generate weather content for multiple cities."""
    
    CITIES = [
        {"name": "London", "country": "UK", "country_code": "GB", "lat": 51.5074, "lon": -0.1278},
        {"name": "Bila Tserkva", "country": "Ukraine", "country_code": "UA", "lat": 49.8094, "lon": 30.1121},
        {"name": "Poltava", "country": "Ukraine", "country_code": "UA", "lat": 49.5883, "lon": 34.5514},
        {"name": "Bengaluru", "country": "India", "country_code": "IN", "lat": 12.9716, "lon": 77.5946},
        {"name": "Protaras", "country": "Cyprus", "country_code": "CY", "lat": 35.0125, "lon": 34.0583},
        {"name": "Kraków", "country": "Poland", "country_code": "PL", "lat": 50.0647, "lon": 19.9450}
    ]
    
    def __init__(self, budget_guard):
        """Initialize weather content generator."""
        self.budget_guard = budget_guard
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-5.2")
        self.llm_enabled = os.getenv("LLM_ENABLED", "off").lower() == "on"
        self.weather_api_key = os.getenv("OPENWEATHER_API_KEY", "")
        
        # API call counter file (for free tier limit: 10 calls/day)
        self.api_counter_file = Path("data/weather_api_calls.json")
        self.api_counter_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Log which method will be used
        if self.weather_api_key:
            logger.info(f"✅ OpenWeatherMap API key found (length: {len(self.weather_api_key)})")
            logger.info(f"🌐 Using One Call API 3.0 (subscription active)")
            logger.info(f"📊 Daily limit: {WEATHER_API_DAILY_LIMIT} calls per day (first 1,000 free)")
        else:
            logger.warning("⚠️ OPENWEATHER_API_KEY not set - will use LLM or template")
        
        if self.llm_enabled and self.openai_api_key:
            self.client = OpenAI(api_key=self.openai_api_key)
        else:
            self.client = None
            if not self.weather_api_key:
                logger.warning("⚠️ LLM disabled and no API key - will use static template")
    
    def _get_api_calls_today(self) -> Dict:
        """Get API call counter for today."""
        today = date.today().isoformat()
        
        try:
            if self.api_counter_file.exists():
                data = json.loads(self.api_counter_file.read_text(encoding="utf-8"))
                # Reset if it's a new day
                if data.get("date") != today:
                    return {"date": today, "calls": 0}
                return data
        except Exception as e:
            logger.warning(f"Error reading API counter: {e}")
        
        return {"date": today, "calls": 0}
    
    def _check_api_limit(self) -> bool:
        """Check if API call limit is reached. Returns True if can make call, False if limit reached."""
        counter = self._get_api_calls_today()
        current_calls = counter.get("calls", 0)
        
        if current_calls >= WEATHER_API_DAILY_LIMIT:
            logger.warning(f"⚠️ API call limit reached: {current_calls}/{WEATHER_API_DAILY_LIMIT} calls today")
            logger.info(f"💡 Using LLM or template instead of API (free tier limit)")
            return False
        
        return True
    
    def _increment_api_call(self) -> None:
        """Increment API call counter after successful API call."""
        today = date.today().isoformat()
        counter = self._get_api_calls_today()
        
        # Increment counter
        counter["date"] = today
        counter["calls"] = counter.get("calls", 0) + 1
        
        try:
            self.api_counter_file.write_text(
                json.dumps(counter, indent=2),
                encoding="utf-8"
            )
            logger.info(f"📊 API calls today: {counter['calls']}/{WEATHER_API_DAILY_LIMIT}")
        except Exception as e:
            logger.warning(f"Error saving API counter: {e}")
    
    async def generate_weather_post(self) -> Optional[Dict]:
        """Generate weather post for all cities."""
        if self.weather_api_key:
            # Check API call limit (free tier: 10 calls/day)
            if not self._check_api_limit():
                # Limit reached, use fallback
                if self.client and self.llm_enabled:
                    logger.info("🤖 Using LLM for weather generation (API limit reached)")
                    return self._generate_with_llm()
                else:
                    logger.warning("⚠️ Using static template (API limit reached, LLM not available)")
                    return self._generate_template()
            
            logger.info("🌤️ Using OpenWeatherMap One Call API 3.0 for real-time weather data")
            result = await self._generate_with_api()
            if result:
                # Only increment counter on successful API call
                self._increment_api_call()
                logger.info(f"✅ Successfully fetched weather from API for {len(result.get('weather', []))} cities")
                return result
            else:
                logger.warning("⚠️ API call failed, falling back to LLM or template (not counting as API call)")
                # Don't count failed calls, but still use fallback
                if self.client and self.llm_enabled:
                    return self._generate_with_llm()
                else:
                    return self._generate_template()
        elif self.client and self.llm_enabled:
            logger.info("🤖 Using LLM for weather generation (API key not available)")
            return self._generate_with_llm()
        else:
            logger.warning("⚠️ Using static template (API key and LLM not available)")
            return self._generate_template()
    
    async def _generate_with_api(self) -> Optional[Dict]:
        """Generate weather using OpenWeatherMap One Call API 3.0."""
        try:
            weather_data = []
            
            async with httpx.AsyncClient() as client:
                for city_info in self.CITIES:
                    city_name = city_info["name"]
                    lat = city_info.get("lat")
                    lon = city_info.get("lon")
                    
                    if not lat or not lon:
                        logger.warning(f"⚠️ Missing coordinates for {city_name}, skipping")
                        continue
                    
                    try:
                        # Use One Call API 3.0
                        url = "https://api.openweathermap.org/data/3.0/onecall"
                        params = {
                            "lat": lat,
                            "lon": lon,
                            "appid": self.weather_api_key,
                            "units": "metric"  # Celsius
                        }
                        logger.debug(f"🌤️ Fetching weather for {city_name} (lat={lat}, lon={lon}) using One Call API 3.0")
                        
                        response = await client.get(url, params=params, timeout=10.0)
                        response.raise_for_status()
                        data = response.json()
                        
                        # One Call API 3.0 response structure:
                        # - current: current weather
                        # - daily: forecast for next days
                        current = data.get("current", {})
                        daily = data.get("daily", [])
                        
                        # Current temperature
                        temp_current = current.get("temp", 0)
                        feels_like = current.get("feels_like", temp_current)
                        
                        # Get today's forecast (first day in daily array)
                        today_forecast = daily[0] if daily else {}
                        temp_max = today_forecast.get("temp", {}).get("max", temp_current)
                        temp_min = today_forecast.get("temp", {}).get("min", temp_current)
                        
                        # Weather condition
                        weather_main = current.get("weather", [{}])[0].get("main", "").lower()
                        weather_desc = current.get("weather", [{}])[0].get("description", "").lower()
                        
                        # Map weather to emoji
                        emoji = self._get_weather_emoji(weather_main, weather_desc)
                        
                        logger.info(f"✅ {city_name}: {round(temp_current)}°C (feels {round(feels_like)}°C), {weather_desc}, emoji: {emoji}")
                        
                        weather_data.append({
                            "city": city_name,
                            "country": city_info["country"],
                            "temp_current": round(temp_current),  # Current temperature
                            "feels_like": round(feels_like),  # Feels like
                            "temp_max": round(temp_max),  # Max (day)
                            "temp_min": round(temp_min),  # Min (night)
                            "emoji": emoji,
                            "condition": weather_main,
                            "description": weather_desc
                        })
                        
                    except httpx.HTTPStatusError as e:
                        logger.error(f"❌ HTTP error for {city_name}: {e.response.status_code} - {e.response.text[:200]}")
                        if e.response.status_code == 401:
                            logger.error("💡 API key may not be activated yet. Activation can take several minutes after subscription.")
                            logger.error("💡 Or check if API key is correct in .env file")
                        elif e.response.status_code == 429:
                            logger.error("💡 Rate limit reached! Check your daily limit in account settings.")
                        # Don't use fallback - skip this city
                        continue
                    except Exception as e:
                        logger.error(f"❌ Error fetching weather for {city_name}: {e}")
                        # Don't use fallback - skip this city
                        continue
            
            if not weather_data:
                logger.error("❌ No weather data fetched from API - all cities failed")
                logger.info("🔄 Falling back to LLM or template...")
                return self._generate_with_llm() if self.client and self.llm_enabled else self._generate_template()
            
            # Check if we got data for all cities
            if len(weather_data) < len(self.CITIES):
                logger.warning(f"⚠️ Only got weather for {len(weather_data)}/{len(self.CITIES)} cities")
                # Still return what we have, but log warning
            
            logger.info(f"✅ Successfully fetched weather for {len(weather_data)} cities from OpenWeatherMap API")
            return {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "weather": weather_data
            }
            
        except Exception as e:
            logger.error(f"❌ Critical error generating weather with API: {e}", exc_info=True)
            logger.info("🔄 Falling back to LLM or template...")
            return self._generate_with_llm() if self.client and self.llm_enabled else self._generate_template()
    
    def _get_weather_emoji(self, weather_main: str, weather_desc: str) -> str:
        """Get emoji based on weather condition."""
        weather_lower = weather_main.lower()
        desc_lower = weather_desc.lower()
        
        if "rain" in weather_lower or "rain" in desc_lower:
            if "thunder" in desc_lower or "storm" in desc_lower:
                return "⛈️"  # Thunderstorm
            return "🌧️"  # Rain
        elif "snow" in weather_lower or "snow" in desc_lower:
            return "❄️"  # Snow
        elif "cloud" in weather_lower or "cloud" in desc_lower:
            if "few" in desc_lower or "scattered" in desc_lower:
                return "⛅"  # Partly cloudy
            return "☁️"  # Cloudy
        elif "clear" in weather_lower or "sun" in desc_lower:
            return "☀️"  # Sunny
        elif "mist" in weather_lower or "fog" in desc_lower:
            return "🌫️"  # Fog
        elif "haze" in weather_lower or "haze" in desc_lower:
            return "🌫️"  # Haze
        else:
            return "☀️"  # Default to sunny
    
    def _generate_with_llm(self) -> Optional[Dict]:
        """Generate weather using LLM."""
        try:
            current_date = datetime.now().strftime("%Y-%m-%d")
            
            cities_list = ", ".join([f"{c['name']} ({c['country']})" for c in self.CITIES])
            
            # Note for LLM: For Cyprus and Poland, use country name as city name
            
            # Get current month and season for realistic temperatures
            from datetime import datetime
            current_month = datetime.now().month
            current_season = "winter" if current_month in [12, 1, 2] else "spring" if current_month in [3, 4, 5] else "summer" if current_month in [6, 7, 8] else "autumn"
            
            prompt = f"""Generate REALISTIC CURRENT weather forecast for TODAY for the following cities:
{cities_list}

CRITICAL: Use REAL, ACCURATE weather based on:
- Current date: {current_date}
- Current season: {current_season}
- Current month: {current_month}
- Typical weather patterns for each location in this season

TEMPERATURE GUIDELINES (must be realistic):
- London (UK) in {current_season}: typical range
  * Winter: -2°C to 8°C (day), -5°C to 3°C (night)
  * Spring: 8°C to 15°C (day), 3°C to 8°C (night)
  * Summer: 18°C to 25°C (day), 12°C to 18°C (night)
  * Autumn: 8°C to 15°C (day), 5°C to 10°C (night)

- Ukraine (Bila Tserkva, Poltava) in {current_season}:
  * Winter: -15°C to -5°C (day), -20°C to -10°C (night) [VERY COLD, often snow ❄️]
  * Spring: 5°C to 15°C (day), 0°C to 8°C (night)
  * Summer: 20°C to 28°C (day), 12°C to 18°C (night)
  * Autumn: 5°C to 15°C (day), 0°C to 8°C (night)

- Bengaluru (India) in {current_season}:
  * Winter: 24°C to 28°C (day), 15°C to 20°C (night)
  * Spring: 28°C to 35°C (day), 20°C to 25°C (night)
  * Summer: 28°C to 35°C (day), 20°C to 25°C (night)
  * Autumn: 25°C to 30°C (day), 18°C to 23°C (night)

- Cyprus in {current_season}:
  * Winter: 15°C to 18°C (day), 8°C to 12°C (night)
  * Spring: 18°C to 25°C (day), 12°C to 18°C (night)
  * Summer: 28°C to 35°C (day), 20°C to 25°C (night)
  * Autumn: 22°C to 28°C (day), 15°C to 20°C (night)

- Poland in {current_season}:
  * Winter: -5°C to 2°C (day), -10°C to -3°C (night) [Cold, often snow ❄️]
  * Spring: 8°C to 15°C (day), 2°C to 8°C (night)
  * Summer: 20°C to 27°C (day), 12°C to 18°C (night)
  * Autumn: 8°C to 15°C (day), 3°C to 10°C (night)

For each city, provide:
1. Current temperature (realistic for {current_season} in that location, at current time of day) in Celsius
2. Feels like temperature in Celsius
3. Maximum temperature (day high) in Celsius
4. Minimum temperature (night low) in Celsius
5. Weather condition matching the season (e.g., winter in Ukraine = snow, cold; summer = sunny, warm)
6. Appropriate emoji (🌧️ rain, ☁️ cloudy, ☀️ sunny, ⛈️ thunderstorm, ❄️ snow, ⛅ partly cloudy, 🌫️ fog)

Format as JSON:
{{
  "date": "{current_date}",
  "weather": [
    {{
      "city": "London",
      "country": "UK",
      "temp_current": <realistic current temp for {current_season}>,
      "feels_like": <feels like temp>,
      "temp_max": <day maximum temp>,
      "temp_min": <night minimum temp>,
      "emoji": "☁️",
      "condition": "cloudy",
      "description": "overcast clouds"
    }},
    {{
      "city": "Bila Tserkva",
      "country": "Ukraine",
      "temp_current": <realistic current temp for {current_season}>,
      "feels_like": <feels like temp>,
      "temp_max": <day maximum temp>,
      "temp_min": <night minimum temp>,
      "emoji": "❄️",
      "condition": "snow",
      "description": "light snow"
    }},
    {{
      "city": "Poltava",
      "country": "Ukraine",
      "temp_current": <realistic current temp for {current_season}>,
      "feels_like": <feels like temp>,
      "temp_max": <day maximum temp>,
      "temp_min": <night minimum temp>,
      "emoji": "❄️",
      "condition": "snow",
      "description": "snow"
    }},
    {{
      "city": "Bengaluru",
      "country": "India",
      "temp_current": <realistic current temp for {current_season}>,
      "feels_like": <feels like temp>,
      "temp_max": <day maximum temp>,
      "temp_min": <night minimum temp>,
      "emoji": "☀️",
      "condition": "clear",
      "description": "clear sky"
    }},
    {{
      "city": "Protaras",
      "country": "Cyprus",
      "temp_current": <realistic current temp for {current_season}>,
      "feels_like": <feels like temp>,
      "temp_max": <day maximum temp>,
      "temp_min": <night minimum temp>,
      "emoji": "☀️",
      "condition": "clear",
      "description": "clear sky"
    }},
    {{
      "city": "Kraków",
      "country": "Poland",
      "temp_current": <realistic current temp for {current_season}>,
      "feels_like": <feels like temp>,
      "temp_max": <day maximum temp>,
      "temp_min": <night minimum temp>,
      "emoji": "❄️",
      "condition": "snow",
      "description": "light snow"
    }}
  ]
}}

CRITICAL REQUIREMENTS:
- Temperatures MUST be realistic for the current season ({current_season}) and location
- Ukraine and Poland in winter: temperatures should be NEGATIVE (below 0°C) with snow ❄️
- Current temp should be realistic for current time of day (between min and max)
- Use accurate weather conditions for the season
- All temperatures in Celsius
- Emoji must match weather condition
- Use exact city names: Protaras for Cyprus, Kraków for Poland
- Include realistic description (e.g., "light snow", "clear sky", "overcast clouds")
- Current date: {current_date}

Return ONLY valid JSON, no additional text."""

            response = self.client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {"role": "system", "content": "You are a weather forecaster. Generate realistic current weather forecasts for cities. Always return valid JSON only, no additional text."},
                    {"role": "user", "content": prompt}
                ],
                max_completion_tokens=800,
                response_format={"type": "json_object"}
            )
            
            import json
            import re
            content = response.choices[0].message.content.strip()
            
            # Try to extract JSON if wrapped in markdown code blocks
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
            if json_match:
                content = json_match.group(1)
            
            # Try to find JSON object in the response
            if not content.startswith('{'):
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    content = json_match.group(0)
            
            # Validate and parse JSON
            if not content or not content.strip():
                logger.error("Empty response from LLM for weather")
                return self._generate_template()
            
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error for weather: {e}. Content: {content[:200]}")
                try:
                    content = content[content.find('{'):]
                    content = content[:content.rfind('}') + 1]
                    data = json.loads(content)
                except Exception as e2:
                    logger.error(f"Failed to fix JSON for weather: {e2}")
                    return self._generate_template()
            
            # Record usage
            tokens_used = response.usage.total_tokens
            # Approximate cost for gpt-5.2 (~$0.30 per 1M tokens)
            cost_per_1k = 0.30 / 1000
            estimated_cost = (tokens_used / 1000) * cost_per_1k
            self.budget_guard.record_llm_call(tokens_used, estimated_cost)
            
            return data
            
        except Exception as e:
            logger.error(f"LLM error generating weather: {e}")
            return self._generate_template()
    
    def _generate_template(self) -> Dict:
        """Generate template weather when API/LLM unavailable - uses seasonal appropriate temperatures."""
        # Get current season for realistic temperatures
        current_month = datetime.now().month
        
        # Winter templates (Dec-Feb): cold, snow in Ukraine/Poland
        if current_month in [12, 1, 2]:
            weather_data = [
                {"city": "London", "country": "UK", "temp_current": 4, "feels_like": 2, "temp_max": 6, "temp_min": 2, "emoji": "☁️", "condition": "cloudy", "description": "overcast clouds"},
                {"city": "Bila Tserkva", "country": "Ukraine", "temp_current": -12, "feels_like": -15, "temp_max": -8, "temp_min": -15, "emoji": "❄️", "condition": "snow", "description": "light snow"},
                {"city": "Poltava", "country": "Ukraine", "temp_current": -13, "feels_like": -16, "temp_max": -10, "temp_min": -16, "emoji": "❄️", "condition": "snow", "description": "snow"},
                {"city": "Bengaluru", "country": "India", "temp_current": 22, "feels_like": 22, "temp_max": 26, "temp_min": 18, "emoji": "☀️", "condition": "clear", "description": "clear sky"},
                {"city": "Protaras", "country": "Cyprus", "temp_current": 13, "feels_like": 12, "temp_max": 16, "temp_min": 10, "emoji": "⛅", "condition": "clouds", "description": "few clouds"},
                {"city": "Kraków", "country": "Poland", "temp_current": -5, "feels_like": -8, "temp_max": -2, "temp_min": -7, "emoji": "❄️", "condition": "snow", "description": "light snow"}
            ]
        # Spring templates (Mar-May)
        elif current_month in [3, 4, 5]:
            weather_data = [
                {"city": "London", "country": "UK", "temp_current": 9, "feels_like": 8, "temp_max": 12, "temp_min": 6, "emoji": "⛅", "condition": "clouds", "description": "few clouds"},
                {"city": "Bila Tserkva", "country": "Ukraine", "temp_current": 7, "feels_like": 5, "temp_max": 10, "temp_min": 3, "emoji": "☁️", "condition": "clouds", "description": "overcast clouds"},
                {"city": "Poltava", "country": "Ukraine", "temp_current": 8, "feels_like": 6, "temp_max": 11, "temp_min": 4, "emoji": "⛅", "condition": "clouds", "description": "scattered clouds"},
                {"city": "Bengaluru", "country": "India", "temp_current": 27, "feels_like": 28, "temp_max": 32, "temp_min": 22, "emoji": "☀️", "condition": "clear", "description": "clear sky"},
                {"city": "Protaras", "country": "Cyprus", "temp_current": 19, "feels_like": 18, "temp_max": 22, "temp_min": 15, "emoji": "☀️", "condition": "clear", "description": "clear sky"},
                {"city": "Kraków", "country": "Poland", "temp_current": 9, "feels_like": 7, "temp_max": 12, "temp_min": 5, "emoji": "☁️", "condition": "clouds", "description": "broken clouds"}
            ]
        # Summer templates (Jun-Aug)
        elif current_month in [6, 7, 8]:
            weather_data = [
                {"city": "London", "country": "UK", "temp_current": 19, "feels_like": 18, "temp_max": 22, "temp_min": 15, "emoji": "⛅", "condition": "clouds", "description": "scattered clouds"},
                {"city": "Bila Tserkva", "country": "Ukraine", "temp_current": 21, "feels_like": 21, "temp_max": 26, "temp_min": 16, "emoji": "☀️", "condition": "clear", "description": "clear sky"},
                {"city": "Poltava", "country": "Ukraine", "temp_current": 22, "feels_like": 22, "temp_max": 27, "temp_min": 17, "emoji": "☀️", "condition": "clear", "description": "clear sky"},
                {"city": "Bengaluru", "country": "India", "temp_current": 26, "feels_like": 27, "temp_max": 30, "temp_min": 21, "emoji": "🌧️", "condition": "rain", "description": "moderate rain"},
                {"city": "Protaras", "country": "Cyprus", "temp_current": 28, "feels_like": 29, "temp_max": 32, "temp_min": 23, "emoji": "☀️", "condition": "clear", "description": "clear sky"},
                {"city": "Kraków", "country": "Poland", "temp_current": 19, "feels_like": 18, "temp_max": 24, "temp_min": 14, "emoji": "⛅", "condition": "clouds", "description": "few clouds"}
            ]
        # Autumn templates (Sep-Nov)
        else:
            weather_data = [
                {"city": "London", "country": "UK", "temp_current": 11, "feels_like": 10, "temp_max": 13, "temp_min": 8, "emoji": "🌧️", "condition": "rain", "description": "light rain"},
                {"city": "Bila Tserkva", "country": "Ukraine", "temp_current": 7, "feels_like": 5, "temp_max": 10, "temp_min": 4, "emoji": "☁️", "condition": "clouds", "description": "overcast clouds"},
                {"city": "Poltava", "country": "Ukraine", "temp_current": 8, "feels_like": 6, "temp_max": 11, "temp_min": 5, "emoji": "☁️", "condition": "clouds", "description": "broken clouds"},
                {"city": "Bengaluru", "country": "India", "temp_current": 24, "feels_like": 24, "temp_max": 27, "temp_min": 20, "emoji": "⛅", "condition": "clouds", "description": "scattered clouds"},
                {"city": "Protaras", "country": "Cyprus", "temp_current": 22, "feels_like": 22, "temp_max": 25, "temp_min": 18, "emoji": "☀️", "condition": "clear", "description": "clear sky"},
                {"city": "Kraków", "country": "Poland", "temp_current": 8, "feels_like": 6, "temp_max": 10, "temp_min": 5, "emoji": "🌧️", "condition": "rain", "description": "light rain"}
            ]
        
        return {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "weather": weather_data
        }
