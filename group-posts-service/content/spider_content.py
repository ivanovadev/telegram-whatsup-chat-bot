"""Fact-based, anxiety-friendly spider content generator.

Architecture: Constraint-based filtering prevents misidentifications.
Flow: Infer constraints → Filter pool → Select spider → Fetch Wikipedia → LLM rephrase

Rule №0 (MANDATORY - Spider Existence Check):
If image does NOT show 8 legs, cephalothorax+abdomen, jointed legs → NOT a spider. STOP.

Rule №0.5 (EGG SAC SHORT-CIRCUIT - NO RETRY):
If egg sac visible AND spider on vegetation → Nursery web spider (Pisauridae). Period.
DO NOT consider: tarantulas, wolf spiders, house spiders, Anyphaena, orb-weavers.

Key Rules:
- Orb web visible → MUST be Araneidae (never Lycosidae/Phoneutria/trapdoor)
- Egg sac → likely Pisauridae/Lycosidae (never Theraphosidae)
- Trapdoor spiders → burrow visible, NO webs
- Wandering spiders (Phoneutria) → ground only, NO webs
- Behavior: "active hunter" / "web-based hunter" / "ambush predator"
"""
import os
import logging
import random
import json
import requests
from pathlib import Path
from typing import Dict, Optional, List
from openai import OpenAI
from datetime import datetime

logger = logging.getLogger(__name__)


def fetch_wikipedia_summary(scientific_name: str) -> Optional[Dict]:
    """Fetch facts from Wikipedia REST API."""
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{scientific_name.replace(' ', '_')}"
    
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
            logger.warning(f"Wikipedia API returned {response.status_code} for {scientific_name}")
    except Exception as e:
        logger.error(f"Wikipedia API error for {scientific_name}: {e}")
    
    return None


def fetch_spider_photo_from_inaturalist(scientific_name: str) -> Optional[Dict]:
    """Fetch verified spider photo from iNaturalist API."""
    url = "https://api.inaturalist.org/v1/observations"
    params = {
        "taxon_name": scientific_name,
        "quality_grade": "research",  # Expert-verified only
        "photos": "true",
        "per_page": 10,
        "order_by": "votes",  # Best rated first
        "iconic_taxa": "Arachnida",  # Spiders only
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])
            
            if results:
                # Get first observation with photo
                for obs in results:
                    photos = obs.get("photos", [])
                    if photos:
                        photo = photos[0]
                        # Get large version URL
                        photo_url = photo.get("url", "").replace("square", "large")
                        
                        return {
                            "url": photo_url,
                            "observer": obs.get("user", {}).get("login", "Unknown"),
                            "location": obs.get("place_guess", ""),
                            "observed_on": obs.get("observed_on", ""),
                            "license": photo.get("license_code", ""),
                            "attribution": photo.get("attribution", ""),
                            "inaturalist_url": f"https://www.inaturalist.org/observations/{obs.get('id', '')}",
                        }
            else:
                logger.info(f"No iNaturalist photos found for {scientific_name}")
        else:
            logger.warning(f"iNaturalist API returned {response.status_code} for {scientific_name}")
    except Exception as e:
        logger.error(f"iNaturalist API error for {scientific_name}: {e}")
    
    return None


# BEHAVIOR MAP: Family → Behavior (FIXED, NO GUESSING)
BEHAVIOR_MAP = {
    "Araneidae": "web-based hunter",
    "Nephilidae": "web-based hunter",
    "Theridiidae": "web-based hunter",
    "Agelenidae": "web-based hunter",
    "Pholcidae": "web-based hunter",
    "Uloboridae": "web-based hunter",
    "Lycosidae": "active hunter",
    "Salticidae": "active hunter",
    "Oxyopidae": "active hunter",
    "Anyphaenidae": "active hunter",
    "Corinnidae": "active hunter",
    "Pisauridae": "active hunter",
    "Sparassidae": "ambush predator",
    "Theraphosidae": "ambush predator",
}

