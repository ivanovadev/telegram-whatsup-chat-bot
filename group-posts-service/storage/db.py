"""SQLite database for storing states, whitelist and usage tracking."""
import sqlite3
import os
from datetime import datetime, date, timedelta
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
        
        # Ukraine news posts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ukraine_news_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT,  -- JSON content
                posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Spider posts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS spider_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                spider_name TEXT NOT NULL,
                content TEXT,  -- JSON content
                posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Track spiders to avoid repetition
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS spiders (
                spider_name TEXT PRIMARY KEY,
                last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Phrase posts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quote_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quote_text TEXT NOT NULL,
                author_name TEXT,
                content TEXT,  -- JSON content
                posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Track phrases to avoid repetition
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quotes (
                quote_text TEXT PRIMARY KEY,
                last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Quote authors tracking (to avoid same images)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quote_authors (
                author_name TEXT PRIMARY KEY,
                last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Africa posts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS africa_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                country TEXT NOT NULL,
                content TEXT,  -- JSON content
                posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Track African countries to avoid repetition
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS africa_countries (
                country_name TEXT PRIMARY KEY,
                last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # London posts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS london_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT,  -- JSON content
                posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # UK posts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS uk_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT,  -- JSON content
                posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Track UK cities to avoid repetition
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS uk_cities (
                city_name TEXT PRIMARY KEY,
                last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Track UK images to avoid repetition
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS uk_images (
                image_location TEXT PRIMARY KEY,
                last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Job posts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS job_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT,  -- JSON content
                posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Track job companies to avoid repetition
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS job_companies (
                company_name TEXT PRIMARY KEY,
                last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Person posts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS person_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                person_name TEXT NOT NULL,
                nationality TEXT,
                category TEXT,
                is_alive INTEGER DEFAULT 0,  -- 1 if alive, 0 if deceased
                is_electrical INTEGER DEFAULT 0,  -- 1 if electrical invention, 0 otherwise
                content TEXT,  -- JSON content
                posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Add new columns if they don't exist (migration)
        try:
            cursor.execute("ALTER TABLE person_posts ADD COLUMN is_alive INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        try:
            cursor.execute("ALTER TABLE person_posts ADD COLUMN is_electrical INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        # Track persons to avoid repetition
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS persons (
                person_name TEXT PRIMARY KEY,
                last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tech posts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tech_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_name TEXT NOT NULL,
                manufacturer TEXT,
                country TEXT,
                category TEXT,
                content TEXT,  -- JSON content
                posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Track tech devices to avoid repetition
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tech_devices (
                device_name TEXT PRIMARY KEY,
                last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Track countries used for tech posts
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tech_countries (
                country_name TEXT PRIMARY KEY,
                last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    
    # ========== Person Posts ==========
    
    def record_person_post(self, content: dict):
        """Record a person post."""
        import json
        conn = self._get_connection()
        cursor = conn.cursor()
        
        person_name = content.get("person_name", "")
        nationality = content.get("nationality", "")
        category = content.get("category", "")
        death_year = content.get("death_year", "")
        is_alive = 1 if (death_year == "Present" or not death_year or death_year == "") else 0
        
        # Check if invention is electrical
        main_invention = content.get("main_invention", "").lower()
        invention_desc = content.get("invention_description", "").lower()
        is_electrical = 1 if any(word in main_invention + " " + invention_desc for word in 
                                ["electric", "electrical", "electricity", "electronic", "electronics", 
                                 "circuit", "voltage", "current", "power system", "ac power", "dc power", 
                                 "transformer", "alternating current", "direct current"]) else 0
        
        cursor.execute("""
            INSERT INTO person_posts (person_name, nationality, category, is_alive, is_electrical, content)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (person_name, nationality, category, is_alive, is_electrical, json.dumps(content)))
        
        conn.commit()
        conn.close()
    
    def get_person_posts_today(self) -> List[Dict[str, Any]]:
        """Get person posts posted today."""
        today = date.today().isoformat()
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM person_posts
            WHERE DATE(posted_at) = ?
            ORDER BY posted_at DESC
        """, (today,))
        
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def record_person(self, person_name: str):
        """Record a person that was used."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO persons (person_name, last_used_at)
            VALUES (?, CURRENT_TIMESTAMP)
        """, (person_name,))
        
        conn.commit()
        conn.close()
    
    # ========== Ukraine News ==========
    
    def record_ukraine_news_post(self, content: dict):
        """Record a Ukraine news post."""
        import json
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO ukraine_news_posts (content)
            VALUES (?)
        """, (json.dumps(content),))
        
        conn.commit()
        conn.close()
    
    def get_ukraine_news_posts_today(self) -> List[Dict[str, Any]]:
        """Get Ukraine news posts posted today."""
        today = date.today().isoformat()
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM ukraine_news_posts
            WHERE DATE(posted_at) = ?
            ORDER BY posted_at DESC
        """, (today,))
        
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    # ========== Spider Posts ==========
    
    def record_spider_post(self, content: dict):
        """Record a spider post."""
        import json
        conn = self._get_connection()
        cursor = conn.cursor()
        
        spider_name = content.get("spider", {}).get("name", "Unknown Spider")
        
        cursor.execute("""
            INSERT INTO spider_posts (spider_name, content)
            VALUES (?, ?)
        """, (spider_name, json.dumps(content)))
        
        conn.commit()
        conn.close()
    
    def get_spider_posts_today(self) -> List[Dict[str, Any]]:
        """Get spider posts posted today."""
        today = date.today().isoformat()
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM spider_posts
            WHERE DATE(posted_at) = ?
            ORDER BY posted_at DESC
        """, (today,))
        
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def record_spider(self, spider_name: str):
        """Record a spider that was used."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO spiders (spider_name, last_used_at)
            VALUES (?, CURRENT_TIMESTAMP)
        """, (spider_name,))
        
        conn.commit()
        conn.close()
    
    def get_used_spiders(self, days: int = 30) -> List[str]:
        """Get spiders used in last N days."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT spider_name FROM spiders
            WHERE last_used_at >= ?
            ORDER BY last_used_at DESC
        """, (cutoff,))
        
        spiders = [row[0] for row in cursor.fetchall()]
        conn.close()
        return spiders
    
    # ========== Phrase Posts ==========
    
    def record_phrase_post(self, content: dict):
        """Record a phrase post."""
        import json
        conn = self._get_connection()
        cursor = conn.cursor()
        
        phrase_text = content.get("phrase", "")
        author_name = content.get("author", "")
        
        # Try to insert into quote_posts first (new table), fallback to phrase_posts (old table)
        try:
            cursor.execute("""
                INSERT INTO quote_posts (quote_text, author_name, content)
                VALUES (?, ?, ?)
            """, (phrase_text, author_name, json.dumps(content)))
        except:
            # Fallback to old table structure
            try:
                cursor.execute("""
                    INSERT INTO phrase_posts (phrase, author, content)
                    VALUES (?, ?, ?)
                """, (phrase_text, author_name, json.dumps(content)))
            except:
                # Try with phrase_text if that column exists
                cursor.execute("""
                    INSERT INTO phrase_posts (phrase_text, author_name, content)
                    VALUES (?, ?, ?)
                """, (phrase_text, author_name, json.dumps(content)))
        
        conn.commit()
        conn.close()
    
    def get_phrase_posts_today(self) -> List[Dict[str, Any]]:
        """Get phrase posts posted today."""
        today = date.today().isoformat()
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT * FROM quote_posts
                WHERE DATE(posted_at) = ?
                ORDER BY posted_at DESC
            """, (today,))
        except:
            cursor.execute("""
                SELECT * FROM phrase_posts
                WHERE DATE(posted_at) = ?
                ORDER BY posted_at DESC
            """, (today,))
        
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def record_phrase(self, phrase_text: str):
        """Record a phrase that was used."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Try quotes table first (new), fallback to phrases (old)
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO quotes (quote_text, last_used_at)
                VALUES (?, CURRENT_TIMESTAMP)
            """, (phrase_text,))
        except:
            # Fallback to old table with 'phrase' column
            cursor.execute("""
                INSERT OR REPLACE INTO phrases (phrase, last_used_at)
                VALUES (?, CURRENT_TIMESTAMP)
            """, (phrase_text,))
        
        conn.commit()
        conn.close()
    
    def get_used_phrases(self, days: int = 30) -> List[str]:
        """Get phrases used in last N days."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Try quotes table first (new), fallback to phrases (old)
        try:
            cursor.execute("""
                SELECT quote_text FROM quotes
                WHERE last_used_at >= ?
                ORDER BY last_used_at DESC
            """, (cutoff,))
        except:
            # Fallback to old table with 'phrase' column
            cursor.execute("""
                SELECT phrase FROM phrases
                WHERE last_used_at >= ?
                ORDER BY last_used_at DESC
            """, (cutoff,))
        
        phrases = [row[0] for row in cursor.fetchall()]
        conn.close()
        return phrases
    
    def record_quote_author(self, author_name: str):
        """Record a quote author that was used (to track image usage)."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO quote_authors (author_name, last_used_at)
                VALUES (?, CURRENT_TIMESTAMP)
            """, (author_name,))
        except:
            # Table doesn't exist yet, skip
            pass
        
        conn.commit()
        conn.close()
    
    def get_used_quote_authors(self, days: int = 30) -> List[str]:
        """Get quote authors used in last N days."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT author_name FROM quote_authors
                WHERE last_used_at >= ?
                ORDER BY last_used_at DESC
            """, (cutoff,))
            authors = [row[0] for row in cursor.fetchall()]
        except:
            authors = []
        
        conn.close()
        return authors
    
    def get_used_persons(self, days: int = 30) -> List[str]:
        """Get persons used in last N days."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT person_name FROM persons
            WHERE last_used_at >= ?
            ORDER BY last_used_at DESC
        """, (cutoff,))
        
        persons = [row[0] for row in cursor.fetchall()]
        conn.close()
        return persons
    
    def get_last_person_posts(self, count: int = 3) -> List[Dict[str, Any]]:
        """Get last N person posts to check distribution."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT is_alive, is_electrical FROM person_posts
            ORDER BY posted_at DESC
            LIMIT ?
        """, (count,))
        
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    # ========== Tech Posts ==========
    
    def record_tech_post(self, content: dict):
        """Record a tech post."""
        import json
        conn = self._get_connection()
        cursor = conn.cursor()
        
        device_name = content.get("device_name", "")
        manufacturer = content.get("manufacturer", "")
        country = content.get("country", "")
        category = content.get("category", "")
        
        cursor.execute("""
            INSERT INTO tech_posts (device_name, manufacturer, country, category, content)
            VALUES (?, ?, ?, ?, ?)
        """, (device_name, manufacturer, country, category, json.dumps(content)))
        
        conn.commit()
        conn.close()
    
    def get_tech_posts_today(self) -> List[Dict[str, Any]]:
        """Get tech posts posted today."""
        today = date.today().isoformat()
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM tech_posts
            WHERE DATE(posted_at) = ?
            ORDER BY posted_at DESC
        """, (today,))
        
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def record_tech_device(self, device_name: str):
        """Record a tech device that was used."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO tech_devices (device_name, last_used_at)
            VALUES (?, CURRENT_TIMESTAMP)
        """, (device_name,))
        
        conn.commit()
        conn.close()
    
    def get_used_tech_devices(self, days: int = 30) -> List[str]:
        """Get tech devices used in last N days."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT device_name FROM tech_devices
            WHERE last_used_at >= ?
            ORDER BY last_used_at DESC
        """, (cutoff,))
        
        devices = [row[0] for row in cursor.fetchall()]
        conn.close()
        return devices
    
    def record_tech_country(self, country_name: str):
        """Record a country used for tech post."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO tech_countries (country_name, last_used_at)
            VALUES (?, CURRENT_TIMESTAMP)
        """, (country_name,))
        
        conn.commit()
        conn.close()
    
    def get_used_tech_countries(self, days: int = 30) -> List[str]:
        """Get countries used for tech posts in last N days."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT country_name FROM tech_countries
            WHERE last_used_at >= ?
            ORDER BY last_used_at DESC
        """, (cutoff,))
        
        countries = [row[0] for row in cursor.fetchall()]
        conn.close()
        return countries
    
    # ========== London Posts ==========
    
    def record_london_post(self, content: dict):
        """Record a London post."""
        import json
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO london_posts (content)
            VALUES (?)
        """, (json.dumps(content),))
        
        conn.commit()
        conn.close()
    
    def get_london_posts_today(self) -> List[Dict[str, Any]]:
        """Get London posts posted today."""
        today = date.today().isoformat()
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM london_posts
            WHERE DATE(posted_at) = ?
            ORDER BY posted_at DESC
        """, (today,))
        
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    # ========== UK Posts ==========
    
    def record_uk_post(self, content: dict):
        """Record a UK post."""
        import json
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO uk_posts (content)
            VALUES (?)
        """, (json.dumps(content),))
        
        conn.commit()
        conn.close()
    
    def get_uk_posts_today(self) -> List[Dict[str, Any]]:
        """Get UK posts posted today."""
        today = date.today().isoformat()
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM uk_posts
            WHERE DATE(posted_at) = ?
            ORDER BY posted_at DESC
        """, (today,))
        
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def record_uk_city(self, city_name: str):
        """Record a UK city that was used."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO uk_cities (city_name, last_used_at)
            VALUES (?, CURRENT_TIMESTAMP)
        """, (city_name,))
        
        conn.commit()
        conn.close()
    
    def get_used_uk_cities(self, days: int = 30) -> List[str]:
        """Get UK cities used in last N days."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT city_name FROM uk_cities
            WHERE last_used_at >= ?
            ORDER BY last_used_at DESC
        """, (cutoff,))
        
        cities = [row[0] for row in cursor.fetchall()]
        conn.close()
        return cities
    
    def record_uk_image(self, image_location: str):
        """Record a UK image location that was used (city or country)."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO uk_images (image_location, last_used_at)
            VALUES (?, CURRENT_TIMESTAMP)
        """, (image_location,))
        
        conn.commit()
        conn.close()
    
    def get_used_uk_images(self, days: int = 7) -> List[str]:
        """Get UK image locations used in last N days."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT image_location FROM uk_images
            WHERE last_used_at >= ?
            ORDER BY last_used_at DESC
        """, (cutoff,))
        
        locations = [row[0] for row in cursor.fetchall()]
        conn.close()
        return locations
    
    # ========== Job Posts ==========
    
    def record_job_post(self, content: dict):
        """Record a job post."""
        import json
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO job_posts (content)
            VALUES (?)
        """, (json.dumps(content),))
        
        conn.commit()
        conn.close()
    
    def get_job_posts_today(self) -> List[Dict[str, Any]]:
        """Get job posts posted today."""
        today = date.today().isoformat()
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM job_posts
            WHERE DATE(posted_at) = ?
            ORDER BY posted_at DESC
        """, (today,))
        
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def record_job_company(self, company_name: str):
        """Record a job company that was used."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO job_companies (company_name, last_used_at)
            VALUES (?, CURRENT_TIMESTAMP)
        """, (company_name,))
        
        conn.commit()
        conn.close()
    
    def get_used_job_companies(self, days: int = 30) -> List[str]:
        """Get job companies used in last N days."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT company_name FROM job_companies
            WHERE last_used_at >= ?
            ORDER BY last_used_at DESC
        """, (cutoff,))
        
        companies = [row[0] for row in cursor.fetchall()]
        conn.close()
        return companies
    
    # ========== Africa Posts ==========
    
    def record_africa_post(self, content: dict):
        """Record an Africa post."""
        import json
        conn = self._get_connection()
        cursor = conn.cursor()
        
        country = content.get("country", "")
        
        cursor.execute("""
            INSERT INTO africa_posts (country, content)
            VALUES (?, ?)
        """, (country, json.dumps(content)))
        
        conn.commit()
        conn.close()
    
    def get_africa_posts_today(self) -> List[Dict[str, Any]]:
        """Get Africa posts posted today."""
        today = date.today().isoformat()
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM africa_posts
            WHERE DATE(posted_at) = ?
            ORDER BY posted_at DESC
        """, (today,))
        
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def record_africa_country(self, country_name: str):
        """Record an Africa country that was used."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO africa_countries (country_name, last_used_at)
            VALUES (?, CURRENT_TIMESTAMP)
        """, (country_name,))
        
        conn.commit()
        conn.close()
    
    def get_used_africa_countries(self, days: int = 30) -> List[str]:
        """Get Africa countries used in last N days."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT country_name FROM africa_countries
            WHERE last_used_at >= ?
            ORDER BY last_used_at DESC
        """, (cutoff,))
        
        countries = [row[0] for row in cursor.fetchall()]
        conn.close()
        return countries