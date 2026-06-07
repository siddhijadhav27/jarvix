"""
LLM Router for Jarvix
Smart routing: Regex → Templates → LLM (only when needed)
"""

from typing import Dict, Optional, Tuple
from .intent import detect_intent_hybrid
from .self_learning import get_learning_system
from .auto_learning import get_auto_learning_system
from .personalization import get_personalization_system

# Commands that NEVER need LLM (instant, free)
REGEX_ONLY_INTENTS = {
    "price", "buy", "sell", "portfolio", "greeting", 
    "advice", "alert", "stop_loss", "take_profit"
}

# Commands that MIGHT need LLM (complex queries)
LLM_CANDIDATE_PATTERNS = [
    "why", "how", "explain", "what if", "should i",
    "news", "analysis", "predict", "forecast",
    "compare", "vs", "versus", "difference between"
]

class LLMRouter:
    """
    Smart router that decides when to use LLM
    """
    
    def __init__(self):
        self.stats = {
            "total_requests": 0,
            "regex_only": 0,
            "template_used": 0,
            "llm_used": 0,
            "cost_saved": 0.0  # Estimated cost savings
        }
    
    def should_use_llm(self, message: str, intent: str) -> Tuple[bool, str]:
        """
        Decide if LLM is needed for this command
        Returns: (use_llm, reason)
        """
        message_lower = message.lower().strip()
        
        # 1. Check if intent is regex-only (no LLM needed)
        if intent in REGEX_ONLY_INTENTS:
            self.stats["regex_only"] += 1
            return (False, f"Intent '{intent}' handled by regex")
        
        # 2. Check for complex query patterns
        for pattern in LLM_CANDIDATE_PATTERNS:
            if pattern in message_lower:
                self.stats["llm_used"] += 1
                return (True, f"Complex query detected: '{pattern}'")
        
        # 3. Check if message is very long (likely complex)
        if len(message) > 50:
            self.stats["llm_used"] += 1
            return (True, "Long message, likely complex query")
        
        # 4. Default: use template
        self.stats["template_used"] += 1
        return (False, "Using template response")
    
    def get_cost_stats(self) -> Dict:
        """Get cost savings statistics"""
        total = self.stats["total_requests"]
        if total == 0:
            return {"message": "No requests yet"}
        
        regex_pct = (self.stats["regex_only"] / total) * 100
        template_pct = (self.stats["template_used"] / total) * 100
        llm_pct = (self.stats["llm_used"] / total) * 100
        
        # Estimate cost savings (assuming $0.002 per LLM call)
        cost_saved = self.stats["cost_saved"]
        
        return {
            "total_requests": total,
            "regex_only": {
                "count": self.stats["regex_only"],
                "percentage": round(regex_pct, 1)
            },
            "template_used": {
                "count": self.stats["template_used"],
                "percentage": round(template_pct, 1)
            },
            "llm_used": {
                "count": self.stats["llm_used"],
                "percentage": round(llm_pct, 1)
            },
            "cost_saved_usd": round(cost_saved, 4),
            "efficiency": f"{100 - llm_pct:.1f}%"
        }
    
    def record_request(self, message: str, intent: str, used_llm: bool):
        """Record a request for stats"""
        self.stats["total_requests"] += 1
        
        if used_llm:
            # Estimate cost saved by NOT using LLM
            self.stats["cost_saved"] += 0.002

# Global instance
_llm_router = None

def get_llm_router() -> LLMRouter:
    """Get or create global LLM router"""
    global _llm_router
    if _llm_router is None:
        _llm_router = LLMRouter()
    return _llm_router
