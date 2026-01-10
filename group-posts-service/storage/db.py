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
        
        # Channel posts table (to track posted content and avoid duplicates)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS channel_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_type TEXT NOT NULL,  -- 'morning' or 'evening'
                topic TEXT NOT NULL,
                content TEXT,  -- JSON content
                posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Track countries that have been used for images (to avoid repetition)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS image_countries (
                country_name TEXT PRIMARY KEY,
                last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Track news topics to avoid repetition
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS news_topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT NOT NULL,
                posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    
    # ========== Channel Posts ==========
    
    def record_channel_post(self, post_type: str, topic: str, content: dict):
        """Record a channel post to avoid duplicates."""
        import json
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO channel_posts (post_type, topic, content)
            VALUES (?, ?, ?)
        """, (post_type, topic, json.dumps(content)))
        
        conn.commit()
        conn.close()
    
    def get_used_channel_topics(self, days: int = 7) -> List[str]:
        """Get topics used in morning posts in last N days."""
        from datetime import datetime, timedelta
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        cursor.execute("""
            SELECT DISTINCT topic FROM channel_posts
            WHERE post_type = 'morning' AND posted_at >= ?
        """, (cutoff,))
        
        topics = [row[0] for row in cursor.fetchall()]
        conn.close()
        return topics
    
    def get_used_channel_types(self, days: int = 7) -> List[str]:
        """Get travel types used in evening posts in last N days."""
        from datetime import datetime, timedelta
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        cursor.execute("""
            SELECT DISTINCT topic FROM channel_posts
            WHERE post_type = 'evening' AND posted_at >= ?
        """, (cutoff,))
        
        types = [row[0] for row in cursor.fetchall()]
        conn.close()
        return types
    
    def get_channel_posts_today(self, post_type: str) -> List[dict]:
        """Get posts of specific type posted today."""
        from datetime import datetime, date
        conn = self._get_connection()
        cursor = conn.cursor()
        
        today = date.today().isoformat()
        cursor.execute("""
            SELECT * FROM channel_posts
            WHERE post_type = ? AND DATE(posted_at) = ?
        """, (post_type, today))
        
        rows = cursor.fetchall()
        posts = [dict(row) for row in rows]
        conn.close()
        return posts
    
    def get_recent_image_countries(self, days: int = 30) -> List[str]:
        """Get countries that were used for images in the last N days."""
        from datetime import datetime, timedelta
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        cursor.execute("""
            SELECT country_name FROM image_countries
            WHERE last_used_at >= ?
            ORDER BY last_used_at DESC
        """, (cutoff,))
        
        countries = [row[0] for row in cursor.fetchall()]
        conn.close()
        return countries
    
    def get_today_image_countries(self) -> List[str]:
        """Get countries that were used for images today."""
        from datetime import datetime
        conn = self._get_connection()
        cursor = conn.cursor()
        
        today = datetime.now().date().isoformat()
        cursor.execute("""
            SELECT country_name FROM image_countries
            WHERE DATE(last_used_at) = ?
            ORDER BY last_used_at DESC
        """, (today,))
        
        countries = [row[0] for row in cursor.fetchall()]
        conn.close()
        return countries
    
    def record_image_country(self, country_name: str):
        """Record that a country was used for an image."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO image_countries (country_name, last_used_at)
            VALUES (?, CURRENT_TIMESTAMP)
        """, (country_name,))
        
        conn.commit()
        conn.close()
    
    def get_used_news_topics(self, days: int = 7) -> List[str]:
        """Get news topics that were used in the last N days."""
        from datetime import datetime, timedelta
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        cursor.execute("""
            SELECT DISTINCT topic FROM news_topics
            WHERE posted_at >= ?
            ORDER BY posted_at DESC
        """, (cutoff,))
        
        topics = [row[0] for row in cursor.fetchall()]
        conn.close()
        return topics
    
    def record_news_topics(self, topics: List[str]):
        """Record news topics that were posted."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        for topic in topics:
            cursor.execute("""
                INSERT INTO news_topics (topic, posted_at)
                VALUES (?, CURRENT_TIMESTAMP)
            """, (topic,))
        
        conn.commit()
        conn.close()
    
    def has_posted_news_today(self) -> bool:
        """Check if news was already posted today."""
        from datetime import datetime
        conn = self._get_connection()
        cursor = conn.cursor()
        
        today = datetime.now().date().isoformat()
        cursor.execute("""
            SELECT COUNT(*) FROM news_topics
            WHERE DATE(posted_at) = ?
        """, (today,))
        
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0