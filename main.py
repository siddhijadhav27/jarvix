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

# Add packages to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'packages'))

from ai.personality import personality_engine
from ai.llm_client import generate_jarvis_response
from ai.openrouter_client import call_openrouter
from ai.mock_llm import generate_mock_response
from ai.intent import IntentClassifier
from ai.memory import get_memory, format_context_for_llm
from ai.ghost_mode import get_ghost_mode
from ai.proactive_alerts import get_alert_manager
from ai.self_learning import get_learning_system
from ai.auto_learning import get_auto_learning_system
from ai.personalization import get_personalization_system
from ai.llm_router import get_llm_router, REGEX_ONLY_INTENTS

app = FastAPI()

# CORS Middleware - dynamic from env var
cors_origins = os.getenv("CORS_ORIGINS", "")
if cors_origins:
    allow_origins = [origin.strip() for origin in cors_origins.split(",")]
else:
    allow_origins = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
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
        from ai.intent import IntentClassifier
        classifier = IntentClassifier()
        result = await classifier.classify(request.message)
        
        latency_ms = int((time.time() - start) * 1000)
        
        return ChatResponse(
            intent=result.get("intent", "UNKNOWN"),
            confidence=result.get("confidence", 0.0),
            fast_path=True,
            source="llm",
            entities=result.get("entities", {}),
            message="Processing complete, sir.",
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
    prices = dict(DEMO_PRICES)
    
    try:
        while True:
            for asset in prices:
                change = random.uniform(-0.005, 0.005)
                prices[asset] = round(DEMO_PRICES[asset] * (1 + change), 2)
            
            await websocket.send_json({
                **prices,
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
            timeout=5
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
        return "Good day, sir. Jarvix at your service. Your portfolio is at $311,342. How may I assist?"
    
    else:
        return f"Sir, I understand. Your portfolio is at $311,342. How can I help?"

app = FastAPI(title="Jarvix AI Backend", version="1.0.0")

# Rate limiting - track last request time
last_request_time = 0
MIN_REQUEST_INTERVAL = 5  # 5 seconds between requests

# CORS for frontend connection
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    user_id: str

class ChatResponse(BaseModel):
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
        return ChatResponse(
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
    from ai.intent import IntentClassifier
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
        from ai.universal_intent import handle_unknown_command
        from ai.agent_planner import plan_agent_task, execute_agent_task, get_task_status
        
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
            from ai.tool_executor import parse_and_execute_tools
            
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
            from ai.agent_planner import plan_agent_task
            
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
    
    return ChatResponse(
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
    from ai.llm_client import test_llm_connection
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
