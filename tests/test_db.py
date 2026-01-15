"""Basic tests for database."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

# Add auto-reply-service to path for imports (using service-specific storage)
project_root = Path(__file__).parent.parent
auto_reply_service = project_root / "auto-reply-service"
sys.path.insert(0, str(auto_reply_service))

try:
    from storage.db import Database, CardStatus
except ImportError:
    # If storage.db is not available, skip tests
    Database = None
    CardStatus = None


class TestDatabase(unittest.TestCase):
    """Test cases for database operations."""
    
    def setUp(self):
        """Create temporary database for tests."""
        if Database is None:
            self.skipTest("storage.db module not available")
        
        self.fd, self.db_path = tempfile.mkstemp(suffix='.db')
        os.close(self.fd)
        self.db = Database(self.db_path)
    
    def tearDown(self):
        """Clean up temporary database."""
        if hasattr(self, 'db_path') and os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    def test_create_card(self):
        """Test card creation."""
        result = self.db.create_card(
            card_id="TEST123",
            from_user_id=12345,
            from_username="testuser",
            original_message_id=1,
            original_text="Test message",
            options=["Option 1", "Option 2", "Option 3"]
        )
        self.assertTrue(result)
        
        card = self.db.get_card("TEST123")
        self.assertIsNotNone(card)
        self.assertEqual(card['from_user_id'], 12345)
        self.assertEqual(card['status'], 'pending')
        self.assertEqual(len(card['options']), 3)
    
    def test_whitelist(self):
        """Test whitelist operations."""
        # Add to whitelist
        self.assertTrue(self.db.add_to_whitelist(12345, "testuser"))
        self.assertTrue(self.db.is_whitelisted(12345))
        self.assertFalse(self.db.is_whitelisted(99999))
        
        # Remove from whitelist
        self.assertTrue(self.db.remove_from_whitelist(12345))
        self.assertFalse(self.db.is_whitelisted(12345))
    
    def test_card_status(self):
        """Test card status update."""
        self.db.create_card(
            card_id="TEST123",
            from_user_id=12345,
            from_username="test",
            original_message_id=1,
            original_text="Test",
            options=["1", "2", "3"]
        )
        
        self.assertTrue(self.db.update_card_status("TEST123", CardStatus.SENT))
        card = self.db.get_card("TEST123")
        self.assertEqual(card['status'], 'sent')
    
    def test_daily_usage(self):
        """Test daily usage tracking."""
        self.db.increment_usage(llm_calls=1, tokens=100, estimated_usd=0.01)
        usage = self.db.get_today_usage()
        self.assertEqual(usage['llm_calls'], 1)
        self.assertEqual(usage['tokens_used'], 100)
        self.assertAlmostEqual(usage['estimated_usd'], 0.01, places=2)


if __name__ == "__main__":
    unittest.main()
