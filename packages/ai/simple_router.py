"""Simple router - stub for missing module"""
import os

async def simple_chat(prompt: str, model: str = "default") -> str:
    """Stub - returns generic response"""
    # Check if we have an API key for real LLM calls
    api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("KIMI_API_KEY")
    
    if not api_key:
        # Return a mock JSON response for intent classification
        if "intent" in prompt.lower():
            return '{"intent": "unknown", "asset": null, "amount": null, "amount_type": null, "price": null, "confidence": 0.5, "needs_clarification": true, "clarification_question": "I am not sure what you mean. Could you please clarify?"}'
        return "Sir, I understand your request. How may I assist you today?"
    
    # Real implementation would call LLM API
    return "Sir, I have processed your request. Your portfolio remains robust."
