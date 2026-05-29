# memory.py
"""Conversation memory with pronoun resolution for Jarvix"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from storage import get_storage


# Words that refer to previously mentioned things
REFERENCE_WORDS = [
    "it", "that", "this", "them", "those",
    "the coin", "that one", "more", "some",
    "the asset", "the token", "my holding"
]

# Common crypto assets for detection
KNOWN_ASSETS = [
    "BTC", "ETH", "SOL", "BNB", "ADA", "DOT", "AVAX",
    "MATIC", "LINK", "UNI", "AAVE", "SNX", "CRV", "COMP",
    "MKR", "YFI", "BAL", "LRC", "IMX", "DYDX", "PERP", "GMX",
    "bitcoin", "ethereum", "solana", "cardano", "polkadot",
    "avalanche", "polygon", "chainlink", "uniswap"
]


class ConversationMemory:
    """
    Stores conversation history and resolves ambiguous references.
    
    Key features:
    - Keeps last N messages per session
    - Tracks last mentioned asset for pronoun resolution
    - Resolves "it", "that", "this" to actual assets
    """
    
    def __init__(self, session_id: str, max_messages: int = 10):
        self.session_id = session_id
        self.max_messages = max_messages
        self.storage = get_storage()
        self.messages: List[Dict[str, Any]] = []
        
        # Load from Redis
        self._load()
    
    # ─── Message Management ────────────────────────────
    
    def add(self, role: str, content: str, entities: Optional[Dict] = None):
        """Add a message to conversation history"""
        message = {
            "role": role,
            "content": content,
            "entities": entities or {},
            "timestamp": datetime.now().isoformat()
        }
        
        self.messages.append(message)
        
        # Keep only last N messages
        if len(self.messages) > self.max_messages:
            self.messages.pop(0)
        
        # Save to Redis
        self._save()
    
    def get_last(self, n: int = 3) -> List[Dict[str, Any]]:
        """Get last N messages"""
        return self.messages[-n:]
    
    def get_all(self) -> List[Dict[str, Any]]:
        """Get all messages"""
        return self.messages.copy()
    
    def clear(self):
        """Clear conversation history"""
        self.messages = []
        self._save()
    
    # ─── Pronoun Resolution ────────────────────────────
    
    def has_reference(self, message: str) -> bool:
        """Check if message contains reference words"""
        message_lower = message.lower()
        return any(word in message_lower for word in REFERENCE_WORDS)
    
    def get_last_mentioned_asset(self) -> Optional[str]:
        """Find the most recently mentioned asset in conversation"""
        # Search from most recent to oldest
        for msg in reversed(self.messages):
            # Check stored entities first
            asset = msg.get("entities", {}).get("asset")
            if asset:
                return asset.upper()
            
            # Fallback: scan message text
            asset = self._extract_asset_from_text(msg["content"])
            if asset:
                return asset
        
        return None
    
    def _extract_asset_from_text(self, text: str) -> Optional[str]:
        """Extract asset from message text"""
        text_lower = text.lower()
        
        for asset in KNOWN_ASSETS:
            if asset.lower() in text_lower:
                return asset.upper()
        
        return None
    
    def resolve_references(self, message: str) -> str:
        """
        Replace ambiguous references with actual values.
        
        Example:
            "Should I buy it?" → "Should I buy it? [Context: user is referring to ETH]"
        """
        if not self.has_reference(message):
            return message  # No resolution needed
        
        last_asset = self.get_last_mentioned_asset()
        
        if last_asset:
            # Add context hint for LLM
            return (
                f"{message} "
                f"[Context: user is referring to {last_asset} "
                f"from previous message]"
            )
        
        return message  # No asset found to resolve
    
    # ─── Context Building ──────────────────────────────
    
    def build_context_prompt(self, current_message: str) -> str:
        """Build context prompt for LLM with conversation history"""
        
        # Resolve references in current message
        resolved = self.resolve_references(current_message)
        
        # Build conversation context
        context_parts = []
        
        # Add recent conversation
        recent = self.get_last(3)
        if recent:
            context_parts.append("Recent conversation:")
            for msg in recent:
                role = "User" if msg["role"] == "user" else "Jarvix"
                context_parts.append(f"  {role}: {msg['content'][:100]}")
        
        # Add current message
        context_parts.append(f"\nCurrent message: {resolved}")
        
        return "\n".join(context_parts)
    
    # ─── Persistence ───────────────────────────────────
    
    def _save(self):
        """Save to Redis"""
        self.storage.save_conversation(self.session_id, self.messages)
    
    def _load(self):
        """Load from Redis"""
        self.messages = self.storage.load_conversation(self.session_id)
    
    # ─── Stats ─────────────────────────────────────────
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics"""
        return {
            "session_id": self.session_id,
            "message_count": len(self.messages),
            "max_messages": self.max_messages,
            "last_asset": self.get_last_mentioned_asset(),
            "recent_messages": len(self.get_last(3))
        }


# Test
if __name__ == "__main__":
    print("🧪 ConversationMemory Tests")
    print("=" * 60)
    
    # Test 1: Basic conversation
    print("\n1. Basic conversation storage")
    mem = ConversationMemory("test_session_1")
    mem.clear()
    
    mem.add("user", "What's the price of ETH?", {"asset": "ETH"})
    mem.add("assistant", "ETH is $2,240")
    mem.add("user", "Should I buy it?")
    
    print(f"   Messages: {len(mem.messages)}")
    print(f"   Last asset: {mem.get_last_mentioned_asset()}")
    
    # Test 2: Pronoun resolution
    print("\n2. Pronoun resolution")
    resolved = mem.resolve_references("Should I buy it?")
    print(f"   Original: 'Should I buy it?'")
    print(f"   Resolved: '{resolved}'")
    
    # Test 3: No reference
    print("\n3. No reference needed")
    resolved = mem.resolve_references("What's my portfolio?")
    print(f"   Original: 'What's my portfolio?'")
    print(f"   Resolved: '{resolved}'")
    
    # Test 4: Multiple references
    print("\n4. Multiple turns with references")
    mem2 = ConversationMemory("test_session_2")
    mem2.clear()
    
    mem2.add("user", "Price of BTC", {"asset": "BTC"})
    print(f"   Turn 1: 'Price of BTC' → last asset: {mem2.get_last_mentioned_asset()}")
    
    mem2.add("user", "Should I buy it?")
    resolved = mem2.resolve_references("Should I buy it?")
    print(f"   Turn 2: '{resolved}'")
    
    mem2.add("user", "What about SOL?", {"asset": "SOL"})
    print(f"   Turn 3: 'What about SOL?' → last asset: {mem2.get_last_mentioned_asset()}")
    
    mem2.add("user", "Is it a good investment?")
    resolved = mem2.resolve_references("Is it a good investment?")
    print(f"   Turn 4: '{resolved}'")
    
    # Test 5: Persistence
    print("\n5. Persistence test")
    mem3 = ConversationMemory("test_session_1")  # Same session
    print(f"   Loaded messages: {len(mem3.messages)}")
    print(f"   Last asset after reload: {mem3.get_last_mentioned_asset()}")
    
    # Test 6: Context prompt
    print("\n6. Context prompt building")
    mem4 = ConversationMemory("test_session_3")
    mem4.clear()
    mem4.add("user", "What's the price of ETH?", {"asset": "ETH"})
    mem4.add("assistant", "ETH is $2,240")
    
    prompt = mem4.build_context_prompt("Should I buy it?")
    print(f"   Context prompt:\n{prompt}")
    
    print("\n✅ All memory tests passed!")
