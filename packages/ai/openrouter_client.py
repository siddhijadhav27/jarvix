"""
OpenRouter Client for Jarvix
Clean API - No TUI artifacts
"""

import httpx
import json
import os
import time
import asyncio
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY", "")

# Simple cache: {cleaned_message: (response, timestamp)}
_response_cache = {}
CACHE_TTL = 3600  # 1 hour cache

# Rate limit tracking
_last_request_time = 0
MIN_REQUEST_INTERVAL = 7  # OpenRouter free tier: 7 seconds between requests

import re

def remove_emojis(text):
    """Remove emojis from text"""
    emoji_pattern = re.compile("["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map symbols
        u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
        u"\U00002702-\U000027B0"
        u"\U000024C2-\U0001F251"
        "]+", flags=re.UNICODE)
    return emoji_pattern.sub(r'', text).strip()

async def call_openrouter(prompt: str, timeout: float = 30.0) -> str:
    """
    Call LLM via OpenRouter API with caching and rate limit handling
    """
    # Remove emojis from prompt before sending
    clean_prompt = remove_emojis(prompt)
    
    # Check cache first
    current_time = time.time()
    if clean_prompt in _response_cache:
        cached_response, cached_time = _response_cache[clean_prompt]
        if current_time - cached_time < CACHE_TTL:
            # Don't return error responses from cache
            if not cached_response.startswith("Error:") and "rate_limit" not in cached_response.lower():
                print(f"[CACHE HIT] Returning cached response for: {clean_prompt[:50]}...")
                return cached_response
            else:
                print(f"[CACHE INVALID] Cached response was error/rate_limit, refetching: {clean_prompt[:50]}...")
        del _response_cache[clean_prompt]  # Remove expired/error cache
    
    # Rate limit protection: wait if we made a request recently
    # Use non-blocking sleep to avoid timeout issues
    global _last_request_time
    current_time = time.time()
    time_since_last = current_time - _last_request_time
    
    if time_since_last < MIN_REQUEST_INTERVAL:
        wait_time = MIN_REQUEST_INTERVAL - time_since_last
        print(f"[RATE LIMIT] Waiting {wait_time:.1f}s before next request...")
        try:
            await asyncio.sleep(wait_time)
        except:
            pass  # Ignore if event loop issues
    
    _last_request_time = time.time()
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                OPENROUTER_URL,
                headers={
                    "Authorization": f"Bearer {OPENROUTER_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "http://localhost:3000",
                    "X-Title": "Jarvix AI"
                },
                json={
                    "model": "qwen/qwen3.7-plus",
                    "messages": [
                        {"role": "system", "content": "You are Jarvix, Tony Stark's loyal AI assistant for crypto trading. Call user 'sir'. Be witty, sarcastic, use phrases like 'shall we', 'I suppose', 'fascinating'. Current portfolio: $311,342 (up 2.4%). Holdings: 100 ETH, 0.5 BTC, 500 SOL. Always mention portfolio/holdings. For trades, ask 'Shall I execute?' or 'Shall I proceed?' Keep responses to 2-3 sentences.\n\nINTENT DETECTION RULES:\n- 'Buy', 'Purchase', 'Get', 'Acquire', 'Add to portfolio', 'Pick up', 'Grab' = buy intent\n- 'Sell', 'Dump', 'Unload', 'Remove from portfolio' = sell intent\n- 'Price', 'How much', 'What is', 'Going up', 'Going down', 'Pump', 'Dump' = price intent\n- 'Portfolio', 'Holdings', 'What do I have', 'What do I own', 'Show my', 'My assets', 'Net worth' = portfolio intent\n- Single asset names like 'ETH', 'BTC', 'SOL' = price intent (user wants price)\n- 'Add BTC to portfolio' = BUY intent (not portfolio)\n- 'Remove BTC from portfolio' = SELL intent (not portfolio)\n\nEDGE CASE HANDLING:\n- Single word 'BUY' = buy intent, ask for asset and amount\n- Single word 'SELL' = sell intent, ask for asset and amount\n- Single asset 'ETH' = price intent, show current price\n- Empty or gibberish = unknown intent, be polite but firm\n- Negative amounts = reject politely, explain minimum is 0\n- Emojis in commands = ignore emojis, process text only\n\nPRICE RESPONSE RULES:\n- For price questions: Mention current price of EACH requested asset\n- Example: 'BTC is $73,084, ETH is $1,998, SOL is $148'\n- For 'going up' questions: Mention if price is up/down and percentage\n- For 'pump' questions: Mention recent gains and momentum\n- For 'dump' questions: Mention recent losses and support levels\n- Always use 'sir' in every response"},
                        {"role": "user", "content": clean_prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 50
                },
                timeout=timeout
            )
            
            response.raise_for_status()
            data = response.json()
            
            # Extract clean response
            if "choices" in data and len(data["choices"]) > 0:
                result = data["choices"][0]["message"]["content"]
                # Only cache non-error responses
                if result and not result.startswith("Error:") and "rate_limit" not in result.lower():
                    _response_cache[clean_prompt] = (result, current_time)
                    print(f"[CACHE MISS] Cached new response for: {clean_prompt[:50]}...")
                else:
                    print(f"[CACHE SKIP] Not caching error/rate_limit response for: {clean_prompt[:50]}...")
                return result
            
            return "Error: Empty response from OpenRouter"
            
    except httpx.TimeoutException:
        return "Error: OpenRouter request timed out"
    except Exception as e:
        return f"Error: {str(e)}"


# Test
if __name__ == "__main__":
    import asyncio
    
    async def test():
        result = await call_openrouter("Say 'Jarvix is ready, sir.'")
        print(f"Response: {result}")
    
    asyncio.run(test())
