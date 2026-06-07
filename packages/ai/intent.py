"""
Hybrid Intent Detection for Jarvix
Fast regex for common commands, LLM fallback for complex ones
"""

import re
import json
from typing import Dict, Any, Optional
from .openrouter_client import call_openrouter

# Fast regex patterns for common commands
# Latin scripts
BUY_PATTERNS = [
    r'\b(buy|purchase|acquire|add|invest in|stack|enter.*position|long|don\'t miss|dont miss|grab|pick up|moon|lambo|rocket|time to buy|buying time|thinking about buying|considering buying|possibly get|kharido|lena hai|comprar|acheter|kaufen|사기|شراء|Купить|comprare|kopen|al|mua|ซื้อ|beli|kupić|köp|Αγορά)\b',
    # "Get" is BUY, but NOT "get rid of" (that's SELL)
    r'\bget\b(?!\s+rid\s+of)',
    # Conditional buy patterns
    r'\bbuy\s+(?:if|when|at)\b',
    r'\bbuy\s+.*\s+(?:dip|low|cheap|discount|bargain)\b',
]
SELL_PATTERNS = [
    r'\b(sell|sale|dump|cash out|liquidate|unload|offload|exit|crash|panic|emergency|stop loss|limit sell|time to sell|selling time|thinking about selling|thinking of selling|thinking of dumping|considering selling|possibly unload|remove from portfolio|remove.*portfolio|get out|take profits|profit taking|becho|bech do|dena hai|nikal do|nikat do|vender|vendre|verkaufen|팔기|بيع|Продать|vendere|verkopen|sat|bán|ขาย|jual|sprzedać|sälj|Πώληση)\b',
    # "Get rid of" is SELL, not BUY
    r'\bget rid of\b',
    # Conditional sell patterns
    r'\bsell\s+(?:if|when|at)\b',
    r'\bsell\s+.*\s+(?:pump|high|expensive|premium|profit|rises)\b',
    r'\bpanic\s+sell\b',
    r'\bcrash\s+sell\b',
    r'\bemergency\s+sell\b',
    r'\bstop loss\s+sell\b',
    r'\blimit\s+sell\b',
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
PORTFOLIO_PATTERNS = [r'\b(portfolio|balance|holdings|net worth|what do i have|what do i own|show my|my assets|kitna paisa|mere paas|hold|assets|show assets|how am i doing|doing|p\u0026l|profit.*loss|summary|gains|do i have|do i own|amount|positions|allocation|total value)\b']
STOP_LOSS_PATTERNS = [r'\b(stop.loss|stoploss|protect|stop loss)\b']

# Add stop loss as sell intent - when triggered, sell
STOP_LOSS_SELL_PATTERNS = [r'\b(stop loss triggered|stoploss triggered|stop loss hit|stoploss hit)\b']
ADVICE_PATTERNS = [r'\b(should i|advice|recommend|what do you think|analysis|help|understand|confused|is.*good investment|what about|advise on|market analysis|good time to|what do you recommend|crypto advice|help me understand|should i diversify|should i hold|should i sell|is it time to|is it good to|which crypto to|what to invest in|is.*a good buy|is it worth|worth buying)\b']
ALERT_PATTERNS = [r'\b(alert|notify|tell me when|warn me|set alert|set notification)\b']

# Alert-specific patterns for price threshold extraction
ALERT_PRICE_PATTERN = r'(?:hits|reaches|goes above|above|drops below|below|falls to|at)\s+(\d+(?:,\d{3})*(?:\.\d+)?)(?:k|K)?'
ALERT_PRICE_PATTERN_SPACE = r'(?:btc|eth|sol|ada|doge|xrp|dot|link|avax|matic|bnb)\s+(\d+(?:,\d{3})*(?:\.\d+)?)(?:k|K)?'
ALERT_DIRECTION_ABOVE = r'\b(hits|reaches|goes above|above|pumps|moons)\b'
ALERT_DIRECTION_BELOW = r'\b(drops below|below|falls to|dump|crashes)\b'
GREETING_PATTERNS = [r'\b(hello|hi|hey|good morning|good afternoon|good evening|good night|greetings|welcome|what is up|whats up|what\'s up|how are you|how do you do|how is it going|how\'s it going|what\'s going on|whats going on|nice to meet you|pleased to meet you|hii|hiii|namaste|salam|hola|ciao|jarvix|you there|wake up|yo|sup|howdy|g\'day|bonjour|guten tag|konnichiwa|annyeong|salaam|marhaba|shalom|sawubona|jambo)\b']

# Emotional patterns for sentiment detection
EMOTIONAL_PATTERNS = [
    r"\b(i am|i'm|feeling|so|very|really|extremely|quite|pretty|too|so)\s+(happy|sad|angry|excited|thrilled|frustrated|scared|worried|nervous|anxious|confused|disappointed|stressed|overwhelmed|shocked|surprised|grateful|hopeful|confident|bullish|bearish|terrified|ecstatic|depressed|furious|delighted|content|peaceful|calm|relaxed|tense|uneasy|restless|impatient|satisfied|unsatisfied|great|best|worst|uncertain)\b",
    r"\b(i|this|that|it)\s+(is|was|has been|will be)\s+(amazing|awesome|terrible|great|best|worst|horrible|fantastic|wonderful|awful|incredible|disgusting|beautiful|ugly|perfect|disastrous|magnificent|brilliant|dreadful|excellent|pathetic|outstanding|unacceptable|remarkable|shocking|surprising|disappointing|frustrating|confusing|overwhelming|stressful|worrying|concerning|terrifying|exhilarating|depressing|uplifting|heartbreaking|heartwarming)\b",
    r"\b(i|we)\s+(love|hate|like|dislike|adore|despise|enjoy|detest|appreciate|resent|admire|loathe|cherish|abhor|treasure|dread|relish|fear|distrust|trust|value|disregard)\s+(this|that|it|the|crypto|market|bitcoin|eth|btc|sol|trading|investing|you|jarvix)\b",
    r"\b(feeling|feel)\s+(good|bad|better|worse|fine|okay|ok|not good|not well|sick|tired|energetic|lazy|motivated|unmotivated|inspired|uninspired|lost|found|empty|full|broken|healed|strong|weak|powerless|empowered|vulnerable|protected|alone|connected|loved|unloved|accepted|rejected|understood|misunderstood|seen|unseen|heard|ignored|valued|worthless)\b",
    r"\b(mood|vibe|energy|spirit|soul|heart|mind|head|gut|instinct|intuition)\s+(is|feels|seems|looks|sounds|tastes|smells)\b",
    r"\b(feeling|feel)\s+(great|good|bad|awesome|terrible|amazing|wonderful|awful|fantastic|excellent|pathetic|outstanding|unacceptable|remarkable|shocking|surprising|disappointing|frustrating|confusing|overwhelming|stressful|worrying|concerning|terrifying|exhilarating|depressing|uplifting|heartbreaking|heartwarming)\b",
    r"\b(best|worst)\s+(day|week|month|year|time|moment|experience|memory|decision|choice|option|alternative|result|outcome|performance|showing|effort|attempt|try|shot|guess|estimate|prediction|forecast|projection|expectation|hope|dream|wish|desire|want|need|requirement|demand|request|suggestion|recommendation|advice|tip|hint|clue|idea|thought|thinking|feeling|emotion|mood|vibe|energy|spirit|soul|heart|mind|head|gut|instinct|intuition)\b",

]












ASSET_PATTERN = r'\b(btc|bitcoin|eth|ethereum|sol|solana|ada|cardano|doge|dogecoin|xrp|ripple|dot|polkadot|link|chainlink|avax|avalanche|matic|polygon|bnb|binance)\b'
AMOUNT_PATTERN = r'(\d+(?:\.\d+)?)'
PRICE_PATTERN = r'(?:at|for|@)\s*(\d+(?:,\d{3})*(?:\.\d+)?)'

# Single asset words that should trigger price intent
SINGLE_ASSET_WORDS = {'btc', 'bitcoin', 'eth', 'ethereum', 'sol', 'solana', 'ada', 'cardano', 'doge', 'dogecoin', 'xrp', 'ripple', 'dot', 'polkadot', 'link', 'chainlink', 'avax', 'avalanche', 'matic', 'polygon', 'bnb', 'binance'}
SINGLE_ACTION_WORDS = {'buy', 'sell'}

# Single word intent mapping
SINGLE_WORD_INTENTS = {
    'buy': 'buy',
    'sell': 'sell',
    'price': 'price',
    'portfolio': 'portfolio',
    'alert': 'alert',
    'help': 'advice',
    'advice': 'advice',
}

# Asset normalization mapping
ASSET_ALIASES = {
    'bitcoin': 'BTC',
    'btc': 'BTC',
    'ethereum': 'ETH',
    'eth': 'ETH',
    'solana': 'SOL',
    'sol': 'SOL',
    'cardano': 'ADA',
    'ada': 'ADA',
    'dogecoin': 'DOGE',
    'doge': 'DOGE',
    'ripple': 'XRP',
    'xrp': 'XRP',
    'polkadot': 'DOT',
    'dot': 'DOT',
    'chainlink': 'LINK',
    'link': 'LINK',
    'avalanche': 'AVAX',
    'avax': 'AVAX',
    'polygon': 'MATIC',
    'matic': 'MATIC',
    'binance': 'BNB',
    'bnb': 'BNB',
}


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
    
    # Check emotional patterns FIRST (before buy/sell/advice)
    if any(re.search(p, message_lower) for p in EMOTIONAL_PATTERNS):
        detected_intents.append("emotional")
    # Check "get rid of" FIRST (SELL, not BUY)
    elif re.search(r'\bget rid of\b', message_lower):
        detected_intents.append("sell")
    # Check advice patterns FIRST (before buy/sell to catch "Should I buy")
    elif any(re.search(p, message_lower) for p in ADVICE_PATTERNS):
        detected_intents.append("advice")
    # Check alert patterns BEFORE price (to catch "Price alert")
    elif any(re.search(p, message_lower) for p in ALERT_PATTERNS):
        detected_intents.append("alert")
    # Check portfolio patterns FIRST (before price to catch "portfolio value")
    elif any(re.search(p, message_lower) for p in PORTFOLIO_PATTERNS):
        detected_intents.append("portfolio")
    # Check buy patterns BEFORE price (to catch "Buy if price drops")
    elif any(re.search(p, message_lower) for p in BUY_PATTERNS):
        detected_intents.append("buy")
    # Check sell patterns BEFORE price (to catch "Sell if price rises")
    elif any(re.search(p, message_lower) for p in SELL_PATTERNS):
        detected_intents.append("sell")
    # Check price patterns (but not if buy/sell context detected)
    elif any(re.search(p, message_lower) for p in PRICE_PATTERNS):
        detected_intents.append("price")
    
    # If multiple intents detected, use the first one but add secondary_intent
    if len(detected_intents) > 0:
        intent = detected_intents[0]
        secondary_intent = detected_intents[1] if len(detected_intents) > 1 else None
    else:
        intent = None
        secondary_intent = None
    
    # Fallback to old logic if no intents detected
    if not intent:
        # Check "get rid of" explicitly (SELL, not BUY)
        if re.search(r'\bget rid of\b', message_lower):
            intent = "sell"
        # Check greeting first (short messages)
        elif any(re.search(p, message_lower) for p in GREETING_PATTERNS):
            intent = "greeting"
        # Check emotional patterns
        elif any(re.search(p, message_lower) for p in EMOTIONAL_PATTERNS):
            intent = "emotional"
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
        
        # Special handling for ALERT intent
        if intent == "alert":
            # Extract price threshold (e.g., "hits 100k", "drops below 1500", "at 200")
            alert_price_match = re.search(ALERT_PRICE_PATTERN, message_lower)
            if not alert_price_match:
                # Try space-separated format: "Price alert BTC 75000"
                alert_price_match = re.search(ALERT_PRICE_PATTERN_SPACE, message_lower)
            if alert_price_match:
                price_str = alert_price_match.group(1).replace(',', '')
                # Handle 'k' suffix (100k = 100000)
                if 'k' in message_lower[alert_price_match.end()-2:alert_price_match.end()]:
                    price = float(price_str) * 1000
                else:
                    price = float(price_str)
            else:
                price = None
            
            # Extract direction (above/below)
            if re.search(ALERT_DIRECTION_ABOVE, message_lower):
                direction = "above"
            elif re.search(ALERT_DIRECTION_BELOW, message_lower):
                direction = "below"
            else:
                direction = "above"  # Default direction
            
            # For alerts, amount should be null (price threshold is not an amount)
            amount = None
        else:
            # Extract amount (for buy/sell)
            amount_match = re.search(AMOUNT_PATTERN, message_lower)
            amount = float(amount_match.group(1)) if amount_match else None
            
            # Extract price (e.g., "at 2000", "for $2000", "@ 2000")
            price_match = re.search(PRICE_PATTERN, message_lower)
            price = float(price_match.group(1).replace(',', '')) if price_match else None
            direction = None
        
        result = {
            "intent": intent,
            "asset": asset,
            "amount": amount,
            "price": price,
            "confidence": confidence,
            "source": "regex"
        }
        
        # Add direction for alerts
        if direction:
            result["direction"] = direction
        
        # Add secondary intent if detected
        if secondary_intent:
            result["secondary_intent"] = secondary_intent
        
        return result
    
    return None


async def detect_intent_hybrid(message: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Hybrid intent detection:
    1. Try regex first (fast, reliable)
    2. Fall back to OpenRouter LLM (clean JSON, no TUI artifacts)
    3. Single word handling (ETH, BUY, SELL)
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
    message_lower = clean_message.lower().strip()
    
    # SPECIAL HANDLING: "get rid of" is SELL, not BUY
    if re.search(r'\bget rid of\b', message_lower):
        # Extract asset
        asset_matches = re.findall(ASSET_PATTERN, message_lower)
        asset = asset_matches[0].upper() if asset_matches else None
        return {
            "intent": "sell",
            "asset": asset,
            "amount": None,
            "price": None,
            "confidence": 0.95,
            "source": "regex"
        }
    
    # SPECIAL HANDLING: "Get {asset} price" is PRICE, not BUY
    if re.search(r'\bget\s+(?:btc|eth|sol|ada|doge|xrp|dot|link|avax|matic|bnb)\s+price\b', message_lower):
        # Extract asset
        asset_matches = re.findall(ASSET_PATTERN, message_lower)
        asset = asset_matches[0].upper() if asset_matches else None
        return {
            "intent": "price",
            "asset": asset,
            "amount": None,
            "price": None,
            "confidence": 0.95,
            "source": "regex"
        }
    
    # SPECIAL HANDLING: Single word commands
    words = message_lower.split()
    if len(words) == 1:
        word = words[0]
        
        # Single asset word (ETH, BTC, SOL) → price intent
        if word in SINGLE_ASSET_WORDS:
            return {
                "intent": "price",
                "asset": ASSET_ALIASES.get(word, word.upper()),
                "amount": None,
                "price": None,
                "confidence": 0.95,
                "source": "regex"
            }
        
        # Single action word (BUY, SELL) → action intent
        if word in SINGLE_ACTION_WORDS:
            return {
                "intent": word,
                "asset": None,
                "amount": None,
                "price": None,
                "confidence": 0.90,
                "source": "regex"
            }
        
        # Single word intent mapping
        if word in SINGLE_WORD_INTENTS:
            return {
                "intent": SINGLE_WORD_INTENTS[word],
                "asset": None,
                "amount": None,
                "price": None,
                "confidence": 0.90,
                "source": "regex"
            }
    
    # Fast path: regex for multi-word commands
    regex_result = detect_intent_regex(clean_message)
    if regex_result:
        return regex_result
    
    # Fallback: _regex_fallback_intent for single word and simple commands
    regex_fallback = _regex_fallback_intent(clean_message)
    if regex_fallback:
        return regex_fallback
    
    # Slow path: OpenRouter LLM for complex commands (clean JSON, no TUI)
    # NOTE: Disabled due to OpenRouter rate limits on free tier
    # Using regex fallback for ALL commands to ensure reliability
    # TODO: Re-enable LLM when OpenRouter credits added
    
    # Use regex fallback for all commands (no rate limits, instant)
    regex_result = _regex_fallback_intent(clean_message)
    if regex_result:
        return regex_result
    
    # Fallback for truly unknown commands
    return {
        "intent": "unknown",
        "asset": None,
        "amount": None,
        "price": None,
        "confidence": 0.0,
        "source": "fallback"
    }


async def classify_intent_openrouter(message: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Use OpenRouter API for intent classification (clean JSON, no TUI artifacts)
    """
    
    # First try regex fallback for common patterns (fast, no API call)
    regex_fallback = _regex_fallback_intent(message)
    if regex_fallback and regex_fallback["intent"] != "unknown":
        return regex_fallback
    
    context_str = ""
    if context:
        context_str = f"""
Context:
- Previous messages: {json.dumps(context.get('messages', []))}
- Portfolio: {json.dumps(context.get('portfolio', {}))}
"""
    
    prompt = f"""You are Jarvix, an AI crypto assistant. Parse this command and return ONLY JSON.

User message: "{message}"
{context_str}

Return ONLY a JSON object with this exact structure:
{{
    "intent": "buy|sell|price|portfolio|stop_loss|advice|alert|greeting|unknown",
    "asset": "BTC|ETH|SOL|ADA|DOGE|XRP|DOT|LINK|AVAX|MATIC|null",
    "amount": number or null,
    "price": number or null,
    "confidence": 0.0 to 1.0
}}

Rules:
- intent: The user's primary intention
- asset: The cryptocurrency mentioned (uppercase), null if not specified
- amount: Numeric amount mentioned, null if not specified
- price: Price target mentioned, null if not specified
- confidence: How certain you are (1.0 = very certain)

Examples:
"Buy 100 ETH" -> {{"intent": "buy", "asset": "ETH", "amount": 100, "price": null, "confidence": 0.95}}
"What's BTC price?" -> {{"intent": "price", "asset": "BTC", "amount": null, "price": null, "confidence": 0.95}}
"ETH" -> {{"intent": "price", "asset": "ETH", "amount": null, "price": null, "confidence": 0.90}}
"BUY" -> {{"intent": "buy", "asset": null, "amount": null, "price": null, "confidence": 0.85}}
"Sell" -> {{"intent": "sell", "asset": null, "amount": null, "price": null, "confidence": 0.85}}
"Sell everything!!!" -> {{"intent": "sell", "asset": null, "amount": null, "price": null, "confidence": 0.90}}
"Good morning" -> {{"intent": "greeting", "asset": null, "amount": null, "price": null, "confidence": 0.95}}
"I want to buy some SOL" -> {{"intent": "buy", "asset": "SOL", "amount": null, "price": null, "confidence": 0.90}}

Return ONLY the JSON object, no other text."""

    response = await call_openrouter(prompt)
    
    # Check if rate limited or error
    if "rate_limited" in response.lower() or "rate limit" in response.lower() or response.startswith("Error:"):
        print(f"[RATE LIMIT] OpenRouter rate limited, using regex fallback for: {message[:50]}...")
        return _regex_fallback_intent(message) or {
            "intent": "unknown",
            "asset": None,
            "amount": None,
            "price": None,
            "confidence": 0.0
        }
    
    # Extract JSON from response
    try:
        # Find JSON object with intent field
        json_pattern = r'\{[^{}]*"intent"[^{}]*\}'
        json_matches = re.findall(json_pattern, response, re.DOTALL)
        if json_matches:
            # Take the first valid JSON
            for match in json_matches:
                try:
                    result = json.loads(match)
                    if "intent" in result:
                        return {
                            "intent": result.get("intent", "unknown"),
                            "asset": result.get("asset"),
                            "amount": result.get("amount"),
                            "price": result.get("price"),
                            "confidence": result.get("confidence", 0.5)
                        }
                except json.JSONDecodeError:
                    continue
    except (json.JSONDecodeError, AttributeError):
        pass
    
    # Try to find any JSON object
    try:
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            return {
                "intent": result.get("intent", "unknown"),
                "asset": result.get("asset"),
                "amount": result.get("amount"),
                "price": result.get("price"),
                "confidence": result.get("confidence", 0.5)
            }
    except (json.JSONDecodeError, AttributeError):
        pass
    
    # Fallback to regex
    fallback = _regex_fallback_intent(message)
    if fallback:
        return fallback
    
    # Final fallback to unknown
    return {
        "intent": "unknown",
        "asset": None,
        "amount": None,
        "price": None,
        "confidence": 0.0
    }


def _regex_fallback_intent(message: str) -> Optional[Dict[str, Any]]:
    """
    Fallback intent detection using regex when LLM fails
    Returns None if no pattern matches
    """
    message_lower = message.lower().strip()
    
    # Check for empty message
    if not message_lower:
        return None
    
    # Single word handling
    words = message_lower.split()
    if len(words) == 1:
        word = words[0]
        
        # Single asset word (ETH, BTC, SOL) → price intent
        if word in SINGLE_ASSET_WORDS:
            return {
                "intent": "price",
                "asset": ASSET_ALIASES.get(word, word.upper()),
                "amount": None,
                "price": None,
                "confidence": 0.95,
                "source": "regex_fallback"
            }
        
        # Single action word (BUY, SELL) → action intent
        if word in SINGLE_ACTION_WORDS:
            return {
                "intent": word,
                "asset": None,
                "amount": None,
                "price": None,
                "confidence": 0.90,
                "source": "regex_fallback"
            }
        
        # Single word intent mapping
        if word in SINGLE_WORD_INTENTS:
            return {
                "intent": SINGLE_WORD_INTENTS[word],
                "asset": None,
                "amount": None,
                "price": None,
                "confidence": 0.90,
                "source": "regex_fallback"
            }
    
    # Multi-word regex patterns
    intent = None
    
    # Check emotional patterns FIRST (before buy/sell/advice)
    if any(re.search(p, message_lower) for p in EMOTIONAL_PATTERNS):
        detected_intents.append("emotional")
    # Check "get rid of" FIRST (SELL, not BUY)
    elif re.search(r'\bget rid of\b', message_lower):
        intent = "sell"
    # Check advice patterns FIRST
    elif any(re.search(p, message_lower) for p in ADVICE_PATTERNS):
        intent = "advice"
    # Check alert patterns BEFORE price
    elif any(re.search(p, message_lower) for p in ALERT_PATTERNS):
        intent = "alert"
    # Check portfolio patterns FIRST
    elif any(re.search(p, message_lower) for p in PORTFOLIO_PATTERNS):
        intent = "portfolio"
    # Check buy patterns BEFORE price
    elif any(re.search(p, message_lower) for p in BUY_PATTERNS):
        intent = "buy"
    # Check sell patterns BEFORE price
    elif any(re.search(p, message_lower) for p in SELL_PATTERNS):
        intent = "sell"
    # Check price patterns
    elif any(re.search(p, message_lower) for p in PRICE_PATTERNS):
        intent = "price"
    # Check greeting
    elif any(re.search(p, message_lower) for p in GREETING_PATTERNS):
        intent = "greeting"
    # Check stop loss
    elif any(re.search(p, message_lower) for p in STOP_LOSS_PATTERNS):
        intent = "stop_loss"
    
    if intent:
        # Extract asset
        asset_matches = re.findall(ASSET_PATTERN, message_lower)
        asset = asset_matches[0].upper() if asset_matches else None
        
        # Extract amount
        amount_match = re.search(AMOUNT_PATTERN, message_lower)
        amount = float(amount_match.group(1)) if amount_match else None
        
        # Extract price
        price_match = re.search(PRICE_PATTERN, message_lower)
        price = float(price_match.group(1).replace(',', '')) if price_match else None
        
        return {
            "intent": intent,
            "asset": asset,
            "amount": amount,
            "price": price,
            "confidence": 0.85,
            "source": "regex_fallback"
        }
    
    return None
