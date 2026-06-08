"""
Hybrid Intent Detection for Jarvix
Fast regex for common commands, LLM fallback for complex ones
"""

import re
import json
from typing import Dict, Any, Optional
from .openrouter_client import call_openrouter
from .self_learning import get_learning_system
from .auto_learning import get_auto_learning_system

# Fast regex patterns for common commands
# Latin scripts
BUY_PATTERNS = [
    r'\b(buy|purchase|acquire|add|invest in|stack|enter.*position|long|don\'t miss|dont miss|grab|pick up|moon|lambo|rocket|time to buy|buying time|thinking about buying|considering buying|possibly get|kharido|lena hai|comprar|acheter|kaufen|사기|شراء|Купить|comprare|kopen|al|mua|ซื้อ|beli|kupić|köp|Αγορά|購入)\b',
    # "Get" is BUY, but NOT "get rid of" (that's SELL)
    r'\bget\b(?!\s+rid\s+of)',
    # "Load up" and "accumulate" are BUY
    r'(?:^|[^a-zA-Z0-9])(load up|accumulate|DCA|dollar cost average)(?:^|[^a-zA-Z0-9])',
    # "BTFD" - Buy The Fucking Dip
    r'(?:^|[^a-zA-Z0-9])(btfd|buy the fucking dip|buy the dip)(?:^|[^a-zA-Z0-9])',
    # Frequency/recurring buy patterns
    r"\b(buy|purchase|get|accumulate)\b.*\b(every|daily|weekly|monthly|auto|recurring)\b",
    r"\b(dca|dollar cost average)\b.*\binto\b",
    # Conditional buy patterns
    r'\bbuy\b.*\b(if|when|drops|dips|crashes|rises|pumps|moons)\b',
    r'\bbuy\s+.*\s+(?:dip|low|cheap|discount|bargain)\b',
]
SELL_PATTERNS = [
    r'\b(sell|sale|dump|cash out|liquidate|unload|offload|exit|crash|panic|emergency|stop loss|limit sell|time to sell|selling time|thinking about selling|thinking of selling|thinking of dumping|considering selling|possibly unload|get out|take profits|profit taking|becho|bech do|dena hai|nikal do|nikat do|vender|vendre|verkaufen|팔기|بيع|Продать|vendere|verkopen|sat|bán|ขาย|jual|sprzedać|sälj|Πώληση|販売)\b',
    # "Get rid of" is SELL, not BUY
    r'\bget rid of\b',
    # "Remove from portfolio" is SELL
    r'\bremove\b.*\bportfolio\b',
    # Short selling patterns
    r"(?:^|[^a-zA-Z0-9])(short|go short|enter short|open short|take short)(?:$|[^a-zA-Z0-9])",
    # Trading/position management
    r"(?:^|[^a-zA-Z0-9])(close|trim|reduce|cut)(?:$|[^a-zA-Z0-9]).*(?:^|[^a-zA-Z0-9])(trade|position|exposure|losses)(?:$|[^a-zA-Z0-9])|(?:^|[^a-zA-Z0-9])(take profit|tp|stfr|sell the fucking rip|sell the freaking rip|scale out|trailing stop|sl)(?:$|[^a-zA-Z0-9])",
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
    r'\b(price|prices|cost|value|how much|worth|rate|chart|show me|kitna|kya chal raha hai|kya scene hai|ka bhav|ka rate|precio|prix|preis|가격|سعر|Цена|prezzo|prijs|fiyat|giá|ราคา|harga|cena|pris|Τιμή|going up|going down|pump|dump|mooning|crashing|support|resistance|all time high|ath|market|scene)\b'
]

