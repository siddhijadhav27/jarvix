"""
JARVIX Multi-LLM Router - FIXED VERSION
Optimized for low latency with proper error handling
"""

import os
import asyncio
import aiohttp
from typing import Optional, Dict, Any, List
from enum import Enum
import json
import time

class ModelProvider(Enum):
    KIMI = "kimi"
    CLAUDE = "claude"
    GPT4 = "gpt4"
    GEMINI = "gemini"

class LLMRouter:
    """
    Intelligent router with aggressive timeouts for trading use case
    """
    
    def __init__(self):
        # Aggressive timeouts for trading platform
        self.timeouts = {
            ModelProvider.KIMI: 5,      # 5 seconds max
            ModelProvider.CLAUDE: 8,
            ModelProvider.GPT4: 8,
            ModelProvider.GEMINI: 8
        }
        
        self.model_health = {model: True for model in ModelProvider}
        
    async def route_request(
        self, 
        message: str, 
        task_type: str = "default",
        conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Route request with aggressive timeouts
        Target: < 5 seconds total latency
        """
        start_time = time.time()
        
        # Try models in order of speed
        models_to_try = [
            ModelProvider.KIMI,
            ModelProvider.CLAUDE,
            ModelProvider.GPT4,
            ModelProvider.GEMINI
        ]
        
        last_error = None
        
        for model in models_to_try:
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
                    "response": result["content"],
                    "model_used": model.value,
                    "latency_ms": int(total_latency * 1000),
                    "fallback_used": model != ModelProvider.KIMI,
                    "task_type": task_type
                }
                
            except asyncio.TimeoutError:
                self.model_health[model] = False
                last_error = f"{model.value} timeout after {self.timeouts[model]}s"
                print(f"⏱️  {model.value} timed out")
                continue
            except Exception as e:
                self.model_health[model] = False
                last_error = str(e)
                print(f"❌ {model.value} failed: {str(e)[:50]}")
                continue
        
        # All failed
        return {
            "success": False,
            "error": f"All models failed. Last: {last_error}",
            "latency_ms": int((time.time() - start_time) * 1000)
        }
    
    async def _call_with_timeout(
        self, 
        model: ModelProvider, 
        message: str, 
        timeout: int
    ) -> Dict[str, Any]:
        """Call model with strict timeout"""
        
        return await asyncio.wait_for(
            self._call_model(model, message),
            timeout=timeout
        )
    
    async def _call_model(self, model: ModelProvider, message: str) -> Dict[str, Any]:
        """Call specific model"""
        
        if model == ModelProvider.KIMI:
            return await self._call_kimi_optimized(message)
        else:
            # For now, all fallback to same method
            return await self._call_kimi_optimized(message)
    
    async def _call_kimi_optimized(self, message: str) -> Dict[str, Any]:
        """Optimized Kimi call via Hermes Gateway"""
        
        # Try gateway first (fastest)
        try:
            return await self._call_gateway(message)
        except Exception as e:
            print(f"Gateway failed: {e}, trying bridge...")
            return await self._call_bridge(message)
    
    async def _call_gateway(self, message: str) -> Dict[str, Any]:
        """Call via Hermes Gateway API (port 8080)"""
        
        timeout = aiohttp.ClientTimeout(total=4, connect=1)
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            payload = {
                "task": message,
                "message": message,
                "model": "kimi-for-coding",
                "provider": "kimi-coding",
                "toolsets": ["terminal"]
            }
            
            async with session.post(
                "http://localhost:8080/api/v1/execute",
                json=payload,
                headers={"Authorization": f"Bearer {os.getenv('HERMES_API_KEY', '')}"}
            ) as response:
                
                if response.status == 401:
                    raise Exception("Invalid API key")
                elif response.status == 404:
                    # Kimi API not found - key issue
                    raise Exception("Kimi API unavailable (404)")
                elif response.status != 200:
                    raise Exception(f"HTTP {response.status}")
                
                result = await response.json()
                
                if not result.get("success", False):
                    raise Exception(result.get("error", "Unknown error"))
                
                return {
                    "content": result.get("result", "No result"),
                    "raw_response": result
                }
    
    async def _call_bridge(self, message: str) -> Dict[str, Any]:
        """Fallback: Call via Jarvix Bridge (port 8081) - slower but works"""
        
        timeout = aiohttp.ClientTimeout(total=15, connect=2)
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            payload = {
                "message": message,
                "model": "kimi-for-coding",
                "provider": "kimi-coding"
            }
            
            async with session.post(
                "http://localhost:8081/chat",
                json=payload
            ) as response:
                
                if response.status != 200:
                    raise Exception(f"Bridge returned {response.status}")
                
                result = await response.json()
                
                return {
                    "content": result.get("response", "No response"),
                    "raw_response": result
                }


# Quick test function
async def test_router():
    router = LLMRouter()
    
    print("🚀 Testing FIXED Multi-LLM Router")
    print("=" * 50)
    
    test_messages = [
        "What is Bitcoin?",
        "Should I buy ETH now?",
        "What's my portfolio?"
    ]
    
    for msg in test_messages:
        print(f"\n💬 Testing: {msg}")
        t1 = time.time()
        
        result = await router.route_request(msg, "general_chat")
        
        latency = time.time() - t1
        
        if result["success"]:
            print(f"✅ {result['model_used']} in {latency:.2f}s")
            print(f"📝 {result['response'][:100]}...")
        else:
            print(f"❌ Failed: {result['error']}")

if __name__ == "__main__":
    asyncio.run(test_router())
