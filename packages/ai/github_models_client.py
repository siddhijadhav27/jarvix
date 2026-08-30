"""
GitHub Models LLM Client for Jarvix
Direct API access to GPT-4o via GitHub Models (free tier)
"""

import httpx
import json
import os
from typing import Optional, Dict, Any

GITHUB_MODELS_URL = "https://models.inference.ai.azure.com/chat/completions"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

async def call_llm(prompt: str, timeout: float = 30.0) -> str:
    """
    Call LLM via GitHub Models API (GPT-4o)
    
    Args:
        prompt: The prompt to send to LLM
        timeout: Request timeout in seconds
        
    Returns:
        Cleaned LLM response text
    """
    # Load token from .env if not in environment
    token = GITHUB_TOKEN
    if not token:
        try:
            with open('/home/siddhi/jarvix-backend/.env') as f:
                for line in f:
                    if line.startswith('GITHUB_TOKEN='):
                        token = line.strip().split('=', 1)[1]
                        break
        except:
            pass
    
    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
        
        payload = {
            "model": "gpt-4o",
            "messages": [
                {"role": "system", "content": "You are a crypto trading assistant. Return ONLY valid JSON."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 500
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                GITHUB_MODELS_URL,
                headers=headers,
                json=payload,
                timeout=timeout
            )
            response.raise_for_status()
            data = response.json()
            
            return data["choices"][0]["message"]["content"]
            
    except httpx.ConnectError:
        return "Error: Cannot connect to GitHub Models API."
    except httpx.TimeoutException:
        return "Error: LLM request timed out."
    except Exception as e:
        return f"Error: {str(e)}"


async def classify_intent_llm_github(message: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Use GitHub Models LLM to classify intent
    """
    prompt = f"""Classify this crypto trading message. Return ONLY JSON:

Message: "{message}"

Return format:
{{
    "intent": "buy|sell|price|portfolio|advice|greeting|unknown",
    "asset": "BTC|ETH|SOL|null",
    "amount": null,
    "price": null,
    "confidence": 0.0-1.0
}}

Examples:
"Buy 100 ETH" -> {{"intent": "buy", "asset": "ETH", "amount": 100, "price": null, "confidence": 0.95}}
"What's BTC price?" -> {{"intent": "price", "asset": "BTC", "amount": null, "price": null, "confidence": 0.95}}
"Hi there" -> {{"intent": "greeting", "asset": null, "amount": null, "price": null, "confidence": 0.95}}
"What is the best time to buy Bitcoin?" -> {{"intent": "advice", "asset": "BTC", "amount": null, "price": null, "confidence": 0.92}}

Return ONLY JSON:"""

    response = await call_llm(prompt)
    
    try:
        # Extract JSON
        json_match = __import__('re').search(r'\{.*\}', response, __import__('re').DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            return {
                "intent": result.get("intent", "unknown"),
                "asset": result.get("asset"),
                "amount": result.get("amount"),
                "price": result.get("price"),
                "confidence": result.get("confidence", 0.5)
            }
    except:
        pass
    
    return {"intent": "unknown", "asset": None, "amount": None, "price": None, "confidence": 0.0}


# Test
async def test_github_models():
    """Test GitHub Models connection"""
    result = await call_llm("Say 'GitHub Models is ready' if you can hear me.")
    return result
