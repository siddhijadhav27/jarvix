"""
JARVIX Intent Classifier
Uses LLM for natural language understanding with regex as fast pre-filter
"""

import json
import re
from typing import Dict, Any, Optional
from enum import Enum

class Intent(Enum):
    BUY = "buy"
    SELL = "sell"
    PORTFOLIO = "portfolio"
    PRICE = "price"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    ADVICE = "advice"
    GREETING = "greeting"
    ALERT = "alert"
    EMOTIONAL = "emotional"
    UNKNOWN = "unknown"

# Fast regex pre-filter for obvious cases
FAST_PATTERNS = {
    Intent.GREETING: r"^(hi+|he+y+|he+l+o+w*|hola|bonjour|salam|as salaam|salaam|namaste|namaskar|sup|yo|good morning|good afternoon|good evening|good night|morning|evening|afternoon)\b",
    Intent.ALERT: r"\b(alert|notify|warn|watch|track|set alert|when.*hits|if.*drops|if.*rises)\b",
    Intent.PRICE: r"(price|cost|worth|trading at|how much|current price|market price|what is|what's|kitne|ka price|ka rate|rate kya|kya hai).*?(btc|bitcoin|eth|ethereum|sol|solana)|(btc|bitcoin|eth|ethereum|sol|solana).*?(price|cost|worth|trading at|how much|current price|market price|kitne|ka price|ka rate|rate kya|kya hai)",
    Intent.ADVICE: r"(should i|advice|recommend|is it good|worth buying|worth selling|\bhold\b|long|short|bullish|bearish|entry|exit|think about|opinion on|kya karu|salah|suggest|good investment|a good)",
    Intent.BUY: r"\b(buy|purchase|grab|get|acquire|invest in|pick up|load up on|go heavy on|kharidna|kharido|lena)\b",
    Intent.SELL: r"\b(sell|dump|offload|unload|liquidate|exit|dispose|bechdo|bechna|bech)\b",
    Intent.PORTFOLIO: r"\b(portfolio|holdings|assets|what do i own|my portfolio|net worth|positions|show my)\b",
    Intent.EMOTIONAL: r"\b(scared|afraid|worried|nervous|anxious|stressed|excited|happy|sad|angry|frustrated|panic|fear|greed|emotional|feel|feeling|dar lag|tension|ghabra)\b",
}

