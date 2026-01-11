"""Generate content for tech device posts."""
import os
import logging
import random
from typing import Dict, Optional, List
from openai import OpenAI
from datetime import datetime

logger = logging.getLogger(__name__)


class TechContentGenerator:
    """Generate tech device content for posts."""
    
    DEVICE_CATEGORIES = [
        "electronic engineering devices",
        "semiconductor devices",
        "microcontrollers",
        "sensors and transducers",
        "power electronics",
        "communication devices",
        "embedded systems",
        "electronic test equipment",
        "robotics and automation",
        "industrial electronics",
        "electronic components",
        "circuit boards and PCBs"
    ]
    
    COUNTRIES = [
        "USA", "China", "Japan", "South Korea", "Germany", "Sweden",
        "Finland", "Netherlands", "Switzerland", "UK", "France", "Italy",
        "Taiwan", "Singapore", "Israel", "Canada", "Australia", "India"
    ]
    
    def __init__(self, budget_guard):
        """Initialize tech content generator."""
        self.budget_guard = budget_guard
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.llm_enabled = os.getenv("LLM_ENABLED", "off").lower() == "on"
        
        if self.llm_enabled and self.openai_api_key:
            self.client = OpenAI(api_key=self.openai_api_key)
        else:
            self.client = None
            logger.warning("LLM disabled for tech content")
    
    def generate_tech_post(self, used_devices: List[str] = None, used_countries: List[str] = None) -> Optional[Dict]:
        """Generate tech device post."""
        used_devices = used_devices or []
        used_countries = used_countries or []
        
        if self.client and self.llm_enabled:
            return self._generate_with_llm(used_devices, used_countries)
        else:
            return self._generate_template(used_devices, used_countries)
    
    def _generate_with_llm(self, used_devices: List[str], used_countries: List[str]) -> Optional[Dict]:
        """Generate tech device using LLM."""
        try:
            current_date = datetime.now().strftime("%Y-%m-%d")
            
            # Choose device type (sometimes unique, sometimes top-notch)
            device_type = random.choice(self.DEVICE_CATEGORIES)
            
            # Choose country (prefer unused)
            available_countries = [c for c in self.COUNTRIES if c not in used_countries]
            if not available_countries:
                available_countries = self.COUNTRIES
            country = random.choice(available_countries)
            
            # Determine if unique or top-notch (70% unique, 30% top-notch)
            is_unique = random.random() < 0.7
            
            used_devices_context = ""
            if used_devices:
                used_devices_context = f"\n\nAvoid devices that were recently covered: {', '.join(used_devices[-5:])}"
            
            used_countries_context = ""
            if used_countries:
                used_countries_context = f"\n\nPrefer countries not recently used: {', '.join(used_countries[-5:])}"
            
            if is_unique:
                prompt = f"""Generate information about an INNOVATIVE engineering/electronic device from {country} in the {device_type} category.

Requirements:
1. Device should be related to ENGINEERING and ELECTRONICS (not consumer gadgets)
2. Can be from a startup, smaller company, or innovative engineering project
3. Should be an actual electronic/engineering device (semiconductors, sensors, microcontrollers, etc.)
4. Include: device name, manufacturer, year of creation/release, key features (3-5), what it does (1-2 sentences MAXIMUM, no marketing language), resource link
5. NO marketing language - avoid words like "revolutionizing", "critical", "game-changing". Use concrete facts: what it does and where it's used.

Format as JSON:
{{
  "device_name": "Device Name",
  "manufacturer": "Company Name",
  "country": "{country}",
  "category": "{device_type}",
  "type": "unique",
  "year_created": "YYYY",
  "key_features": ["short feature 1", "short feature 2", "short feature 3", "short feature 4"],
  "what_it_does": "1-2 sentences MAXIMUM. What the device does and where it's used. NO marketing language, just facts.",
  "resource_link": "https://wikipedia.org/... or https://manufacturer.com/... or technical article URL"
}}

IMPORTANT:
- "what_it_does" must be 1-2 sentences MAXIMUM
- NO marketing buzzwords (revolutionizing, critical, game-changing, etc.)
- Use concrete facts: what it does, where it's used
- Keep features short and specific

Current date: {current_date}{used_devices_context}{used_countries_context}

Return ONLY valid JSON, no additional text."""
            else:
                prompt = f"""Generate information about a TOP-NOTCH or FLAGSHIP engineering/electronic device from {country} in the {device_type} category.

Requirements:
1. Device should be related to ENGINEERING and ELECTRONICS (not consumer gadgets)
2. From well-known manufacturers or leading engineering companies
3. Should be an actual electronic/engineering device (semiconductors, sensors, microcontrollers, etc.)
4. Include: device name, manufacturer, year of creation/release, key features (3-5), what it does (1-2 sentences MAXIMUM, no marketing language), resource link
5. NO marketing language - avoid words like "revolutionizing", "critical", "game-changing". Use concrete facts: what it does and where it's used.

Format as JSON:
{{
  "device_name": "Device Name",
  "manufacturer": "Company Name",
  "country": "{country}",
  "category": "{device_type}",
  "type": "top-notch",
  "year_created": "YYYY",
  "key_features": ["short feature 1", "short feature 2", "short feature 3", "short feature 4"],
  "what_it_does": "1-2 sentences MAXIMUM. What the device does and where it's used. NO marketing language, just facts.",
  "resource_link": "https://wikipedia.org/... or https://manufacturer.com/... or technical article URL"
}}

IMPORTANT:
- "what_it_does" must be 1-2 sentences MAXIMUM
- NO marketing buzzwords (revolutionizing, critical, game-changing, etc.)
- Use concrete facts: what it does, where it's used
- Keep features short and specific

Current date: {current_date}{used_devices_context}{used_countries_context}

Return ONLY valid JSON, no additional text."""

            response = self.client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {"role": "system", "content": "You are a tech journalist. Generate information about engineering devices from different countries. Always return valid JSON only, no additional text."},
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
                logger.error("Empty response from LLM for tech device")
                return self._generate_template(used_devices, used_countries)
            
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error for tech device: {e}. Content: {content[:200]}")
                try:
                    content = content[content.find('{'):]
                    content = content[:content.rfind('}') + 1]
                    data = json.loads(content)
                except Exception as e2:
                    logger.error(f"Failed to fix JSON for tech device: {e2}")
                    return self._generate_template(used_devices, used_countries)
            
            # Record usage
            tokens_used = response.usage.total_tokens
            cost_per_1k = 0.15 / 1000
            estimated_cost = (tokens_used / 1000) * cost_per_1k
            self.budget_guard.record_llm_call(tokens_used, estimated_cost)
            
            return data
            
        except Exception as e:
            logger.error(f"LLM error generating tech device: {e}")
            return self._generate_template(used_devices, used_countries)
    
    def _generate_template(self, used_devices: List[str], used_countries: List[str]) -> Dict:
        """Generate template tech device when LLM unavailable."""
        device_type = random.choice(self.DEVICE_CATEGORIES)
        country = random.choice(self.COUNTRIES)
        is_unique = random.random() < 0.7
        
        result = {
            "device_name": "Engineering Device",
            "manufacturer": "Engineering Company",
            "country": country,
            "category": device_type,
            "type": "unique" if is_unique else "top-notch",
            "year_created": "2020",
            "key_features": [
                "Feature 1",
                "Feature 2",
                "Feature 3"
            ],
            "what_it_does": f"Device for {device_type} applications. Used in industrial and engineering systems.",
            "resource_link": "https://wikipedia.org"
        }
        
        return result
