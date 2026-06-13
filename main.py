from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import uvicorn

# Override FastAPI's Contact to avoid conflicts
class Contact(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
import sys
import os
import time
import asyncio
import json
import random
import requests
from dotenv import load_dotenv

# Add packages to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'packages'))

from packages.ai.personality import personality_engine
from packages.ai.llm_client import generate_jarvis_response
from packages.ai.openrouter_client import call_openrouter
from packages.ai.mock_llm import generate_mock_response
from packages.ai.intent import IntentClassifier
from packages.ai.memory import get_memory, format_context_for_llm
from packages.ai.ghost_mode import get_ghost_mode
from packages.ai.proactive_alerts import get_alert_manager
from packages.ai.self_learning import get_learning_system
from packages.ai.auto_learning import get_auto_learning_system
from packages.ai.personalization import get_personalization_system
from packages.ai.llm_router import get_llm_router, REGEX_ONLY_INTENTS

# Language detection and self-learning imports
import sqlite3
from datetime import datetime, timedelta

# Groq API integration
import requests
import os
from dotenv import load_dotenv


async def call_groq_llm_async(messages, max_tokens=100):
    """Call GitHub Models API for LLM responses (async)"""
    try:
        load_dotenv('/home/siddhi/jarvix-repo/.env', override=True)
        api_key = os.getenv('GITHUB_TOKEN')
        if not api_key:
            print("[DEBUG] No GitHub token found")
            return None
        
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(None, lambda: requests.post(
            'https://models.inference.ai.azure.com/chat/completions',
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            },
            json={
                'model': 'Meta-Llama-3.1-8B-Instruct',
                'messages': messages,
                'max_tokens': max_tokens,
                'temperature': 0.7
            },
            timeout=10
        ))
        
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content'].strip()
        else:
            print(f"[DEBUG] API error: {response.status_code}")
            return None
    except Exception as e:
        print(f"[DEBUG] LLM error: {e}")
        return None

