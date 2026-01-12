"""Generate content for quote of the day posts with anti-duplicate system."""
import os
import logging
import json
import re
import random
import requests
from typing import Dict, Optional, List
from openai import OpenAI
from datetime import datetime

from content.base_content_generator import BaseContentGenerator

logger = logging.getLogger(__name__)


def fetch_wikipedia_summary(person_name: str) -> Optional[Dict]:
    """Fetch facts from Wikipedia REST API."""
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{person_name.replace(' ', '_')}"
    
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return {
                "extract": data.get("extract", ""),
                "title": data.get("title", ""),
                "url": data.get("content_urls", {}).get("desktop", {}).get("page", "")
            }
        else:
            logger.warning(f"Wikipedia API returned {response.status_code} for {person_name}")
    except Exception as e:
        logger.error(f"Wikipedia API error for {person_name}: {e}")
    
    return None


# Famous authors pool (100+ names - facts from Wikipedia)
AUTHOR_POOL = [
    # Philosophers & Ancient Thinkers
    "Aristotle", "Socrates", "Plato", "Confucius", "Lao Tzu",
    "Marcus Aurelius", "Seneca", "Epictetus", "Buddha", "Rumi",
    
    # Writers & Poets
    "Oscar Wilde", "Mark Twain", "Maya Angelou", "Ernest Hemingway", "F. Scott Fitzgerald",
    "Jane Austen", "Virginia Woolf", "Charles Dickens", "Leo Tolstoy", "Fyodor Dostoevsky",
    "Victor Hugo", "George Orwell", "J.R.R. Tolkien", "C.S. Lewis", "Ralph Waldo Emerson",
    "Henry David Thoreau", "Walt Whitman", "Emily Dickinson", "Shakespeare", "Dante Alighieri",
    
    # Scientists & Inventors
    "Albert Einstein", "Isaac Newton", "Marie Curie", "Nikola Tesla", "Thomas Edison",
    "Stephen Hawking", "Carl Sagan", "Richard Feynman", "Neil deGrasse Tyson", "Charles Darwin",
    "Galileo Galilei", "Leonardo da Vinci", "Benjamin Franklin", "Alan Turing",
    
    # Political Leaders & Activists
    "Winston Churchill", "Abraham Lincoln", "Theodore Roosevelt", "Franklin D. Roosevelt", "Eleanor Roosevelt",
    "John F. Kennedy", "Nelson Mandela", "Martin Luther King Jr.", "Gandhi", "Dalai Lama",
    "Malcolm X", "Rosa Parks", "Susan B. Anthony", "Harriet Tubman", "Desmond Tutu",
    
    # Business Leaders & Entrepreneurs
    "Steve Jobs", "Bill Gates", "Elon Musk", "Warren Buffett", "Jeff Bezos",
    "Henry Ford", "Andrew Carnegie", "John D. Rockefeller", "Walt Disney", "Richard Branson",
    "Oprah Winfrey", "Sara Blakely", "Jack Ma", "Peter Thiel", "Mark Cuban",
    
    # Artists & Creators
    "Pablo Picasso", "Vincent van Gogh", "Michelangelo", "Frida Kahlo", "Andy Warhol",
    "Salvador Dalí", "Claude Monet", "Rembrandt", "Georgia O'Keeffe",
    
    # Musicians & Entertainers
    "John Lennon", "Bob Dylan", "David Bowie", "Prince", "Freddie Mercury",
    "Bob Marley", "Nina Simone", "Ludwig van Beethoven", "Wolfgang Amadeus Mozart",
    
    # Athletes & Sports Icons
    "Muhammad Ali", "Michael Jordan", "Kobe Bryant", "Serena Williams", "Pelé",
    "Mike Tyson", "Bruce Lee", "Jackie Robinson", "Billie Jean King", "Jesse Owens",
    
    # Motivational Speakers & Life Coaches
    "Tony Robbins", "Zig Ziglar", "Jim Rohn", "Les Brown", "Wayne Dyer",
    "Brené Brown", "Simon Sinek", "Dale Carnegie",
    
    # Religious & Spiritual Leaders
    "Mother Teresa", "Pope John Paul II", "Thích Nhất Hạnh", "Desmond Tutu",
    
    # Actors & Cultural Icons
    "Charlie Chaplin", "Audrey Hepburn", "Robin Williams", "Fred Rogers",
    
    # Modern Thought Leaders
    "Jordan Peterson", "Sam Harris", "Malcolm Gladwell", "Yuval Noah Harari",
    
    # Historical Figures
    "Julius Caesar", "Alexander the Great", "Cleopatra", "Napoleon Bonaparte",
    "George Washington", "Thomas Jefferson", "Voltaire", "Jean-Jacques Rousseau",
]