# Non-Latin scripts (Chinese, Japanese, Russian) - no word boundaries
BUY_PATTERNS_NONLATIN = [
    r'购买|買う|买入|買入|購入|Купить|購入',
]
SELL_PATTERNS_NONLATIN = [
    r'出售|売る|卖出|売出|売却|Продать|販売',
]
PRICE_PATTERNS_NONLATIN = [
    r'价格|価格|價格|料金|Цена',
]
PORTFOLIO_PATTERNS = [
    r'(?:^|[^a-zA-Z0-9])(portfolio|balance|holdings|net worth|what do i have|what do i own|show my|my assets|kitna paisa|mere paas|hold|assets|show assets|how am i doing|p&l|profit.*loss|summary|gains|do i have|do i own|amount|positions|allocation|total value|my coins|what am i holding|portfolio check|assets overview|mon portefeuille|mein Portfolio|mera portfolio|mi cartera|il mio portafoglio|mijn portefeuille|minha carteira|benim portföyüm|danh mục đầu tư|min portfölj|η χαρτοθήκη μου|私のポートフォリオ|我的投资组合|мой портфель|محفظتي)(?:$|[^a-zA-Z0-9])'
]
PORTFOLIO_PATTERNS_NONLATIN = [
    r'ポートフォリオ|投资组合|投資組合',
]
STOP_LOSS_PATTERNS = [r'\b(stop.loss|stoploss|protect|stop loss)\b']

# Add stop loss as sell intent - when triggered, sell
STOP_LOSS_SELL_PATTERNS = [r'\b(stop loss triggered|stoploss triggered|stop loss hit|stoploss hit)\b']
ADVICE_PATTERNS = [
    r'(?:^|[^a-zA-Z0-9])(hold or sell|buy or sell|keep or sell|keep or buy)(?:$|[^a-zA-Z0-9])',
    r'\b(should i|advice|recommend|what do you think|analysis|help|understand|confused|is.*good investment|what about|advise on|market analysis|good time to|what do you recommend|crypto advice|help me understand|should i diversify|should i hold|should i sell|is it time to|is it good to|which crypto to|what to invest in|is.*a good buy|is it worth|worth buying|worth investing|should i buy|should i get|should i purchase|should i acquire|is.*worth it|would you recommend|do you suggest|any thoughts on|what\'s your take)\b',
    r'\b(your opinion|your thoughts|your analysis|your recommendation|your advice|your suggestion|your view|your perspective|your insight|your understanding|your knowledge|your expertise|your experience|your wisdom|your guidance|your counsel|your direction)\b',
    r'\b(thoughts on|opinion on|recommendation for|advice on|analysis of|view on|perspective on|insight on|take on)\b',
    r'\b(hold or sell|buy or sell|should i hold|should i sell|is it too late|too late to|worth it|worth buying|worth investing|worth getting)\b',
    r'\b(kya kharidu|conseil pour|rat für|rat fur|conselho para|consiglio per|advies over|öneri|tavsiye|khuyến nghị|råd om|συμβουλή για|アドバイス|建议|建議|совет для)\b',
]
ALERT_PATTERNS = [r'\b(alert|notify|tell me when|warn me|set alert|set notification|remind me|watch for|keep an eye on|let me know when|inform me when|ping me when|message me when|send me when|update me when|tell me if|warn me if|alert me if|notify me if|remind me if|watch if|keep an eye if|let me know if|inform me if|ping me if|message me if|send me if|update me if)\b']

# Alert-specific patterns for price threshold extraction
ALERT_PRICE_PATTERN = r'(?:hits|reaches|goes above|above|drops below|below|falls to|at)\s+(\d+(?:,\d{3})*(?:\.\d+)?)(?:k|K)?'
ALERT_PRICE_PATTERN_SPACE = r'(?:btc|eth|sol|ada|doge|xrp|dot|link|avax|matic|bnb|usdt|usdc|dai)\s+(\d+(?:,\d{3})*(?:\.\d+)?)(?:k|K)?'
ALERT_DIRECTION_ABOVE = r'\b(hits|reaches|goes above|above|pumps|moons)\b'
ALERT_DIRECTION_BELOW = r'\b(drops below|below|falls to|dump|crashes)\b'
GREETING_PATTERNS = [r'\b(hello|hi|hey|good morning|good afternoon|good evening|good night|greetings|greeting|welcome|what is up|whats up|what\'s up|what up|how are you|how do you do|how is it going|how\'s it going|what\'s going on|whats going on|nice to meet you|pleased to meet you|hii|hiii|namaste|salam|hola|ciao|jarvix|you there|wake up|yo|sup|howdy|g\'day|gday|bonjour|guten tag|konnichiwa|annyeong|salaam|marhaba|shalom|sawubona|jambo|what\'s up|sup|howdy|g\'day|gday|yo|hey there|hi there|hello there|greetings|salutations|how goes it|what\'s new|whats new|long time no see|good to see you|nice to see you|pleased to see you|happy to see you|glad to see you|good to meet you|nice to meet you|pleased to meet you|happy to meet you|glad to meet you|good day|good evening|good night|good afternoon|good morning|morning|evening|privet|privyet|привет|hallo|merhaba|xin chao|sawasdee|selamat|hej|hej hej|hejsan|halla|hallå|hei|heii|moi|tere|tsau|labas|sveiki|ahoj|czesc|cześć|szia|servus|salut|buna|alo|shalom|salaam|marhaban|as-salam|assalam|konnichi wa|ohayo|ohayou|annyeong|annyeonghaseyo|ni hao|namaskar|namaskara|satsriakal|sat sri akal|jo|jo jo|sawatdee|sawatdee krub|sawatdee kha|selamat pagi|selamat siang|selamat sore|selamat malam|apa kabar|halo|hai|hei hei|mornin|evenin|howdy do|howdy partner|yoo|yooo|yoooo|sup dude|sup bro|sup man|yo dude|yo bro|yo man|hey dude|hey bro|hey man|hi dude|hi bro|hi man|hello dude|hello bro|hello man)\b']

