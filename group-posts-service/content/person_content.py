"""Generate content for famous person posts."""
import os
import logging
import random
from typing import Dict, Optional, List
from openai import OpenAI
from datetime import datetime

logger = logging.getLogger(__name__)


class PersonContentGenerator:
    """Generate famous person content for posts."""
    
    PERSON_CATEGORIES = [
        "inventors",
        "engineers",
        "scientists",
        "mathematicians",
        "physicists",
        "computer scientists",
        "electrical engineers",
        "mechanical engineers",
        "chemists",
        "biologists",
        "astronomers",
        "innovators"
    ]
    
    def __init__(self, budget_guard):
        """Initialize person content generator."""
        self.budget_guard = budget_guard
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.llm_enabled = os.getenv("LLM_ENABLED", "off").lower() == "on"
        
        if self.llm_enabled and self.openai_api_key:
            self.client = OpenAI(api_key=self.openai_api_key)
        else:
            self.client = None
            logger.warning("LLM disabled for person content")
    
    def generate_person_post(self, used_persons: List[str] = None, last_posts: List[Dict] = None) -> Optional[Dict]:
        """Generate famous person post.
        
        Args:
            used_persons: List of recently used person names
            last_posts: List of last 3 posts with is_alive and is_electrical flags
        """
        used_persons = used_persons or []
        last_posts = last_posts or []
        
        # Determine if we need alive person (2/3 should be alive, 1/3 deceased)
        alive_count = sum(1 for p in last_posts if p.get("is_alive", 0) == 1)
        need_alive = alive_count < 2  # Need 2 alive out of 3
        
        # Determine if we need electrical invention (1/3 should be electrical)
        electrical_count = sum(1 for p in last_posts if p.get("is_electrical", 0) == 1)
        need_electrical = electrical_count < 1  # Need 1 electrical out of 3
        
        if self.client and self.llm_enabled:
            return self._generate_with_llm(used_persons, need_alive, need_electrical)
        else:
            return self._generate_template(used_persons, need_alive, need_electrical)
    
    def _generate_with_llm(self, used_persons: List[str], need_alive: bool = True, need_electrical: bool = False) -> Optional[Dict]:
        """Generate famous person using LLM.
        
        Args:
            used_persons: List of recently used person names
            need_alive: If True, person should be alive (death_year = "Present")
            need_electrical: If True, invention should be electrical/electronic
        """
        try:
            current_date = datetime.now().strftime("%Y-%m-%d")
            
            # Choose person category
            if need_electrical:
                # Prefer electrical engineering category for electrical inventions
                electrical_categories = ["electrical engineers", "inventors", "engineers", "physicists"]
                category = random.choice(electrical_categories)
            else:
                category = random.choice(self.PERSON_CATEGORIES)
            
            used_persons_context = ""
            if used_persons:
                used_persons_context = f"\n\nAvoid persons that were recently covered: {', '.join(used_persons[-10:])}"
            
            # Add requirements based on distribution needs
            status_requirement = ""
            if need_alive:
                status_requirement = "\n\nIMPORTANT: The person MUST be ALIVE (death_year should be 'Present' or empty)."
            else:
                status_requirement = "\n\nIMPORTANT: The person MUST be DECEASED (death_year should be a year, not 'Present')."
            
            invention_requirement = ""
            if need_electrical:
                invention_requirement = "\n\nIMPORTANT: The invention MUST be ELECTRICAL or ELECTRONIC (related to electricity, electronics, circuits, power systems, AC/DC, transformers, etc.)."
            
            # Determine label based on category
            contribution_label = "Key Contribution" if category in ["scientists", "mathematicians", "physicists", "biologists", "chemists", "astronomers"] else "Main Invention"
            
            prompt = f"""Generate information about a FAMOUS PERSON related to {category} who made significant inventions or contributions.{status_requirement}{invention_requirement}

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
  "nationality": "Country (use specific region if relevant, e.g., 'Austrian Empire (Moravia)')",
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
- Use category in singular form if needed (e.g., "Biologist" not "Biologists")
- Keep everything concise and scannable

Current date: {current_date}{used_persons_context}

Return ONLY valid JSON, no additional text."""

            response = self.client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {"role": "system", "content": "You are a historian and science writer. Generate information about famous inventors, engineers, and scientists. Always return valid JSON only, no additional text."},
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
                logger.error("Empty response from LLM for famous person")
                return self._generate_template(used_persons)
            
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
                    return self._generate_template(used_persons)
            
            # Record usage
            tokens_used = response.usage.total_tokens
            cost_per_1k = 0.15 / 1000
            estimated_cost = (tokens_used / 1000) * cost_per_1k
            self.budget_guard.record_llm_call(tokens_used, estimated_cost)
            
            return data
            
        except Exception as e:
            logger.error(f"LLM error generating famous person: {e}")
            # Use default values for template
            return self._generate_template(used_persons, True, False)
    
    def _generate_template(self, used_persons: List[str], need_alive: bool = True, need_electrical: bool = False) -> Dict:
        """Generate template famous person when LLM unavailable."""
        if need_electrical:
            category = "electrical engineer"
            invention = "Electrical Device"
        else:
            category = random.choice(self.PERSON_CATEGORIES)
            invention = "Important Invention"
        
        death_year = "Present" if need_alive else "1980"
        contribution_label = "Key Contribution" if category in ["scientist", "mathematician", "physicist", "biologist", "chemist", "astronomer"] else "Main Invention"
        
        return {
            "person_name": "Famous Inventor",
            "birth_year": "1900",
            "death_year": death_year,
            "nationality": "Country",
            "category": category,
            "one_line_description": "Known for significant contributions to their field.",
            "contribution_name": invention,
            "contribution_label": contribution_label,
            "key_facts": [
                "Fact 1 about the person",
                "Fact 2 about their work",
                "Fact 3 about their impact"
            ],
            "why_it_matters": "This contribution changed the world. It enabled new possibilities.",
            "fun_fact": "An interesting fact about this person.",
            "resource_link": "https://en.wikipedia.org"
        }