# Keep sync version for backward compatibility
def call_groq_llm(messages, max_tokens=100):
    """Call GitHub Models API for LLM responses (sync)"""
    try:
        # Load .env file explicitly with override
        load_dotenv('/home/siddhi/jarvix-repo/.env', override=True)
        # GitHub token from environment
        api_key = os.getenv('GITHUB_TOKEN')
        if not api_key:
            print("[DEBUG] No GitHub token found")
            return None
        
        response = requests.post(
            'https://models.inference.ai.azure.com/chat/completions',
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            },
            json={
                'model': 'Meta-Llama-3.1-8B-Instruct',
                'messages': messages,
                'max_tokens': max_tokens,
                'temperature': 0.7
            },
            timeout=10
        )
        
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            print(f"[DEBUG] GitHub Models API error: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"[DEBUG] LLM call error: {e}")
        return None
async def detect_language_with_llm_async(text):
    """Detect language using LLM (async)"""
    messages = [
        {'role': 'system', 'content': 'You are a language detection expert. Identify the language of the user text. Reply with ONLY the language code: en, hi, hinglish, es, fr, de, ja, zh, ar, ru, or other.'},
        {'role': 'user', 'content': f'What language is this: "{text}"? Reply with only the language code.'}
    ]
    result = await call_groq_llm_async(messages, max_tokens=10)
    if result:
        return result.strip().lower()
    return 'en'

# Keep sync version for backward compatibility
def detect_language_with_llm(text):
    """Detect language using LLM (sync)"""
    messages = [
        {'role': 'system', 'content': 'You are a language detection expert. Identify the language of the user text. Reply with ONLY the language code: en, hi, hinglish, es, fr, de, ja, zh, ar, ru, or other.'},
        {'role': 'user', 'content': f'What language is this: "{text}"? Reply with only the language code.'}
    ]
    result = call_groq_llm(messages, max_tokens=10)
    if result:
        return result.strip().lower()
    return 'en'

def generate_response_in_language(intent, user_message, portfolio_value='$311,342'):
    """Generate response in user's detected language using LLM"""
    detected_lang = detect_language_with_llm(user_message)
    
    messages = [
        {'role': 'system', 'content': f'You are Jarvix, a helpful AI crypto assistant. The user speaks {detected_lang}. Respond naturally in their language. Keep it concise and warm. Portfolio value: {portfolio_value}.'},
        {'role': 'user', 'content': f'User intent: {intent}. User message: "{user_message}". Generate a natural response.'}
    ]
    
    response = call_groq_llm(messages, max_tokens=150)
    if response:
        return response.strip()
    
    # Fallback to English
    return f"Sir, I understand. Your portfolio is at {portfolio_value}. How can I help?"

async def generate_response_in_language_async(intent, user_message, portfolio_value='$311,342'):
    """Async response generation using GitHub Models API"""
    detected_lang = await detect_language_with_llm_async(user_message)
    
    messages = [
        {'role': 'system', 'content': f'You are Jarvix, a helpful AI crypto assistant. The user speaks {detected_lang}. Respond naturally in their language. Keep it concise and warm. Portfolio value: {portfolio_value}.'},
        {'role': 'user', 'content': f'User intent: {intent}. User message: "{user_message}". Generate a natural response.'}
    ]
    
    response = await call_groq_llm_async(messages, max_tokens=150)
    if response:
        return response.strip()
    
    # Fallback to English
    return f"Sir, I understand. Your portfolio is at {portfolio_value}. How can I help?"

app = FastAPI()
LANGUAGE_KNOWLEDGE = {
    'en': {
        'name': 'English',
        'greetings': ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening'],
        'keywords': ['what', 'how', 'when', 'where', 'why', 'who', 'which', 'price', 'buy', 'sell', 'portfolio', 'advice', 'alert', 'help'],
        'common_phrases': ['thank you', 'please', 'sorry', 'excuse me', 'goodbye', 'see you'],
        'responses': {
            'greeting': 'Hello sir, how can I help you today?',
            'price': 'The price is {price}',
            'buy': 'Purchase order ready',
            'sell': 'Sale order ready',
            'portfolio': 'Your portfolio is at {portfolio_value}',
            'advice': 'My advice is to hold',
            'alert': 'Alert set successfully',
            'help': 'How can I assist you?'
        }
    },
    'hi': {
        'name': 'Hindi',
        'greetings': ['नमस्ते', 'हैलो', 'सुप्रभात', 'शुभ अपराह्न', 'शुभ संध्या'],
        'keywords': ['क्या', 'कैसे', 'कब', 'कहाँ', 'क्यों', 'कौन', 'कौनसा', 'कीमत', 'खरीद', 'बेच', 'पोर्टफोलियो', 'सलाह', 'अलर्ट', 'मदद'],
        'common_phrases': ['धन्यवाद', 'कृपया', 'माफ़ करना', 'अलविदा', 'फिर मिलेंगे'],
        'responses': {
            'greeting': 'नमस्ते सर, मैं कैसे मदद कर सकता हूँ?',
            'price': 'कीमत {price} है',
            'buy': 'खरीद का आदेश तैयार',
            'sell': 'बिक्री का आदेश तैयार',
            'portfolio': 'आपका पोर्टफोलियो {portfolio_value} पर है',
            'advice': 'मेरी सलाह है होल्ड करें',
            'alert': 'अलर्ट सेट हो गया',
            'help': 'मैं कैसे मदद कर सकता हूँ?'
        }
    },
    'hinglish': {
        'name': 'Hinglish',
        'greetings': ['namaste', 'hello', 'hi', 'good morning', 'good afternoon', 'good evening', 'kaise ho', 'kya haal hai'],
        'keywords': ['kya', 'kaise', 'kab', 'kahan', 'kyu', 'kaun', 'kaunsa', 'price', 'buy', 'sell', 'portfolio', 'advice', 'alert', 'help', 'batao', 'dekhna', 'karu', 'chahiye'],
        'common_phrases': ['thank you', 'please', 'sorry', 'bye', 'see you', 'dhanyawad', 'kripya', 'maaf karna'],
        'responses': {
            'greeting': 'Hello sir, kaise ho?',
            'price': 'Price {price} hai',
            'buy': 'Buy order ready hai',
            'sell': 'Sell order ready hai',
            'portfolio': 'Portfolio {portfolio_value} pe hai',
            'advice': 'Advice hai hold karo',
            'alert': 'Alert set ho gaya',
            'help': 'Kya help chahiye?'
        }
    },
    'es': {
        'name': 'Spanish',
        'greetings': ['hola', 'buenos días', 'buenas tardes', 'buenas noches', 'qué tal'],
        'keywords': ['qué', 'cómo', 'cuándo', 'dónde', 'por qué', 'quién', 'cuál', 'precio', 'comprar', 'vender', 'cartera', 'consejo', 'alerta', 'ayuda'],
        'common_phrases': ['gracias', 'por favor', 'lo siento', 'adiós', 'hasta luego'],
        'responses': {
            'greeting': 'Hola señor, ¿cómo puedo ayudarle?',
            'price': 'El precio es {price}',
            'buy': 'Orden de compra lista',
            'sell': 'Orden de venta lista',
            'portfolio': 'Su cartera está en {portfolio_value}',
            'advice': 'Mi consejo es mantener',
            'alert': 'Alerta configurada',
            'help': '¿Cómo puedo ayudarle?'
        }
    },
    'fr': {
        'name': 'French',
        'greetings': ['bonjour', 'salut', 'bonsoir', 'bonne journée', 'bonne soirée'],
        'keywords': ['quoi', 'comment', 'quand', 'où', 'pourquoi', 'qui', 'quel', 'prix', 'acheter', 'vendre', 'portefeuille', 'conseil', 'alerte', 'aide'],
        'common_phrases': ['merci', 's\'il vous plaît', 'pardon', 'au revoir', 'à bientôt'],
        'responses': {
            'greeting': 'Bonjour monsieur, comment puis-je vous aider?',
            'price': 'Le prix est {price}',
            'buy': 'Ordre d\'achat prêt',
            'sell': 'Ordre de vente prêt',
            'portfolio': 'Votre portefeuille est à {portfolio_value}',
            'advice': 'Mon conseil est de garder',
            'alert': 'Alerte configurée',
            'help': 'Comment puis-je vous aider?'
        }
    },
    'de': {
        'name': 'German',
        'greetings': ['hallo', 'guten morgen', 'guten tag', 'guten abend', 'wie geht\'s'],
        'keywords': ['was', 'wie', 'wann', 'wo', 'warum', 'wer', 'welcher', 'preis', 'kaufen', 'verkaufen', 'portfolio', 'rat', 'alarm', 'hilfe'],
        'common_phrases': ['danke', 'bitte', 'entschuldigung', 'tschüss', 'bis bald'],
        'responses': {
            'greeting': 'Hallo Herr, wie kann ich Ihnen helfen?',
            'price': 'Der Preis ist {price}',
            'buy': 'Kaufauftrag bereit',
            'sell': 'Verkaufsauftrag bereit',
            'portfolio': 'Ihr Portfolio ist bei {portfolio_value}',
            'advice': 'Mein Rat ist zu halten',
            'alert': 'Alarm eingestellt',
            'help': 'Wie kann ich Ihnen helfen?'
        }
    },
    'ja': {
        'name': 'Japanese',
        'greetings': ['こんにちは', 'おはよう', 'こんばんは', 'さようなら', 'お元気ですか'],
        'keywords': ['何', 'どう', 'いつ', 'どこ', 'なぜ', '誰', 'どの', '価格', '買う', '売る', 'ポートフォリオ', 'アドバイス', 'アラート', 'ヘルプ'],
        'common_phrases': ['ありがとう', 'お願いします', 'ごめんなさい', 'さようなら', 'またね'],
        'responses': {
            'greeting': 'こんにちは、お手伝いできますか？',
            'price': '価格は{price}です',
            'buy': '購入注文の準備完了',
            'sell': '売却注文の準備完了',
            'portfolio': 'ポートフォリオは{portfolio_value}です',
            'advice': 'アドバイスはホールドです',
            'alert': 'アラート設定完了',
            'help': 'お手伝いできますか？'
        }
    },
    'zh': {
        'name': 'Chinese',
        'greetings': ['你好', '早上好', '下午好', '晚上好', '再见'],
        'keywords': ['什么', '怎么', '什么时候', '哪里', '为什么', '谁', '哪个', '价格', '买', '卖', '投资组合', '建议', '提醒', '帮助'],
        'common_phrases': ['谢谢', '请', '对不起', '再见', '回头见'],
        'responses': {
            'greeting': '你好先生，有什么可以帮您？',
            'price': '价格是{price}',
            'buy': '购买订单已准备好',
            'sell': '出售订单已准备好',
            'portfolio': '您的投资组合在{portfolio_value}',
            'advice': '建议是持有',
            'alert': '提醒已设置',
            'help': '有什么可以帮您？'
        }
    },
    'ar': {
        'name': 'Arabic',
        'greetings': ['مرحبا', 'صباح الخير', 'مساء الخير', 'تصبح على خير', 'كيف حالك'],
        'keywords': ['ماذا', 'كيف', 'متى', 'أين', 'لماذا', 'من', 'أي', 'سعر', 'شراء', 'بيع', 'محفظة', 'نصيحة', 'تنبيه', 'مساعدة'],
        'common_phrases': ['شكرا', 'من فضلك', 'آسف', 'وداعا', 'إلى اللقاء'],
        'responses': {
            'greeting': 'مرحبا سيدي، كيف يمكنني مساعدتك؟',
            'price': 'السعر هو {price}',
            'buy': 'أمر الشراء جاهز',
            'sell': 'أمر البيع جاهز',
            'portfolio': 'محفظتك في {portfolio_value}',
            'advice': 'نصيحتي هي الاحتفاظ',
            'alert': 'تم تعيين التنبيه',
            'help': 'كيف يمكنني مساعدتك؟'
        }
    },
    'ru': {
        'name': 'Russian',
        'greetings': ['привет', 'доброе утро', 'добрый день', 'добрый вечер', 'как дела'],
        'keywords': ['что', 'как', 'когда', 'где', 'почему', 'кто', 'какой', 'цена', 'купить', 'продать', 'портфель', 'совет', 'оповещение', 'помощь'],
        'common_phrases': ['спасибо', 'пожалуйста', 'извините', 'до свидания', 'до встречи'],
        'responses': {
            'greeting': 'Здравствуйте, чем могу помочь?',
            'price': 'Цена {price}',
            'buy': 'Ордер на покупку готов',
            'sell': 'Ордер на продажу готов',
            'portfolio': 'Ваш портфель на {portfolio_value}',
            'advice': 'Мой совет держать',
            'alert': 'Оповещение установлено',
            'help': 'Чем могу помочь?'
        }
    }
}

# Supported languages list
SUPPORTED_LANGUAGES = list(LANGUAGE_KNOWLEDGE.keys())

def detect_language_advanced(text):
    """Advanced language detection with keyword matching"""
    text_lower = text.lower().strip()
    words = set(text_lower.split())
    
    # Check each language's keywords
    language_scores = {}
    for lang_code, lang_data in LANGUAGE_KNOWLEDGE.items():
        score = 0
        
        # Check greetings
        for greeting in lang_data['greetings']:
            if greeting in text_lower:
                score += 10
        
        # Check keywords
        for keyword in lang_data['keywords']:
            if keyword in words:
                score += 5
        
        # Check common phrases
        for phrase in lang_data['common_phrases']:
            if phrase in text_lower:
                score += 8
        
        language_scores[lang_code] = score
    
    # Return language with highest score, or English if no match
    if language_scores:
        best_lang = max(language_scores, key=language_scores.get)
        if language_scores[best_lang] > 0:
            return best_lang
    
    # Fallback to basic detection
    return detect_language(text)

def get_language_response(intent, lang_code, **kwargs):
    """Get response in user's detected language"""
    lang_data = LANGUAGE_KNOWLEDGE.get(lang_code, LANGUAGE_KNOWLEDGE['en'])
    response_template = lang_data['responses'].get(intent, 'Hello sir, how can I help?')
    
    # Format with variables
    try:
        return response_template.format(**kwargs)
    except KeyError:
        return response_template

def is_language_supported(lang_code):
    """Check if language is supported"""
    return lang_code in SUPPORTED_LANGUAGES

def get_all_language_names():
    """Get all supported language names"""
    return {code: data['name'] for code, data in LANGUAGE_KNOWLEDGE.items()}

# Language detection functions (keep existing ones)
def detect_language(text):
    """Detect language from user text"""
    text_lower = text.lower()
    
    # Hinglish detection (Romanized Hindi)
    hinglish_keywords = {'hai', 'kya', 'kaise', 'namaste', 'kar', 'raha', 'tum', 'mera', 'bhai', 'aap', 'kyu', 'nahi', 'thik', 'ho', 'ka', 'ke', 'ki', 'ko', 'se', 'mein', 'pe', 'hoon', 'rahi', 'raha', 'karu', 'dekhna', 'chahiye', 'batao', 'bolo', 'bataiye', 'karo', 'jaao', 'aao', 'dekho', 'sunno', 'samajh', 'liya', 'gaya', 'hui', 'hue', 'hain', 'hun', 'hoga', 'hogi', 'honge', 'hongi', 'tha', 'thi', 'the', 'thi', 'karunga', 'karungi', 'karega', 'karegi', 'karenge', 'karegi', 'raha', 'rahi', 'rahe', 'rahi', 'sakta', 'sakti', 'sakte', 'sakti', 'chahiye', 'chahiye', 'chahiye', 'chahiye'}
    
    words = set(text_lower.split())
    overlap = words & hinglish_keywords
    
    if len(overlap) / max(len(words), 1) > 0.2:
        return 'hinglish'
    
    # Pure Hindi detection (Devanagari script)
    hindi_chars = set('अआइईउऊऋएऐओऔंःकखगघङचछजझञटठडढणतथदधनपफबभमयरलवशषसहञ़ािीुूेोैौंः')
    text_chars = set(text_lower)
    if len(text_chars & hindi_chars) > 2:
        return 'hi'
    
    # Default to English
    return 'en'

def update_user_language(user_id, language_code, message_length=1):
    """Update user language preference in database with weighted confidence"""
    try:
        conn = sqlite3.connect('jarvix.db')
        cursor = conn.cursor()
        
        # Weight short messages lower (≤2 words = 0.3x, 3-5 words = 0.7x, 6+ words = 1.0x)
        if message_length <= 2:
            weight = 0.3
        elif message_length <= 5:
            weight = 0.7
        else:
            weight = 1.0
        
        # Check if entry exists
        cursor.execute("SELECT confidence_score, message_count FROM user_languages WHERE user_id=? AND language_code=?", 
                      (user_id, language_code))
        result = cursor.fetchone()
        
        if result:
            # Update existing entry
            confidence_score, message_count = result
            # Add weighted confidence (10-15 base * weight)
            base_increase = 15 if message_length > 2 else 10
            new_confidence = min(confidence_score + (base_increase * weight), 100)
            new_count = message_count + 1
            cursor.execute("UPDATE user_languages SET confidence_score=?, message_count=?, last_used=? WHERE user_id=? AND language_code=?",
                          (new_confidence, new_count, datetime.now(), user_id, language_code))
        else:
            # Create new entry with lower starting confidence for short messages
            start_confidence = 20 * weight
            cursor.execute("INSERT INTO user_languages (user_id, language_code, confidence_score, message_count, last_used) VALUES (?, ?, ?, ?, ?)",
                          (user_id, language_code, start_confidence, 1, datetime.now()))
        
        # Update primary language
        cursor.execute("SELECT language_code FROM user_languages WHERE user_id=? ORDER BY confidence_score DESC LIMIT 1", (user_id,))
        primary = cursor.fetchone()
        if primary:
            cursor.execute("INSERT OR REPLACE INTO user_profile (user_id, primary_language, last_updated) VALUES (?, ?, ?)",
                          (user_id, primary[0], datetime.now()))
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[DEBUG] Language update error: {e}")

def apply_language_decay(user_id):
    """Apply confidence decay for unused languages (-1 per week)"""
    try:
        conn = sqlite3.connect('jarvix.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT language_code, confidence_score, last_used FROM user_languages WHERE user_id=?", (user_id,))
        results = cursor.fetchall()
        
        for lang_code, confidence, last_used in results:
            if last_used:
                last_date = datetime.fromisoformat(last_used.replace('Z', '+00:00'))
                weeks_inactive = (datetime.now() - last_date).days // 7
                if weeks_inactive > 0:
                    decay = weeks_inactive * 1  # -1 per week
                    new_confidence = max(confidence - decay, 0)
                    cursor.execute("UPDATE user_languages SET confidence_score=? WHERE user_id=? AND language_code=?",
                                  (new_confidence, user_id, lang_code))
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[DEBUG] Language decay error: {e}")

def get_known_languages(user_id, min_confidence=30):
    """Get list of languages user knows with confidence above threshold"""
    try:
        conn = sqlite3.connect('jarvix.db')
        cursor = conn.cursor()
        cursor.execute("SELECT language_code FROM user_languages WHERE user_id=? AND confidence_score >= ?",
                      (user_id, min_confidence))
        result = [row[0] for row in cursor.fetchall()]
        conn.close()
        return result if result else ['en']
    except Exception as e:
        print(f"[DEBUG] Get languages error: {e}")
        return ['en']

app = FastAPI()

# CORS Middleware - dynamic from env var + default deployed origin
cors_origins = os.getenv("CORS_ORIGINS", "")
if cors_origins:
    allow_origins = [origin.strip() for origin in cors_origins.split(",")]
else:
    allow_origins = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3003",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3003",
        "https://jarvix-48y1.onrender.com",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── API Models ───

from typing import Optional, Dict, Any, List

class ChatRequest(BaseModel):
    message: str
    user_id: str = "default"

class ChatResponse(BaseModel):
    intent: str
    confidence: float
    fast_path: bool
    source: str
    entities: Dict
    message: str
    latency_ms: int

class Holding(BaseModel):
    asset: str
    amount: float
    value: float
    change_pct: float

from typing import Optional, Dict, Any, List

class PortfolioResponse(BaseModel):
    total_value: float
    change_pct: float
    holdings: List[Holding]

class HealthResponse(BaseModel):
    neural_engine: int
    intent_router: int
    memory_cache: int
    commands_total: int
    pass_rate: float
    redis_status: str
    learning_db: str
    accuracy_score: str
    total_corrections: int
    auto_learn_patterns: int
    personalization_profiles: int
    uptime_seconds: int

# ─── Demo Data ───

DEMO_PORTFOLIO = PortfolioResponse(
    total_value=100000.00,
    change_pct=2.4,
    holdings=[
        Holding(asset="BTC", amount=0.5, value=36542.50, change_pct=0.29),
        Holding(asset="ETH", amount=100, value=199795.0, change_pct=1.08),
        Holding(asset="SOL", amount=500, value=76200.0, change_pct=-0.5),
    ]
)

DEMO_PRICES = {
    "BTC": 73085.0,
    "ETH": 1997.95,
    "SOL": 152.40,
}

SERVER_START = time.time()

# ─── API Endpoints ───

@app.get("/api/portfolio", response_model=PortfolioResponse)
async def get_portfolio():
    """Returns portfolio data (demo for now)"""
    return DEMO_PORTFOLIO

@app.get("/api/health", response_model=HealthResponse)
async def get_health():
    """Returns system health + self-learning stats"""
    uptime = int(time.time() - SERVER_START)
    
    return HealthResponse(
        neural_engine=78,
        intent_router=45,
        memory_cache=62,
        commands_total=284,
        pass_rate=100.0,
        redis_status="CONNECTED",
        learning_db="ACTIVE",
        accuracy_score="275/275",
        total_corrections=35,
        auto_learn_patterns=367,
        personalization_profiles=12,
        uptime_seconds=uptime,
    )

@app.post("/api/ai/chat", response_model=ChatResponse)
async def post_chat(request: ChatRequest):
    """Main command handler — calls intent detection"""
    start = time.time()
    
    try:
        # Use existing intent detection
        from packages.ai.intent import IntentClassifier
        classifier = IntentClassifier()
        result = classifier.classify(request.message)
        
        latency_ms = int((time.time() - start) * 1000)
        
        # Generate real-time price message for price intents
        intent = result.get("intent", "UNKNOWN")
        asset = result.get("asset") or result.get("entities", {}).get("asset")
        amount = result.get("amount") or result.get("entities", {}).get("amount")
        
        # Also check if asset is in entities dict for backward compatibility
        if not asset and "entities" in result:
            asset = result["entities"].get("asset")
        if not amount and "entities" in result:
            amount = result["entities"].get("amount")
        
        # Ensure entities dict includes asset for response
        entities = result.get("entities", {})
        if asset and "asset" not in entities:
            entities["asset"] = asset
        if amount and "amount" not in entities:
            entities["amount"] = amount
        
        # Debug: print what we got
        print(f"[DEBUG] intent={intent}, asset={asset}, result={result}")
        
        # Fast path for unknown intents - use OpenAI for general knowledge
        if intent == "unknown":
            try:
                import openai
                import os
                from dotenv import load_dotenv
                load_dotenv()
                api_key = os.environ.get("OPENAI_API_KEY")
                if api_key:
                    client = openai.OpenAI(api_key=api_key)
                    resp = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": "You are Jarvix, a helpful AI assistant. You can answer any question - crypto, news, daily life, general knowledge, etc. Always be concise and helpful."},
                            {"role": "user", "content": request.message}
                        ],
                        max_tokens=150,
                        timeout=10
                    )
                    ai_msg = resp.choices[0].message.content
                    return ChatResponse(
                        intent=intent,
                        confidence=0.9,
                        fast_path=True,
                        source="openai",
                        entities=entities,
                        message=ai_msg,
                        latency_ms=latency_ms,
                    )
            except Exception as e:
                print(f"[DEBUG] OpenAI error: {e}")
            
            # Fallback if OpenAI fails
            return ChatResponse(
                intent=intent,
                confidence=result.get("confidence", 0.0),
                fast_path=True,
                source="llm",
                entities=entities,
                message="Sir, I understand. Your portfolio is at $311,342. How can I help?",
                latency_ms=latency_ms,
            )
        
        # Language detection using LLM for ALL intents
        detected_lang = await detect_language_with_llm_async(request.message)
        message_length = len(request.message.split())
        update_user_language(request.user_id, detected_lang, message_length)
        apply_language_decay(request.user_id)
        known_langs = get_known_languages(request.user_id, min_confidence=30)
        
        # Check if user knows non-English languages
        knows_hinglish = 'hinglish' in known_langs or 'hi' in known_langs
        portfolio_value = "$311,342"  # TODO: Replace with real portfolio service call
        
        # Try LLM-based response generation first for ALL intents
        llm_response = await generate_response_in_language_async(intent, request.message, portfolio_value)
        if llm_response and llm_response != f"Sir, I understand. Your portfolio is at {portfolio_value}. How can I help?":
            message = llm_response
        else:
            # Fallback to pre-written responses
            if intent == "price" and asset:
                prices = get_live_prices()
                asset_upper = asset.upper()
                if asset_upper in prices:
                    p = prices[asset_upper]
                    change_emoji = "📈" if p['change'] >= 0 else "📉"
                    change_sign = "+" if p['change'] >= 0 else ""
                    if knows_hinglish:
                        message = f"Sir, {asset_upper} ka price ${p['price']:,} hai. {change_emoji} {change_sign}{p['change']:.2f}% 24h mein. Portfolio {portfolio_value} pe robust hai."
                    else:
                        message = f"Sir, {asset_upper} is trading at ${p['price']:,}. {change_emoji} {change_sign}{p['change']:.2f}% in 24h. Your portfolio remains robust at $311,342."
                else:
                    if knows_hinglish:
                        message = f"Sir, {asset_upper} ka price data nahi hai. Portfolio {portfolio_value} pe robust hai."
                    else:
                        message = f"Sir, {asset_upper} price data not available. Your portfolio remains robust at $311,342."
            elif intent == "price":
                prices = get_live_prices()
                btc = prices.get('BTC', {}).get('price', 62000)
                message = f"Sir, BTC is at ${btc:,}. Which asset would you like the price for? Your portfolio remains robust at $311,342."
            elif intent == "buy":
                if asset and amount:
                    prices = get_live_prices()
                    asset_upper = asset.upper()
                    current_price = prices.get(asset_upper, {}).get('price', 0)
                    total = amount * current_price
                    message = f"Sir, purchase order prepared for {amount} {asset_upper} at ${current_price:,} (total: ${total:,}). Shall I execute? Your portfolio remains robust at $311,342."
                elif asset:
                    prices = get_live_prices()
                    asset_upper = asset.upper()
                    current_price = prices.get(asset_upper, {}).get('price', 0)
                    message = f"Sir, purchase order ready for {asset_upper} at ${current_price:,}. Please specify the amount. Your portfolio remains robust at $311,342."
                else:
                    message = f"Sir, I understand you wish to buy. Please specify the asset and amount. Your portfolio remains robust at $311,342."
            elif intent == "sell":
                if asset and amount:
                    prices = get_live_prices()
                    asset_upper = asset.upper()
                    current_price = prices.get(asset_upper, {}).get('price', 0)
                    total = amount * current_price
                    message = f"Sir, sell order prepared for {amount} {asset_upper} at ${current_price:,} (total: ${total:,}). Shall I execute? Your portfolio remains robust at $311,342."
                elif asset:
                    prices = get_live_prices()
                    asset_upper = asset.upper()
                    current_price = prices.get(asset_upper, {}).get('price', 0)
                    message = f"Sir, sell order ready for {asset_upper} at ${current_price:,}. Please specify the amount. Your portfolio remains robust at $311,342."
                else:
                    message = f"Sir, I understand you wish to sell. Please specify the asset and amount. Your portfolio remains robust at $311,342."
            elif intent == "portfolio":
                message = f"Sir, your portfolio is valued at $311,342. Top holdings: BTC 40%, ETH 30%, SOL 20%, USDC 10%. All positions healthy."
            elif intent == "advice":
                prices = get_live_prices()
                if asset:
                    asset_upper = asset.upper()
                    p = prices.get(asset_upper, {})
                    price = p.get('price', 0)
                    change = p.get('change', 0)
                    change_emoji = "📈" if change >= 0 else "📉"
                    change_sign = "+" if change >= 0 else ""
                    if knows_hinglish:
                        message = f"Sir, {asset_upper} ka price ${price:,} hai. {change_emoji} {change_sign}{change:.2f}% 24h mein. Portfolio {portfolio_value} pe robust hai."
                    else:
                        message = f"Sir, {asset_upper} is trading at ${price:,}. {change_emoji} {change_sign}{change:.2f}% in 24h. Your portfolio remains robust at $311,342."
                else:
                    message = f"Sir, here are the top movers: BTC {prices.get('BTC', {}).get('change', 0):.2f}%, ETH {prices.get('ETH', {}).get('change', 0):.2f}%, SOL {prices.get('SOL', {}).get('change', 0):.2f}%. Your portfolio remains robust at $311,342."
            elif intent == "alert":
                if asset:
                    asset_upper = asset.upper()
                    message = f"Sir, alert set for {asset_upper}. I'll notify you when significant price movements occur. Your portfolio remains robust at $311,342."
                else:
                    message = f"Sir, alert configured. I'll monitor the market and notify you of significant movements. Your portfolio remains robust at $311,342."
            elif intent == "emotional":
                message = f"Sir, I understand this can be stressful. Your portfolio is at $311,342. Would you like me to show you some calming market insights or shall we review your positions?"
            elif intent == "unknown":
                message = f"Sir, I'm not sure I understood that correctly. Could you please rephrase? Your portfolio remains robust at $311,342."
            else:
                message = f"Sir, I understand. Your portfolio is at {portfolio_value}. How can I help?"
        
        if intent == "greeting":
            from datetime import datetime
            import random
            hour = datetime.now().hour
            
            # Detect language using LLM for ALL intents
            detected_lang = detect_language_with_llm(request.message)
            message_length = len(request.message.split())
            update_user_language(request.user_id, detected_lang, message_length)
            
            # Apply decay for unused languages
            apply_language_decay(request.user_id)
            
            # Get known languages for user with confidence tiers
            known_langs = get_known_languages(request.user_id, min_confidence=30)
            
            # Get portfolio value dynamically
            portfolio_value = "$311,342"  # TODO: Replace with real portfolio service call
            
            # Try LLM-based response generation first
            llm_response = generate_response_in_language(intent, request.message, portfolio_value)
            if llm_response and llm_response != f"Sir, I understand. Your portfolio is at {portfolio_value}. How can I help?":
                message = llm_response
            else:
                # Fallback to pre-written pools
                if 5 <= hour < 12:
                    # Afternoon - professional, business-as-usual
                    messages_english = [
                        f"Good afternoon, sir. Jarvix at your service. Portfolio is at {portfolio_value}.",
                        f"Afternoon, sir. Everything's steady — portfolio at {portfolio_value}.",
                        f"Good afternoon, sir. Portfolio holding at {portfolio_value}. Any updates needed?",
                        f"Sir, halfway through the day — portfolio's at {portfolio_value}.",
                        f"Good afternoon! Portfolio stable at {portfolio_value}, sir.",
                        f"Afternoon, sir. How's the day going? Portfolio at {portfolio_value}.",
                        f"Good afternoon, sir. Quick check — portfolio's at {portfolio_value}.",
                        f"Sir, hope lunch went well. Portfolio at {portfolio_value}.",
                        f"Good afternoon! All systems normal, sir. Portfolio at {portfolio_value}.",
                        f"Afternoon, sir. Portfolio steady at {portfolio_value}. What's next?"
                    ]
                    messages_hinglish = [
                        f"Good afternoon sir, Jarvix ready hai. Portfolio {portfolio_value} pe hai.",
                        f"Sir, lunch ho gaya? Portfolio {portfolio_value} pe steady hai.",
                        f"Good afternoon sir, sab kuch normal hai. Portfolio {portfolio_value}.",
                        f"Sir, din ka half ho gaya. Portfolio {portfolio_value} pe hai.",
                        f"Good afternoon! Portfolio {portfolio_value} pe stable, sab theek hai.",
                        f"Sir, energy thodi low? Portfolio {portfolio_value} pe hai, koi update?",
                        f"Good afternoon sir, kaam kaisa chal raha hai? Portfolio {portfolio_value}.",
                        f"Sir, afternoon break ka time? Portfolio {portfolio_value} pe hai.",
                        f"Good afternoon! Sab smooth chal raha hai sir, portfolio {portfolio_value}.",
                        f"Sir, half day done — portfolio {portfolio_value} pe stable hai."
                    ]
                elif 17 <= hour < 22:
                    # Evening - relaxed, winding-down
                    messages_english = [
                        f"Good evening, sir. How was your day? Portfolio's at {portfolio_value}.",
                        f"Evening, sir. Portfolio currently at {portfolio_value}. Anything to review?",
                        f"Good evening! Day's winding down — portfolio at {portfolio_value}.",
                        f"Sir, hope today went smoothly. Portfolio's at {portfolio_value}.",
                        f"Good evening, sir. Time to relax? Portfolio at {portfolio_value}.",
                        f"Evening, sir. Portfolio holding steady at {portfolio_value}.",
                        f"Good evening! Let's do a quick check — portfolio's at {portfolio_value}.",
                        f"Sir, productive day? Portfolio currently at {portfolio_value}.",
                        f"Good evening, sir. Portfolio at {portfolio_value} — any plans for tonight?",
                        f"Evening, sir. Wrapping up the day — portfolio's at {portfolio_value}."
                    ]
                    messages_hinglish = [
                        f"Good evening sir, din kaisa raha? Portfolio {portfolio_value} pe hai.",
                        f"Sir, evening ho gayi. Portfolio {portfolio_value}. Kuch check karna hai?",
                        f"Good evening! Portfolio {portfolio_value} pe hai, din wrap up ho raha hai.",
                        f"Sir, kaam khatam hone wala hai? Portfolio {portfolio_value} pe stable.",
                        f"Good evening sir, relax mode on? Portfolio {portfolio_value} pe hai.",
                        f"Sir, shaam ho gayi — portfolio {portfolio_value} pe khada hai.",
                        f"Good evening! Sab settle ho raha hai, portfolio {portfolio_value}.",
                        f"Sir, din productive raha? Portfolio {portfolio_value} pe hai abhi.",
                        f"Good evening sir, ek baar portfolio check kar lete hain — {portfolio_value}.",
                        f"Sir, sham ka time — portfolio {portfolio_value}, kuch plan karna hai?"
                    ]
                else:
                    # Late night - caring, slightly concerned
                    messages_english = [
                        f"You're up late, sir. Just so you know, your portfolio is at {portfolio_value}. Anything urgent, or should this wait till morning?",
                        f"Late night session, sir? Your portfolio is at {portfolio_value}. Markets are quieter now — what's on your mind?",
                        f"Sir, it's quite late. Your portfolio stands at {portfolio_value}. Is this urgent, or can we tackle it fresh tomorrow?",
                        f"Still up, sir? Portfolio's at {portfolio_value}. Anything urgent?",
                        f"It's pretty late, sir. Portfolio's at {portfolio_value} — all good?",
                        f"Burning the midnight oil, sir? Portfolio at {portfolio_value}.",
                        f"Sir, Jarvix is here even at this hour. Portfolio's at {portfolio_value}.",
                        f"Sir, maybe this can wait — portfolio's at {portfolio_value} for now.",
                        f"Night mode active, sir. Portfolio at {portfolio_value}. How can I help?",
                        f"Sir, the night is deep — portfolio's steady at {portfolio_value}."
                    ]
                    messages_hinglish = [
                        f"Sir, raat ho gayi hai. Portfolio {portfolio_value}. Koi urgent kaam hai?",
                        f"Itni raat ko bhi active ho sir? Portfolio {portfolio_value} pe hai abhi.",
                        f"Sir, neend nahi aa rahi kya? Portfolio {portfolio_value} pe hai.",
                        f"Late night ho gaya sir — portfolio {portfolio_value}, sab theek hai?",
                        f"Sir, kaafi raat ho gayi. Portfolio {portfolio_value} pe stable hai.",
                        f"Sir, abhi tak awake? Portfolio {portfolio_value} — kuch zaroori hai?",
                        f"Itni raat ko Jarvix hazir hai sir. Portfolio {portfolio_value} pe hai.",
                        f"Sir, kal subah dekh lete? Abhi portfolio {portfolio_value} pe hai.",
                        f"Sir, night mode on hai. Portfolio {portfolio_value}, kya help chahiye?",
                        f"Sir, raat gehri hai — portfolio {portfolio_value} pe khada hai abhi."
                    ]
                
                # Select messages based on known languages
                if 'hinglish' in known_langs or 'hi' in known_langs:
                    # User knows Hindi/Hinglish - use mixed pool
                    messages = messages_english + messages_hinglish
                else:
                    # User only knows English - use English only
                    messages = messages_english
                
                message = random.choice(messages)
        elif intent == "advice":
            prices = get_live_prices()
            if asset:
                asset_upper = asset.upper()
                if asset_upper in prices:
                    p = prices[asset_upper]
                    change_emoji = "📈" if p['change'] >= 0 else "📉"
                    change_sign = "+" if p['change'] >= 0 else ""
                    trend = "bullish" if p['change'] >= 0 else "bearish"
                    message = f"Sir, {asset_upper} is at ${p['price']:,} ({change_sign}{p['change']:.2f}%). Market sentiment is {trend}. Based on current momentum, {asset_upper} shows {trend} signals. Your portfolio remains robust at $311,342. Shall I set an alert for significant moves?"
                else:
                    message = f"Sir, I cannot access real-time data for {asset} at the moment. Based on recent market analysis, consider dollar-cost averaging. Your portfolio is at $311,342."
            else:
                btc = prices.get('BTC', {}).get('price', 61186)
                eth = prices.get('ETH', {}).get('price', 1619)
                message = f"Sir, BTC is at ${btc:,} and ETH at ${eth:,}. Both showing mixed signals. Consider your risk tolerance before entering. Portfolio at $311,342. Which asset interests you?"
        elif intent == "alert":
            prices = get_live_prices()
            if asset:
                asset_upper = asset.upper()
                current_price = prices.get(asset_upper, {}).get('price', 0)
                message = f"Sir, alert set for {asset_upper}. Current price: ${current_price:,}. I shall notify you when the target is reached. Your portfolio remains robust at $311,342."
            else:
                btc = prices.get('BTC', {}).get('price', 61186)
                message = f"Sir, alert configured. BTC is currently at ${btc:,}. I shall notify you when conditions are met. Your portfolio remains robust at $311,342."
        elif intent == "emotional":
            message = f"Sir, I sense your emotions. Markets fluctuate, but your portfolio at $311,342 remains stable. Take a deep breath. How may I assist?"
        else:
            message = f"Sir, I understand. Your portfolio is at $311,342. How can I help?"
        
        return ChatResponse(
            intent=intent,
            confidence=result.get("confidence", 0.0),
            fast_path=True,
            source="llm",
            entities=entities,
            message=message,
            latency_ms=latency_ms,
        )
    except Exception as e:
        latency_ms = int((time.time() - start) * 1000)
        return ChatResponse(
            intent="ERROR",
            confidence=0.0,
            fast_path=False,
            source="error",
            entities={},
            message=f"Error: {str(e)}",
            latency_ms=latency_ms,
        )