# Template pool for fallback mode (when LLM is off)
QUOTE_TEMPLATE_POOL = [
    {"quote": "The only way to do great work is to love what you do.", "author": "Steve Jobs", "author_info": "Co-founder of Apple Inc. and pioneer of personal computing.", "advice": "This quote reminds us that passion is essential for excellence. When you love your work, it doesn't feel like work, and you naturally strive to do your best.", "resource_link": "https://en.wikipedia.org/wiki/Steve_Jobs"},
    {"quote": "Be yourself; everyone else is already taken.", "author": "Oscar Wilde", "author_info": "Irish poet and playwright known for his wit.", "advice": "Authenticity is your superpower. Trying to be someone else wastes the person you are. Embrace your uniqueness and let it shine.", "resource_link": "https://en.wikipedia.org/wiki/Oscar_Wilde"},
    {"quote": "The future belongs to those who believe in the beauty of their dreams.", "author": "Eleanor Roosevelt", "author_info": "Former First Lady and human rights activist.", "advice": "Your dreams are the blueprint for your future. Believe in them fiercely, pursue them relentlessly, and watch them transform into reality.", "resource_link": "https://en.wikipedia.org/wiki/Eleanor_Roosevelt"},
    {"quote": "It is during our darkest moments that we must focus to see the light.", "author": "Aristotle", "author_info": "Ancient Greek philosopher and scientist.", "advice": "Challenges often reveal our true strength. When times are tough, maintaining hope and perspective helps us find solutions we couldn't see before.", "resource_link": "https://en.wikipedia.org/wiki/Aristotle"},
    {"quote": "The way to get started is to quit talking and begin doing.", "author": "Walt Disney", "author_info": "American entrepreneur and animator who created Mickey Mouse.", "advice": "Action beats intention every time. Stop planning and start executing. Progress comes from doing, not from endless preparation.", "resource_link": "https://en.wikipedia.org/wiki/Walt_Disney"},
    {"quote": "Don't watch the clock; do what it does. Keep going.", "author": "Sam Levenson", "author_info": "American humorist and writer.", "advice": "Persistence is the key to success. Like time, which never stops moving forward, you should keep advancing toward your goals regardless of obstacles.", "resource_link": "https://en.wikipedia.org/wiki/Sam_Levenson"},
    {"quote": "The only impossible journey is the one you never begin.", "author": "Tony Robbins", "author_info": "Motivational speaker and life coach.", "advice": "Every achievement starts with the decision to try. The biggest risk is not taking the first step. Start now, learn as you go.", "resource_link": "https://en.wikipedia.org/wiki/Tony_Robbins"},
    {"quote": "Life is what happens when you're busy making other plans.", "author": "John Lennon", "author_info": "Singer, songwriter, and peace activist.", "advice": "While planning is important, don't forget to live in the present moment. Balance your future ambitions with appreciation for what's happening now.", "resource_link": "https://en.wikipedia.org/wiki/John_Lennon"},
]