CLASSIFICATION_PROMPT = """You are a crypto trading assistant intent classifier.
Analyze the user message and return ONLY valid JSON. No explanation. No markdown. Just raw JSON.

{
  "intent": "buy|sell|portfolio|price|stop_loss|take_profit|advice|greeting|unknown",
  "asset": "BTC|ETH|SOL|ADA|DOT|XRP|DOGE|null",
  "amount": number|null,
  "amount_type": "fixed|percentage|all|half|null",
  "price": number|null,
  "confidence": 0.0-1.0,
  "needs_clarification": true|false,
  "clarification_question": "string|null"
}

Rules:
- intent: Classify the user's primary goal
- asset: Extract cryptocurrency name/ticker (BTC, ETH, SOL, etc.)
- amount: Numeric value only (100, 0.5, etc.)
- amount_type: "fixed" (100 ETH), "percentage" (50%), "all" (all my ETH), "half" (half my BTC)
- price: Target price if mentioned ($60k → 60000, $2,500 → 2500)
- confidence: How sure you are (0.0-1.0)
- needs_clarification: true if missing critical info (amount, asset)
- clarification_question: Ask user for missing info

Examples:
"Buy 100 ETH" → {"intent":"buy","asset":"ETH","amount":100,"amount_type":"fixed","price":null,"confidence":0.99,"needs_clarification":false,"clarification_question":null}
"Get some bitcoin" → {"intent":"buy","asset":"BTC","amount":null,"amount_type":null,"price":null,"confidence":0.85,"needs_clarification":true,"clarification_question":"How much Bitcoin would you like to buy?"}
"Should I buy SOL now?" → {"intent":"advice","asset":"SOL","amount":null,"amount_type":null,"price":null,"confidence":0.95,"needs_clarification":false,"clarification_question":null}
"Sell half my ETH at $3000" → {"intent":"sell","asset":"ETH","amount":50,"amount_type":"percentage","price":3000,"confidence":0.97,"needs_clarification":false,"clarification_question":null}
"What's my portfolio?" → {"intent":"portfolio","asset":null,"amount":null,"amount_type":null,"price":null,"confidence":0.99,"needs_clarification":false,"clarification_question":null}
"Price of Bitcoin" → {"intent":"price","asset":"BTC","amount":null,"amount_type":null,"price":null,"confidence":0.98,"needs_clarification":false,"clarification_question":null}
"Set stop-loss for BTC at $55k" → {"intent":"stop_loss","asset":"BTC","amount":null,"amount_type":null,"price":55000,"confidence":0.96,"needs_clarification":false,"clarification_question":null}
"Hi Jarvix" → {"intent":"greeting","asset":null,"amount":null,"amount_type":null,"price":null,"confidence":1.0,"needs_clarification":false,"clarification_question":null}
"I want to get some ETH" → {"intent":"buy","asset":"ETH","amount":null,"amount_type":null,"price":null,"confidence":0.88,"needs_clarification":true,"clarification_question":"How much ETH would you like to buy?"}
"Can you grab me some SOL?" → {"intent":"buy","asset":"SOL","amount":null,"amount_type":null,"price":null,"confidence":0.87,"needs_clarification":true,"clarification_question":"How much SOL would you like to buy?"}
"Let's go heavy on Bitcoin" → {"intent":"buy","asset":"BTC","amount":null,"amount_type":null,"price":null,"confidence":0.82,"needs_clarification":true,"clarification_question":"How much Bitcoin would you like to buy?"}
"ETH looks good, buy it" → {"intent":"buy","asset":"ETH","amount":null,"amount_type":null,"price":null,"confidence":0.84,"needs_clarification":true,"clarification_question":"How much ETH would you like to buy?"}

Now classify this message:"""