@app.websocket("/ws/prices")
async def ws_prices(websocket: WebSocket):
    """Streams live prices every 10 seconds"""
    await websocket.accept()
    
    try:
        while True:
            prices = get_live_prices()
            await websocket.send_json({
                "BTC": prices.get('BTC', {}).get('price', 62000),
                "ETH": prices.get('ETH', {}).get('price', 1600),
                "SOL": prices.get('SOL', {}).get('price', 65),
                "timestamp": time.time()
            })
            await asyncio.sleep(10)
    except WebSocketDisconnect:
        pass

# Cache for prices
price_cache = {}
price_cache_time = 0
PRICE_CACHE_TTL = 30  # 30 seconds

def get_live_prices():
    """Fetch real-time prices from CoinGecko"""
    global price_cache, price_cache_time
    
    now = time.time()
    if now - price_cache_time < PRICE_CACHE_TTL and price_cache:
        return price_cache
    
    try:
        res = requests.get(
            'https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana&vs_currencies=usd&include_24hr_change=true',
            headers={'Accept': 'application/json', 'User-Agent': 'Jarvix/1.0', 'x-cg-demo-api-key': 'CG-demo'},
            timeout=10
        )
        data = res.json()
        price_cache = {
            'BTC': {'price': data['bitcoin']['usd'], 'change': data['bitcoin'].get('usd_24h_change', 0)},
            'ETH': {'price': data['ethereum']['usd'], 'change': data['ethereum'].get('usd_24h_change', 0)},
            'SOL': {'price': data['solana']['usd'], 'change': data['solana'].get('usd_24h_change', 0)},
        }
        price_cache_time = now
        return price_cache
    except Exception as e:
        print(f"[PRICE ERROR] {e}")
        # Fallback to cached or default
        return price_cache or {
            'BTC': {'price': 61186, 'change': -2.3},
            'ETH': {'price': 1619, 'change': -2.9},
            'SOL': {'price': 63.43, 'change': -4.1},
        }

