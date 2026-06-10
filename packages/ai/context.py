# context.py
"""Context integration layer — combines profile, memory, and market context"""

from typing import Dict, Any, Optional
from profile import UserProfile
from memory import ConversationMemory
from market import MarketContext

# Asset symbol to CoinGecko ID mapping
ASSET_SYMBOLS = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "BNB": "binancecoin",
    "ADA": "cardano",
    "DOT": "polkadot",
    "AVAX": "avalanche-2",
    "MATIC": "matic-network",
    "LINK": "chainlink",
    "UNI": "uniswap",
}

def resolve_asset_symbol(symbol: str) -> str:
    """Convert common symbol to CoinGecko ID"""
    return ASSET_SYMBOLS.get(symbol.upper(), symbol.lower())
import asyncio


class JarvixContext:
    """
    Integrates all context sources into a single prompt for the LLM.
    
    Sources:
    1. User Profile — learned behavior, risk tolerance
    2. Conversation Memory — recent messages, pronoun resolution
    3. Market Context — price, change, sentiment
    """
    
    def __init__(self, user_id: str, session_id: str):
        self.user_id = user_id
        self.session_id = session_id
        self.profile = UserProfile(user_id)
        self.memory = ConversationMemory(session_id)
        self.market = MarketContext()
    
    async def build_prompt(self, message: str, intent: str, entities: Dict[str, Any]) -> str:
        """
        Build complete prompt with all context.
        
        Returns a structured prompt that includes:
        - User profile context
        - Conversation history
        - Market data
        - Resolved message (with pronouns fixed)
        """
        
        parts = []
        
        # ─── User Profile Context ──────────────────────
        parts.append("=== USER PROFILE ===")
        parts.append(f"Risk Tolerance: {self.profile.risk_tolerance}")
        
        if self.profile.usual_amounts:
            parts.append("Usual Trade Sizes:")
            for asset, amount in self.profile.usual_amounts.items():
                parts.append(f"  {asset}: {amount}")
        
        if self.profile.trade_counts:
            parts.append("Trade History:")
            for asset, count in self.profile.trade_counts.items():
                parts.append(f"  {asset}: {count} trades")
        
        # ─── Market Context ────────────────────────────
        asset = entities.get("asset")
        if asset:
            parts.append("\n=== MARKET CONTEXT ===")
            # Map symbol to CoinGecko ID
            cg_id = resolve_asset_symbol(asset)
            market_ctx = await self.market.build_context(cg_id)
            parts.append(market_ctx)
        
        # ─── Conversation History ──────────────────────
        parts.append("\n=== CONVERSATION HISTORY ===")
        recent = self.memory.get_last(3)
        if recent:
            for msg in recent:
                role = "User" if msg["role"] == "user" else "Jarvix"
                parts.append(f"{role}: {msg['content'][:80]}")
        else:
            parts.append("No previous conversation.")
        
        # ─── Current Message ───────────────────────────
        parts.append("\n=== CURRENT MESSAGE ===")
        
        # Resolve pronouns
        resolved = self.memory.resolve_references(message)
        parts.append(f"Intent: {intent}")
        parts.append(f"Entities: {entities}")
        parts.append(f"Message: {resolved}")
        
        # ─── Instructions ──────────────────────────────
        parts.append("\n=== INSTRUCTIONS ===")
        parts.append("1. Consider user's risk tolerance in your response")
        parts.append("2. Reference market context if relevant")
        parts.append("3. Maintain conversation continuity")
        parts.append("4. Be concise but informative")
        
        return "\n".join(parts)
    
    def add_to_memory(self, role: str, content: str, entities: Optional[Dict] = None):
        """Add message to conversation memory"""
        self.memory.add(role, content, entities)
    
    def learn_from_trade(self, asset: str, amount: float, usd_value: float):
        """Update profile after confirmed trade"""
        self.profile.learn_from_trade(asset, amount, usd_value)
    
    async def close(self):
        """Cleanup"""
        await self.market.close()


# Test
if __name__ == "__main__":
    print("🧪 JarvixContext Tests")
    print("=" * 60)
    
    async def run_tests():
        # Test 1: Build prompt with all context
        print("\n1. Build prompt with profile + memory + market")
        
        ctx = JarvixContext("user_123", "session_abc")
        
        # Simulate previous conversation
        ctx.add_to_memory("user", "What's the price of ETH?", {"asset": "ETH"})
        ctx.add_to_memory("assistant", "ETH is $2,240, up 1.5% today")
        
        # Simulate learned behavior
        ctx.learn_from_trade("ETH", 0.5, 1000)
        ctx.learn_from_trade("ETH", 0.5, 1100)
        
        # Build prompt for follow-up
        prompt = await ctx.build_prompt(
            "Should I buy it?",
            "advice",
            {"asset": "ETH"}
        )
        
        print(f"\nPrompt preview (first 800 chars):\n{prompt[:800]}")
        
        # Test 2: Pronoun resolution in context
        print("\n2. Pronoun resolution in prompt")
        if "referring to ETH" in prompt:
            print("   ✅ Pronoun resolved: 'it' → ETH")
        else:
            print("   ❌ Pronoun not resolved")
        
        # Test 3: Profile context included
        print("\n3. Profile context in prompt")
        if "Risk Tolerance" in prompt:
            print("   ✅ Risk tolerance included")
        else:
            print("   ❌ Risk tolerance missing")
        
        # Test 4: Market context included
        print("\n4. Market context in prompt")
        if "Market Context" in prompt:
            print("   ✅ Market context included")
        else:
            print("   ❌ Market context missing")
        
        await ctx.close()
        print("\n✅ Context integration tests complete!")
    
    asyncio.run(run_tests())
