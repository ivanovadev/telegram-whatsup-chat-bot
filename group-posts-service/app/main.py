"""Main file for Group Posts Service (Dev Environment)."""
import os
import asyncio
import logging
from dotenv import load_dotenv
from telethon import TelegramClient
from storage.db import Database
from content.channel_content import ChannelContentGenerator
from services.image_service import ImageService
from services.news_service import NewsService
from content.person_content import PersonContentGenerator
from content.tech_content import TechContentGenerator
from services.ukraine_news_service import UkraineNewsService
from content.spider_content import SpiderContentGenerator
from content.quote_content import QuoteContentGenerator
from content.africa_content import AfricaContentGenerator
from content.london_content import LondonContentGenerator
from content.uk_content import UKContentGenerator
from services.job_content import JobContentGenerator
from content.weather_content import WeatherContentGenerator
from services.channel_handler import ChannelHandler

# Import BudgetGuard and Neo4j from shared services
import sys
from pathlib import Path
# Add project root to path to import shared_services
service_dir = Path(__file__).parent.parent  # group-posts-service/
project_root = service_dir.parent  # telegram-whatsup-chat-bot/
sys.path.insert(0, str(project_root))
from shared_services.budget_guard import BudgetGuard
from shared_services.neo4j_service import Neo4jService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Load environment variables from service directory
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(env_path)


async def main():
    """Main function to start the group posts service."""
    # Get credentials
    api_id = int(os.getenv("TG_API_ID", "0"))
    api_hash = os.getenv("TG_API_HASH", "")
    # Use session path from env (can be relative or absolute)
    session_path = os.getenv("TG_SESSION_PATH", "./data/session.session")
    # If relative path starts with ../, resolve from service directory
    # Otherwise, if relative, resolve from service directory
    service_dir = os.path.dirname(os.path.dirname(__file__))
    if not os.path.isabs(session_path):
        # Handle ../ paths (go up from service directory)
        if session_path.startswith("../"):
            # Go up from service directory to project root
            project_root = os.path.dirname(service_dir)
            session_path = os.path.join(project_root, session_path[3:])
        else:
            # Relative to service directory
            session_path = os.path.join(service_dir, session_path.lstrip("./"))
    # Create data directory if needed
    os.makedirs(os.path.dirname(session_path), exist_ok=True)
    
    if not api_id or not api_hash:
        print("❌ Error: TG_API_ID and TG_API_HASH must be set in .env")
        return
    
    # Check if group posts are enabled
    if os.getenv("GROUP_POSTS_ENABLED", "off").lower() != "on":
        print("❌ Group posts disabled. Set GROUP_POSTS_ENABLED=on in .env")
        return
    
    # Create client
    client = TelegramClient(session_path, api_id, api_hash)
    
    print("🔌 Connecting to Telegram...")
    await client.start()
    
    if not await client.is_user_authorized():
        print("❌ Not authorized. Check session.")
        return
    
    me = await client.get_me()
    print(f"✅ Authorized as: {me.first_name} (@{me.username})")
    
    # Initialize components
    print("📦 Initializing components...")
    # Use database path from env (can be relative or absolute)
    service_dir = os.path.dirname(os.path.dirname(__file__))
    db_path = os.getenv("DB_PATH", "./data/bot.db")
    if not os.path.isabs(db_path):
        # Handle ../ paths (go up from service directory)
        if db_path.startswith("../"):
            # Go up from service directory to project root
            project_root = os.path.dirname(service_dir)
            db_path = os.path.join(project_root, db_path[3:])
        else:
            # Relative to service directory
            db_path = os.path.join(service_dir, db_path.lstrip("./"))
    print(f"📁 Using database: {db_path}")
    db = Database(db_path=db_path)
    budget_guard = BudgetGuard(db)
    
    # Check budget status
    status = budget_guard.get_status()
    print(f"💰 Budget status: ${status['estimated_usd']:.2f} / ${status['daily_budget']:.2f} USD")
    if not status['can_use_llm']:
        print(f"⚠️  LLM disabled: check settings or budget limits")
    
    content_generator = ChannelContentGenerator(budget_guard)
    image_service = ImageService()
    news_service = NewsService(budget_guard)
    person_service = PersonContentGenerator(budget_guard)
    tech_service = TechContentGenerator(budget_guard)
    ukraine_news_service = UkraineNewsService(budget_guard)
    spider_service = SpiderContentGenerator(budget_guard)
    quote_service = QuoteContentGenerator(budget_guard)
    africa_service = AfricaContentGenerator(budget_guard)
    london_service = LondonContentGenerator(budget_guard)
    uk_service = UKContentGenerator(budget_guard)
    job_service = JobContentGenerator(budget_guard)
    weather_service = WeatherContentGenerator(budget_guard)
    
    # Initialize Neo4j
    neo4j = Neo4jService()
    if neo4j.enabled:
        print("✅ Neo4j graph database connected")
    else:
        print("ℹ️  Neo4j is disabled (set NEO4J_ENABLED=on to enable)")
    
    # Create channel handler (works for groups too)
    channel_handler = ChannelHandler(
        client, db, content_generator, image_service, news_service, person_service, tech_service, ukraine_news_service, spider_service, quote_service, africa_service, london_service, uk_service, job_service, weather_service, neo4j
    )
    
    # Start scheduler
    await channel_handler.start_scheduler()
    
    # Check and send budget alerts
    await budget_guard.check_and_alert(client)
    
    print("✅ Group Posts Service started! (Dev Environment)")
    print("📅 Sequential Morning Schedule (10-minute intervals):")
    print(f"   08:10 - 📢 Travel (evening)")
    print(f"   08:20 - 🌅 Travel (morning)")
    print(f"   08:30 - 📰 News")
    print(f"   08:40 - 🔧 Tech")
    print(f"   08:50 - 👤 Person")
    print(f"   09:00 - 🇺🇦 Ukraine")
    print(f"   09:10 - 🕷️ Spider")
    print(f"   09:20 - 💬 Quote")
    print(f"   09:30 - 🌍 Africa")
    print(f"   09:40 - 🏢 Canary Wharf")
    print(f"   09:50 - 🇬🇧 UK")
    print(f"   10:00 - 💼 Job")
    print(f"   10:10 - 🌤️ Weather")
    
    # Run bot
    await client.run_until_disconnected()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Service stopped")
    except Exception as e:
        print(f"❌ Error: {e}")
