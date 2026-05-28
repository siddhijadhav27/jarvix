from typing import Dict, Any, List
import re

class IntentClassifier:
    """Classify user intent from natural language"""
    
    def __init__(self):
        self.intents = {
            "portfolio_query": ["portfolio", "balance", "assets", "holdings", "net worth"],
            "trade_execute": ["buy", "sell", "trade", "order", "execute"],
            "price_check": ["price", "cost", "value", "how much", "current price"],
            "market_analysis": ["analyze", "trend", "prediction", "forecast", "outlook"],
            "alert_setup": ["alert", "notify", "remind", "watch", "monitor"],
            "help": ["help", "assist", "support", "how to", "what can"]
        }
    
    def classify(self, message: str) -> Dict[str, Any]:
        """Classify intent from message"""
        message_lower = message.lower()
        
        scores = {}
        for intent, keywords in self.intents.items():
            score = sum(1 for keyword in keywords if keyword in message_lower)
            scores[intent] = score / len(keywords)
        
        # Get best matching intent
        best_intent = max(scores, key=scores.get)
        confidence = scores[best_intent]
        
        return {
            "intent": best_intent,
            "confidence": confidence,
            "all_scores": scores,
            "entities": self._extract_entities(message)
        }
    
    def _extract_entities(self, message: str) -> List[Dict[str, str]]:
        """Extract entities like symbols, amounts, etc."""
        entities = []
        
        # Extract crypto symbols
        symbols = re.findall(r'\b(BTC|ETH|SOL|BNB|USDC|USDT)\b', message.upper())
        for symbol in symbols:
            entities.append({"type": "symbol", "value": symbol})
        
        # Extract amounts
        amounts = re.findall(r'(\d+\.?\d*)\s*(BTC|ETH|SOL|USD|USDC)?', message)
        for amount, unit in amounts:
            entities.append({"type": "amount", "value": amount, "unit": unit})
        
        return entities
