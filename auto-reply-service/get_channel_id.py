#!/usr/bin/env python3
"""Helper script to get channel ID."""
import asyncio
import os
from telethon import TelegramClient
from dotenv import load_dotenv

load_dotenv()

api_id = int(os.getenv("TG_API_ID"))
api_hash = os.getenv("TG_API_HASH")
session_path = os.getenv("TG_SESSION_PATH", "./data/session.session")

async def main():
    client = TelegramClient(session_path, api_id, api_hash)
    await client.start()
    
    print("\n📋 Your channels and groups:\n")
    
    async for dialog in client.iter_dialogs():
        if dialog.is_channel or dialog.is_group:
            chat_type = "Channel" if dialog.is_channel else "Group"
            username = f"@{dialog.entity.username}" if hasattr(dialog.entity, 'username') and dialog.entity.username else "No username"
            print(f"{chat_type}: {dialog.name}")
            print(f"  ID: {dialog.id}")
            print(f"  Username: {username}")
            print()
    
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
