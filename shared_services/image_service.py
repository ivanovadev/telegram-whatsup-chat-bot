"""Service for fetching country images."""
import os
import httpx
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ImageService:
    """Fetch images for countries."""
    
    def __init__(self):
        """Initialize image service."""
        self.unsplash_access_key = os.getenv("UNSPLASH_ACCESS_KEY", "")
        self.use_unsplash = bool(self.unsplash_access_key)
    
    async def get_country_image(self, country_name: str) -> Optional[str]:
        """
        Get image URL for a country.
        Returns URL or None if unavailable.
        """
        if self.use_unsplash:
            return await self._get_from_unsplash(country_name)
        else:
            # Fallback to a placeholder or public API
            return self._get_placeholder_url(country_name)
    
    async def _get_from_unsplash(self, country_name: str) -> Optional[str]:
        """Get image from Unsplash API."""
        if not self.unsplash_access_key:
            logger.debug("Unsplash API key not set, skipping image fetch")
            return None
            
        try:
            async with httpx.AsyncClient() as client:
                url = "https://api.unsplash.com/search/photos"
                params = {
                    "query": f"{country_name} landscape travel",
                    "per_page": 1,
                    "orientation": "landscape"
                }
                headers = {
                    "Authorization": f"Client-ID {self.unsplash_access_key}"
                }
                
                response = await client.get(url, params=params, headers=headers, timeout=10.0)
                response.raise_for_status()
                data = response.json()
                
                if data.get("results") and len(data["results"]) > 0:
                    # Return regular size (not raw to save bandwidth)
                    return data["results"][0]["urls"]["regular"]
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                logger.warning("Unsplash API key invalid or expired. Posts will work without images.")
            else:
                logger.warning(f"Unsplash API error: {e}. Posts will work without images.")
        except Exception as e:
            logger.warning(f"Error fetching from Unsplash: {e}. Posts will work without images.")
        
        return None
    
    def _get_placeholder_url(self, country_name: str) -> Optional[str]:
        """Get placeholder image URL."""
        # Using a free service like Picsum or similar
        # For now, return None - images will be optional
        return None