# Template responses for simple commands (no LLM needed)
def generate_template_response(intent_data, message, context_str):
    """Generate template response for simple commands"""
    intent = intent_data["intent"]
    asset = intent_data.get("asset")
    amount = intent_data.get("amount")
    
    if intent == "price":
        prices = get_live_prices()
        if asset:
            asset_upper = asset.upper()
            if asset_upper in prices:
                p = prices[asset_upper]
                change_emoji = "📈" if p['change'] >= 0 else "📉"
                change_sign = "+" if p['change'] >= 0 else ""
                return f"Sir, {asset_upper} is trading at ${p['price']:,}. {change_emoji} {change_sign}{p['change']:.2f}% in 24h. Your portfolio remains robust at $311,342."
            else:
                return f"Sir, {asset} is currently trading at $1,998. Your portfolio remains robust at $311,342."
        else:
            btc = prices.get('BTC', {}).get('price', 61186)
            return f"Sir, BTC is at ${btc:,}. Which asset would you like the price for?"
    
    elif intent == "buy":
        if asset and amount:
            return f"Sir, you wish to buy {amount} {asset}? I shall prepare the transaction. Your portfolio is at $311,342."
        elif asset:
            return f"Sir, you wish to buy {asset}? How much would you like to purchase?"
        else:
            return "Sir, what would you like to buy?"
    
    elif intent == "sell":
        if asset and amount:
            return f"Sir, you wish to sell {amount} {asset}? I shall prepare the transaction. Your portfolio is at $311,342."
        elif asset:
            return f"Sir, you wish to sell {asset}? How much would you like to sell?"
        else:
            return "Sir, what would you like to sell?"
    
    elif intent == "portfolio":
        return "Sir, your portfolio is valued at $311,342, up 2.4%. You hold 100 ETH, 0.5 BTC, and 1000 SOL."
    
    elif intent == "greeting":
        from datetime import datetime
        import random
        hour = datetime.now().hour
        
        # 10 variations per time slot
        MORNING_MSGS = [
            "Good morning, sir. Your portfolio stands at $311,342. What's the plan for today?",
            "Morning, sir. Hope you rested well — portfolio's at $311,342.",
            "Good morning, sir. Fresh start — portfolio currently at $311,342.",
            "Good morning sir, portfolio $311,342 pe stable hai. Aaj ka plan kya hai?",
            "Subah ho gayi sir, portfolio $311,342 pe hai. Kuch dekhna hai?",
            "Good morning sir. Neend poori hui? Portfolio $311,342 pe khada hai.",
            "Sir, naya din shuru — portfolio $311,342 pe hai. Chaliye shuru karte hain.",
            "Good morning sir! Sab fresh hai, portfolio $311,342 pe stable.",
            "Subah ka time hai sir, portfolio $311,342. Aaj kya focus karna hai?",
            "Good morning sir, energy high rakhiye — portfolio $311,342 pe hai."
        ]
        
        AFTERNOON_MSGS = [
            "Good afternoon, sir. Jarvix at your service. Portfolio is at $311,342.",
            "Afternoon, sir. Everything's steady — portfolio at $311,342.",
            "Good afternoon, sir. Portfolio holding at $311,342. Any updates needed?",
            "Good afternoon sir, Jarvix ready hai. Portfolio $311,342 pe hai.",
            "Sir, lunch ho gaya? Portfolio $311,342 pe steady hai.",
            "Good afternoon sir, sab kuch normal hai. Portfolio $311,342.",
            "Sir, din ka half ho gaya. Portfolio $311,342 pe hai.",
            "Good afternoon! Portfolio $311,342 pe stable, sab theek hai.",
            "Sir, energy thodi low? Portfolio $311,342 pe hai, koi update?",
            "Good afternoon sir, kaam kaisa chal raha hai? Portfolio $311,342."
        ]
        
        EVENING_MSGS = [
            "Good evening, sir. How was your day? Portfolio's at $311,342.",
            "Evening, sir. Portfolio currently at $311,342. Anything to review?",
            "Good evening! Day's winding down — portfolio at $311,342.",
            "Good evening sir, din kaisa raha? Portfolio $311,342 pe hai.",
            "Sir, evening ho gayi. Portfolio $311,342. Kuch check karna hai?",
            "Good evening! Portfolio $311,342 pe hai, din wrap up ho raha hai.",
            "Sir, kaam khatam hone wala hai? Portfolio $311,342 pe stable.",
            "Good evening sir, relax mode on? Portfolio $311,342 pe hai.",
            "Sir, shaam ho gayi — portfolio $311,342 pe khada hai.",
            "Good evening! Sab settle ho raha hai, portfolio $311,342."
        ]
        
        LATE_NIGHT_MSGS = [
            "Still up, sir? Portfolio's at $311,342. Anything urgent?",
            "It's quite late, sir. Portfolio stands at $311,342 — should this wait till morning?",
            "Sir, can't sleep? Portfolio's at $311,342.",
            "Sir, raat ho gayi hai. Portfolio $311,342. Koi urgent kaam hai?",
            "Itni raat ko bhi active ho sir? Portfolio $311,342 pe hai abhi.",
            "Sir, neend nahi aa rahi kya? Portfolio $311,342 pe hai.",
            "Late night ho gaya sir — portfolio $311,342, sab theek hai?",
            "Sir, kaafi raat ho gayi. Portfolio $311,342 pe stable hai.",
            "Sir, abhi tak awake? Portfolio $311,342 — kuch zaroori hai?",
            "Itni raat ko Jarvix hazir hai sir. Portfolio $311,342 pe hai."
        ]
        
        if 5 <= hour < 12:
            return random.choice(MORNING_MSGS)
        elif 12 <= hour < 17:
            return random.choice(AFTERNOON_MSGS)
        elif 17 <= hour < 21:
            return random.choice(EVENING_MSGS)
        else:
            return random.choice(LATE_NIGHT_MSGS)
    
    else:
        return f"Sir, I understand. Your portfolio is at $311,342. How can I help?"

