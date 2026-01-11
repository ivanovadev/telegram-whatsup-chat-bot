"""Generate content for Africa exploration posts."""
import os
import logging
import random
from typing import Dict, Optional, List
from openai import OpenAI
from datetime import datetime

logger = logging.getLogger(__name__)


class AfricaContentGenerator:
    """Generate Africa exploration content."""
    
    AFRICAN_COUNTRIES = [
        "South Africa", "Kenya", "Tanzania", "Morocco", "Egypt", "Ghana",
        "Nigeria", "Ethiopia", "Botswana", "Namibia", "Zambia", "Zimbabwe",
        "Rwanda", "Uganda", "Senegal", "Tunisia", "Algeria", "Mozambique"
    ]
    
    def __init__(self, budget_guard):
        """Initialize Africa content generator."""
        self.budget_guard = budget_guard
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.llm_enabled = os.getenv("LLM_ENABLED", "off").lower() == "on"
        
        if self.llm_enabled and self.openai_api_key:
            self.client = OpenAI(api_key=self.openai_api_key)
        else:
            self.client = None
            logger.warning("LLM disabled for Africa content")
    
    def generate_africa_post(self, used_countries: List[str] = None) -> Optional[Dict]:
        """Generate Africa exploration post."""
        used_countries = used_countries or []
        
        if self.client and self.llm_enabled:
            return self._generate_with_llm(used_countries)
        else:
            return self._generate_template(used_countries)
    
    def _generate_with_llm(self, used_countries: List[str]) -> Optional[Dict]:
        """Generate Africa content using LLM."""
        try:
            current_date = datetime.now().strftime("%Y-%m-%d")
            
            # Choose country (prefer unused)
            available_countries = [c for c in self.AFRICAN_COUNTRIES if c not in used_countries]
            if not available_countries:
                available_countries = self.AFRICAN_COUNTRIES
            country = random.choice(available_countries)
            
            used_countries_context = ""
            if used_countries:
                used_countries_context = f"\n\nPrefer countries not recently used: {', '.join(used_countries[-5:])}"
            
            prompt = f"""Generate information about exploring {country} in Africa.

Requirements:
1. Country: {country}
2. Cities to visit: 2-3 main cities or destinations
3. Places to explore: 2 specific places (national parks, landmarks, cultural sites, markets, etc.) - choose the most iconic
4. Best time to visit: When is the best time to visit (brief, e.g., "May-Oct" or "Dry season")
5. Activities: 2 key activities (brief, e.g., "Safari • Sandboarding")
6. Cultural fact: 1 SHORT interesting fact about the country's culture (max 1 sentence, 80 words)
7. Wildlife fact: 1 SHORT interesting fact about wildlife (max 1 sentence, 80 words)
8. Historical fact: 1 SHORT interesting fact about history (max 1 sentence, 80 words)
9. Total: 3 facts (cultural, wildlife, historical) - each must be concise and informative

Format as JSON:
{{
  "country": "{country}",
  "capital": "Capital city",
  "cities": ["City 1", "City 2", "City 3"],
  "places": [
    {{"name": "Place name", "type": "national park/landmark/cultural site/market/etc"}},
    {{"name": "Place name", "type": "national park/landmark/cultural site/market/etc"}}
  ],
  "best_time": "May-Oct or Dry season (brief format)",
  "activities": ["Activity 1", "Activity 2"],
  "cultural_fact": "One SHORT sentence about culture (max 80 words)",
  "wildlife_fact": "One SHORT sentence about wildlife (max 80 words)",
  "historical_fact": "One SHORT sentence about history (max 80 words)",
  "resource_link": "https://wikipedia.org/wiki/Country_Name or travel resource URL"
}}

IMPORTANT:
- All information must be REAL and ACCURATE
- Keep facts SHORT and INFORMATIVE (1 sentence each, max 80 words)
- Places: Choose only 3 most iconic/important places
- Activities: Keep brief (3 activities max)
- Best time: Use brief format (e.g., "May-Oct", "Dry season")
- Focus on exploration, nature, culture, and wildlife
- Include resource link for the country
- Current date: {current_date}{used_countries_context}

Return ONLY valid JSON, no additional text."""

            response = self.client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {"role": "system", "content": "You are a travel writer specializing in Africa. Generate accurate information about African countries for exploration. Always return valid JSON only, no additional text."},
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
                logger.error("Empty response from LLM for Africa")
                return self._generate_template(used_countries)
            
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error for Africa: {e}. Content: {content[:200]}")
                try:
                    content = content[content.find('{'):]
                    content = content[:content.rfind('}') + 1]
                    data = json.loads(content)
                except Exception as e2:
                    logger.error(f"Failed to fix JSON for Africa: {e2}")
                    return self._generate_template(used_countries)
            
            # Record usage
            tokens_used = response.usage.total_tokens
            cost_per_1k = 0.15 / 1000
            estimated_cost = (tokens_used / 1000) * cost_per_1k
            self.budget_guard.record_llm_call(tokens_used, estimated_cost)
            
            return data
            
        except Exception as e:
            logger.error(f"LLM error generating Africa content: {e}")
            return self._generate_template(used_countries)
    
    def _generate_template(self, used_countries: List[str]) -> Dict:
        """Generate template Africa content when LLM unavailable."""
        country = random.choice(self.AFRICAN_COUNTRIES)
        return {
            "country": country,
            "capital": "Capital",
            "cities": ["City 1", "City 2"],
            "places": [
                {"name": "National Park", "type": "national park"},
                {"name": "Cultural Site", "type": "cultural site"},
                {"name": "Market", "type": "market"}
            ],
            "best_time": "Dry season (June-September)",
            "activities": ["Safari", "Cultural tours", "Wildlife watching"],
            "cultural_fact": "Interesting cultural fact about the country.",
            "wildlife_fact": "Interesting wildlife fact about the country.",
            "historical_fact": "Interesting historical fact about the country.",
            "resource_link": f"https://en.wikipedia.org/wiki/{country.replace(' ', '_')}"
        }
