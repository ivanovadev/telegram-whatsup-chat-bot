"""Generate content for weather posts."""
import os
import logging
from typing import Dict, Optional, List
from openai import OpenAI
from datetime import datetime
import httpx

logger = logging.getLogger(__name__)


class WeatherContentGenerator:
    """Generate weather content for multiple cities."""
    
    CITIES = [
        {"name": "London", "country": "UK", "country_code": "GB"},
        {"name": "Bila Tserkva", "country": "Ukraine", "country_code": "UA"},
        {"name": "Poltava", "country": "Ukraine", "country_code": "UA"},
        {"name": "Bengaluru", "country": "India", "country_code": "IN"},
        {"name": "Protaras", "country": "Cyprus", "country_code": "CY"},
        {"name": "Kraków", "country": "Poland", "country_code": "PL"}
    ]
    
    def __init__(self, budget_guard):
        """Initialize weather content generator."""
        self.budget_guard = budget_guard
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.llm_enabled = os.getenv("LLM_ENABLED", "off").lower() == "on"
        self.weather_api_key = os.getenv("OPENWEATHER_API_KEY", "")
        
        if self.llm_enabled and self.openai_api_key:
            self.client = OpenAI(api_key=self.openai_api_key)
        else:
            self.client = None
            logger.warning("LLM disabled for weather content")
    
    async def generate_weather_post(self) -> Optional[Dict]:
        """Generate weather post for all cities."""
        if self.weather_api_key:
            return await self._generate_with_api()
        elif self.client and self.llm_enabled:
            return self._generate_with_llm()
        else:
            return self._generate_template()
    
    async def _generate_with_api(self) -> Optional[Dict]:
        """Generate weather using OpenWeatherMap API."""
        try:
            weather_data = []
            
            async with httpx.AsyncClient() as client:
                for city_info in self.CITIES:
                    city_name = city_info["name"]
                    country_code = city_info["country_code"]
                    
                    try:
                        url = "https://api.openweathermap.org/data/2.5/weather"
                        params = {
                            "q": f"{city_name},{country_code}",
                            "appid": self.weather_api_key,
                            "units": "metric"  # Celsius
                        }
                        
                        response = await client.get(url, params=params, timeout=10.0)
                        response.raise_for_status()
                        data = response.json()
                        
                        # Extract weather information
                        temp = data.get("main", {}).get("temp", 0)
                        temp_min = data.get("main", {}).get("temp_min", 0)
                        temp_max = data.get("main", {}).get("temp_max", 0)
                        weather_main = data.get("weather", [{}])[0].get("main", "").lower()
                        weather_desc = data.get("weather", [{}])[0].get("description", "").lower()
                        
                        # Map weather to emoji
                        emoji = self._get_weather_emoji(weather_main, weather_desc)
                        
                        weather_data.append({
                            "city": city_name,
                            "country": city_info["country"],
                            "temp_day": round(temp_max),
                            "temp_night": round(temp_min),
                            "temp_avg": round(temp),
                            "emoji": emoji,
                            "condition": weather_main
                        })
                        
                    except Exception as e:
                        logger.warning(f"Error fetching weather for {city_name}: {e}")
                        # Use fallback
                        weather_data.append({
                            "city": city_name,
                            "country": city_info["country"],
                            "temp_day": 20,
                            "temp_night": 15,
                            "temp_avg": 18,
                            "emoji": "☀️",
                            "condition": "clear"
                        })
            
            return {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "weather": weather_data
            }
            
        except Exception as e:
            logger.error(f"Error generating weather with API: {e}")
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
1. Day temperature (realistic for {current_season} in that location) in Celsius
2. Night temperature (realistic for {current_season} in that location) in Celsius
3. Average temperature in Celsius
4. Weather condition matching the season (e.g., winter in Ukraine = snow, cold; summer = sunny, warm)
5. Appropriate emoji (🌧️ rain, ☁️ cloudy, ☀️ sunny, ⛈️ thunderstorm, ❄️ snow, ⛅ partly cloudy, 🌫️ fog)

Format as JSON:
{{
  "date": "{current_date}",
  "weather": [
    {{
      "city": "London",
      "country": "UK",
      "temp_day": <realistic day temp for {current_season}>,
      "temp_night": <realistic night temp for {current_season}>,
      "temp_avg": <average of day/night>,
      "emoji": "☁️",
      "condition": "cloudy"
    }},
    {{
      "city": "Bila Tserkva",
      "country": "Ukraine",
      "temp_day": <realistic day temp for {current_season}>,
      "temp_night": <realistic night temp for {current_season}>,
      "temp_avg": <average of day/night>,
      "emoji": "❄️",
      "condition": "snow"
    }},
    {{
      "city": "Poltava",
      "country": "Ukraine",
      "temp_day": <realistic day temp for {current_season}>,
      "temp_night": <realistic night temp for {current_season}>,
      "temp_avg": <average of day/night>,
      "emoji": "❄️",
      "condition": "snow"
    }},
    {{
      "city": "Bengaluru",
      "country": "India",
      "temp_day": <realistic day temp for {current_season}>,
      "temp_night": <realistic night temp for {current_season}>,
      "temp_avg": <average of day/night>,
      "emoji": "☀️",
      "condition": "sunny"
    }},
    {{
      "city": "Protaras",
      "country": "Cyprus",
      "temp_day": <realistic day temp for {current_season}>,
      "temp_night": <realistic night temp for {current_season}>,
      "temp_avg": <average of day/night>,
      "emoji": "☀️",
      "condition": "sunny"
    }},
    {{
      "city": "Kraków",
      "country": "Poland",
      "temp_day": <realistic day temp for {current_season}>,
      "temp_night": <realistic night temp for {current_season}>,
      "temp_avg": <average of day/night>,
      "emoji": "❄️",
      "condition": "snow"
    }}
  ]
}}

