"""List of all services added to group-posts-service.

This file contains a comprehensive list of all content generation services
that have been integrated into the group-posts-service.
"""

SERVICES = [
    {
        "name": "news_service",
        "file": "news_service.py",
        "class": "NewsService",
        "description": "Generates daily news summaries from Bloomberg and BBC, plus Ukraine war news from Ukrainian Truth",
        "schedule": "08:00 and 19:00",
        "command": "news",
        "categories": ["Bloomberg", "BBC", "Ukrainian Truth"]
    },
    {
        "name": "tech_content",
        "file": "content/tech_content.py",
        "class": "TechContentGenerator",
        "description": "Generates tech device posts with photos, specifications, and links",
        "schedule": "18:00",
        "command": "tech",
        "focus": "Engineering and electronic devices"
    },
    {
        "name": "person_content",
        "file": "content/person_content.py",
        "class": "PersonContentGenerator",
        "description": "Generates famous person posts (inventors, engineers, scientists) with photos and contributions",
        "schedule": "17:00",
        "command": "person",
        "distribution": "2/3 alive, 1/3 deceased; 1/3 electrical inventions"
    },
    {
        "name": "ukraine_news_service",
        "file": "ukraine_news_service.py",
        "class": "UkraineNewsService",
        "description": "Generates 3 main Ukraine news items (economy, politics, war) from last 12 hours",
        "schedule": "Configurable via UKRAINE_NEWS_POST_TIME",
        "command": "ukraine",
        "sources": ["Ukrainian Truth", "BBC Ukraine", "Ukrinform"]
    },
    {
        "name": "spider_content",
        "file": "content/spider_content.py",
        "class": "SpiderContentGenerator",
        "description": "Generates educational spider posts with cute/small spiders only (arachnophobia-friendly)",
        "schedule": "Configurable via SPIDER_POST_TIME",
        "command": "spider",
        "features": ["Only tiny/cute spiders", "Educational content", "Helpful facts", "Non-scary photos"]
    },
    {
        "name": "quote_content",
        "file": "content/quote_content.py",
        "class": "QuoteContentGenerator",
        "description": "Generates quote of the day posts with author photos and advice",
        "schedule": "Configurable via QUOTE_POST_TIME",
        "command": "quote",
        "note": "Previously known as 'phrase' service"
    },
    {
        "name": "africa_content",
        "file": "content/africa_content.py",
        "class": "AfricaContentGenerator",
        "description": "Generates Africa exploration posts with cities, places, activities, and facts",
        "schedule": "Configurable via AFRICA_POST_TIME",
        "command": "africa",
        "features": ["cities", "places (2 max)", "activities (2 max)", "cultural/wildlife/historical facts"]
    },
    {
        "name": "canary_wharf_content",
        "file": "content/london_content.py",
        "class": "LondonContentGenerator",
        "description": "Generates Canary Wharf (London) information posts with events and facts",
        "schedule": "Configurable via LONDON_POST_TIME",
        "command": "canary",
        "features": ["upcoming events (1-2)", "Canary Wharf facts", "Dog Island area", "photos from district"]
    },
    {
        "name": "uk_content",
        "file": "content/uk_content.py",
        "class": "UKContentGenerator",
        "description": "Generates UK information posts with cities, distance from London, travel time, and reasons to visit",
        "schedule": "Configurable via UK_POST_TIME",
        "command": "uk",
        "features": ["cities", "distance from London", "travel time", "reasons to visit", "UK facts"]
    },
    {
        "name": "job_content",
        "file": "content/job_content.py",
        "class": "JobContentGenerator",
        "description": "Generates job vacancy posts for London/Canary Wharf (DevOps, MLOps, SRE, System Engineer)",
        "schedule": "08:00 and 19:00",
        "command": "job",
        "requirements": [
            "City: London",
            "Company: Canary Wharf",
            "Job titles: DevOps, MLOps, SRE, System Engineer",
            "Company rating: > 4",
            "Not FAANG, bank, or AI sphere",
            "Salary: >= 60,000 pounds",
            "Not remote",
            "LinkedIn link required"
        ]
    },
    {
        "name": "weather_content",
        "file": "content/weather_content.py",
        "class": "WeatherContentGenerator",
        "description": "Generates weather forecast posts with temperatures in Celsius (day, night, average) for multiple cities",
        "schedule": "09:00",
        "command": "weather",
        "cities": ["London (UK)", "Bila Tserkva (Ukraine)", "Poltava (Ukraine)", "Bengaluru (India)", "Cyprus", "Poland"],
        "features": ["Temperature in Celsius", "Day/Night/Average temps", "Weather emojis (rain, cloudy, sunny, snow, etc.)", "OpenWeatherMap API or LLM fallback"]
    }
]

# Legacy services (from original implementation)
LEGACY_SERVICES = [
    {
        "name": "channel_content",
        "file": "content/channel_content.py",
        "description": "Generates morning and evening travel posts with top countries",
        "schedule": "Morning and evening (configurable)",
        "command": "travel",
        "features": ["top 3 countries", "drinks (morning)", "signature dishes (evening)", "activities", "facts"]
    }
]

def get_all_services():
    """Get all services (new + legacy)."""
    return SERVICES + LEGACY_SERVICES

def get_service_by_command(command: str):
    """Get service by command keyword."""
    all_services = get_all_services()
    for service in all_services:
        if service.get("command") == command:
            return service
    return None

def get_service_by_name(name: str):
    """Get service by name."""
    all_services = get_all_services()
    for service in all_services:
        if service.get("name") == name:
            return service
    return None
