"""Handler for posting to Telegram group/channel."""
import os
import asyncio
import logging
import httpx
from datetime import datetime, time
from typing import Optional
from telethon import TelegramClient
from telethon.tl.types import MessageMediaPhoto
from shared_services.channel_content import ChannelContentGenerator
from shared_services.image_service import ImageService
from storage.db import Database

logger = logging.getLogger(__name__)


class ChannelHandler:
    """Handler for automated group/channel posts."""
    
    def __init__(
        self,
        client: TelegramClient,
        db: Database,
        content_generator: ChannelContentGenerator,
        image_service: ImageService
    ):
        self.client = client
        self.db = db
        self.content_generator = content_generator
        self.image_service = image_service
        # Can be group username, group ID, or channel username
        self.target_username = os.getenv("CHANNEL_USERNAME", "")
        self.target_id = os.getenv("CHANNEL_ID", "")  # Alternative: group/channel ID
        self.morning_time = os.getenv("MORNING_POST_TIME", "09:00")
        self.evening_time = os.getenv("EVENING_POST_TIME", "20:00")
        self.enabled = os.getenv("CHANNEL_POSTS_ENABLED", "off").lower() == "on"
    
    async def start_scheduler(self):
        """Start scheduled posts."""
        if not self.enabled:
            logger.info("Group/channel posts disabled")
            return
        
        if not self.target_username and not self.target_id:
            logger.warning("CHANNEL_USERNAME or CHANNEL_ID not set, posts disabled")
            return
        
        # Try to resolve target to verify it exists
        try:
            if self.target_id:
                target_entity = await self.client.get_entity(int(self.target_id))
            elif self.target_username:
                target_entity = await self.client.get_entity(self.target_username)
            else:
                target_entity = None
            
            if target_entity:
                target_name = getattr(target_entity, 'title', getattr(target_entity, 'username', 'Unknown'))
                logger.info(f"✅ Target group/channel found: {target_name}")
            else:
                logger.warning("⚠️ Could not resolve target group/channel")
        except Exception as e:
            logger.warning(f"⚠️ Could not verify target: {e}")
        
        target = f"@{self.target_username}" if self.target_username else f"ID:{self.target_id}"
        logger.info(f"Starting scheduler for {target}")
        logger.info(f"Morning posts at {self.morning_time}, evening at {self.evening_time}")
        
        # Start background task
        asyncio.create_task(self._scheduler_loop())
    
    async def _scheduler_loop(self):
        """Main scheduler loop."""
        while True:
            try:
                now = datetime.now()
                current_time = now.strftime("%H:%M")
                
                # Check morning post
                if current_time == self.morning_time:
                    await self._post_morning_content()
                    # Wait 1 minute to avoid duplicate posts
                    await asyncio.sleep(60)
                
                # Check evening post
                elif current_time == self.evening_time:
                    await self._post_evening_content()
                    # Wait 1 minute to avoid duplicate posts
                    await asyncio.sleep(60)
                
                # Check every minute
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(60)
    
    async def _post_morning_content(self):
        """Post morning content (top 5 countries)."""
        try:
            logger.info("Generating morning post...")
            
            # Get used topics to avoid repetition
            used_topics = self.db.get_used_channel_topics(days=7)
            
            # Generate content
            content = self.content_generator.generate_morning_post(used_topics)
            
            if not content:
                logger.error("Failed to generate morning content")
                return
            
            # Format message
            message = self._format_morning_message(content)
            
            # Get image for first country
            image_url = None
            first_country_name = None
            first_country_capital = None
            if content.get("countries") and len(content["countries"]) > 0:
                first_country = content["countries"][0]
                first_country_name = first_country.get("name", "")
                first_country_capital = first_country.get("capital", "")
                image_url = await self.image_service.get_country_image(first_country_name)
            
            # Post to group/channel
            await self._post_to_channel(message, image_url, first_country_name, first_country_capital)
            
            # Save to database
            topic = content.get("title", "unknown")
            self.db.record_channel_post("morning", topic, content)
            
            logger.info(f"Morning post sent: {topic}")
            
        except Exception as e:
            logger.error(f"Error posting morning content: {e}")
    
    async def _post_evening_content(self):
        """Post evening content (top 3 travel destinations)."""
        try:
            logger.info("Generating evening post...")
            
            # Get used travel types to avoid repetition
            used_types = self.db.get_used_channel_types(days=7)
            
            # Generate content
            content = self.content_generator.generate_evening_post(used_types)
            
            if not content:
                logger.error("Failed to generate evening content")
                return
            
            # Format message
            message = self._format_evening_message(content)
            
            # Get image for first country
            image_url = None
            first_country_name = None
            first_country_capital = None
            if content.get("countries") and len(content["countries"]) > 0:
                first_country = content["countries"][0]
                first_country_name = first_country.get("name", "")
                first_country_capital = first_country.get("capital", "")
                image_url = await self.image_service.get_country_image(first_country_name)
            
            # Post to group/channel
            await self._post_to_channel(message, image_url, first_country_name, first_country_capital)
            
            # Save to database
            travel_type = content.get("travel_type", "unknown")
            self.db.record_channel_post("evening", travel_type, content)
            
            logger.info(f"Evening post sent: {travel_type}")
            
        except Exception as e:
            logger.error(f"Error posting evening content: {e}")
    
    def _format_morning_message(self, content: dict) -> str:
        """Format morning post message."""
        title = content.get("title", "Top Countries")
        countries = content.get("countries", [])
        
        message = f"🌍 {title}\n\n"
        
        for country in countries:
            rank = country.get("rank", 0)
            name = country.get("name", "Unknown")
            capital = country.get("capital", "")
            reason = country.get("reason", "")
            fact = country.get("fact", "")
            
            # Format country name with capital
            country_name = f"{name} ({capital})" if capital else name
            
            # Truncate to fit Telegram limits
            reason = reason[:120] + "..." if len(reason) > 120 else reason
            fact = fact[:80] + "..." if len(fact) > 80 else fact
            
            emoji = self._get_rank_emoji(rank)
            message += f"{emoji} **{rank}. {country_name}**\n"
            message += f"   {reason}\n"
            if fact:
                message += f"   💡 {fact}\n"
            
            # Signature dish
            signature_dish = country.get("signature_dish", "")
            dish_ingredients = country.get("dish_ingredients", "")
            if signature_dish:
                if dish_ingredients:
                    message += f"   🍽️ {signature_dish} ({dish_ingredients})\n"
                else:
                    message += f"   🍽️ {signature_dish}\n"
            
            message += "\n"
        
        message += "#Travel #Countries #Top5"
        
        return message
    
    def _format_evening_message(self, content: dict) -> str:
        """Format evening post message."""
        title = content.get("title", "Top Travel Destinations")
        countries = content.get("countries", [])
        travel_type = content.get("travel_type", "")
        
        type_emoji = self._get_travel_type_emoji(travel_type)
        message = f"{type_emoji} {title}\n\n"
        
        for country in countries:
            rank = country.get("rank", 0)
            name = country.get("name", "Unknown")
            capital = country.get("capital", "")
            activities = country.get("activities", [])
            best_time = country.get("best_time", "")
            unique_fact = country.get("unique_fact", "")
            
            # Format country name with capital
            country_name = f"{name} ({capital})" if capital else name
            
            emoji = self._get_rank_emoji(rank)
            message += f"{emoji} **{rank}. {country_name}**\n"
            
            # Format activities (each on new line)
            if activities:
                for activity in activities[:6]:  # Max 6 activities
                    message += f"   • {activity}\n"
            elif country.get("reason"):  # Fallback to old format
                reason = country.get("reason", "")
                reason = reason[:120] + "..." if len(reason) > 120 else reason
                message += f"   {reason}\n"
            
            # Best time (short format)
            if best_time:
                message += f"   📅 {best_time}\n"
            elif country.get("highlight"):  # Fallback
                highlight = country.get("highlight", "")[:50]
                message += f"   📅 {highlight}\n"
            
            # Unique fact
            if unique_fact:
                message += f"   💡 {unique_fact}\n"
            
            # Signature dish
            signature_dish = country.get("signature_dish", "")
            dish_ingredients = country.get("dish_ingredients", "")
            if signature_dish:
                if dish_ingredients:
                    message += f"   🍽️ {signature_dish} ({dish_ingredients})\n"
                else:
                    message += f"   🍽️ {signature_dish}\n"
            
            message += "\n"
        
        message += f"#Travel #{travel_type.title() if travel_type else 'Travel'} #Top3"
        
        return message
    
    def _get_rank_emoji(self, rank: int) -> str:
        """Get emoji for rank."""
        emojis = {
            1: "🥇",
            2: "🥈",
            3: "🥉",
            4: "4️⃣",
            5: "5️⃣"
        }
        return emojis.get(rank, f"{rank}.")
    
    def _get_travel_type_emoji(self, travel_type: str) -> str:
        """Get emoji for travel type."""
        emojis = {
            "winter": "❄️",
            "summer": "☀️",
            "hiking": "🥾",
            "beach": "🏖️",
            "culture": "🏛️",
            "adventure": "⛰️",
            "budget": "💰",
            "luxury": "💎"
        }
        return emojis.get(travel_type, "✈️")
    
    async def _post_to_channel(self, message: str, image_url: Optional[str] = None, country_name: Optional[str] = None, country_capital: Optional[str] = None):
        """Post message to group or channel."""
        try:
            # Determine target (group/channel)
            target = None
            if self.target_id:
                try:
                    target = int(self.target_id)
                except ValueError:
                    target = self.target_id
            elif self.target_username:
                # Try with @ prefix first, then without
                try:
                    target = self.target_username if self.target_username.startswith('@') else self.target_username
                except:
                    target = self.target_username
            
            if not target:
                logger.error("No target group/channel specified")
                return
            
            logger.info(f"Attempting to post to: {target}")
            
            # Create photo caption with country name and capital
            photo_caption = None
            if country_name and country_capital:
                photo_caption = f"{country_name} ({country_capital})"
            elif country_name:
                photo_caption = country_name
            
            # Telegram caption limit is 1024 characters
            # If message is too long, send image and text separately
            if image_url and len(message) > 1024:
                logger.warning(f"Message too long ({len(message)} chars), sending separately")
                # Download and send image with country name caption
                async with httpx.AsyncClient() as client:
                    response = await client.get(image_url, timeout=10.0)
                    response.raise_for_status()
                    
                    import tempfile
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                        tmp.write(response.content)
                        tmp_path = tmp.name
                    
                    # Send image with country name caption
                    await self.client.send_file(
                        target,
                        tmp_path,
                        caption=photo_caption
                    )
                    
                    import os
                    os.unlink(tmp_path)
                
                # Send text as separate message
                await self.client.send_message(
                    target,
                    message,
                    parse_mode='md'
                )
            elif image_url:
                # Download and send image with caption
                async with httpx.AsyncClient() as client:
                    response = await client.get(image_url, timeout=10.0)
                    response.raise_for_status()
                    
                    # Save temporarily
                    import tempfile
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                        tmp.write(response.content)
                        tmp_path = tmp.name
                    
                    # Combine photo caption with message if there's space
                    if photo_caption:
                        # Try to add photo caption to message if it fits
                        combined_caption = f"{photo_caption}\n\n{message}"
                        if len(combined_caption) <= 1024:
                            caption = combined_caption
                        else:
                            # Use just the message, send photo caption separately or skip
                            caption = message[:1024] if len(message) > 1024 else message
                    else:
                        # Truncate caption if needed (safety check)
                        caption = message[:1024] if len(message) > 1024 else message
                    
                    # Send to group/channel
                    await self.client.send_file(
                        target,
                        tmp_path,
                        caption=caption,
                        parse_mode='md'
                    )
                    
                    # Clean up
                    import os
                    os.unlink(tmp_path)
            else:
                # Send text only
                await self.client.send_message(
                    target,
                    message,
                    parse_mode='md'
                )
            
            target_str = f"@{self.target_username}" if self.target_username else f"ID:{self.target_id}"
            logger.info(f"Posted to {target_str}")
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error posting to group/channel: {error_msg}")
            
            # Check specific error types
            if "can't write" in error_msg.lower() or "write" in error_msg.lower():
                logger.error("❌ Permission denied: You don't have permission to post in this group/channel")
                logger.error("💡 Make sure you are admin with 'Post messages' permission")
            elif "not found" in error_msg.lower() or "chat" in error_msg.lower():
                logger.error("❌ Group/channel not found")
                logger.error("💡 Check CHANNEL_USERNAME or CHANNEL_ID in .env")
            
            # Fallback: try without image
            try:
                target = int(self.target_id) if self.target_id else self.target_username
                await self.client.send_message(
                    target,
                    message,
                    parse_mode='md'
                )
                logger.info("✅ Posted text-only successfully")
            except Exception as e2:
                logger.error(f"Error posting text-only: {e2}")
                raise  # Re-raise to show in control handler