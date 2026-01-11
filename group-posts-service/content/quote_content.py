"""Generate content for quote of the day posts."""
import os
import logging
import random
from typing import Dict, Optional, List
from openai import OpenAI
from datetime import datetime

logger = logging.getLogger(__name__)


class QuoteContentGenerator:
    """Generate quote of the day content."""
    
    def __init__(self, budget_guard):
        """Initialize quote content generator."""
        self.budget_guard = budget_guard
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.llm_enabled = os.getenv("LLM_ENABLED", "off").lower() == "on"
        
        if self.llm_enabled and self.openai_api_key:
            self.client = OpenAI(api_key=self.openai_api_key)
        else:
            self.client = None
            logger.warning("LLM disabled for quote content")
    
    def generate_quote_post(self, used_quotes: List[str] = None) -> Optional[Dict]:
        """Generate quote of the day post."""
        used_quotes = used_quotes or []
        
        if self.client and self.llm_enabled:
            return self._generate_with_llm(used_quotes)
        else:
            return self._generate_template(used_quotes)
    
    def _generate_with_llm(self, used_quotes: List[str]) -> Optional[Dict]:
        """Generate quote content using LLM."""
        try:
            current_date = datetime.now().strftime("%Y-%m-%d")
            
            used_quotes_context = ""
            if used_quotes:
                used_quotes_context = f"\n\nAvoid quotes that were recently covered: {', '.join(used_quotes[-5:])}"
            
            prompt = f"""Generate a "Quote of the Day" with author and advice.

Requirements:
1. Quote: An inspiring, motivational, or wise quote/phrase
2. Author: The person who said/wrote this quote (famous person, philosopher, writer, etc.)
3. Advice or context: Brief advice, explanation, or context about the quote (2-3 sentences)
4. Category: Type of quote (motivational, philosophical, business, life advice, etc.)

Format as JSON:
{{
  "quote": "The inspiring or wise quote/phrase",
  "author": "Author Name",
  "author_info": "Brief info about author (1 sentence)",
  "advice": "Brief advice or explanation about the quote (2-3 sentences)",
  "category": "motivational/philosophical/business/life advice/etc",
  "resource_link": "https://wikipedia.org/wiki/Author_Name or other resource URL"
}}

IMPORTANT:
- Quote should be inspiring, meaningful, or thought-provoking
- Author should be a real, famous person
- Advice should be practical and relevant
- Include resource link for author
- Current date: {current_date}{used_quotes_context}

Return ONLY valid JSON, no additional text."""

            response = self.client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {"role": "system", "content": "You are a wisdom curator. Generate inspiring quotes with authors and practical advice. Always return valid JSON only, no additional text."},
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
                logger.error("Empty response from LLM for quote")
                return self._generate_template(used_quotes)
            
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error for quote: {e}. Content: {content[:200]}")
                try:
                    content = content[content.find('{'):]
                    content = content[:content.rfind('}') + 1]
                    data = json.loads(content)
                except Exception as e2:
                    logger.error(f"Failed to fix JSON for quote: {e2}")
                    return self._generate_template(used_quotes)
            
            # Record usage
            tokens_used = response.usage.total_tokens
            cost_per_1k = 0.15 / 1000
            estimated_cost = (tokens_used / 1000) * cost_per_1k
            self.budget_guard.record_llm_call(tokens_used, estimated_cost)
            
            return data
            
        except Exception as e:
            logger.error(f"LLM error generating quote: {e}")
            return self._generate_template(used_quotes)
    
    def _generate_template(self, used_quotes: List[str]) -> Dict:
        """Generate template quote when LLM unavailable."""
        return {
            "quote": "The only way to do great work is to love what you do.",
            "author": "Steve Jobs",
            "author_info": "Co-founder of Apple Inc.",
            "advice": "This quote reminds us that passion is essential for excellence. When you love your work, it doesn't feel like work, and you naturally strive to do your best.",
            "category": "motivational",
            "resource_link": "https://en.wikipedia.org/wiki/Steve_Jobs"
        }
