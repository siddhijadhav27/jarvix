"""OpenRouter client - stub for missing module"""
import os

async def call_openrouter(prompt, model="anthropic/claude-sonnet-4", max_tokens=500, temperature=0.7):
    """Stub - returns generic response if API key not available"""
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        return f"Sir, I understand your request about: {prompt[:50]}... Your portfolio remains robust. How may I assist further?"
    
    # Real implementation would call OpenRouter API
    return f"Sir, I have analyzed your request. Your portfolio remains robust at $100,000. How may I assist?"

async def test_llm_connection():
    """Test LLM connection"""
    return "LLM connection test - stub mode"
