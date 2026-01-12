"""Base content generator with anti-duplicate system."""
import json
import logging
import random
from pathlib import Path
from typing import Dict, Optional, List, Any
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseContentGenerator(ABC):
    """Base class for content generators with anti-duplicate system."""
    
    def __init__(self, 
                 budget_guard,
                 content_type: str,
                 history_file: Optional[str] = None,
                 template_pool: Optional[List[Dict[str, Any]]] = None):
        """Initialize content generator."""
        self.budget_guard = budget_guard
        self.content_type = content_type
        
        # Set default history file path
        if history_file is None:
            history_file = f"data/{content_type}_history.json"
        self.history_file = Path(history_file)
        
        # Template pool for fallback
        self.template_pool = template_pool or []
        
        logger.info(f"Initialized {content_type} generator with history: {self.history_file}")
    
    # History management
    
    def load_history(self) -> List[str]:
        """Load content history from file."""
        try:
            if self.history_file.exists():
                data = json.loads(self.history_file.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    logger.info(f"Loaded {len(data)} {self.content_type}s from history")
                    return data
                logger.warning(f"{self.content_type} history file contains non-list data: {type(data)}")
        except Exception as e:
            logger.warning(f"Failed to load {self.content_type} history: {e}")
        return []
    
    def save_history(self, items: List[str], keep_last: int = 200) -> None:
        """Save content history, keeping last N items."""
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
            logger.info(f"Saved {len(items_to_save)} {self.content_type}s to history")
        except Exception as e:
            logger.error(f"Failed to save {self.content_type} history: {e}")
    
    # Content generation
    
    def generate(self, used_items: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        """Generate content with automatic history management."""
        # Load history if not provided
        if used_items is None:
            used_items = self.load_history()
            logger.info(f"Loaded {len(used_items)} {self.content_type}s from history")
        
        # Generate content
        content = self._generate_with_retry(used_items)
        
        # Save to history if successful
        if content:
            item_id = self._extract_item_id(content)
            if item_id and item_id not in used_items[-10:]:
                used_items.append(item_id)
                self.save_history(used_items)
                logger.info(f"Added {item_id} to {self.content_type} history")
        
        return content
    
    def _generate_with_retry(self, used_items: List[str], max_attempts: int = 3) -> Optional[Dict[str, Any]]:
        """Generate content with retry logic to avoid duplicates."""
        for attempt in range(max_attempts):
            try:
                # Try to generate content (LLM or other method)
                content = self._generate_content(used_items)
                
                if not content:
                    logger.warning(f"Empty content on attempt {attempt + 1}/{max_attempts}")
                    continue
                
                # Check for duplicate
                item_id = self._extract_item_id(content)
                if item_id and item_id in set(used_items[-30:]):
                    logger.info(f"Repeated {self.content_type} {item_id}, retrying (attempt {attempt + 1}/{max_attempts})")
                    continue  # Try again
                
                logger.info(f"Successfully generated {self.content_type}: {item_id}")
                return content
                
            except Exception as e:
                logger.error(f"Error generating {self.content_type} (attempt {attempt + 1}/{max_attempts}): {e}")
                if attempt < max_attempts - 1:
                    continue
        
        # All attempts failed, use template
        logger.warning(f"All {max_attempts} attempts failed, using template for {self.content_type}")
        return self._generate_from_template(used_items)
    
    def _generate_from_template(self, used_items: List[str]) -> Optional[Dict[str, Any]]:
        """Generate content from template pool."""
        if not self.template_pool:
            logger.error(f"No template pool available for {self.content_type}")
            return None
        
        # Get recent used items to avoid
        recent_used = set(used_items[-20:]) if used_items else set()
        
        # Filter available items (not recently used)
        available_items = [
            item for item in self.template_pool 
            if self._extract_item_id(item) not in recent_used
        ]
        
        # If all items were recently used, just use the full pool
        if not available_items:
            available_items = self.template_pool
        
        # Select random item
        selected = random.choice(available_items)
        item_id = self._extract_item_id(selected)
        
        logger.info(f"Template mode: selected {self.content_type} {item_id}")
        return selected
    
    # Abstract methods (implement in subclass)
    
    @abstractmethod
    def _generate_content(self, used_items: List[str]) -> Optional[Dict[str, Any]]:
        """Generate content (implement in subclass)."""
        pass
    
    @abstractmethod
    def _extract_item_id(self, content: Dict[str, Any]) -> str:
        """Extract unique identifier from content (implement in subclass)."""
        pass
    
    # Optional methods (override if needed)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about history and usage.
        
        Returns:
            Dictionary with statistics
        """
        history = self.load_history()
        return {
            'content_type': self.content_type,
            'history_size': len(history),
            'template_pool_size': len(self.template_pool),
            'history_file': str(self.history_file),
            'recent_items': history[-10:] if history else []
        }
    
    def clear_history(self) -> None:
        """Clear content history (use with caution!)."""
        try:
            if self.history_file.exists():
                self.history_file.unlink()
                logger.warning(f"Cleared {self.content_type} history: {self.history_file}")
        except Exception as e:
            logger.error(f"Failed to clear {self.content_type} history: {e}")