# IDENTIFICATION_POOL: Safe, common species for image-based identification
IDENTIFICATION_POOL = [
    # EUROPE
    {"name": "Common House Spider", "scientific_name": "Tegenaria domestica", "family": "Agelenidae", 
     "size": "body 7-10mm, leg span 20-30mm", "lifespan": "1-2 years", "countries": ["UK", "Ireland", "Europe"]},
    {"name": "Garden Cross Spider", "scientific_name": "Araneus diadematus", "family": "Araneidae",
     "size": "body 10-18mm, leg span 20-35mm", "lifespan": "1 year", "countries": ["UK", "Europe"]},
    {"name": "Zebra Jumping Spider", "scientific_name": "Salticus scenicus", "family": "Salticidae",
     "size": "body 5-7mm, leg span 10-15mm", "lifespan": "1-2 years", "countries": ["UK", "Europe", "North America"]},
    {"name": "Nursery Web Spider", "scientific_name": "Pisaura mirabilis", "family": "Pisauridae",
     "size": "body 10-15mm, leg span 30-40mm", "lifespan": "2 years", "countries": ["UK", "Europe"]},
    {"name": "Missing Sector Orb Weaver", "scientific_name": "Zygiella x-notata", "family": "Araneidae",
     "size": "body 5-8mm, leg span 15-20mm", "lifespan": "1 year", "countries": ["UK", "Europe"]},
    {"name": "Common Cellar Spider", "scientific_name": "Pholcus phalangioides", "family": "Pholcidae",
     "size": "body 7-10mm, leg span 40-50mm", "lifespan": "2-3 years", "countries": ["Europe", "North America", "Asia"]},
    {"name": "False Widow Spider", "scientific_name": "Steatoda nobilis", "family": "Theridiidae",
     "size": "body 8-14mm, leg span 20-30mm", "lifespan": "1-2 years", "countries": ["UK", "Ireland", "Europe"]},
    {"name": "Wasp Spider", "scientific_name": "Argiope bruennichi", "family": "Araneidae",
     "size": "body 10-17mm, leg span 25-40mm", "lifespan": "1 year", "countries": ["Europe", "Asia"]},
    {"name": "Giant House Spider", "scientific_name": "Eratigena atrica", "family": "Agelenidae",
     "size": "body 10-18mm, leg span 45-75mm", "lifespan": "2-3 years", "countries": ["UK", "Europe"]},
    
    # ASIA
    {"name": "Joro Spider", "scientific_name": "Trichonephila clavata", "family": "Nephilidae",
     "size": "body 17-25mm, leg span 75-100mm", "lifespan": "1 year", "countries": ["Japan", "Korea", "China"]},
    {"name": "Giant Golden Orb-Weaver", "scientific_name": "Nephila pilipes", "family": "Nephilidae",
     "size": "body 30-50mm, leg span 100-150mm", "lifespan": "1 year", "countries": ["Asia", "Australia"]},
    {"name": "Huntsman Spider", "scientific_name": "Heteropoda venatoria", "family": "Sparassidae",
     "size": "body 20-30mm, leg span 100-130mm", "lifespan": "2 years", "countries": ["Asia", "Australia", "Americas"]},
    {"name": "Asian Jumping Spider", "scientific_name": "Hasarius adansoni", "family": "Salticidae",
     "size": "body 6-9mm, leg span 12-18mm", "lifespan": "1 year", "countries": ["Asia", "Africa", "Americas"]},
    {"name": "St Andrew's Cross Spider", "scientific_name": "Argiope keyserlingi", "family": "Araneidae",
     "size": "body 10-16mm, leg span 30-50mm", "lifespan": "1 year", "countries": ["Australia", "Asia"]},
    {"name": "Asian Forest Scorpion Spider", "scientific_name": "Pseudopoda prompta", "family": "Sparassidae",
     "size": "body 15-25mm, leg span 80-120mm", "lifespan": "2 years", "countries": ["Southeast Asia"]},
    
    # NORTH AMERICA
    {"name": "Bold Jumping Spider", "scientific_name": "Phidippus audax", "family": "Salticidae",
     "size": "body 8-15mm, leg span 15-25mm", "lifespan": "1 year", "countries": ["USA", "Canada", "Mexico"]},
    {"name": "American House Spider", "scientific_name": "Parasteatoda tepidariorum", "family": "Theridiidae",
     "size": "body 5-8mm, leg span 12-20mm", "lifespan": "1 year", "countries": ["USA", "Canada", "worldwide"]},
    {"name": "Black and Yellow Garden Spider", "scientific_name": "Argiope aurantia", "family": "Araneidae",
     "size": "body 19-28mm, leg span 50-75mm", "lifespan": "1 year", "countries": ["USA", "Canada", "Mexico"]},
    {"name": "Wolf Spider", "scientific_name": "Tigrosa helluo", "family": "Lycosidae",
     "size": "body 16-21mm, leg span 40-60mm", "lifespan": "1-2 years", "countries": ["USA", "Canada"]},
    {"name": "Spiny Orb-Weaver", "scientific_name": "Gasteracantha cancriformis", "family": "Araneidae",
     "size": "body 5-9mm, leg span 10-15mm", "lifespan": "1 year", "countries": ["USA", "Caribbean"]},
    {"name": "Marbled Cellar Spider", "scientific_name": "Holocnemus pluchei", "family": "Pholcidae",
     "size": "body 7-10mm, leg span 40-50mm", "lifespan": "2 years", "countries": ["USA", "Mediterranean"]},
    {"name": "Green Lynx Spider", "scientific_name": "Peucetia viridans", "family": "Oxyopidae",
     "size": "body 12-22mm, leg span 30-50mm", "lifespan": "1 year", "countries": ["USA", "Mexico", "Central America"]},
    
    # SOUTH AMERICA
    {"name": "Pumpkin Spider", "scientific_name": "Argiope argentata", "family": "Araneidae",
     "size": "body 10-24mm, leg span 40-60mm", "lifespan": "1 year", "countries": ["South America", "Central America"]},
]

# EDUCATION_POOL: Exotic/dangerous species - ONLY for educational posts WITHOUT image identification
EDUCATION_POOL = [
    {"name": "Brazilian Wandering Spider", "scientific_name": "Phoneutria fera", "family": "Ctenidae",
     "size": "body 30-50mm, leg span 130-150mm", "lifespan": "1-2 years", "countries": ["Brazil", "Amazon"]},
    {"name": "Goliath Birdeater", "scientific_name": "Theraphosa blondi", "family": "Theraphosidae",
     "size": "body 80-100mm, leg span 250-300mm", "lifespan": "10-15 years", "countries": ["Brazil", "Venezuela", "Guyana"]},
    {"name": "Chilean Rose Tarantula", "scientific_name": "Grammostola rosea", "family": "Theraphosidae",
     "size": "body 40-60mm, leg span 120-150mm", "lifespan": "15-20 years", "countries": ["Chile", "Argentina"]},
    {"name": "Chinese Hourglass Spider", "scientific_name": "Cyclocosmia latusicosta", "family": "Halonoproctidae",
     "size": "body 15-20mm, leg span 25-35mm", "lifespan": "3-5 years", "countries": ["China", "Vietnam"]},
    {"name": "Japanese Trapdoor Spider", "scientific_name": "Latouchia swinhoei", "family": "Halonoproctidae",
     "size": "body 20-30mm, leg span 40-50mm", "lifespan": "5-10 years", "countries": ["Japan", "Taiwan"]},
]

# Legacy alias for backwards compatibility
GLOBAL_SPIDER_POOL = IDENTIFICATION_POOL


