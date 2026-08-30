"""
JARVIX Intent Classifier
Uses LLM for natural language understanding with regex as fast pre-filter
"""

import json
import re
import unicodedata
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
    UNKNOWN = "unknown"

# Fast regex pre-filter for obvious cases
FAST_PATTERNS = {
    Intent.GREETING: r"^(hi|hello|hey|hii|namaste|namaskar|नमस्ते|नमस्कार|good morning|good afternoon|good evening)\b",
}

CLASSIFICATION_PROMPT = """You are a crypto trading assistant. Analyze the user message and classify intent.

Return ONLY a JSON object. No explanation. No markdown. Just raw JSON.

Format:
{"intent": "buy|sell|price|portfolio|advice|greeting|unknown", "asset": "BTC|ETH|SOL|null", "amount": number|null, "price": number|null, "confidence": 0.0-1.0}

Examples:
"Buy 100 ETH" → {"intent": "buy", "asset": "ETH", "amount": 100, "price": null, "confidence": 0.95}
"What's BTC price?" → {"intent": "price", "asset": "BTC", "amount": null, "price": null, "confidence": 0.95}
"Hi there" → {"intent": "greeting", "asset": null, "amount": null, "price": null, "confidence": 0.95}
"What is the best time to buy Bitcoin?" → {"intent": "advice", "asset": "BTC", "amount": null, "price": null, "confidence": 0.92}
"Should I invest in Ethereum now?" → {"intent": "advice", "asset": "ETH", "amount": null, "price": null, "confidence": 0.93}

Now classify this message:"""