class QuoteContentGenerator(BaseContentGenerator):
    """Generate quote of the day content with anti-duplicate system."""
    
    def __init__(self, budget_guard):
        """Initialize quote content generator with anti-duplicate system."""
        super().__init__(
            budget_guard=budget_guard,
            content_type="quote",
            history_file="data/quote_history.json",
            template_pool=QUOTE_TEMPLATE_POOL
        )
        
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-5.2")
        self.llm_enabled = os.getenv("LLM_ENABLED", "off").lower() == "on"
        
        if self.llm_enabled and self.openai_api_key:
            self.client = OpenAI(api_key=self.openai_api_key)
        else:
            self.client = None
            logger.warning("LLM disabled for quote content")
    
    def _select_author_from_pool(self, used_authors: List[str]) -> str:
        """Select an author from pool, avoiding recently used.
        
        Args:
            used_authors: List of recently used authors
            
        Returns:
            Author name
        """
        # Try to find unused author from pool
        recent_set = set(used_authors[-20:]) if used_authors else set()
        available = [a for a in AUTHOR_POOL if a not in recent_set]
        
        if not available:
            # If all authors used, pick randomly
            available = AUTHOR_POOL
            
        return random.choice(available)
    
    def _generate_content(self, used_items: List[str]) -> Optional[Dict]:
        """Generate quote content using LLM.
        
        FACT-BASED APPROACH:
        1. Select author from pool
        2. Fetch real facts from Wikipedia
        3. LLM rephrases facts + creates quote based on author's real work
        
        Args:
            used_items: List of recently used authors
            
        Returns:
            Quote data dict or None if failed
        """
        if not self.client or not self.llm_enabled:
            return None
        
        try:
            # Step 1: Select author
            author_name = self._select_author_from_pool(used_items)
            
            # Step 2: Fetch Wikipedia facts
            wiki_data = fetch_wikipedia_summary(author_name)
            
            if not wiki_data or not wiki_data.get("extract"):
                logger.warning(f"No Wikipedia data for {author_name}, skipping")
                return None
            
            wiki_text = wiki_data["extract"]
            wiki_url = wiki_data.get("url", f"https://en.wikipedia.org/wiki/{author_name.replace(' ', '_')}")
            
            logger.info(f"Wikipedia facts for {author_name}: {wiki_text[:200]}...")
            
            # Step 3: LLM rephrase with STRICT rules
            prompt = f"""You are creating a "Quote of the Day" post for {author_name}.

WIKIPEDIA FACTS (use ONLY these, add nothing):
{wiki_text}

Your task:
1. Select or create a quote that reflects this person's work/philosophy
2. Write author_info (1 sentence) based ONLY on Wikipedia text above
3. Write advice (2-3 sentences) explaining the quote's meaning and practical application

CRITICAL RULES:
- Use ONLY facts from Wikipedia text above
- Do NOT add information not in the Wikipedia text
- Do NOT invent facts, dates, or details
- Author info must be verifiable from Wikipedia text
- Quote should be inspiring and meaningful

Format as JSON:
{{
  "quote": "The inspiring or wise quote/phrase",
  "author": "{author_name}",
  "author_info": "Brief factual info from Wikipedia (1 sentence)",
  "advice": "Explanation and practical advice about the quote (2-3 sentences)",
  "resource_link": "{wiki_url}"
}}

Return ONLY valid JSON, no additional text."""

            response = self.client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {"role": "system", "content": "You are a wisdom curator. Create inspiring quotes based ONLY on factual Wikipedia information. Never add information not present in the source text. Always return valid JSON only, no additional text."},
                    {"role": "user", "content": prompt}
                ],
                max_completion_tokens=600,
                temperature=0.5,
                response_format={"type": "json_object"}
            )
            
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
                return None
            
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
                    return None
            
            # Record usage
            tokens_used = response.usage.total_tokens
            cost_per_1k = 0.15 / 1000
            estimated_cost = (tokens_used / 1000) * cost_per_1k
            self.budget_guard.record_llm_call(tokens_used, estimated_cost)
            
            return data
            
        except Exception as e:
            logger.error(f"LLM error generating quote: {e}")
            return None
    
    def _extract_item_id(self, content: Dict) -> str:
        """Extract unique identifier from quote content.
        
        Returns author name to track which authors have been used.
        """
        return content.get("author", "Unknown")
    
    # Legacy compatibility
    def generate_quote_post(self, used_quotes: Optional[List[str]] = None) -> Optional[Dict]:
        """Generate quote post (legacy method for backward compatibility)."""
        return self.generate(used_items=used_quotes)
