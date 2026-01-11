"""Cost control: limits, alerts, hard stop."""
import os
from typing import Optional
from storage.db import Database


class BudgetGuard:
    """Class for controlling LLM costs."""
    
    def __init__(self, db: Database):
        self.db = db
        self.daily_budget_usd = float(os.getenv("DAILY_BUDGET_USD", "2.0"))
        self.alert_at_usd = float(os.getenv("ALERT_AT_USD", "1.5"))
        self.hard_stop_usd = float(os.getenv("HARD_STOP_USD", "2.5"))
        self.llm_enabled = os.getenv("LLM_ENABLED", "off").lower() == "on"
    
    def can_use_llm(self) -> tuple[bool, Optional[str]]:
        """
        Check if LLM can be used.
        Returns (can_use, reason_if_no)
        """
        if not self.llm_enabled:
            return False, "LLM disabled in settings"
        
        usage = self.db.get_today_usage()
        estimated_usd = usage.get("estimated_usd", 0.0)
        
        if estimated_usd >= self.hard_stop_usd:
            return False, f"Hard stop: spending {estimated_usd:.2f} USD >= {self.hard_stop_usd} USD"
        
        return True, None
    
    def record_llm_call(self, tokens_used: int, estimated_cost_usd: float):
        """Record LLM usage."""
        self.db.increment_usage(
            llm_calls=1,
            tokens=tokens_used,
            estimated_usd=estimated_cost_usd
        )
    
    async def check_and_alert(self, client) -> bool:
        """
        Check spending and send alert if needed.
        Returns True if alert was sent.
        """
        usage = self.db.get_today_usage()
        estimated_usd = usage.get("estimated_usd", 0.0)
        
        if estimated_usd >= self.alert_at_usd and estimated_usd < self.hard_stop_usd:
            # Send alert to control chat
            control_chat_id = os.getenv("CONTROL_CHAT_ID", "me")
            alert_msg = (
                f"⚠️ Budget Alert\n\n"
                f"Spending today: ${estimated_usd:.2f} USD\n"
                f"Alert threshold: ${self.alert_at_usd:.2f} USD\n"
                f"Hard stop: ${self.hard_stop_usd:.2f} USD\n\n"
                f"LLM calls: {usage.get('llm_calls', 0)}\n"
                f"Tokens: {usage.get('tokens_used', 0)}"
            )
            
            try:
                await client.send_message(control_chat_id, alert_msg)
                return True
            except Exception:
                pass
        
        return False
    
    def get_status(self) -> dict:
        """Get current spending status."""
        usage = self.db.get_today_usage()
        estimated_usd = usage.get("estimated_usd", 0.0)
        
        return {
            "estimated_usd": estimated_usd,
            "daily_budget": self.daily_budget_usd,
            "alert_threshold": self.alert_at_usd,
            "hard_stop": self.hard_stop_usd,
            "llm_enabled": self.llm_enabled,
            "can_use_llm": self.can_use_llm()[0],
            "llm_calls": usage.get("llm_calls", 0),
            "tokens_used": usage.get("tokens_used", 0),
            "cards_created": usage.get("cards_created", 0)
        }
