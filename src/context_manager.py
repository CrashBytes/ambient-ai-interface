"""
Context Manager - Conversation Memory and State Persistence
Maintains conversation history and user context across sessions
"""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

from src.utils.logging import get_logger
from src.utils.config import Config

logger = get_logger(__name__)


class ContextManager:
    """
    Context and Memory Manager
    
    Manages:
    - Conversation history
    - User preferences
    - System state
    - Long-term memory
    """
    
    def __init__(self, config: Config):
        """
        Initialize context manager
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.max_context_length = config.max_context_length
        self.context_window_hours = config.context_window_hours
        
        # In-memory conversation history
        self.conversation_history: List[Dict[str, Any]] = []
        
        # User preferences
        self.user_preferences: Dict[str, Any] = {}
        
        # Initialize persistent storage
        if config.enable_persistent_memory:
            self.db_path = Path(config.memory_db_path)
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._init_database()
            self._load_from_database()
        else:
            self.db_path = None
        
        logger.info("Context manager initialized")
    
    def _init_database(self):
        """Initialize SQLite database for persistent memory"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Create tables
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS preferences (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON conversations(timestamp)
            """)
            
            conn.commit()
            conn.close()
            
            logger.info(f"Database initialized: {self.db_path}")
            
        except Exception as e:
            logger.error(f"Database initialization error: {e}", exc_info=True)
    
    def _load_from_database(self):
        """Load recent context from database"""
        if not self.db_path:
            return
        
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Load recent conversations (within context window)
            cutoff_time = datetime.now() - timedelta(hours=self.context_window_hours)
            cutoff_str = cutoff_time.isoformat()
            
            cursor.execute("""
                SELECT timestamp, role, content, metadata
                FROM conversations
                WHERE timestamp > ?
                ORDER BY timestamp ASC
            """, (cutoff_str,))
            
            for row in cursor.fetchall():
                timestamp, role, content, metadata_str = row
                metadata = json.loads(metadata_str) if metadata_str else {}
                
                self.conversation_history.append({
                    "timestamp": timestamp,
                    "role": role,
                    "content": content,
                    "metadata": metadata
                })
            
            # Load preferences
            cursor.execute("SELECT key, value FROM preferences")
            for key, value_str in cursor.fetchall():
                try:
                    self.user_preferences[key] = json.loads(value_str)
                except json.JSONDecodeError:
                    self.user_preferences[key] = value_str
            
            conn.close()
            
            logger.info(f"Loaded {len(self.conversation_history)} messages from database")
            
        except Exception as e:
            logger.error(f"Database load error: {e}", exc_info=True)
    
    def add_message(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Add a message to conversation history
        
        Args:
            role: Message role ('user' or 'assistant')
            content: Message content
            metadata: Optional metadata dictionary
        """
        timestamp = datetime.now().isoformat()
        
        message = {
            "timestamp": timestamp,
            "role": role,
            "content": content,
            "metadata": metadata or {}
        }
        
        self.conversation_history.append(message)
        
        # Persist to database
        if self.db_path:
            self._save_message_to_db(message)
        
        # Trim history if needed
        self._trim_history()
        
        logger.debug(f"Added {role} message: {content[:50]}...")
    
    def _save_message_to_db(self, message: Dict[str, Any]):
        """Save message to database"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO conversations (timestamp, role, content, metadata)
                VALUES (?, ?, ?, ?)
            """, (
                message["timestamp"],
                message["role"],
                message["content"],
                json.dumps(message["metadata"])
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Database save error: {e}", exc_info=True)
    
    def get_recent_context(self, last_n: Optional[int] = None) -> List[Dict[str, str]]:
        """
        Get recent conversation context
        
        Args:
            last_n: Number of recent messages to return (default: max_context_length)
            
        Returns:
            List of recent messages in format {role, content}
        """
        n = last_n or self.max_context_length
        
        # Get last N messages
        recent_messages = self.conversation_history[-n:]
        
        # Format for GPT-4
        formatted = [
            {
                "role": msg["role"],
                "content": msg["content"]
            }
            for msg in recent_messages
        ]
        
        return formatted
    
    def get_full_history(self) -> List[Dict[str, Any]]:
        """Get complete conversation history"""
        return self.conversation_history.copy()
    
    def search_history(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search conversation history
        
        Args:
            query: Search query
            limit: Maximum results to return
            
        Returns:
            List of matching messages
        """
        query_lower = query.lower()
        
        matches = [
            msg for msg in self.conversation_history
            if query_lower in msg["content"].lower()
        ]
        
        return matches[-limit:]
    
    def set_preference(self, key: str, value: Any):
        """
        Set user preference
        
        Args:
            key: Preference key
            value: Preference value
        """
        self.user_preferences[key] = value
        
        # Persist to database
        if self.db_path:
            self._save_preference_to_db(key, value)
        
        logger.info(f"Set preference: {key} = {value}")
    
    def _save_preference_to_db(self, key: str, value: Any):
        """Save preference to database"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO preferences (key, value, updated_at)
                VALUES (?, ?, ?)
            """, (key, json.dumps(value), datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Preference save error: {e}", exc_info=True)
    
    def get_preference(self, key: str, default: Any = None) -> Any:
        """Get user preference"""
        return self.user_preferences.get(key, default)
    
    def clear_context(self):
        """Clear conversation history"""
        logger.info("Clearing conversation context")
        self.conversation_history.clear()
    
    def _trim_history(self):
        """Trim history to context window"""
        if not self.context_window_hours:
            return
        
        cutoff_time = datetime.now() - timedelta(hours=self.context_window_hours)
        
        # Remove old messages
        self.conversation_history = [
            msg for msg in self.conversation_history
            if datetime.fromisoformat(msg["timestamp"]) > cutoff_time
        ]
    
    def save(self):
        """Save current state (called on shutdown)"""
        if self.db_path:
            logger.info("Context saved to database")
        else:
            logger.info("No persistent storage configured")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get context statistics"""
        if not self.conversation_history:
            return {
                "total_messages": 0,
                "user_messages": 0,
                "assistant_messages": 0,
                "oldest_message": None,
                "newest_message": None
            }
        
        user_count = sum(1 for msg in self.conversation_history if msg["role"] == "user")
        assistant_count = len(self.conversation_history) - user_count
        
        return {
            "total_messages": len(self.conversation_history),
            "user_messages": user_count,
            "assistant_messages": assistant_count,
            "oldest_message": self.conversation_history[0]["timestamp"],
            "newest_message": self.conversation_history[-1]["timestamp"],
            "preferences_count": len(self.user_preferences)
        }
