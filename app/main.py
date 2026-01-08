"""Main file for running Telegram userbot."""
import os
import asyncio
from dotenv import load_dotenv
from telethon import TelegramClient
from storage.db import Database
from services.budget_guard import BudgetGuard
from services.suggester import Suggester
from handlers.inbox import InboxHandler
from handlers.control import ControlHandler


# Load environment variables
load_dotenv()


async def main():
    """Main function to start the bot."""
    # Get credentials
    api_id = int(os.getenv("TG_API_ID", "0"))
    api_hash = os.getenv("TG_API_HASH", "")
    session_path = os.getenv("TG_SESSION_PATH", "./data/session.session")
    
    if not api_id or not api_hash:
        print("❌ Error: TG_API_ID and TG_API_HASH must be set in .env")
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
    db = Database()
    budget_guard = BudgetGuard(db)
    suggester = Suggester(budget_guard)
    
    # Create handlers
    inbox_handler = InboxHandler(client, db, suggester, budget_guard)
    control_handler = ControlHandler(
        client, db, suggester, budget_guard, inbox_handler
    )
    
    # Register handlers
    inbox_handler.register()
    control_handler.register()
    
    print("✅ Bot started! Waiting for messages...")
    print("💡 Write 'status' in control chat to check")
    
    # Check and send alerts
    await budget_guard.check_and_alert(client)
    
    # Run bot
    await client.run_until_disconnected()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot stopped")
    except Exception as e:
        print(f"❌ Error: {e}")
