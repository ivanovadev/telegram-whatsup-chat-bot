"""Basic tests for database."""
import os
import tempfile
import pytest
from storage.db import Database, CardStatus


@pytest.fixture
def temp_db():
    """Create temporary database for tests."""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    db = Database(path)
    yield db
    os.unlink(path)


def test_create_card(temp_db):
    """Test card creation."""
    result = temp_db.create_card(
        card_id="TEST123",
        from_user_id=12345,
        from_username="testuser",
        original_message_id=1,
        original_text="Test message",
        options=["Option 1", "Option 2", "Option 3"]
    )
    assert result is True
    
    card = temp_db.get_card("TEST123")
    assert card is not None
    assert card['from_user_id'] == 12345
    assert card['status'] == 'pending'
    assert len(card['options']) == 3


def test_whitelist(temp_db):
    """Test whitelist."""
    # Add
    assert temp_db.add_to_whitelist(12345, "testuser") is True
    assert temp_db.is_whitelisted(12345) is True
    assert temp_db.is_whitelisted(99999) is False
    
    # Remove
    assert temp_db.remove_from_whitelist(12345) is True
    assert temp_db.is_whitelisted(12345) is False


def test_card_status(temp_db):
    """Test card status update."""
    temp_db.create_card(
        card_id="TEST123",
        from_user_id=12345,
        from_username="test",
        original_message_id=1,
        original_text="Test",
        options=["1", "2", "3"]
    )
    
    assert temp_db.update_card_status("TEST123", CardStatus.SENT) is True
    card = temp_db.get_card("TEST123")
    assert card['status'] == 'sent'


def test_daily_usage(temp_db):
    """Test daily usage."""
    temp_db.increment_usage(llm_calls=1, tokens=100, estimated_usd=0.01)
    usage = temp_db.get_today_usage()
    assert usage['llm_calls'] == 1
    assert usage['tokens_used'] == 100
    assert usage['estimated_usd'] == 0.01
