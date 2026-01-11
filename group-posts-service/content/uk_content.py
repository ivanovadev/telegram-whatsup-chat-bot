"""Generate content for UK posts."""
import os
import logging
import random
from typing import Dict, Optional, List
from openai import OpenAI
from datetime import datetime

logger = logging.getLogger(__name__)


class UKContentGenerator:
    """Generate UK travel information."""
    
    UK_CITIES = [
        "London", "Edinburgh", "Manchester", "Birmingham", "Liverpool",
        "Bristol", "Leeds", "Glasgow", "Cardiff", "Belfast", "Newcastle",
        "Nottingham", "Sheffield", "Brighton", "Oxford", "Cambridge", "York"
    ]
    
    def __init__(self, budget_guard):
        """Initialize UK content generator."""
        self.budget_guard = budget_guard
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.llm_enabled = os.getenv("LLM_ENABLED", "off").lower() == "on"
        
        if self.llm_enabled and self.openai_api_key:
            self.client = OpenAI(api_key=self.openai_api_key)
        else:
            self.client = None
            logger.warning("LLM disabled for UK content")
    
    def generate_uk_post(self, used_cities: List[str] = None) -> Optional[Dict]:
        """Generate UK post."""
        used_cities = used_cities or []
        
        if self.client and self.llm_enabled:
            return self._generate_with_llm(used_cities)
        else:
            return self._generate_template(used_cities)
    
    def _generate_with_llm(self, used_cities: List[str]) -> Optional[Dict]:
        """Generate UK content using LLM."""
        try:
            current_date = datetime.now().strftime("%Y-%m-%d")
            
            # Choose cities (prefer unused)
            available_cities = [c for c in self.UK_CITIES if c not in used_cities]
            if not available_cities:
                available_cities = self.UK_CITIES
            
            # Select 2-3 cities
            num_cities = random.randint(2, 3)
            selected_cities = random.sample(available_cities, min(num_cities, len(available_cities)))
            
            used_context = ""
            if used_cities:
                used_context = f"\n\nPrefer cities not recently used: {', '.join(used_cities[-5:])}"
            
            prompt = f"""Generate information about UK travel.

Requirements:
1. UK cities to visit: 2-3 cities from {', '.join(selected_cities)}
2. For EACH city, provide:
   - Distance from London (in km or miles)
   - Travel time from London (by train or car, e.g., "2h 15min by train" or "3h by car")
   - Why tourists visit: Reason (museum, famous person, unique attraction, sea/coast, history, etc.) - be specific and brief (1 sentence)
3. UK fact: 1 interesting fact about UK (culture, history, geography, etc.)

Format as JSON:
{{
  "cities": [
    {{
      "name": "City 1",
      "distance_from_london": "200 km",
      "travel_time": "2h 15min by train",
      "why_visit": "Home to the Beatles Story museum and historic Albert Dock"
    }},
    {{
      "name": "City 2",
      "distance_from_london": "190 km",
      "travel_time": "1h 30min by train",
      "why_visit": "Famous for Cadbury World and the Birmingham Museum & Art Gallery"
    }}
  ],
  "uk_fact": "Interesting fact about UK",
  "resource_link": "https://wikipedia.org/wiki/United_Kingdom or travel resource URL"
}}

IMPORTANT:
- All information must be REAL and ACCURATE
- Cities should be from the provided list: {', '.join(selected_cities)}
- Distance and travel time must be accurate (verify)
- Why_visit should be specific: mention museums, famous people, unique attractions, sea/coast, etc.
- Fact should be interesting and factual
- Include resource link
- Current date: {current_date}{used_context}

Return ONLY valid JSON, no additional text."""

            response = self.client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {"role": "system", "content": "You are a travel writer specializing in UK. Generate accurate information about UK cities and facts. Always return valid JSON only, no additional text."},
                    {"role": "user", "content": prompt}
                ],
                max_completion_tokens=500,
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
                logger.error("Empty response from LLM for UK")
                return self._generate_template(used_cities)
            
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error for UK: {e}. Content: {content[:200]}")
                try:
                    content = content[content.find('{'):]
                    content = content[:content.rfind('}') + 1]
                    data = json.loads(content)
                except Exception as e2:
                    logger.error(f"Failed to fix JSON for UK: {e2}")
                    return self._generate_template(used_cities)
            
            # Record usage
            tokens_used = response.usage.total_tokens
            cost_per_1k = 0.15 / 1000
            estimated_cost = (tokens_used / 1000) * cost_per_1k
            self.budget_guard.record_llm_call(tokens_used, estimated_cost)
            
            return data
            
        except Exception as e:
            logger.error(f"LLM error generating UK content: {e}")
            return self._generate_template(used_cities)
    
    def _generate_template(self, used_cities: List[str]) -> Dict:
        """Generate template UK content when LLM unavailable."""
        cities_list = random.sample(self.UK_CITIES, min(3, len(self.UK_CITIES)))
        cities = []
        for city in cities_list:
            if city == "Liverpool":
                cities.append({
                    "name": "Liverpool",
                    "distance_from_london": "350 km",
                    "travel_time": "2h 15min by train",
                    "why_visit": "Home to the Beatles Story museum and historic Albert Dock"
                })
            elif city == "Birmingham":
                cities.append({
                    "name": "Birmingham",
                    "distance_from_london": "190 km",
                    "travel_time": "1h 30min by train",
                    "why_visit": "Famous for Cadbury World and the Birmingham Museum & Art Gallery"
                })
            else:
                cities.append({
                    "name": city,
                    "distance_from_london": "~200 km",
                    "travel_time": "~2h by train",
                    "why_visit": f"Historic city with cultural attractions"
                })
        return {
            "cities": cities,
            "uk_fact": "UK has 4 constituent countries: England, Scotland, Wales, and Northern Ireland.",
            "resource_link": "https://en.wikipedia.org/wiki/United_Kingdom"
        }