class IntentClassifier:
    """
    Hybrid classifier:
    1. Fast regex pre-filter for obvious cases (greetings, etc.)
    2. LLM classification for everything else
    """
    
    def __init__(self):
        self.use_llm = True
    
    def _detect_language(self, message: str) -> Dict[str, Any]:
        """Detect language with confidence score"""
        
        # Simple language detection based on character patterns
        import re
        
        # Check for Hindi characters
        if re.search(r'[\u0900-\u097F]', message):
            return {"language": "hi", "confidence": 0.95, "english": False}
        
        # Check for Hinglish (English + Hindi mixed)
        if re.search(r'\b(hai|kya|kaise|kyu|nahi|acha|bhai|sir|ji)\b', message.lower()):
            return {"language": "hi-en", "confidence": 0.90, "english": False}
        
        # Check for Japanese
        if re.search(r'[\u3040-\u309F\u30A0-\u30FF]', message):
            return {"language": "ja", "confidence": 0.95, "english": False}
        
        # Check for Spanish
        if re.search(r'\b(hola|como|estas|buenos|dias|gracias)\b', message.lower()):
            return {"language": "es", "confidence": 0.85, "english": False}
        
        # Check for French
        if re.search(r'\b(bonjour|salut|comment|ca va|merci)\b', message.lower()):
            return {"language": "fr", "confidence": 0.85, "english": False}
        
        # Check for German
        if re.search(r'\b(hallo|guten|tag|danke|wie|geht)\b', message.lower()):
            return {"language": "de", "confidence": 0.85, "english": False}
        
        # Default: English
        return {"language": "en", "confidence": 0.95, "english": True}
    
    async def _classify_with_llm(self, message: str) -> Dict[str, Any]:
        """Use LLM for intent classification"""
        
        from .simple_router import simple_chat
        from .response_cleaner import clean_response
        
        prompt = f"{CLASSIFICATION_PROMPT}\n'{message}'"
        
        try:
            # Call LLM via GitHub Models (GPT-4o)
            print(f"🔍 [DEBUG] Calling GPT-4o for: {message}")
            from .github_models_client import call_llm
            raw_response = await call_llm(prompt)
            print(f"🔍 [DEBUG] Raw GPT-4o response: {raw_response[:200]}")
            response_text = clean_response(raw_response)
            print(f"🔍 [DEBUG] Cleaned response: {response_text[:200]}")
            
            # Extract JSON from response
            cleaned = self._extract_json(response_text)
            print(f"🔍 [DEBUG] Extracted JSON: {cleaned[:200]}")
            
            # Parse JSON
            parsed = json.loads(cleaned)
            print(f"🔍 [DEBUG] Parsed JSON: {parsed}")
            
            # Validate required fields - use defaults if missing
            required_defaults = {
                "intent": "unknown",
                "asset": None,
                "amount": None,
                "amount_type": None,
                "price": None,
                "confidence": 0.5,
                "needs_clarification": False,
                "clarification_question": None
            }
            
            for field, default in required_defaults.items():
                if field not in parsed:
                    parsed[field] = default
            
            # Add message field if missing
            if "message" not in parsed:
                lang_result = self._detect_language(message)
                parsed["message"] = self._get_fast_response(parsed.get("intent", "unknown"), lang_result["language"])
            
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
        
        # Remove TUI artifacts
        text = re.sub(r'⚕.*?\n', '', text)
        text = re.sub(r'─.*?\n', '', text)
        text = re.sub(r'╭.*?\n', '', text)
        text = re.sub(r'╰.*?\n', '', text)
        text = re.sub(r'│.*?\n', '', text)
        text = re.sub(r'❯.*?\n', '', text)
        text = re.sub(r'⏲.*?\n', '', text)
        text = re.sub(r'⏱.*?\n', '', text)
        text = re.sub(r'●.*?\n', '', text)
        text = re.sub(r'\(⌐■_■\).*?\n', '', text)
        text = re.sub(r'ಠ_ಠ.*?\n', '', text)
        
        # Find JSON with intent field (most reliable pattern)
        match = re.search(r'\{[^{}]*"intent"[^{}]*\}', text, re.DOTALL)
        if match:
            return match.group(0)
        
        # Fallback: find any JSON object
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return match.group(0)
        
        return text.strip()
    
    async def classify(self, message: str) -> Dict[str, Any]:
        """Hybrid intent classification"""
        
        # Normalize message
        normalized_msg = unicodedata.normalize('NFKC', message)
        normalized_msg_lower = normalized_msg.casefold()
        
        # 1. Fast pattern matching (regex)
        for intent, pattern in FAST_PATTERNS.items():
            if re.search(pattern, normalized_msg_lower, re.IGNORECASE):
                # Generate response using hybrid system
                response_data = await self.generate_response(intent.value, message)
                return {
                    "intent": intent.value,
                    "asset": None,
                    "amount": None,
                    "amount_type": None,
                    "price": None,
                    "confidence": 0.99,
                    "needs_clarification": False,
                    "clarification_question": None,
                    "message": response_data["message"],
                    "source": response_data["source"],
                    "language": response_data["language"],
                    "language_confidence": response_data["language_confidence"],
                    "latency_ms": response_data["latency_ms"]
                }
        
        # 2. LLM fallback for complex queries
        print(f"🔍 [DEBUG] use_llm={self.use_llm}, checking LLM fallback...")
        if self.use_llm:
            print(f"🔍 [DEBUG] Calling _classify_with_llm for: {message}")
            result = await self._classify_with_llm(message)
            print(f"🔍 [DEBUG] LLM result: {result}")
            # Detect language and generate response
            lang_result = self._detect_language(message)
            result["detected_language"] = lang_result["language"]
            result["language_confidence"] = lang_result["confidence"]
            result["is_english"] = lang_result["english"]
            # Ensure message field present
            if "message" not in result or not result["message"]:
                result["message"] = self._get_fast_response(result.get("intent", "unknown"), lang_result["language"])
            return result
        
        # 3. Fallback
        return self._fallback_response(message)
    
    async def generate_response(self, intent: str, message: str, user_id: str = None) -> Dict[str, Any]:
        """Hybrid response generation - Fast path + LLM fallback"""
        
        # 1. Language detection with confidence
        lang_result = self._detect_language(message)
        detected_lang = lang_result["language"]
        confidence = lang_result["confidence"]
        
        # 2. Confidence check - High confidence (>0.8) -> Fast path
        if confidence > 0.8:
            fast_response = self._get_fast_response(intent, detected_lang)
            return {
                "intent": intent,
                "message": fast_response,
                "source": "fast_path",
                "language": detected_lang,
                "language_confidence": confidence,
                "latency_ms": 1
            }
        
        # 3. Low confidence (<0.8) -> LLM fallback
        try:
            llm_response = await self._llm_generate_response(intent, message, detected_lang, user_id)
            return {
                "intent": intent,
                "message": llm_response,
                "source": "llm_fallback",
                "language": detected_lang,
                "language_confidence": confidence,
                "latency_ms": 500
            }
        except Exception as e:
            print(f"⚠️ LLM fallback failed: {e}")
            # Fallback to fast path if LLM fails
            fast_response = self._get_fast_response(intent, detected_lang)
            return {
                "intent": intent,
                "message": fast_response,
                "source": "fast_path_fallback",
                "language": detected_lang,
                "language_confidence": confidence,
                "latency_ms": 2
            }
    
    def _get_fast_response(self, intent: str, language: str) -> str:
        """Get hardcoded response for fast path"""
        
        # Multi-language responses
        responses = {
            "greeting": {
                "en": "Hey! Ready to trade?",
                "hi": "नमस्ते! ट्रेडिंग शुरू करें?",
                "hi-en": "Hiii! Trading shuru kare?",
                "es": "¡Hola! ¿Listo para tradear?",
                "fr": "Salut! Prêt à trader?",
                "de": "Hallo! Bereit zu traden?",
                "ja": "こんにちは！トレード準備OK？"
            },
            "buy": {
                "en": "Processing your buy request...",
                "hi": "खरीदारी प्रोसेस हो रही है...",
                "hi-en": "Buy request process ho rahi hai...",
                "es": "Procesando tu orden de compra...",
                "fr": "Traitement de votre achat...",
                "de": "Verarbeite deinen Kauf...",
                "ja": "購入処理中..."
            },
            "sell": {
                "en": "Processing your sell request...",
                "hi": "बिक्री प्रोसेस हो रही है...",
                "hi-en": "Sell request process ho rahi hai...",
                "es": "Procesando tu orden de venta...",
                "fr": "Traitement de votre vente...",
                "de": "Verarbeite deinen Verkauf...",
                "ja": "売却処理中..."
            },
            "price": {
                "en": "Fetching live prices for you...",
                "hi": "लाइव प्राइस ला रहा हूँ...",
                "hi-en": "Live price la raha hoon...",
                "es": "Obteniendo precios en vivo...",
                "fr": "Récupération des prix en direct...",
                "de": "Hole aktuelle Preise...",
                "ja": "価格を取得中..."
            },
            "portfolio": {
                "en": "Sir, your portfolio is valued at $100,000, up 2.4%. You hold 100 ETH, 0.5 BTC, and 1000 SOL.",
                "hi": "सर, आपका पोर्टफोलियो $100,000 है, 2.4% बढ़ा। आपके पास 100 ETH, 0.5 BTC, और 1000 SOL हैं।",
                "hi-en": "Sir, aapka portfolio $100,000 hai, 2.4% up. Aapke paas 100 ETH, 0.5 BTC, aur 1000 SOL hain.",
                "es": "Señor, su cartera vale $100,000, sube 2.4%. Tiene 100 ETH, 0.5 BTC y 1000 SOL.",
                "fr": "Monsieur, votre portefeuille vaut $100,000, +2.4%. Vous détenez 100 ETH, 0.5 BTC et 1000 SOL.",
                "de": "Herr, Ihr Portfolio ist $100.000 wert, +2,4%. Sie halten 100 ETH, 0,5 BTC und 1000 SOL.",
                "ja": "ポートフォリオは$100,000、2.4%上昇。100 ETH、0.5 BTC、1000 SOLを保有。"
            },
            "advice": {
                "en": "Analyzing market conditions for your request...",
                "hi": "मार्केट एनालिसिस हो रहा है...",
                "hi-en": "Market analysis ho raha hai...",
                "es": "Analizando condiciones del mercado...",
                "fr": "Analyse des conditions du marché...",
                "de": "Marktbedingungen analysieren...",
                "ja": "市場分析中..."
            },
            "alert": {
                "en": "Setting up your alert...",
                "hi": "अलर्ट सेट हो रहा है...",
                "hi-en": "Alert set ho raha hai...",
                "es": "Configurando tu alerta...",
                "fr": "Configuration de votre alerte...",
                "de": "Richte deinen Alarm ein...",
                "ja": "アラート設定中..."
            },
            "stop_loss": {
                "en": "Configuring stop loss...",
                "hi": "स्टॉप लॉस कॉन्फिगर हो रहा है...",
                "hi-en": "Stop loss configure ho raha hai...",
                "es": "Configurando stop loss...",
                "fr": "Configuration du stop loss...",
                "de": "Konfiguriere Stop-Loss...",
                "ja": "損切り設定中..."
            },
            "take_profit": {
                "en": "Configuring take profit...",
                "hi": "टेक प्रॉफिट कॉन्फिगर हो रहा है...",
                "hi-en": "Take profit configure ho raha hai...",
                "es": "Configurando take profit...",
                "fr": "Configuration du take profit...",
                "de": "Konfiguriere Take-Profit...",
                "ja": "利確設定中..."
            }
        }
        
        # Get response for intent and language, fallback to English
        intent_responses = responses.get(intent, {})
        return intent_responses.get(language, intent_responses.get("en", "Processing complete, sir."))
    
    async def _llm_generate_response(self, intent: str, message: str, language: str, user_id: str = None) -> str:
        """Generate dynamic response using LLM"""
        
        from .simple_router import simple_chat
        
        # Build prompt for LLM
        lang_names = {
            "en": "English", "hi": "Hindi", "hi-en": "Hinglish",
            "es": "Spanish", "fr": "French", "de": "German", "ja": "Japanese"
        }
        
        lang_name = lang_names.get(language, "English")
        
        prompt = f"""You are a crypto trading assistant. Respond in {lang_name}.

User intent: {intent}
User message: {message}

Respond naturally in {lang_name} language. Keep it short and professional."""
        
        try:
            response = await simple_chat(prompt)
            return response.strip()
        except Exception as e:
            print(f"⚠️ LLM response generation failed: {e}")
            raise
    
    async def detect_intent_hybrid(self, message: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Hybrid intent detection - combines fast regex + LLM fallback"""
        return await self.classify(message)
    
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