class IntentClassifier:
    """
    Hybrid classifier:
    1. Fast regex pre-filter for obvious cases (greetings, etc.)
    2. LLM classification for everything else
    """
    
    def __init__(self):
        self.use_llm = True
    
    def _extract_asset(self, message: str) -> Optional[str]:
        """Extract cryptocurrency asset from message"""
        message_lower = message.lower()
        
        # Map of asset names to tickers
        asset_map = {
            'bitcoin': 'BTC', 'btc': 'BTC',
            'ethereum': 'ETH', 'eth': 'ETH',
            'solana': 'SOL', 'sol': 'SOL',
            'cardano': 'ADA', 'ada': 'ADA',
            'polkadot': 'DOT', 'dot': 'DOT',
            'ripple': 'XRP', 'xrp': 'XRP',
            'dogecoin': 'DOGE', 'doge': 'DOGE',
        }
        
        # Check for each asset
        for name, ticker in asset_map.items():
            if name in message_lower:
                return ticker
        
        return None
    
    def classify(self, message: str) -> Dict[str, Any]:
        """
        Classify user intent (sync version)
        
        Returns:
            Dict with intent, entities, confidence, etc.
        """
        # Step 1: Fast regex pre-filter
        for intent, pattern in FAST_PATTERNS.items():
            match = re.search(pattern, message.lower())
            if match:
                # Extract asset from message
                asset = self._extract_asset(message)
                # Extract amount from regex groups
                amount = None
                if match.groups():
                    # Try to find numeric group
                    for group in match.groups():
                        if group and re.match(r'^\d*\.?\d+$', group):
                            amount = float(group)
                            break
                # If no amount in regex groups, try to extract from message
                if amount is None:
                    amount_match = re.search(r'(\d+\.?\d*)\s*(btc|eth|sol|bitcoin|ethereum|solana)', message.lower())
                    if amount_match:
                        amount = float(amount_match.group(1))
                return {
                    "intent": intent.value,
                    "asset": asset,
                    "amount": amount,
                    "amount_type": "units" if amount else None,
                    "price": None,
                    "confidence": 0.99,
                    "needs_clarification": False,
                    "clarification_question": None
                }
        
        # Step 2: LLM classification for complex cases
        if self.use_llm:
            return self._classify_with_llm(message)
        
        # Fallback
        return {
            "intent": "unknown",
            "asset": None,
            "amount": None,
            "amount_type": None,
            "price": None,
            "confidence": 0.0,
            "needs_clarification": True,
            "clarification_question": "I'm not sure what you mean. Try: 'Buy 100 ETH' or 'What's my portfolio?'"
        }
    
    def _classify_with_llm(self, message: str) -> Dict[str, Any]:
        """Use LLM for intent classification (sync)"""
        
        from .simple_router import simple_chat
        from .response_cleaner import clean_response
        
        prompt = f"{CLASSIFICATION_PROMPT}\n'{message}'"
        
        try:
            # Call LLM (sync version)
            raw_response = simple_chat(prompt)
            response_text = clean_response(raw_response)
            
            # Extract JSON from response
            cleaned = self._extract_json(response_text)
            
            # Parse JSON
            parsed = json.loads(cleaned)
            
            # Validate required fields
            required = ["intent", "asset", "amount", "amount_type", 
                       "price", "confidence", "needs_clarification"]
            
            for field in required:
                if field not in parsed:
                    parsed[field] = None
            
            return parsed
            
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON parse error: {e}")
            print(f"Raw response: {response_text[:200]}")
            return self._fallback_response(message)
        except Exception as e:
            print(f"⚠️ LLM classification error: {e}")
            return self._fallback_response(message)
    
    def _extract_json(self, text: str) -> str:
        """Extract JSON from LLM response"""
        
        # Remove markdown code blocks
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        
        # Find JSON with intent field (most reliable pattern)
        match = re.search(r'\{.*"intent".*\}', text, re.DOTALL)
        if match:
            return match.group(0)
        
        # Fallback: find any JSON object
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return match.group(0)
        
        return text.strip()
    
    def _fallback_response(self, message: str) -> Dict[str, Any]:
        """Fallback when LLM fails"""
        return {
            "intent": "unknown",
            "asset": None,
            "amount": None,
            "amount_type": None,
            "price": None,
            "confidence": 0.0,
            "needs_clarification": True,
            "clarification_question": "I'm not sure what you mean. Try: 'Buy 100 ETH' or 'What's my portfolio?'"
        }


# Test function
async def test_classifier():
    """Test intent classifier"""
    
    classifier = IntentClassifier()
    
    test_cases = [
        "Buy 100 ETH",
        "I want to get some ETH",
        "Can you grab me some SOL?",
        "Let's go heavy on Bitcoin",
        "ETH looks good, buy it",
        "What's my portfolio?",
        "Should I buy SOL now?",
        "Hi Jarvix",
        "Set stop-loss for BTC at $55k",
        "Sell half my ETH at $3000"
    ]
    
    print("🧪 Testing Intent Classifier (LLM-based)")
    print("=" * 60)
    
    for msg in test_cases:
        print(f"\n💬 '{msg}'")
        result = await classifier.classify(msg)
        
        print(f"   Intent: {result['intent']}")
        print(f"   Asset: {result['asset']}")
        print(f"   Amount: {result['amount']} {result['amount_type']}")
        print(f"   Confidence: {result['confidence']}")
        
        if result['needs_clarification']:
            print(f"   ❓ {result['clarification_question']}")
        else:
            print(f"   ✅ Ready to execute")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_classifier())
