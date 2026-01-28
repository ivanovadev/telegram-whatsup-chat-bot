"""Neo4j graph database service for conversation and knowledge graphs."""
import os
from typing import Optional, List, Dict, Any
from datetime import datetime
from neo4j import GraphDatabase
import logging

logger = logging.getLogger(__name__)


class Neo4jService:
    """Service for managing Neo4j graph database."""
    
    def __init__(self):
        """Initialize Neo4j connection."""
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "password")
        
        self.enabled = os.getenv("NEO4J_ENABLED", "off").lower() == "on"
        
        if not self.enabled:
            logger.info("Neo4j is disabled")
            self.driver = None
            return
        
        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            # Test connection
            with self.driver.session() as session:
                session.run("RETURN 1")
            logger.info("Neo4j connected successfully")
            self._create_indexes()
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            self.driver = None
            self.enabled = False
    
    def _create_indexes(self):
        """Create indexes for better performance."""
        if not self.enabled or not self.driver:
            return
        
        indexes = [
            "CREATE INDEX user_id_index IF NOT EXISTS FOR (u:User) ON (u.user_id)",
            "CREATE INDEX message_id_index IF NOT EXISTS FOR (m:Message) ON (m.message_id)",
            "CREATE INDEX card_id_index IF NOT EXISTS FOR (c:Card) ON (c.card_id)",
            "CREATE INDEX country_name_index IF NOT EXISTS FOR (c:Country) ON (c.name)",
            "CREATE INDEX topic_name_index IF NOT EXISTS FOR (t:Topic) ON (t.name)",
        ]
        
        with self.driver.session() as session:
            for index_query in indexes:
                try:
                    session.run(index_query)
                except Exception as e:
                    logger.warning(f"Index creation warning: {e}")
    
    def close(self):
        """Close Neo4j connection."""
        if self.driver:
            self.driver.close()
    
    # ========== Conversation Graph ==========
    
    def create_or_update_user(
        self,
        user_id: int,
        username: Optional[str] = None,
        is_husband: bool = False,
        is_friend: bool = False
    ) -> bool:
        """Create or update user node."""
        if not self.enabled or not self.driver:
            return False
        
        try:
            with self.driver.session() as session:
                session.run("""
                    MERGE (u:User {user_id: $user_id})
                    SET u.username = $username,
                        u.is_husband = $is_husband,
                        u.is_friend = $is_friend,
                        u.last_seen = datetime()
                    RETURN u
                """, user_id=user_id, username=username, 
                    is_husband=is_husband, is_friend=is_friend)
            return True
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return False
    
    def create_message(
        self,
        message_id: int,
        user_id: int,
        text: str,
        timestamp: Optional[datetime] = None
    ) -> bool:
        """Create message node and link to user."""
        if not self.enabled or not self.driver:
            return False
        
        try:
            with self.driver.session() as session:
                session.run("""
                    MATCH (u:User {user_id: $user_id})
                    CREATE (m:Message {
                        message_id: $message_id,
                        text: $text,
                        timestamp: coalesce($timestamp, datetime())
                    })
                    CREATE (u)-[:SENT]->(m)
                """, message_id=message_id, user_id=user_id, 
                    text=text, timestamp=timestamp)
            return True
        except Exception as e:
            logger.error(f"Error creating message: {e}")
            return False
    
    def create_card(
        self,
        card_id: str,
        user_id: int,
        original_message_id: int,
        original_text: str,
        options: List[str],
        selected_option: Optional[int] = None
    ) -> bool:
        """Create card node and link to message and user."""
        if not self.enabled or not self.driver:
            return False
        
        try:
            with self.driver.session() as session:
                # Create card
                session.run("""
                    MATCH (u:User {user_id: $user_id})
                    MATCH (m:Message {message_id: $original_message_id})
                    CREATE (c:Card {
                        card_id: $card_id,
                        original_text: $original_text,
                        options: $options,
                        selected_option: $selected_option,
                        created_at: datetime()
                    })
                    CREATE (m)-[:GENERATED]->(c)
                    CREATE (u)-[:RECEIVED]->(c)
                """, card_id=card_id, user_id=user_id,
                    original_message_id=original_message_id,
                    original_text=original_text, options=options,
                    selected_option=selected_option)
            return True
        except Exception as e:
            logger.error(f"Error creating card: {e}")
            return False
    
    def update_card_selection(self, card_id: str, selected_option: int) -> bool:
        """Update card with selected option."""
        if not self.enabled or not self.driver:
            return False
        
        try:
            with self.driver.session() as session:
                session.run("""
                    MATCH (c:Card {card_id: $card_id})
                    SET c.selected_option = $selected_option,
                        c.sent_at = datetime()
                """, card_id=card_id, selected_option=selected_option)
            return True
        except Exception as e:
            logger.error(f"Error updating card: {e}")
            return False
    
    def extract_and_link_topics(self, message_id: int, topics: List[str]) -> bool:
        """Extract topics from message and create relationships."""
        if not self.enabled or not self.driver:
            return False
        
        try:
            with self.driver.session() as session:
                for topic in topics:
                    session.run("""
                        MATCH (m:Message {message_id: $message_id})
                        MERGE (t:Topic {name: $topic})
                        MERGE (m)-[:MENTIONS]->(t)
                    """, message_id=message_id, topic=topic.lower())
            return True
        except Exception as e:
            logger.error(f"Error linking topics: {e}")
            return False
    
    # ========== Travel Knowledge Graph ==========
    
    def create_or_update_country(
        self,
        country_name: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Create or update country node."""
        if not self.enabled or not self.driver:
            return False
        
        try:
            props = properties or {}
            props['name'] = country_name
            props['updated_at'] = datetime.now().isoformat()
            
            with self.driver.session() as session:
                session.run("""
                    MERGE (c:Country {name: $name})
                    SET c += $properties
                """, name=country_name, properties=props)
            return True
        except Exception as e:
            logger.error(f"Error creating country: {e}")
            return False
    
    def link_country_to_topic(
        self,
        country_name: str,
        topic_name: str,
        rank: Optional[int] = None
    ) -> bool:
        """Link country to topic with optional ranking."""
        if not self.enabled or not self.driver:
            return False
        
        try:
            with self.driver.session() as session:
                props = {}
                if rank is not None:
                    props['rank'] = rank
                
                session.run("""
                    MATCH (c:Country {name: $country_name})
                    MERGE (t:Topic {name: $topic_name})
                    MERGE (c)-[r:APPEARS_IN]->(t)
                    SET r += $props
                """, country_name=country_name, topic_name=topic_name, props=props)
            return True
        except Exception as e:
            logger.error(f"Error linking country to topic: {e}")
            return False
    
    def link_countries(self, country1: str, country2: str, relationship: str = "RELATED") -> bool:
        """Link two countries with a relationship."""
        if not self.enabled or not self.driver:
            return False
        
        try:
            with self.driver.session() as session:
                session.run("""
                    MATCH (c1:Country {name: $country1})
                    MATCH (c2:Country {name: $country2})
                    MERGE (c1)-[r:RELATED_TO]->(c2)
                    SET r.type = $relationship,
                        r.updated_at = datetime()
                """, country1=country1, country2=country2, relationship=relationship)
            return True
        except Exception as e:
            logger.error(f"Error linking countries: {e}")
            return False
    
    def record_post(
        self,
        post_type: str,
        topic: str,
        countries: List[str],
        content: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Record a channel/group post in the graph."""
        if not self.enabled or not self.driver:
            return False
        
        try:
            with self.driver.session() as session:
                # Create post node with timestamp
                posted_at = datetime.now().isoformat()
                session.run("""
                    MERGE (t:Topic {name: $topic})
                    CREATE (p:Post {
                        post_type: $post_type,
                        topic: $topic,
                        posted_at: $posted_at,
                        content: $content
                    })
                    CREATE (p)-[:ABOUT]->(t)
                """, post_type=post_type, topic=topic, 
                    posted_at=posted_at, content=content)
                
                # Link countries
                for i, country in enumerate(countries):
                    if country:  # Skip empty country names
                        session.run("""
                            MATCH (p:Post {posted_at: $posted_at})
                            MERGE (c:Country {name: $country})
                            MERGE (p)-[r:FEATURES]->(c)
                            SET r.rank = $rank
                        """, posted_at=posted_at, country=country, rank=i+1)
            
            return True
        except Exception as e:
            logger.error(f"Error recording post: {e}")
            return False
    
    # ========== Analytics & Recommendations ==========
    
    def get_user_conversation_topics(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most discussed topics by user."""
        if not self.enabled or not self.driver:
            return []
        
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (u:User {user_id: $user_id})-[:SENT]->(m:Message)-[:MENTIONS]->(t:Topic)
                    RETURN t.name AS topic, COUNT(*) AS count
                    ORDER BY count DESC
                    LIMIT $limit
                """, user_id=user_id, limit=limit)
                
            return [{"topic": record["topic"], "count": record["count"]} 
                    for record in result]
        except Exception as e:
            logger.error(f"Error getting user topics: {e}")
            return []
    
    def get_related_countries(self, country_name: str, limit: int = 5) -> List[str]:
        """Get countries related to given country based on shared topics."""
        if not self.enabled or not self.driver:
            return []
        
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (c1:Country {name: $country_name})-[:APPEARS_IN]->(t:Topic)<-[:APPEARS_IN]-(c2:Country)
                    WHERE c1 <> c2
                    RETURN DISTINCT c2.name AS country, COUNT(t) AS shared_topics
                    ORDER BY shared_topics DESC
                    LIMIT $limit
                """, country_name=country_name, limit=limit)
                
            return [record["country"] for record in result]
        except Exception as e:
            logger.error(f"Error getting related countries: {e}")
            return []
    
    def get_popular_topics(self, days: int = 30, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most popular topics in conversations."""
        if not self.enabled or not self.driver:
            return []
        
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (m:Message)-[:MENTIONS]->(t:Topic)
                    WHERE m.timestamp >= datetime() - duration({days: $days})
                    RETURN t.name AS topic, COUNT(*) AS count
                    ORDER BY count DESC
                    LIMIT $limit
                """, days=days, limit=limit)
                
            return [{"topic": record["topic"], "count": record["count"]} 
                    for record in result]
        except Exception as e:
            logger.error(f"Error getting popular topics: {e}")
            return []
    
    def get_user_similarity(self, user_id1: int, user_id2: int) -> float:
        """Calculate similarity between two users based on shared topics."""
        if not self.enabled or not self.driver:
            return 0.0
        
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (u1:User {user_id: $user_id1})-[:SENT]->(m1:Message)-[:MENTIONS]->(t:Topic)<-[:MENTIONS]-(m2:Message)<-[:SENT]-(u2:User {user_id: $user_id2})
                    RETURN COUNT(DISTINCT t) AS shared_topics
                """, user_id1=user_id1, user_id2=user_id2)
                
                record = result.single()
                if record:
                    shared = record["shared_topics"]
                    # Simple similarity: shared topics / (total unique topics for both users)
                    # This is a simplified version
                    return min(shared / 10.0, 1.0) if shared > 0 else 0.0
            return 0.0
        except Exception as e:
            logger.error(f"Error calculating user similarity: {e}")
            return 0.0
    
    def get_recommended_countries_for_topic(self, topic: str, limit: int = 5) -> List[str]:
        """Get countries recommended for a topic based on graph relationships."""
        if not self.enabled or not self.driver:
            return []
        
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (t:Topic {name: $topic})<-[:APPEARS_IN]-(c:Country)
                    OPTIONAL MATCH (c)-[:APPEARS_IN]->(related_topic:Topic)
                    WHERE related_topic <> t
                    RETURN c.name AS country, 
                           COUNT(DISTINCT related_topic) AS related_topics,
                           COUNT(*) AS appearances
                    ORDER BY appearances DESC, related_topics DESC
                    LIMIT $limit
                """, topic=topic, limit=limit)
                
            return [record["country"] for record in result]
        except Exception as e:
            logger.error(f"Error getting recommended countries: {e}")
            return []

