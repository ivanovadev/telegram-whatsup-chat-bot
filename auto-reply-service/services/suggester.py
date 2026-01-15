# suggester.py
import os
import random
import re
from typing import List, Optional
from services.budget_guard import BudgetGuard


class Suggester:
    """Class for generating response options."""

    # --- NEW: language-aware templates ---
    GENERIC_TEMPLATES = {
        "en": [
            [
                "I can, just a bit later. What time works for you?",
                "I’m tied up right now, but I can do it later today or tomorrow. What’s better?",
                "I’m in the middle of something. If it’s urgent, tell me what you need and I’ll prioritize it."
            ],
            [
                "Thanks, I saw it. I’ll check and get back to you soon.",
                "Got it. I’ll reply properly a bit later.",
                "Not ignoring you, just busy. I’ll come back to this shortly."
            ],
            [
                "Sure. Can you share the details so I do it right away when I’m free?",
                "Yes, happy to help. What’s the key info I should know?",
                "Ok. When do you want to discuss it?"
            ]
        ],
        "uk": [
            [
                "Можу, але трохи пізніше. На котру тобі зручно?",
                "Зараз зайнята, але зроблю сьогодні ввечері або завтра. Як краще?",
                "Я зараз у процесі. Якщо терміново, напиши коротко що потрібно і я пріоритезую."
            ],
            [
                "Бачу повідомлення. Перевірю і відповім трохи пізніше.",
                "Прийняла. Напишу нормально трохи згодом.",
                "Не ігнорю, просто зайнята. Повернусь до цього скоро."
            ],
            [
                "Так. Скинь деталі, щоб я зробила правильно, як звільнюсь.",
                "Так, допоможу. Що саме важливо врахувати?",
                "Ок. Коли тобі зручно це обговорити?"
            ]
        ],
    }

    WIFE_TEMPLATES = {
        "en": [
            [
                "Yep, love. I'll handle it a bit later. Can you send the details?",
                "Got it. I'm busy for the next hour, then I'll do it.",
                "Okay. I'll sort it out today and update you."
            ],
            [
                "I saw it. I'll reply properly in a bit 😊",
                "Noted. I'll check and come back to you soon.",
                "I'm on it. Give me a moment and I'll respond."
            ],
            [
                "Sure. Do you want me to do it now, or is later fine?",
                "Ok. Quick question: what's the priority here?",
                "Alright. Tell me what outcome you want and I'll make it happen."
            ]
        ],
        "uk": [
            [
                "Так, коханий. Зроблю трохи пізніше. Скинь, будь ласка, деталі.",
                "Бачу. Я зайнята найближчу годину, потім зроблю.",
                "Ок. Сьогодні закрию це і напишу тобі."
            ],
            [
                "Прийняла. Відповім нормально трохи згодом 😊",
                "Бачу. Перевірю і повернусь до тебе скоро.",
                "Я візьму це на себе. Дай мені хвилинку."
            ],
            [
                "Ок. Тобі треба це прямо зараз чи можна пізніше?",
                "Ок, уточню: що тут найтерміновіше?",
                "Добре. Скажи, який результат ти хочеш, і я зроблю."
            ]
        ],
    }

    FRIENDS_TEMPLATES = {
        "en": [
            [
                "Sure! I'm a bit tied up now, but I'll do it later today. Sound good?",
                "Yeah, I can handle that. Just busy for the next hour or so.",
                "Absolutely. Let me finish what I'm doing and I'll get to it."
            ],
            [
                "Got it! I'll check and get back to you soon.",
                "Thanks for letting me know. I'll take a look shortly.",
                "Saw your message. I'll reply properly in a bit."
            ],
            [
                "Of course! When do you need this by?",
                "Happy to help. Just give me the key details so I can do it right.",
                "Sure thing. What's the most important part here?"
            ]
        ],
        "uk": [
            [
                "Так, звісно! Я зараз трохи зайнята, але зроблю сьогодні. Окей?",
                "Так, зроблю. Просто зайнята найближчу годину.",
                "Авжеж. Дай мені закінчити це і я візьмусь за твоє."
            ],
            [
                "Бачу! Перевірю і напишу скоро.",
                "Дякую, що написала. Подивлюсь трохи згодом.",
                "Бачила повідомлення. Відповім нормально трохи пізніше."
            ],
            [
                "Звісно! На коли тобі це потрібно?",
                "З радістю допоможу. Тільки скинь основні деталі, щоб я зробила правильно.",
                "Так, без проблем. Що тут найважливіше?"
            ]
        ],
    }

    def __init__(self, budget_guard: BudgetGuard):
        self.budget_guard = budget_guard
        self.llm_enabled = os.getenv("LLM_ENABLED", "off").lower() == "on"
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-5.2")
        self.max_output_tokens = int(os.getenv("MAX_OUTPUT_TOKENS", "200"))

    # --- NEW: simple language detection ---
    def _detect_lang(self, text: str, context_messages: Optional[List[str]] = None) -> str:
        sample = text or ""
        if not sample and context_messages:
            sample = context_messages[-1] or ""
        # Any Cyrillic -> treat as Ukrainian mode (you only need uk/en)
        return "uk" if re.search(r"[А-Яа-яІіЇїЄєҐґ]", sample) else "en"

    def generate_options(
        self,
        incoming_text: str,
        context_messages: Optional[List[str]] = None,
        sender_username: Optional[str] = None,
        is_husband: bool = False,
        is_friend: bool = False
    ) -> List[str]:
        can_use, reason = self.budget_guard.can_use_llm()

        if can_use and self.llm_enabled and self.openai_api_key:
            return self._generate_with_llm(incoming_text, context_messages, sender_username, is_husband, is_friend)
        else:
            return self._generate_with_templates(incoming_text, context_messages, sender_username, is_husband, is_friend)

    def _generate_with_templates(
        self,
        incoming_text: str,
        context_messages: Optional[List[str]] = None,
        sender_username: Optional[str] = None,
        is_husband: bool = False,
        is_friend: bool = False
    ) -> List[str]:
        lang = self._detect_lang(incoming_text, context_messages)

        # Choose templates based on user type
        if is_husband:
            templates = self.WIFE_TEMPLATES[lang]
        elif is_friend:
            templates = self.FRIENDS_TEMPLATES[lang]
        else:
            templates = self.GENERIC_TEMPLATES[lang]
        
        return random.choice(templates).copy()

    def _generate_with_llm(
        self,
        incoming_text: str,
        context_messages: Optional[List[str]] = None,
        sender_username: Optional[str] = None,
        is_husband: bool = False,
        is_friend: bool = False
    ) -> List[str]:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.openai_api_key)

            lang = self._detect_lang(incoming_text, context_messages)

            context = ""
            if context_messages:
                context = "Previous messages:\n" + "\n".join(context_messages[-5:])

            if is_husband:
                system_prompt = (
                    "You are Olha replying to her husband Eugen. "
                    "Sound natural and human, not scripted. "
                    "Keep the same language as the incoming message (Ukrainian or English). "
                    "No long dashes."
                )
                prompt = f"""
Rules:
- Reply in {"Ukrainian" if lang == "uk" else "English"} only.
- Keep it short: 1-2 sentences.
- Endearments are optional (max 1). Emojis are optional (max 1).
- If the message asks something, answer it. If not, suggest next step or timing.
- Avoid over-the-top compliments or dramatic tone.

{context}

Incoming message from husband: "{incoming_text}"

Create 3 natural reply options. Each option on a separate line, without numbering.
""".strip()
            elif is_friend:
                system_prompt = (
                    "You are Olha replying to a close friend. "
                    "Sound warm, natural, and friendly, but professional. "
                    "Keep the same language as the incoming message (Ukrainian or English). "
                    "No long dashes."
                )
                prompt = f"""
Rules:
- Reply in {"Ukrainian" if lang == "uk" else "English"} only.
- Keep it short: 1-2 sentences.
- Sound friendly and warm but not over-the-top.
- If the message asks something, answer it. If not, suggest next step or timing.
- Be helpful and enthusiastic.

{context}

Incoming message from friend: "{incoming_text}"

Create 3 natural reply options. Each option on a separate line, without numbering.
""".strip()
            else:
                system_prompt = (
                    "You help craft friendly, non-categorical replies. "
                    "Keep the same language as the incoming message (Ukrainian or English). "
                    "No long dashes."
                )
                prompt = f"""
Rules:
- Reply in {"Ukrainian" if lang == "uk" else "English"} only.
- Never give a hard 'no'. Offer an alternative or timing.
- Keep it short: 1-2 sentences.
- Sound natural and specific.

{context}

Incoming message: "{incoming_text}"

Create 3 reply options. Each option on a separate line, without numbering.
""".strip()

            response = client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                max_completion_tokens=self.max_output_tokens
            )

            content = response.choices[0].message.content.strip()
            
            # Record LLM usage
            tokens_used = response.usage.total_tokens
            # Approximate cost for gpt-5.2 (using similar pricing to gpt-4o-mini: $0.15 per 1M input, $0.60 per 1M output)
            # Average estimate: ~$0.30 per 1M tokens
            cost_per_1k = 0.30 / 1000  # $0.0003 per 1k tokens
            estimated_cost = (tokens_used / 1000) * cost_per_1k
            self.budget_guard.record_llm_call(tokens_used, estimated_cost)

            # Slightly safer parsing: remove bullets/numbering if model adds them
            options = []
            for line in content.split("\n"):
                line = line.strip()
                if not line:
                    continue
                line = re.sub(r"^(\-|\*|\d+[\.\)]|\•)\s*", "", line).strip()
                if line:
                    options.append(line)

            # Fallback fill if needed
            if is_husband:
                templates = self.WIFE_TEMPLATES[lang]
            elif is_friend:
                templates = self.FRIENDS_TEMPLATES[lang]
            else:
                templates = self.GENERIC_TEMPLATES[lang]
            
            while len(options) < 3:
                options.append(random.choice(random.choice(templates)))

            return options[:3]

        except Exception as e:
            print(f"LLM error: {e}")
            return self._generate_with_templates(incoming_text, context_messages, sender_username, is_husband, is_friend)
