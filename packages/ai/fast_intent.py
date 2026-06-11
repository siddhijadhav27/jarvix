# fast_intent.py
"""Fast path intent classification — no LLM needed for obvious commands"""

import re
from typing import Dict, Any, Optional
from enum import Enum

class Intent(Enum):
    BUY = "buy"
    SELL = "sell"
    PRICE = "price"
    PORTFOLIO = "portfolio"
    STOP_LOSS = "stop_loss"
    ADVICE = "advice"
    MARKET_ANALYSIS = "market_analysis"
    GREETING = "greeting"
    UNKNOWN = "unknown"

# Fast path patterns — compiled once for speed
FAST_PATH_PATTERNS = {
    Intent.PRICE: [
        r"price\s+of\s+(\w+)",
        r"how\s+much\s+is\s+(\w+)",
        r"what'?s\s+(\w+)\s+(worth|at|trading)",
        r"(\w+)\s+price",
        r"current\s+price\s+(\w+)",
    ],
    Intent.GREETING: [
        r"^(hi|hello|hey|hii|good\s+morning|good\s+evening)",
    ],
    Intent.PORTFOLIO: [
        r"(my\s+)?(portfolio|balance|holdings|assets|positions)",
        r"what\s+do\s+i\s+own",
        r"show\s+my\s+crypto",
    ],
    Intent.BUY: [
        r"buy\s+(\d+)?\s*(\w+)",
        r"purchase\s+(\d+)?\s*(\w+)",
        r"get\s+(\d+)?\s*(\w+)",
    ],
    Intent.SELL: [
        r"sell\s+(\d+)?\s*(\w+)",
        r"sell\s+(\d+)%\s+of\s+(\w+)",
    ],
    Intent.STOP_LOSS: [
        r"stop\s*loss",
        r"set\s+stop",
        r"protect\s+my\s+(\w+)",
    ],
    Intent.ADVICE: [
        r"should\s+i\s+(buy|sell)",
        r"is\s+(\w+)\s+a\s+good\s+(buy|investment)",
        r"recommend",
        r"advice",
    ],
    Intent.MARKET_ANALYSIS: [
        r"analyze\s+(\w+)\s+market",
        r"market\s+analysis\s+(\w+)",
        r"how\s+is\s+(\w+)\s+doing",
        r"(\w+)\s+trend",
        r"market\s+outlook",
    ],
}

# Entity extractors
ENTITY_PATTERNS = {
    "asset": [
        r"\b(BTC|ETH|SOL|ADA|DOT|AVAX|MATIC|LINK|UNI|AAVE|SNX|CRV|COMP|MKR|YFI|BAL|LRC|IMX|DYDX|PERP|GMX|BTC|ETH|SOL)\b",
        r"\b(bitcoin|ethereum|solana|cardano|polkadot|avalanche|polygon|chainlink|uniswap|aave|synthetix|curve|compound|maker|yearn|balancer|loopring|immutable|dydx|perpetual|gmx)\b",
    ],
    "amount": [
        r"(\d+(?:\.\d+)?)\s*(?:USD|USDT|USDC|\$)?",
        r"(\d+)%",
    ],
    "price": [
        r"\$?(\d+(?:,\d{3})*(?:\.\d+)?)",
    ],
}


def classify_fast(message: str) -> Optional[Dict[str, Any]]:
    """
    Fast path classification — returns result in <1ms
    Returns None if no fast path match (fall back to LLM)
    """
    message_lower = message.lower().strip()
    
    # Try each intent pattern
    for intent, patterns in FAST_PATH_PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, message_lower)
            if match:
                # Extract entities
                entities = extract_entities_fast(message_lower, intent)
                
                return {
                    "intent": intent.value,
                    "confidence": 0.95,
                    "entities": entities,
                    "fast_path": True,
                    "matched_pattern": pattern,
                }
    
    # No fast path match
    return None


def extract_entities_fast(message: str, intent: Intent) -> Dict[str, Any]:
    """Extract entities using regex"""
    entities = {}
    
    # Extract asset using improved patterns
    entities["asset"] = _extract_asset(message)
    
    # Extract amount
    for pattern in ENTITY_PATTERNS["amount"]:
        match = re.search(pattern, message)
        if match:
            amount_str = match.group(1)
            if "%" in message:
                entities["amount"] = float(amount_str)
                entities["amount_type"] = "percentage"
            else:
                entities["amount"] = float(amount_str)
                entities["amount_type"] = "absolute"
            break
    
    # Extract price (for stop-loss)
    if intent == Intent.STOP_LOSS:
        for pattern in ENTITY_PATTERNS["price"]:
            match = re.search(pattern, message)
            if match:
                price_str = match.group(1).replace(",", "")
                entities["price"] = float(price_str)
                break
    
    return entities


