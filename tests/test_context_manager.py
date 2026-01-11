"""
Unit tests for Context Manager
Tests conversation history, preferences, and persistent storage
"""

import pytest
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from src.context_manager import ContextManager


class TestContextManager:
    """Test context and memory management"""
    
    def test_initialization_no_persistence(self, test_config):
        """Test initialization without persistent memory"""
        test_config.enable_persistent_memory = False
        context = ContextManager(test_config)
        
        assert context.db_path is None
        assert len(context.conversation_history) == 0
        assert len(context.user_preferences) == 0
    
    def test_initialization_with_persistence(self, test_config, temp_db_path):
        """Test initialization with persistent memory"""
        test_config.enable_persistent_memory = True
        test_config.memory_db_path = temp_db_path
        
        context = ContextManager(test_config)
        
        assert context.db_path is not None
        assert Path(temp_db_path).exists()
    
    def test_database_creation(self, test_config, temp_db_path):
        """Test database tables are created correctly"""
        test_config.enable_persistent_memory = True
        test_config.memory_db_path = temp_db_path
        
        context = ContextManager(test_config)
        
        # Check tables exist
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        assert "conversations" in tables
        assert "preferences" in tables
        
        conn.close()
    
    def test_add_message(self, test_config):
        """Test adding messages to history"""
        test_config.enable_persistent_memory = False
        context = ContextManager(test_config)
        
        context.add_message("user", "Hello")
        context.add_message("assistant", "Hi there!")
        
        assert len(context.conversation_history) == 2
        assert context.conversation_history[0]["role"] == "user"
        assert context.conversation_history[0]["content"] == "Hello"
        assert context.conversation_history[1]["role"] == "assistant"
    
    def test_add_message_with_metadata(self, test_config):
        """Test adding messages with metadata"""
        test_config.enable_persistent_memory = False
        context = ContextManager(test_config)
        
        metadata = {"intent": "greeting", "confidence": 0.95}
        context.add_message("user", "Hello", metadata=metadata)
        
        assert context.conversation_history[0]["metadata"] == metadata
    
    def test_add_message_with_persistence(self, test_config, temp_db_path):
        """Test messages are saved to database"""
        test_config.enable_persistent_memory = True
        test_config.memory_db_path = temp_db_path
        
        context = ContextManager(test_config)
        context.add_message("user", "Test message")
        
        # Check database
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM conversations")
        count = cursor.fetchone()[0]
        conn.close()
        
        assert count == 1
    
    def test_get_recent_context(self, test_config):
        """Test retrieving recent context"""
        test_config.enable_persistent_memory = False
        test_config.max_context_length = 5
        context = ContextManager(test_config)
        
        # Add multiple messages
        for i in range(10):
            context.add_message("user" if i % 2 == 0 else "assistant", f"Message {i}")
        
        recent = context.get_recent_context()
        
        assert len(recent) == 5
        assert all("role" in msg and "content" in msg for msg in recent)
    
    def test_get_recent_context_custom_limit(self, test_config):
        """Test retrieving context with custom limit"""
        test_config.enable_persistent_memory = False
        context = ContextManager(test_config)
        
        for i in range(10):
            context.add_message("user", f"Message {i}")
        
        recent = context.get_recent_context(last_n=3)
        
        assert len(recent) == 3
    
    def test_get_full_history(self, test_config):
        """Test retrieving full conversation history"""
        test_config.enable_persistent_memory = False
        context = ContextManager(test_config)
        
        context.add_message("user", "First")
        context.add_message("assistant", "Second")
        context.add_message("user", "Third")
        
        history = context.get_full_history()
        
        assert len(history) == 3
        assert "timestamp" in history[0]
        assert "metadata" in history[0]
    
    def test_search_history(self, test_config):
        """Test searching conversation history"""
        test_config.enable_persistent_memory = False
        context = ContextManager(test_config)
        
        context.add_message("user", "What's the weather like?")
        context.add_message("assistant", "It's sunny today")
        context.add_message("user", "Turn on the lights")
        context.add_message("assistant", "Lights turned on")
        context.add_message("user", "How about the weather tomorrow?")
        
        results = context.search_history("weather")
        
        assert len(results) == 2
        assert all("weather" in msg["content"].lower() for msg in results)
    
    def test_search_history_with_limit(self, test_config):
        """Test search with result limit"""
        test_config.enable_persistent_memory = False
        context = ContextManager(test_config)
        
        for i in range(10):
            context.add_message("user", f"Test message {i}")
        
        results = context.search_history("test", limit=3)
        
        assert len(results) == 3
    
    def test_set_preference(self, test_config):
        """Test setting user preferences"""
        test_config.enable_persistent_memory = False
        context = ContextManager(test_config)
        
        context.set_preference("theme", "dark")
        context.set_preference("voice_speed", 1.2)
        
        assert context.user_preferences["theme"] == "dark"
        assert context.user_preferences["voice_speed"] == 1.2
    
    def test_set_preference_with_persistence(self, test_config, temp_db_path):
        """Test preferences are saved to database"""
        test_config.enable_persistent_memory = True
        test_config.memory_db_path = temp_db_path
        
        context = ContextManager(test_config)
        context.set_preference("language", "en")
        
        # Check database
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM preferences")
        count = cursor.fetchone()[0]
        conn.close()
        
        assert count == 1
    
    def test_get_preference(self, test_config):
        """Test retrieving user preferences"""
        test_config.enable_persistent_memory = False
        context = ContextManager(test_config)
        
        context.set_preference("volume", 50)
        
        assert context.get_preference("volume") == 50
        assert context.get_preference("nonexistent", "default") == "default"
    
    def test_clear_context(self, test_config):
        """Test clearing conversation context"""
        test_config.enable_persistent_memory = False
        context = ContextManager(test_config)
        
        context.add_message("user", "Message 1")
        context.add_message("assistant", "Message 2")
        
        assert len(context.conversation_history) > 0
        
        context.clear_context()
        
        assert len(context.conversation_history) == 0
    
    def test_history_trimming_by_time(self, test_config):
        """Test automatic history trimming by time window"""
        test_config.enable_persistent_memory = False
        test_config.context_window_hours = 24
        context = ContextManager(test_config)
        
        # Add old message (manually set timestamp)
        old_time = (datetime.now() - timedelta(hours=25)).isoformat()
        context.conversation_history.append({
            "timestamp": old_time,
            "role": "user",
            "content": "Old message",
            "metadata": {}
        })
        
        # Add new message
        context.add_message("user", "New message")
        
        # Trim should remove old message
        context._trim_history()
        
        assert len(context.conversation_history) == 1
        assert context.conversation_history[0]["content"] == "New message"
    
    def test_get_stats_empty(self, test_config):
        """Test stats for empty context"""
        test_config.enable_persistent_memory = False
        context = ContextManager(test_config)
        
        stats = context.get_stats()
        
        assert stats["total_messages"] == 0
        assert stats["user_messages"] == 0
        assert stats["assistant_messages"] == 0
        assert stats["oldest_message"] is None
    
    def test_get_stats_with_messages(self, test_config):
        """Test stats with messages"""
        test_config.enable_persistent_memory = False
        context = ContextManager(test_config)
        
        context.add_message("user", "Hello")
        context.add_message("assistant", "Hi")
        context.add_message("user", "How are you?")
        context.add_message("assistant", "I'm good!")
        
        stats = context.get_stats()
        
        assert stats["total_messages"] == 4
        assert stats["user_messages"] == 2
        assert stats["assistant_messages"] == 2
        assert stats["oldest_message"] is not None
        assert stats["newest_message"] is not None
    
    def test_get_stats_with_preferences(self, test_config):
        """Test stats include preference count"""
        test_config.enable_persistent_memory = False
        context = ContextManager(test_config)
        
        context.set_preference("pref1", "value1")
        context.set_preference("pref2", "value2")
        
        stats = context.get_stats()
        
        assert stats["preferences_count"] == 2
    
    def test_save_no_persistence(self, test_config):
        """Test save() with no persistent storage"""
        test_config.enable_persistent_memory = False
        context = ContextManager(test_config)
        
        # Should not raise error
        context.save()
    
    def test_save_with_persistence(self, test_config, temp_db_path):
        """Test save() with persistent storage"""
        test_config.enable_persistent_memory = True
        test_config.memory_db_path = temp_db_path
        
        context = ContextManager(test_config)
        context.add_message("user", "Test")
        
        # Should not raise error
        context.save()
    
    def test_load_from_database(self, test_config, temp_db_path):
        """Test loading data from existing database"""
        test_config.enable_persistent_memory = True
        test_config.memory_db_path = temp_db_path
        
        # Create first context and add data
        context1 = ContextManager(test_config)
        context1.add_message("user", "Persisted message")
        context1.set_preference("test_pref", "test_value")
        
        # Create second context - should load data
        context2 = ContextManager(test_config)
        
        assert len(context2.conversation_history) > 0
        assert context2.get_preference("test_pref") == "test_value"
    
    def test_timestamp_format(self, test_config):
        """Test message timestamps are in ISO format"""
        test_config.enable_persistent_memory = False
        context = ContextManager(test_config)
        
        context.add_message("user", "Test")
        
        timestamp = context.conversation_history[0]["timestamp"]
        # Should be parseable as ISO format
        datetime.fromisoformat(timestamp)  # Will raise if invalid
