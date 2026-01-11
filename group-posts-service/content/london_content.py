"""Generate content for Canary Wharf posts."""
import os
import logging
import random
from typing import Dict, Optional, List
from openai import OpenAI
from datetime import datetime

logger = logging.getLogger(__name__)


class LondonContentGenerator:
    """Generate Canary Wharf travel information and events."""
    
    def __init__(self, budget_guard):
        """Initialize Canary Wharf content generator."""
        self.budget_guard = budget_guard
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.llm_enabled = os.getenv("LLM_ENABLED", "off").lower() == "on"
        
        if self.llm_enabled and self.openai_api_key:
            self.client = OpenAI(api_key=self.openai_api_key)
        else:
            self.client = None
            logger.warning("LLM disabled for Canary Wharf content")
    
    def generate_london_post(self, used_topics: List[str] = None) -> Optional[Dict]:
        """Generate Canary Wharf post with events."""
        used_topics = used_topics or []
        
        if self.client and self.llm_enabled:
            return self._generate_with_llm(used_topics)
        else:
            return self._generate_template(used_topics)
    
    def _generate_with_llm(self, used_topics: List[str]) -> Optional[Dict]:
        """Generate Canary Wharf content using LLM."""
        try:
            current_date = datetime.now().strftime("%Y-%m-%d")
            current_month = datetime.now().strftime("%B %Y")
            
            used_context = ""
            if used_topics:
                used_context = f"\n\nAvoid topics that were recently covered: {', '.join(used_topics[-5:])}"
            
            prompt = f"""Generate information about Canary Wharf district in London, UK.

CRITICAL: Focus ONLY on Canary Wharf district - the business and shopping district in East London, including:
- Dog Island (West India Quay area)
- Docklands area
- Thames riverside
- Modern architecture and business towers

Requirements:
1. Upcoming events in Canary Wharf: 1-2 REAL upcoming events happening in {current_month} or next month
   - Check for real events at Canary Wharf (markets, exhibitions, performances, festivals, business events, etc.)
   - Include event name, date (if known), and brief description
   - If no specific events known, mention general recurring events (weekend markets, Thames Festival events, etc.)
2. Fact about Canary Wharf: 1 interesting fact specifically about Canary Wharf district or Docklands
3. Include photo search term for Canary Wharf district

Format as JSON:
{{
  "events": [
    {{"name": "Event name", "date": "Date or 'Weekly' or 'Monthly'", "description": "Brief description of the event"}},
    {{"name": "Event name", "date": "Date or time period", "description": "Brief description"}}
  ],
  "canary_wharf_fact": "Interesting fact specifically about Canary Wharf district or its history",
  "resource_link": "https://canarywharf.com or https://wikipedia.org/wiki/Canary_Wharf",
  "image_search_term": "Canary Wharf London skyline" or "Canary Wharf district" or "Dog Island Canary Wharf"
}}

IMPORTANT:
- All information must be REAL and ACCURATE about Canary Wharf district specifically
- Events should be upcoming or regular recurring events in Canary Wharf
- Facts should be about Canary Wharf, not general London
- Include specific, accurate information
- Photo search term should help find Canary Wharf district images
- Current date: {current_date} ({current_month}){used_context}

Return ONLY valid JSON, no additional text."""

            response = self.client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {"role": "system", "content": "You are an events specialist for Canary Wharf, London's business and shopping district in Docklands. Generate accurate information about Canary Wharf events and facts. Focus specifically on the Canary Wharf district, not general London. Always return valid JSON only, no additional text."},
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
                logger.error("Empty response from LLM for London")
                return self._generate_template(used_topics)
            
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error for London: {e}. Content: {content[:200]}")
                try:
                    content = content[content.find('{'):]
                    content = content[:content.rfind('}') + 1]
                    data = json.loads(content)
                except Exception as e2:
                    logger.error(f"Failed to fix JSON for London: {e2}")
                    return self._generate_template(used_topics)
            
            # Record usage
            tokens_used = response.usage.total_tokens
            cost_per_1k = 0.15 / 1000
            estimated_cost = (tokens_used / 1000) * cost_per_1k
            self.budget_guard.record_llm_call(tokens_used, estimated_cost)
            
            return data
            
        except Exception as e:
            logger.error(f"LLM error generating London content: {e}")
            return self._generate_template(used_topics)
    
    def _generate_template(self, used_topics: List[str]) -> Dict:
        """Generate template Canary Wharf content when LLM unavailable."""
        return {
            "events": [
                {"name": "Canary Wharf Winter Lights", "date": "January-February", "description": "Annual light art installations across the estate."},
                {"name": "Weekend Market at Jubilee Place", "date": "Every Saturday", "description": "Local artisan market with food and crafts."}
            ],
            "canary_wharf_fact": "Canary Wharf was named after the cargo trade with the Canary Islands, and One Canada Square was the UK's tallest building from 1991 to 2012.",
            "resource_link": "https://canarywharf.com",
            "image_search_term": "Canary Wharf London skyline"
        }
