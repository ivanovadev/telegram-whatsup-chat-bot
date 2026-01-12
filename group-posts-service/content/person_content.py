"""Generate content for famous person posts with anti-duplicate system."""
import os
import logging
import json
import re
import random
from typing import Dict, Optional, List
from openai import OpenAI
from datetime import datetime

from content.base_content_generator import BaseContentGenerator

logger = logging.getLogger(__name__)


# Template pool for fallback mode
PERSON_TEMPLATE_POOL = [
    {"person_name": "Nikola Tesla", "birth_year": "1856", "death_year": "1943", "nationality": "Austrian Empire (Croatia)", "category": "electrical engineer", "one_line_description": "Inventor of alternating current (AC) electrical system", "contribution_name": "AC Electrical System", "contribution_label": "Main Invention", "key_facts": ["Developed AC power distribution", "Invented Tesla coil", "Held over 300 patents", "Worked with Thomas Edison"], "why_it_matters": "Tesla's AC system powers the modern world. It enabled efficient long-distance power transmission.", "fun_fact": "Tesla claimed to visualize his inventions in 3D before building them.", "resource_link": "https://en.wikipedia.org/wiki/Nikola_Tesla"},
    {"person_name": "Grace Hopper", "birth_year": "1906", "death_year": "1992", "nationality": "USA", "category": "computer scientist", "one_line_description": "Pioneer of computer programming and inventor of first compiler", "contribution_name": "COBOL Programming Language", "contribution_label": "Main Invention", "key_facts": ["Created first compiler for programming language", "Developed COBOL language", "Coined term 'debugging'", "US Navy Rear Admiral"], "why_it_matters": "Hopper's work made programming accessible to non-specialists. COBOL is still used in banking systems today.", "fun_fact": "She kept a clock in her office that ran backwards to remind people to think differently.", "resource_link": "https://en.wikipedia.org/wiki/Grace_Hopper"},
    {"person_name": "Tim Berners-Lee", "birth_year": "1955", "death_year": "Present", "nationality": "UK", "category": "computer scientist", "one_line_description": "Inventor of the World Wide Web", "contribution_name": "World Wide Web", "contribution_label": "Main Invention", "key_facts": ["Created HTML, HTTP, and URL", "Made web technology free and open", "Founded W3C standards organization", "Knighted by Queen Elizabeth II"], "why_it_matters": "The Web transformed global communication and information sharing. It connected billions of people worldwide.", "fun_fact": "He could have patented the Web and become a billionaire, but chose to give it away for free.", "resource_link": "https://en.wikipedia.org/wiki/Tim_Berners-Lee"},
    {"person_name": "Marie Curie", "birth_year": "1867", "death_year": "1934", "nationality": "Poland/France", "category": "physicist", "one_line_description": "First woman to win Nobel Prize, discovered radioactivity", "contribution_name": "Radioactivity Research", "contribution_label": "Key Contribution", "key_facts": ["Won two Nobel Prizes (Physics and Chemistry)", "Discovered radium and polonium", "First female professor at Sorbonne", "Pioneered radiation therapy"], "why_it_matters": "Curie's work revolutionized medicine and physics. Her discoveries led to cancer treatments and nuclear energy.", "fun_fact": "Her notebooks are still radioactive and stored in lead-lined boxes.", "resource_link": "https://en.wikipedia.org/wiki/Marie_Curie"},
    {"person_name": "Alan Turing", "birth_year": "1912", "death_year": "1954", "nationality": "UK", "category": "mathematician", "one_line_description": "Father of computer science and artificial intelligence", "contribution_name": "Turing Machine", "contribution_label": "Key Contribution", "key_facts": ["Broke Nazi Enigma code in WWII", "Created Turing Test for AI", "Laid foundations of computer science", "Prosecuted for homosexuality"], "why_it_matters": "Turing's work saved millions of lives in WWII and defined modern computing. He created the theoretical foundation for all computers.", "fun_fact": "He was a talented marathon runner who nearly qualified for the Olympics.", "resource_link": "https://en.wikipedia.org/wiki/Alan_Turing"},
    {"person_name": "Elon Musk", "birth_year": "1971", "death_year": "Present", "nationality": "South Africa/USA", "category": "engineer", "one_line_description": "CEO of Tesla and SpaceX, pioneering electric vehicles and space exploration", "contribution_name": "Reusable Rockets & Electric Vehicles", "contribution_label": "Main Invention", "key_facts": ["Made rockets reusable (SpaceX)", "Popularized electric cars (Tesla)", "Working on brain-computer interface (Neuralink)", "Founded PayPal predecessor"], "why_it_matters": "Musk accelerated the transition to sustainable energy and made space travel more affordable. His companies are reshaping transportation.", "fun_fact": "He taught himself rocket science by reading textbooks.", "resource_link": "https://en.wikipedia.org/wiki/Elon_Musk"},
    {"person_name": "Ada Lovelace", "birth_year": "1815", "death_year": "1852", "nationality": "UK", "category": "mathematician", "one_line_description": "First computer programmer in history", "contribution_name": "First Computer Algorithm", "contribution_label": "Key Contribution", "key_facts": ["Wrote first computer algorithm", "Worked on Charles Babbage's Analytical Engine", "Recognized computers could do more than math", "Daughter of poet Lord Byron"], "why_it_matters": "Lovelace envisioned computers' potential beyond calculations. She laid the conceptual foundation for modern programming.", "fun_fact": "She predicted computers could create music and art, 100 years before it happened.", "resource_link": "https://en.wikipedia.org/wiki/Ada_Lovelace"},
    {"person_name": "Hedy Lamarr", "birth_year": "1914", "death_year": "2000", "nationality": "Austria/USA", "category": "inventor", "one_line_description": "Hollywood actress who invented frequency-hopping spread spectrum technology", "contribution_name": "Frequency-Hopping Technology", "contribution_label": "Main Invention", "key_facts": ["Invented tech used in Wi-Fi and Bluetooth", "Was a famous Hollywood movie star", "Created invention to help Allies in WWII", "Received no money from her patent"], "why_it_matters": "Her invention is the foundation of modern wireless communication. It's used in Wi-Fi, Bluetooth, and military systems.", "fun_fact": "She was a glamorous movie star by day and an inventor at night.", "resource_link": "https://en.wikipedia.org/wiki/Hedy_Lamarr"},
]


