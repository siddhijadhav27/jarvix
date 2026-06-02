"""
Hybrid Intent Detection for Jarvix
Fast regex for common commands, LLM fallback for complex ones
"""

import re
from typing import Dict, Any, Optional
from .llm_client import classify_intent_llm

# Fast regex patterns for common commands
BUY_PATTERNS = [r'\b(buy|purchase|get|acquire|add|don\'t miss|dont miss|grab|pick up|moon|lambo|rocket)\b']
SELL_PATTERNS = [r'\b(sell|dump|cash out|liquidate|get rid of|unload|offload|exit|crash|panic)\b']
PRICE_PATTERNS = [r'\b(price|cost|value|how much|worth|rate|chart|kitna|rate)\b']
PORTFOLIO_PATTERNS = [r'\b(portfolio|balance|holdings|net worth|what do i own|assets|p\u0026l|profit|loss|kitna paisa|mere paas)\b']
STOP_LOSS_PATTERNS = [r'\b(stop.loss|stoploss|protect|stop loss)\b']
ADVICE_PATTERNS = [r'\b(should i|advice|recommend|what do you think|analysis|help|understand|confused)\b']
ALERT_PATTERNS = [r'\b(alert|notify|tell me when)\b']
GREETING_PATTERNS = [r'\b(hello|hi|hey|good morning|good afternoon|good evening|what is up|hii|hiii|namaste|hola|ciao|jarvix|you there|wake up|yo)\b']

ASSET_PATTERN = r'\b(btc|eth|sol|ada|doge|xrp|dot|link|avax|matic|bnb)\b'
AMOUNT_PATTERN = r'(\d+(?:\.\d+)?)'


def detect_intent_regex(message: str) -> Optional[Dict[str, Any]]:
    """
    Fast regex-based intent detection
    Returns None if no match (fall back to LLM)
    """
    message_lower = message.lower().strip()
    
    # Check for empty message
    if not message_lower:
        return None
    
    intent = None
    confidence = 0.95
    
    # Check greeting first (short messages)
    if any(re.search(p, message_lower) for p in GREETING_PATTERNS):
        intent = "greeting"
    # Check portfolio BEFORE price (to catch "portfolio value")
    elif any(re.search(p, message_lower) for p in PORTFOLIO_PATTERNS):
        intent = "portfolio"
    # Check sell BEFORE buy (to catch "get rid of")
    elif any(re.search(p, message_lower) for p in SELL_PATTERNS):
        intent = "sell"
    # Check buy
    elif any(re.search(p, message_lower) for p in BUY_PATTERNS):
        intent = "buy"
    # Check price
    elif any(re.search(p, message_lower) for p in PRICE_PATTERNS):
        intent = "price"
    # Check stop loss
    elif any(re.search(p, message_lower) for p in STOP_LOSS_PATTERNS):
        intent = "stop_loss"
    # Check advice
    elif any(re.search(p, message_lower) for p in ADVICE_PATTERNS):
        intent = "advice"
    # Check alert
    elif any(re.search(p, message_lower) for p in ALERT_PATTERNS):
        intent = "alert"
    
    if intent:
        # Extract asset
        asset_match = re.search(ASSET_PATTERN, message_lower)
        asset = asset_match.group(1).upper() if asset_match else None
        
        # Extract amount
        amount_match = re.search(AMOUNT_PATTERN, message_lower)
        amount = float(amount_match.group(1)) if amount_match else None
        
        return {
            "intent": intent,
            "asset": asset,
            "amount": amount,
            "price": None,
            "confidence": confidence,
            "source": "regex"
        }
    
    return None


async def detect_intent_hybrid(message: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Hybrid intent detection:
    1. Try regex first (fast, reliable)
    2. Fall back to LLM (smart, slow)
    """
    # Fast path: regex
    regex_result = detect_intent_regex(message)
    if regex_result:
        return regex_result
    
    # Slow path: LLM for complex commands
    llm_result = await classify_intent_llm(message, context)
    llm_result["source"] = "llm"
    return llm_result
