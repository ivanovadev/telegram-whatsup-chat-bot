"""Generate content for tech device posts with anti-duplicate system."""
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
TECH_TEMPLATE_POOL = [
    {"device_name": "Arduino Uno", "manufacturer": "Arduino", "country": "Italy", "category": "microcontrollers", "type": "unique", "year_created": "2010", "key_features": ["ATmega328P microcontroller", "14 digital I/O pins", "6 analog inputs", "Open-source hardware"], "what_it_does": "Microcontroller board for building digital devices and interactive objects. Used in robotics, automation, and prototyping.", "resource_link": "https://en.wikipedia.org/wiki/Arduino"},
    {"device_name": "Raspberry Pi 4", "manufacturer": "Raspberry Pi Foundation", "country": "UK", "category": "embedded systems", "type": "top-notch", "year_created": "2019", "key_features": ["Quad-core ARM processor", "Up to 8GB RAM", "Dual 4K display support", "Low-cost computing"], "what_it_does": "Single-board computer for education and embedded projects. Used in IoT, robotics, and computer science education.", "resource_link": "https://en.wikipedia.org/wiki/Raspberry_Pi"},
    {"device_name": "ESP32", "manufacturer": "Espressif Systems", "country": "China", "category": "microcontrollers", "type": "unique", "year_created": "2016", "key_features": ["Wi-Fi and Bluetooth built-in", "Dual-core processor", "Low power consumption", "Affordable price"], "what_it_does": "Microcontroller with integrated Wi-Fi and Bluetooth for IoT applications. Used in smart home devices, wearables, and wireless sensors.", "resource_link": "https://en.wikipedia.org/wiki/ESP32"},
    {"device_name": "NVIDIA A100", "manufacturer": "NVIDIA", "country": "USA", "category": "semiconductor devices", "type": "top-notch", "year_created": "2020", "key_features": ["7nm process technology", "Multi-instance GPU support", "Tensor cores for AI", "600GB/s memory bandwidth"], "what_it_does": "Data center GPU designed for AI training and high-performance computing. Used in machine learning research and scientific simulations.", "resource_link": "https://www.nvidia.com/en-us/data-center/a100/"},
    {"device_name": "STM32", "manufacturer": "STMicroelectronics", "country": "Switzerland", "category": "microcontrollers", "type": "top-notch", "year_created": "2007", "key_features": ["ARM Cortex-M core", "Wide range of models", "Low power modes", "Rich peripheral set"], "what_it_does": "Family of 32-bit microcontrollers for embedded applications. Used in industrial control, automotive systems, and consumer electronics.", "resource_link": "https://en.wikipedia.org/wiki/STM32"},
    {"device_name": "DHT22", "manufacturer": "Aosong Electronics", "country": "China", "category": "sensors and transducers", "type": "unique", "year_created": "2010", "key_features": ["Measures temperature and humidity", "Digital output", "Low cost", "Easy to use"], "what_it_does": "Digital sensor for measuring temperature and humidity. Used in weather stations, HVAC systems, and IoT projects.", "resource_link": "https://learn.adafruit.com/dht"},
    {"device_name": "LM317", "manufacturer": "Texas Instruments", "country": "USA", "category": "power electronics", "type": "top-notch", "year_created": "1976", "key_features": ["Adjustable voltage regulator", "1.2V to 37V output", "Current limiting", "Thermal protection"], "what_it_does": "Voltage regulator IC for power supply circuits. Used in electronics projects, battery chargers, and power management.", "resource_link": "https://en.wikipedia.org/wiki/LM317"},
    {"device_name": "HC-SR04", "manufacturer": "Generic", "country": "China", "category": "sensors and transducers", "type": "unique", "year_created": "2010", "key_features": ["Ultrasonic distance measurement", "2cm to 400cm range", "Low cost", "Simple interface"], "what_it_does": "Ultrasonic sensor for measuring distance using sound waves. Used in robotics, obstacle detection, and parking sensors.", "resource_link": "https://www.sparkfun.com/products/15569"},
]


