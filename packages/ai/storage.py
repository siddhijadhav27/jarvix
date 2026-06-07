# storage.py
"""Redis persistence layer for Jarvix memory"""

import redis
import json
from datetime import timedelta
from typing import Optional, Dict, Any, List

class PersistentStorage:
    """Redis-backed persistent storage"""
    
    def __init__(self, host='localhost', port=6379, db=0):
        self.redis = redis.Redis(
            host=host,
            port=port,
            db=db,
            decode_responses=True
        )
        
        # Verify connection
        try:
            self.redis.ping()
            print("✅ Redis connected")
        except redis.ConnectionError:
            print("❌ Redis connection failed")
            raise
    
    # ─── Profile Storage ───────────────────────────────
    
    def save_profile(self, user_id: str, profile: dict):
        """Save user profile with 90-day TTL"""
        key = f"profile:{user_id}"
        self.redis.setex(
            key,
            timedelta(days=90),
            json.dumps(profile)
        )
    
    def load_profile(self, user_id: str) -> Optional[dict]:
        """Load user profile"""
        key = f"profile:{user_id}"
        data = self.redis.get(key)
        return json.loads(data) if data else None
    
    def delete_profile(self, user_id: str):
        """Delete user profile"""
        key = f"profile:{user_id}"
        self.redis.delete(key)
    
    # ─── Conversation Storage ──────────────────────────
    
    def save_conversation(self, session_id: str, messages: list):
        """Save conversation with 24h TTL"""
        key = f"conv:{session_id}"
        self.redis.setex(
            key,
            timedelta(hours=24),
            json.dumps(messages)
        )
    
    def load_conversation(self, session_id: str) -> list:
        """Load conversation"""
        key = f"conv:{session_id}"
        data = self.redis.get(key)
        return json.loads(data) if data else []
    
    def append_message(self, session_id: str, message: dict):
        """Append single message to conversation"""
        messages = self.load_conversation(session_id)
        messages.append(message)
        self.save_conversation(session_id, messages)
    
    # ─── User Session Mapping ──────────────────────────
    
    def save_user_session(self, user_id: str, session_id: str):
        """Map user to active session"""
        key = f"user_session:{user_id}"
        self.redis.setex(
            key,
            timedelta(hours=24),
            session_id
        )
    
    def get_user_session(self, user_id: str) -> Optional[str]:
        """Get user's active session"""
        key = f"user_session:{user_id}"
        return self.redis.get(key)
    
    # ─── Cache Storage ─────────────────────────────────
    
    def cache_set(self, key: str, value: Any, ttl_seconds: int):
        """Generic cache set"""
        self.redis.setex(
            key,
            timedelta(seconds=ttl_seconds),
            json.dumps(value)
        )
    
    def cache_get(self, key: str) -> Optional[Any]:
        """Generic cache get"""
        data = self.redis.get(key)
        return json.loads(data) if data else None
    
    def cache_delete(self, key: str):
        """Delete cache entry"""
        self.redis.delete(key)
    
    # ─── Statistics ────────────────────────────────────
    
    def get_stats(self) -> dict:
        """Get storage statistics"""
        info = self.redis.info()
        return {
            "connected": True,
            "keys": self.redis.dbsize(),
            "memory_used": info.get("used_memory_human", "unknown"),
            "uptime": info.get("uptime_in_seconds", 0)
        }


# Global storage instance
_storage_instance = None

def get_storage() -> PersistentStorage:
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = PersistentStorage()
    return _storage_instance


# Test
if __name__ == "__main__":
    storage = get_storage()
    
    print("\n🧪 Storage Tests")
    print("=" * 60)
    
    # Test profile
    storage.save_profile("user_123", {
        "risk_tolerance": "moderate",
        "usual_amounts": {"ETH": 0.5}
    })
    profile = storage.load_profile("user_123")
    print(f"✅ Profile: {profile}")
    
    # Test conversation
    storage.save_conversation("session_abc", [
        {"role": "user", "content": "Price of BTC"},
        {"role": "assistant", "content": "$45,000"}
    ])
    conv = storage.load_conversation("session_abc")
    print(f"✅ Conversation: {len(conv)} messages")
    
    # Test cache
    storage.cache_set("price:BTC", {"price": 45000}, 30)
    cached = storage.cache_get("price:BTC")
    print(f"✅ Cache: {cached}")
    
    # Stats
    print(f"\n📊 Stats: {storage.get_stats()}")