# Rate limiting - track last request time
last_request_time = 0
MIN_REQUEST_INTERVAL = 5  # 5 seconds between requests

class ChatRequest(BaseModel):
    message: str
    user_id: str

class AIChatResponse(BaseModel):
    response: str
    intent: str
    asset: Optional[str] = None
    amount: Optional[float] = None
    price: Optional[float] = None
    confidence: float = 0.95
    behavioral_warning: Optional[Dict] = None
    status: str = "complete"

@app.post("/api/ai/chat")
async def chat(request: ChatRequest):
    """
    Main chat endpoint - handles all user commands with JARVIS personality via LLM
    """
    # Rate limiting check (disabled - no external API calls needed)
    # All responses use regex/templates (instant, no rate limits)
    # TODO: Re-enable if using OpenRouter in future
    """
    global last_request_time
    current_time = time.time()
    time_since_last = current_time - last_request_time
    if time_since_last < MIN_REQUEST_INTERVAL:
        wait_time = MIN_REQUEST_INTERVAL - time_since_last
        return AIChatResponse(
            response=f"Sir, please wait {wait_time:.1f} seconds before sending another command.",
            intent="rate_limited",
            confidence=0.95,
            status="rate_limited"
        )
    last_request_time = current_time
    """
    
    # Get user's memory
    memory = get_memory(request.user_id)
    
    # Get conversation context
    context = memory.get_full_context()
    
    # Classify intent using LLM
    from packages.ai.intent import IntentClassifier
    classifier = IntentClassifier()
    intent_data = await classifier.classify(request.message)
    
    # Check learned patterns (self-learning Phase 1)
    learning = get_learning_system()
    learned_intent = learning.check_learned_pattern(request.message)
    if learned_intent:
        intent_data["intent"] = learned_intent
        intent_data["source"] = "learned"
        print(f"[CHAT] Used learned intent: {request.message} → {learned_intent}")
    else:
        # Check auto-learned patterns (self-learning Phase 2)
        auto_learning = get_auto_learning_system()
        auto_result = auto_learning.check_auto_learned_pattern(request.user_id, request.message)
        if auto_result:
            auto_intent, auto_confidence = auto_result
            intent_data["intent"] = auto_intent
            intent_data["confidence"] = auto_confidence
            intent_data["source"] = "auto_learned"
            print(f"[CHAT] Used auto-learned intent: {request.message} → {auto_intent} ({auto_confidence:.2f})")
    
    # Record command for auto-learning (after intent detection)
    auto_learning = get_auto_learning_system()
    auto_learning.record_command(request.user_id, request.message, intent_data["intent"])
    
    # Record command for personalization (Phase 3)
    personalization = get_personalization_system()
    personalization.update_behavior(
        request.user_id, 
        request.message, 
        intent_data["intent"],
        intent_data.get("asset"),
        intent_data.get("amount")
    )
    
    # Detect emotion
    emotion = personality_engine.detect_emotion(request.message)
    
    # Format context for LLM
    context_str = format_context_for_llm(memory)
    
    # Generate personalized response (Phase 3)
    personalization = get_personalization_system()
    personalized_response = personalization.get_personalized_response(
        request.user_id,
        intent_data["intent"],
        intent_data.get("asset")
    )
    
    # Override with real-time data for price intents
    if intent_data["intent"] == "price":
        prices = get_live_prices()
        asset = intent_data.get("asset")
        if asset:
            asset_upper = asset.upper()
            if asset_upper in prices:
                p = prices[asset_upper]
                change_emoji = "📈" if p['change'] >= 0 else "📉"
                change_sign = "+" if p['change'] >= 0 else ""
                personalized_response = f"Sir, {asset_upper} is trading at ${p['price']:,}. {change_emoji} {change_sign}{p['change']:.2f}% in 24h. Your portfolio remains robust at $311,342."
            else:
                personalized_response = f"Sir, {asset} is currently trading at $1,998. Your portfolio remains robust at $311,342."
        else:
            btc = prices.get('BTC', {}).get('price', 61186)
            personalized_response = f"Sir, BTC is at ${btc:,}. Which asset would you like the price for?"
    
    # Override for advice intents - give real analysis without LLM
    elif intent_data["intent"] == "advice":
        prices = get_live_prices()
        asset = intent_data.get("asset")
        if asset:
            asset_upper = asset.upper()
            if asset_upper in prices:
                p = prices[asset_upper]
                change_emoji = "📈" if p['change'] >= 0 else "📉"
                change_sign = "+" if p['change'] >= 0 else ""
                trend = "bullish" if p['change'] >= 0 else "bearish"
                personalized_response = f"Sir, {asset_upper} is at ${p['price']:,} ({change_sign}{p['change']:.2f}%). Market sentiment is {trend}. Based on current momentum, {asset_upper} shows {trend} signals. Your portfolio remains robust at $311,342. Shall I set an alert for significant moves?"
            else:
                personalized_response = f"Sir, I cannot access real-time data for {asset} at the moment. Based on recent market analysis, consider dollar-cost averaging. Your portfolio is at $311,342."
        else:
            btc = prices.get('BTC', {}).get('price', 61186)
            eth = prices.get('ETH', {}).get('price', 1619)
            personalized_response = f"Sir, BTC is at ${btc:,} and ETH at ${eth:,}. Both showing mixed signals. Consider your risk tolerance before entering. Portfolio at $311,342. Which asset interests you?"
    
    # Override for alert intents
    elif intent_data["intent"] == "alert":
        prices = get_live_prices()
        asset = intent_data.get("asset")
        if asset:
            asset_upper = asset.upper()
            current_price = prices.get(asset_upper, {}).get('price', 0)
            personalized_response = f"Sir, alert set for {asset_upper}. Current price: ${current_price:,}. I shall notify you when the target is reached. Your portfolio remains robust at $311,342."
        else:
            btc = prices.get('BTC', {}).get('price', 61186)
            personalized_response = f"Sir, alert configured. BTC is currently at ${btc:,}. I shall notify you when conditions are met. Your portfolio remains robust at $311,342."
    
    # Override for portfolio intent
    elif intent_data["intent"] == "portfolio":
        prices = get_live_prices()
        btc = prices.get('BTC', {}).get('price', 61186)
        eth = prices.get('ETH', {}).get('price', 1619)
        sol = prices.get('SOL', {}).get('price', 63)
        personalized_response = f"Sir, your portfolio is valued at $311,342. Holdings: BTC at ${btc:,}, ETH at ${eth:,}, SOL at ${sol:,}. All systems optimal."
    
    # Override for buy/sell intents
    elif intent_data["intent"] in ["buy", "sell"]:
        prices = get_live_prices()
        asset = intent_data.get("asset")
        amount = intent_data.get("amount")
        if asset and amount:
            asset_upper = asset.upper()
            current_price = prices.get(asset_upper, {}).get('price', 0)
            total = amount * current_price
            action = "purchase" if intent_data["intent"] == "buy" else "sale"
            personalized_response = f"Sir, {action} order prepared for {amount} {asset_upper} at ${current_price:,} (total: ${total:,}). Shall I execute? Your portfolio remains robust at $311,342."
        elif asset:
            asset_upper = asset.upper()
            current_price = prices.get(asset_upper, {}).get('price', 0)
            action = "purchase" if intent_data["intent"] == "buy" else "sale"
            personalized_response = f"Sir, {action} order ready for {asset_upper} at ${current_price:,}. Please specify the amount. Your portfolio remains robust at $311,342."
        else:
            personalized_response = f"Sir, I understand you wish to {intent_data['intent']}. Please specify the asset and amount. Your portfolio remains robust at $311,342."
    
    # LLM Router (Step 3): Decide if LLM is needed
    llm_router = get_llm_router()
    use_llm, reason = llm_router.should_use_llm(request.message, intent_data["intent"])
    
    # Step 1: Universal Intent Parser for unknown commands
    if intent_data["intent"] == "unknown" and intent_data.get("universal_parse", False):
        print(f"[UNIVERSAL PARSER] Handling unknown command: {request.message}")
        from packages.ai.universal_intent import handle_unknown_command
        from packages.ai.agent_planner import plan_agent_task, execute_agent_task, get_task_status
        
        universal_result = await handle_unknown_command(
            request.message, 
            intent_data["intent"], 
            context
        )
        
        classification = universal_result["classification"]
        category = classification["category"]
        
        print(f"[UNIVERSAL PARSER] Category: {category}, Confidence: {classification['confidence']:.2f}")
        
        if category == "reject":
            response_text = universal_result["response"]
            intent_data["intent"] = "rejected"
            intent_data["confidence"] = classification["confidence"]
            
        elif category == "direct_answer":
            response_text = universal_result["response"]
            intent_data["intent"] = "direct_answer"
            intent_data["confidence"] = classification["confidence"]
            
        elif category == "clarify":
            response_text = universal_result["response"]
            intent_data["intent"] = "clarify"
            intent_data["confidence"] = classification["confidence"]
            
        elif category == "tool_call":
            # Step 2: Execute the tool!
            from packages.ai.tool_executor import parse_and_execute_tools
            
            suggested_tools = classification.get("suggested_tools", [])
            if suggested_tools:
                print(f"[TOOL EXECUTOR] Executing tools: {suggested_tools}")
                tool_result = await parse_and_execute_tools(
                    request.message,
                    suggested_tools
                )
                response_text = tool_result["response"]
                print(f"[TOOL EXECUTOR] Result: {response_text[:100]}...")
            else:
                response_text = universal_result["response"]
            
            intent_data["intent"] = "tool_call"
            intent_data["confidence"] = classification["confidence"]
            intent_data["suggested_tools"] = suggested_tools
            
        elif category == "agent_task":
            # Step 3: Plan and execute agent task!
            from packages.ai.agent_planner import plan_agent_task
            
            agent_result = await plan_agent_task(request.message, request.user_id)
            
            if agent_result["is_agent_task"]:
                response_text = agent_result["response"]
                intent_data["intent"] = "agent_task"
                intent_data["confidence"] = classification["confidence"]
                intent_data["task_id"] = agent_result.get("task_id")
                intent_data["steps_count"] = agent_result.get("steps_count")
            else:
                response_text = agent_result["response"]
                intent_data["intent"] = "agent_task"
                intent_data["confidence"] = classification["confidence"]
            
        elif category == "known_crypto":
            # Re-classify as crypto command
            response_text = universal_result["response"]
            intent_data["intent"] = "advice"  # Generic crypto handler
            intent_data["confidence"] = classification["confidence"]
            
        else:
            response_text = universal_result["response"]
            intent_data["intent"] = "unknown_handled"
            intent_data["confidence"] = classification["confidence"]
        
        llm_router.record_request(request.message, intent_data["intent"], True)
        
    elif personalized_response:
        response_text = personalized_response
        llm_router.record_request(request.message, intent_data["intent"], False)
    elif intent_data["intent"] in REGEX_ONLY_INTENTS:
        # Regex-only intents: no LLM needed
        response_text = generate_template_response(intent_data, request.message, context_str)
        llm_router.record_request(request.message, intent_data["intent"], False)
    else:
        # Complex queries: would use LLM if available
        # For now, use template with note
        response_text = generate_template_response(intent_data, request.message, context_str)
        llm_router.record_request(request.message, intent_data["intent"], False)
        print(f"[LLM ROUTER] Would use LLM for: {request.message} (Reason: {reason})")
    
    # Clean response before storing in memory
    cleaned_response = response_text.strip()
    
    # Fallback if response is empty
    if not cleaned_response.strip():
        cleaned_response = f"Sir, I understand. Your portfolio is at $311,342. How can I help?"
    
    # Store in memory
    memory.add_message("user", request.message, intent_data["intent"])
    memory.add_message("assistant", cleaned_response)
    
    return AIChatResponse(
        response=cleaned_response,
        intent=intent_data["intent"],
        asset=intent_data.get("asset"),
        amount=intent_data.get("amount"),
        price=intent_data.get("price"),
        confidence=intent_data.get("confidence", 0.95),
        behavioral_warning={"detected_emotion": emotion, "secondary_intent": intent_data.get("secondary_intent")} if intent_data.get("secondary_intent") else {"detected_emotion": emotion} if emotion != "neutral" else None,
        status="complete"
    )

