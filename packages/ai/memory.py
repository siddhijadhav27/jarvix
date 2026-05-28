from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json

class ContextManager:
    """Manage conversation context and memory"""
    
    def __init__(self, max_history: int = 10):
        self.max_history = max_history
        self.conversations: Dict[str, List[Dict]] = {}
        self.user_preferences: Dict[str, Dict] = {}
        self.market_context: Dict[str, Any] = {}
    
    def add_message(self, user_id: str, role: str, content: str, metadata: Optional[Dict] = None):
        """Add message to conversation history"""
        if user_id not in self.conversations:
            self.conversations[user_id] = []
        
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        self.conversations[user_id].append(message)
        
        # Keep only last N messages
        if len(self.conversations[user_id]) > self.max_history:
            self.conversations[user_id] = self.conversations[user_id][-self.max_history:]
    
    def get_context(self, user_id: str, limit: int = 5) -> List[Dict]:
        """Get recent conversation context"""
        return self.conversations.get(user_id, [])[-limit:]
    
    def set_preference(self, user_id: str, key: str, value: Any):
        """Set user preference"""
        if user_id not in self.user_preferences:
            self.user_preferences[user_id] = {}
        self.user_preferences[user_id][key] = value
    
    def get_preference(self, user_id: str, key: str, default: Any = None) -> Any:
        """Get user preference"""
        return self.user_preferences.get(user_id, {}).get(key, default)
    
    def update_market_context(self, data: Dict[str, Any]):
        """Update current market context"""
        self.market_context = {
            **data,
            "last_updated": datetime.now().isoformat()
        }
    
    def get_market_context(self) -> Dict[str, Any]:
        """Get current market context"""
        return self.market_context
    
    def clear_history(self, user_id: str):
        """Clear conversation history for user"""
        if user_id in self.conversations:
            self.conversations[user_id] = []
