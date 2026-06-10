"""
Memory System for Jarvix
Stores conversation history and user context in Redis
"""

import json
import redis
from typing import Dict, Any, List, Optional
from datetime import datetime

# Redis connection
redis_client = redis.Redis(
    host='localhost',
    port=6379,
    db=0,
    decode_responses=True
)

class ConversationMemory:
    """Manages conversation history and user context"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.key_prefix = f"jarvix:user:{user_id}"
    
    def _get_key(self, suffix: str) -> str:
        return f"{self.key_prefix}:{suffix}"
    
    def add_message(self, role: str, message: str, intent: str = None):
        """Add a message to conversation history"""
        key = self._get_key("messages")
        
        entry = {
            "role": role,
            "message": message,
            "intent": intent,
            "timestamp": datetime.now().isoformat()
        }
        
        # Add to list (keep last 20)
        redis_client.lpush(key, json.dumps(entry))
        redis_client.ltrim(key, 0, 19)  # Keep only last 20
    
    def get_messages(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent messages"""
        key = self._get_key("messages")
        messages = redis_client.lrange(key, 0, limit - 1)
        
        result = []
        for msg in reversed(messages):  # Oldest first
            try:
                result.append(json.loads(msg))
            except json.JSONDecodeError:
                continue
        
        return result
    
    def get_conversation_context(self, limit: int = 5) -> str:
        """Get formatted conversation context for LLM"""
        messages = self.get_messages(limit)
        
        if not messages:
            return "No previous conversation."
        
        lines = []
        for msg in messages:
            prefix = "User" if msg["role"] == "user" else "Jarvix"
            lines.append(f"{prefix}: {msg['message']}")
        
        return "\n".join(lines)
    
    def update_portfolio(self, portfolio: Dict[str, Any]):
        """Update portfolio information"""
        key = self._get_key("portfolio")
        redis_client.set(key, json.dumps(portfolio))
    
    def get_portfolio(self) -> Dict[str, Any]:
        """Get portfolio information"""
        key = self._get_key("portfolio")
        data = redis_client.get(key)
        
        if data:
            return json.loads(data)
        
        # Default demo portfolio
        return {
            "BTC": {"amount": 0.5, "value": 36542},
            "ETH": {"amount": 100, "value": 199800},
            "SOL": {"amount": 500, "value": 75000},
            "total_value": 311342,
            "total_change_24h": 2.4
        }
    
    def update_preferences(self, preferences: Dict[str, Any]):
        """Update user preferences"""
        key = self._get_key("preferences")
        redis_client.set(key, json.dumps(preferences))
    
    def get_preferences(self) -> Dict[str, Any]:
        """Get user preferences"""
        key = self._get_key("preferences")
        data = redis_client.get(key)
        
        if data:
            return json.loads(data)
        
        return {
            "risk_level": "medium",
            "preferred_assets": ["BTC", "ETH", "SOL"],
            "auto_confirm": False,
            "notifications": True
        }
    
    def get_full_context(self) -> Dict[str, Any]:
        """Get complete user context"""
        return {
            "messages": self.get_messages(),
            "portfolio": self.get_portfolio(),
            "preferences": self.get_preferences(),
            "user_id": self.user_id
        }
    
    def clear_history(self):
        """Clear conversation history"""
        key = self._get_key("messages")
        redis_client.delete(key)


# Global memory store for active users
_active_memories: Dict[str, ConversationMemory] = {}


def get_memory(user_id: str) -> ConversationMemory:
    """Get or create memory for user"""
    if user_id not in _active_memories:
        _active_memories[user_id] = ConversationMemory(user_id)
    
    return _active_memories[user_id]


def format_context_for_llm(memory: ConversationMemory) -> str:
    """Format user context for LLM prompt - LIMITED to prevent confusion"""
    portfolio = memory.get_portfolio()
    
    context_parts = []
    
    # Portfolio summary ONLY (no conversation history in context)
    context_parts.append(f"Portfolio Value: ${portfolio.get('total_value', 0):,.0f}")
    context_parts.append(f"24h Change: {portfolio.get('total_change_24h', 0):+.1f}%")
    
    # Holdings
    holdings = []
    for asset, data in portfolio.items():
        if asset not in ["total_value", "total_change_24h"]:
            holdings.append(f"{asset}: {data.get('amount', 0)} (${data.get('value', 0):,.0f})")
    
    if holdings:
        context_parts.append("Holdings: " + ", ".join(holdings))
    
    return "\n".join(context_parts)
