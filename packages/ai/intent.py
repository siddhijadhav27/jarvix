"""
Hybrid Intent Detection for Jarvix
Fast regex for common commands, LLM fallback for complex ones
"""

import re
from typing import Dict, Any, Optional
from .llm_client import classify_intent_llm

# Fast regex patterns for common commands
# Latin scripts
BUY_PATTERNS = [
    r'\b(buy|purchase|get|acquire|add|don\'t miss|dont miss|grab|pick up|moon|lambo|rocket|time to buy|buying time|thinking about buying|considering buying|possibly get|kharido|lena hai|comprar|acheter|kaufen|사기|شراء|Купить|comprare|kopen|al|mua|ซื้อ|beli|kupić|köp|Αγορά)\b'
]
SELL_PATTERNS = [
    r'\b(sell|dump|cash out|liquidate|get rid of|unload|offload|exit|crash|panic|time to sell|selling time|thinking about selling|considering selling|becho|dena hai|vender|vendre|verkaufen|팔기|بيع|Продать|vendere|verkopen|sat|bán|ขาย|jual|sprzedać|sälj|Πώληση)\b'
]
PRICE_PATTERNS = [
    r'\b(price|cost|value|how much|worth|rate|chart|kitna|rate|precio|prix|preis|가격|سعر|Цена|prezzo|prijs|fiyat|giá|ราคา|harga|cena|pris|Τιμή)\b'
]

# Non-Latin scripts (Chinese, Japanese, Russian) - no word boundaries
BUY_PATTERNS_NONLATIN = [
    r'购买|買う|买入|買入|購入|Купить',
]
SELL_PATTERNS_NONLATIN = [
    r'出售|売る|卖出|売出|売却|Продать',
]
PRICE_PATTERNS_NONLATIN = [
    r'价格|価格|價格|料金|Цена',
]
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
    # Check non-Latin sell patterns
    elif any(re.search(p, message_lower) for p in SELL_PATTERNS_NONLATIN):
        intent = "sell"
    # Check buy
    elif any(re.search(p, message_lower) for p in BUY_PATTERNS):
        intent = "buy"
    # Check non-Latin buy patterns
    elif any(re.search(p, message_lower) for p in BUY_PATTERNS_NONLATIN):
        intent = "buy"
    # Check price
    elif any(re.search(p, message_lower) for p in PRICE_PATTERNS):
        intent = "price"
    # Check non-Latin price patterns
    elif any(re.search(p, message_lower) for p in PRICE_PATTERNS_NONLATIN):
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
