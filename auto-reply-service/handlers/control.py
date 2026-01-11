"""Handle commands in control chat."""
import os
import re
import asyncio
from telethon import TelegramClient, events
from storage.db import Database, CardStatus
from shared_services.suggester import Suggester
from shared_services.budget_guard import BudgetGuard


class ControlHandler:
    """Handler for control chat commands."""
    
    def __init__(
        self,
        client: TelegramClient,
        db: Database,
        suggester: Suggester,
        budget_guard: BudgetGuard,
        inbox_handler,
        channel_handler=None
    ):
        self.client = client
        self.db = db
        self.suggester = suggester
        self.budget_guard = budget_guard
        self.inbox_handler = inbox_handler
        self.channel_handler = channel_handler
        self.control_chat_id = os.getenv("CONTROL_CHAT_ID", "me")
    
    def register(self):
        """Register command handler."""
        
        @self.client.on(events.NewMessage(chats=self.control_chat_id))
        async def handle_control(event):
            # Debug log for every control message
            try:
                print(
                    f"[CONTROL] New message in control chat: "
                    f"text={event.message.message!r}, reply_to={event.message.reply_to}"
                )
            except Exception:
                pass
            # Ignore messages we sent ourselves (except commands)
            if event.message.out and not event.message.message:
                return
            
            text = event.message.message or ""
            text = text.strip()
            
            # If it's a reply to a card
            if event.message.reply_to:
                await self._handle_reply(event, text)
            else:
                # Commands without reply
                await self._handle_command(event, text)
    
    async def _handle_reply(self, event, text: str):
        """Handle reply to a card."""
        reply_to = event.message.reply_to
        print(f"[CONTROL] Handling reply with text={text!r}, reply_to={reply_to}")
        
        # Find card_id in the message we're replying to
        try:
            replied_msg = await event.get_reply_message()
            if not replied_msg or not replied_msg.message:
                return
            
            # Find CARD ID in text
            card_match = re.search(r'CARD\s+([A-F0-9]+)', replied_msg.message)
            if not card_match:
                return
            
            card_id = card_match.group(1)
            card = self.db.get_card(card_id)
            
            if not card or card['status'] != 'pending':
                print(f"[CONTROL] Card {card_id} not found or status != pending")
                await event.reply("❌ Card not found or already processed")
                return
            
            # Handle selection
            if text in ['1', '2', '3']:
                option_idx = int(text) - 1
                if 0 <= option_idx < len(card['options']):
                    response_text = card['options'][option_idx]
                    
                    # Send response immediately (most important - do this first!)
                    print(f"[CONTROL] Sending response {text} for card {card_id} to user {card['from_user_id']}")
                    await self._send_response(card, response_text)
                    
                    # Update status after sending (non-blocking)
                    self.db.update_card_status(card_id, CardStatus.SENT)
                    
                    # Reply confirmation
                    await event.reply(f"✅ Response {text} sent")
                    print(f"[CONTROL] Response option {text} sent for card {card_id}")
                else:
                    print(f"[CONTROL] Invalid option index {option_idx} for card {card_id}")
                    await event.reply("❌ Invalid option number")
            
            elif text == '0':
                self.db.update_card_status(card_id, CardStatus.DECLINED)
                print(f"[CONTROL] Response declined for card {card_id}")
                await event.reply("❌ Response declined")
            
            elif text.startswith('custom:'):
                custom_text = text[7:].strip()
                if custom_text:
                    await self._send_response(card, custom_text)
                    self.db.update_card_status(card_id, CardStatus.SENT)
                    print(f"[CONTROL] Custom response sent for card {card_id}")
                    await event.reply("✅ Custom response sent")
                else:
                    await event.reply("❌ Empty text after 'custom:'")
            
            elif text == 'regen':
                # Regenerate options
                new_options = self.suggester.generate_options(
                    card['original_text']
                )
                # Update card in database
                import json
                conn = self.db._get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE cards SET options = ? WHERE card_id = ?",
                    (json.dumps(new_options), card_id)
                )
                conn.commit()
                conn.close()
                
                # Send new card
                new_card_msg = self.inbox_handler._format_card_message(
                    card_id, card['from_user_id'], card['from_username'],
                    card['original_text'], new_options
                )
                print(f"[CONTROL] Regenerated options for card {card_id}")
                await event.reply(new_card_msg)
            
        except Exception as e:
            print(f"[CONTROL] Error while handling reply: {e}")
            await event.reply(f"❌ Error: {e}")
    
    async def _handle_command(self, event, text: str):
        """Handle command without reply."""
        if not text:
            return
        
        text_lower = text.lower()
        print(f"[CONTROL] Handling command: {text_lower!r}")
        
        # busy on/off
        if text_lower == 'busy on':
            self.inbox_handler.set_busy_mode(True)
            await event.reply("✅ Busy mode enabled")
        
        elif text_lower == 'busy off':
            self.inbox_handler.set_busy_mode(False)
            await event.reply("✅ Busy mode disabled")
        
        # whitelist
        elif text_lower.startswith('whitelist add '):
            username = text[14:].strip().lstrip('@')
            # Need to find user_id by username
            try:
                entity = await self.client.get_entity(username)
                if self.db.add_to_whitelist(entity.id, username):
                    await event.reply(f"✅ @{username} added to whitelist")
                else:
                    await event.reply(f"❌ Error adding to whitelist")
            except Exception as e:
                await event.reply(f"❌ User not found: {e}")
        
        elif text_lower.startswith('whitelist remove '):
            username = text[17:].strip().lstrip('@')
            try:
                entity = await self.client.get_entity(username)
                if self.db.remove_from_whitelist(entity.id):
                    await event.reply(f"✅ @{username} removed from whitelist")
                else:
                    await event.reply(f"❌ User not found in whitelist")
            except Exception as e:
                await event.reply(f"❌ Error: {e}")
        
        elif text_lower == 'whitelist list':
            whitelist = self.db.get_whitelist()
            if whitelist:
                lines = [f"- @{w.get('username', 'unknown')} (id: {w['user_id']})" 
                        for w in whitelist]
                await event.reply("📋 Whitelist:\n" + "\n".join(lines))
            else:
                await event.reply("📋 Whitelist is empty")
        
        # status
        elif text_lower == 'status':
            status = self.budget_guard.get_status()
            usage = self.db.get_today_usage()
            
            status_msg = f"""📊 Status

💰 Budget:
  Spending: ${status['estimated_usd']:.2f} USD
  Limit: ${status['daily_budget']:.2f} USD
  Alert: ${status['alert_threshold']:.2f} USD
  Hard stop: ${status['hard_stop']:.2f} USD

🤖 LLM:
  Enabled: {'✅' if status['llm_enabled'] else '❌'}
  Available: {'✅' if status['can_use_llm'] else '❌'}
  Calls: {status['llm_calls']}
  Tokens: {status['tokens_used']}

📝 Cards:
  Created today: {usage.get('cards_created', 0)}
  Pending: {len(self.db.get_pending_cards())}

⚙️ Modes:
  Busy: {'✅' if self.inbox_handler.busy_mode else '❌'}
  Whitelist: {'✅' if os.getenv('WHITELIST_ENABLED', 'on').lower() == 'on' else '❌'}"""
            
            await event.reply(status_msg)
        
        elif text_lower == 'travel':
            # Trigger group/channel post manually (for testing)
            if self.channel_handler:
                await event.reply("🚀 Generating travel post...")
                try:
                    await self.channel_handler._post_evening_content()
                    await event.reply("✅ Travel post sent to group!")
                except Exception as e:
                    error_msg = str(e)
                    await event.reply(f"❌ Error: {error_msg}\n\n💡 Check:\n- Is CHANNEL_USERNAME or CHANNEL_ID set?\n- Are you admin in the group?\n- Check bot logs for details")
                    print(f"[CONTROL] Travel post error: {e}")
            else:
                await event.reply("❌ Group posts not enabled. Set CHANNEL_POSTS_ENABLED=on in .env")
        
        elif text_lower == 'travel morning':
            # Trigger morning post manually (for testing)
            if self.channel_handler:
                await event.reply("🌍 Generating morning post...")
                try:
                    await self.channel_handler._post_morning_content()
                    await event.reply("✅ Morning post sent to group!")
                except Exception as e:
                    error_msg = str(e)
                    await event.reply(f"❌ Error: {error_msg}\n\n💡 Check:\n- Is CHANNEL_USERNAME or CHANNEL_ID set?\n- Are you admin in the group?\n- Check bot logs for details")
                    print(f"[CONTROL] Morning post error: {e}")
            else:
                await event.reply("❌ Group posts not enabled. Set CHANNEL_POSTS_ENABLED=on in .env")
        
        elif text_lower == 'get group id':
            # Helper command to get group ID
            try:
                if event.message.reply_to:
                    replied = await event.get_reply_message()
                    if replied:
                        # Get chat from replied message
                        chat = await replied.get_chat()
                        chat_id = chat.id
                        chat_title = getattr(chat, 'title', 'Unknown')
                        chat_username = getattr(chat, 'username', None)
                        
                        info = f"📋 Group Info:\nTitle: {chat_title}\nID: {chat_id}"
                        if chat_username:
                            info += f"\nUsername: @{chat_username}"
                        
                        info += f"\n\n💡 Add to .env:\nCHANNEL_ID={chat_id}"
                        if chat_username:
                            info += f"\n# OR use username:\n# CHANNEL_USERNAME={chat_username}"
                        
                        await event.reply(info)
                    else:
                        await event.reply("❌ Could not get replied message")
                else:
                    await event.reply("💡 Reply to any message from the group with 'get group id' to get the ID")
            except Exception as e:
                await event.reply(f"❌ Error: {e}\n\n💡 Make sure you're in the group and reply to a message from there")
                print(f"[CONTROL] get group id error: {e}")
        
        else:
            # Unknown command
            pass
    
    async def _send_response(self, card: dict, response_text: str):
        """Send response to original dialog."""
        try:
            user_id = card['from_user_id']
            original_msg_id = card['original_message_id']
            
            print(f"[CONTROL] Sending response to user {user_id}, message {original_msg_id}")
            
            # Send reply to original message (without waiting for typing indicator)
            await self.client.send_message(
                user_id,
                response_text,
                reply_to=original_msg_id
            )
            
            print(f"[CONTROL] Response sent successfully to user {user_id}")
        except Exception as e:
            print(f"[CONTROL] Error sending response: {e}")
