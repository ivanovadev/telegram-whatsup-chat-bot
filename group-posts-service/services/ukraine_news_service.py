"""Service for generating Ukraine news summaries (economy, politics, war)."""
import os
import logging
from typing import Dict, List, Optional
from openai import OpenAI
from datetime import datetime

logger = logging.getLogger(__name__)


class UkraineNewsService:
    """Generate Ukraine news summaries (economy, politics, war)."""
    
    def __init__(self, budget_guard):
        """Initialize Ukraine news service."""
        self.budget_guard = budget_guard
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-5.2")
        self.llm_enabled = os.getenv("LLM_ENABLED", "off").lower() == "on"
        
        if self.llm_enabled and self.openai_api_key:
            self.client = OpenAI(api_key=self.openai_api_key)
        else:
            self.client = None
            logger.warning("LLM disabled for Ukraine news service")
    
    def generate_ukraine_news(self, used_topics: List[str] = None) -> Optional[Dict]:
        """Generate 3 main Ukraine news items from last 12 hours (economy, politics, war)."""
        used_topics = used_topics or []
        
        if self.client and self.llm_enabled:
            return self._generate_with_llm(used_topics)
        else:
            return self._generate_template(used_topics)
    
    def _generate_with_llm(self, used_topics: List[str]) -> Optional[Dict]:
        """Generate Ukraine news using LLM."""
        try:
            current_date = datetime.now().strftime("%Y-%m-%d")
            
            used_context = ""
            if used_topics:
                used_context = f"\n\nAvoid topics that were recently covered: {', '.join(used_topics[-5:])}"
            
            prompt = f"""Generate 3 main news stories about Ukraine from the last 12 hours:
1. Economic news - about Ukraine's economy, finance, business, trade, reconstruction
2. Political news - about Ukraine's politics, government, international relations, diplomacy
3. War news - about the war against Russia, military operations, defense, frontline updates

Requirements:
1. All news must be about UKRAINE
2. All news should be REAL and CURRENT (from last 12 hours)
3. Three categories: economy, politics, war (one news per category)
4. Format: headline, brief summary (2-3 sentences), source, and URL to the article
5. Include URL to the actual article if available, or use main site URL
6. Use reliable Ukrainian sources: Ukrainian Truth, BBC Ukraine, Ukrinform, or other reputable Ukrainian media
7. Make it engaging and informative

Format as JSON:
{{
  "title": "Top 3 Ukraine News",
  "news": [
    {{
      "headline": "Headline of economic news",
      "summary": "Brief 2-3 sentence summary of economic development",
      "source": "Ukrainian Truth" or "BBC Ukraine" or "Ukrinform",
      "category": "economy",
      "url": "https://www.pravda.com.ua/article-url"
    }},
    {{
      "headline": "Headline of political news",
      "summary": "Brief 2-3 sentence summary of political development",
      "source": "Ukrainian Truth" or "BBC Ukraine" or "Ukrinform",
      "category": "politics",
      "url": "https://www.pravda.com.ua/article-url"
    }},
    {{
      "headline": "Headline about war against Russia",
      "summary": "Brief 2-3 sentence summary about latest war developments",
      "source": "Ukrainian Truth" or "BBC Ukraine" or "Ukrinform",
      "category": "war",
      "url": "https://www.pravda.com.ua/article-url"
    }}
  ]
}}

IMPORTANT:
- All news must be about UKRAINE
- Three categories: economy, politics, war (one news per category)
- All news must be REAL and from last 12 hours
- Include URL to the actual article if available, or use main site URL
- Use reliable Ukrainian sources
- Current date: {current_date}{used_context}

Return ONLY valid JSON, no additional text."""

            response = self.client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {"role": "system", "content": "You are a news editor specializing in Ukraine news. Generate real, current news summaries about Ukraine's economy, politics, and war. Always return valid JSON only, no additional text."},
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
                logger.error("Empty response from LLM for Ukraine news")
                return self._generate_template(used_topics)
            
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error for Ukraine news: {e}. Content: {content[:200]}")
                try:
                    content = content[content.find('{'):]
                    content = content[:content.rfind('}') + 1]
                    data = json.loads(content)
                except Exception as e2:
                    logger.error(f"Failed to fix JSON for Ukraine news: {e2}")
                    return self._generate_template(used_topics)
            
            # Record usage
            tokens_used = response.usage.total_tokens
            cost_per_1k = 0.15 / 1000
            estimated_cost = (tokens_used / 1000) * cost_per_1k
            self.budget_guard.record_llm_call(tokens_used, estimated_cost)
            
            return data
            
        except Exception as e:
            logger.error(f"LLM error generating Ukraine news: {e}")
            return self._generate_template(used_topics)
    
    def _generate_template(self, used_topics: List[str]) -> Dict:
        """Generate template Ukraine news when LLM unavailable."""
        news_items = [
            {
                "headline": "Ukraine Economic Development",
                "summary": "Important economic news and financial updates from Ukraine.",
                "source": "Ukrainian Truth",
                "category": "economy",
                "url": "https://www.pravda.com.ua"
            },
            {
                "headline": "Ukraine Political Update",
                "summary": "Latest political developments and government decisions in Ukraine.",
                "source": "BBC Ukraine",
                "category": "politics",
                "url": "https://www.bbc.com/ukrainian"
            },
            {
                "headline": "War Against Russia Update",
                "summary": "Latest developments in Ukraine's defense against Russian aggression.",
                "source": "Ukrainian Truth",
                "category": "war",
                "url": "https://www.pravda.com.ua"
            }
        ]
        
        return {
            "title": "Top 3 Ukraine News",
            "news": news_items
        }
