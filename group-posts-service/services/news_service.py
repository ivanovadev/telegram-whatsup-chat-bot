"""Service for generating news summaries from Bloomberg and BBC."""
import os
import logging
from typing import Dict, List, Optional
from openai import OpenAI
from datetime import datetime

logger = logging.getLogger(__name__)


class NewsService:
    """Generate news summaries from Bloomberg and BBC."""
    
    def __init__(self, budget_guard):
        """Initialize news service."""
        self.budget_guard = budget_guard
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-5.2")
        self.llm_enabled = os.getenv("LLM_ENABLED", "off").lower() == "on"
        
        if self.llm_enabled and self.openai_api_key:
            self.client = OpenAI(api_key=self.openai_api_key)
        else:
            self.client = None
            logger.warning("LLM disabled for news service")
    
    def generate_news_summary(self, used_topics: List[str] = None) -> Optional[Dict]:
        """Generate news summary with 3 main news items from last 12 hours (2 from Bloomberg/BBC, 1 about Ukraine war from Ukrainian Truth)."""
        used_topics = used_topics or []
        
        if self.client and self.llm_enabled:
            return self._generate_with_llm(used_topics)
        else:
            return self._generate_template(used_topics)
    
    def _generate_with_llm(self, used_topics: List[str]) -> Optional[Dict]:
        """Generate news using LLM."""
        try:
            # Get current date for context
            current_date = datetime.now().strftime("%Y-%m-%d")
            
            # Build used topics context
            used_context = ""
            if used_topics:
                used_context = f"\n\nAvoid topics that were recently covered: {', '.join(used_topics[-5:])}"
            
            prompt = f"""Generate 3 main news stories from the last 12 hours:
1. First news from Bloomberg or BBC (about politics, economy, technology, international relations, etc.)
2. Second news from Bloomberg or BBC (about DIFFERENT topic than first)
3. Third news MUST be about war in Ukraine from Ukrainian Truth

Requirements:
1. First two news items must be about DIFFERENT topics (politics, economy, technology, international relations, etc.)
2. Third news MUST be about war in Ukraine from Ukrainian Truth
3. All news should be REAL and CURRENT (from last 12 hours)
4. Format: headline, brief summary (2-3 sentences), source, and URL to the article
5. Include URL to the actual article if available, or use main site URL
6. Make it engaging and informative

Format as JSON:
{{
  "title": "Top 3 World News",
  "news": [
    {{
      "headline": "Headline of the news",
      "summary": "Brief 2-3 sentence summary of what happened",
      "source": "Bloomberg" or "BBC",
      "topic": "politics" or "economy" or "technology" or "international" or "business" or "sports" or "culture",
      "url": "https://www.bloomberg.com/article-url" or "https://www.bbc.com/news/article-url"
    }},
    {{
      "headline": "Headline of the second news",
      "summary": "Brief 2-3 sentence summary of what happened",
      "source": "Bloomberg" or "BBC",
      "topic": "politics" or "economy" or "technology" or "international" or "business" or "sports" or "culture",
      "url": "https://www.bloomberg.com/article-url" or "https://www.bbc.com/news/article-url"
    }},
    {{
      "headline": "Headline about war in Ukraine",
      "summary": "Brief 2-3 sentence summary about latest developments in Ukraine war",
      "source": "Ukrainian Truth",
      "topic": "ukraine_war",
      "url": "https://www.pravda.com.ua/article-url"
    }}
  ]
}}

IMPORTANT:
- First two topics must be DIFFERENT (e.g., one politics, one economy)
- Third news MUST be about war in Ukraine from Ukrainian Truth
- All news must be REAL and from last 12 hours
- Include URL to the actual article if available, or use main site URL
- Current date: {current_date}{used_context}

Return ONLY valid JSON, no additional text."""

            response = self.client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {"role": "system", "content": "You are a news editor. Generate real, current news summaries based on Bloomberg and BBC coverage. Always return valid JSON only, no additional text."},
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
                logger.error("Empty response from LLM for news")
                return self._generate_template(used_topics)
            
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error for news: {e}. Content: {content[:200]}")
                try:
                    content = content[content.find('{'):]
                    content = content[:content.rfind('}') + 1]
                    data = json.loads(content)
                except Exception as e2:
                    logger.error(f"Failed to fix JSON for news: {e2}")
                    return self._generate_template(used_topics)
            
            # Record usage
            tokens_used = response.usage.total_tokens
            cost_per_1k = 0.15 / 1000
            estimated_cost = (tokens_used / 1000) * cost_per_1k
            self.budget_guard.record_llm_call(tokens_used, estimated_cost)
            
            return data
            
        except Exception as e:
            logger.error(f"LLM error generating news: {e}")
            return self._generate_template(used_topics)
    
    def _generate_template(self, used_topics: List[str]) -> Dict:
        """Generate template news when LLM unavailable."""
        news_items = [
            {
                "headline": "Major International Development",
                "summary": "Significant global event occurred affecting international relations and diplomacy.",
                "source": "BBC",
                "topic": "international",
                "url": "https://www.bbc.com/news"
            },
            {
                "headline": "Economic Market Update",
                "summary": "Important economic indicators and market movements reported by financial analysts.",
                "source": "Bloomberg",
                "topic": "economy",
                "url": "https://www.bloomberg.com"
            },
            {
                "headline": "Latest Developments in Ukraine War",
                "summary": "Recent updates on the situation in Ukraine and ongoing military operations.",
                "source": "Ukrainian Truth",
                "topic": "ukraine_war",
                "url": "https://www.pravda.com.ua"
            }
        ]
        
        return {
            "title": "Top 3 World News",
            "news": news_items
        }
