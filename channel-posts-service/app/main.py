"""Main file for Channel Posts Service (Production)."""
import os
import asyncio
from dotenv import load_dotenv
from telethon import TelegramClient
from storage.db import Database
from shared_services.channel_content import ChannelContentGenerator
from shared_services.image_service import ImageService
from neo4j_app.neo4j_service import Neo4jService
from neo4j_app.user_relationships import seed_example_social_graph
from services.channel_handler import ChannelHandler

# Load environment variables from service directory
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(env_path)

# Simple BudgetGuard for channel posts service
import os
class BudgetGuard:
    def __init__(self, db):
        self.db = db
        self.llm_enabled = os.getenv("LLM_ENABLED", "off").lower() == "on"
    def can_use_llm(self):
        return (self.llm_enabled, None)
    def record_llm_call(self, tokens, cost):
        pass


async def main():
    """Main function to start the channel posts service."""
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
    
    # Check if channel posts are enabled
    if os.getenv("CHANNEL_POSTS_ENABLED", "off").lower() != "on":
        print("❌ Channel posts disabled. Set CHANNEL_POSTS_ENABLED=on in .env")
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
    content_generator = ChannelContentGenerator(budget_guard)
    image_service = ImageService()
    
    # Initialize Neo4j
    neo4j = Neo4jService()
    if neo4j.enabled:
        print("✅ Neo4j graph database connected")
        # Always (re)seed demo social graph on service start (idempotent).
        print("🌱 Seeding example social graph into Neo4j...")
        seeded = seed_example_social_graph(neo4j)
        status = "done" if seeded else "skipped"
        print(f"🌱 Seed status: {status}")
    else:
        print("ℹ️  Neo4j is disabled (set NEO4J_ENABLED=on to enable)")
    
    # Create channel handler
    channel_handler = ChannelHandler(
        client, db, content_generator, image_service, neo4j
    )
    
    # Start scheduler
    await channel_handler.start_scheduler()
    
    print("✅ Channel Posts Service started! (Production)")
    print(f"📢 Morning posts at: {channel_handler.morning_time}")
    print(f"📢 Evening posts at: {channel_handler.evening_time}")
    
    # Run bot
    await client.run_until_disconnected()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Service stopped")
    except Exception as e:
        print(f"❌ Error: {e}")
