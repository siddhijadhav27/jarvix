from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import sys
import os
import time

# Add packages to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'packages'))

from ai.personality import personality_engine
from ai.llm_client import generate_jarvis_response
from ai.openrouter_client import call_openrouter
from ai.mock_llm import generate_mock_response
from ai.intent import detect_intent_hybrid
from ai.memory import get_memory, format_context_for_llm
from ai.ghost_mode import get_ghost_mode
from ai.proactive_alerts import get_alert_manager

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
    asset: str | None = None
    amount: float | None = None
    price: float | None = None
    confidence: float = 0.95
    behavioral_warning: dict | None = None
    status: str = "complete"

@app.post("/api/ai/chat")
async def chat(request: ChatRequest):
    """
    Main chat endpoint - handles all user commands with JARVIS personality via LLM
    """
    global last_request_time
    
    # Rate limiting check
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
    
    # Get user's memory
    memory = get_memory(request.user_id)
    
    # Get conversation context
    context = memory.get_full_context()
    
    # Classify intent using hybrid approach (regex + LLM fallback)
    intent_data = await detect_intent_hybrid(request.message, context)
    
    # Detect emotion
    emotion = personality_engine.detect_emotion(request.message)
    
    # Format context for LLM
    context_str = format_context_for_llm(memory)
    
    # Generate JARVIS-style response using OpenRouter
    prompt = f"""You are Jarvix, Tony Stark's personal AI assistant for cryptocurrency trading.

User message: "{request.message}"
Intent: {intent_data['intent']}
Asset: {intent_data.get('asset', 'not specified')}
Amount: {intent_data.get('amount', 'not specified')}

Context: {context_str}

Respond like JARVIS from Iron Man:
- Call user "sir"
- Be witty, sarcastic, loyal
- Include relevant portfolio data
- Keep it to 2-3 sentences
- Ask for confirmation on trades"""
    
    response_text = await call_openrouter(prompt)
    
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

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "jarvix-backend", "version": "1.0.0"}

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

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