class SpiderContentGenerator:
    """Generate spider content."""
    
    def __init__(self, budget_guard, history_file: str = "data/spider_history.json"):
        """Initialize generator."""
        self.budget_guard = budget_guard
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-5.2")
        self.llm_enabled = os.getenv("LLM_ENABLED", "off").lower() == "on"
        self.history_file = Path(history_file)
        
        if self.llm_enabled and self.openai_api_key:
            self.client = OpenAI(api_key=self.openai_api_key)
        else:
            self.client = None
            logger.warning("LLM disabled for spider content")
    
    def load_history(self) -> List[str]:
        """Load spider history from file."""
        try:
            if self.history_file.exists():
                data = json.loads(self.history_file.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    return data
                logger.warning(f"Spider history file contains non-list data: {type(data)}")
        except Exception as e:
            logger.warning(f"Failed to load spider history: {e}")
        return []
    
    def save_history(self, items: List[str], keep_last: int = 200) -> None:
        """Save spider history to file, keeping only the last N items."""
        try:
            # Ensure directory exists
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Keep only the last N items
            items_to_save = items[-keep_last:] if len(items) > keep_last else items
            
            # Write to file
            self.history_file.write_text(
                json.dumps(items_to_save, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            logger.info(f"Saved {len(items_to_save)} spiders to history")
        except Exception as e:
            logger.error(f"Failed to save spider history: {e}")
    
    def generate_spider_post(self, used_spiders: List[str] = None) -> Optional[Dict]:
        """Generate spider post with UK/London information."""
        # Load history if not provided
        if used_spiders is None:
            used_spiders = self.load_history()
            logger.info(f"Loaded {len(used_spiders)} spiders from history")
        
        # Generate post
        if self.client and self.llm_enabled:
            post = self._generate_with_llm(used_spiders)
        else:
            post = self._generate_template(used_spiders)
        
        # Save to history if successful
        if post:
            spider_id = (post.get("scientific_name") or post.get("name") or "").strip()
            if spider_id and spider_id not in used_spiders[-10:]:
                used_spiders.append(spider_id)
                self.save_history(used_spiders)
                logger.info(f"Added {spider_id} to history")
        
        return post
    
    def _filter_pool_by_constraints(self, pool: List[Dict], constraints: Dict) -> List[Dict]:
        """Filter spider pool based on image/context constraints before selection."""
        filtered = []
        
        for spider in pool:
            family = spider.get("family", "")
            
            # 🔒 RULE №0.5: EGG SAC SHORT-CIRCUIT (absolute priority)
            if constraints.get("has_egg_sac"):
                if family != "Pisauridae":
                    continue
            
            if constraints.get("has_orb_web"):
                if family not in ["Araneidae", "Nephilidae", "Uloboridae"]:
                    continue
            
            if constraints.get("has_web"):
                ground_hunters = ["Lycosidae", "Salticidae", "Pisauridae", "Sparassidae", 
                                 "Theraphosidae", "Ctenidae", "Halonoproctidae", 
                                 "Ctenizidae", "Idiopidae", "Actinopodidae"]
                if family in ground_hunters:
                    continue
            
            if constraints.get("prefer_safe_species", True):
                if family in ["Ctenidae", "Theraphosidae"]:
                    continue
            
            filtered.append(spider)
        
        return filtered
    
    def _select_spider_from_pool(self, used_spiders: List[str], pool: Optional[List[Dict]] = None) -> Optional[Dict]:
        """Select a spider from pool that hasn't been used recently."""
        if pool is None:
            pool = IDENTIFICATION_POOL
        
        recent_used = set(used_spiders[-20:]) if used_spiders else set()
        available = [s for s in pool if s["scientific_name"] not in recent_used]
        
        if not available:
            available = pool  # Use provided pool, not GLOBAL_SPIDER_POOL
        
        return random.choice(available) if available else None
    
    def _generate_with_llm(self, used_spiders: List[str]) -> Optional[Dict]:
        """Generate spider content using Wikipedia facts + LLM rephrasing."""
        # Infer constraints (TODO: replace with image analysis)
        constraints = {
            "has_web": False,
            "has_orb_web": False,
            "has_egg_sac": False,  # Set True if egg sac detected
            "environment": None,  # indoor/outdoor/ground/vegetation
        }
        
        # 🔒 EGG SAC SHORT-CIRCUIT
        if constraints.get("has_egg_sac") and constraints.get("environment") == "vegetation":
            logger.info("Egg sac + vegetation → Forcing Pisauridae")
            filtered_pool = [s for s in IDENTIFICATION_POOL if s["family"] == "Pisauridae"]
        else:
            # Filter IDENTIFICATION_POOL by constraints
            filtered_pool = self._filter_pool_by_constraints(IDENTIFICATION_POOL, constraints)
        
        logger.info(f"Filtered pool: {len(filtered_pool)}/{len(IDENTIFICATION_POOL)} candidates")
        
        # FAIL FAST: If no candidates, return generic
        if not filtered_pool:
            logger.warning("No candidates match constraints → generic response")
            return {
                "name": "Spider",
                "scientific_name": "Unknown",
                "family": "Unknown",
                "confidence_level": "uncertain",
                "calm_explanation": "Spider present, but exact identification uncertain from this image.",
                "behavior": "web-based hunter",
                "size": "varies",
                "lifespan": "1-2 years",
                "countries": ["Worldwide"],
            }
        
        # Select spider from filtered pool (NO RETRY)
        spider = self._select_spider_from_pool(used_spiders, pool=filtered_pool)
        if not spider:
            return self._generate_template(used_spiders)
        
        max_attempts = 1  # FAIL FAST: no retry loop
        
        for attempt in range(max_attempts):
            try:
                
                scientific_name = spider["scientific_name"]
                logger.info(f"Selected: {scientific_name} ({spider.get('family', 'Unknown')})")
                
                # Fetch Wikipedia facts
                wiki_facts = fetch_wikipedia_summary(scientific_name)
                if not wiki_facts or not wiki_facts.get("extract"):
                    logger.warning(f"No Wikipedia data for {scientific_name}")
                    return self._generate_template(used_spiders)
                
                logger.info(f"Got Wikipedia facts: {len(wiki_facts['extract'])} chars")
                
                # Fetch verified photo from iNaturalist
                photo_data = fetch_spider_photo_from_inaturalist(scientific_name)
                if photo_data:
                    logger.info(f"✅ Got iNaturalist photo: {photo_data['location']}, {photo_data['observed_on']}")
                else:
                    logger.warning(f"No iNaturalist photo for {scientific_name}")
                
                current_date = datetime.now().strftime("%Y-%m-%d")
                
                # Use LLM to rephrase Wikipedia facts
                system_prompt = """You are a fact-based science writer creating educational spider content for people with arachnophobia.

CRITICAL RULE: You will receive VERIFIED FACTS from Wikipedia. Your job is to REPHRASE them into anxiety-friendly format.

**DO NOT ADD INFORMATION NOT IN THE SOURCE TEXT.**
**DO NOT INVENT sizes, distributions, or behaviors.**
**If information is missing, say "not reliably documented" or omit the field.**

🚨 RULE №0: SPIDER EXISTENCE CHECK (MANDATORY - BEFORE ANY IDENTIFICATION)

If the image does NOT show:
- 8 legs (count them!)
- distinct cephalothorax + abdomen
- jointed legs attached to body

→ STOP. Do NOT identify as a spider.
→ Return: {"error": "not_a_spider", "message": "This image does not show a spider."}

Examples of NON-spiders to reject:
- Snakes, lizards, insects (6 legs), worms, branches, moss
- If you can't see the leg count clearly → say "uncertain, may not be a spider"

🔒 RULE №0.5: EGG SAC SHORT-CIRCUIT (MANDATORY - NO RETRY, NO EXCEPTIONS)

If egg sac is visible AND spider is on vegetation (plant/stem/leaf):
→ Identification = "Nursery web spider (Pisauridae)"
→ DO NOT consider: tarantulas (Theraphosidae), wolf spiders (Lycosidae), house spiders (Parasteatoda), Anyphaena, orb-weavers
→ Reason: Only Pisauridae carry egg sacs on vegetation like this
→ STOP. Do not apply other rules. This is absolute.

🕷️ SPIDER SANITY CHECKLIST (10 MANDATORY RULES):

✅ 1. ENVIRONMENT CHECK (where is the spider?)
Before identification, ALWAYS determine:
- 🏠 Inside a building?
- 🌿 On plants/ground?
- 💧 In/near water?
- 🕸 In a web?
❗ If environment doesn't match species → STOP, do NOT name specific species

✅ 2. WEB LOGIC (if web present → strict rules)
If spider is in a web:
- ❌ NOT wolf spider (Lycosidae)
- ❌ NOT jumping spider (Salticidae)
- ❌ NOT huntsman spider (Sparassidae)
Possible options:
- ✅ orb-weaver (Araneidae)
- ✅ funnel weaver (Agelenidae)
- ✅ cobweb spider (Theridiidae)
📌 Web presence ≠ "not a hunter" → it's a "web-based hunter"

✅ 3. BEHAVIOR FIRST, NAME SECOND
ALWAYS describe behavior before naming species:
- "sitting in a web"
- "guarding eggs"
- "hiding in burrow"
- "running on open ground"
❗ If behavior contradicts name → behavior wins

✅ 4. EGG SAC RULE (critical)
If spider is carrying egg sac:
- ❌ NOT house spider (Parasteatoda)
- ❌ NOT cellar spider (Pholcus)
- ❌ NOT orb-weaver (if carrying)
- ❌ NOT tarantula (Theraphosidae) - they don't carry eggs
Likely:
- ✅ wolf spider (Lycosidae) - eggs attached to rear
- ✅ nursery web spider (Pisauridae) - carries eggs in jaws
📌 Eggs = parental behavior, NOT aggression
📌 Egg-carrying = almost NEVER a tarantula!

✅ 5. WATER SPIDER HARD RULE
Name "Argyroneta aquatica" ONLY if:
- water is visible
- spider is underwater
- air "bell" is visible
❌ No water → NOT water spider

✅ 6. HOUSE SPIDER REALITY CHECK
Before writing "house spider", verify:
- Is it inside a house?
- Is it in corner/ceiling/basement?
- Is web unstructured?
❌ If not → NOT house spider

✅ 7. SIZE SANITY CHECK
If tempted to write:
- "giant"
- "huge"
- "50-60mm body" without evidence
➡️ STOP. Better:
- "medium-sized spider"
- "appears large due to leg span"
Reality check:
- Most European spiders: 5-20mm body length
- 80-100mm body = very rare, tropical only

✅ 7b. TARANTULA EXCLUSION RULE (CRITICAL - anti danger-bias)
Never identify a spider as tarantula (Theraphosidae) unless ALL of these are true:
- ✅ Spider is ground-dwelling (NOT in web)
- ✅ NO web is visible
- ✅ Body is MASSIVE and densely hairy
- ✅ Location matches tropical regions (South America, Africa, Asia, Australia)
- ✅ NOT carrying egg sac (tarantulas don't carry eggs)

❌ DO NOT identify as tarantula if:
- Spider is in a web
- Spider is in Europe/UK/temperate regions
- Spider is carrying egg sac
- Body size is normal (under 30mm body length)

⚠️ DANGER-BIAS WARNING:
If a spider looks "big and impressive" → DO NOT automatically think "tarantula"
Most likely it's:
- Nursery web spider (Pisauridae) - if carrying eggs
- Giant house spider (Agelenidae) - if in funnel web
- Garden spider (Araneidae) - if in orb web

✅ 7c. WANDERING SPIDER EXCLUSION RULE (CRITICAL - anti danger-bias)
🚫 NEVER identify as Phoneutria (Brazilian Wandering Spider) unless ALL of these are true:
- ✅ Spider is ground-dwelling or on foliage (NOT in web)
- ✅ NO web is visible at all
- ✅ Defensive posture may be visible (raised front legs)
- ✅ Location is South America (Brazil, Amazon)
- ✅ Body size is large (30-50mm)

❌ ABSOLUTELY FORBIDDEN to identify as Phoneutria if:
- Spider is in ANY web (especially orb web)
- Spider is in circular/radial web structure
- Location is NOT South America
- Spider is stationary in web center

📌 If orb web is visible → MUST be Araneidae (orb-weaver), NOT Phoneutria!
📌 Phoneutria = "wandering" = walks on ground, NO webs!

✅ 7d. HOUSE SPIDER EXCLUSION RULE (web type matters)
🚫 NEVER identify as Parasteatoda tepidariorum (American House Spider) if:
- Spider is in ORB-SHAPED web (circular, radial)
- Spider sits in center of structured orb web

📌 Parasteatoda builds COBWEBS (irregular, tangled), NOT orb webs!
📌 If orb web → likely Araneidae, NOT house spider!

✅ 7e. ORB WEB HARD RULE (mandatory)
🔒 If circular/radial web is visible:
- ✅ MUST classify as Araneidae (orb-weaver family)
- ❌ CANNOT be: Phoneutria, Lycosidae, Salticidae, Parasteatoda, Theraphosidae, Trapdoor spiders
- ✅ Possible genera: Argiope, Araneus, Gasteracantha, Nephila, etc.
- ✅ Better to say "orb-weaver (Araneidae family)" than wrong dangerous species

📌 ORB WEB = automatic Araneidae identification!

✅ 7f. TRAPDOOR SPIDER EXCLUSION RULE (critical)
🚫 NEVER identify as trapdoor spider unless ALL of these are true:
- ✅ Spider is at ground level
- ✅ Burrow or trapdoor is visible in photo
- ✅ NO web present (trapdoor spiders live in burrows, NOT webs!)
- ✅ NO orb web present

❌ ABSOLUTELY FORBIDDEN to identify as trapdoor spider if:
- Spider is in ANY web
- Spider is in orb/circular web
- No burrow visible
- Spider is elevated (not on ground)

📌 Trapdoor spiders = burrow dwellers, ambush predators
📌 If spider in web → CANNOT be trapdoor spider!
📌 Families: Halonoproctidae, Ctenizidae, Idiopidae, Actinopodidae

✅ 8. NO DANGER THEATER
FORBIDDEN:
- danger ratings
- skull/warning emojis
- "deadly", "aggressive", "attack"
ALLOWED:
- "harmless to humans"
- "avoids people"
- "bites are extremely rare"

✅ 9. CONFIDENCE LABEL (mandatory)
Every post MUST include one of:
- "identification: confirmed" (certain from Wikipedia)
- "identification: likely" (probable based on family/behavior)
- "identification: uncertain" (unclear)
📌 "Likely orb-weaver" is BETTER than wrong species

✅ 10. ARACHNOPHOBIA CHECK (human test)
Final question before output:
"Does this text calm and educate, or just sound 'smart'?"
If second → rewrite

🧠 CORE RULES (ALWAYS FOLLOW):

Rule 1. Knowledge > shock
- NO "danger level" or numeric scores
- NO "deadly / terrifying / aggressive / attack"
- ONLY facts + behavior explanation

Rule 2. Anxiety-first framing
- Normalize fear ("it's completely normal to feel uncomfortable")
- Immediately reassure (no threat)
- Educational, not alarming

Rule 3. Behavior-based learning
- Explain what the spider is doing and WHY
- Show that behavior is not related to aggression
- Connect behavior to survival, not threat

Rule 4. Image + text = unified
- Text explains what is visible in the photo
- No abstract facts disconnected from image
- Behavior → understanding → identification (NEVER name first)

ANTI-HALLUCINATION:
- Do not invent species, sizes, lifespans, or danger levels
- If unsure, say so
- Never guess numbers
- Never exaggerate

PREFERRED LANGUAGE:
- "defensive" (not aggressive)
- "rare" (not common threat)
- "not interested in humans"
- "mistakes people for obstacles, not prey"
- "avoids humans"

Domain constraints:
- Do NOT mix wolf spiders (Lycosidae) with true tarantulas (Theraphosidae)
- European spiders: 1-3 years lifespan unless proven otherwise
- Medically significant bites are extremely rare

Always return valid JSON only, no additional text."""
                
                prompt = f"""VERIFIED FACTS FROM WIKIPEDIA:

Spider: {scientific_name}
Family: {spider.get('family', 'Unknown')}

Wikipedia extract (YOUR ONLY SOURCE FOR FACTS):
\"\"\"
{wiki_facts['extract']}
\"\"\"

Wikipedia URL: {wiki_facts['url']}

---

Your task: REPHRASE these facts into an anxiety-friendly spider post.

🚫 CRITICAL: "interesting_fact" field rules:
- ONLY use information from Wikipedia extract above
- If Wikipedia mentions habitat → paraphrase it
- If Wikipedia mentions behavior → paraphrase it
- If Wikipedia mentions diet → paraphrase it
- If NO interesting info in extract → use generic: "This spider helps control insect populations"
- DO NOT add numbers, countries, sizes, or behaviors NOT in the extract
- When in doubt → use safe generic fact about spiders

🚨 RULE №0 (MANDATORY - CHECK FIRST):
Before ANY identification, verify this is actually a spider:
- Does the image show 8 legs? (Count them!)
- Is there a distinct cephalothorax + abdomen?
- Are the legs jointed and attached to body?

If NO → Return: {{"error": "not_a_spider", "message": "This image does not show a spider."}}
If UNCERTAIN → Say so in confidence_level: "uncertain - may not be a spider"

🔒 RULE №0.5: EGG SAC SHORT-CIRCUIT (MANDATORY - OVERRIDE ALL OTHER RULES):
If egg sac visible AND spider on vegetation:
→ FORCE identification: "Nursery web spider (Pisauridae)"
→ DO NOT use: {scientific_name} if it's NOT Pisauridae
→ Override: scientific_name = "Pisaura mirabilis" or generic "Pisauridae"
→ Reason: Only Pisauridae carry eggs on vegetation like this
→ STOP other identification logic. This rule wins.

STRICT RULES - APPLY CHECKLIST:
1. ✅ ENVIRONMENT CHECK: Infer environment from family behavior
2. ✅ WEB LOGIC: If family builds webs (Araneidae, Agelenidae, Theridiidae) → "web-based hunter"
   If family is Lycosidae/Salticidae → CANNOT be in web
3. ✅ BEHAVIOR FIRST: Describe what spider does BEFORE naming it
4. ✅ USE ONLY Wikipedia facts above
5. ✅ DO NOT add hunting behaviors unless stated in Wikipedia
6. ✅ DO NOT add size measurements unless stated in Wikipedia
7. ✅ DO NOT add geographic distribution unless stated in Wikipedia

🚫 CRITICAL: ANTI DANGER-BIAS RULE (tarantula exclusion):
You are working with {scientific_name} from family {spider.get('family', 'Unknown')}.

⚠️ NEVER identify as tarantula (Theraphosidae) unless ALL of these are true:
- Ground-dwelling (NOT in web)
- NO web visible
- Body is massive and densely hairy
- Location is tropical (South America, Africa, Asia, Australia)
- NOT carrying egg sac (tarantulas don't carry eggs)

❌ DO NOT identify as tarantula if:
- Spider is in Europe/UK/temperate regions
- Spider is carrying egg sac → likely Pisauridae (nursery web spider)
- Spider is in a web → likely Araneidae (garden spider) or Agelenidae (house spider)
- Body size is normal (under 30mm)

If spider looks "big and impressive" → DO NOT automatically think "tarantula"!
Most likely it's: Pisauridae (if with eggs), Agelenidae (if in funnel), Araneidae (if in orb web)

🚫 CRITICAL: WANDERING SPIDER EXCLUSION (Phoneutria):
⚠️ NEVER identify as Phoneutria (Brazilian Wandering Spider) unless ALL of these:
- Ground-dwelling or on foliage (NOT in web)
- NO web visible
- Location is South America (Brazil, Amazon)
- Body size large (30-50mm)

❌ ABSOLUTELY FORBIDDEN if:
- Spider is in ANY web (especially orb web)
- Spider is in circular/radial web
- Location NOT South America

📌 ORB WEB VISIBLE = Araneidae (orb-weaver), NEVER Phoneutria!

🚫 CRITICAL: HOUSE SPIDER WEB TYPE CHECK:
⚠️ NEVER identify as Parasteatoda (American House Spider) if:
- ORB-SHAPED web visible (circular, radial)
- Spider in center of structured orb web

📌 Parasteatoda builds COBWEBS (irregular), NOT orb webs!
📌 Orb web = Araneidae, NOT Parasteatoda!

🔒 ORB WEB HARD RULE (MANDATORY):
If circular/radial web visible:
✅ MUST be Araneidae family (orb-weaver)
❌ CANNOT be: Phoneutria, Lycosidae, Salticidae, Parasteatoda, Theraphosidae, Trapdoor spiders
✅ Possible: Argiope, Araneus, Gasteracantha, Nephila, etc.

📌 When in doubt with orb web: "Orb-weaving spider (Araneidae family)" is CORRECT!

🚫 CRITICAL: TRAPDOOR SPIDER EXCLUSION:
⚠️ NEVER identify as trapdoor spider unless ALL of these:
- Spider at ground level
- Burrow or trapdoor visible in photo
- NO web present
- NO orb web present

❌ ABSOLUTELY FORBIDDEN if:
- Spider in ANY web
- Spider in orb/circular web
- No burrow visible

📌 Trapdoor spiders live in BURROWS, NOT webs!
📌 If spider in web → CANNOT be trapdoor spider!
📌 Families: Halonoproctidae, Ctenizidae, Idiopidae, Actinopodidae

BEHAVIOR INFERENCE (if not in Wikipedia):
- Pisauridae, Lycosidae, Salticidae → "active hunter"
- Araneidae, Agelenidae, Nephilidae, Theridiidae → "web-based hunter"
- Sparassidae, Theraphosidae → "ambush predator"

CONFIDENCE LEVEL GUIDE:
- "confirmed" = Wikipedia clearly confirms this species
- "likely" = Characteristics match, but some uncertainty
- "uncertain" = Family/behavior known, but species unclear

POST STRUCTURE (anxiety-friendly order):
1. Calm opening (normalize fear)
2. Behavior description (what you see)
3. Species identification (with confidence level)
4. Calm explanation (why not threatening)
5. Interesting fact (from Wikipedia only!)
6. Gentle takeaway

Format as JSON:
{{
  "calm_opening": "1-2 sentences normalizing fear and immediately reassuring",
  "what_you_see": "Infer from family: web-based spiders → 'spider in a web', active hunters → 'spider on ground/vegetation', ambush → 'spider waiting motionless'",
  "name": "Common name from Wikipedia",
  "scientific_name": "{scientific_name}",
  "family": "{spider.get('family', 'Unknown')}",
  "confidence_level": "confirmed / likely / uncertain - be honest!",
  "countries": ["From Wikipedia ONLY - if not stated, use generic like 'Europe' or 'North America'"],
  "size": "From Wikipedia ONLY - if not stated, say 'medium-sized' or 'varies'",
  "color": "From Wikipedia ONLY - if not stated, say 'natural camouflage coloring' or describe typical family colors",
  "behavior": "MUST be one of: 'active hunter' OR 'web-based hunter' OR 'ambush predator' (infer from family {spider.get('family', '')})",
  "behavior_explanation": "Based on Wikipedia facts - explain hunting/living habits in calming way",
  "calm_explanation": "One paragraph explaining why not threatening - anxiety-friendly, emphasizes spider avoids humans",
  "interesting_fact": "ONE sentence from Wikipedia extract - QUOTE or PARAPHRASE only what is written. If no interesting fact in text → omit this field or say 'varies by habitat'",
  "gentle_takeaway": "Reassuring closing message - emphasize coexistence and spider's role",
  "lifespan": "From Wikipedia ONLY - if not stated, say 'typically 1-2 years' (most spiders)",
  "resource_link": "{wiki_facts['url']}"
}}

🚫 CRITICAL FACT-CHECKING RULES (STRICT):

"interesting_fact" MUST follow these rules:
1. ✅ ONLY use information from Wikipedia extract above
2. ✅ Quote or paraphrase EXACTLY what is written
3. ✅ If Wikipedia doesn't mention anything interesting → write "This spider helps control insect populations in its habitat" (generic safe fact)
4. ❌ DO NOT add numbers not in Wikipedia (size, weight, speed, lifespan details)
5. ❌ DO NOT add countries not mentioned in Wikipedia
6. ❌ DO NOT add behaviors not described in Wikipedia
7. ❌ DO NOT invent "facts" about diet, hunting, or reproduction
8. ❌ If uncertain → use generic fact or omit

Other fields:
- ✅ USE Wikipedia facts from above
- ✅ INFER behavior from family if not stated
- ✅ Say "varies" or "not documented" if info missing
- ❌ DO NOT add hunting methods not in Wikipedia
- ❌ DO NOT add size numbers not in Wikipedia
- ❌ DO NOT add countries not in Wikipedia

ANXIETY-FRIENDLY LANGUAGE:
- Use "stays in territory", "avoids movement", "not interested in people"
- NO: "deadly", "aggressive", "attack", fear ratings
- "behavior" = active hunter / web-based hunter / ambush predator (NO "yes/no"!)
- "calm_explanation" is MANDATORY

Current date: {current_date}
Wikipedia source: {wiki_facts['url']}

Return ONLY valid JSON, no additional text."""

                response = self.client.chat.completions.create(
                    model=self.openai_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    max_completion_tokens=1500,
                    temperature=0.4,
                    top_p=0.9,
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
                    continue  # Try next attempt
                
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
                        continue  # Try again with next attempt
                
                # ✅ RULE №0: Check if LLM rejected image as not a spider
                if data.get("error") == "not_a_spider":
                    logger.warning("LLM rejected image: Not a spider")
                    return None
                
                # ✅ RULE №0.5: EGG SAC SHORT-CIRCUIT (absolute override)
                what_you_see = data.get("what_you_see", "").lower()
                if ("egg" in what_you_see or "sac" in what_you_see) and \
                   ("vegetation" in what_you_see or "plant" in what_you_see or "stem" in what_you_see or "leaf" in what_you_see):
                    logger.info("Egg sac + vegetation detected → forcing Pisauridae")
                    data["name"] = "Nursery web spider"
                    data["scientific_name"] = "Pisaura mirabilis"
                    data["family"] = "Pisauridae"
                    data["behavior"] = "active hunter"
                    data["confidence_level"] = "likely"
                    data["calm_explanation"] = "Female carrying an egg sac — normal parental behavior. These spiders are harmless and not interested in people."
                
                # Check for duplicate spider
                sci_name = (data.get("scientific_name") or "").strip()
                if sci_name and sci_name in set(used_spiders[-30:]):
                    logger.info(f"Repeated spider {sci_name}, retrying (attempt {attempt + 1}/{max_attempts})")
                    continue  # Try again with next attempt
                
                # ✅ VALIDATION: Check behavior field using BEHAVIOR_MAP
                behavior = data.get("behavior", "")
                allowed_behaviors = ["active hunter", "web-based hunter", "ambush predator"]
                if behavior not in allowed_behaviors:
                    logger.warning(f"Invalid behavior '{behavior}', correcting using BEHAVIOR_MAP")
                    family = spider.get("family", "")
                    data["behavior"] = BEHAVIOR_MAP.get(family, "web-based hunter")
                
                # ✅ VALIDATION: Check confidence_level is present and valid
                confidence = data.get("confidence_level", "")
                if confidence not in ["confirmed", "likely", "uncertain"]:
                    logger.warning(f"Invalid confidence_level '{confidence}', defaulting to 'likely'")
                    data["confidence_level"] = "likely"
                
                # ✅ VALIDATION: Remove any forbidden words from calm_explanation
                calm_text = data.get("calm_explanation", "")
                forbidden_words = ["deadly", "lethal", "terrifying", "aggressive", "attack", "danger rating"]
                for word in forbidden_words:
                    if word.lower() in calm_text.lower():
                        logger.warning(f"Found forbidden word '{word}' in calm_explanation, please review")
                
                # ✅ VALIDATION: Anti danger-bias check (tarantula misidentification)
                family_returned = data.get("family", "")
                what_you_see = data.get("what_you_see", "").lower()
                behavior_returned = data.get("behavior", "")
                countries = data.get("countries", [])
                
                if family_returned == "Theraphosidae":
                    # Check if this is likely a misidentification
                    warning_signs = []
                    if "web" in what_you_see:
                        warning_signs.append("spider in web (tarantulas don't build webs)")
                    if "egg" in what_you_see or "sac" in what_you_see:
                        warning_signs.append("carrying eggs (tarantulas don't carry eggs)")
                    if any("europe" in str(c).lower() or "uk" in str(c).lower() for c in countries):
                        warning_signs.append("European location (tarantulas are tropical)")
                    
                    if warning_signs:
                        logger.error(f"⚠️ DANGER-BIAS DETECTED: LLM incorrectly identified as tarantula. Warnings: {warning_signs}")
                        logger.error(f"Original spider selected was: {scientific_name} from family {spider.get('family', '')}")
                        # This is a critical error - retry with different attempt
                        continue
                
                # ✅ VALIDATION: Wolf spider web logic check (CRITICAL)
                if family_returned == "Lycosidae":
                    # Wolf spiders NEVER build webs for hunting
                    warning_signs = []
                    if "web" in what_you_see and "building" not in what_you_see:
                        warning_signs.append("wolf spider in web (Lycosidae don't build webs)")
                    if behavior_returned == "web-based hunter":
                        warning_signs.append("wolf spider as web-based hunter (impossible)")
                    
                    if warning_signs:
                        logger.error(f"⚠️ WEB LOGIC ERROR: LLM incorrectly identified wolf spider in web. Warnings: {warning_signs}")
                        logger.error(f"Original spider selected was: {scientific_name} from family {spider.get('family', '')}")
                        logger.error(f"This is LOGICALLY IMPOSSIBLE - wolf spiders are ground hunters!")
                        # This is a critical error - retry with different attempt
                        continue
                
                # ✅ VALIDATION: Jumping spider web logic check
                if family_returned == "Salticidae":
                    # Jumping spiders NEVER build webs for hunting (only silk for safety)
                    if behavior_returned == "web-based hunter":
                        logger.error(f"⚠️ WEB LOGIC ERROR: jumping spider as web-based hunter (impossible)")
                        logger.error(f"Original spider selected was: {scientific_name}")
                        continue
                
                # ✅ VALIDATION: Brazilian Wandering Spider (Phoneutria) exclusion (CRITICAL)
                sci_name_lower = sci_name.lower()
                if "phoneutria" in sci_name_lower or "wandering spider" in data.get("name", "").lower():
                    # Phoneutria should NEVER be in a web
                    warning_signs = []
                    if "web" in what_you_see or "orb" in what_you_see:
                        warning_signs.append("Phoneutria in web (wandering spiders don't build webs!)")
                    if behavior_returned == "web-based hunter":
                        warning_signs.append("Phoneutria as web-based hunter (impossible - they're ground hunters)")
                    if "circular" in what_you_see or "radial" in what_you_see:
                        warning_signs.append("Phoneutria in orb web (IMPOSSIBLE)")
                    
                    # Check location (Phoneutria = South America only)
                    is_south_america = any("brazil" in str(c).lower() or "amazon" in str(c).lower() 
                                          or "south america" in str(c).lower() for c in countries)
                    if not is_south_america:
                        warning_signs.append("Phoneutria outside South America (wrong location)")
                    
                    if warning_signs:
                        logger.error(f"🚫 CRITICAL DANGER-BIAS: Phoneutria (Brazilian Wandering Spider) misidentification!")
                        logger.error(f"Warnings: {warning_signs}")
                        logger.error(f"Original spider was: {scientific_name} from {spider.get('family', '')}")
                        logger.error(f"⚠️ This is one of the most venomous spiders - NEVER misidentify!")
                        # This is CRITICAL - retry
                        continue
                
                # ✅ VALIDATION: House spider (Parasteatoda) orb web check
                if "parasteatoda" in sci_name_lower or "house spider" in data.get("name", "").lower():
                    # Parasteatoda builds cobwebs, NOT orb webs
                    warning_signs = []
                    if "orb" in what_you_see or "circular" in what_you_see or "radial" in what_you_see:
                        warning_signs.append("House spider in orb web (Parasteatoda builds cobwebs, not orb webs)")
                    if "center of" in what_you_see and "web" in what_you_see:
                        warning_signs.append("House spider in center of structured web (likely orb-weaver instead)")
                    
                    if warning_signs:
                        logger.error(f"⚠️ WEB TYPE ERROR: House spider in orb web. Warnings: {warning_signs}")
                        logger.error(f"Original spider was: {scientific_name}")
                        logger.error(f"If orb web visible → should be Araneidae, NOT Parasteatoda")
                        # Retry
                        continue
                
                # ✅ VALIDATION: Orb web hard rule
                if "orb" in what_you_see or "circular web" in what_you_see or "radial web" in what_you_see:
                    # If orb web is visible, family MUST be Araneidae (or similar orb-weavers)
                    orb_web_families = ["Araneidae", "Nephilidae", "Uloboridae"]
                    if family_returned not in orb_web_families:
                        logger.error(f"🔒 ORB WEB RULE VIOLATION: Orb web visible but family is {family_returned}")
                        logger.error(f"Orb web present → MUST be {orb_web_families}, NOT {family_returned}")
                        logger.error(f"Original spider was: {scientific_name}")
                        # Retry with correct family
                        continue
                
                # ✅ VALIDATION: Trapdoor spider exclusion (CRITICAL)
                trapdoor_families = ["Halonoproctidae", "Ctenizidae", "Idiopidae", "Actinopodidae"]
                is_trapdoor = family_returned in trapdoor_families or "trapdoor" in data.get("name", "").lower()
                
                if is_trapdoor:
                    # Trapdoor spiders NEVER build webs - they live in burrows
                    warning_signs = []
                    if "web" in what_you_see:
                        warning_signs.append("Trapdoor spider in web (trapdoor spiders live in burrows, NOT webs)")
                    if "orb" in what_you_see or "circular" in what_you_see:
                        warning_signs.append("Trapdoor spider in orb web (IMPOSSIBLE - they're burrow dwellers)")
                    if behavior_returned == "web-based hunter":
                        warning_signs.append("Trapdoor spider as web-based hunter (impossible - they're ambush predators in burrows)")
                    if "burrow" not in what_you_see.lower() and "ground" not in what_you_see.lower():
                        warning_signs.append("Trapdoor spider without burrow/ground mentioned (burrow should be visible)")
                    
                    if warning_signs:
                        logger.error(f"🚫 TRAPDOOR SPIDER ERROR: Trapdoor spider in web. Warnings: {warning_signs}")
                        logger.error(f"Original spider was: {scientific_name} from {spider.get('family', '')}")
                        logger.error(f"⚠️ Trapdoor spiders = burrow dwellers, NOT web builders!")
                        logger.error(f"If spider in web → should be Araneidae or other web-builder, NOT trapdoor spider")
                        # This is critical - retry
                        continue
                
                # Record usage
                tokens_used = response.usage.total_tokens
                cost_per_1k = 0.15 / 1000
                estimated_cost = (tokens_used / 1000) * cost_per_1k
                self.budget_guard.record_llm_call(tokens_used, estimated_cost)
                
                # Add iNaturalist photo if available
                if photo_data:
                    data["photo_url"] = photo_data["url"]
                    data["photo_attribution"] = f"Photo by {photo_data['observer']} (iNaturalist, {photo_data['license']})"
                    data["photo_location"] = photo_data["location"]
                    data["photo_date"] = photo_data["observed_on"]
                    data["inaturalist_url"] = photo_data["inaturalist_url"]
                
                # Log interesting_fact to verify it's from Wikipedia
                interesting_fact = data.get("interesting_fact", "")
                if interesting_fact and len(interesting_fact) > 10:
                    logger.info(f"📝 Interesting fact generated: {interesting_fact[:100]}...")
                
                logger.info(f"✅ Successfully generated spider: {sci_name} (behavior: {data.get('behavior')}, confidence: {data.get('confidence_level')})")
                return data
                
            except Exception as e:
                logger.error(f"LLM error generating spider content (attempt {attempt + 1}/{max_attempts}): {e}")
                if attempt < max_attempts - 1:
                    continue
        
        # All attempts failed, use template
        logger.warning("All LLM attempts failed, using template")
        return self._generate_template(used_spiders)
    
    def _generate_template(self, used_spiders: List[str]) -> Dict:
        """Generate template spider content when LLM unavailable."""
        recent_used = set(used_spiders[-20:]) if used_spiders else set()
        
        # Use IDENTIFICATION_POOL only (safe species)
        available_spiders = [
            spider for spider in IDENTIFICATION_POOL 
            if spider["scientific_name"] not in recent_used
        ]
        
        if not available_spiders:
            available_spiders = IDENTIFICATION_POOL
        
        spider_data = random.choice(available_spiders)
        logger.info(f"Template mode: {spider_data['scientific_name']}")
        
        # Try to get iNaturalist photo
        photo_data = fetch_spider_photo_from_inaturalist(spider_data["scientific_name"])
        
        # Use BEHAVIOR_MAP (fixed mapping)
        behavior = BEHAVIOR_MAP.get(spider_data["family"], "web-based hunter")
        
        if behavior == "active hunter":
            what_you_see = "Spider on the ground or vegetation, no web visible"
        elif behavior == "ambush predator":
            what_you_see = "Spider waiting motionless in its territory"
        else:
            what_you_see = "Spider sitting in or near its web"
        
        result = {
            "calm_opening": f"If spiders make you uncomfortable, that's completely normal. This is a {spider_data['name'].lower()}, and it poses no threat to you.",
            "what_you_see": what_you_see,
            "name": spider_data["name"],
            "scientific_name": spider_data["scientific_name"],
            "family": spider_data["family"],
            "confidence_level": "confirmed",
            "countries": spider_data["countries"],
            "size": spider_data["size"],
            "color": "Natural coloring for camouflage",
            "behavior": behavior,
            "behavior_explanation": f"This spider uses {behavior} strategy. It waits for prey to come nearby and is not interested in pursuing humans.",
            "calm_explanation": f"This spider prefers to stay in its territory and avoid confrontation. It has no reason to approach people and will move away if disturbed. Like most spiders, it is defensive rather than aggressive.",
            "interesting_fact": "This spider helps control insect populations in its natural habitat, playing an important role in the ecosystem.",
            "gentle_takeaway": "This spider is simply living its life in its natural habitat. It is not interested in humans and poses no threat.",
            "lifespan": spider_data["lifespan"],
            "resource_link": f"https://en.wikipedia.org/wiki/{spider_data['scientific_name'].replace(' ', '_')}"
        }
        
        # Add iNaturalist photo if available
        if photo_data:
            result["photo_url"] = photo_data["url"]
            result["photo_attribution"] = f"Photo by {photo_data['observer']} (iNaturalist, {photo_data['license']})"
            result["photo_location"] = photo_data["location"]
            result["photo_date"] = photo_data["observed_on"]
            result["inaturalist_url"] = photo_data["inaturalist_url"]
        
        return result