CRITICAL REQUIREMENTS:
- Temperatures MUST be realistic for the current season ({current_season}) and location
- Ukraine and Poland in winter: temperatures should be NEGATIVE (below 0°C) with snow ❄️
- Use accurate weather conditions for the season
- All temperatures in Celsius
- Emoji must match weather condition
- Use exact city names: Protaras for Cyprus, Kraków for Poland
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
            cost_per_1k = 0.15 / 1000
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
                {"city": "London", "country": "UK", "temp_day": 6, "temp_night": 2, "temp_avg": 4, "emoji": "☁️", "condition": "cloudy"},
                {"city": "Bila Tserkva", "country": "Ukraine", "temp_day": -8, "temp_night": -15, "temp_avg": -12, "emoji": "❄️", "condition": "snow"},
                {"city": "Poltava", "country": "Ukraine", "temp_day": -10, "temp_night": -16, "temp_avg": -13, "emoji": "❄️", "condition": "snow"},
                {"city": "Bengaluru", "country": "India", "temp_day": 26, "temp_night": 18, "temp_avg": 22, "emoji": "☀️", "condition": "sunny"},
                {"city": "Protaras", "country": "Cyprus", "temp_day": 16, "temp_night": 10, "temp_avg": 13, "emoji": "⛅", "condition": "partly cloudy"},
                {"city": "Kraków", "country": "Poland", "temp_day": -2, "temp_night": -7, "temp_avg": -5, "emoji": "❄️", "condition": "snow"}
            ]
        # Spring templates (Mar-May)
        elif current_month in [3, 4, 5]:
            weather_data = [
                {"city": "London", "country": "UK", "temp_day": 12, "temp_night": 6, "temp_avg": 9, "emoji": "⛅", "condition": "partly cloudy"},
                {"city": "Bila Tserkva", "country": "Ukraine", "temp_day": 10, "temp_night": 3, "temp_avg": 7, "emoji": "☁️", "condition": "cloudy"},
                {"city": "Poltava", "country": "Ukraine", "temp_day": 11, "temp_night": 4, "temp_avg": 8, "emoji": "⛅", "condition": "partly cloudy"},
                {"city": "Bengaluru", "country": "India", "temp_day": 32, "temp_night": 22, "temp_avg": 27, "emoji": "☀️", "condition": "sunny"},
                {"city": "Protaras", "country": "Cyprus", "temp_day": 22, "temp_night": 15, "temp_avg": 19, "emoji": "☀️", "condition": "sunny"},
                {"city": "Kraków", "country": "Poland", "temp_day": 12, "temp_night": 5, "temp_avg": 9, "emoji": "☁️", "condition": "cloudy"}
            ]
        # Summer templates (Jun-Aug)
        elif current_month in [6, 7, 8]:
            weather_data = [
                {"city": "London", "country": "UK", "temp_day": 22, "temp_night": 15, "temp_avg": 19, "emoji": "⛅", "condition": "partly cloudy"},
                {"city": "Bila Tserkva", "country": "Ukraine", "temp_day": 26, "temp_night": 16, "temp_avg": 21, "emoji": "☀️", "condition": "sunny"},
                {"city": "Poltava", "country": "Ukraine", "temp_day": 27, "temp_night": 17, "temp_avg": 22, "emoji": "☀️", "condition": "sunny"},
                {"city": "Bengaluru", "country": "India", "temp_day": 30, "temp_night": 21, "temp_avg": 26, "emoji": "🌧️", "condition": "rain"},
                {"city": "Protaras", "country": "Cyprus", "temp_day": 32, "temp_night": 23, "temp_avg": 28, "emoji": "☀️", "condition": "sunny"},
                {"city": "Kraków", "country": "Poland", "temp_day": 24, "temp_night": 14, "temp_avg": 19, "emoji": "⛅", "condition": "partly cloudy"}
            ]
        # Autumn templates (Sep-Nov)
        else:
            weather_data = [
                {"city": "London", "country": "UK", "temp_day": 13, "temp_night": 8, "temp_avg": 11, "emoji": "🌧️", "condition": "rain"},
                {"city": "Bila Tserkva", "country": "Ukraine", "temp_day": 10, "temp_night": 4, "temp_avg": 7, "emoji": "☁️", "condition": "cloudy"},
                {"city": "Poltava", "country": "Ukraine", "temp_day": 11, "temp_night": 5, "temp_avg": 8, "emoji": "☁️", "condition": "cloudy"},
                {"city": "Bengaluru", "country": "India", "temp_day": 27, "temp_night": 20, "temp_avg": 24, "emoji": "⛅", "condition": "partly cloudy"},
                {"city": "Protaras", "country": "Cyprus", "temp_day": 25, "temp_night": 18, "temp_avg": 22, "emoji": "☀️", "condition": "sunny"},
                {"city": "Kraków", "country": "Poland", "temp_day": 10, "temp_night": 5, "temp_avg": 8, "emoji": "🌧️", "condition": "rain"}
            ]
        
        return {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "weather": weather_data
        }