@app.post("/api/ai/feedback")
async def add_feedback(request: ChatRequest):
    """
    Add user feedback/correction
    Example: User says "No, I meant sell" after Jarvix detected "buy"
    """
    learning = get_learning_system()
    
    # Parse feedback message
    # Expected format: "correct: {correct_intent}" or "No, I meant {correct_intent}"
    message = request.message.lower()
    
    # Extract correct intent from feedback
    correct_intent = None
    if "correct:" in message:
        correct_intent = message.split("correct:")[1].strip()
    elif "meant" in message:
        correct_intent = message.split("meant")[1].strip()
    elif "should be" in message:
        correct_intent = message.split("should be")[1].strip()
    
    if correct_intent:
        # Get last message from memory
        memory = get_memory(request.user_id)
        last_messages = memory.get_messages(2)
        
        if len(last_messages) >= 2:
            original_message = last_messages[0]['message']  # User's original message
            predicted_intent = last_messages[0].get('intent', 'unknown')
            
            # Add correction
            learning.add_correction(original_message, predicted_intent, correct_intent, request.user_id)
            
            return {
                "status": "learned",
                "message": f"Thank you, sir. I have learned that '{original_message}' should be '{correct_intent}'.",
                "original_message": original_message,
                "correct_intent": correct_intent
            }
    
    return {
        "status": "error",
        "message": "I apologize, sir. I could not understand your feedback. Please use format: 'correct: {intent}'"
    }

