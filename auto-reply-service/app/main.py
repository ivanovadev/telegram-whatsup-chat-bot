"""Main file for Auto-Reply Service."""
import os
import asyncio
from dotenv import load_dotenv
from telethon import TelegramClient
from storage.db import Database
from services.budget_guard import BudgetGuard
from services.suggester import Suggester
from handlers.inbox import InboxHandler
from handlers.control import ControlHandler


# Load environment variables from service directory
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(env_path)


async def main():
    """Main function to start the auto-reply service."""
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
    
    # Create client
    client = TelegramClient(session_path, api_id, api_hash)
    
    print("🔌 Connecting to Telegram...")
    await client.start()
    
    if not await client.is_user_authorized():
        print("❌ Not authorized. Check session.")
        return
    
    me = await client.get_me()
    print(f"✅ Authorized as: {me.first_name} (@{me.username})")
    
    # Verify control chat access
    control_chat_id = os.getenv("CONTROL_CHAT_ID", "me")
    if control_chat_id != "me":
        try:
            control_id = int(control_chat_id)
            control_entity = await client.get_entity(control_id)
            print(f"✅ Control chat found: {getattr(control_entity, 'title', 'Unknown')}")
        except ValueError:
            # Try as username
            try:
                control_entity = await client.get_entity(control_chat_id)
                print(f"✅ Control chat found: {getattr(control_entity, 'title', 'Unknown')}")
            except Exception as e:
                print(f"⚠️  Warning: Cannot access control chat {control_chat_id}: {e}")
                print(f"💡 Make sure you've added your account to the channel as admin")
        except Exception as e:
            print(f"⚠️  Warning: Cannot access control chat {control_chat_id}: {e}")
            print(f"💡 Make sure you've added your account to the channel as admin")
    
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
    suggester = Suggester(budget_guard)
    
    # Create handlers
    inbox_handler = InboxHandler(client, db, suggester, budget_guard)
    control_handler = ControlHandler(
        client, db, suggester, budget_guard, inbox_handler, None
    )
    
    # Register handlers
    inbox_handler.register()
    control_handler.register()
    
    print("✅ Auto-Reply Service started! Waiting for messages...")
    print("💡 Write 'status' in control chat to check")
    
    # Check and send alerts
    await budget_guard.check_and_alert(client)
    
    # Run bot
    await client.run_until_disconnected()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Service stopped")
    except Exception as e:
        print(f"❌ Error: {e}")
