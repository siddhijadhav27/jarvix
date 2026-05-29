# market.py
"""Lightweight market context for Jarvix — price, change, volatility"""

import aiohttp
import asyncio
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
from storage import get_storage


class MarketContext:
    """
    Provides lightweight market context for LLM prompts.
    
    Key features:
    - Price data from CoinGecko (free, no key needed)
    - 24h change percentage
    - Market sentiment (bullish/bearish/neutral)
    - Cached for 60 seconds to avoid rate limits
    """
    
    COINGECKO_API = "https://api.coingecko.com/api/v3"
    CACHE_TTL = 60  # seconds
    
    def __init__(self):
        self.storage = get_storage()
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    # ─── Price Fetching ────────────────────────────────
    
    async def get_price(self, asset: str) -> Optional[Dict[str, Any]]:
        """Get current price and 24h change for an asset"""
        asset = asset.lower()
        
        # Check cache first
        cache_key = f"market:price:{asset}"
        cached = self.storage.cache_get(cache_key)
        if cached:
            return cached
        
        # Fetch from CoinGecko
        try:
            session = await self._get_session()
            url = f"{self.COINGECKO_API}/simple/price"
            params = {
                "ids": asset,
                "vs_currencies": "usd",
                "include_24hr_change": "true",
                "include_24hr_vol": "true"
            }
            
            async with session.get(url, params=params, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    if asset in data:
                        result = {
                            "asset": asset.upper(),
                            "price_usd": data[asset].get("usd"),
                            "change_24h": data[asset].get("usd_24h_change"),
                            "volume_24h": data[asset].get("usd_24h_vol"),
                            "timestamp": datetime.now().isoformat()
                        }
                        
                        # Cache for 60 seconds
                        self.storage.cache_set(cache_key, result, self.CACHE_TTL)
                        return result
        
        except Exception as e:
            print(f"[MARKET] Error fetching price for {asset}: {e}")
        
        return None
    
    async def get_multiple_prices(self, assets: list) -> Dict[str, Dict]:
        """Get prices for multiple assets at once"""
        results = {}
        
        for asset in assets:
            price_data = await self.get_price(asset)
            if price_data:
                results[asset.upper()] = price_data
        
        return results
    
    # ─── Market Sentiment ──────────────────────────────
    
    def get_sentiment(self, change_24h: Optional[float]) -> str:
        """Determine market sentiment from 24h change"""
        if change_24h is None:
            return "unknown"
        
        if change_24h > 5:
            return "bullish"
        elif change_24h > 0:
            return "slightly_bullish"
        elif change_24h > -5:
            return "slightly_bearish"
        else:
            return "bearish"
    
    # ─── Context Building ──────────────────────────────
    
    async def build_context(self, asset: str) -> str:
        """Build market context string for LLM prompt"""
        asset = asset.upper()
        
        # Get price data
        price_data = await self.get_price(asset)
        
        if not price_data:
            return f"[Market: No data available for {asset}]"
        
        price = price_data.get("price_usd")
        change = price_data.get("change_24h")
        sentiment = self.get_sentiment(change)
        
        # Format context
        context_parts = [f"[Market Context for {asset}]"]
        
        if price:
            context_parts.append(f"Price: ${price:,.2f}")
        
        if change is not None:
            change_str = f"+{change:.2f}%" if change > 0 else f"{change:.2f}%"
            context_parts.append(f"24h Change: {change_str}")
        
        context_parts.append(f"Sentiment: {sentiment}")
        
        return "\n".join(context_parts)
    
    async def build_multi_context(self, assets: list) -> str:
        """Build market context for multiple assets"""
        contexts = []
        
        for asset in assets:
            ctx = await self.build_context(asset)
            contexts.append(ctx)
        
        return "\n\n".join(contexts)
    
    # ─── Cleanup ───────────────────────────────────────
    
    async def close(self):
        """Close aiohttp session"""
        if self.session and not self.session.closed:
            await self.session.close()


# Synchronous wrapper for testing
def get_market_context_sync(asset: str) -> str:
    """Synchronous wrapper for market context"""
    market = MarketContext()
    
    # Try cache first
    storage = get_storage()
    cache_key = f"market:price:{asset.lower()}"
    cached = storage.cache_get(cache_key)
    
    if cached:
        price = cached.get("price_usd")
        change = cached.get("change_24h")
        sentiment = MarketContext().get_sentiment(change)
        
        return f"[Market Context for {asset}]\nPrice: ${price:,.2f}\n24h Change: {change:+.2f}%\nSentiment: {sentiment}"
    
    return f"[Market Context for {asset}]\nNo cached data available"


# Test
if __name__ == "__main__":
    print("🧪 MarketContext Tests")
    print("=" * 60)
    
    async def run_tests():
        market = MarketContext()
        
        # Test 1: Get ETH price
        print("\n1. Get ETH price")
        eth_data = await market.get_price("ethereum")
        if eth_data:
            print(f"   Price: ${eth_data['price_usd']:,.2f}")
            print(f"   24h Change: {eth_data['change_24h']:+.2f}%")
            print(f"   Sentiment: {market.get_sentiment(eth_data['change_24h'])}")
        else:
            print("   ⚠️ Could not fetch ETH price")
        
        # Test 2: Get BTC price
        print("\n2. Get BTC price")
        btc_data = await market.get_price("bitcoin")
        if btc_data:
            print(f"   Price: ${btc_data['price_usd']:,.2f}")
            print(f"   24h Change: {btc_data['change_24h']:+.2f}%")
        else:
            print("   ⚠️ Could not fetch BTC price")
        
        # Test 3: Cache test
        print("\n3. Cache test (second call should be instant)")
        import time
        start = time.time()
        eth_data2 = await market.get_price("ethereum")
        latency = time.time() - start
        print(f"   Second call latency: {latency*1000:.1f}ms")
        print(f"   Same data: {eth_data2 == eth_data}")
        
        # Test 4: Build context
        print("\n4. Build context for ETH")
        ctx = await market.build_context("ETH")
        print(f"   {ctx}")
        
        # Test 5: Sentiment
        print("\n5. Sentiment tests")
        test_changes = [10.5, 2.0, -1.5, -8.0, None]
        for change in test_changes:
            sentiment = market.get_sentiment(change)
            print(f"   {change}% → {sentiment}")
        
        await market.close()
        print("\n✅ Market tests complete!")
    
    asyncio.run(run_tests())