@app.get("/api/ai/learning/stats")
async def learning_stats():
    """Get learning statistics"""
    learning = get_learning_system()
    stats = learning.get_learning_stats()
    return stats

@app.get("/api/ai/learning/stats/{user_id}")
async def user_learning_stats(user_id: str):
    """Get learning statistics for specific user"""
    learning = get_learning_system()
    auto_learning = get_auto_learning_system()
    
    feedback_stats = learning.get_user_learning_stats(user_id)
    auto_stats = auto_learning.get_user_stats(user_id)
    
    return {
        'feedback': feedback_stats,
        'auto_learning': auto_stats
    }

@app.get("/api/ai/auto-learning/stats")
async def auto_learning_stats():
    """Get auto-learning statistics"""
    auto_learning = get_auto_learning_system()
    stats = auto_learning.get_stats()
    return stats

@app.get("/api/ai/llm-router/stats")
async def llm_router_stats():
    """Get LLM router statistics"""
    llm_router = get_llm_router()
    stats = llm_router.get_cost_stats()
    return stats

@app.get("/api/ai/personalization/insights/{user_id}")
async def user_insights(user_id: str):
    """Get user insights and personalization data"""
    personalization = get_personalization_system()
    insights = personalization.get_user_insights(user_id)
    return insights

@app.get("/api/ai/personalization/suggestions/{user_id}")
async def user_suggestions(user_id: str):
    """Get personalized suggestions for user"""
    personalization = get_personalization_system()
    suggestions = personalization.get_suggestions(user_id)
    return {"suggestions": suggestions}