class TechContentGenerator(BaseContentGenerator):
    """Generate tech device content with anti-duplicate system."""
    
    DEVICE_CATEGORIES = [
        "electronic engineering devices", "semiconductor devices", "microcontrollers",
        "sensors and transducers", "power electronics", "communication devices",
        "embedded systems", "electronic test equipment", "robotics and automation",
        "industrial electronics", "electronic components", "circuit boards and PCBs"
    ]
    
    COUNTRIES = [
        "USA", "China", "Japan", "South Korea", "Germany", "Sweden",
        "Finland", "Netherlands", "Switzerland", "UK", "France", "Italy",
        "Taiwan", "Singapore", "Israel", "Canada", "Australia", "India"
    ]
    
    def __init__(self, budget_guard):
        """Initialize tech content generator with anti-duplicate system."""
        super().__init__(
            budget_guard=budget_guard,
            content_type="tech",
            history_file="data/tech_history.json",
            template_pool=TECH_TEMPLATE_POOL
        )
        
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-5.2")
        self.llm_enabled = os.getenv("LLM_ENABLED", "off").lower() == "on"
        
        if self.llm_enabled and self.openai_api_key:
            self.client = OpenAI(api_key=self.openai_api_key)
        else:
            self.client = None
            logger.warning("LLM disabled for tech content")
    
    def _generate_content(self, used_items: List[str]) -> Optional[Dict]:
        """Generate tech device content using LLM."""
        if not self.client or not self.llm_enabled:
            return None
        
        try:
            current_date = datetime.now().strftime("%Y-%m-%d")
            
            device_type = random.choice(self.DEVICE_CATEGORIES)
            country = random.choice(self.COUNTRIES)
            is_unique = random.random() < 0.7
            
            used_devices_context = ""
            if used_items:
                recent_items = used_items[-10:]
                used_devices_context = f"\n\nIMPORTANT: Avoid devices that were recently covered: {', '.join(recent_items)}\nChoose a DIFFERENT device and manufacturer."
            
            type_prompt = "INNOVATIVE engineering/electronic device" if is_unique else "TOP-NOTCH or FLAGSHIP engineering/electronic device"
            
            prompt = f"""Generate information about a {type_prompt} from {country} in the {device_type} category.

Requirements:
1. Device should be related to ENGINEERING and ELECTRONICS (not consumer gadgets)
2. Should be an actual electronic/engineering device (semiconductors, sensors, microcontrollers, etc.)
3. Include: device name, manufacturer, year of creation/release, key features (3-5), what it does (1-2 sentences MAXIMUM, no marketing language), resource link
4. NO marketing language - avoid words like "revolutionizing", "critical", "game-changing". Use concrete facts: what it does and where it's used.

Format as JSON:
{{
  "device_name": "Device Name",
  "manufacturer": "Company Name",
  "country": "{country}",
  "category": "{device_type}",
  "type": "{"unique" if is_unique else "top-notch"}",
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
- Current date: {current_date}{used_devices_context}

Return ONLY valid JSON, no additional text."""

            response = self.client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {"role": "system", "content": "You are a tech journalist. Generate information about engineering devices from different countries. Always return valid JSON only, no additional text."},
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
                logger.error("Empty response from LLM for tech device")
                return None
            
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
                    return None
            
            # Record usage
            tokens_used = response.usage.total_tokens
            cost_per_1k = 0.15 / 1000
            estimated_cost = (tokens_used / 1000) * cost_per_1k
            self.budget_guard.record_llm_call(tokens_used, estimated_cost)
            
            return data
            
        except Exception as e:
            logger.error(f"LLM error generating tech device: {e}")
            return None
    
    def _extract_item_id(self, content: Dict) -> str:
        """Extract unique identifier from tech device content."""
        device = content.get("device_name", "Unknown")
        manufacturer = content.get("manufacturer", "")
        return f"{device} ({manufacturer})" if manufacturer else device
    
    # Legacy compatibility
    def generate_tech_post(self, used_devices: Optional[List[str]] = None, used_countries: Optional[List[str]] = None) -> Optional[Dict]:
        """Generate tech post (legacy method for backward compatibility)."""
        return self.generate(used_items=used_devices)
