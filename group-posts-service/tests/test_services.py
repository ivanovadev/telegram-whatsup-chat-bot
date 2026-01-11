#!/usr/bin/env python3
"""Test script to run all service commands sequentially.

This script sends all service commands to the Telegram bot to test if everything works.
Make sure the bot is running before executing this script.

Usage:
    # Using venv (recommended):
    source venv/bin/activate
    python3 test_services.py              # Test all services
    python3 test_services.py travel        # Test specific service
    python3 test_services.py travel news   # Test multiple services
    
    # Or using run.sh (which activates venv):
    ./run.sh test_services.py
"""

import os
import sys
import asyncio
import time

# Try to load dotenv (optional)
try:
    from dotenv import load_dotenv
    # Look for .env in parent directory (group-posts-service/)
    script_dir = os.path.dirname(__file__)
    parent_dir = os.path.dirname(script_dir)
    env_path = os.path.join(parent_dir, '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
        print(f"✅ Loaded .env from: {env_path}")
    else:
        print(f"⚠️  .env file not found at: {env_path}")
        print("💡 Make sure .env exists in the group-posts-service/ directory")
except ImportError:
    # dotenv not available, will use system environment variables
    print("⚠️  python-dotenv not found. Using system environment variables.")
    print("💡 Install with: pip install python-dotenv")
except Exception as e:
    print(f"⚠️  Could not load .env file: {e}")
    print("💡 Will use system environment variables.")

try:
    from telethon import TelegramClient
except ImportError:
    print("❌ Error: telethon module not found.")
    print("💡 Install with: pip install telethon")
    sys.exit(1)

# All available service commands
ALL_SERVICE_COMMANDS = [
    "status",           # Budget and service status
    "travel",           # Evening travel post
    "travel morning",   # Morning travel post
    "news",
    "tech",
    "person",
    "ukraine",
    "spider",
    "quote",
    "africa",
    "london",
    "uk",
    "job",
    "weather"
]

# Delay between commands (in seconds)
# Increased to allow bot to process each command before next one
# Content generation can take 5-10 seconds, so we wait longer
DELAY_BETWEEN_COMMANDS = 15


async def send_command(client, command: str):
    """Send a command to Saved Messages."""
    try:
        print(f"📤 Sending command: '{command}'")
        await client.send_message("me", command)
        print(f"✅ Command '{command}' sent successfully")
        return True
    except Exception as e:
        print(f"❌ Error sending command '{command}': {e}")
        return False


async def test_services(commands_to_test):
    """Test services by sending commands sequentially."""
    # Get credentials
    api_id = int(os.getenv("TG_API_ID", "0"))
    api_hash = os.getenv("TG_API_HASH", "")
    # Use separate test session to avoid database lock conflicts
    session_path = os.getenv("TG_SESSION_PATH", "./data/session.session")
    test_session_path = session_path.replace(".session", "_test.session")
    
    # Resolve session path
    service_dir = os.path.dirname(__file__)
    if not os.path.isabs(test_session_path):
        if test_session_path.startswith("../"):
            project_root = os.path.dirname(service_dir)
            test_session_path = os.path.join(project_root, test_session_path[3:])
        else:
            test_session_path = os.path.join(service_dir, test_session_path.lstrip("./"))
    
    if not api_id or not api_hash:
        print("❌ Error: TG_API_ID and TG_API_HASH must be set in .env")
        return
    
    # Copy main session to test session if test session doesn't exist
    if not os.path.exists(test_session_path) and os.path.exists(session_path):
        service_dir = os.path.dirname(__file__)
        if not os.path.isabs(session_path):
            if session_path.startswith("../"):
                project_root = os.path.dirname(service_dir)
                session_path = os.path.join(project_root, session_path[3:])
            else:
                session_path = os.path.join(service_dir, session_path.lstrip("./"))
        import shutil
        shutil.copy(session_path, test_session_path)
        print(f"📋 Created test session from main session")
    
    # Validate commands
    invalid_commands = [cmd for cmd in commands_to_test if cmd not in ALL_SERVICE_COMMANDS]
    if invalid_commands:
        print(f"❌ Invalid commands: {', '.join(invalid_commands)}")
        print(f"📋 Available commands: {', '.join(ALL_SERVICE_COMMANDS)}")
        return
    
    # Create client
    client = TelegramClient(test_session_path, api_id, api_hash)
    print(f"🔧 Using test session: {test_session_path}")
    
    print("🔌 Connecting to Telegram...")
    await client.start()
    
    if not await client.is_user_authorized():
        print("❌ Not authorized. Check session.")
        return
    
    me = await client.get_me()
    print(f"✅ Authorized as: {me.first_name} (@{me.username})")
    print(f"\n🧪 Starting service tests...\n")
    print(f"📋 Will test {len(commands_to_test)} command(s)")
    print(f"⏱️  Delay between commands: {DELAY_BETWEEN_COMMANDS} seconds\n")
    print("=" * 60)
    
    # Test each command
    results = {}
    for idx, command in enumerate(commands_to_test, 1):
        print(f"\n[{idx}/{len(commands_to_test)}] Testing: '{command}'")
        print("-" * 60)
        
        success = await send_command(client, command)
        results[command] = success
        
        # Wait before next command (except for last one)
        # Give bot time to process the command and generate content
        if idx < len(commands_to_test):
            print(f"⏳ Waiting {DELAY_BETWEEN_COMMANDS} seconds for bot to process...")
            await asyncio.sleep(DELAY_BETWEEN_COMMANDS)
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    successful = sum(1 for success in results.values() if success)
    failed = len(results) - successful
    
    print(f"✅ Successful: {successful}/{len(results)}")
    print(f"❌ Failed: {failed}/{len(results)}")
    
    if failed > 0:
        print("\n❌ Failed commands:")
        for command, success in results.items():
            if not success:
                print(f"   - {command}")
    
    print("\n✅ Test completed!")
    print("💡 Check your Telegram Saved Messages to see if posts were generated.")
    
    await client.disconnect()


if __name__ == "__main__":
    # Parse command line arguments
    if len(sys.argv) > 1:
        # Test specific commands provided as arguments
        commands_to_test = sys.argv[1:]
        print(f"📝 Testing specific commands: {', '.join(commands_to_test)}")
    else:
        # Test all commands
        commands_to_test = ALL_SERVICE_COMMANDS
        print(f"📝 Testing all {len(commands_to_test)} services")
    
    try:
        asyncio.run(test_services(commands_to_test))
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
