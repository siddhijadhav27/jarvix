"""
Auto-Learning System for Jarvix
Detects patterns from user behavior without explicit feedback
"""

import json
import os
import re
from typing import Dict, Optional, List, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, Counter

# Auto-learning database path
AUTO_LEARN_DB_PATH = os.path.join(os.path.dirname(__file__), "../../data/auto_learn_db.json")

class AutoLearningSystem:
    """
    Auto-learning system that detects patterns from user behavior
    """
    
    def __init__(self):
        self.user_patterns = {}  # {user_id: {pattern: {intent: count}}}
        self.global_patterns = {}  # {pattern: {intent: count}}
        self.confidence_threshold = 3  # Minimum occurrences to auto-learn
        self.confidence_ratio = 0.7  # 70% of times must be same intent
        self.load_database()
    
    def load_database(self):
        """Load auto-learning database"""
        if os.path.exists(AUTO_LEARN_DB_PATH):
            try:
                with open(AUTO_LEARN_DB_PATH, 'r') as f:
                    data = json.load(f)
                    self.user_patterns = data.get('user_patterns', {})
                    self.global_patterns = data.get('global_patterns', {})
                print(f"[AUTO-LEARN] Loaded {len(self.global_patterns)} global patterns")
            except Exception as e:
                print(f"[AUTO-LEARN] Error loading database: {e}")
                self._init_empty_db()
        else:
            self._init_empty_db()
    
    def _init_empty_db(self):
        """Initialize empty database"""
        os.makedirs(os.path.dirname(AUTO_LEARN_DB_PATH), exist_ok=True)
        self.save_database()
    
    def save_database(self):
        """Save auto-learning database"""
        try:
            with open(AUTO_LEARN_DB_PATH, 'w') as f:
                json.dump({
                    'user_patterns': self.user_patterns,
                    'global_patterns': self.global_patterns,
                    'last_updated': datetime.now().isoformat()
                }, f, indent=2)
        except Exception as e:
            print(f"[AUTO-LEARN] Error saving database: {e}")
    
    def extract_pattern(self, message: str) -> str:
        """
        Extract pattern from message
        Examples:
        - "Buy 100 ETH" → "buy {amount} eth"
        - "Get some BTC" → "get {amount} btc"
        - "What's ETH price?" → "what {asset} price"
        """
        message_lower = message.lower().strip()
        
        # Replace numbers with {amount}
        pattern = re.sub(r'\b\d+(?:\.\d+)?\b', '{amount}', message_lower)
        
        # Replace asset names with {asset}
        assets = ['btc', 'eth', 'sol', 'ada', 'doge', 'xrp', 'dot', 'link', 'avax', 'matic', 'bnb']
        for asset in assets:
            pattern = re.sub(rf'\b{asset}\b', '{asset}', pattern)
        
        # Replace multiple spaces with single space
        pattern = re.sub(r'\s+', ' ', pattern).strip()
        
        return pattern
    
    def record_command(self, user_id: str, message: str, detected_intent: str):
        """
        Record a command for pattern analysis
        Called every time user sends a command
        """
        pattern = self.extract_pattern(message)
        
        # SKIP LEARNING for problematic patterns
        # These patterns are ambiguous and cause false learning
        skip_patterns = [
            '{asset}',  # Too generic
            '{asset} usd',  # Can be PRICE or UNKNOWN
            'dca {asset}',  # Can be BUY or UNKNOWN
            'convert {asset} to {asset}',  # Can be BUY or SELL
            'exchange {asset} for {asset}',  # Can be BUY or SELL
            'trade {asset} for {asset}',  # Can be BUY or SELL
            'swap {asset} for {asset}',  # Can be BUY or SELL
            'should i buy {asset}',  # Can be ADVICE or BUY
            'should i sell {asset}',  # Can be ADVICE or SELL
            'thinking about buying {asset}',  # Can be ADVICE or BUY
            'thinking about selling {asset}',  # Can be ADVICE or SELL
        ]
        
        if pattern in skip_patterns:
            print(f"[AUTO-LEARN] Skipping ambiguous pattern: '{pattern}'")
            return
        
        # Skip if pattern is too generic
        if pattern in ['{asset}', 'buy {asset}', 'sell {asset}']:
            return
        
        # Update user patterns
        if user_id not in self.user_patterns:
            self.user_patterns[user_id] = {}
        
        if pattern not in self.user_patterns[user_id]:
            self.user_patterns[user_id][pattern] = {}
        
        if detected_intent not in self.user_patterns[user_id][pattern]:
            self.user_patterns[user_id][pattern][detected_intent] = 0
        
        self.user_patterns[user_id][pattern][detected_intent] += 1
        
        # Update global patterns
        if pattern not in self.global_patterns:
            self.global_patterns[pattern] = {}
        
        if detected_intent not in self.global_patterns[pattern]:
            self.global_patterns[pattern][detected_intent] = 0
        
        self.global_patterns[pattern][detected_intent] += 1
        
        # Save periodically (every 10 commands)
        total_commands = sum(sum(intents.values()) for intents in self.global_patterns.values())
        if total_commands % 10 == 0:
            self.save_database()
    
    def check_auto_learned_pattern(self, user_id: str, message: str) -> Optional[Tuple[str, float]]:
        """
        Check if we have an auto-learned pattern for this message
        Returns (intent, confidence) or None
        """
        pattern = self.extract_pattern(message)
        
        # Check user-specific patterns first
        if user_id in self.user_patterns and pattern in self.user_patterns[user_id]:
            intent_counts = self.user_patterns[user_id][pattern]
            total = sum(intent_counts.values())
            
            if total >= self.confidence_threshold:
                most_common_intent = max(intent_counts.items(), key=lambda x: x[1])
                intent, count = most_common_intent
                ratio = count / total
                
                if ratio >= self.confidence_ratio:
                    confidence = min(ratio * 0.95, 0.95)  # Cap at 0.95
                    print(f"[AUTO-LEARN] User pattern: '{pattern}' → {intent} ({confidence:.2f})")
                    return (intent, confidence)
        
        # Check global patterns
        if pattern in self.global_patterns:
            intent_counts = self.global_patterns[pattern]
            total = sum(intent_counts.values())
            
            if total >= self.confidence_threshold * 2:  # Higher threshold for global
                most_common_intent = max(intent_counts.items(), key=lambda x: x[1])
                intent, count = most_common_intent
                ratio = count / total
                
                if ratio >= self.confidence_ratio:
                    confidence = min(ratio * 0.90, 0.90)  # Slightly lower for global
                    print(f"[AUTO-LEARN] Global pattern: '{pattern}' → {intent} ({confidence:.2f})")
                    return (intent, confidence)
        
        return None
    
    def get_suggestions(self, user_id: str, message: str) -> List[Dict]:
        """
        Get suggestions for ambiguous commands
        Example: "ETH" could be price or buy
        """
        pattern = self.extract_pattern(message)
        suggestions = []
        
        # Check user patterns
        if user_id in self.user_patterns and pattern in self.user_patterns[user_id]:
            intent_counts = self.user_patterns[user_id][pattern]
            total = sum(intent_counts.values())
            
            for intent, count in sorted(intent_counts.items(), key=lambda x: x[1], reverse=True):
                suggestions.append({
                    'intent': intent,
                    'confidence': count / total,
                    'count': count,
                    'source': 'user_history'
                })
        
        return suggestions
    
    def get_stats(self) -> Dict:
        """Get auto-learning statistics"""
        total_user_patterns = sum(len(patterns) for patterns in self.user_patterns.values())
        total_global_patterns = len(self.global_patterns)
        
        # Count auto-learned patterns (above threshold)
        auto_learned = 0
        for pattern, intents in self.global_patterns.items():
            total = sum(intents.values())
            if total >= self.confidence_threshold * 2:
                most_common = max(intents.items(), key=lambda x: x[1])
                if most_common[1] / total >= self.confidence_ratio:
                    auto_learned += 1
        
        return {
            'total_user_patterns': total_user_patterns,
            'total_global_patterns': total_global_patterns,
            'auto_learned_patterns': auto_learned,
            'unique_users': len(self.user_patterns),
            'confidence_threshold': self.confidence_threshold,
            'confidence_ratio': self.confidence_ratio
        }
    
    def get_user_stats(self, user_id: str) -> Dict:
        """Get auto-learning stats for specific user"""
        if user_id not in self.user_patterns:
            return {
                'user_id': user_id,
                'total_patterns': 0,
                'auto_learned': 0,
                'top_patterns': []
            }
        
        patterns = self.user_patterns[user_id]
        auto_learned = 0
        
        for pattern, intents in patterns.items():
            total = sum(intents.values())
            if total >= self.confidence_threshold:
                most_common = max(intents.items(), key=lambda x: x[1])
                if most_common[1] / total >= self.confidence_ratio:
                    auto_learned += 1
        
        # Get top patterns
        top_patterns = []
        for pattern, intents in sorted(patterns.items(), 
                                      key=lambda x: sum(x[1].values()), 
                                      reverse=True)[:5]:
            total = sum(intents.values())
            most_common = max(intents.items(), key=lambda x: x[1])
            top_patterns.append({
                'pattern': pattern,
                'most_common_intent': most_common[0],
                'count': total,
                'confidence': most_common[1] / total
            })
        
        return {
            'user_id': user_id,
            'total_patterns': len(patterns),
            'auto_learned': auto_learned,
            'top_patterns': top_patterns
        }

# Global instance
_auto_learning_system = None

def get_auto_learning_system() -> AutoLearningSystem:
    """Get or create global auto-learning system instance"""
    global _auto_learning_system
    if _auto_learning_system is None:
        _auto_learning_system = AutoLearningSystem()
    return _auto_learning_system

# Test
if __name__ == "__main__":
    auto_learn = AutoLearningSystem()
    
    # Simulate user behavior
    commands = [
        ("user1", "Get ETH", "buy"),
        ("user1", "Get BTC", "buy"),
        ("user1", "Get SOL", "buy"),
        ("user1", "Dump ETH", "sell"),
        ("user1", "Dump BTC", "sell"),
    ]
    
    for user_id, message, intent in commands:
        auto_learn.record_command(user_id, message, intent)
    
    # Check patterns
    result = auto_learn.check_auto_learned_pattern("user1", "Get ETH")
    print(f"Pattern result: {result}")
    
    stats = auto_learn.get_stats()
    print(f"Stats: {stats}")
