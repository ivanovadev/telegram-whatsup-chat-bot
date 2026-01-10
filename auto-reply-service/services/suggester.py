"""Generate 3 response options (LLM or templates)."""
import os
import random
from typing import List, Optional
from services.budget_guard import BudgetGuard


class Suggester:
    """Class for generating response options."""
    
    # Response templates (if LLM is disabled)
    TEMPLATES = [
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
    
    def __init__(self, budget_guard: BudgetGuard):
        self.budget_guard = budget_guard
        self.llm_enabled = os.getenv("LLM_ENABLED", "off").lower() == "on"
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.max_output_tokens = int(os.getenv("MAX_OUTPUT_TOKENS", "200"))
    
    def generate_options(
        self,
        incoming_text: str,
        context_messages: Optional[List[str]] = None
    ) -> List[str]:
        """
        Generate 3 response options.
        
        Args:
            incoming_text: Incoming message text
            context_messages: Context of previous messages (optional)
        
        Returns:
            List of 3 response options
        """
        can_use, reason = self.budget_guard.can_use_llm()
        
        if can_use and self.llm_enabled and self.openai_api_key:
            return self._generate_with_llm(incoming_text, context_messages)
        else:
            return self._generate_with_templates(incoming_text)
    
    def _generate_with_templates(self, incoming_text: str) -> List[str]:
        """Generate responses from templates."""
        # Simple random template selection
        return random.choice(self.TEMPLATES).copy()
    
    def _generate_with_llm(
        self,
        incoming_text: str,
        context_messages: Optional[List[str]] = None
    ) -> List[str]:
        """Generate responses via OpenAI API."""
        try:
            from openai import OpenAI
            
            client = OpenAI(api_key=self.openai_api_key)
            
            # Build prompt
            context = ""
            if context_messages:
                context = "\n".join([
                    f"Previous messages:\n" + "\n".join(context_messages[-5:])
                ])
            
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
                    {"role": "system", "content": "You help form friendly replies to messages."},
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
            while len(options) < 3:
                options.append(random.choice(self.TEMPLATES[0]))
            
            return options[:3]
            
        except Exception as e:
            # If LLM error, return templates
            print(f"LLM error: {e}")
            return self._generate_with_templates(incoming_text)
