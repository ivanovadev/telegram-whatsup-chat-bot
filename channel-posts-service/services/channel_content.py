"""Generate content for channel posts about countries."""
import os
import random
import logging
from typing import List, Dict, Optional
from openai import OpenAI

logger = logging.getLogger(__name__)

# Simple BudgetGuard interface for channel posts service
class BudgetGuard:
    def __init__(self, db):
        self.db = db
        self.llm_enabled = os.getenv("LLM_ENABLED", "off").lower() == "on"
    def can_use_llm(self):
        return (self.llm_enabled, None)
    def record_llm_call(self, tokens, cost):
        pass


class ChannelContentGenerator:
    """Generate country rankings and travel content for channel."""
    
    MORNING_TOPICS = [
        "happiest countries in the world",
        "safest countries in the world",
        "most developed countries",
        "countries with best quality of life",
        "most peaceful countries",
        "countries with best healthcare",
        "most innovative countries",
        "countries with best education systems"
    ]
    
    EVENING_TRAVEL_TYPES = [
        ("winter", "best countries to visit in winter"),
        ("summer", "best countries to visit in summer"),
        ("hiking", "best countries for hiking and trekking"),
        ("beach", "best countries for beach vacations"),
        ("culture", "best countries for cultural tourism"),
        ("adventure", "best countries for adventure travel"),
        ("budget", "best budget-friendly travel destinations"),
        ("luxury", "best luxury travel destinations")
    ]
    
    def __init__(self, budget_guard):
        """Initialize content generator."""
        self.budget_guard = budget_guard
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-5.2")
        self.llm_enabled = os.getenv("LLM_ENABLED", "off").lower() == "on"
        
        if self.llm_enabled and self.openai_api_key:
            self.client = OpenAI(api_key=self.openai_api_key)
        else:
            self.client = None
            logger.warning("LLM disabled for channel content")
    
    def generate_morning_post(self, used_topics: List[str] = None) -> Dict[str, any]:
        """Generate morning post with top 5 countries."""
        used_topics = used_topics or []
        
        # Choose topic that hasn't been used
        available_topics = [t for t in self.MORNING_TOPICS if t not in used_topics]
        if not available_topics:
            available_topics = self.MORNING_TOPICS  # Reset if all used
        
        topic = random.choice(available_topics)
        
        if self.client and self.llm_enabled:
            result = self._generate_with_llm(
                topic=topic,
                count=5,
                post_type="morning"
            )
        else:
            result = self._generate_template(topic, count=5, post_type="morning")
        
        # Add topic to result
        if result:
            result["topic"] = topic
        
        return result
    
    def generate_evening_post(self, used_types: List[str] = None) -> Dict[str, any]:
        """Generate evening post with top 3 travel destinations."""
        used_types = used_types or []
        
        # Choose travel type that hasn't been used
        available_types = [
            t for t in self.EVENING_TRAVEL_TYPES 
            if t[0] not in used_types
        ]
        if not available_types:
            available_types = self.EVENING_TRAVEL_TYPES  # Reset if all used
        
        travel_type, topic = random.choice(available_types)
        
        if self.client and self.llm_enabled:
            result = self._generate_with_llm(
                topic=topic,
                count=3,
                post_type="evening",
                travel_type=travel_type
            )
        else:
            result = self._generate_template(topic, count=3, post_type="evening", travel_type=travel_type)
        
        # Add topic to result
        if result:
            result["topic"] = topic
        
        return result
    
    def _generate_with_llm(
        self,
        topic: str,
        count: int,
        post_type: str,
        travel_type: Optional[str] = None
    ) -> Dict[str, any]:
        """Generate content using LLM."""
        try:
            can_use, reason = self.budget_guard.can_use_llm()
            if not can_use:
                logger.warning(f"Cannot use LLM: {reason}")
                return self._generate_template(topic, count, post_type, travel_type)
            
            if post_type == "morning":
                prompt = f"""Create a ranking of top {count} countries for: {topic}

For each country, provide:
1. Country name
2. Capital city
3. Brief reason (1-2 sentences) why it's in the top {count}
4. Key statistic or interesting fact
5. Signature dish name
6. Main ingredients of the signature dish (comma-separated)

Format as JSON:
{{
  "title": "Top {count} Countries: {topic.title()}",
  "countries": [
    {{
      "name": "Country Name",
      "capital": "Capital City",
      "rank": 1,
      "reason": "Brief explanation",
      "fact": "Interesting statistic or fact",
      "signature_dish": "Dish Name",
      "dish_ingredients": "ingredient1, ingredient2, ingredient3"
    }}
  ]
}}

Return ONLY valid JSON, no additional text."""
            else:  # evening
                prompt = f"""Create a ranking of top {count} countries for: {topic}

For each country, provide:
1. Country name
2. Capital city
3. List of activities (each on new line, max 5-6 activities)
4. Best time to visit (short format, e.g. "Dec-Apr" or "Oct-Nov")
5. Unique fact about the country (what was invented there, unique animal, etc.)
6. Signature dish name
7. Main ingredients of the signature dish (comma-separated)

Format as JSON:
{{
  "title": "Top {count} Countries for {travel_type.title()} Travel",
  "travel_type": "{travel_type}",
  "countries": [
    {{
      "name": "Country Name",
      "capital": "Capital City",
      "rank": 1,
      "activities": ["Activity 1", "Activity 2", "Activity 3"],
      "best_time": "Dec-Apr",
      "unique_fact": "Unique fact about the country",
      "signature_dish": "Dish Name",
      "dish_ingredients": "ingredient1, ingredient2, ingredient3"
    }}
  ]
}}

Return ONLY valid JSON, no additional text."""
            
            response = self.client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {"role": "system", "content": "You are a travel and country statistics expert. Always return valid JSON only, no additional text. Never add explanations before or after the JSON."},
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
                # Look for JSON object in the text
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    content = json_match.group(0)
            
            # Validate and parse JSON
            if not content or not content.strip():
                logger.error("Empty response from LLM")
                return self._generate_template(topic, count, post_type, travel_type)
            
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}. Content: {content[:200]}")
                # Try to fix common JSON issues
                try:
                    # Remove any text before first {
                    content = content[content.find('{'):]
                    # Remove any text after last }
                    content = content[:content.rfind('}') + 1]
                    data = json.loads(content)
                except Exception as e2:
                    logger.error(f"Failed to fix JSON: {e2}")
                    return self._generate_template(topic, count, post_type, travel_type)
            
            # Record usage
            tokens_used = response.usage.total_tokens
            cost_per_1k = 0.15 / 1000
            estimated_cost = (tokens_used / 1000) * cost_per_1k
            self.budget_guard.record_llm_call(tokens_used, estimated_cost)
            
            return data
            
        except Exception as e:
            logger.error(f"LLM error generating content: {e}")
            return self._generate_template(topic, count, post_type, travel_type)
    
    def _generate_template(
        self,
        topic: str,
        count: int,
        post_type: str,
        travel_type: Optional[str] = None
    ) -> Dict[str, any]:
        """Generate template content when LLM unavailable."""
        if post_type == "morning":
            countries = [
                {"name": "Finland", "capital": "Helsinki", "rank": 1, "reason": "Consistently ranks highest in happiness indexes", "fact": "World Happiness Report leader", "signature_dish": "Karelian pie", "dish_ingredients": "rye flour, rice, butter, egg"},
                {"name": "Denmark", "capital": "Copenhagen", "rank": 2, "reason": "Strong social support and work-life balance", "fact": "High trust in government", "signature_dish": "Smørrebrød", "dish_ingredients": "rye bread, butter, fish, vegetables"},
                {"name": "Switzerland", "capital": "Bern", "rank": 3, "reason": "Excellent quality of life and healthcare", "fact": "One of highest GDP per capita", "signature_dish": "Fondue", "dish_ingredients": "cheese, white wine, garlic, bread"},
                {"name": "Iceland", "capital": "Reykjavik", "rank": 4, "reason": "Low crime rates and strong community", "fact": "99% literacy rate", "signature_dish": "Hákarl", "dish_ingredients": "fermented shark, potatoes"},
                {"name": "Netherlands", "capital": "Amsterdam", "rank": 5, "reason": "Progressive policies and high life satisfaction", "fact": "Excellent cycling infrastructure", "signature_dish": "Stroopwafel", "dish_ingredients": "flour, butter, syrup, cinnamon"}
            ]
            return {
                "title": f"Top {count} Countries: {topic.title()}",
                "countries": countries[:count]
            }
        else:  # evening
            if travel_type == "winter":
                countries = [
                    {"name": "Japan", "capital": "Tokyo", "rank": 1, "activities": ["Skiing in Hokkaido", "Hot springs (onsen)", "Snow festivals", "Winter hiking"], "best_time": "Dec-Feb", "unique_fact": "Home to snow monkeys that bathe in hot springs"},
                    {"name": "Switzerland", "capital": "Bern", "rank": 2, "activities": ["Alpine skiing", "Mountain resorts", "Ice skating", "Winter hiking"], "best_time": "Jan-Mar", "unique_fact": "Invented milk chocolate and the Swiss Army knife"},
                    {"name": "Iceland", "capital": "Reykjavik", "rank": 3, "activities": ["Northern lights viewing", "Glacier tours", "Ice caves", "Geothermal pools"], "best_time": "Nov-Mar", "unique_fact": "No mosquitoes and home to puffins and Icelandic horses"}
                ]
            elif travel_type == "summer":
                countries = [
                    {"name": "Greece", "capital": "Athens", "rank": 1, "activities": ["Island hopping", "Beach relaxation", "Ancient ruins", "Mediterranean cuisine"], "best_time": "Jun-Sep", "unique_fact": "Birthplace of democracy and home to over 6,000 islands"},
                    {"name": "Italy", "capital": "Rome", "rank": 2, "activities": ["Coastal towns", "Cultural sites", "Beaches", "Gelato tasting"], "best_time": "May-Sep", "unique_fact": "Home to the Colosseum and invented pizza and pasta"},
                    {"name": "Croatia", "capital": "Zagreb", "rank": 3, "activities": ["Crystal clear waters", "Historic cities", "Island tours", "Adriatic beaches"], "best_time": "Jun-Aug", "unique_fact": "Home to the Dalmatian dog breed and Game of Thrones filming locations"}
                ]
            elif travel_type == "hiking":
                countries = [
                    {"name": "Nepal", "capital": "Kathmandu", "rank": 1, "activities": ["Everest Base Camp trek", "Annapurna Circuit", "High-altitude trekking", "Mountain climbing"], "best_time": "Oct-Nov, Mar-Apr", "unique_fact": "Home to 8 of the world's 14 highest peaks", "signature_dish": "Dal Bhat", "dish_ingredients": "lentils, rice, vegetables, spices"},
                    {"name": "New Zealand", "capital": "Wellington", "rank": 2, "activities": ["Milford Track", "Alpine hiking", "Coastal walks", "Glacier trekking"], "best_time": "Dec-Mar", "unique_fact": "Home to the kiwi bird and flightless kakapo", "signature_dish": "Pavlova", "dish_ingredients": "meringue, cream, kiwi, berries"},
                    {"name": "Peru", "capital": "Lima", "rank": 3, "activities": ["Inca Trail to Machu Picchu", "Andean trekking", "Rainforest hikes", "Colca Canyon"], "best_time": "May-Sep", "unique_fact": "Home to the ancient Inca civilization and llamas", "signature_dish": "Ceviche", "dish_ingredients": "raw fish, lime, onions, cilantro"}
                ]
            elif travel_type == "beach":
                countries = [
                    {"name": "Maldives", "capital": "Malé", "rank": 1, "activities": ["Crystal clear waters", "Overwater bungalows", "Snorkeling", "Diving"], "best_time": "Nov-Apr", "unique_fact": "Lowest country in the world, average elevation 1.5m above sea level", "signature_dish": "Mas Huni", "dish_ingredients": "tuna, coconut, onions, chili"},
                    {"name": "Seychelles", "capital": "Victoria", "rank": 2, "activities": ["Pristine beaches", "Coral reefs", "Turtle watching", "Island hopping"], "best_time": "Apr-May, Oct-Nov", "unique_fact": "Home to the giant Aldabra tortoise", "signature_dish": "Grilled fish", "dish_ingredients": "red snapper, garlic, ginger, lime"},
                    {"name": "Bora Bora", "capital": "Vaitape", "rank": 3, "activities": ["Lagoon activities", "Overwater villas", "Snorkeling", "Sunset cruises"], "best_time": "May-Oct", "unique_fact": "Part of French Polynesia, known for its turquoise lagoon", "signature_dish": "Poisson cru", "dish_ingredients": "raw fish, coconut milk, lime, vegetables"}
                ]
            elif travel_type == "culture":
                countries = [
                    {"name": "Italy", "capital": "Rome", "rank": 1, "activities": ["Ancient ruins", "Renaissance art", "Historic cities", "Museums"], "best_time": "Apr-Jun, Sep-Oct", "unique_fact": "Home to more UNESCO World Heritage sites than any other country", "signature_dish": "Pasta Carbonara", "dish_ingredients": "pasta, eggs, pancetta, parmesan"},
                    {"name": "Greece", "capital": "Athens", "rank": 2, "activities": ["Archaeological sites", "Museums", "Byzantine churches", "Ancient temples"], "best_time": "Apr-May, Sep-Oct", "unique_fact": "Birthplace of democracy, philosophy, and the Olympic Games", "signature_dish": "Moussaka", "dish_ingredients": "eggplant, ground meat, béchamel, tomatoes"},
                    {"name": "Egypt", "capital": "Cairo", "rank": 3, "activities": ["Pyramids", "Temples", "Museums", "Historic sites"], "best_time": "Oct-Apr", "unique_fact": "Home to the Great Pyramid of Giza, one of the Seven Wonders", "signature_dish": "Koshari", "dish_ingredients": "rice, lentils, pasta, chickpeas, tomato sauce"}
                ]
            elif travel_type == "adventure":
                countries = [
                    {"name": "New Zealand", "capital": "Wellington", "rank": 1, "activities": ["Bungee jumping", "White-water rafting", "Mountain biking", "Skydiving"], "best_time": "Nov-Apr", "unique_fact": "Home to the kiwi bird and flightless kakapo", "signature_dish": "Pavlova", "dish_ingredients": "meringue, cream, kiwi, berries"},
                    {"name": "Nepal", "capital": "Kathmandu", "rank": 2, "activities": ["Mountaineering", "Trekking", "Paragliding", "White-water rafting"], "best_time": "Oct-Nov, Mar-Apr", "unique_fact": "Home to 8 of the world's 14 highest peaks", "signature_dish": "Dal Bhat", "dish_ingredients": "lentils, rice, vegetables, spices"},
                    {"name": "Costa Rica", "capital": "San José", "rank": 3, "activities": ["Rainforest canopy tours", "White-water rafting", "Volcano hiking", "Surfing"], "best_time": "Dec-Apr", "unique_fact": "Home to 5% of world's biodiversity despite being 0.03% of Earth's surface", "signature_dish": "Gallo Pinto", "dish_ingredients": "rice, beans, onions, cilantro"}
                ]
            elif travel_type == "budget":
                countries = [
                    {"name": "Thailand", "capital": "Bangkok", "rank": 1, "activities": ["Street food", "Temples", "Beaches", "Markets"], "best_time": "Nov-Mar", "unique_fact": "Home to the world's largest solid gold Buddha statue", "signature_dish": "Pad Thai", "dish_ingredients": "rice noodles, shrimp, eggs, tamarind"},
                    {"name": "Vietnam", "capital": "Hanoi", "rank": 2, "activities": ["Street food", "Historic sites", "Rice terraces", "Motorbike tours"], "best_time": "Oct-Apr", "unique_fact": "Home to Ha Long Bay with over 1,600 limestone islands", "signature_dish": "Pho", "dish_ingredients": "rice noodles, beef, herbs, broth"},
                    {"name": "India", "capital": "New Delhi", "rank": 3, "activities": ["Temples", "Street food", "Markets", "Historic sites"], "best_time": "Oct-Mar", "unique_fact": "Home to the Taj Mahal, one of the Seven Wonders", "signature_dish": "Butter Chicken", "dish_ingredients": "chicken, tomatoes, cream, spices"}
                ]
            elif travel_type == "luxury":
                countries = [
                    {"name": "Switzerland", "capital": "Bern", "rank": 1, "activities": ["Luxury resorts", "Fine dining", "Spa retreats", "Alpine experiences"], "best_time": "Jun-Aug, Dec-Mar", "unique_fact": "Home to some of the world's most expensive ski resorts", "signature_dish": "Fondue", "dish_ingredients": "cheese, white wine, garlic, bread"},
                    {"name": "Monaco", "capital": "Monaco", "rank": 2, "activities": ["Casinos", "Luxury yachts", "Fine dining", "Formula 1 Grand Prix"], "best_time": "May-Sep", "unique_fact": "Second smallest country in the world, highest population density", "signature_dish": "Barbajuan", "dish_ingredients": "dough, spinach, ricotta, herbs"},
                    {"name": "Maldives", "capital": "Malé", "rank": 3, "activities": ["Overwater villas", "Private islands", "Luxury spas", "Fine dining"], "best_time": "Nov-Apr", "unique_fact": "Lowest country in the world, average elevation 1.5m above sea level", "signature_dish": "Mas Huni", "dish_ingredients": "tuna, coconut, onions, chili"}
                ]
            else:  # Default fallback
                countries = [
                    {"name": "Nepal", "capital": "Kathmandu", "rank": 1, "activities": ["Everest Base Camp trek", "Annapurna Circuit", "High-altitude trekking", "Mountain climbing"], "best_time": "Oct-Nov, Mar-Apr", "unique_fact": "Home to 8 of the world's 14 highest peaks"},
                    {"name": "New Zealand", "capital": "Wellington", "rank": 2, "activities": ["Milford Track", "Alpine hiking", "Coastal walks", "Glacier trekking"], "best_time": "Dec-Mar", "unique_fact": "Home to the kiwi bird and flightless kakapo"},
                    {"name": "Peru", "capital": "Lima", "rank": 3, "activities": ["Inca Trail to Machu Picchu", "Andean trekking", "Rainforest hikes", "Colca Canyon"], "best_time": "May-Sep", "unique_fact": "Home to the ancient Inca civilization and llamas"}
                ]
            
            return {
                "title": f"Top {count} Countries for {travel_type.title()} Travel",
                "travel_type": travel_type,
                "countries": countries[:count]
            }
