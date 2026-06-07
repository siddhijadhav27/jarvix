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
from ai.self_learning import get_learning_system
from ai.auto_learning import get_auto_learning_system
from ai.personalization import get_personalization_system
from ai.llm_router import get_llm_router, REGEX_ONLY_INTENTS

# Template responses for simple commands (no LLM needed)
def generate_template_response(intent_data, message, context_str):
    """Generate template response for simple commands"""
    intent = intent_data["intent"]
    asset = intent_data.get("asset")
    amount = intent_data.get("amount")
    
    if intent == "price":
        if asset:
            return f"Sir, {asset} is currently trading at $1,998. Your portfolio remains robust at $311,342."
        else:
            return "Sir, which asset would you like the price for?"
    
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
    
    # Classify intent using hybrid approach (regex + LLM fallback)
    intent_data = await detect_intent_hybrid(request.message, context)
    
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
    
    # LLM Router (Step 3): Decide if LLM is needed
    llm_router = get_llm_router()
    use_llm, reason = llm_router.should_use_llm(request.message, intent_data["intent"])
    
    # Use personalized response if available, otherwise use template
    if personalized_response:
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