@app.post("/api/ai/personalization/preferences/{user_id}")
async def update_user_preferences(user_id: str, preferences: dict):
    """Update user preferences"""
    personalization = get_personalization_system()
    updated = personalization.update_preferences(user_id, preferences)
    return {"status": "updated", "preferences": updated}

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "jarvix-backend", "version": "1.0.0"}

@app.get("/api/health")
async def api_health():
    """API health check endpoint"""
    return {"status": "healthy", "service": "jarvix-backend", "version": "1.0.0"}

@app.get("/api/portfolio")
async def api_portfolio():
    """API portfolio endpoint"""
    return {"total_value": 100000, "change_pct": 2.4, "holdings": []}

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Jarvix AI Backend", "version": "1.0.0", "personality": "JARVIS", "llm": "enabled"}

@app.get("/test-llm")
async def test_llm():
    """Test LLM connection"""
    from packages.ai.llm_client import test_llm_connection
    result = await test_llm_connection()
    return {"llm_response": result}

@app.post("/api/ghost/initialize")
async def ghost_initialize(user_id: str):
    """Initialize ghost mode for user"""
    ghost = get_ghost_mode(user_id)
    portfolio = ghost.initialize()
    return {"status": "initialized", "portfolio": portfolio}

@app.get("/api/ghost/portfolio")
async def ghost_portfolio(user_id: str):
    """Get ghost mode portfolio"""
    ghost = get_ghost_mode(user_id)
    summary = ghost.get_summary()
    return summary

@app.post("/api/ghost/trade")
async def ghost_trade(user_id: str, action: str, asset: str, amount: float, price: float):
    """Execute paper trade"""
    ghost = get_ghost_mode(user_id)
    result = ghost.execute_trade(action, asset, amount, price)
    return result

@app.get("/api/ghost/trades")
async def ghost_trades(user_id: str, limit: int = 10):
    """Get recent trades"""
    ghost = get_ghost_mode(user_id)
    trades = ghost.get_trades(limit)
    return {"trades": trades}

@app.get("/api/alerts")
async def get_alerts(user_id: str, limit: int = 10):
    """Get user alerts"""
    manager = get_alert_manager(user_id)
    alerts = manager.get_alerts(limit, include_read=True)
    return {"alerts": alerts, "unread_count": manager.get_unread_count()}

@app.post("/api/alerts/mark-read")
async def mark_alert_read(user_id: str, alert_id: str):
    """Mark alert as read"""
    manager = get_alert_manager(user_id)
    success = manager.mark_read(alert_id)
    return {"success": success}

@app.post("/api/alerts/check")
async def check_alerts(user_id: str):
    """Check for new alerts"""
    manager = get_alert_manager(user_id)
    
    # Check market alerts
    market_alerts = manager.check_market_alerts()
    
    return {
        "market_alerts": market_alerts,
        "unread_count": manager.get_unread_count()
    }

@app.websocket("/ws/prices")
async def websocket_prices(websocket: WebSocket):
    """WebSocket for real-time prices"""
    await websocket.accept()
    try:
        while True:
            # Send demo price data
            prices = {
                "BTC": {"price": 65000 + random.randint(-1000, 1000), "change_24h": 2.5},
                "ETH": {"price": 3500 + random.randint(-100, 100), "change_24h": 1.8},
                "SOL": {"price": 150 + random.randint(-10, 10), "change_24h": -0.5},
            }
            await websocket.send_json(prices)
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        pass

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), reload=True)
# Deploy trigger
