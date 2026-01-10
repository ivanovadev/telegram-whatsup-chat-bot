"""Handler for posting to Telegram group/channel."""
import os
import asyncio
import logging
import httpx
from datetime import datetime, time
from typing import Optional
from telethon import TelegramClient, events
from telethon.tl.types import MessageMediaPhoto
from services.channel_content import ChannelContentGenerator
from services.image_service import ImageService
from storage.db import Database

logger = logging.getLogger(__name__)


class ChannelHandler:
    """Handler for automated group/channel posts."""
    
    def __init__(
        self,
        client: TelegramClient,
        db: Database,
        content_generator: ChannelContentGenerator,
        image_service: ImageService,
        news_service=None
    ):
        self.client = client
        self.db = db
        self.content_generator = content_generator
        self.image_service = image_service
        self.news_service = news_service
        # Can be group username, group ID, or channel username
        self.target_username = os.getenv("GROUP_USERNAME", os.getenv("CHANNEL_USERNAME", ""))
        self.target_id = os.getenv("GROUP_ID", os.getenv("CHANNEL_ID", ""))  # Alternative: group ID
        self.morning_time = os.getenv("MORNING_POST_TIME", "09:00")
        self.evening_time = os.getenv("EVENING_POST_TIME", "20:00")
        self.news_morning_time = os.getenv("NEWS_MORNING_TIME", "08:00")
        self.news_evening_time = os.getenv("NEWS_EVENING_TIME", "19:00")
        self.enabled = os.getenv("GROUP_POSTS_ENABLED", "off").lower() == "on"
        self.control_chat_id = os.getenv("CONTROL_CHAT_ID", "me")
        
        # Commands will be registered after client is started
        self._commands_registered = False
        
        logger.info(f"🎛️ Control chat ID: {self.control_chat_id}")
    
    async def start_scheduler(self):
        """Start scheduled posts."""
        if not self.enabled:
            logger.info("Group/channel posts disabled")
            return
        
        if not self.target_username and not self.target_id:
            logger.warning("GROUP_USERNAME or GROUP_ID not set, posts disabled")
            return
        
        # Try to resolve target to verify it exists and check permissions
        try:
            target_entity = None
            if self.target_id:
                try:
                    target_entity = await self.client.get_entity(int(self.target_id))
                except ValueError:
                    logger.warning(f"⚠️ Invalid GROUP_ID format: {self.target_id}")
            elif self.target_username:
                # Try with @ prefix first, then without
                try:
                    username = self.target_username if self.target_username.startswith('@') else self.target_username
                    target_entity = await self.client.get_entity(username)
                except Exception as e:
                    logger.warning(f"⚠️ Could not find group with username '{self.target_username}': {e}")
                    logger.info("💡 Try using GROUP_ID instead. Forward a message from the group and use 'get group id' command")
            
            if target_entity:
                target_name = getattr(target_entity, 'title', getattr(target_entity, 'username', 'Unknown'))
                logger.info(f"✅ Target group/channel found: {target_name}")
                
                # Check if we can send messages (basic permission check)
                try:
                    # Try to get chat info to check permissions
                    from telethon.tl.functions.channels import GetFullChannelRequest
                    from telethon.tl.functions.messages import GetFullChatRequest
                    
                    if hasattr(target_entity, 'broadcast') or hasattr(target_entity, 'megagroup'):
                        # It's a channel or supergroup
                        full_chat = await self.client(GetFullChannelRequest(target_entity))
                        if hasattr(full_chat, 'full_chat'):
                            logger.info("✅ Channel/supergroup access verified")
                    else:
                        # Regular group
                        full_chat = await self.client(GetFullChatRequest(target_entity.id))
                        if hasattr(full_chat, 'full_chat'):
                            logger.info("✅ Group access verified")
                except Exception as perm_e:
                    logger.warning(f"⚠️ Could not verify permissions: {perm_e}")
                    logger.info("💡 Make sure you are admin with 'Post messages' permission")
            else:
                logger.warning("⚠️ Could not resolve target group/channel")
                logger.info("💡 Check GROUP_USERNAME or GROUP_ID in .env file")
        except Exception as e:
            logger.warning(f"⚠️ Could not verify target: {e}")
            logger.info("💡 Make sure GROUP_USERNAME or GROUP_ID is correct in .env")
        
        target = f"@{self.target_username}" if self.target_username else f"ID:{self.target_id}"
        logger.info(f"Starting scheduler for {target}")
        logger.info(f"Morning posts at {self.morning_time}, evening at {self.evening_time}")
        
        # Check if we missed morning post today
        await self._check_missed_posts()
        
        # Register manual trigger commands (after client is started)
        if not self._commands_registered:
            self._register_commands()
            self._commands_registered = True
        
        # Start background task
        asyncio.create_task(self._scheduler_loop())
    
    def _register_commands(self):
        """Register manual trigger commands for testing."""
        logger.info(f"📝 Registering manual commands for control chat: {self.control_chat_id}")
        
        @self.client.on(events.NewMessage(chats=self.control_chat_id))
        async def handle_manual_trigger(event):
            try:
                # Debug logging
                text = (event.message.message or "").strip()
                me = await self.client.get_me()
                logger.info(f"📨 Received message: '{text}' (out={event.message.out}, sender_id={event.sender_id}, me_id={me.id}, reply_to={bool(event.message.reply_to)})")
                
                # In Saved Messages, all messages have out=True and sender_id == me_id (it's a userbot)
                # So we can't use sender_id to distinguish. Instead:
                # 1. Ignore if it's a reply to bot's message (user responding to bot)
                # 2. Process all other messages that match commands
                
                if event.message.reply_to:
                    try:
                        replied_msg = await event.get_reply_message()
                        if replied_msg and replied_msg.out:
                            # User is replying to bot's message - this is not a command
                            logger.debug(f"Ignoring reply to bot's message: '{text}'")
                            return
                    except Exception as e:
                        logger.debug(f"Could not get replied message: {e}")
                
                # If message is empty or just whitespace, ignore
                if not text:
                    return
                
                # Process all non-reply messages that match commands
                # In Saved Messages, user commands are usually not replies
                text_lower = text.lower()
                logger.info(f"📨 Processing message for commands: '{text}'")
                
                if text_lower == "travel":
                    logger.info("🚀 Manual travel command triggered")
                    await event.reply("🚀 Generating evening travel post...")
                    try:
                        await self._post_evening_content()
                        await event.reply("✅ Evening travel post sent!")
                        logger.info("✅ Manual evening post completed successfully")
                    except Exception as e:
                        error_msg = str(e)
                        logger.error(f"❌ Manual travel post error: {e}", exc_info=True)
                        await event.reply(f"❌ Error: {error_msg}\n\n💡 Check:\n- Is GROUP_USERNAME or GROUP_ID set?\n- Are you admin in the group?\n- Check logs for details")
                
                elif text_lower == "travel morning":
                    logger.info("🌍 Manual travel morning command triggered")
                    await event.reply("🌍 Generating morning post...")
                    try:
                        await self._post_morning_content()
                        await event.reply("✅ Morning post sent!")
                        logger.info("✅ Manual morning post completed successfully")
                    except Exception as e:
                        error_msg = str(e)
                        logger.error(f"❌ Manual morning post error: {e}", exc_info=True)
                        await event.reply(f"❌ Error: {error_msg}\n\n💡 Check:\n- Is GROUP_USERNAME or GROUP_ID set?\n- Are you admin in the group?\n- Check logs for details")
                
                elif text_lower == "news":
                    logger.info("📰 Manual news command triggered")
                    await event.reply("📰 Generating news summary...")
                    try:
                        await self._post_news_content()
                        await event.reply("✅ News post sent!")
                        logger.info("✅ Manual news post completed successfully")
                    except Exception as e:
                        error_msg = str(e)
                        logger.error(f"❌ Manual news post error: {e}", exc_info=True)
                        await event.reply(f"❌ Error: {error_msg}\n\n💡 Check:\n- Is GROUP_USERNAME or GROUP_ID set?\n- Are you admin in the group?\n- Check logs for details")
                else:
                    logger.debug(f"Message '{text}' is not a recognized command")
            except Exception as e:
                logger.error(f"Error in handle_manual_trigger: {e}", exc_info=True)
    
    async def _check_missed_posts(self):
        """Check if we missed any posts today and post them if needed."""
        try:
            from datetime import date
            now = datetime.now()
            today = date.today()
            current_time_str = now.strftime("%H:%M")
            
            logger.info(f"🔍 Checking for missed posts... Current time: {current_time_str}")
            
            # Check if morning post was sent today
            morning_posts_today = self.db.get_channel_posts_today("morning")
            logger.info(f"📊 Morning posts today: {len(morning_posts_today) if morning_posts_today else 0}")
            
            if not morning_posts_today:
                # Check if morning time has passed
                morning_hour, morning_min = map(int, self.morning_time.split(":"))
                current_hour = now.hour
                current_min = now.minute
                
                logger.info(f"⏰ Morning time: {self.morning_time}, Current: {current_hour:02d}:{current_min:02d}")
                
                # If current time is after morning time, we missed it
                if (current_hour > morning_hour) or (current_hour == morning_hour and current_min >= morning_min):
                    logger.info("⚠️ Morning post was missed today, posting now...")
                    await self._post_morning_content()
                    await asyncio.sleep(5)  # Small delay before checking evening
                else:
                    logger.info(f"✅ Morning post time hasn't passed yet ({self.morning_time})")
            else:
                logger.info("✅ Morning post already sent today")
            
            # Check if evening post was sent today
            evening_posts_today = self.db.get_channel_posts_today("evening")
            logger.info(f"📊 Evening posts today: {len(evening_posts_today) if evening_posts_today else 0}")
            
            if not evening_posts_today:
                # Check if evening time has passed
                evening_hour, evening_min = map(int, self.evening_time.split(":"))
                current_hour = now.hour
                current_min = now.minute
                
                logger.info(f"⏰ Evening time: {self.evening_time}, Current: {current_hour:02d}:{current_min:02d}")
                
                # If current time is after evening time, we missed it
                if (current_hour > evening_hour) or (current_hour == evening_hour and current_min >= evening_min):
                    logger.info("⚠️ Evening post was missed today, posting now...")
                    await self._post_evening_content()
                else:
                    logger.info(f"✅ Evening post time hasn't passed yet ({self.evening_time})")
            else:
                logger.info("✅ Evening post already sent today")
                
        except Exception as e:
            logger.error(f"❌ Error checking missed posts: {e}", exc_info=True)
    
    async def _scheduler_loop(self):
        """Main scheduler loop."""
        last_morning_post_date = None
        last_evening_post_date = None
        
        logger.info("🔄 Scheduler loop started")
        
        while True:
            try:
                now = datetime.now()
                current_time = now.strftime("%H:%M")
                today = now.date()
                
                # Check morning post
                if current_time == self.morning_time:
                    # Only post if we haven't posted today
                    if last_morning_post_date != today:
                        logger.info(f"⏰ Morning post time reached: {self.morning_time}")
                        await self._post_morning_content()
                        last_morning_post_date = today
                        # Wait 1 minute to avoid duplicate posts
                        await asyncio.sleep(60)
                    else:
                        logger.debug(f"⏰ Morning post already sent today at {self.morning_time}")
                
                # Check evening post
                elif current_time == self.evening_time:
                    # Only post if we haven't posted today
                    if last_evening_post_date != today:
                        logger.info(f"⏰ Evening post time reached: {self.evening_time}")
                        await self._post_evening_content()
                        last_evening_post_date = today
                        # Wait 1 minute to avoid duplicate posts
                        await asyncio.sleep(60)
                    else:
                        logger.debug(f"⏰ Evening post already sent today at {self.evening_time}")
                
                # Check news posts (if news service is available)
                if self.news_service:
                    # Morning news at 8:00
                    if current_time == self.news_morning_time:
                        if not self.db.has_posted_news_today():
                            logger.info(f"📰 Morning news time reached: {self.news_morning_time}")
                            await self._post_news_content()
                            await asyncio.sleep(60)
                    
                    # Evening news at 19:00
                    elif current_time == self.news_evening_time:
                        if not self.db.has_posted_news_today():
                            logger.info(f"📰 Evening news time reached: {self.news_evening_time}")
                            await self._post_news_content()
                            await asyncio.sleep(60)
                
                # Log every 5 minutes for debugging
                if now.minute % 5 == 0 and now.second < 5:
                    waiting_times = f"{self.morning_time} / {self.evening_time}"
                    if self.news_service:
                        waiting_times += f" / News: {self.news_morning_time} / {self.news_evening_time}"
                    logger.debug(f"🕐 Scheduler running... Current time: {current_time}, Waiting for: {waiting_times}")
                
                # Check every minute
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"❌ Error in scheduler loop: {e}", exc_info=True)
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
            
            # Log countries count for debugging
            countries = content.get("countries", [])
            logger.info(f"📊 Generated {len(countries)} countries for morning post")
            for i, c in enumerate(countries, 1):
                logger.debug(f"  {i}. {c.get('name', 'Unknown')}")
            
            # Format message
            message = self._format_morning_message(content)
            
            # Get image for a country that hasn't been used recently
            image_url = None
            first_country_name = None
            first_country_capital = None
            if content.get("countries") and len(content["countries"]) > 0:
                # Get countries used TODAY (to avoid same day repetition)
                today_image_countries = self.db.get_today_image_countries()
                logger.info(f"📸 Countries used for images today: {today_image_countries}")
                
                # Get recently used countries for images (last 30 days)
                recent_image_countries = self.db.get_recent_image_countries(days=30)
                
                # Try to find a country that hasn't been used TODAY
                selected_country = None
                for country in content["countries"]:
                    country_name = country.get("name", "")
                    if country_name and country_name not in today_image_countries:
                        selected_country = country
                        logger.info(f"✅ Selected country not used today: {country_name}")
                        break
                
                # If all countries were used today, try to find one not used in last 7 days
                if not selected_country:
                    logger.warning("⚠️ All countries in post were used today, checking last 7 days...")
                    recent_7_days = self.db.get_recent_image_countries(days=7)
                    for country in content["countries"]:
                        country_name = country.get("name", "")
                        if country_name and country_name not in recent_7_days:
                            selected_country = country
                            logger.info(f"✅ Selected country not used in last 7 days: {country_name}")
                            break
                
                # If still no country found, use the first one anyway
                if not selected_country:
                    selected_country = content["countries"][0]
                    logger.warning(f"⚠️ Using first country (may repeat): {selected_country.get('name', 'Unknown')}")
                
                first_country_name = selected_country.get("name", "")
                first_country_capital = selected_country.get("capital", "")
                
                logger.info(f"🖼️ Fetching image for country: {first_country_name}")
                image_url = await self.image_service.get_country_image(first_country_name)
                
                if image_url:
                    logger.info(f"✅ Image URL received: {image_url[:100]}...")
                else:
                    logger.warning(f"⚠️ No image URL received for {first_country_name}")
                
                # Record that this country was used for an image
                if first_country_name:
                    self.db.record_image_country(first_country_name)
                    logger.info(f"📝 Recorded image usage for: {first_country_name}")
            
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
            
            # Get image for a country that hasn't been used recently
            image_url = None
            first_country_name = None
            first_country_capital = None
            if content.get("countries") and len(content["countries"]) > 0:
                # Get countries used TODAY (to avoid same day repetition)
                today_image_countries = self.db.get_today_image_countries()
                logger.info(f"📸 Countries used for images today: {today_image_countries}")
                
                # Get recently used countries for images (last 30 days)
                recent_image_countries = self.db.get_recent_image_countries(days=30)
                
                # Try to find a country that hasn't been used TODAY
                selected_country = None
                for country in content["countries"]:
                    country_name = country.get("name", "")
                    if country_name and country_name not in today_image_countries:
                        selected_country = country
                        logger.info(f"✅ Selected country not used today: {country_name}")
                        break
                
                # If all countries were used today, try to find one not used in last 7 days
                if not selected_country:
                    logger.warning("⚠️ All countries in post were used today, checking last 7 days...")
                    recent_7_days = self.db.get_recent_image_countries(days=7)
                    for country in content["countries"]:
                        country_name = country.get("name", "")
                        if country_name and country_name not in recent_7_days:
                            selected_country = country
                            logger.info(f"✅ Selected country not used in last 7 days: {country_name}")
                            break
                
                # If still no country found, use the first one anyway
                if not selected_country:
                    selected_country = content["countries"][0]
                    logger.warning(f"⚠️ Using first country (may repeat): {selected_country.get('name', 'Unknown')}")
                
                first_country_name = selected_country.get("name", "")
                first_country_capital = selected_country.get("capital", "")
                
                logger.info(f"🖼️ Fetching image for country: {first_country_name}")
                image_url = await self.image_service.get_country_image(first_country_name)
                
                if image_url:
                    logger.info(f"✅ Image URL received: {image_url[:100]}...")
                else:
                    logger.warning(f"⚠️ No image URL received for {first_country_name}")
                
                # Record that this country was used for an image
                if first_country_name:
                    self.db.record_image_country(first_country_name)
            
            # Post to group/channel
            await self._post_to_channel(message, image_url, first_country_name, first_country_capital)
            
            # Save to database
            travel_type = content.get("travel_type", "unknown")
            self.db.record_channel_post("evening", travel_type, content)
            
            logger.info(f"Evening post sent: {travel_type}")
            
        except Exception as e:
            logger.error(f"Error posting evening content: {e}")
    
    async def _post_news_content(self):
        """Post news summary (2 main news items)."""
        if not self.news_service:
            logger.warning("News service not available")
            return
        
        try:
            logger.info("Generating news summary...")
            
            # Get used news topics to avoid repetition
            used_topics = self.db.get_used_news_topics(days=7)
            
            # Generate news
            news_data = self.news_service.generate_news_summary(used_topics)
            
            if not news_data:
                logger.error("Failed to generate news")
                return
            
            # Format message
            message = self._format_news_message(news_data)
            
            # Post to group/channel (no image for news)
            await self._post_to_channel(message, None, None, None)
            
            # Save topics to database
            topics = [news.get("topic", "") for news in news_data.get("news", []) if news.get("topic")]
            if topics:
                self.db.record_news_topics(topics)
            
            logger.info(f"News post sent with {len(news_data.get('news', []))} items")
            
        except Exception as e:
            logger.error(f"Error posting news content: {e}")
    
    def _format_news_message(self, news_data: dict) -> str:
        """Format news post message."""
        title = news_data.get("title", "Top 3 World News")
        news_items = news_data.get("news", [])
        
        message = f"📰 {title}\n\n"
        
        for i, news in enumerate(news_items, 1):
            headline = news.get("headline", "")
            summary = news.get("summary", "")
            source = news.get("source", "")
            topic = news.get("topic", "")
            url = news.get("url", "")
            
            # Emoji based on source
            if source == "Bloomberg":
                source_emoji = "💼"
            elif source == "BBC":
                source_emoji = "🌍"
            elif source == "Ukrainian Truth":
                source_emoji = "🇺🇦"
            else:
                source_emoji = "📰"
            
            # Default URLs if not provided
            if not url:
                if source == "Bloomberg":
                    url = "https://www.bloomberg.com"
                elif source == "BBC":
                    url = "https://www.bbc.com/news"
                elif source == "Ukrainian Truth":
                    url = "https://www.pravda.com.ua"
            
            message += f"{i}. **{headline}**\n"
            message += f"   {summary}\n"
            if url:
                message += f"   {source_emoji} [{source}]({url})\n"
            else:
                message += f"   {source_emoji} Source: {source}\n"
            message += "\n"
        
        message += "📚 Sources:\n"
        message += "• [Bloomberg](https://www.bloomberg.com)\n"
        message += "• [BBC News](https://www.bbc.com/news)\n"
        message += "• [Ukrainian Truth](https://www.pravda.com.ua)"
        
        return message
    
    def _format_morning_message(self, content: dict) -> str:
        """Format morning post message."""
        title = content.get("title", "Top Countries")
        topic = content.get("topic", "")
        countries = content.get("countries", [])
        
        # Add title about what the post is about
        post_title = f"📊 {title}"
        if topic:
            post_title = f"📊 {title}\n💡 Topic: {topic.title()}"
        
        message = f"{post_title}\n\n"
        
        for country in countries:
            rank = country.get("rank", 0)
            name = country.get("name", "Unknown")
            capital = country.get("capital", "")
            reason = country.get("reason", "")
            fact = country.get("fact", "")
            
            # Format country name with capital
            country_name = f"{name} ({capital})" if capital else name
            
            # Don't truncate - show full text (Telegram allows up to 4096 chars per message)
            emoji = self._get_rank_emoji(rank)
            message += f"{emoji} **{rank}. {country_name}**\n"
            if reason:
                message += f"   {reason}\n"
            if fact:
                message += f"   💡 {fact}\n"
            
            # Drink (alcoholic or non-alcoholic) with category
            drink = country.get("drink", "")
            drink_category = country.get("drink_category", "")
            if drink:
                if drink_category:
                    message += f"   🍷 {drink} ({drink_category})\n"
                else:
                    message += f"   🍷 {drink}\n"
            
            message += "\n"
        
        # Collect country names and drinks for tags (clean them properly) - AFTER all countries
        country_tags = []
        for c in countries:
            name = c.get("name", "")
            if name:
                # Clean country name for tag (remove spaces, special chars)
                tag = name.replace(" ", "").replace("-", "").replace("'", "")
                if tag:
                    country_tags.append(tag)
        
        drink_tags = []
        for c in countries:
            drink = c.get("drink", "")
            if drink:
                # Clean drink name for tag (remove spaces, parentheses, special chars)
                tag = drink.split("(")[0].strip()  # Take part before parentheses
                tag = tag.replace(" ", "").replace("-", "").replace("'", "").replace(".", "")
                if tag:
                    drink_tags.append(tag)
        
        # Build tags - one per line for readability
        message += "\n"
        message += "#Travel #Countries #Top3\n"
        if country_tags:
            country_tag_line = " ".join([f"#{tag}" for tag in country_tags[:5] if tag])
            if country_tag_line:
                message += f"{country_tag_line}\n"
        if drink_tags:
            drink_tag_line = " ".join([f"#{tag}" for tag in drink_tags[:3] if tag])
            if drink_tag_line:
                message += f"{drink_tag_line}\n"
        
        message += "\n📚 Sources:\n"
        message += "• World Bank Data\n"
        message += "• UN Statistics"
        
        return message
    
    def _format_evening_message(self, content: dict) -> str:
        """Format evening post message."""
        title = content.get("title", "Top Travel Destinations")
        topic = content.get("topic", "")
        countries = content.get("countries", [])
        travel_type = content.get("travel_type", "")
        
        type_emoji = self._get_travel_type_emoji(travel_type)
        # Add title about what the post is about
        post_title = f"{type_emoji} {title}"
        if topic:
            post_title = f"{type_emoji} {title}\n💡 Topic: {topic.title()}"
        
        message = f"{post_title}\n\n"
        
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
            
            # Format activities (each on new line) - limit to 3
            if activities:
                for activity in activities[:3]:  # Max 3 activities
                    message += f"   • {activity}\n"
            elif country.get("reason"):  # Fallback to old format
                reason = country.get("reason", "")
                message += f"   {reason}\n"
            
            # Best time (short format)
            if best_time:
                message += f"   📅 {best_time}\n"
            elif country.get("highlight"):  # Fallback
                highlight = country.get("highlight", "")
                message += f"   📅 {highlight}\n"
            
            # Unique fact
            if unique_fact:
                message += f"   💡 {unique_fact}\n"
            
            # Signature dish (for evening posts)
            signature_dish = country.get("signature_dish", "")
            dish_ingredients = country.get("dish_ingredients", "")
            if signature_dish:
                if dish_ingredients:
                    message += f"   🍽️ {signature_dish} ({dish_ingredients})\n"
                else:
                    message += f"   🍽️ {signature_dish}\n"
            
            message += "\n"
        
        # Collect country names and dishes for tags (clean them properly)
        country_tags = []
        for c in countries:
            name = c.get("name", "")
            if name:
                # Clean country name for tag (remove spaces, special chars)
                tag = name.replace(" ", "").replace("-", "").replace("'", "")
                if tag:
                    country_tags.append(tag)
        
        dish_tags = []
        for c in countries:
            dish = c.get("signature_dish", "")
            if dish:
                # Clean dish name for tag (remove spaces, special chars)
                tag = dish.replace(" ", "").replace("-", "").replace("'", "").replace(".", "")
                if tag:
                    dish_tags.append(tag)
        
        # Build tags - one per line for readability
        message += "\n"
        travel_type_tag = f"#{travel_type.title()}" if travel_type else "#Travel"
        message += f"#Travel {travel_type_tag} #Top3\n"
        if country_tags:
            country_tag_line = " ".join([f"#{tag}" for tag in country_tags[:5] if tag])
            if country_tag_line:
                message += f"{country_tag_line}\n"
        if dish_tags:
            dish_tag_line = " ".join([f"#{tag}" for tag in dish_tags[:3] if tag])
            if dish_tag_line:
                message += f"{dish_tag_line}\n"
            
            message += "\n📚 Sources:\n"
            message += "• Travel Guides & Tourism Boards\n"
            message += "• World Tourism Organization"
            
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
            
            # Always send everything in one post
            if image_url:
                logger.info(f"📸 Downloading image from: {image_url[:100]}...")
                try:
                    # Download and send image with caption
                    async with httpx.AsyncClient() as client:
                        response = await client.get(image_url, timeout=10.0)
                        response.raise_for_status()
                        
                        logger.info(f"✅ Image downloaded, size: {len(response.content)} bytes")
                        
                        # Save temporarily
                        import tempfile
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                            tmp.write(response.content)
                            tmp_path = tmp.name
                        
                        logger.info(f"💾 Image saved to temp file: {tmp_path}")
                        
                        # Combine photo caption with message
                        if photo_caption:
                            combined_caption = f"{photo_caption}\n\n{message}"
                        else:
                            combined_caption = message
                        
                        # Truncate if too long (Telegram limit is 1024 chars for caption)
                        if len(combined_caption) > 1024:
                            # Keep first part and add truncation note
                            truncated = combined_caption[:1000] + "..."
                            caption = truncated
                            logger.warning(f"⚠️ Caption truncated from {len(combined_caption)} to 1024 chars")
                        else:
                            caption = combined_caption
                        
                        logger.info(f"📤 Sending image with caption ({len(caption)} chars) to {target}")
                        
                        # Send to group/channel
                        await self.client.send_file(
                            target,
                            tmp_path,
                            caption=caption,
                            parse_mode='md'
                        )
                        
                        logger.info("✅ Image sent successfully!")
                        
                        # Clean up
                        import os
                        os.unlink(tmp_path)
                        logger.debug("🗑️ Temp file deleted")
                except Exception as img_error:
                    logger.error(f"❌ Error sending image: {img_error}", exc_info=True)
                    logger.info("📝 Falling back to text-only message")
                    # Fallback to text only
                    await self.client.send_message(
                        target,
                        message,
                        parse_mode='md'
                    )
            else:
                logger.info("📝 No image URL, sending text-only message")
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
                logger.error("💡 Check GROUP_USERNAME or GROUP_ID in .env")
            
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