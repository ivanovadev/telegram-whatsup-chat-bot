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
        {"name": "Nicosia", "country": "Cyprus", "country_code": "CY"},  # Capital of Cyprus
        {"name": "Warsaw", "country": "Poland", "country_code": "PL"}  # Capital of Poland
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
                        
                        # For Cyprus and Poland, use country name as city display
                        display_city = city_name
                        if city_info["country"] in ["Cyprus", "Poland"]:
                            display_city = city_info["country"]
                        
                        weather_data.append({
                            "city": display_city,
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
                        # For Cyprus and Poland, use country name as city display
                        display_city = city_name
                        if city_info["country"] in ["Cyprus", "Poland"]:
                            display_city = city_info["country"]
                        
                        weather_data.append({
                            "city": display_city,
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
            
            prompt = f"""Generate current weather forecast for the following cities:
{cities_list}

For each city, provide:
1. Day temperature (high) in Celsius
2. Night temperature (low) in Celsius
3. Average temperature in Celsius
4. Weather condition (rain, cloudy, sunny, snow, thunderstorm, etc.)
5. Appropriate emoji (🌧️ for rain, ☁️ for cloudy, ☀️ for sunny, ⛈️ for thunderstorm, ❄️ for snow, ⛅ for partly cloudy)

Format as JSON:
{{
  "date": "{current_date}",
  "weather": [
    {{
      "city": "London",
      "country": "UK",
      "temp_day": 22,
      "temp_night": 15,
      "temp_avg": 18,
      "emoji": "☀️",
      "condition": "sunny"
    }},
    {{
      "city": "Bila Tserkva",
      "country": "Ukraine",
      "temp_day": 18,
      "temp_night": 10,
      "temp_avg": 14,
      "emoji": "☁️",
      "condition": "cloudy"
    }},
    {{
      "city": "Cyprus",
      "country": "Cyprus",
      "temp_day": 25,
      "temp_night": 18,
      "temp_avg": 22,
      "emoji": "☀️",
      "condition": "sunny"
    }},
    {{
      "city": "Poland",
      "country": "Poland",
      "temp_day": 16,
      "temp_night": 8,
      "temp_avg": 12,
      "emoji": "☁️",
      "condition": "cloudy"
    }}
    // ... for all cities
  ]
}}

IMPORTANT:
- Use realistic temperatures based on current season and location
- All temperatures in Celsius
- Emoji must match weather condition
- For Cyprus: use "Cyprus" as city name (not "Nicosia")
- For Poland: use "Poland" as city name (not "Warsaw")
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
        """Generate template weather when API/LLM unavailable."""
        return {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "weather": [
                {"city": "London", "country": "UK", "temp_day": 20, "temp_night": 12, "temp_avg": 16, "emoji": "☁️", "condition": "cloudy"},
                {"city": "Bila Tserkva", "country": "Ukraine", "temp_day": 18, "temp_night": 10, "temp_avg": 14, "emoji": "☀️", "condition": "sunny"},
                {"city": "Poltava", "country": "Ukraine", "temp_day": 19, "temp_night": 11, "temp_avg": 15, "emoji": "⛅", "condition": "partly cloudy"},
                {"city": "Bengaluru", "country": "India", "temp_day": 28, "temp_night": 20, "temp_avg": 24, "emoji": "☀️", "condition": "sunny"},
                {"city": "Cyprus", "country": "Cyprus", "temp_day": 25, "temp_night": 18, "temp_avg": 22, "emoji": "☀️", "condition": "sunny"},
                {"city": "Poland", "country": "Poland", "temp_day": 16, "temp_night": 8, "temp_avg": 12, "emoji": "☁️", "condition": "cloudy"}
            ]
        }
