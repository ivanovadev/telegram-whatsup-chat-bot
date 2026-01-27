"""Simple topic extraction from text."""
import re
from typing import List, Set


class TopicExtractor:
    """Extract topics/keywords from text."""
    
    # Common travel-related keywords
    TRAVEL_KEYWORDS = {
        'travel', 'trip', 'vacation', 'holiday', 'journey', 'destination',
        'country', 'city', 'beach', 'mountain', 'hotel', 'flight', 'booking',
        'подорож', 'поїздка', 'відпустка', 'країна', 'місто', 'пляж', 'гора'
    }
    
    # Common question/request keywords
    REQUEST_KEYWORDS = {
        'help', 'need', 'want', 'can', 'could', 'please', 'when', 'where',
        'допомога', 'потрібно', 'можеш', 'будь ласка', 'коли', 'де'
    }
    
    @staticmethod
    def extract_topics(text: str, max_topics: int = 5) -> List[str]:
        """Extract topics from text."""
        if not text:
            return []
        
        text_lower = text.lower()
        topics = set()
        
        # Extract travel keywords
        for keyword in TopicExtractor.TRAVEL_KEYWORDS:
            if keyword in text_lower:
                topics.add(keyword)
        
        # Extract request keywords
        for keyword in TopicExtractor.REQUEST_KEYWORDS:
            if keyword in text_lower:
                topics.add(keyword)
        
        # Extract country names (simple pattern - can be improved)
        country_patterns = [
            r'\b(ukraine|ukrainian|україна|українськ)\w*\b',
            r'\b(uk|united kingdom|britain|британія)\w*\b',
            r'\b(usa|america|united states|америка)\w*\b',
            r'\b(france|french|франція)\w*\b',
            r'\b(germany|german|німеччина)\w*\b',
            r'\b(spain|spanish|іспанія)\w*\b',
            r'\b(italy|italian|італія)\w*\b',
            r'\b(japan|japanese|японія)\w*\b',
        ]
        
        for pattern in country_patterns:
            matches = re.findall(pattern, text_lower)
            if matches:
                topics.add(matches[0])
        
        # Extract capitalized words (potential proper nouns/topics)
        capitalized_words = re.findall(r'\b[A-Z][a-z]+\b', text)
        for word in capitalized_words[:3]:  # Limit to avoid noise
            if len(word) > 3:  # Skip short words
                topics.add(word.lower())
        
        return list(topics)[:max_topics]
