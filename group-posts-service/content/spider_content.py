"""Generate content for spider posts with UK/London information."""
import os
import logging
import random
from typing import Dict, Optional, List
from openai import OpenAI
from datetime import datetime

logger = logging.getLogger(__name__)


class SpiderContentGenerator:
    """Generate spider content with UK/London information."""
    
    def __init__(self, budget_guard):
        """Initialize spider content generator."""
        self.budget_guard = budget_guard
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.llm_enabled = os.getenv("LLM_ENABLED", "off").lower() == "on"
        
        if self.llm_enabled and self.openai_api_key:
            self.client = OpenAI(api_key=self.openai_api_key)
        else:
            self.client = None
            logger.warning("LLM disabled for spider content")
    
    def generate_spider_post(self, used_spiders: List[str] = None) -> Optional[Dict]:
        """Generate spider post with UK/London information."""
        used_spiders = used_spiders or []
        
        if self.client and self.llm_enabled:
            return self._generate_with_llm(used_spiders)
        else:
            return self._generate_template(used_spiders)
    
    def _generate_with_llm(self, used_spiders: List[str]) -> Optional[Dict]:
        """Generate spider content using LLM."""
        try:
            current_date = datetime.now().strftime("%Y-%m-%d")
            
            used_spiders_context = ""
            if used_spiders:
                used_spiders_context = f"\n\nAvoid spiders that were recently covered: {', '.join(used_spiders[-5:])}"
            
            prompt = f"""Generate information about a SPIDER species.

Requirements:
1. Spider information:
   - Spider name (scientific and common name)
   - Where to meet (1-2 countries where this spider is found)
   - Size (body length, leg span)
   - Color (main colors and patterns)
   - Is it a hunter? (yes/no and brief explanation)
   - Speed (how fast it moves)
   - Lifespan (how long it lives)
   - Dangerous rate: Number from 0 to 10 (0 = harmless, 10 = highly dangerous/venomous)

Format as JSON:
{{
  "name": "Common name",
  "scientific_name": "Scientific name",
  "countries": ["Country 1", "Country 2"],
  "size": "Size description (body length, leg span)",
  "color": "Color description",
  "is_hunter": true/false,
  "hunter_description": "Brief explanation if hunter",
  "speed": "Speed description",
  "lifespan": "Lifespan description",
  "dangerous_rate": 0-10,
  "resource_link": "https://wikipedia.org/wiki/Spider_Name or other resource URL"
}}

IMPORTANT:
- All information must be REAL and ACCURATE
- Spider should be a real species
- Dangerous rate must be between 0 and 10
- Include resource link for spider information
- Current date: {current_date}{used_spiders_context}

Return ONLY valid JSON, no additional text."""

            response = self.client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {"role": "system", "content": "You are a biologist and travel writer. Generate accurate information about spiders and UK/London travel. Always return valid JSON only, no additional text."},
                    {"role": "user", "content": prompt}
                ],
                max_completion_tokens=1000,
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
                logger.error("Empty response from LLM for spider")
                return self._generate_template(used_spiders)
            
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error for spider: {e}. Content: {content[:200]}")
                try:
                    content = content[content.find('{'):]
                    content = content[:content.rfind('}') + 1]
                    data = json.loads(content)
                except Exception as e2:
                    logger.error(f"Failed to fix JSON for spider: {e2}")
                    return self._generate_template(used_spiders)
            
            # Record usage
            tokens_used = response.usage.total_tokens
            cost_per_1k = 0.15 / 1000
            estimated_cost = (tokens_used / 1000) * cost_per_1k
            self.budget_guard.record_llm_call(tokens_used, estimated_cost)
            
            return data
            
        except Exception as e:
            logger.error(f"LLM error generating spider content: {e}")
            return self._generate_template(used_spiders)
    
    def _generate_template(self, used_spiders: List[str]) -> Dict:
        """Generate template spider content when LLM unavailable."""
        return {
            "name": "Common Spider",
            "scientific_name": "Araneae sp.",
            "countries": ["UK", "Ireland"],
            "size": "5-10mm body length",
            "color": "Brown with darker patterns",
            "is_hunter": True,
            "hunter_description": "Hunts small insects",
            "speed": "Moderate speed",
            "lifespan": "1-2 years",
            "dangerous_rate": 2,
            "resource_link": "https://en.wikipedia.org/wiki/Spider"
        }
