"""Handler for posting to Telegram group/channel."""
import os
import asyncio
import logging
import httpx
from datetime import datetime, time
from typing import Optional
from telethon import TelegramClient, events
from telethon.tl.types import MessageMediaPhoto
from telethon.tl.custom import Button
from content.channel_content import ChannelContentGenerator
from services.image_service import ImageService
from content.person_content import PersonContentGenerator
from content.tech_content import TechContentGenerator
from content.london_content import LondonContentGenerator
from content.uk_content import UKContentGenerator
from services.job_content import JobContentGenerator
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
        news_service=None,
        person_service=None,
        tech_service=None,
        ukraine_news_service=None,
        spider_service=None,
        quote_service=None,
        africa_service=None,
        london_service=None,
        uk_service=None,
        job_service=None,
        weather_service=None
    ):
        self.client = client
        self.db = db
        self.content_generator = content_generator
        self.image_service = image_service
        self.news_service = news_service
        self.person_service = person_service
        self.tech_service = tech_service
        self.ukraine_news_service = ukraine_news_service
        self.spider_service = spider_service
        self.quote_service = quote_service
        self.africa_service = africa_service
        self.london_service = london_service
        self.uk_service = uk_service
        self.job_service = job_service
        self.weather_service = weather_service
        # Can be group username, group ID, or channel username
        self.target_username = os.getenv("GROUP_USERNAME", os.getenv("CHANNEL_USERNAME", ""))
        self.target_id = os.getenv("GROUP_ID", os.getenv("CHANNEL_ID", ""))  # Alternative: group ID
        # Sequential scheduling times (aligned with 10-minute intervals starting at 08:00)
        self.evening_time = os.getenv("EVENING_POST_TIME", "08:10")  # travel
        self.morning_time = os.getenv("MORNING_POST_TIME", "08:20")  # travel morning
        self.news_morning_time = os.getenv("NEWS_MORNING_TIME", "08:30")
        self.news_evening_time = os.getenv("NEWS_EVENING_TIME", "08:30")  # same as morning in sequential mode
        self.tech_time = os.getenv("TECH_POST_TIME", "08:40")
        self.person_time = os.getenv("PERSON_POST_TIME", "08:50")
        self.ukraine_news_time = os.getenv("UKRAINE_NEWS_TIME", "09:00")
        self.spider_time = os.getenv("SPIDER_POST_TIME", "09:10")
        self.quote_time = os.getenv("QUOTE_POST_TIME", "09:20")
        self.africa_time = os.getenv("AFRICA_POST_TIME", "09:30")
        self.london_time = os.getenv("LONDON_POST_TIME", "09:40")  # Canary Wharf
        self.uk_time = os.getenv("UK_POST_TIME", "09:50")
        self.job_morning_time = os.getenv("JOB_MORNING_TIME", "10:00")
        self.job_evening_time = os.getenv("JOB_EVENING_TIME", "10:00")  # same as morning in sequential mode
        self.weather_morning_time = os.getenv("WEATHER_MORNING_TIME", "09:00")
        self.weather_evening_time = os.getenv("WEATHER_EVENING_TIME", "19:00")
        # Legacy support for single WEATHER_POST_TIME
        if os.getenv("WEATHER_POST_TIME") and not os.getenv("WEATHER_MORNING_TIME"):
            self.weather_morning_time = os.getenv("WEATHER_POST_TIME", "09:00")
        self.enabled = os.getenv("GROUP_POSTS_ENABLED", "off").lower() == "on"
        self.control_chat_id = os.getenv("CONTROL_CHAT_ID", "me")
        
        # Commands will be registered after client is started
        self._commands_registered = False
        self._resolved_control_chat = None  # Will be resolved when client is started
        
        # Sequential scheduling mode (starts at START_TIME, posts every INTERVAL_MIN minutes)
        self.sequential_mode = os.getenv("SEQUENTIAL_SCHEDULING", "off").lower() == "on"
        self.sequential_start_time = os.getenv("SEQUENTIAL_START_TIME", "08:00")
        self.sequential_interval = int(os.getenv("SEQUENTIAL_INTERVAL_MIN", "10"))
        
        logger.info(f"🎛️ Control chat ID: {self.control_chat_id}")
        if self.sequential_mode:
            logger.info(f"📅 Sequential scheduling enabled: starts at {self.sequential_start_time}, every {self.sequential_interval} min")
    
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
        logger.info(f"📅 Sequential schedule: All posts in morning (08:10-10:10, 10-min intervals)")
        
        # Check if we missed morning post today
        await self._check_missed_posts()
        
        # Resolve control chat ID first (need async)
        await self._resolve_control_chat()
        
        # Register manual trigger commands (after client is started)
        if not self._commands_registered:
            self._register_commands()
            self._commands_registered = True
        
        # Start background task
        asyncio.create_task(self._scheduler_loop())
    
    async def _resolve_control_chat(self):
        """Resolve control chat ID to actual entity."""
        if self._resolved_control_chat is not None:
            return self._resolved_control_chat
        
        try:
            # If control_chat_id is "me", get our own user ID
            if self.control_chat_id == "me":
                me = await self.client.get_me()
                self._resolved_control_chat = me.id
                logger.info(f"✅ Resolved 'me' to user ID: {self._resolved_control_chat}")
            else:
                # Try to parse as int (user/chat ID)
                try:
                    chat_id = int(self.control_chat_id)
                    self._resolved_control_chat = chat_id
                    logger.info(f"✅ Using numeric chat ID: {self._resolved_control_chat}")
                except ValueError:
                    # It's a username, resolve it
                    entity = await self.client.get_entity(self.control_chat_id)
                    self._resolved_control_chat = entity.id
                    logger.info(f"✅ Resolved '{self.control_chat_id}' to ID: {self._resolved_control_chat}")
            
            return self._resolved_control_chat
        except Exception as e:
            logger.error(f"❌ Failed to resolve control chat '{self.control_chat_id}': {e}")
            # Fallback to "me"
            me = await self.client.get_me()
            self._resolved_control_chat = me.id
            logger.info(f"⚠️ Using fallback 'me' -> {self._resolved_control_chat}")
            return self._resolved_control_chat
    
    def _register_commands(self):
        """Register manual trigger commands for testing."""
        logger.info(f"📝 Registering manual commands for control chat: {self.control_chat_id}")
        
        # Register event handler without chat filter first, then filter inside
        # This is more reliable for catching all messages
        @self.client.on(events.NewMessage)
        async def handle_manual_trigger(event):
            try:
                # First, check if this message is from the control chat
                control_chat_id = await self._resolve_control_chat()
                
                # Get chat ID from event
                chat_id = None
                if event.is_private:
                    chat_id = event.sender_id
                elif event.chat_id:
                    chat_id = event.chat_id
                
                # Only process messages from control chat
                if chat_id != control_chat_id:
                    return
                
                # Debug logging
                text = (event.message.message or "").strip()
                me = await self.client.get_me()
                logger.info(f"📨 Received message from control chat: '{text}' (out={event.message.out}, sender_id={event.sender_id}, me_id={me.id}, reply_to={bool(event.message.reply_to)})")
                
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
                text_lower = text.lower().strip()
                logger.info(f"📨 Processing message for commands: '{text}' (lowercase: '{text_lower}')")
                
                # Handle commands
                command_handled = False
                
                if text_lower == "status":
                    command_handled = True
                    logger.info("📊 Manual status command triggered")
                    try:
                        # Get budget status
                        budget_status = self.content_generator.budget_guard.get_status()
                        
                        # Build status message
                        status_msg = "📊 **Group Posts Service Status**\n\n"
                        
                        # Budget info
                        status_msg += f"💰 **Budget**\n"
                        status_msg += f"Spent today: ${budget_status.get('estimated_usd', 0):.2f}\n"
                        status_msg += f"Daily budget: ${budget_status.get('daily_budget', 0):.2f}\n"
                        status_msg += f"LLM calls: {budget_status.get('llm_calls', 0)}\n"
                        status_msg += f"Tokens used: {budget_status.get('tokens_used', 0)}\n\n"
                        
                        # LLM status
                        status_msg += f"🤖 **LLM Status**\n"
                        if budget_status.get('can_use_llm', False):
                            status_msg += f"✅ Enabled and available\n"
                        else:
                            status_msg += f"❌ Disabled or budget exceeded\n"
                        status_msg += f"LLM enabled: {budget_status.get('llm_enabled', False)}\n"
                        status_msg += f"Model: {self.content_generator.openai_model}\n\n"
                        
                        # Post counts today
                        status_msg += f"📈 **Posts Today**\n"
                        
                        morning_posts = len(self.db.get_channel_posts_today("morning"))
                        evening_posts = len(self.db.get_channel_posts_today("evening"))
                        spider_posts = len(self.db.get_spider_posts_today())
                        
                        status_msg += f"🌍 Morning travel: {morning_posts}\n"
                        status_msg += f"🚀 Evening travel: {evening_posts}\n"
                        status_msg += f"🕷️ Spider: {spider_posts}\n"
                        
                        # Weather API calls (from counter file)
                        weather_api_calls = 0
                        weather_api_limit = 10
                        try:
                            from pathlib import Path
                            import json
                            from datetime import date
                            import os
                            # Get service directory (parent of services/)
                            service_dir = os.path.dirname(os.path.dirname(__file__))
                            counter_file = Path(service_dir) / "data" / "weather_api_calls.json"
                            if counter_file.exists():
                                data = json.loads(counter_file.read_text(encoding="utf-8"))
                                today = date.today().isoformat()
                                if data.get("date") == today:
                                    weather_api_calls = data.get("calls", 0)
                        except Exception as e:
                            logger.debug(f"Could not read weather API counter: {e}")
                        
                        status_msg += f"🌤️ Weather: API calls {weather_api_calls}/{weather_api_limit}\n\n"
                        
                        # Service status
                        status_msg += f"✅ **Service Running**\n"
                        status_msg += f"Control chat: {self.control_chat_id}\n"
                        status_msg += f"Target: {self.target_username or self.target_id or 'Not configured'}"
                        
                        await event.reply(status_msg)
                        logger.info("✅ Status command completed successfully")
                    except Exception as e:
                        logger.error(f"❌ Status command error: {e}", exc_info=True)
                        await event.reply(f"❌ Error getting status: {e}")
                
                elif text_lower == "travel":
                    command_handled = True
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
                    command_handled = True
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
                    command_handled = True
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
                
                elif text_lower == "person":
                    command_handled = True
                    logger.info("👤 Manual person command triggered")
                    await event.reply("👤 Generating famous person post...")
                    try:
                        await self._post_person_content()
                        await event.reply("✅ Person post sent!")
                        logger.info("✅ Manual person post completed successfully")
                    except Exception as e:
                        error_msg = str(e)
                        logger.error(f"❌ Manual person post error: {e}", exc_info=True)
                        await event.reply(f"❌ Error: {error_msg}\n\n💡 Check:\n- Is GROUP_USERNAME or GROUP_ID set?\n- Are you admin in the group?\n- Check logs for details")
                
                elif text_lower == "tech":
                    command_handled = True
                    logger.info("🔧 Manual tech command triggered")
                    await event.reply("🔧 Generating tech device post...")
                    try:
                        await self._post_tech_content()
                        await event.reply("✅ Tech post sent!")
                        logger.info("✅ Manual tech post completed successfully")
                    except Exception as e:
                        error_msg = str(e)
                        logger.error(f"❌ Manual tech post error: {e}", exc_info=True)
                        await event.reply(f"❌ Error: {error_msg}\n\n💡 Check:\n- Is GROUP_USERNAME or GROUP_ID set?\n- Are you admin in the group?\n- Check logs for details")
                
                elif text_lower == "ukraine":
                    command_handled = True
                    logger.info("🇺🇦 Manual Ukraine news command triggered")
                    await event.reply("🇺🇦 Generating Ukraine news...")
                    try:
                        await self._post_ukraine_news_content()
                        await event.reply("✅ Ukraine news post sent!")
                        logger.info("✅ Manual Ukraine news post completed successfully")
                    except Exception as e:
                        error_msg = str(e)
                        logger.error(f"❌ Manual Ukraine news post error: {e}", exc_info=True)
                        await event.reply(f"❌ Error: {error_msg}\n\n💡 Check:\n- Is GROUP_USERNAME or GROUP_ID set?\n- Are you admin in the group?\n- Check logs for details")
                
                elif text_lower == "spider":
                    command_handled = True
                    logger.info("🕸️ Manual spider command triggered (cute spiders only)")
                    await event.reply("🕸️ Generating educational spider post...")
                    try:
                        await self._post_spider_content()
                        await event.reply("✅ Spider post sent!")
                        logger.info("✅ Manual spider post completed successfully")
                    except Exception as e:
                        error_msg = str(e)
                        logger.error(f"❌ Manual spider post error: {e}", exc_info=True)
                        await event.reply(f"❌ Error: {error_msg}\n\n💡 Check:\n- Is GROUP_USERNAME or GROUP_ID set?\n- Are you admin in the group?\n- Check logs for details")
                elif text_lower == "canary":
                    command_handled = True
                    logger.info("🏢 Manual Canary Wharf command triggered")
                    await event.reply("🏢 Generating Canary Wharf post...")
                    try:
                        await self._post_london_content()
                        await event.reply("✅ Canary Wharf post sent!")
                        logger.info("✅ Manual Canary Wharf post completed successfully")
                    except Exception as e:
                        error_msg = str(e)
                        logger.error(f"❌ Manual Canary Wharf post error: {e}", exc_info=True)
                        await event.reply(f"❌ Error: {error_msg}\n\n💡 Check:\n- Is GROUP_USERNAME or GROUP_ID set?\n- Are you admin in the group?\n- Check logs for details")
                elif text_lower == "uk":
                    command_handled = True
                    logger.info("🇬🇧 Manual UK command triggered")
                    await event.reply("🇬🇧 Generating UK post...")
                    try:
                        await self._post_uk_content()
                        await event.reply("✅ UK post sent!")
                        logger.info("✅ Manual UK post completed successfully")
                    except Exception as e:
                        error_msg = str(e)
                        logger.error(f"❌ Manual UK post error: {e}", exc_info=True)
                        await event.reply(f"❌ Error: {error_msg}\n\n💡 Check:\n- Is GROUP_USERNAME or GROUP_ID set?\n- Are you admin in the group?\n- Check logs for details")
                elif text_lower == "job":
                    command_handled = True
                    logger.info("💼 Manual job command triggered")
                    await event.reply("💼 Generating job vacancies...")
                    try:
                        await self._post_job_content()
                        await event.reply("✅ Job post sent!")
                        logger.info("✅ Manual job post completed successfully")
                    except Exception as e:
                        error_msg = str(e)
                        logger.error(f"❌ Manual job post error: {e}", exc_info=True)
                        await event.reply(f"❌ Error: {error_msg}\n\n💡 Check:\n- Is GROUP_USERNAME or GROUP_ID set?\n- Are you admin in the group?\n- Check logs for details")
                elif text_lower == "quote":
                    command_handled = True
                    logger.info("💬 Manual quote command triggered")
                    await event.reply("💬 Generating quote of the day...")
                    try:
                        await self._post_quote_content()
                        await event.reply("✅ Quote post sent!")
                        logger.info("✅ Manual quote post completed successfully")
                    except Exception as e:
                        error_msg = str(e)
                        logger.error(f"❌ Manual quote post error: {e}", exc_info=True)
                        await event.reply(f"❌ Error: {error_msg}\n\n💡 Check:\n- Is GROUP_USERNAME or GROUP_ID set?\n- Are you admin in the group?\n- Check logs for details")
                elif text_lower == "weather":
                    command_handled = True
                    logger.info("🌤️ Manual weather command triggered")
                    await event.reply("🌤️ Generating weather forecast...")
                    try:
                        await self._post_weather_content()
                        await event.reply("✅ Weather post sent!")
                        logger.info("✅ Manual weather post completed successfully")
                    except Exception as e:
                        error_msg = str(e)
                        logger.error(f"❌ Manual weather post error: {e}", exc_info=True)
                        await event.reply(f"❌ Error: {error_msg}\n\n💡 Check:\n- Is GROUP_USERNAME or GROUP_ID set?\n- Are you admin in the group?\n- Check logs for details")
                elif text_lower == "africa":
                    command_handled = True
                    logger.info("🌍 Manual Africa explore command triggered")
                    await event.reply("🌍 Generating Africa explore post...")
                    try:
                        await self._post_africa_content()
                        await event.reply("✅ Africa explore post sent!")
                        logger.info("✅ Manual Africa explore post completed successfully")
                    except Exception as e:
                        error_msg = str(e)
                        logger.error(f"❌ Manual Africa explore post error: {e}", exc_info=True)
                        await event.reply(f"❌ Error: {error_msg}\n\n💡 Check:\n- Is GROUP_USERNAME or GROUP_ID set?\n- Are you admin in the group?\n- Check logs for details")
                
                if not command_handled:
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
            
            # Check if person post was sent today (if person service is available)
            if self.person_service:
                person_posts_today = self.db.get_person_posts_today()
                logger.info(f"📊 Person posts today: {len(person_posts_today) if person_posts_today else 0}")
                
                if not person_posts_today:
                    # Check if person time has passed
                    person_hour, person_min = map(int, self.person_time.split(":"))
                    current_hour = now.hour
                    current_min = now.minute
                    
                    logger.info(f"⏰ Person time: {self.person_time}, Current: {current_hour:02d}:{current_min:02d}")
                    
                    # If current time is after person time, we missed it
                    if (current_hour > person_hour) or (current_hour == person_hour and current_min >= person_min):
                        logger.info("⚠️ Person post was missed today, posting now...")
                        await self._post_person_content()
                    else:
                        logger.info(f"✅ Person post time hasn't passed yet ({self.person_time})")
                else:
                    logger.info("✅ Person post already sent today")
            
            # Check if tech post was sent today (if tech service is available)
            if self.tech_service:
                tech_posts_today = self.db.get_tech_posts_today()
                logger.info(f"📊 Tech posts today: {len(tech_posts_today) if tech_posts_today else 0}")
                
                if not tech_posts_today:
                    # Check if tech time has passed
                    tech_hour, tech_min = map(int, self.tech_time.split(":"))
                    current_hour = now.hour
                    current_min = now.minute
                    
                    logger.info(f"⏰ Tech time: {self.tech_time}, Current: {current_hour:02d}:{current_min:02d}")
                    
                    # If current time is after tech time, we missed it
                    if (current_hour > tech_hour) or (current_hour == tech_hour and current_min >= tech_min):
                        logger.info("⚠️ Tech post was missed today, posting now...")
                        await self._post_tech_content()
                    else:
                        logger.info(f"✅ Tech post time hasn't passed yet ({self.tech_time})")
                else:
                    logger.info("✅ Tech post already sent today")
                
        except Exception as e:
            logger.error(f"❌ Error checking missed posts: {e}", exc_info=True)
    
    async def _scheduler_loop(self):
        """Main scheduler loop."""
        last_morning_post_date = None
        last_evening_post_date = None
        
        # Sequential scheduling state
        sequential_services = [
            ("status", None),  # status doesn't post, just reports
            ("travel", self._post_evening_content),
            ("travel morning", self._post_morning_content),
            ("news", self._post_news_content),
            ("tech", self._post_tech_content),
            ("person", self._post_person_content),
            ("ukraine", self._post_ukraine_news_content),
            ("spider", self._post_spider_content),  # Educational, cute spiders only
            ("quote", self._post_quote_content),
            ("africa", self._post_africa_content),
            ("canary", self._post_london_content),
            ("uk", self._post_uk_content),
            ("job", self._post_job_content),
            ("weather", self._post_weather_content),
        ]
        sequential_last_run = {}  # Track when each service last ran
        sequential_today_runs = {}  # Track services run today
        
        logger.info("🔄 Scheduler loop started")
        if self.sequential_mode:
            logger.info(f"📅 Sequential mode: starting at {self.sequential_start_time}, every {self.sequential_interval} minutes")
        
        while True:
            try:
                now = datetime.now()
                current_time = now.strftime("%H:%M")
                today = now.date()
                
                # Reset daily sequential tracking at midnight
                if sequential_today_runs.get('date') != today:
                    sequential_today_runs = {'date': today, 'services': []}
                    logger.info(f"📅 New day detected, resetting sequential tracking")
                
                # Sequential scheduling mode
                if self.sequential_mode:
                    start_hour, start_min = map(int, self.sequential_start_time.split(":"))
                    current_total_minutes = now.hour * 60 + now.minute
                    start_total_minutes = start_hour * 60 + start_min
                    
                    # Check if we're past start time
                    if current_total_minutes >= start_total_minutes:
                        # Calculate which service should run now
                        minutes_since_start = current_total_minutes - start_total_minutes
                        service_index = minutes_since_start // self.sequential_interval
                        
                        if service_index < len(sequential_services):
                            service_name, service_func = sequential_services[service_index]
                            
                            # Check if this service hasn't run today yet
                            if service_name not in sequential_today_runs.get('services', []):
                                # Check if it's time to run (at the exact interval)
                                if minutes_since_start % self.sequential_interval == 0:
                                    logger.info(f"📅 Sequential: Running service {service_index + 1}/{len(sequential_services)}: {service_name}")
                                    
                                    try:
                                        if service_func:
                                            await service_func()
                                        else:
                                            # Status doesn't post, just log
                                            logger.info(f"✅ Sequential: {service_name} (status check)")
                                        
                                        sequential_today_runs['services'].append(service_name)
                                        sequential_last_run[service_name] = now
                                        logger.info(f"✅ Sequential: {service_name} completed")
                                        
                                        # Wait for next interval
                                        await asyncio.sleep(60)
                                    except Exception as e:
                                        logger.error(f"❌ Sequential: Error running {service_name}: {e}", exc_info=True)
                                        sequential_today_runs['services'].append(service_name)  # Mark as attempted
                
                # Regular scheduling mode (if not sequential or as fallback)
                if not self.sequential_mode:
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
                    
                    # Person and Tech posts removed from scheduler (as requested)
                    
                    # Check UK posts (if UK service is available)
                    if self.uk_service:
                        if current_time == self.uk_time:
                            uk_posts_today = self.db.get_uk_posts_today()
                            if not uk_posts_today:
                                logger.info(f"🇬🇧 UK post time reached: {self.uk_time}")
                                await self._post_uk_content()
                                await asyncio.sleep(60)
                    
                    # Check London posts (if London service is available)
                    if self.london_service:
                        if current_time == self.london_time:
                            london_posts_today = self.db.get_london_posts_today()
                            if not london_posts_today:
                                logger.info(f"🏢 Canary Wharf post time reached: {self.london_time}")
                                await self._post_london_content()
                                await asyncio.sleep(60)
                    
                    # Check spider posts (educational, cute spiders only)
                    if self.spider_service:
                        if current_time == self.spider_time:
                            spider_posts_today = self.db.get_spider_posts_today()
                            if not spider_posts_today:
                                logger.info(f"🕸️ Spider post time reached: {self.spider_time}")
                                await self._post_spider_content()
                                await asyncio.sleep(60)
                    
                    # Check quote posts (if quote service is available)
                    if self.quote_service:
                        if current_time == self.quote_time:
                            quote_posts_today = self.db.get_phrase_posts_today()  # Still uses same DB method
                            if not quote_posts_today:
                                logger.info(f"💬 Quote post time reached: {self.quote_time}")
                                await self._post_quote_content()
                                await asyncio.sleep(60)
                    
                    # Check weather posts (if weather service is available) - twice per day
                    if self.weather_service:
                        if current_time == self.weather_morning_time:
                            logger.info(f"🌤️ Weather post time reached (morning): {self.weather_morning_time}")
                            await self._post_weather_content()
                            await asyncio.sleep(60)
                        elif current_time == self.weather_evening_time:
                            logger.info(f"🌤️ Weather post time reached (evening): {self.weather_evening_time}")
                            await self._post_weather_content()
                            await asyncio.sleep(60)
                    
                    # Log every 5 minutes for debugging
                    if now.minute % 5 == 0 and now.second < 5:
                        waiting_times = f"{self.morning_time} / {self.evening_time}"
                        if self.news_service:
                            waiting_times += f" / News: {self.news_morning_time} / {self.news_evening_time}"
                        if self.job_service:
                            waiting_times += f" / Jobs: {self.job_morning_time} / {self.job_evening_time}"
                        if self.uk_service:
                            waiting_times += f" / UK: {self.uk_time}"
                        if self.london_service:
                            waiting_times += f" / Canary: {self.london_time}"
                        if self.spider_service:
                            waiting_times += f" / Spider: {self.spider_time}"
                        if self.quote_service:
                            waiting_times += f" / Quote: {self.quote_time}"
                        if self.weather_service:
                            waiting_times += f" / Weather: {self.weather_morning_time} / {self.weather_evening_time}"
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
    
    async def _post_ukraine_news_content(self):
        """Post Ukraine news summary (economy, politics, war)."""
        if not self.ukraine_news_service:
            logger.warning("Ukraine news service not available")
            return
        
        try:
            # Get used news topics to avoid repetition
            used_topics = self.db.get_used_news_topics(days=7)
            
            # Generate Ukraine news
            news_data = self.ukraine_news_service.generate_ukraine_news(used_topics)
            
            if not news_data:
                logger.error("Failed to generate Ukraine news")
                return
            
            # Format message
            message = self._format_ukraine_news_message(news_data)
            
            # Ukrainian flag image URL
            # Using flagcdn.com as primary source (more bot-friendly than Wikimedia)
            ukraine_flag_url = "https://flagcdn.com/w1280/ua.png"
            logger.info(f"🇺🇦 Preparing to post Ukraine news with flag image: {ukraine_flag_url}")
            
            # Post to group/channel with Ukrainian flag image
            await self._post_to_channel(message, ukraine_flag_url, None, None)
            
            # Save to database
            self.db.record_ukraine_news_post(news_data)
            
            # Save topics to database
            topics = [news.get("category", "") for news in news_data.get("news", []) if news.get("category")]
            if topics:
                self.db.record_news_topics(topics)
            
        except Exception as e:
            logger.error(f"Error posting Ukraine news content: {e}", exc_info=True)
    
    def _format_ukraine_news_message(self, news_data: dict) -> str:
        """Format Ukraine news post message."""
        title = news_data.get("title", "Top 3 Ukraine News")
        news_items = news_data.get("news", [])
        
        message = f"🇺🇦 {title}\n\n"
        
        for i, news in enumerate(news_items, 1):
            headline = news.get("headline", "")
            summary = news.get("summary", "")
            source = news.get("source", "")
            category = news.get("category", "")
            url = news.get("url", "")
            
            # Emoji based on category
            if category == "economy":
                category_emoji = "💰"
            elif category == "politics":
                category_emoji = "🏛️"
            elif category == "war":
                category_emoji = "⚔️"
            else:
                category_emoji = "📰"
            
            # Ensure URL has protocol
            if url and not url.startswith(("http://", "https://")):
                url = "https://" + url
            
            # Default URLs if not provided
            if not url:
                if "pravda" in source.lower() or "Ukrainian Truth" in source:
                    url = "https://www.pravda.com.ua"
                elif "bbc" in source.lower():
                    url = "https://www.bbc.com/ukrainian"
                elif "ukrinform" in source.lower():
                    url = "https://www.ukrinform.net"
                else:
                    url = "https://www.pravda.com.ua"
            
            message += f"{category_emoji} **{headline}**\n"
            message += f"   {summary}\n"
            if url:
                # Extract domain for display
                try:
                    from urllib.parse import urlparse
                    parsed_url = urlparse(url)
                    domain = parsed_url.netloc.replace("www.", "")
                    if not domain:
                        domain = url.replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0]
                    message += f"   📰 [{source}]({url})\n"
                except:
                    message += f"   📰 [{source}]({url})\n"
            else:
                message += f"   📰 Source: {source}\n"
            message += "\n"
        
        message += "📚 Sources:\n"
        message += "• [Ukrainian Truth](https://www.pravda.com.ua)\n"
        message += "• [BBC Ukraine](https://www.bbc.com/ukrainian)\n"
        message += "• [Ukrinform](https://www.ukrinform.net)"
        
        return message
    
    async def _post_spider_content(self):
        """Post spider content with UK/London information."""
        if not self.spider_service:
            logger.warning("Spider service not available")
            return
        
        try:
            # Get used spiders to avoid repetition
            used_spiders = self.db.get_used_spiders(days=30)
            
            # Generate spider content
            content = self.spider_service.generate_spider_post(used_spiders)
            
            if not content:
                logger.error("Failed to generate spider content")
                return
            
            # Format message
            message, inline_keyboard = self._format_spider_message(content)
            
            # Get spider name for database recording
            spider_name = content.get("name", "")
            
            # Get image for the spider
            # Priority: 1) iNaturalist photo (if available), 2) Unsplash fallback
            image_url = content.get("photo_url")  # iNaturalist photo
            
            if not image_url:
                # Fallback to Unsplash if no iNaturalist photo
                if spider_name:
                    image_url = await self._get_spider_image(spider_name)
                    logger.info("Using Unsplash photo (no iNaturalist photo available)")
            else:
                logger.info(f"✅ Using iNaturalist photo: {content.get('photo_location', 'unknown location')}")
            
            # Post to group/channel with inline keyboard
            await self._post_to_channel(message, image_url, None, None, inline_keyboard)
            
            # Save to database
            self.db.record_spider_post(content)
            
            # Record spider usage
            if spider_name:
                self.db.record_spider(spider_name)
            
        except Exception as e:
            logger.error(f"Error posting spider content: {e}", exc_info=True)
    
    async def _get_spider_image(self, spider_name: str) -> Optional[str]:
        """Get image URL for a spider."""
        unsplash_key = os.getenv("UNSPLASH_ACCESS_KEY", "")
        if not unsplash_key:
            logger.debug("Unsplash API key not set, skipping image fetch")
            return None
        
        try:
            async with httpx.AsyncClient() as client:
                url = "https://api.unsplash.com/search/photos"
                
                # Try multiple query strategies
                queries = [
                    f"{spider_name} spider",
                    f"{spider_name} arachnid",
                    f"{spider_name}",
                ]
                
                for query in queries:
                    params = {
                        "query": query,
                        "per_page": 10,
                        "orientation": "landscape",
                        "order_by": "relevance"
                    }
                    headers = {
                        "Authorization": f"Client-ID {unsplash_key}"
                    }
                    
                    response = await client.get(url, params=params, headers=headers, timeout=10.0)
                    response.raise_for_status()
                    data = response.json()
                    
                    if data.get("results") and len(data["results"]) > 0:
                        # Try to find image that matches spider name
                        spider_name_lower = spider_name.lower()
                        for photo in data["results"]:
                            desc = (photo.get("description", "") or "") + " " + (photo.get("alt_description", "") or "")
                            desc_lower = desc.lower()
                            # Check if spider name or key words appear in description
                            if any(word in desc_lower for word in spider_name_lower.split()[:2]):
                                image_url = photo["urls"]["regular"]
                                return image_url
                        
                        # Fallback to first result
                        image_url = data["results"][0]["urls"]["regular"]
                        return image_url
                
                return None
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                logger.warning("Unsplash API key invalid or expired. Posts will work without images.")
            else:
                logger.warning(f"Unsplash API error: {e}. Posts will work without images.")
        except Exception as e:
            logger.debug(f"Error fetching from Unsplash: {e}")
        
        return None
    
    def _format_spider_message(self, content: dict) -> tuple:
        """Format spider post message (anxiety-friendly, cute, educational).
        
        Uses new behavior-based format:
        - "active hunter" / "web-based hunter" / "ambush predator"
        - NO "Hunter: Yes/No"
        - NO "Dangerous rate"
        - Includes calm_opening, calm_explanation, gentle_takeaway for arachnophobia-friendly content
        """
        spider_name = content.get("name", "Spider")
        scientific_name = content.get("scientific_name", "")
        countries = content.get("countries", [])
        size = content.get("size", "")
        color = content.get("color", "")
        behavior = content.get("behavior", "")  # NEW: active hunter / web-based hunter / ambush predator
        behavior_explanation = content.get("behavior_explanation", "")
        lifespan = content.get("lifespan", "")
        resource_link = content.get("resource_link", "")
        confidence_level = content.get("confidence_level", "")  # NEW: confirmed / likely / uncertain
        
        # 🥰 CUTE & CALM FIELDS (for arachnophobia-friendly content)
        calm_opening = content.get("calm_opening", "")
        what_you_see = content.get("what_you_see", "")
        calm_explanation = content.get("calm_explanation", "")
        interesting_fact = content.get("interesting_fact", "")
        gentle_takeaway = content.get("gentle_takeaway", "")
        
        # Build message with anxiety-friendly structure
        message = f"🕷️ **{spider_name}**"
        if scientific_name:
            message += f" ({scientific_name})"
        message += "\n\n"
        
        # 🥰 START WITH CALM OPENING (if available) - this is the key to making it not scary!
        if calm_opening:
            message += f"{calm_opening}\n\n"
        
        # What you see (if available)
        if what_you_see:
            message += f"👀 {what_you_see}\n\n"
        
        # Basic details (compact format)
        if countries:
            countries_str = ', '.join(countries) if isinstance(countries, list) else str(countries)
            message += f"📍 **Where to meet:** {countries_str}\n"
        if size:
            message += f"📏 **Size:** {size}\n"
        if color:
            message += f"🎨 **Color:** {color}\n"
        
        # ✅ NEW: Behavior (replaces "Hunter: Yes/No")
        if behavior:
            # Capitalize first letter for display
            behavior_display = behavior.capitalize() if behavior else ""
            message += f"🕸️ **Behavior:** {behavior_display}\n"
            
            # Add behavior explanation if provided (short, calming)
            if behavior_explanation:
                # Keep it short - first sentence only
                explanation_short = behavior_explanation.split('.')[0] + '.'
                message += f"   {explanation_short}\n"
        
        if lifespan:
            message += f"⏳ **Lifespan:** {lifespan}\n"
        
        message += "\n"
        
        # 🥰 CALM EXPLANATION (why not threatening) - very important for arachnophobes!
        if calm_explanation:
            message += f"💚 {calm_explanation}\n\n"
        
        # 🥰 INTERESTING FACT (educational, not scary)
        if interesting_fact:
            message += f"💡 {interesting_fact}\n\n"
        
        # 🥰 GENTLE TAKEAWAY (reassuring closing)
        if gentle_takeaway:
            message += f"✨ {gentle_takeaway}\n\n"
        
        # Source link
        if resource_link:
            # Ensure link has protocol
            if not resource_link.startswith(("http://", "https://")):
                resource_link = "https://" + resource_link
            
            try:
                from urllib.parse import urlparse
                parsed_url = urlparse(resource_link)
                domain = parsed_url.netloc.replace("www.", "")
                if not domain:
                    domain = resource_link.replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0]
                
                # Short domain name for source
                if "wikipedia" in domain.lower():
                    message += f"**Source:** [Wikipedia]({resource_link})\n\n"
                elif len(domain) > 30:
                    domain = domain[:27] + "..."
                    message += f"**Source:** [{domain}]({resource_link})\n\n"
                else:
                    message += f"**Source:** [{domain}]({resource_link})\n\n"
            except:
                message += f"**Source:** {resource_link}\n\n"
        
        # Photo attribution (if from iNaturalist)
        photo_attribution = content.get("photo_attribution")
        photo_location = content.get("photo_location")
        if photo_attribution:
            message += f"\n\n📸 {photo_attribution}"
            if photo_location:
                message += f" • {photo_location}"
        
        # Tags
        message += "\n\n#Spider #Nature"
        
        # Create inline keyboard with Wikipedia + iNaturalist
        inline_keyboard = []
        buttons_row = []
        
        if resource_link:
            button_link = resource_link
            if not button_link.startswith(("http://", "https://")):
                button_link = "https://" + button_link
            
            button_text = "📖 Source"
            if "wikipedia" in button_link.lower():
                button_text = "📖 Wikipedia"
            
            buttons_row.append(Button.url(button_text, button_link))
        
        # Add iNaturalist button if photo is from there
        inaturalist_url = content.get("inaturalist_url")
        if inaturalist_url:
            buttons_row.append(Button.url("📸 iNaturalist", inaturalist_url))
        
        if buttons_row:
            inline_keyboard = [buttons_row]
        else:
            inline_keyboard = None
        
        return message, inline_keyboard
    
    async def _post_quote_content(self):
        """Post quote of the day content."""
        if not self.quote_service:
            logger.warning("Quote service not available")
            return
        
        try:
            # Get used quotes to avoid repetition
            used_quotes = self.db.get_used_phrases(days=30)  # Still uses same DB method (backward compatible)
            
            # Get used authors to avoid same images
            used_authors = self.db.get_used_quote_authors(days=7)
            
            # Generate quote content
            content = self.quote_service.generate_quote_post(used_quotes)
            
            if not content:
                logger.error("Failed to generate quote content")
                return
            
            # Get random Asian country for nature image
            asian_countries = [
                "Japan", "South Korea", "Thailand", "Vietnam", "Indonesia", 
                "Malaysia", "Philippines", "Singapore", "India", "Nepal",
                "Bhutan", "Myanmar", "Cambodia", "Laos", "Sri Lanka",
                "China", "Taiwan", "Mongolia", "Bangladesh"
            ]
            
            # Get used countries to avoid repetition
            used_countries = self.db.get_used_quote_authors(days=7)  # Reuse this table for countries
            available_countries = [c for c in asian_countries if c not in used_countries]
            
            # If all countries were used, reset
            if not available_countries:
                available_countries = asian_countries
            
            import random
            selected_country = random.choice(available_countries)
            
            # Get nature image for the country (prefer nature photos)
            image_url = await self._get_country_image(selected_country, prefer_nature=True)
            
            # Record country usage
            self.db.record_quote_author(selected_country)
            
            # Format message with country name
            message, inline_keyboard = self._format_quote_message(content, selected_country)
            
            # Post to group/channel with inline keyboard
            await self._post_to_channel(message, image_url, None, None, inline_keyboard)
            
            # Save to database
            self.db.record_phrase_post(content)  # Still uses same DB method (backward compatible)
            
            # Record quote usage
            quote = content.get("quote", content.get("phrase", ""))
            if quote:
                self.db.record_phrase(quote)  # Still uses same DB method (backward compatible)
            
        except Exception as e:
            logger.error(f"Error posting quote content: {e}", exc_info=True)
    
    def _format_quote_message(self, content: dict, country_name: str = "") -> tuple:
        """Format quote of the day message. Returns (message_text, inline_keyboard)."""
        quote = content.get("quote", content.get("phrase", ""))
        author = content.get("author", "")
        author_info = content.get("author_info", "")
        advice = content.get("advice", "")
        category = content.get("category", "")
        resource_link = content.get("resource_link", "")
        
        # Build compact message
        message = f"💬 **Quote of the Day**\n\n"
        message += f"\"{quote}\"\n\n"
        
        # Author: 1 short line, no repetition
        if author:
            # Use only author name, or very short info if needed
            if author_info and len(author_info) < 40:
                # Only use short author_info if it's really brief
                message += f"— {author}, {author_info}\n\n"
            else:
                message += f"— {author}\n\n"
        
        # Advice: just add it directly without "Takeaway" label
        if advice:
            # Shorten advice to 1-2 sentences
            sentences = advice.split('.')
            short_advice = '. '.join(sentences[:2]).strip()
            if short_advice and not short_advice.endswith('.'):
                short_advice += '.'
            if short_advice:
                message += f"{short_advice}\n\n"
        
        # Category is not needed - removed for cleaner output
        
        # Source: Wikipedia format (removed text, using only button below)
        # No need for text source since we have clickable button
        
        # Country name signature for image
        if country_name:
            message += f"📍 {country_name}\n\n"
        
        # Tags: simplified
        tags = ["#QuoteOfTheDay", "#Wisdom"]
        message += " ".join(tags)
        
        # Create inline keyboard for source
        inline_keyboard = None
        if resource_link:
            button_link = resource_link
            if not button_link.startswith(("http://", "https://")):
                button_link = "https://" + button_link
            
            # Choose button text based on source
            button_text = "📖 Source"
            if "wikipedia" in button_link.lower():
                button_text = "📖 Wikipedia"
            elif "wikiquote" in button_link.lower():
                button_text = "📖 Wikiquote"
            
            inline_keyboard = [[Button.url(button_text, button_link)]]
        
        return message, inline_keyboard
    
    async def _post_africa_content(self):
        """Post Africa exploration content."""
        if not self.africa_service:
            logger.warning("Africa service not available")
            return
        
        try:
            # Get used countries to avoid repetition
            used_countries = self.db.get_used_africa_countries(days=30)
            
            # Generate Africa content
            content = self.africa_service.generate_africa_post(used_countries)
            
            if not content:
                logger.error("Failed to generate Africa content")
                return
            
            # Format message
            message, inline_keyboard = self._format_africa_message(content)
            
            # Get image for the country or city
            image_url = None
            country = content.get("country", "")
            cities = content.get("cities", [])
            
            # Try to get image for the first city, fallback to country
            if cities and len(cities) > 0:
                city = cities[0]
                image_url = await self._get_city_image(city, country)
            
            # Fallback to country image if city image not found
            if not image_url and country:
                image_url = await self._get_country_image(country)
            
            # Post to group/channel with inline keyboard
            await self._post_to_channel(message, image_url, None, None, inline_keyboard)
            
            # Save to database
            self.db.record_africa_post(content)
            
            # Record country usage
            if country:
                self.db.record_africa_country(country)
            
        except Exception as e:
            logger.error(f"Error posting Africa content: {e}", exc_info=True)
    
    async def _get_country_image(self, country_name: str, prefer_nature: bool = False) -> Optional[str]:
        """Get image URL for a country."""
        unsplash_key = os.getenv("UNSPLASH_ACCESS_KEY", "")
        if not unsplash_key:
            logger.debug("Unsplash API key not set, skipping image fetch")
            return None
        
        try:
            async with httpx.AsyncClient() as client:
                url = "https://api.unsplash.com/search/photos"
                
                if prefer_nature:
                    queries = [
                        f"{country_name} nature landscape",
                        f"{country_name} nature scenery",
                        f"{country_name} natural landscape",
                        f"{country_name} landscape",
                    ]
                else:
                    queries = [
                        f"{country_name} landscape",
                        f"{country_name} nature",
                        f"{country_name}",
                    ]
                
                for query in queries:
                    params = {
                        "query": query,
                        "per_page": 10,
                        "orientation": "landscape",
                        "order_by": "relevance"
                    }
                    headers = {
                        "Authorization": f"Client-ID {unsplash_key}"
                    }
                    
                    response = await client.get(url, params=params, headers=headers, timeout=10.0)
                    response.raise_for_status()
                    data = response.json()
                    
                    if data.get("results") and len(data["results"]) > 0:
                        # Try to find image that matches country name
                        country_name_lower = country_name.lower()
                        for photo in data["results"]:
                            desc = (photo.get("description", "") or "") + " " + (photo.get("alt_description", "") or "")
                            desc_lower = desc.lower()
                            if country_name_lower in desc_lower or any(word in desc_lower for word in country_name_lower.split()):
                                image_url = photo["urls"]["regular"]
                                return image_url
                        
                        # Fallback to first result
                        image_url = data["results"][0]["urls"]["regular"]
                        return image_url
                
                return None
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                logger.warning("Unsplash API key invalid or expired. Posts will work without images.")
            else:
                logger.warning(f"Unsplash API error: {e}. Posts will work without images.")
        except Exception as e:
            logger.debug(f"Error fetching from Unsplash: {e}")
        
        return None
    
    async def _get_city_image(self, city_name: str, country_name: str = "") -> Optional[str]:
        """Get image URL for a city. Prioritizes city-specific images."""
        unsplash_key = os.getenv("UNSPLASH_ACCESS_KEY", "")
        if not unsplash_key:
            logger.debug("Unsplash API key not set, skipping image fetch")
            return None
        
        try:
            async with httpx.AsyncClient() as client:
                url = "https://api.unsplash.com/search/photos"
                
                # Try multiple query strategies for better city images
                queries = [
                    f"{city_name} {country_name} city" if country_name else f"{city_name} city",
                    f"{city_name} {country_name} landscape" if country_name else f"{city_name} landscape",
                    f"{city_name} {country_name}" if country_name else f"{city_name}",
                ]
                
                for query in queries:
                    params = {
                        "query": query,
                        "per_page": 10,
                        "orientation": "landscape",
                        "order_by": "relevance"
                    }
                    headers = {
                        "Authorization": f"Client-ID {unsplash_key}"
                    }
                    
                    response = await client.get(url, params=params, headers=headers, timeout=10.0)
                    response.raise_for_status()
                    data = response.json()
                    
                    results = data.get("results", [])
                    if results:
                        # Try to find image that matches city name
                        city_name_lower = city_name.lower()
                        for photo in results:
                            desc = (photo.get("description", "") or "") + " " + (photo.get("alt_description", "") or "")
                            desc_lower = desc.lower()
                            if city_name_lower in desc_lower or any(word in desc_lower for word in city_name_lower.split()):
                                image_url = photo.get("urls", {}).get("regular")
                                if image_url:
                                    logger.debug(f"Found city image for {city_name}: {image_url[:50]}...")
                                    return image_url
                        
                        # Fallback to first result
                        image_url = results[0].get("urls", {}).get("regular")
                        if image_url:
                            logger.debug(f"Using first result for {city_name}")
                            return image_url
                
                logger.debug(f"No city image found for {city_name}")
                return None
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                logger.warning("Unsplash API key invalid or expired. Posts will work without images.")
            else:
                logger.warning(f"Unsplash API error: {e}. Posts will work without images.")
        except Exception as e:
            logger.debug(f"Error fetching city image from Unsplash: {e}")
        
        return None
    
    def _format_africa_message(self, content: dict) -> tuple:
        """Format Africa exploration message. Returns (message_text, inline_keyboard)."""
        country = content.get("country", "")
        capital = content.get("capital", "")
        cities = content.get("cities", [])
        places = content.get("places", [])
        best_time = content.get("best_time", "")
        activities = content.get("activities", [])
        cultural_fact = content.get("cultural_fact", "")
        wildlife_fact = content.get("wildlife_fact", "")
        historical_fact = content.get("historical_fact", "")
        resource_link = content.get("resource_link", "")
        
        # Build compact message
        message = f"🌍 **{country}**"
        if capital:
            message += f" ({capital})"
        message += "\n\n"
        
        # Cities (compact)
        if cities:
            message += f"🏙️ {', '.join(cities[:3])}\n\n"
        
        # Places (max 2, no emoji)
        if places:
            for place in places[:2]:
                place_name = place.get("name", "")
                if place_name:
                    message += f"{place_name}\n"
            message += "\n"
        
        # Best time + Activities (combined, compact, no emoji for activities)
        if best_time or activities:
            if best_time:
                message += f"📅 {best_time}"
            if activities:
                activities_list = " • ".join(activities[:2])
                if best_time:
                    message += f" | {activities_list}"
                else:
                    message += f"{activities_list}"
            message += "\n\n"
        
        # Facts (compact, 1 sentence each)
        facts = []
        if cultural_fact:
            # Shorten fact to 1 sentence if longer
            fact = cultural_fact.split('.')[0] + '.' if '.' in cultural_fact else cultural_fact[:100]
            facts.append(f"🎭 {fact}")
        if wildlife_fact:
            fact = wildlife_fact.split('.')[0] + '.' if '.' in wildlife_fact else wildlife_fact[:100]
            facts.append(f"🦁 {fact}")
        if historical_fact:
            fact = historical_fact.split('.')[0] + '.' if '.' in historical_fact else historical_fact[:100]
            facts.append(f"📜 {fact}")
        
        if facts:
            for fact in facts:
                message += f"{fact}\n"
            message += "\n"
        
        # Source link
        if resource_link:
            # Ensure link has protocol
            if not resource_link.startswith(("http://", "https://")):
                resource_link = "https://" + resource_link
            
            try:
                from urllib.parse import urlparse
                parsed_url = urlparse(resource_link)
                domain = parsed_url.netloc.replace("www.", "")
                if not domain:
                    domain = resource_link.replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0]
                if len(domain) > 30:
                    domain = domain[:27] + "..."
                message += f"**Source:** [{domain}]({resource_link})\n\n"
            except:
                message += f"**Source:** {resource_link}\n\n"
        
        # Tags
        tags = ["#Africa", "#Exploration", "#Travel"]
        if country:
            tags.append("#" + country.replace(" ", ""))
        message += " ".join(tags)
        
        # Create inline keyboard for source
        inline_keyboard = None
        if resource_link:
            button_link = resource_link
            if not button_link.startswith(("http://", "https://")):
                button_link = "https://" + button_link
            inline_keyboard = [[Button.url("Source", button_link)]]
        
        return message, inline_keyboard
    
    async def _post_london_content(self):
        """Post Canary Wharf content with events."""
        if not self.london_service:
            logger.warning("Canary Wharf service not available")
            return
        
        try:
            # Get used topics to avoid repetition
            used_topics = []  # Could track topics if needed
            
            # Generate Canary Wharf content
            content = self.london_service.generate_london_post(used_topics)
            
            if not content:
                logger.error("Failed to generate Canary Wharf content")
                return
            
            # Format message
            message, inline_keyboard = self._format_london_message(content)
            
            # Get image for Canary Wharf using the search term from content
            image_search_term = content.get("image_search_term", "Canary Wharf London skyline")
            logger.info(f"🖼️ Fetching image for: {image_search_term}")
            image_url = await self._get_country_image(image_search_term)
            
            # Post to group/channel with inline keyboard
            await self._post_to_channel(message, image_url, None, None, inline_keyboard)
            
            # Save to database
            self.db.record_london_post(content)
            
        except Exception as e:
            logger.error(f"Error posting Canary Wharf content: {e}", exc_info=True)
    
    def _format_london_message(self, content: dict) -> tuple:
        """Format Canary Wharf post message with events. Returns (message_text, inline_keyboard)."""
        events = content.get("events", [])
        canary_wharf_fact = content.get("canary_wharf_fact", "")
        resource_link = content.get("resource_link", "")
        
        message = "🏢 **Canary Wharf, London**\n\n"
        
        # Upcoming events
        if events:
            message += "🎉 **Upcoming Events:**\n"
            for event in events[:2]:  # Max 2 events
                event_name = event.get("name", "")
                event_date = event.get("date", "")
                event_desc = event.get("description", "")
                if event_name:
                    message += f"🗓️ **{event_name}**"
                    if event_date:
                        message += f" ({event_date})"
                    message += "\n"
                    if event_desc:
                        message += f"   {event_desc}\n"
            message += "\n"
        
        # Fact about Canary Wharf
        if canary_wharf_fact:
            message += f"💡 **Did you know?**\n{canary_wharf_fact}\n\n"
        
        # Source link
        if resource_link:
            if not resource_link.startswith(("http://", "https://")):
                resource_link = "https://" + resource_link
            
            try:
                from urllib.parse import urlparse
                parsed_url = urlparse(resource_link)
                domain = parsed_url.netloc.replace("www.", "")
                if not domain:
                    domain = resource_link.replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0]
                if len(domain) > 30:
                    domain = domain[:27] + "..."
                message += f"🌐 **More info:** [{domain}]({resource_link})\n\n"
            except:
                message += f"🌐 **More info:** {resource_link}\n\n"
        
        # Tags
        message += "#CanaryWharf\n"
        
        # Create inline keyboard for source
        inline_keyboard = None
        if resource_link:
            button_link = resource_link
            if not button_link.startswith(("http://", "https://")):
                button_link = "https://" + button_link
            inline_keyboard = [[Button.url("Visit Website", button_link)]]
        
        return message, inline_keyboard
    
    async def _post_uk_content(self):
        """Post UK content."""
        if not self.uk_service:
            logger.warning("UK service not available")
            return
        
        try:
            # Get used cities to avoid repetition
            used_cities = self.db.get_used_uk_cities(days=30)
            
            # Generate UK content
            content = self.uk_service.generate_uk_post(used_cities)
            
            if not content:
                logger.error("Failed to generate UK content")
                return
            
            # Format message
            message, inline_keyboard = self._format_uk_message(content)
            
            # Get image for UK - use first city if available, fallback to "United Kingdom"
            # Track used images to avoid repetition
            used_images = self.db.get_used_uk_images(days=7)
            image_url = None
            image_location = None
            cities_data = content.get("cities", [])
            
            # Try to get image for the first city (if not used recently)
            if cities_data and len(cities_data) > 0:
                # Handle both new format (dict) and old format (string)
                if isinstance(cities_data[0], dict):
                    city_name = cities_data[0].get("name", "")
                else:
                    city_name = cities_data[0]
                
                if city_name and city_name not in used_images:
                    # Try city image first
                    image_url = await self._get_city_image(city_name, "United Kingdom")
                    if image_url:
                        image_location = city_name
            
            # Fallback to country image if city image not found or was used recently
            if not image_url and "United Kingdom" not in used_images:
                image_url = await self._get_country_image("United Kingdom")
                if image_url:
                    image_location = "United Kingdom"
            
            # Record image usage
            if image_location:
                self.db.record_uk_image(image_location)
            
            # Post to group/channel with inline keyboard
            await self._post_to_channel(message, image_url, None, None, inline_keyboard)
            
            # Save to database
            self.db.record_uk_post(content)
            
            # Record city usage
            cities_data = content.get("cities", [])
            for city in cities_data:
                # Handle both new format (dict) and old format (string)
                if isinstance(city, dict):
                    city_name = city.get("name", "")
                else:
                    city_name = city
                if city_name:
                    self.db.record_uk_city(city_name)
            
        except Exception as e:
            logger.error(f"Error posting UK content: {e}", exc_info=True)
    
    def _format_uk_message(self, content: dict) -> tuple:
        """Format UK post message. Returns (message_text, inline_keyboard)."""
        cities_data = content.get("cities", [])
        uk_fact = content.get("uk_fact", "")
        resource_link = content.get("resource_link", "")
        
        message = "🇬🇧 **United Kingdom**\n\n"
        
        # Cities - check if it's new format (list of dicts) or old format (list of strings)
        if cities_data:
            # Check if first item is dict (new format) or string (old format)
            if isinstance(cities_data[0], dict):
                # New format: list of city objects
                city_names = [city.get("name", "") for city in cities_data if city.get("name")]
                message += f"🏙️ {', '.join(city_names)}\n\n"
                
                # Add details for each city
                for city in cities_data:
                    city_name = city.get("name", "")
                    distance = city.get("distance_from_london", "")
                    travel_time = city.get("travel_time", "")
                    why_visit = city.get("why_visit", "")
                    
                    if city_name:
                        message += f"**{city_name}**\n"
                        if distance and travel_time:
                            message += f"📍 {distance} from London • {travel_time}\n"
                        if why_visit:
                            message += f"💡 {why_visit}\n"
                        message += "\n"
            else:
                # Old format: list of strings (backward compatibility)
                message += f"🏙️ {', '.join(cities_data)}\n\n"
        
        # UK fact
        if uk_fact:
            message += f"💡 **UK Fact:** {uk_fact}\n\n"
        
        # Source link
        if resource_link:
            if not resource_link.startswith(("http://", "https://")):
                resource_link = "https://" + resource_link
            
            try:
                from urllib.parse import urlparse
                parsed_url = urlparse(resource_link)
                domain = parsed_url.netloc.replace("www.", "")
                if not domain:
                    domain = resource_link.replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0]
                if len(domain) > 30:
                    domain = domain[:27] + "..."
                message += f"**Source:** [{domain}]({resource_link})\n\n"
            except:
                message += f"**Source:** {resource_link}\n\n"
        
        # Tags
        message += "#UK #Travel #Cities\n"
        
        # Create inline keyboard for source
        inline_keyboard = None
        if resource_link:
            button_link = resource_link
            if not button_link.startswith(("http://", "https://")):
                button_link = "https://" + button_link
            inline_keyboard = [[Button.url("Source", button_link)]]
        
        return message, inline_keyboard
    
    async def _post_job_content(self):
        """Post job vacancies content."""
        if not self.job_service:
            logger.warning("Job service not available")
            return
        
        try:
            # Get used companies to avoid repetition
            used_companies = self.db.get_used_job_companies(days=30)
            
            # Generate job content
            content = self.job_service.generate_job_post(used_companies)
            
            if not content:
                logger.error("Failed to generate job content")
                return
            
            # Format message
            message, inline_keyboard = self._format_job_message(content)
            
            # Post to group/channel with inline keyboard
            await self._post_to_channel(message, None, None, None, inline_keyboard)
            
            # Save to database
            self.db.record_job_post(content)
            
            # Record company usage
            vacancies = content.get("vacancies", [])
            for vacancy in vacancies:
                company = vacancy.get("company", "")
                if company:
                    self.db.record_job_company(company)
            
        except Exception as e:
            logger.error(f"Error posting job content: {e}", exc_info=True)
    
    async def _post_weather_content(self):
        """Post weather forecast content."""
        if not self.weather_service:
            logger.warning("Weather service not available")
            return
        
        try:
            # Generate weather content
            content = await self.weather_service.generate_weather_post()
            
            if not content:
                logger.error("Failed to generate weather content")
                return
            
            # Format message
            message = self._format_weather_message(content)
            
            # Post to group/channel
            await self._post_to_channel(message, None, None, None, None)
            
            # Save to database (if needed)
            # self.db.record_weather_post(content)
            
        except Exception as e:
            logger.error(f"Error posting weather content: {e}", exc_info=True)
    
    def _format_weather_message(self, content: dict) -> str:
        """Format weather forecast message.
        
        Pattern: Current temp with day/night range, grouped by country.
        Example:
            🌤️ Weather | 15 Jan 2026
            
            ☁️ UK
            London: 4°C (↑6/↓2°C)
            
            ❄️ Ukraine
            Bila Tserkva: -12°C (↑-8/↓-15°C)
            Poltava: -13°C (↑-10/↓-16°C)
            
            🌐 Full forecast: openweathermap.org
        """
        weather_data = content.get("weather", [])
        date = content.get("date", "")
        
        # Header with compact date
        from datetime import datetime
        if date:
            try:
                date_obj = datetime.strptime(date, "%Y-%m-%d")
                date_str = date_obj.strftime("%d %b %Y")
            except:
                date_str = date
        else:
            date_str = datetime.now().strftime("%d %b %Y")
        
        message = f"🌤️ Weather | {date_str}\n\n"
        
        # Group cities by country (with emoji)
        by_country = {}
        city_links = {}  # Store city -> OpenWeather link mapping
        
        for city_weather in weather_data:
            city = city_weather.get("city", "")
            country = city_weather.get("country", "")
            emoji = city_weather.get("emoji", "☀️")
            
            # Get temperature data (new format with current temp)
            temp_current = city_weather.get("temp_current")
            temp_max = city_weather.get("temp_max")
            temp_min = city_weather.get("temp_min")
            
            # Fallback to old format if new format not available
            if temp_current is None:
                temp_current = city_weather.get("temp_avg", 0)
            if temp_max is None:
                temp_max = city_weather.get("temp_day", 0)
            if temp_min is None:
                temp_min = city_weather.get("temp_night", 0)
            
            if city and country:
                if country not in by_country:
                    by_country[country] = {"cities": []}
                by_country[country]["cities"].append({
                    "city": city,
                    "emoji": emoji,  # Each city has its own weather emoji
                    "temp_current": temp_current,
                    "temp_max": temp_max,
                    "temp_min": temp_min
                })
                
                # Generate OpenWeather link for each city
                # Format: city name with spaces replaced by dashes, lowercase
                city_slug = city.lower().replace(" ", "-")
                city_links[city] = f"https://openweathermap.org/city/{city_slug}"
        
        # Format blocks by country with weather emoji per city
        for country, data in by_country.items():
            cities = data["cities"]
            
            # Country name (no emoji here, each city has its own)
            message += f"📍 {country}\n"
            
            for city_data in cities:
                city = city_data["city"]
                emoji = city_data.get("emoji", "☀️")
                temp_current = city_data.get("temp_current", 0)
                temp_max = city_data.get("temp_max", 0)
                temp_min = city_data.get("temp_min", 0)
                
                # Format: Emoji + City + Current temp with day/night range
                # Example: "❄️ London: 6°C (↑8/↓3°C)"
                message += f"{emoji} {city}: {temp_current}°C (↑{temp_max}/↓{temp_min}°C)\n"
            
            message += "\n"
        
        # Add OpenWeather links at the end
        message += "🌐 **Full forecast:**\n"
        message += "[OpenWeatherMap](https://openweathermap.org)\n"
        
        # Add tag
        message += "\n#Weather"
        
        return message
    
    def _format_job_message(self, content: dict) -> tuple:
        """Format job vacancies message. Returns (message_text, inline_keyboard)."""
        vacancies = content.get("vacancies", [])
        
        message = "💼 **Job Vacancies - Canary Wharf, London**\n\n"
        message += "✨ Your dream job is waiting! 💪\n\n"
        
        # Format each vacancy
        buttons = []
        for idx, vacancy in enumerate(vacancies[:3], 1):  # Max 3 vacancies
            company = vacancy.get("company", "")
            job_title = vacancy.get("job_title", "")
            location = vacancy.get("location", "")
            salary = vacancy.get("salary", "")
            company_rating = vacancy.get("company_rating", "")
            description = vacancy.get("description", "")
            requirements = vacancy.get("requirements", [])
            linkedin_url = vacancy.get("linkedin_url", "")
            
            message += f"**{idx}. {job_title}**\n"
            message += f"🏢 **Company:** {company}"
            if company_rating:
                message += f" ⭐ {company_rating}"
            message += "\n"
            message += f"📍 **Location:** {location}\n"
            message += f"💰 **Salary:** {salary}\n"
            
            if description:
                # Shorten "As a..." phrase - make it 3x shorter
                desc_lines = description.split(".")
                if desc_lines and desc_lines[0].strip():
                    # Take only first sentence and shorten it
                    first_sentence = desc_lines[0].strip()
                    # If it starts with "As a", make it very concise
                    if first_sentence.lower().startswith("as a"):
                        # Extract role and key responsibility only
                        words = first_sentence.split()
                        # Aim for ~1/3 of original length
                        max_words = max(8, len(words) // 3)
                        shortened = " ".join(words[:max_words])
                        if not shortened.endswith(('.', '!', '?')):
                            shortened += "."
                        message += f"\n📝 {shortened}\n"
                    else:
                        # For non "As a" descriptions, keep first sentence
                        message += f"\n📝 {first_sentence}.\n"
            
            if requirements:
                # Combine all requirements into ONE sentence
                req_text = ", ".join(requirements[:3])  # Use max 3 requirements
                message += f"\n**Requirements:** {req_text}\n"
            
            # Add LinkedIn link in text and button
            if linkedin_url:
                # Ensure link has protocol
                if not linkedin_url.startswith(("http://", "https://")):
                    linkedin_url = "https://" + linkedin_url
                
                # Add link in text
                try:
                    from urllib.parse import urlparse
                    parsed_url = urlparse(linkedin_url)
                    domain = parsed_url.netloc.replace("www.", "")
                    if not domain:
                        domain = linkedin_url.replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0]
                    if len(domain) > 30:
                        domain = domain[:27] + "..."
                    message += f"\n🔗 **Apply on LinkedIn:** [{domain}]({linkedin_url})\n"
                except:
                    message += f"\n🔗 **Apply on LinkedIn:** {linkedin_url}\n"
                
                # Add button
                buttons.append([Button.url(f"Apply - {company}", linkedin_url)])
            
            message += "\n" + "─" * 30 + "\n\n"
        
        # Single tag related to jobs
        message += "#Jobs\n"
        
        # Create inline keyboard with all LinkedIn buttons
        inline_keyboard = buttons if buttons else None
        
        return message, inline_keyboard
    
    async def _post_person_content(self):
        """Post famous person content."""
        if not self.person_service:
            logger.warning("Person service not available")
            return
        
        try:
            # Get used persons to avoid repetition
            used_persons = self.db.get_used_persons(days=30)
            
            # Get last 3 posts to check distribution
            last_posts = self.db.get_last_person_posts(count=3)
            
            # Generate content with distribution requirements
            content = self.person_service.generate_person_post(used_persons, last_posts)
            
            if not content:
                logger.error("Failed to generate person content")
                return
            
            # Format message (returns message and inline_keyboard)
            message, inline_keyboard = self._format_person_message(content)
            
            # Get image for the person
            image_url = None
            person_name = content.get("person_name", "")
            if person_name:
                image_url = await self._get_person_image(person_name)
            
            # Post to group/channel with inline keyboard
            await self._post_to_channel(message, image_url, None, None, inline_keyboard)
            
            # Save to database
            self.db.record_person_post(content)
            
            # Record person usage
            if person_name:
                self.db.record_person(person_name)
            
            
        except Exception as e:
            logger.error(f"Error posting person content: {e}", exc_info=True)
    
    async def _get_person_image(self, person_name: str) -> Optional[str]:
        """Get image URL for a famous person from verified sources (Wikipedia/Wikimedia Commons first, then Unsplash as fallback)."""
        # First, try Wikipedia/Wikimedia Commons (verified source)
        wikipedia_image = await self._get_person_image_from_wikipedia(person_name)
        if wikipedia_image:
            logger.debug(f"Found Wikipedia image for {person_name}")
            return wikipedia_image
        
        # Fallback to Unsplash if Wikipedia doesn't have image
        logger.debug(f"Wikipedia image not found for {person_name}, trying Unsplash...")
        return await self._get_person_image_from_unsplash(person_name)
    
    async def _get_person_image_from_wikipedia(self, person_name: str) -> Optional[str]:
        """Get person image from Wikipedia/Wikimedia Commons (verified source)."""
        try:
            async with httpx.AsyncClient() as client:
                # Step 1: Search for Wikipedia page
                search_url = "https://en.wikipedia.org/api/rest_v1/page/summary"
                # URL encode person name
                from urllib.parse import quote
                encoded_name = quote(person_name.replace(" ", "_"))
                
                try:
                    response = await client.get(f"{search_url}/{encoded_name}", timeout=10.0)
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Check if page has an image
                        # Try originalimage first (larger, better quality)
                        if "originalimage" in data and "source" in data["originalimage"]:
                            image_url = data["originalimage"]["source"]
                        elif "thumbnail" in data and "source" in data["thumbnail"]:
                            image_url = data["thumbnail"]["source"]
                        else:
                            image_url = None
                        
                        if image_url:
                            # Ensure it's a full URL
                            if image_url.startswith("//"):
                                image_url = "https:" + image_url
                            elif not image_url.startswith("http"):
                                image_url = "https://" + image_url
                            
                            logger.debug(f"Found Wikipedia image for {person_name}: {image_url[:50]}...")
                            return image_url
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 404:
                        logger.debug(f"Wikipedia page not found for {person_name}")
                    else:
                        logger.debug(f"Wikipedia API error for {person_name}: {e}")
                except Exception as e:
                    logger.debug(f"Error fetching from Wikipedia for {person_name}: {e}")
                
                # Step 2: Try Wikimedia Commons search
                commons_url = "https://commons.wikimedia.org/w/api.php"
                params = {
                    "action": "query",
                    "format": "json",
                    "titles": person_name,
                    "prop": "pageimages",
                    "pithumbsize": "800",
                    "piprop": "thumbnail"
                }
                
                try:
                    response = await client.get(commons_url, params=params, timeout=10.0)
                    if response.status_code == 200:
                        data = response.json()
                        pages = data.get("query", {}).get("pages", {})
                        for page_id, page_data in pages.items():
                            if "thumbnail" in page_data:
                                image_url = page_data["thumbnail"]["source"]
                                if image_url.startswith("//"):
                                    image_url = "https:" + image_url
                                logger.debug(f"Found Wikimedia Commons image for {person_name}")
                                return image_url
                except Exception as e:
                    logger.debug(f"Error fetching from Wikimedia Commons for {person_name}: {e}")
                
        except Exception as e:
            logger.debug(f"Error in Wikipedia/Wikimedia Commons search for {person_name}: {e}")
        
        return None
    
    async def _get_person_image_from_unsplash(self, person_name: str) -> Optional[str]:
        """Get person image from Unsplash (fallback, less reliable)."""
        unsplash_key = os.getenv("UNSPLASH_ACCESS_KEY", "")
        if not unsplash_key:
            logger.debug("Unsplash API key not set, skipping image fetch")
            return None
        
        try:
            async with httpx.AsyncClient() as client:
                url = "https://api.unsplash.com/search/photos"
                
                # Try multiple query strategies for better results
                queries = [
                    f"{person_name} portrait official",
                    f"{person_name} scientist inventor engineer portrait",
                    f"{person_name} portrait",
                ]
                
                for query in queries:
                    params = {
                        "query": query,
                        "per_page": 20,
                        "orientation": "portrait",
                        "order_by": "relevance"
                    }
                    headers = {
                        "Authorization": f"Client-ID {unsplash_key}"
                    }
                    
                    response = await client.get(url, params=params, headers=headers, timeout=10.0)
                    response.raise_for_status()
                    data = response.json()
                    
                    if data.get("results") and len(data["results"]) > 0:
                        person_name_lower = person_name.lower()
                        person_words = person_name_lower.split()
                        first_name = person_words[0] if person_words else ""
                        last_name = person_words[-1] if len(person_words) > 1 else ""
                        
                        # Filter out common false matches (rappers, celebrities)
                        exclude_keywords = ["rapper", "hip hop", "music", "singer", "celebrity", "entertainer", "actor", "actress"]
                        
                        # Try to find image that matches person name in description/tags
                        for photo in data["results"]:
                            desc = photo.get("description") or ""
                            alt_desc = photo.get("alt_description") or ""
                            tags_text = " ".join([tag.get("title", "") or "" for tag in photo.get("tags", []) if tag])
                            description = (desc + " " + alt_desc + " " + tags_text).lower()
                            
                            # Skip if contains exclude keywords
                            if any(keyword in description for keyword in exclude_keywords):
                                continue
                            
                            # Check if person name appears in description (both first and last name for better match)
                            if first_name and last_name:
                                if (first_name in description and last_name in description):
                                    image_url = photo["urls"]["regular"]
                                    logger.debug(f"Found Unsplash image for {person_name} (matched name)")
                                    return image_url
                            elif first_name:
                                if first_name in description:
                                    # Additional check: make sure it's not a generic match
                                    if any(word in description for word in ["portrait", "photo", "picture", "person", "official"]):
                                        image_url = photo["urls"]["regular"]
                                        logger.debug(f"Found Unsplash image for {person_name} (matched with keywords)")
                                        return image_url
                        
                        # Last fallback: first result (if we have results) - but log warning
                        logger.warning(f"Using Unsplash fallback image for {person_name} - may not be accurate")
                        image_url = data["results"][0]["urls"]["regular"]
                        return image_url
                
                # If no results from any query
                return None
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                logger.warning("Unsplash API key invalid or expired. Posts will work without images.")
            else:
                logger.warning(f"Unsplash API error: {e}. Posts will work without images.")
        except Exception as e:
            logger.debug(f"Error fetching from Unsplash: {e}")
        
        return None
    
    def _format_person_message(self, content: dict) -> tuple:
        """Format famous person message. Returns (message_text, inline_keyboard)."""
        person_name = content.get("person_name", "Famous Person")
        one_line_description = content.get("one_line_description", "")
        birth_year = content.get("birth_year", "")
        death_year = content.get("death_year", "")
        nationality = content.get("nationality", "Unknown")
        category = content.get("category", "inventor")
        contribution_name = content.get("contribution_name", content.get("main_invention", ""))
        contribution_label = content.get("contribution_label", "Main Invention")
        key_facts = content.get("key_facts", [])
        why_it_matters = content.get("why_it_matters", content.get("invention_description", ""))
        fun_fact = content.get("fun_fact", content.get("tricky_fact", ""))
        resource_link = content.get("resource_link", "")
        
        # Build message - compact structure, scannable in 2 seconds
        # Block 1: Name + one-line description
        message = f"**{person_name}**"
        if one_line_description:
            message += f"\n{one_line_description}"
        message += "\n\n"
        
        # Block 2: Key facts (3-5 bullets)
        if key_facts:
            for fact in key_facts[:5]:  # Max 5 facts
                message += f"• {fact}\n"
            message += "\n"
        
        # Block 3: Why it matters (1-2 sentences)
        if why_it_matters:
            # Ensure max 2 sentences
            sentences = [s.strip() for s in why_it_matters.split('.') if s.strip()]
            why_text = '. '.join(sentences[:2])  # Max 2 sentences
            if why_text and not why_text.endswith('.'):
                why_text += '.'
            message += f"**Why it matters:** {why_text}\n\n"
        
        # Block 4: Fun fact (1 sentence)
        if fun_fact:
            # Ensure 1 sentence only
            fact_text = fun_fact.strip()
            # Take first sentence only
            if '.' in fact_text:
                fact_text = fact_text.split('.')[0] + '.'
            message += f"**Fun fact:** {fact_text}\n\n"
        
        # Block 5: Source link in text (short format)
        if resource_link:
            # Ensure link has protocol
            if not resource_link.startswith(("http://", "https://")):
                resource_link = "https://" + resource_link
            
            # Extract domain name for short display
            try:
                from urllib.parse import urlparse
                parsed_url = urlparse(resource_link)
                domain = parsed_url.netloc.replace("www.", "")
                if not domain:
                    # If parsing failed, try to extract from original link
                    domain = resource_link.replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0]
                # Shorten domain if too long
                if len(domain) > 30:
                    domain = domain[:27] + "..."
                message += f"**Source:** [{domain}]({resource_link})\n\n"
            except:
                # Fallback to full link if parsing fails
                message += f"**Source:** {resource_link}\n\n"
        
        # Minimal tags (2-3 max)
        tags = []
        # Use category in singular if needed
        category_singular = category.rstrip('s') if category.endswith('s') else category
        tags.append("#" + category_singular.replace(" ", "").replace("_", ""))
        if tags:
            message += " ".join(tags)
        
        # Create inline keyboard for source
        inline_keyboard = None
        if resource_link:
            # Ensure link has protocol for button too
            button_link = resource_link
            if not button_link.startswith(("http://", "https://")):
                button_link = "https://" + button_link
            inline_keyboard = [[Button.url("Source", button_link)]]
        
        return message, inline_keyboard
    
    async def _post_tech_content(self):
        """Post tech device content."""
        if not self.tech_service:
            logger.warning("Tech service not available")
            return
        
        try:
            logger.info("Generating tech device post...")
            
            # Get used devices and countries to avoid repetition
            used_devices = self.db.get_used_tech_devices(days=30)
            used_countries = self.db.get_used_tech_countries(days=30)
            
            # Generate content
            content = self.tech_service.generate_tech_post(used_devices, used_countries)
            
            if not content:
                logger.error("Failed to generate tech content")
                return
            
            # Format message (returns message and inline_keyboard)
            message, inline_keyboard = self._format_tech_message(content)
            
            # Get image for the device
            image_url = None
            device_name = content.get("device_name", "")
            manufacturer = content.get("manufacturer", "")
            if device_name:
                image_url = await self._get_device_image(device_name, manufacturer)
            
            # Post to group/channel with inline keyboard
            await self._post_to_channel(message, image_url, None, None, inline_keyboard)
            
            # Save to database
            self.db.record_tech_post(content)
            
            # Record device and country usage
            if device_name:
                self.db.record_tech_device(device_name)
            country = content.get("country", "")
            if country:
                self.db.record_tech_country(country)
            
            
        except Exception as e:
            logger.error(f"Error posting tech content: {e}", exc_info=True)
    
    async def _get_device_image(self, device_name: str, manufacturer: str = "") -> Optional[str]:
        """Get image URL for a tech device."""
        unsplash_key = os.getenv("UNSPLASH_ACCESS_KEY", "")
        if not unsplash_key:
            logger.debug("Unsplash API key not set, skipping image fetch")
            return None
        
        try:
            async with httpx.AsyncClient() as client:
                url = "https://api.unsplash.com/search/photos"
                
                # Try multiple query strategies for better results
                queries = [
                    f"{device_name} sensor device" if "sensor" in device_name.lower() else f"{device_name} device",
                    f"{manufacturer} {device_name}" if manufacturer else f"{device_name}",
                    f"{device_name} tech",
                ]
                
                for query in queries:
                    params = {
                        "query": query,
                        "per_page": 10,
                        "orientation": "landscape",
                        "order_by": "relevance"
                    }
                    headers = {
                        "Authorization": f"Client-ID {unsplash_key}"
                    }
                    
                    response = await client.get(url, params=params, headers=headers, timeout=10.0)
                    response.raise_for_status()
                    data = response.json()
                    
                    if data.get("results") and len(data["results"]) > 0:
                        # Try to find image that matches device name
                        device_name_lower = device_name.lower()
                        for photo in data["results"]:
                            desc = (photo.get("description", "") or "") + " " + (photo.get("alt_description", "") or "")
                            desc_lower = desc.lower()
                            # Check if device name or key words appear in description
                            if any(word in desc_lower for word in device_name_lower.split()[:2]):  # First 2 words
                                image_url = photo["urls"]["regular"]
                                return image_url
                        
                        # Fallback to first result
                        image_url = data["results"][0]["urls"]["regular"]
                        return image_url
                
                # If no results from any query
                return None
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                logger.warning("Unsplash API key invalid or expired. Posts will work without images.")
            else:
                logger.warning(f"Unsplash API error: {e}. Posts will work without images.")
        except Exception as e:
            logger.debug(f"Error fetching from Unsplash: {e}")
        
        return None
    
    def _format_tech_message(self, content: dict) -> tuple:
        """Format tech device message. Returns (message_text, inline_keyboard)."""
        device_name = content.get("device_name", "Tech Device")
        manufacturer = content.get("manufacturer", "Unknown")
        country = content.get("country", "Unknown")
        category = content.get("category", "device")
        device_type = content.get("type", "unique")
        year_created = content.get("year_created", "")
        key_features = content.get("key_features", [])
        what_it_does = content.get("what_it_does", content.get("overview", content.get("description", "")))
        resource_link = content.get("resource_link", "")
        
        # Build message - compact structure
        # Block 1: Title (name + category, no "Unique")
        category_short = category.split()[0] if category else "Device"
        message = f"**{device_name} ({category_short})**\n\n"
        
        # Block 2: Metadata (2-3 lines max, no emojis)
        metadata_parts = []
        if manufacturer and manufacturer != "Unknown":
            # Short country code if available
            country_code = ""
            if country == "USA":
                country_code = "US"
            elif country == "UK":
                country_code = "UK"
            elif len(country) <= 3:
                country_code = country
            else:
                # Get first letters or common abbreviation
                country_code = country[:2].upper() if len(country) > 2 else country.upper()
            
            metadata_parts.append(f"{manufacturer} ({country_code})")
        
        if year_created:
            metadata_parts.append(year_created)
        
        category_clean = category.replace("_", " ").title()
        if category_clean:
            metadata_parts.append(category_clean)
        
        if metadata_parts:
            message += " • ".join(metadata_parts) + "\n\n"
        
        # Block 3: What it does (1-2 sentences, no marketing)
        if what_it_does:
            # Ensure max 2 sentences
            sentences = [s.strip() for s in what_it_does.split('.') if s.strip()]
            what_text = '. '.join(sentences[:2])  # Max 2 sentences
            if what_text and not what_text.endswith('.'):
                what_text += '.'
            message += f"**What it does:** {what_text}\n\n"
        
        # Block 4: Key features (3-5, compact)
        if key_features:
            message += "**Key features:**\n"
            for feature in key_features[:5]:  # Max 5 features
                # Make features more compact
                feature_clean = feature.strip()
                if feature_clean:
                    message += f"• {feature_clean}\n"
            message += "\n"
        
        # Block 5: Source link in text (short format)
        if resource_link:
            # Ensure link has protocol
            if not resource_link.startswith(("http://", "https://")):
                resource_link = "https://" + resource_link
            
            # Extract domain name for short display
            try:
                from urllib.parse import urlparse
                parsed_url = urlparse(resource_link)
                domain = parsed_url.netloc.replace("www.", "")
                if not domain:
                    # If parsing failed, try to extract from original link
                    domain = resource_link.replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0]
                # Shorten domain if too long
                if len(domain) > 30:
                    domain = domain[:27] + "..."
                message += f"**Source:** [{domain}]({resource_link})\n\n"
            except:
                # Fallback to full link if parsing fails
                message += f"**Source:** {resource_link}\n\n"
        
        # Minimal tags (2-3 max)
        tags = []
        tags.append("#Engineering")
        tags.append("#Electronics")
        if tags:
            message += " ".join(tags)
        
        # Create inline keyboard for source
        inline_keyboard = None
        if resource_link:
            # Ensure link has protocol for button too
            button_link = resource_link
            if not button_link.startswith(("http://", "https://")):
                button_link = "https://" + button_link
            inline_keyboard = [[Button.url("Source", button_link)]]
        
        return message, inline_keyboard
    
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
    
    async def _post_to_channel(self, message: str, image_url: Optional[str] = None, country_name: Optional[str] = None, country_capital: Optional[str] = None, inline_keyboard: Optional[list] = None):
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
                    # Add User-Agent header to avoid 403 errors from image hosts
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                    }
                    async with httpx.AsyncClient() as client:
                        response = await client.get(image_url, headers=headers, timeout=10.0, follow_redirects=True)
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
                            parse_mode='md',
                            buttons=inline_keyboard
                        )
                        
                        logger.info("✅ Image sent successfully!")
                        
                        # Clean up
                        import os
                        os.unlink(tmp_path)
                        logger.debug("🗑️ Temp file deleted")
                except Exception as img_error:
                    logger.error(f"❌ Error sending image from {image_url[:100]}: {img_error}", exc_info=True)
                    logger.info(f"📝 Image error details: {type(img_error).__name__}: {str(img_error)}")
                    logger.info("📝 Falling back to text-only message")
                    # Fallback to text only
                    await self.client.send_message(
                        target,
                        message,
                        parse_mode='md',
                        buttons=inline_keyboard
                    )
                    logger.warning("⚠️ Posted without image due to download/send failure")
            else:
                logger.info("📝 No image URL, sending text-only message")
                # Send text only
                await self.client.send_message(
                    target,
                    message,
                    parse_mode='md',
                    buttons=inline_keyboard
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
                    parse_mode='md',
                    buttons=inline_keyboard
                )
                logger.info("✅ Posted text-only successfully")
            except Exception as e2:
                logger.error(f"Error posting text-only: {e2}")
                raise  # Re-raise to show in control handler