class PersonContentGenerator(BaseContentGenerator):
    """Generate famous person content with anti-duplicate system."""
    
    PERSON_CATEGORIES = [
        "inventors", "engineers", "scientists", "mathematicians", "physicists",
        "computer scientists", "electrical engineers", "mechanical engineers",
        "chemists", "biologists", "astronomers", "innovators"
    ]
    
    def __init__(self, budget_guard):
        """Initialize person content generator with anti-duplicate system."""
        super().__init__(
            budget_guard=budget_guard,
            content_type="person",
            history_file="data/person_history.json",
            template_pool=PERSON_TEMPLATE_POOL
        )
        
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-5.2")
        self.llm_enabled = os.getenv("LLM_ENABLED", "off").lower() == "on"
        
        if self.llm_enabled and self.openai_api_key:
            self.client = OpenAI(api_key=self.openai_api_key)
        else:
            self.client = None
            logger.warning("LLM disabled for person content")
    
    def _generate_content(self, used_items: List[str]) -> Optional[Dict]:
        """Generate person content using LLM."""
        if not self.client or not self.llm_enabled:
            return None
        
        try:
            current_date = datetime.now().strftime("%Y-%m-%d")
            
            category = random.choice(self.PERSON_CATEGORIES)
            contribution_label = "Key Contribution" if category in ["scientists", "mathematicians", "physicists", "biologists", "chemists", "astronomers"] else "Main Invention"
            
            used_persons_context = ""
            if used_items:
                recent_items = used_items[-10:]
                used_persons_context = f"\n\nIMPORTANT: Avoid persons that were recently covered: {', '.join(recent_items)}\nChoose a DIFFERENT person."
            
            prompt = f"""Generate information about a FAMOUS PERSON related to {category} who made significant inventions or contributions.

STRUCTURE REQUIREMENTS (5 blocks max):
1. Name + one-line description (what this person is known for)
2. Key facts (3-5 bullet points with important facts)
3. Why it matters (1-2 sentences MAXIMUM explaining impact)
4. Fun fact (1 sentence MAXIMUM - surprising or little-known fact)
5. Source link (Wikipedia or reliable resource URL)

TEXT LIMITS:
- "Why it matters" = 2 sentences MAXIMUM (keep it short!)
- "Fun fact" = 1 sentence MAXIMUM (one punchy sentence)
- Key facts = 3-5 bullet points, no more
- Use simple, clear language
- Short sentences only

Format as JSON:
{{
  "person_name": "Full Name",
  "birth_year": "YYYY",
  "death_year": "YYYY or 'Present'",
  "nationality": "Country (use specific region if relevant)",
  "category": "{category}",
  "one_line_description": "One sentence describing what this person is known for",
  "contribution_name": "Name of main invention/contribution/discovery",
  "contribution_label": "{contribution_label}",
  "key_facts": ["Fact 1", "Fact 2", "Fact 3", "Fact 4", "Fact 5"],
  "why_it_matters": "1-2 sentences MAXIMUM explaining why this matters. Keep it short and impactful.",
  "fun_fact": "1 sentence MAXIMUM - a surprising, little-known, or unexpected fact. Make it punchy and memorable.",
  "resource_link": "https://en.wikipedia.org/wiki/Person_Name or other reliable resource URL"
}}

IMPORTANT: 
- "why_it_matters" must be 1-2 sentences MAXIMUM
- "fun_fact" must be 1 sentence MAXIMUM
- "key_facts" must be 3-5 items, no more
- Keep everything concise and scannable
- Current date: {current_date}{used_persons_context}

Return ONLY valid JSON, no additional text."""

            response = self.client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {"role": "system", "content": "You are a historian and science writer. Generate information about famous inventors, engineers, and scientists. Always return valid JSON only, no additional text."},
                    {"role": "user", "content": prompt}
                ],
                max_completion_tokens=600,
                temperature=0.7,
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
                logger.error("Empty response from LLM for famous person")
                return None
            
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error for famous person: {e}. Content: {content[:200]}")
                try:
                    content = content[content.find('{'):]
                    content = content[:content.rfind('}') + 1]
                    data = json.loads(content)
                except Exception as e2:
                    logger.error(f"Failed to fix JSON for famous person: {e2}")
                    return None
            
            # Record usage
            tokens_used = response.usage.total_tokens
            cost_per_1k = 0.15 / 1000
            estimated_cost = (tokens_used / 1000) * cost_per_1k
            self.budget_guard.record_llm_call(tokens_used, estimated_cost)
            
            return data
            
        except Exception as e:
            logger.error(f"LLM error generating famous person: {e}")
            return None
    
    def _extract_item_id(self, content: Dict) -> str:
        """Extract unique identifier from person content."""
        return content.get("person_name", "Unknown")
    
    # Legacy compatibility
    def generate_person_post(self, used_persons: Optional[List[str]] = None, last_posts: Optional[List[Dict]] = None) -> Optional[Dict]:
        """Generate person post (legacy method for backward compatibility)."""
        return self.generate(used_items=used_persons)
