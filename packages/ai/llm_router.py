"""
JARVIX Multi-LLM Router
Routes AI requests to the best available model with automatic fallback
"""

import os
import asyncio
import aiohttp
from typing import Optional, Dict, Any, List
from enum import Enum
import json

class ModelProvider(Enum):
    KIMI = "kimi"
    CLAUDE = "claude"
    GPT4 = "gpt4"
    GEMINI = "gemini"

class LLMRouter:
    """
    Intelligent router that selects the best LLM for each task
    and automatically falls back if one fails
    """
    
    def __init__(self):
        # Model configurations
        self.models = {
            ModelProvider.KIMI: {
                "name": "kimi-for-coding",
                "base_url": "https://api.moonshot.cn/v1",
                "api_key": os.getenv("KIMI_API_KEY", ""),
                "priority": 1,  # Primary
                "strengths": ["coding", "quick_response", "cost_effective"],
                "timeout": 30
            },
            ModelProvider.CLAUDE: {
                "name": "claude-3-opus",
                "base_url": "https://api.anthropic.com/v1",
                "api_key": os.getenv("ANTHROPIC_API_KEY", ""),
                "priority": 2,  # Fallback 1
                "strengths": ["reasoning", "analysis", "complex_tasks"],
                "timeout": 45
            },
            ModelProvider.GPT4: {
                "name": "gpt-4",
                "base_url": "https://api.openai.com/v1",
                "api_key": os.getenv("OPENAI_API_KEY", ""),
                "priority": 3,  # Fallback 2
                "strengths": ["creativity", "general_knowledge", "conversation"],
                "timeout": 30
            },
            ModelProvider.GEMINI: {
                "name": "gemini-pro",
                "base_url": "https://generativelanguage.googleapis.com/v1",
                "api_key": os.getenv("GEMINI_API_KEY", ""),
                "priority": 4,  # Fallback 3
                "strengths": ["multimodal", "long_context"],
                "timeout": 30
            }
        }
        
        # Task-to-model mapping
        self.task_routing = {
            "trading_strategy": ModelProvider.CLAUDE,
            "market_analysis": ModelProvider.CLAUDE,
            "risk_assessment": ModelProvider.CLAUDE,
            "quick_response": ModelProvider.KIMI,
            "portfolio_check": ModelProvider.KIMI,
            "price_query": ModelProvider.KIMI,
            "creative_content": ModelProvider.GPT4,
            "user_onboarding": ModelProvider.GPT4,
            "general_chat": ModelProvider.KIMI,
            "code_generation": ModelProvider.KIMI,
            "default": ModelProvider.KIMI
        }
        
        # Health status tracking
        self.model_health = {model: True for model in ModelProvider}
        self.last_failure = {model: None for model in ModelProvider}
    
    def get_model_for_task(self, task_type: str) -> ModelProvider:
        """Select the best model for a given task type"""
        if task_type in self.task_routing:
            preferred = self.task_routing[task_type]
            # Check if preferred model is healthy
            if self.model_health[preferred]:
                return preferred
        
        # Fallback to first healthy model by priority
        for model in sorted(ModelProvider, key=lambda m: self.models[m]["priority"]):
            if self.model_health[model]:
                return model
        
        # Last resort - return default even if unhealthy
        return ModelProvider.KIMI
    
    async def route_request(
        self, 
        message: str, 
        task_type: str = "default",
        conversation_id: Optional[str] = None,
        context: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Route a request to the best available model
        
        Args:
            message: User's message
            task_type: Type of task (trading_strategy, quick_response, etc.)
            conversation_id: Optional conversation ID for context
            context: Optional conversation history
            
        Returns:
            Dict with response, model used, and metadata
        """
        # Select primary model
        primary_model = self.get_model_for_task(task_type)
        
        # Try primary model, then fallbacks
        models_to_try = [primary_model] + [
            m for m in ModelProvider 
            if m != primary_model and self.model_health[m]
        ]
        
        last_error = None
        
        for model in models_to_try:
            try:
                result = await self._call_model(model, message, context)
                
                # Mark model as healthy on success
                self.model_health[model] = True
                
                return {
                    "success": True,
                    "response": result["content"],
                    "model_used": model.value,
                    "model_name": self.models[model]["name"],
                    "task_type": task_type,
                    "conversation_id": conversation_id,
                    "latency_ms": result.get("latency_ms", 0),
                    "fallback_used": model != primary_model
                }
                
            except Exception as e:
                last_error = str(e)
                self.model_health[model] = False
                self.last_failure[model] = asyncio.get_event_loop().time()
                
                # Log the failure
                print(f"⚠️ Model {model.value} failed: {e}")
                continue
        
        # All models failed
        return {
            "success": False,
            "error": f"All models failed. Last error: {last_error}",
            "model_used": None,
            "task_type": task_type
        }
    
    async def _call_model(
        self, 
        model: ModelProvider, 
        message: str, 
        context: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """Call a specific model API"""
        
        config = self.models[model]
        
        # For now, use Hermes Bridge as primary (Kimi)
        if model == ModelProvider.KIMI:
            return await self._call_hermes_bridge(message, context)
        
        # TODO: Implement direct API calls for other models
        # For now, fallback to Hermes Bridge for all
        return await self._call_hermes_bridge(message, context)
    
    async def _call_hermes_bridge(
        self, 
        message: str, 
        context: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """Call Kimi through Hermes Bridge (localhost:8081)"""
        
        import time
        start_time = time.time()
        
        async with aiohttp.ClientSession() as session:
            payload = {
                "message": message,
                "model": "kimi-for-coding",
                "provider": "kimi-coding"
            }
            
            if context:
                payload["context"] = context
            
            async with session.post(
                "http://localhost:8081/chat",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status != 200:
                    raise Exception(f"Hermes Bridge returned {response.status}")
                
                result = await response.json()
                
                latency_ms = int((time.time() - start_time) * 1000)
                
                return {
                    "content": result.get("response", "No response"),
                    "latency_ms": latency_ms,
                    "raw_response": result
                }
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of all models"""
        health_status = {}
        
        for model in ModelProvider:
            try:
                # Quick ping to check if model is responsive
                await self._call_model(model, "ping", None)
                health_status[model.value] = "healthy"
                self.model_health[model] = True
            except Exception as e:
                health_status[model.value] = f"unhealthy: {str(e)}"
                self.model_health[model] = False
        
        return {
            "overall_status": "healthy" if any(self.model_health.values()) else "critical",
            "models": health_status,
            "primary_model": self.get_model_for_task("default").value
        }
    
    def get_routing_info(self) -> Dict[str, Any]:
        """Get current routing configuration"""
        return {
            "task_routing": {k: v.value for k, v in self.task_routing.items()},
            "model_health": {k.value: v for k, v in self.model_health.items()},
            "model_priorities": {k.value: v["priority"] for k, v in self.models.items()},
            "model_strengths": {k.value: v["strengths"] for k, v in self.models.items()}
        }


# Singleton instance
_router = None

def get_router() -> LLMRouter:
    """Get or create the LLM Router singleton"""
    global _router
    if _router is None:
        _router = LLMRouter()
    return _router


# Convenience function for direct usage
async def route_ai_request(
    message: str, 
    task_type: str = "default",
    conversation_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Quick function to route an AI request
    
    Usage:
        result = await route_ai_request("What's my portfolio?", "portfolio_check")
        print(result["response"])
    """
    router = get_router()
    return await router.route_request(message, task_type, conversation_id)


if __name__ == "__main__":
    # Test the router
    async def test():
        router = get_router()
        
        print("🧠 JARVIX Multi-LLM Router")
        print("=" * 50)
        
        # Health check
        health = await router.health_check()
        print(f"\nHealth Status: {health['overall_status']}")
        for model, status in health['models'].items():
            print(f"  {model}: {status}")
        
        # Test routing
        print("\n📝 Testing Task Routing:")
        test_tasks = [
            "trading_strategy",
            "quick_response", 
            "creative_content",
            "default"
        ]
        
        for task in test_tasks:
            model = router.get_model_for_task(task)
            print(f"  {task} → {model.value}")
        
        # Test actual request
        print("\n💬 Testing AI Request:")
        result = await router.route_request(
            "What is Bitcoin?",
            task_type="general_chat"
        )
        
        if result["success"]:
            print(f"✅ Model: {result['model_used']}")
            print(f"⏱️  Latency: {result['latency_ms']}ms")
            print(f"🔄 Fallback: {'Yes' if result['fallback_used'] else 'No'}")
            print(f"\nResponse: {result['response'][:200]}...")
        else:
            print(f"❌ Error: {result['error']}")
    
    asyncio.run(test())