def _extract_asset(message: str) -> Optional[str]:
    """
    Extract cryptocurrency asset from message.
    Returns uppercase symbol (BTC, ETH, SOL, etc.) or None.
    """
    message_lower = message.lower()
    
    # Direct symbol matches
    symbol_map = {
        "btc": "BTC", "bitcoin": "BTC",
        "eth": "ETH", "ethereum": "ETH",
        "sol": "SOL", "solana": "SOL",
        "ada": "ADA", "cardano": "ADA",
        "dot": "DOT", "polkadot": "DOT",
        "avax": "AVAX", "avalanche": "AVAX",
        "matic": "MATIC", "polygon": "MATIC",
        "link": "LINK", "chainlink": "LINK",
        "uni": "UNI", "uniswap": "UNI",
        "aave": "AAVE",
        "snx": "SNX", "synthetix": "SNX",
        "crv": "CRV", "curve": "CRV",
        "comp": "COMP", "compound": "COMP",
        "mkr": "MKR", "maker": "MKR",
        "yfi": "YFI", "yearn": "YFI",
        "bal": "BAL", "balancer": "BAL",
        "lrc": "LRC", "loopring": "LRC",
        "imx": "IMX", "immutable": "IMX",
        "dydx": "DYDX",
        "perp": "PERP", "perpetual": "PERP",
        "gmx": "GMX",
    }
    
    # Check for direct matches
    for key, symbol in symbol_map.items():
        if key in message_lower:
            return symbol
    
    # Regex fallback for any uppercase crypto symbol
    match = re.search(r"\b([A-Z]{2,5})\b", message)
    if match:
        return match.group(1)
    
    return None


def classify_with_fallback(message: str, bridge) -> Dict[str, Any]:
    """
    Full classification with fast path + LLM fallback
    """
    # Try fast path first
    fast_result = classify_fast(message)
    if fast_result:
        print(f"[FAST PATH] {fast_result['intent']} matched in <1ms")
        return fast_result
    
    # Fall back to LLM
    print(f"[LLM PATH] Routing to Kimi for classification")
    
    prompt = f"""Classify this crypto command: "{message}"

Return JSON only:
{{
    "intent": "buy|sell|price|portfolio|stop_loss|advice|unknown",
    "confidence": 0.0-1.0,
    "entities": {{
        "asset": "BTC|ETH|SOL|...",
        "amount": number or null,
        "amount_type": "absolute|percentage|null",
        "price": number or null
    }}
}}"""
    
    raw = bridge.send(prompt)
    
    # Parse JSON from response
    try:
        import json
        start = raw.find('{')
        end = raw.rfind('}')
        if start != -1 and end != -1:
            parsed = json.loads(raw[start:end+1])
            return {
                "intent": parsed.get("intent", "unknown"),
                "confidence": parsed.get("confidence", 0.5),
                "entities": parsed.get("entities", {}),
                "fast_path": False,
            }
    except:
        pass
    
    return {
        "intent": "unknown",
        "confidence": 0.0,
        "entities": {},
        "fast_path": False,
    }


# Test
if __name__ == "__main__":
    import time
    
    test_messages = [
        "Price of BTC",
        "What's my portfolio?",
        "Buy 100 ETH",
        "Sell 25% of my BTC",
        "Hi Jarvix",
        "Set stop-loss for ETH at $2000",
        "Should I buy SOL now?",
        "Analyze ETH market",
    ]
    
    print("🧪 Fast Intent Classification Tests")
    print("=" * 60)
    
    for msg in test_messages:
        start = time.time()
        result = classify_fast(msg)
        latency = (time.time() - start) * 1000  # ms
        
        if result:
            print(f"✅ {msg:30s} → {result['intent']:12s} ({latency:.2f}ms) [FAST]")
        else:
            print(f"⚠️  {msg:30s} → unknown      ({latency:.2f}ms) [LLM]")