# Emotional patterns for sentiment detection
EMOTIONAL_PATTERNS = [
    r"\b(i am|i'm|feeling|so|very|really|extremely|quite|pretty|too|so)\s+(happy|sad|angry|excited|thrilled|frustrated|scared|worried|nervous|anxious|confused|disappointed|stressed|overwhelmed|shocked|surprised|grateful|hopeful|confident|bullish|bearish|terrified|ecstatic|depressed|furious|delighted|content|peaceful|calm|relaxed|tense|uneasy|restless|impatient|satisfied|unsatisfied|great|best|worst|uncertain|panic|fear|fomo|fud)\b",
    r"\b(i|this|that|it)\s+(is|was|has been|will be)\s+(amazing|awesome|terrible|great|best|worst|horrible|fantastic|wonderful|awful|incredible|disgusting|beautiful|ugly|perfect|disastrous|magnificent|brilliant|dreadful|excellent|pathetic|outstanding|unacceptable|remarkable|shocking|surprising|disappointing|frustrating|confusing|overwhelming|stressful|worrying|concerning|terrifying|exhilarating|depressing|uplifting|heartbreaking|heartwarming)\b",
    r"\b(i|we)\s+(love|hate|like|dislike|adore|despise|enjoy|detest|appreciate|resent|admire|loathe|cherish|abhor|treasure|dread|relish|fear|distrust|trust|value|disregard)\s+(this|that|it|the|crypto|market|bitcoin|eth|btc|sol|trading|investing|you|jarvix)\b",
    r"\b(feeling|feel)\s+(good|bad|better|worse|fine|okay|ok|not good|not well|sick|tired|energetic|lazy|motivated|unmotivated|inspired|uninspired|lost|found|empty|full|broken|healed|strong|weak|powerless|empowered|vulnerable|protected|alone|connected|loved|unloved|accepted|rejected|understood|misunderstood|seen|unseen|heard|ignored|valued|worthless)\b",
    r"\b(mood|vibe|energy|spirit|soul|heart|mind|head|gut|instinct|intuition)\s+(is|feels|seems|looks|sounds|tastes|smells)\b",
    r"\b(feeling|feel)\s+(great|good|bad|awesome|terrible|amazing|wonderful|awful|fantastic|excellent|pathetic|outstanding|unacceptable|remarkable|shocking|surprising|disappointing|frustrating|confusing|overwhelming|stressful|worrying|concerning|terrifying|exhilarating|depressing|uplifting|heartbreaking|heartwarming)\b",
    r"\b(best|worst)\s+(day|week|month|year|time|moment|experience|memory|decision|choice|option|alternative|result|outcome|performance|showing|effort|attempt|try|shot|guess|estimate|prediction|forecast|projection|expectation|hope|dream|wish|desire|want|need|requirement|demand|request|suggestion|recommendation|advice|tip|hint|clue|idea|thought|thinking|feeling|emotion|mood|vibe|energy|spirit|soul|heart|mind|head|gut|instinct|intuition)\b",
    r"\b(scared|worried|stressed|panicking|freaking out|losing it|losing my mind|going crazy|can't take|cannot take|can't handle|cannot handle|too much|overwhelmed|devastated|heartbroken|destroyed|ruined|finished|done|dead|gone|lost|hopeless|helpless|powerless|worthless|useless|pointless|meaningless|empty|hollow|numb|shocked|stunned|speechless|breathless|mind blown|blown away|taken aback|caught off guard|unprepared|ready|go|all in|in it|committed|dedicated|devoted|loyal|faithful|true|honest|sincere|genuine|real|authentic|actual|valid|legitimate|legal|lawful|permissible|acceptable|appropriate|suitable|fit|ready|prepared|willing|eager|enthusiastic|passionate|zealous|ardent|fervent|intense|extreme|ultimate|final|last|end|finish|complete|total|full|absolute|complete|utter|sheer|pure|total|complete|absolute|utter|sheer|pure|total)\b",
    r"\b(panic|fear|anxiety|anxious|nervous|terrified|frightened|scared|worried|stressed|depressed|sad|crying|tears|regret|mistake|error|wrong|bad|terrible|horrible|awful|disgusting|pathetic|unacceptable|disappointing|frustrating|confusing|overwhelming|stressful|worrying|concerning|terrifying|depressing|heartbreaking|oh no|oh god|oh my god|omg|wtf|what the|holy shit|damn|dammit|damm it|fuck|fucking|shit|crap|hell|jesus christ|cant take it|cannot take it|giving up|so tired|exhausted|losing it|going crazy|freaking out|im done|i am done)\b",
    r"\b(i need help|please help|someone help|help me now|i\'m begging|i\'m desperate|i\'m drowning|i\'m struggling|i\'m suffering|i\'m in pain|i\'m hurting|i\'m broken|i\'m lost|i\'m confused|i\'m scared|i\'m terrified|i\'m frightened|i\'m worried|i\'m stressed|i\'m overwhelmed|i\'m devastated|i\'m heartbroken|i\'m destroyed|i\'m ruined|i\'m finished|i\'m done|i\'m dead|i\'m gone|i\'m hopeless|i\'m helpless|i\'m powerless|i\'m worthless|i\'m useless)\b",
    r"\b(help me|save me|rescue me|help us|save us|rescue us)\b",
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


# Agent task patterns - if detected, mark as unknown so universal parser handles it
AGENT_TASK_PATTERNS = [
    r'\b(buy\s+\w+\s+if\s+\w+\s+(drops|falls|below|under)|sell\s+\w+\s+if\s+\w+\s+(rises|pumps|above|over))\b',
    r'\b(buy\s+\w+\s+when\s+\w+\s+(drops|falls|below|under)|sell\s+\w+\s+when\s+\w+\s+(rises|pumps|above|over))\b',
    r'\b(monitor\s+\w+\s+every|watch\s+\w+\s+every|track\s+\w+\s+every)\b',
    r'\b(set\s+stop\s+loss|stop\s+loss\s+for)\b',
    r'\b(if\s+\w+\s+(drops|falls|below|under|rises|pumps|above|over|goes)\s+(then|and)\b)\b',
    r'\b(and\s+(then|message|notify|alert)\s+me)\b',
    r'\b(whenever|every\s+hour|every\s+day|every\s+minute)\b',
]

def is_agent_task(message: str) -> bool:
    """Check if message is a multi-step agent task"""
    msg_lower = message.lower()
    return any(re.search(p, msg_lower) for p in AGENT_TASK_PATTERNS)


def detect_intent_regex(message: str) -> Optional[Dict[str, Any]]:
    """
    Fast regex-based intent detection
    Returns None if no match (fall back to LLM)
    """
    # Check conditional sell BEFORE agent task (so "sell if pumps" works)
    message_lower = message.lower().strip()
    if re.search(r"(?:^|[^a-zA-Z0-9])(sell|dump|unload|liquidate|cash out|exit|close|take profit|tp|stfr|sell the rip|sell the fucking rip|sell the freaking rip|short|go short|enter short|open short|take short|market sell|limit sell|stop sell|trim|scale out|reduce|cut|stop loss|sl|trailing stop)\s+.*\s+(if|when|at|pumps|moons|rises|drops|dips|crashes|hits|reaches|goes above|goes below|crosses|breaks|falls|surges|spikes|dumps|corrects|recovers|rallies|pulls back|consolidates|breaks out|breaks down|reverses|bounces|rejects|retests|tests|holds|fails|closes|opens|moves|trends)(?:$|[^a-zA-Z0-9])", message_lower):
        return {"intent": "sell", "asset": None, "amount": None, "price": None, "confidence": 0.95, "source": "regex"}
    # Check conditional buy BEFORE agent task (so "buy if drops" works)
    elif re.search(r"(?:^|[^a-zA-Z0-9])(buy|purchase|get|acquire|add|pick up|grab|load up|accumulate|long|go long|enter long|open long|take long|market buy|limit buy|stop buy|dca|dollar cost average)\s+.*\s+(if|when|at|drops|dips|crashes|rises|pumps|moons|hits|reaches|goes above|goes below|crosses|breaks|falls|surges|spikes|dumps|corrects|recovers|rallies|pulls back|consolidates|breaks out|breaks down|reverses|bounces|rejects|retests|tests|holds|fails|closes|opens|moves|trends)(?:$|[^a-zA-Z0-9])", message_lower):
        return {"intent": "buy", "asset": None, "amount": None, "price": None, "confidence": 0.95, "source": "regex"}
    # Check for agent tasks - if detected, return unknown so universal parser handles it
    elif is_agent_task(message):
        return {"intent": "unknown", "asset": None, "amount": None, "price": None, "confidence": 0.9, "source": "regex", "universal_parse": True}
    
    # Don't lowercase for non-Latin scripts (Cyrillic, Chinese, etc.)
    # Check if message contains non-Latin characters
    has_nonlatin = any(ord(c) > 127 for c in message)
    
    if has_nonlatin:
        message_lower = message.strip()  # Keep original case
        # Check non-Latin buy patterns first
        if any(re.search(p, message) for p in BUY_PATTERNS_NONLATIN):
            return {"intent": "buy", "asset": None, "amount": None, "price": None, "confidence": 0.95, "source": "regex"}
        # Check non-Latin sell patterns
        if any(re.search(p, message) for p in SELL_PATTERNS_NONLATIN):
            return {"intent": "sell", "asset": None, "amount": None, "price": None, "confidence": 0.95, "source": "regex"}
        # Check non-Latin price patterns
        if any(re.search(p, message) for p in PRICE_PATTERNS_NONLATIN):
            return {"intent": "price", "asset": None, "amount": None, "price": None, "confidence": 0.95, "source": "regex"}
        # Check non-Latin portfolio patterns
        try:
            if any(re.search(p, message) for p in PORTFOLIO_PATTERNS_NONLATIN):
                return {"intent": "portfolio", "asset": None, "amount": None, "price": None, "confidence": 0.95, "source": "regex"}
        except NameError:
            pass
    else:
        message_lower = message.lower().strip()
    
    # Check for empty message
    if not message_lower:
        return {"intent": "unknown", "asset": None, "amount": None, "price": None, "confidence": 0.95, "source": "regex"}
    
    intent = None
    confidence = 0.95
    
    # Check for multiple intents
    detected_intents = []
    
    # Special check: 'hold or sell' / 'buy or sell' is ADVICE, not portfolio
    if re.search(r"(?:^|[^a-zA-Z0-9])(hold or sell|buy or sell|keep or sell|keep or buy)(?:$|[^a-zA-Z0-9])", message_lower):
        detected_intents.append("advice")
    # Check portfolio patterns FIRST (before emotional to catch "total value")
    elif any(re.search(p, message_lower) for p in PORTFOLIO_PATTERNS):
        detected_intents.append("portfolio")
    # Check BTFD patterns before emotional (to catch "buy the fucking dip")
    elif re.search(r"(?:^|[^a-zA-Z0-9])(btfd|buy the fucking dip|buy the freaking dip)(?:$|[^a-zA-Z0-9])", message_lower):
        detected_intents.append("buy")
    # Check "go long" before emotional (to catch "go long ETH")
    elif re.search(r"(?:^|[^a-zA-Z0-9])go\s+long(?:$|[^a-zA-Z0-9])", message_lower):
        detected_intents.append("buy")
    # Check "sell the fucking rip" before emotional
    elif re.search(r"(?:^|[^a-zA-Z0-9])(sell the fucking rip|sell the freaking rip|stfr)(?:$|[^a-zA-Z0-9])", message_lower):
        detected_intents.append("sell")
    # Check "go short" before emotional
    elif re.search(r"(?:^|[^a-zA-Z0-9])go\s+short(?:$|[^a-zA-Z0-9])", message_lower):
        detected_intents.append("sell")
    # Check "help me decide/guide me" before emotional (it's ADVICE)
    elif re.search(r"(?:^|[^a-zA-Z0-9])(help me decide|guide me|not sure about|confused about|lena chahiye|bechna chahiye|kya kharidu)(?:$|[^a-zA-Z0-9])", message_lower):
        detected_intents.append("advice")
    # Check emotional patterns (before buy/sell/advice)
    elif any(re.search(p, message_lower) for p in EMOTIONAL_PATTERNS):
        detected_intents.append("emotional")
    # Check "get rid of" FIRST (SELL, not BUY)
    elif re.search(r'\bget rid of\b', message_lower):
        detected_intents.append("sell")
    # Check "get out" (SELL, not BUY)
    elif re.search(r'\bget out\b', message_lower):
        detected_intents.append("sell")
    # Check alert patterns BEFORE advice (to catch "set alert" before "help" in advice)
    elif any(re.search(p, message_lower) for p in ALERT_PATTERNS):
        detected_intents.append("alert")
    # Check advice patterns (before buy/sell to catch "Should I buy")
    elif any(re.search(p, message_lower, re.IGNORECASE) for p in ADVICE_PATTERNS):
        detected_intents.append("advice")
    # Check directional swap/convert/exchange/trade
    # "swap/convert/exchange/trade [asset] for/to [asset]" = SELL (giving away first asset)
    # "buy/get [asset] for/with [asset]" = BUY (acquiring first asset)
    # "sell/dump/unload [asset] for [asset]" = SELL (giving away)
    buy_swap_match = re.search(r"(?:^|[^a-zA-Z0-9])(buy|get|purchase|acquire)\s+(btc|eth|sol|ada|doge|xrp|dot|link|avax|matic|bnb|usdt|usdc|dai)\s+(for|with)\s+(btc|eth|sol|ada|doge|xrp|dot|link|avax|matic|bnb|usdt|usdc|dai)(?:$|[^a-zA-Z0-9])", message_lower)
    swap_match = re.search(r"(?:^|[^a-zA-Z0-9])(swap|convert|exchange|trade)\s+(btc|eth|sol|ada|doge|xrp|dot|link|avax|matic|bnb|usdt|usdc|dai)\s+(for|to)\s+(btc|eth|sol|ada|doge|xrp|dot|link|avax|matic|bnb|usdt|usdc|dai)(?:$|[^a-zA-Z0-9])", message_lower)
    sell_swap_match = re.search(r"(?:^|[^a-zA-Z0-9])(sell|dump|unload)\s+(btc|eth|sol|ada|doge|xrp|dot|link|avax|matic|bnb|usdt|usdc|dai)\s+(for|to)\s+(btc|eth|sol|ada|doge|xrp|dot|link|avax|matic|bnb|usdt|usdc|dai)(?:$|[^a-zA-Z0-9])", message_lower)
    if buy_swap_match:
        detected_intents.append("buy")
    elif sell_swap_match:
        detected_intents.append("sell")
    elif swap_match:
        detected_intents.append("sell")
    # Check buy patterns BEFORE price (to catch "add ADA" as buy)
    elif any(re.search(p, message_lower) for p in BUY_PATTERNS):
        detected_intents.append("buy")
    # Check sell patterns BEFORE price (to catch "Sell if price rises")
    elif any(re.search(p, message_lower) for p in SELL_PATTERNS):
        detected_intents.append("sell")
    # Check "my worth/net worth" before price (it's PORTFOLIO)
    elif re.search(r"(?:^|[^a-zA-Z0-9])(my worth|net worth|what is my worth|how much is my)(?:$|[^a-zA-Z0-9])", message_lower):
        detected_intents.append("portfolio")
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
        elif re.search(r'\badd\s+(btc|eth|sol|ada|doge|xrp|dot|link|avax|matic|bnb|usdt|usdc|dai)\b', message_lower):
            intent = "buy"
        # Check sell with "remove" explicitly (before portfolio to catch "remove BTC from portfolio")
        elif re.search(r'\bremove\s+(btc|eth|sol|ada|doge|xrp|dot|link|avax|matic|bnb|usdt|usdc|dai)\b', message_lower):
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
        
        result = {
            "intent": intent,
            "asset": asset,
            "amount": None,
            "price": None,
            "confidence": confidence,
            "source": "regex"
        }
        
        # Add secondary intent if detected
        if secondary_intent:
            result["secondary_intent"] = secondary_intent
        
        return result
    
    # If no intent detected, return unknown instead of None
    return {"intent": "unknown", "asset": None, "amount": None, "price": None, "confidence": 0.5, "source": "regex"}


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
    
    # SPECIAL HANDLING: Non-Latin scripts (Japanese, Chinese, etc.)
    has_nonlatin = any(ord(c) > 127 for c in message)
    if has_nonlatin:
        # Check non-Latin buy patterns
        if any(re.search(p, message) for p in BUY_PATTERNS_NONLATIN):
            return {"intent": "buy", "asset": None, "amount": None, "price": None, "confidence": 0.95, "source": "regex"}
        # Check non-Latin sell patterns
        if any(re.search(p, message) for p in SELL_PATTERNS_NONLATIN):
            return {"intent": "sell", "asset": None, "amount": None, "price": None, "confidence": 0.95, "source": "regex"}
        # Check non-Latin price patterns
        if any(re.search(p, message) for p in PRICE_PATTERNS_NONLATIN):
            return {"intent": "price", "asset": None, "amount": None, "price": None, "confidence": 0.95, "source": "regex"}
        # Check non-Latin portfolio patterns
        try:
            if any(re.search(p, message) for p in PORTFOLIO_PATTERNS_NONLATIN):
                return {"intent": "portfolio", "asset": None, "amount": None, "price": None, "confidence": 0.95, "source": "regex"}
        except NameError:
            pass
    
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
    if re.search(r'\bget\s+(?:btc|eth|sol|ada|doge|xrp|dot|link|avax|matic|bnb|usdt|usdc|dai)\s+price\b', message_lower):
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
    
    # Fallback for truly unknown commands - now uses Universal Intent Parser
    from .universal_intent import handle_unknown_command
    
    # We return unknown but with a flag that tells main.py to use universal parser
    return {
        "intent": "unknown",
        "asset": None,
        "amount": None,
        "price": None,
        "confidence": 0.0,
        "source": "fallback",
        "universal_parse": True  # Signal to main.py to use universal parser
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


def detect_intent_with_learning(message: str, user_id: str = "default") -> Dict[str, Any]:
    """Detect intent with self-learning feedback loop"""
    
    # Step 1: Check learned patterns first (exact matches from feedback)
    learning_system = get_learning_system()
    learned_intent = learning_system.check_learned_pattern(message)
    if learned_intent:
        return {
            "intent": learned_intent,
            "asset": None,
            "amount": None,
            "price": None,
            "confidence": 0.98,
            "source": "learned",
            "learned": True
        }
    
    # Step 2: Check auto-learned patterns (behavioral patterns)
    auto_learning = get_auto_learning_system()
    auto_result = auto_learning.check_auto_learned_pattern(user_id, message)
    if auto_result:
        intent, confidence = auto_result
        return {
            "intent": intent,
            "asset": None,
            "amount": None,
            "price": None,
            "confidence": confidence,
            "source": "auto_learned",
            "auto_learned": True
        }
    
    # Step 3: Use regex detection
    result = detect_intent_regex(message)
    
    # Step 4: Record for auto-learning
    if result and result.get("intent"):
        auto_learning.record_command(user_id, message, result["intent"])
    
    return result

def report_correction(message: str, predicted_intent: str, correct_intent: str, user_id: str = "default"):
    """Report a correction to improve learning"""
    learning_system = get_learning_system()
    learning_system.add_correction(message, predicted_intent, correct_intent, user_id)
    
    # Also update auto-learning
    auto_learning = get_auto_learning_system()
    auto_learning.record_command(user_id, message, correct_intent)
    
    return True
