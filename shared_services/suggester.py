"""Generate 3 response options (LLM or templates)."""
import os
import random
from typing import List, Optional
from shared_services.budget_guard import BudgetGuard


class Suggester:
    """Class for generating response options."""
    
    # Generic response templates (if LLM is disabled) - for general contacts
    GENERIC_TEMPLATES = [
        [
            "I can, but a bit later. What time works for you?",
            "I'm busy today, but I can do it tomorrow or on weekends. What's better for you?",
            "I'm busy right now. If urgent, write 'urgent' and what you need."
        ],
        [
            "Thanks for the message! I'll check and reply soon.",
            "Got it, I'll think about it and write back later.",
            "Can't reply in detail right now, but I'll write soon."
        ],
        [
            "Sure! When is a good time to discuss details?",
            "Yes, I can help. Please provide more information.",
            "Of course, let's discuss. What time works for you?"
        ]
    ]
    
    # Wife-to-husband templates (for eugen_parasochka_pl)
    WIFE_TEMPLATES = [
        [
            "Of course, my love! ❤️ I'll do it as soon as I can. What time would be best for you?",
            "Sure, darling! 😊 I'm a bit busy now, but I'll handle it soon. Love you!",
            "Yes, sweetheart! Just give me a little time, okay? 💕"
        ],
        [
            "Got your message, honey! 💖 I'll take care of it and let you know.",
            "Saw this, my dear! I'll get back to you shortly. Miss you! 😘",
            "Thanks for writing, love! I'll think about it and reply soon. ❤️"
        ],
        [
            "Absolutely, my love! 😊 When do you want to discuss it?",
            "Of course I'll help you, darling! 💕 Just tell me what you need.",
            "Sure thing, sweetheart! Let's talk about it. Love you! ❤️"
        ]
    ]
    
    def __init__(self, budget_guard: BudgetGuard):
        self.budget_guard = budget_guard
        self.llm_enabled = os.getenv("LLM_ENABLED", "off").lower() == "on"
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.max_output_tokens = int(os.getenv("MAX_OUTPUT_TOKENS", "200"))
    
    def generate_options(
        self,
        incoming_text: str,
        context_messages: Optional[List[str]] = None,
        sender_username: Optional[str] = None
    ) -> List[str]:
        """
        Generate 3 response options.
        
        Args:
            incoming_text: Incoming message text
            context_messages: Context of previous messages (optional)
            sender_username: Username of the sender (to determine tone/style)
        
        Returns:
            List of 3 response options
        """
        can_use, reason = self.budget_guard.can_use_llm()
        
        if can_use and self.llm_enabled and self.openai_api_key:
            return self._generate_with_llm(incoming_text, context_messages, sender_username)
        else:
            return self._generate_with_templates(incoming_text, sender_username)
    
    def _generate_with_templates(self, incoming_text: str, sender_username: Optional[str] = None) -> List[str]:
        """Generate responses from templates."""
        # Check if sender is husband (eugen_parasochka_pl)
        is_husband = sender_username and sender_username.lower() == "eugen_parasochka_pl"
        
        # Select appropriate templates
        templates = self.WIFE_TEMPLATES if is_husband else self.GENERIC_TEMPLATES
        
        # Simple random template selection
        return random.choice(templates).copy()
    
    def _generate_with_llm(
        self,
        incoming_text: str,
        context_messages: Optional[List[str]] = None,
        sender_username: Optional[str] = None
    ) -> List[str]:
        """Generate responses via OpenAI API."""
        try:
            from openai import OpenAI
            
            client = OpenAI(api_key=self.openai_api_key)
            
            # Check if sender is husband (eugen_parasochka_pl)
            is_husband = sender_username and sender_username.lower() == "eugen_parasochka_pl"
            
            # Build prompt based on recipient
            context = ""
            if context_messages:
                context = "\n".join([
                    f"Previous messages:\n" + "\n".join(context_messages[-5:])
                ])
            
            if is_husband:
                # Wife responding to husband - loving, warm tone
                system_prompt = "You are a loving wife responding to her husband. Your tone is warm, affectionate, and supportive."
                prompt = f"""You are helping a wife reply to messages from her husband (Eugen) in a loving and caring style.

Rules:
- Be warm, affectionate, and loving
- Use terms of endearment (darling, honey, sweetheart, my love)
- Add heart emojis occasionally (❤️, 💕, 😘, 😊)
- Always be supportive and understanding
- Show care and concern for his needs
- Keep responses sweet but natural (2-3 sentences max)
- Never be cold or distant

{context}

Incoming message from husband: "{incoming_text}"

Create 3 loving response options from wife to husband. Each option on a separate line, without numbering."""
            else:
                # Generic friendly style for other contacts
                system_prompt = "You help form friendly replies to messages."
                prompt = f"""You help reply to Telegram messages in a friendly but not categorical style.

Rules:
- Never say a categorical "no"
- Always offer alternatives
- Be friendly and open
- Responses should be short (2-3 sentences max)

{context}

Incoming message: "{incoming_text}"

Create 3 response options in this style. Each option on a separate line, without numbering."""

            response = client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                # Some newer models only support default temperature (1),
                # so we rely on the server default and only control max tokens.
                max_completion_tokens=self.max_output_tokens
            )
            
            # Parse response
            content = response.choices[0].message.content.strip()
            options = [line.strip() for line in content.split("\n") if line.strip()]
            
            # Record usage
            tokens_used = response.usage.total_tokens
            # Approximate cost (for gpt-4o-mini)
            cost_per_1k_tokens = 0.15 / 1000  # $0.15 per 1M tokens input, $0.60 per 1M output
            estimated_cost = (tokens_used / 1000) * cost_per_1k_tokens
            
            self.budget_guard.record_llm_call(tokens_used, estimated_cost)
            
            # If we got less than 3 options, fill with templates
            is_husband = sender_username and sender_username.lower() == "eugen_parasochka_pl"
            templates = self.WIFE_TEMPLATES if is_husband else self.GENERIC_TEMPLATES
            
            while len(options) < 3:
                options.append(random.choice(templates[0]))
            
            return options[:3]
            
        except Exception as e:
            # If LLM error, return templates
            print(f"LLM error: {e}")
            return self._generate_with_templates(incoming_text, sender_username)
