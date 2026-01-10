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
        if not country_name:
            logger.warning("⚠️ No country name provided for image")
            return None
            
        if self.use_unsplash:
            logger.info(f"🔍 Using Unsplash to find image for: {country_name}")
            return await self._get_from_unsplash(country_name)
        else:
            logger.warning("⚠️ Unsplash API key not set, cannot fetch images")
            # Fallback to a placeholder or public API
            return self._get_placeholder_url(country_name)
    
    async def _get_from_unsplash(self, country_name: str) -> Optional[str]:
        """Get image from Unsplash API. Prefers colorful images over black and white."""
        if not self.unsplash_access_key:
            logger.debug("Unsplash API key not set, skipping image fetch")
            return None
            
        try:
            async with httpx.AsyncClient() as client:
                url = "https://api.unsplash.com/search/photos"
                # Add keywords to prefer colorful images
                params = {
                    "query": f"{country_name} landscape travel colorful vibrant",
                    "per_page": 10,  # Get more results to filter out B&W
                    "orientation": "landscape",
                    "order_by": "relevance"  # Get most relevant results
                }
                headers = {
                    "Authorization": f"Client-ID {self.unsplash_access_key}"
                }
                
                response = await client.get(url, params=params, headers=headers, timeout=10.0)
                response.raise_for_status()
                data = response.json()
                
                if data.get("results") and len(data["results"]) > 0:
                    # Filter out black and white images by checking color saturation
                    # Unsplash API doesn't have a direct B&W filter, so we check multiple results
                    for photo in data["results"]:
                        # Check if photo has color information
                        # Unsplash photos with color usually have color field
                        photo_color = photo.get("color", "")
                        
                        # Skip if it's likely black and white (very dark or very light colors)
                        if photo_color:
                            # Convert hex to RGB to check saturation
                            hex_color = photo_color.lstrip('#')
                            if len(hex_color) == 6:
                                r = int(hex_color[0:2], 16)
                                g = int(hex_color[2:4], 16)
                                b = int(hex_color[4:6], 16)
                                
                                # Calculate brightness
                                brightness = (r + g + b) / 3
                                
                                # Calculate saturation (simplified)
                                max_val = max(r, g, b)
                                min_val = min(r, g, b)
                                saturation = (max_val - min_val) / max_val if max_val > 0 else 0
                                
                                # Skip if it's likely B&W (low saturation and extreme brightness)
                                if saturation < 0.1 and (brightness < 30 or brightness > 225):
                                    continue
                        
                        # Also check description/tags for B&W keywords
                        description = photo.get("description", "").lower() + " " + photo.get("alt_description", "").lower()
                        if any(word in description for word in ["black and white", "b&w", "monochrome", "grayscale", "black white"]):
                            continue
                        
                        # Found a colorful image
                        image_url = photo["urls"]["regular"]
                        logger.info(f"✅ Found colorful image for {country_name}: {image_url[:100]}...")
                        return image_url
                    
                    # If all images seem B&W, return the first one anyway
                    logger.warning(f"⚠️ All images for {country_name} appear to be B&W, using first result")
                    image_url = data["results"][0]["urls"]["regular"]
                    logger.info(f"📸 Using first image: {image_url[:100]}...")
                    return image_url
                
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
