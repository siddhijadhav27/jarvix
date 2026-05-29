# cache.py
"""Response caching for Jarvix AI commands"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Callable, Optional

class ResponseCache:
    def __init__(self):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.lock = asyncio.Lock()
    
    def _cache_key(self, intent: str, asset: str) -> str:
        return f"{intent}:{asset.upper()}"
    
    async def get_or_fetch(
        self,
        intent: str,
        asset: str,
        ttl_seconds: int,
        fetch_fn: Callable
    ) -> Any:
        """Get from cache or fetch and store"""
        key = self._cache_key(intent, asset)
        
        async with self.lock:
            if key in self.cache:
                entry = self.cache[key]
                if datetime.now() < entry["expires"]:
                    print(f"[CACHE HIT] {key} — returning instantly")
                    return entry["data"]
        
        # Cache miss — fetch for real
        print(f"[CACHE MISS] {key} — calling LLM")
        data = await fetch_fn()
        
        async with self.lock:
            self.cache[key] = {
                "data": data,
                "expires": datetime.now() + timedelta(seconds=ttl_seconds)
            }
        
        return data
    
    async def invalidate(self, intent: str, asset: str):
        """Invalidate cache entry"""
        key = self._cache_key(intent, asset)
        async with self.lock:
            if key in self.cache:
                del self.cache[key]
    
    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics"""
        return {
            "entries": len(self.cache),
            "intents": list(set(k.split(":")[0] for k in self.cache.keys()))
        }


# TTL by intent type
CACHE_TTL = {
    "price":           30,   # Price updates every 30s
    "market_analysis": 300,  # Analysis valid for 5 minutes
    "advice":          120,  # Advice valid for 2 minutes
    "portfolio":       60,   # Portfolio valid for 1 minute
    "buy":             0,    # Never cache trades
    "sell":            0,    # Never cache trades
}


# Global cache instance
_cache_instance = None

def get_cache() -> ResponseCache:
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = ResponseCache()
    return _cache_instance