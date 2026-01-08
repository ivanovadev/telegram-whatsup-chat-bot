"""SQLite database for storing states, whitelist and usage tracking."""
import sqlite3
import os
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from enum import Enum


class CardStatus(Enum):
    """Card statuses."""
    PENDING = "pending"
    SENT = "sent"
    DECLINED = "declined"
    EXPIRED = "expired"


class Database:
    """Class for working with SQLite database."""
    
    def __init__(self, db_path: str = "./data/bot.db"):
        """Initialize database."""
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._init_db()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_db(self):
        """Create tables if they don't exist."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Cards table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cards (
                card_id TEXT PRIMARY KEY,
                from_user_id INTEGER NOT NULL,
                from_username TEXT,
                original_message_id INTEGER,
                original_text TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sent_at TIMESTAMP,
                options TEXT  -- JSON with 3 response options
            )
        """)
        
        # Whitelist table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS whitelist (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Daily usage table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_usage (
                date TEXT PRIMARY KEY,
                llm_calls INTEGER DEFAULT 0,
                tokens_used INTEGER DEFAULT 0,
                estimated_usd REAL DEFAULT 0.0,
                cards_created INTEGER DEFAULT 0
            )
        """)
        
        # Cooldown table (last card creation time for user)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_cooldown (
                user_id INTEGER PRIMARY KEY,
                last_card_at TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    
    # ========== Cards ==========
    
    def create_card(
        self,
        card_id: str,
        from_user_id: int,
        from_username: Optional[str],
        original_message_id: int,
        original_text: str,
        options: List[str]
    ) -> bool:
        """Create a new card."""
        import json
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO cards (card_id, from_user_id, from_username, 
                                 original_message_id, original_text, options)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (card_id, from_user_id, from_username, original_message_id, 
                  original_text, json.dumps(options)))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()
    
    def get_card(self, card_id: str) -> Optional[Dict[str, Any]]:
        """Get card by ID."""
        import json
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM cards WHERE card_id = ?", (card_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            result = dict(row)
            if result.get('options'):
                result['options'] = json.loads(result['options'])
            return result
        return None
    
    def update_card_status(
        self,
        card_id: str,
        status: CardStatus,
        sent_at: Optional[datetime] = None
    ) -> bool:
        """Update card status."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE cards 
            SET status = ?, sent_at = ?
            WHERE card_id = ?
        """, (status.value, sent_at, card_id))
        
        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return updated
    
    def get_pending_cards(self) -> List[Dict[str, Any]]:
        """Get all pending cards."""
        import json
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM cards 
            WHERE status = 'pending'
            ORDER BY created_at DESC
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        result = []
        for row in rows:
            card = dict(row)
            if card.get('options'):
                card['options'] = json.loads(card['options'])
            result.append(card)
        return result
    
    # ========== Whitelist ==========
    
    def add_to_whitelist(self, user_id: int, username: Optional[str] = None) -> bool:
        """Add user to whitelist."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO whitelist (user_id, username)
                VALUES (?, ?)
            """, (user_id, username))
            conn.commit()
            return True
        except Exception:
            return False
        finally:
            conn.close()
    
    def remove_from_whitelist(self, user_id: int) -> bool:
        """Remove user from whitelist."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM whitelist WHERE user_id = ?", (user_id,))
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return deleted
    
    def is_whitelisted(self, user_id: int) -> bool:
        """Check if user is in whitelist."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT 1 FROM whitelist WHERE user_id = ?", (user_id,))
        result = cursor.fetchone() is not None
        conn.close()
        return result
    
    def get_whitelist(self) -> List[Dict[str, Any]]:
        """Get entire whitelist."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM whitelist ORDER BY added_at DESC")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    # ========== Cooldown ==========
    
    def update_user_cooldown(self, user_id: int):
        """Update last card time for user."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO user_cooldown (user_id, last_card_at)
            VALUES (?, CURRENT_TIMESTAMP)
        """, (user_id,))
        conn.commit()
        conn.close()
    
    def get_user_cooldown(self, user_id: int) -> Optional[datetime]:
        """Get last card time for user."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT last_card_at FROM user_cooldown WHERE user_id = ?
        """, (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row and row[0]:
            return datetime.fromisoformat(row[0])
        return None
    
    # ========== Daily Usage ==========
    
    def get_today_usage(self) -> Dict[str, Any]:
        """Get today's usage."""
        today = date.today().isoformat()
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM daily_usage WHERE date = ?
        """, (today,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return {
            'date': today,
            'llm_calls': 0,
            'tokens_used': 0,
            'estimated_usd': 0.0,
            'cards_created': 0
        }
    
    def increment_usage(
        self,
        llm_calls: int = 0,
        tokens: int = 0,
        estimated_usd: float = 0.0,
        cards: int = 0
    ):
        """Increment today's usage counters."""
        today = date.today().isoformat()
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO daily_usage (date, llm_calls, tokens_used, estimated_usd, cards_created)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(date) DO UPDATE SET
                llm_calls = llm_calls + ?,
                tokens_used = tokens_used + ?,
                estimated_usd = estimated_usd + ?,
                cards_created = cards_created + ?
        """, (today, llm_calls, tokens, estimated_usd, cards,
              llm_calls, tokens, estimated_usd, cards))
        
        conn.commit()
        conn.close()
