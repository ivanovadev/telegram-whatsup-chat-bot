"""Generate content for London posts."""
import os
import logging
import random
from typing import Dict, Optional, List
from openai import OpenAI
from datetime import datetime

logger = logging.getLogger(__name__)


class LondonContentGenerator:
    """Generate London travel information."""
    
    def __init__(self, budget_guard):
        """Initialize London content generator."""
        self.budget_guard = budget_guard
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.llm_enabled = os.getenv("LLM_ENABLED", "off").lower() == "on"
        
        if self.llm_enabled and self.openai_api_key:
            self.client = OpenAI(api_key=self.openai_api_key)
        else:
            self.client = None
            logger.warning("LLM disabled for London content")
    
    def generate_london_post(self, used_topics: List[str] = None) -> Optional[Dict]:
        """Generate London post."""
        used_topics = used_topics or []
        
        if self.client and self.llm_enabled:
            return self._generate_with_llm(used_topics)
        else:
            return self._generate_template(used_topics)
    
    def _generate_with_llm(self, used_topics: List[str]) -> Optional[Dict]:
        """Generate London content using LLM."""
        try:
            current_date = datetime.now().strftime("%Y-%m-%d")
            
            used_context = ""
            if used_topics:
                used_context = f"\n\nAvoid topics that were recently covered: {', '.join(used_topics[-5:])}"
            
            prompt = f"""Generate information about London, UK.

Requirements:
1. Places in London to visit: 3-5 specific places (museums, pubs, streets, music venues, landmarks, parks, etc.)
2. Fact about London: 1 interesting fact about London
3. Fact about British politician: 1 interesting fact about a famous British politician

Format as JSON:
{{
  "places": [
    {{"name": "Place name", "type": "museum/pub/street/music venue/landmark/park/etc"}},
    {{"name": "Place name", "type": "museum/pub/street/music venue/landmark/park/etc"}},
    {{"name": "Place name", "type": "museum/pub/street/music venue/landmark/park/etc"}}
  ],
  "london_fact": "Interesting fact about London",
  "politician_fact": "Interesting fact about a famous British politician",
  "resource_link": "https://wikipedia.org/wiki/London or travel resource URL"
}}

IMPORTANT:
- All information must be REAL and ACCURATE
- Places should be real and well-known
- Facts should be interesting and factual
- Include resource link
- Current date: {current_date}{used_context}

Return ONLY valid JSON, no additional text."""

            response = self.client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {"role": "system", "content": "You are a travel writer specializing in London. Generate accurate information about London places and facts. Always return valid JSON only, no additional text."},
                    {"role": "user", "content": prompt}
                ],
                max_completion_tokens=600,
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
        """Generate template London content when LLM unavailable."""
        return {
            "places": [
                {"name": "British Museum", "type": "museum"},
                {"name": "The Shard", "type": "landmark"},
                {"name": "Camden Market", "type": "street"},
                {"name": "Hyde Park", "type": "park"}
            ],
            "london_fact": "London has over 170 museums.",
            "politician_fact": "Winston Churchill was Prime Minister during WWII.",
            "resource_link": "https://en.wikipedia.org/wiki/London"
        }
