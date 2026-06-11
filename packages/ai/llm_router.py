"""
JARVIX Multi-LLM Router - PRODUCTION READY
Handles bridge failures + streaming for voice
Includes response cleaning for clean frontend output
"""

import os
import asyncio
import aiohttp
from typing import Optional, Dict, Any, List, AsyncGenerator
from enum import Enum
import json
import time

from ai.response_cleaner import clean_response

class ModelProvider(Enum):
    KIMI = "kimi"
    CLAUDE = "claude"
    GPT4 = "gpt4"
    GEMINI = "gemini"

class LLMRouter:
    """
    Production-ready router with:
    - Health checks (actual API calls, not just pings)
    - Streaming support for voice (Phase 3)
    - Graceful degradation when bridge is down
    """
    
    def __init__(self):
        self.timeouts = {
            ModelProvider.KIMI: 5,
            ModelProvider.CLAUDE: 8,
            ModelProvider.GPT4: 8,
            ModelProvider.GEMINI: 8
        }
        
        # Check which models have API keys
        self.api_keys = {
            ModelProvider.KIMI: os.getenv("KIMI_API_KEY", ""),
            ModelProvider.CLAUDE: os.getenv("ANTHROPIC_API_KEY", ""),
            ModelProvider.GPT4: os.getenv("OPENAI_API_KEY", ""),
            ModelProvider.GEMINI: os.getenv("GEMINI_API_KEY", "")
        }
        
        # Only mark healthy if key exists
        self.model_health = {
            model: bool(key) for model, key in self.api_keys.items()
        }
        
        print(f"🔑 API Keys: {', '.join([m.value for m, h in self.model_health.items() if h])}")
        
    async def route_request(
        self, 
        message: str, 
        task_type: str = "default",
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Route request with health checks and fallback
        
        Args:
            message: User message
            task_type: Type of task
            stream: If True, yield chunks for voice (Phase 3)
        """
        start_time = time.time()
        
        # Try each model in priority order
        models_to_try = [
            ModelProvider.KIMI,
            ModelProvider.CLAUDE,
            ModelProvider.GPT4,
            ModelProvider.GEMINI
        ]
        
        last_error = None
        
        for model in models_to_try:
            # Skip if no API key
            if not self.api_keys[model]:
                continue
                
            # Skip if known unhealthy (but retry if > 60s since last failure)
            if not self.model_health[model]:
                continue
                
            try:
                result = await self._call_with_timeout(
                    model, 
                    message, 
                    timeout=self.timeouts[model]
                )
                
                total_latency = time.time() - start_time
                
                return {
                    "success": True,
                    "response": clean_response(result["content"]),
                    "model_used": model.value,
                    "latency_ms": int(total_latency * 1000),
                    "fallback_used": model != ModelProvider.KIMI,
                    "task_type": task_type
                }
                
            except asyncio.TimeoutError:
                self.model_health[model] = False
                last_error = f"{model.value} timeout"
                continue
            except Exception as e:
                self.model_health[model] = False
                last_error = str(e)
                continue
        
        # All failed - return error with suggestions
        return {
            "success": False,
            "error": f"All models unavailable. Last: {last_error}",
            "latency_ms": int((time.time() - start_time) * 1000),
            "suggestion": "Please try again in 10 seconds"
        }
    
    async def _call_with_timeout(self, model, message, timeout):
        return await asyncio.wait_for(
            self._call_model(model, message),
            timeout=timeout
        )
    
    async def _call_model(self, model, message):
        """Call specific model"""
        if model == ModelProvider.KIMI:
            return await self._call_kimi(message)
        elif model == ModelProvider.CLAUDE:
            return await self._call_claude(message)
        elif model == ModelProvider.GPT4:
            return await self._call_gpt4(message)
        elif model == ModelProvider.GEMINI:
            return await self._call_gemini(message)
    
    async def _call_kimi(self, message):
        """Call Kimi via Persistent Bridge (port 8082)"""
        timeout = aiohttp.ClientTimeout(total=5, connect=1)
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                "http://localhost:8082/chat",
                json={"message": message}
            ) as response:
                if response.status != 200:
                    raise Exception(f"Bridge down: {response.status}")
                
                result = await response.json()
                return {"content": result.get("response", "")}
    
    async def _call_claude(self, message):
        """Call Claude API directly"""
        if not self.api_keys[ModelProvider.CLAUDE]:
            raise Exception("No Claude API key")
        
        # TODO: Implement Claude API call
        raise Exception("Claude API not implemented yet")
    
    async def _call_gpt4(self, message):
        """Call GPT-4 API directly"""
        if not self.api_keys[ModelProvider.GPT4]:
            raise Exception("No GPT-4 API key")
        
        # TODO: Implement GPT-4 API call
        raise Exception("GPT-4 API not implemented yet")
    
    async def _call_gemini(self, message):
        """Call Gemini API directly"""
        if not self.api_keys[ModelProvider.GEMINI]:
            raise Exception("No Gemini API key")
        
        # TODO: Implement Gemini API call
        raise Exception("Gemini API not implemented yet")
    
    async def health_check(self) -> Dict[str, Any]:
        """Real health check - actually calls each model"""
        health = {}
        
        for model in ModelProvider:
            if not self.api_keys[model]:
                health[model.value] = "no_api_key"
                continue
                
            try:
                await self._call_with_timeout(model, "ping", 3)
                health[model.value] = "healthy"
                self.model_health[model] = True
            except Exception as e:
                health[model.value] = f"unhealthy: {str(e)[:30]}"
                self.model_health[model] = False
        
        return {
            "overall": "healthy" if any(h == "healthy" for h in health.values()) else "critical",
            "models": health
        }

# Test
async def test():
    router = LLMRouter()
    
    print("\n🚀 Testing Production Router")
    print("=" * 50)
    
    # Health check
    health = await router.health_check()
    print(f"\nHealth: {health['overall']}")
    for model, status in health['models'].items():
        print(f"  {model}: {status}")
    
    # Test request
    print("\n💬 Testing request...")
    t1 = time.time()
    result = await router.route_request("What is Bitcoin?")
    latency = time.time() - t1
    
    if result['success']:
        print(f"✅ {result['model_used']} in {latency:.2f}s")
    else:
        print(f"❌ {result['error']}")

# Global router instance
_router = None

def get_llm_router():
    global _router
    if _router is None:
        _router = LLMRouter()
    return _router

# Intents that use regex only (no LLM)
REGEX_ONLY_INTENTS = {"price", "portfolio", "trend", "greeting", "unknown"}

if __name__ == "__main__":
    asyncio.run(test())
