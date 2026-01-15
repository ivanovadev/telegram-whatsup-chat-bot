"""Handle incoming private messages (DM)."""
import os
import secrets
from datetime import datetime, timedelta
from typing import Optional
from telethon import TelegramClient, events
from telethon.tl.types import User, PeerUser
from storage.db import Database
from services.suggester import Suggester
from services.budget_guard import BudgetGuard


class InboxHandler:
    """Handler for incoming messages."""
    
    def __init__(
        self,
        client: TelegramClient,
        db: Database,
        suggester: Suggester,
        budget_guard: BudgetGuard
    ):
        self.client = client
        self.db = db
        self.suggester = suggester
        self.budget_guard = budget_guard
        self.busy_mode = os.getenv("BUSY_MODE", "on").lower() == "on"
        self.whitelist_enabled = os.getenv("WHITELIST_ENABLED", "on").lower() == "on"
        self.cooldown_sec = int(os.getenv("COOLDOWN_SEC", "300"))
        
        # Parse control chat ID (can be "me" or numeric ID)
        control_id = os.getenv("CONTROL_CHAT_ID", "me")
        if control_id == "me":
            self.control_chat_id = "me"
        else:
            try:
                self.control_chat_id = int(control_id)
            except ValueError:
                self.control_chat_id = control_id
        
        self.context_messages = int(os.getenv("CONTEXT_MESSAGES", "10"))
        
        # Husband username (single user)
        husband = os.getenv("HUSBAND_USERNAME", "").strip().lstrip("@").lower()
        self.husband_username = husband if husband else None
        
        # Friends usernames (comma-separated list)
        friends = os.getenv("FRIENDS_USERNAMES", "")
        self.friends_usernames = {
            u.lstrip("@").lower()
            for u in [item.strip() for item in friends.split(",")]
            if u
        }
        
        # All allowed usernames (husband + friends)
        self.env_whitelist_usernames = set()
        if self.husband_username:
            self.env_whitelist_usernames.add(self.husband_username)
        self.env_whitelist_usernames.update(self.friends_usernames)
    
    def register(self):
        """Register event handler."""
        
        @self.client.on(events.NewMessage(incoming=True))
        async def handle_incoming(event):
            # Debug logging (can be turned off later)
            print(
                f"📨 Received message: from_id={event.sender_id}, "
                f"out={event.message.out}, peer={type(event.message.peer_id).__name__}"
            )
            
            # Check if it's a private message (PeerUser for private chats)
            if not isinstance(event.message.peer_id, (User, PeerUser)):
                # Silently ignore non-private messages (groups, channels, etc.)
                return
            
            # Check if it's not from ourselves
            if event.message.out:
                print("❌ Message is outgoing (from ourselves)")
                return
            
            print(f"✅ Message passed initial checks. Busy mode: {self.busy_mode}")

            # Check busy mode
            if self.busy_mode:
                # Check whitelist
                if self.whitelist_enabled:
                    user_id = event.sender_id
                    sender = await event.get_sender()
                    username = getattr(sender, "username", None)
                    username_norm = username.lower() if username else None

                    # First: check env-based whitelist (by username)
                    if self.env_whitelist_usernames:
                        if (
                            not username_norm
                            or username_norm not in self.env_whitelist_usernames
                        ):
                            print(
                                f"❌ User {user_id} (@{username}) "
                                f"not in env whitelist {self.env_whitelist_usernames}"
                            )
                            return
                        print(
                            f"✅ User {user_id} (@{username}) "
                            "allowed by env whitelist"
                        )
                    else:
                        # Fallback: DB-based whitelist (by user_id)
                        if not self.db.is_whitelisted(user_id):
                            print(f"❌ User {user_id} not in DB whitelist")
                            return
                        print(f"✅ User {user_id} is whitelisted (DB)")
                
                # Check cooldown
                last_card_time = self.db.get_user_cooldown(event.sender_id)
                if last_card_time:
                    time_diff = datetime.now() - last_card_time
                    if time_diff.total_seconds() < self.cooldown_sec:
                        print(f"❌ Cooldown active: {int(self.cooldown_sec - time_diff.total_seconds())}s remaining")
                        return
                    print(f"✅ Cooldown passed")
                
                # Create card
                print(f"✅ Creating card for user {event.sender_id}")
                await self._create_card(event)
            else:
                print("❌ Busy mode is OFF")
    
    async def _create_card(self, event):
        """Create a card for incoming message."""
        # Generate unique card ID
        card_id = secrets.token_hex(4).upper()
        
        # Get sender information
        sender = await event.get_sender()
        user_id = event.sender_id
        username = getattr(sender, "username", None)
        
        # Get message text
        text = event.message.message or "[media or sticker]"
        
        # Get context (recent messages)
        context = await self._get_context(user_id)
        
        # Determine user type
        username_lower = username.lower() if username else None
        is_husband = username_lower == self.husband_username
        is_friend = username_lower in self.friends_usernames
        
        # Generate 3 response options (pass username and user type)
        options = self.suggester.generate_options(
            text, 
            context, 
            sender_username=username,
            is_husband=is_husband,
            is_friend=is_friend
        )
        
        # Save card to database
        self.db.create_card(
            card_id=card_id,
            from_user_id=user_id,
            from_username=username,
            original_message_id=event.message.id,
            original_text=text,
            options=options
        )
        
        # Update cooldown
        self.db.update_user_cooldown(user_id)
        
        # Update card counter
        self.db.increment_usage(cards=1)
        
        # Format message for control chat
        card_message = self._format_card_message(
            card_id, user_id, username, text, options
        )
        
        # Create reply keyboard buttons (visible at bottom of screen)
        from telethon.tl.custom import Button
        
        # Create simple text buttons that will be visible as keyboard
        buttons = [
            [Button.text(f"✅ Send 1"), Button.text(f"✅ Send 2"), Button.text(f"✅ Send 3")],
            [Button.text("🔄 Regen"), Button.text("⏭️ Skip"), Button.text("🚫 Ignore")]
        ]
        
        # Send to control chat
        try:
            print(f"[INBOX] Sending card with {len(buttons)} button rows")
            await self.client.send_message(
                self.control_chat_id, 
                card_message,
                buttons=buttons
            )
            print(f"[INBOX] Card sent successfully with buttons")
        except Exception as e:
            print(f"[INBOX] Error sending card with buttons: {e}")
            # Try sending without buttons as fallback
            try:
                await self.client.send_message(self.control_chat_id, card_message)
                print(f"[INBOX] Card sent without buttons (fallback)")
            except Exception as e2:
                print(f"[INBOX] Error sending card (fallback): {e2}")
    
    async def _get_context(self, user_id: int) -> list[str]:
        """Get context of recent messages with user."""
        try:
            messages = []
            async for msg in self.client.iter_messages(user_id, limit=self.context_messages):
                if msg.message:
                    messages.append(msg.message)
            return list(reversed(messages))  # From older to newer
        except Exception:
            return []
    
    def _format_card_message(
        self,
        card_id: str,
        user_id: int,
        username: Optional[str],
        text: str,
        options: list[str]
    ) -> str:
        """Format card message for control chat."""
        username_str = f"@{username}" if username else f"user_{user_id}"
        
        message = f"""📬 CARD {card_id}
👤 From: {username_str} (ID: {user_id})
💬 Incoming: "{text}"

📝 Reply options:
1️⃣ {options[0]}
2️⃣ {options[1]}
3️⃣ {options[2]}

👇 Click a button below to reply"""
        
        return message
    
    def set_busy_mode(self, enabled: bool):
        """Set busy mode."""
        self.busy_mode = enabled
