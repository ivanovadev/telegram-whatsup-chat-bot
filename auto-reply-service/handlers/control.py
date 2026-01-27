"""Handle commands in control chat."""
import os
import re
import asyncio
from telethon import TelegramClient, events
from storage.db import Database, CardStatus
from services.suggester import Suggester
from services.budget_guard import BudgetGuard


class ControlHandler:
    """Handler for control chat commands."""
    
    def __init__(
        self,
        client: TelegramClient,
        db: Database,
        suggester: Suggester,
        budget_guard: BudgetGuard,
        inbox_handler,
        channel_handler=None,
        neo4j=None
    ):
        self.client = client
        self.db = db
        self.suggester = suggester
        self.budget_guard = budget_guard
        self.inbox_handler = inbox_handler
        self.channel_handler = channel_handler
        self.neo4j = neo4j
        
        # Parse control chat ID (can be "me" or numeric ID)
        control_id = os.getenv("CONTROL_CHAT_ID", "me")
        if control_id == "me":
            self.control_chat_id = "me"
        else:
            try:
                self.control_chat_id = int(control_id)
            except ValueError:
                self.control_chat_id = control_id
    
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
        
        @self.client.on(events.CallbackQuery(chats=self.control_chat_id))
        async def handle_callback(event):
            """Handle inline button clicks."""
            try:
                data = event.data.decode('utf-8')
                print(f"[CONTROL] Button clicked: {data}")
                
                # Parse callback data: "action:card_id:option" or "action:card_id"
                parts = data.split(':')
                if len(parts) < 2:
                    await event.answer("❌ Invalid button data")
                    return
                
                action = parts[0]
                card_id = parts[1]
                
                # Get card from database
                card = self.db.get_card(card_id)
                if not card or card['status'] != 'pending':
                    await event.answer("❌ Card not found or already processed")
                    return
                
                if action == "reply" and len(parts) == 3:
                    # Reply with option 1/2/3
                    option_num = parts[2]
                    option_idx = int(option_num) - 1
                    
                    if 0 <= option_idx < len(card['options']):
                        response_text = card['options'][option_idx]
                        
                        # Update Neo4j if available
                        if hasattr(self, 'neo4j') and self.neo4j:
                            try:
                                self.neo4j.update_card_selection(card_id, option_idx + 1)
                            except Exception as e:
                                print(f"⚠️  Neo4j update error: {e}")
                        
                        # Send response
                        await self._send_response(card, response_text)
                        self.db.update_card_status(card_id, CardStatus.SENT)
                        
                        # Edit message to show it's done
                        await event.edit(
                            f"{event.message.message}\n\n✅ Response {option_num} sent!",
                            buttons=None
                        )
                        await event.answer(f"✅ Response {option_num} sent")
                    else:
                        await event.answer("❌ Invalid option")
                
                elif action == "regen":
                    # Regenerate options
                    await event.answer("🔄 Regenerating options...")
                    
                    # Get context
                    context = await self.inbox_handler._get_context(card['from_user_id'])
                    
                    # Check if this is husband or friend
                    is_husband = (card.get('from_username', '').lower() == self.inbox_handler.husband_username)
                    is_friend = (card.get('from_username', '').lower() in self.inbox_handler.friends_usernames)
                    
                    # Generate new options
                    new_options = self.suggester.generate_options(
                        card['original_text'],
                        context,
                        card.get('from_username'),
                        is_husband=is_husband,
                        is_friend=is_friend
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
                    
                    # Edit message with new options
                    new_card_msg = self.inbox_handler._format_card_message(
                        card_id,
                        card['from_user_id'],
                        card['from_username'],
                        card['original_text'],
                        new_options
                    )
                    
                    # Recreate reply keyboard buttons
                    from telethon.tl.custom import Button
                    buttons = [
                        [Button.text(f"✅ Send 1"), Button.text(f"✅ Send 2"), Button.text(f"✅ Send 3")],
                        [Button.text("🔄 Regen"), Button.text("⏭️ Skip"), Button.text("🚫 Ignore")]
                    ]
                    
                    await event.edit(new_card_msg, buttons=buttons)
                    await event.answer("✅ Options regenerated")
                
                elif action == "skip":
                    # Skip card
                    self.db.update_card_status(card_id, CardStatus.DECLINED)
                    await event.edit(
                        f"{event.message.message}\n\n⏭️ Skipped",
                        buttons=None
                    )
                    await event.answer("⏭️ Card skipped")
                
                elif action == "ignore":
                    # Ignore sender
                    self.db.update_card_status(card_id, CardStatus.DECLINED)
                    # TODO: Add to ignore list in future
                    await event.edit(
                        f"{event.message.message}\n\n🚫 Ignored",
                        buttons=None
                    )
                    await event.answer("🚫 Sender ignored")
                
            except Exception as e:
                print(f"[CONTROL] Error handling callback: {e}")
                await event.answer(f"❌ Error: {e}")
    
    async def _handle_reply(self, event, text: str):
        """Handle reply to a card."""
        reply_to = event.message.reply_to
        print(f"[CONTROL] Handling reply with text={text!r}, reply_to={reply_to}")
        
        # Special command: get group id
        if text.lower() == 'get group id':
            try:
                replied_msg = await event.get_reply_message()
                if replied_msg:
                    # Get chat from the message (works with forwarded messages)
                    chat = await replied_msg.get_chat()
                    chat_id = chat.id
                    chat_title = getattr(chat, 'title', getattr(chat, 'first_name', 'Unknown'))
                    chat_username = getattr(chat, 'username', None)
                    
                    info = f"📋 Chat Info:\nTitle: {chat_title}\nID: {chat_id}"
                    if chat_username:
                        info += f"\nUsername: @{chat_username}"
                    
                    info += f"\n\n💡 Add to .env:\nCONTROL_CHAT_ID={chat_id}"
                    
                    await event.reply(info)
                    print(f"[CONTROL] Sent chat ID: {chat_id}")
                else:
                    await event.reply("❌ Could not get replied message")
            except Exception as e:
                await event.reply(f"❌ Error: {e}")
                print(f"[CONTROL] get group id error: {e}")
            return
        
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
                # Get context
                context = await self.inbox_handler._get_context(card['from_user_id'])
                
                # Check if this is husband or friend
                is_husband = (card.get('from_username', '').lower() == self.inbox_handler.husband_username)
                is_friend = (card.get('from_username', '').lower() in self.inbox_handler.friends_usernames)
                
                new_options = self.suggester.generate_options(
                    card['original_text'],
                    context,
                    card.get('from_username'),
                    is_husband=is_husband,
                    is_friend=is_friend
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
                
                # Send new card with buttons
                new_card_msg = self.inbox_handler._format_card_message(
                    card_id, card['from_user_id'], card['from_username'],
                    card['original_text'], new_options
                )
                
                # Create reply keyboard buttons
                from telethon.tl.custom import Button
                buttons = [
                    [Button.text(f"✅ Send 1"), Button.text(f"✅ Send 2"), Button.text(f"✅ Send 3")],
                    [Button.text("🔄 Regen"), Button.text("⏭️ Skip"), Button.text("🚫 Ignore")]
                ]
                
                print(f"[CONTROL] Regenerated options for card {card_id}")
                await event.reply(new_card_msg, buttons=buttons)
            
        except Exception as e:
            print(f"[CONTROL] Error while handling reply: {e}")
            await event.reply(f"❌ Error: {e}")
    
    async def _handle_command(self, event, text: str):
        """Handle command without reply."""
        if not text:
            return
        
        text_lower = text.lower()
        print(f"[CONTROL] Handling command: {text_lower!r}")
        
        # Handle reply keyboard buttons (✅ Send 1/2/3, 🔄 Regen, etc.)
        # These commands need to work on the most recent pending card
        if text_lower in ['✅ send 1', '✅ send 2', '✅ send 3', '🔄 regen', '⏭️ skip', '🚫 ignore']:
            # Get the most recent pending card
            pending_cards = self.db.get_pending_cards()
            if not pending_cards:
                await event.reply("❌ No pending cards")
                return
            
            card = pending_cards[0]  # Most recent
            card_id = card['card_id']
            
            if text_lower == '✅ send 1':
                option_idx = 0
            elif text_lower == '✅ send 2':
                option_idx = 1
            elif text_lower == '✅ send 3':
                option_idx = 2
            elif text_lower == '🔄 regen':
                # Regenerate options for most recent card
                context = await self.inbox_handler._get_context(card['from_user_id'])
                is_husband = (card.get('from_username', '').lower() == self.inbox_handler.husband_username)
                is_friend = (card.get('from_username', '').lower() in self.inbox_handler.friends_usernames)
                
                new_options = self.suggester.generate_options(
                    card['original_text'],
                    context,
                    card.get('from_username'),
                    is_husband=is_husband,
                    is_friend=is_friend
                )
                
                # Update in database
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
                
                # Create reply keyboard
                from telethon.tl.custom import Button
                buttons = [
                    [Button.text(f"✅ Send 1"), Button.text(f"✅ Send 2"), Button.text(f"✅ Send 3")],
                    [Button.text("🔄 Regen"), Button.text("⏭️ Skip"), Button.text("🚫 Ignore")]
                ]
                
                await event.reply(f"🔄 Regenerated:\n\n{new_card_msg}", buttons=buttons)
                return
            elif text_lower == '⏭️ skip':
                self.db.update_card_status(card_id, CardStatus.DECLINED)
                await event.reply(f"⏭️ Card {card_id} skipped")
                return
            elif text_lower == '🚫 ignore':
                self.db.update_card_status(card_id, CardStatus.DECLINED)
                await event.reply(f"🚫 Card {card_id} ignored")
                return
            else:
                return
            
            # Send response for option 1/2/3
            if 0 <= option_idx < len(card['options']):
                response_text = card['options'][option_idx]
                
                # Update Neo4j if available
                if self.neo4j:
                    try:
                        self.neo4j.update_card_selection(card['card_id'], option_idx + 1)
                    except Exception as e:
                        print(f"⚠️  Neo4j update error: {e}")
                
                await self._send_response(card, response_text)
                self.db.update_card_status(card_id, CardStatus.SENT)
                await event.reply(f"✅ Response {option_idx + 1} sent to {card.get('from_username', 'user')}")
            return
        
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
  Total (all time): {self.db.get_total_cards_count()}
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
        
        elif text_lower in ['help', 'commands', '?']:
            help_msg = """📚 Available Commands:

**🎮 Keyboard Buttons (use buttons below):**
• ✅ Send 1/2/3 - Send response option
• 🔄 Regen - Regenerate options
• ⏭️ Skip - Skip card
• 🚫 Ignore - Ignore sender

**💬 Text Commands (reply to card):**
• 1, 2, 3 - Send response option
• regen - Regenerate options
• skip - Skip card
• custom: <text> - Send custom text

**📊 Status & Info:**
• status - Show budget, LLM stats, cards
• help - Show this message
• get group id - Get chat ID (reply to message)

**⚙️ Settings:**
• busy on/off - Toggle busy mode
• whitelist list - Show whitelist
• whitelist add/remove @username

**🧪 Testing:**
• travel - Send evening post
• travel morning - Send morning post"""
            await event.reply(help_msg)
        
        else:
            # Unknown command
            if text and len(text) < 50:  # Only for short texts that look like commands
                await event.reply(f"❓ Unknown command: '{text}'\n\n💡 Type 'help' to see available commands")
    
    async def _send_response(self, card: dict, response_text: str):
        """Send response to original dialog."""
        try:
            user_id = card['from_user_id']
            original_msg_id = card['original_message_id']
            
            print(f"[CONTROL] Sending response to user {user_id}, message {original_msg_id}")
            
            # Send as separate message (not as reply)
            await self.client.send_message(
                user_id,
                response_text
            )
            
            print(f"[CONTROL] Response sent successfully to user {user_id}")
        except Exception as e:
            print(f"[CONTROL] Error sending response: {e}")
