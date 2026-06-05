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
    r'\b(buy|purchase|acquire|add|don\'t miss|dont miss|grab|pick up|moon|lambo|rocket|time to buy|buying time|thinking about buying|considering buying|possibly get|kharido|lena hai|comprar|acheter|kaufen|사기|شراء|Купить|comprare|kopen|al|mua|ซื้อ|beli|kupić|köp|Αγορά)\b'
]
SELL_PATTERNS = [
    r'\b(sell|sale|dump|cash out|liquidate|get rid of|unload|offload|exit|crash|panic|time to sell|selling time|thinking about selling|thinking of selling|thinking of dumping|considering selling|possibly unload|remove from portfolio|remove.*portfolio|get out|take profits|profit taking|becho|bech do|dena hai|nikal do|nikat do|vender|vendre|verkaufen|팔기|بيع|Продать|vendere|verkopen|sat|bán|ขาย|jual|sprzedać|sälj|Πώληση)\b'
]
PRICE_PATTERNS = [
    r'\b(price|prices|cost|value|how much|worth|rate|chart|kitna|kya chal raha hai|kya scene hai|ka bhav|ka rate|precio|prix|preis|가격|سعر|Цена|prezzo|prijs|fiyat|giá|ราคา|harga|cena|pris|Τιμή|going up|going down|pump|dump|mooning|crashing|support|resistance|all time high|ath)\b'
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
PORTFOLIO_PATTERNS = [r'\b(portfolio|balance|holdings|net worth|what do i have|what do i own|show my|my assets|kitna paisa|mere paas|hold|assets|show assets|how am i doing|doing|p\u0026l|profit.*loss|summary|gains|do i have|do i own|amount)\b']
STOP_LOSS_PATTERNS = [r'\b(stop.loss|stoploss|protect|stop loss)\b']

# Add stop loss as sell intent - when triggered, sell
STOP_LOSS_SELL_PATTERNS = [r'\b(stop loss triggered|stoploss triggered|stop loss hit|stoploss hit)\b']
ADVICE_PATTERNS = [r'\b(should i|advice|recommend|what do you think|analysis|help|understand|confused|is.*good investment|what about|advise on|market analysis|good time to|what do you recommend|crypto advice|help me understand|should i diversify|should i hold|should i sell|is it time to)\b']
ALERT_PATTERNS = [r'\b(alert|notify|tell me when)\b']
GREETING_PATTERNS = [r'\b(hello|hi|hey|good morning|good afternoon|good evening|what is up|whats up|what\'s up|how are you|how do you do|hii|hiii|namaste|salam|hola|ciao|jarvix|you there|wake up|yo|sup|howdy|g\'day|bonjour|guten tag|konnichiwa|annyeong|salaam|marhaba|shalom|sawubona|jambo)\b']

ASSET_PATTERN = r'\b(btc|bitcoin|eth|ethereum|sol|solana|ada|cardano|doge|dogecoin|xrp|ripple|dot|polkadot|link|chainlink|avax|avalanche|matic|polygon|bnb|binance)\b'
AMOUNT_PATTERN = r'(\d+(?:\.\d+)?)'
PRICE_PATTERN = r'(?:at|for|@)\s*(\d+(?:,\d{3})*(?:\.\d+)?)'


def detect_intent_regex(message: str) -> Optional[Dict[str, Any]]:
    """
    Fast regex-based intent detection
    Returns None if no match (fall back to LLM)
    """
    # Don't lowercase for non-Latin scripts (Cyrillic, Chinese, etc.)
    # Check if message contains non-Latin characters
    has_nonlatin = any(ord(c) > 127 for c in message)
    
    if has_nonlatin:
        message_lower = message.strip()  # Keep original case
    else:
        message_lower = message.lower().strip()
    
    # Check for empty message
    if not message_lower:
        return None
    
    intent = None
    confidence = 0.95
    
    # Check for multiple intents
    detected_intents = []
    
    # Check advice patterns FIRST (before buy/sell to catch "Should I buy")
    if any(re.search(p, message_lower) for p in ADVICE_PATTERNS):
        detected_intents.append("advice")
    # Check portfolio patterns FIRST (before price to catch "portfolio value")
    elif any(re.search(p, message_lower) for p in PORTFOLIO_PATTERNS):
        detected_intents.append("portfolio")
    # Check price patterns (but not if portfolio context detected)
    elif any(re.search(p, message_lower) for p in PRICE_PATTERNS):
        detected_intents.append("price")
    # Check sell patterns (but not if price context detected)
    elif any(re.search(p, message_lower) for p in SELL_PATTERNS):
        detected_intents.append("sell")
    # Check buy patterns
    elif any(re.search(p, message_lower) for p in BUY_PATTERNS):
        detected_intents.append("buy")
    
    # If multiple intents detected, use the first one but add secondary_intent
    if len(detected_intents) > 0:
        intent = detected_intents[0]
        secondary_intent = detected_intents[1] if len(detected_intents) > 1 else None
    else:
        intent = None
        secondary_intent = None
    
    # Fallback to old logic if no intents detected
    if not intent:
        # Check greeting first (short messages)
        if any(re.search(p, message_lower) for p in GREETING_PATTERNS):
            intent = "greeting"
        # Check buy with "add" explicitly (before portfolio to catch "add BTC to portfolio")
        elif re.search(r'\badd\s+(btc|eth|sol|ada|doge|xrp|dot|link|avax|matic|bnb)\b', message_lower):
            intent = "buy"
        # Check sell with "remove" explicitly (before portfolio to catch "remove BTC from portfolio")
        elif re.search(r'\bremove\s+(btc|eth|sol|ada|doge|xrp|dot|link|avax|matic|bnb)\b', message_lower):
            intent = "sell"
        # Check stop loss triggered as sell (before portfolio)
        elif any(re.search(p, message_lower) for p in STOP_LOSS_SELL_PATTERNS):
            intent = "sell"
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
        # Extract ALL assets (multiple assets support)
        asset_matches = re.findall(ASSET_PATTERN, message_lower)
        if asset_matches:
            # If multiple assets, join them with comma
            if len(asset_matches) > 1:
                asset = ', '.join([a.upper() for a in asset_matches])
            else:
                asset = asset_matches[0].upper()
        else:
            asset = None
        
        # Extract amount
        amount_match = re.search(AMOUNT_PATTERN, message_lower)
        amount = float(amount_match.group(1)) if amount_match else None
        
        # Extract price (e.g., "at 2000", "for $2000", "@ 2000")
        price_match = re.search(PRICE_PATTERN, message_lower)
        price = float(price_match.group(1).replace(',', '')) if price_match else None
        
        result = {
            "intent": intent,
            "asset": asset,
            "amount": amount,
            "price": price,
            "confidence": confidence,
            "source": "regex"
        }
        
        # Add secondary intent if detected
        if secondary_intent:
            result["secondary_intent"] = secondary_intent
        
        return result
    
    return None


async def detect_intent_hybrid(message: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Hybrid intent detection:
    1. Try regex first (fast, reliable)
    2. Fall back to LLM (smart, slow)
    """
    # Remove emojis before detection
    import re
    emoji_pattern = re.compile("["
        u"\U0001F600-\U0001F64F"
        u"\U0001F300-\U0001F5FF"
        u"\U0001F680-\U0001F6FF"
        u"\U0001F1E0-\U0001F1FF"
        u"\U00002702-\U000027B0"
        u"\U000024C2-\U0001F251"
        "]+", flags=re.UNICODE)
    clean_message = emoji_pattern.sub(r'', message).strip()
    
    # Fast path: regex
    regex_result = detect_intent_regex(clean_message)
    if regex_result:
        return regex_result
    
    # Slow path: LLM for complex commands
    llm_result = await classify_intent_llm(clean_message, context)
    llm_result["source"] = "llm"
    return llm_result
