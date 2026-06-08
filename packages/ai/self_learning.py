"""
Self-Learning System for Jarvix
Learns from user feedback and improves intent detection
"""

import json
import os
from typing import Dict, Optional, List
from datetime import datetime

# Learning database path
LEARNING_DB_PATH = os.path.join(os.path.dirname(__file__), "../../data/learning_db.json")

class SelfLearningSystem:
    """
    Self-learning system that improves from user feedback
    """
    
    def __init__(self):
        self.corrections = []  # List of user corrections
        self.learned_patterns = {}  # Learned patterns {pattern: correct_intent}
        self.feedback_history = []  # History of feedback
        self.load_database()
    
    def load_database(self):
        """Load learning database from file"""
        if os.path.exists(LEARNING_DB_PATH):
            try:
                with open(LEARNING_DB_PATH, 'r') as f:
                    data = json.load(f)
                    self.corrections = data.get('corrections', [])
                    self.learned_patterns = data.get('learned_patterns', {})
                    self.feedback_history = data.get('feedback_history', [])
                print(f"[LEARNING] Loaded {len(self.corrections)} corrections, {len(self.learned_patterns)} patterns")
            except Exception as e:
                print(f"[LEARNING] Error loading database: {e}")
                self._init_empty_db()
        else:
            self._init_empty_db()
    
    def _init_empty_db(self):
        """Initialize empty database"""
        os.makedirs(os.path.dirname(LEARNING_DB_PATH), exist_ok=True)
        self.save_database()
    
    def save_database(self):
        """Save learning database to file"""
        try:
            with open(LEARNING_DB_PATH, 'w') as f:
                json.dump({
                    'corrections': self.corrections,
                    'learned_patterns': self.learned_patterns,
                    'feedback_history': self.feedback_history,
                    'last_updated': datetime.now().isoformat()
                }, f, indent=2)
        except Exception as e:
            print(f"[LEARNING] Error saving database: {e}")
    
    def add_correction(self, original_message: str, predicted_intent: str, correct_intent: str, user_id: str = "default"):
        """
        Add user correction
        Example: "Buy ETH" was predicted as "buy" but user meant "sell"
        """
        correction = {
            'timestamp': datetime.now().isoformat(),
            'user_id': user_id,
            'original_message': original_message,
            'predicted_intent': predicted_intent,
            'correct_intent': correct_intent,
            'learned': False
        }
        
        self.corrections.append(correction)
        
        # Immediately learn this pattern
        self._learn_pattern(original_message, correct_intent)
        
        # Save to database
        self.save_database()
        
        print(f"[LEARNING] Learned: '{original_message}' → {correct_intent} (was: {predicted_intent})")
        
        return True
    
    def _learn_pattern(self, message: str, correct_intent: str):
        """Learn a pattern from correction"""
        # Normalize message (lowercase, remove extra spaces)
        normalized = message.lower().strip()
        
        # Store in learned patterns
        if normalized not in self.learned_patterns:
            self.learned_patterns[normalized] = {
                'intent': correct_intent,
                'count': 1,
                'first_seen': datetime.now().isoformat(),
                'last_used': datetime.now().isoformat()
            }
        else:
            # Update existing pattern
            self.learned_patterns[normalized]['count'] += 1
            self.learned_patterns[normalized]['last_used'] = datetime.now().isoformat()
            # If intent changed, update it
            if self.learned_patterns[normalized]['intent'] != correct_intent:
                self.learned_patterns[normalized]['intent'] = correct_intent
                print(f"[LEARNING] Updated pattern: '{normalized}' → {correct_intent}")
    
    def check_learned_pattern(self, message: str) -> Optional[str]:
        """
        Check if we have a learned pattern for this message
        Returns correct intent if found, None otherwise
        """
        normalized = message.lower().strip()
        
        # Exact match
        if normalized in self.learned_patterns:
            pattern_data = self.learned_patterns[normalized]
            pattern_data['last_used'] = datetime.now().isoformat()
            print(f"[LEARNING] Found learned pattern: '{normalized}' → {pattern_data['intent']}")
            return pattern_data['intent']
        
        # No partial match - exact match only to prevent false positives
        
        return None
    
    def get_learning_stats(self) -> Dict:
        """Get learning statistics"""
        return {
            'total_corrections': len(self.corrections),
            'learned_patterns': len(self.learned_patterns),
            'unique_users': len(set(c['user_id'] for c in self.corrections)),
            'most_corrected_intent': self._get_most_corrected_intent(),
            'recent_corrections': self.corrections[-5:] if self.corrections else []
        }
    
    def _get_most_corrected_intent(self) -> Optional[str]:
        """Get the intent that was corrected most often"""
        if not self.corrections:
            return None
        
        intent_counts = {}
        for c in self.corrections:
            intent = c['predicted_intent']
            intent_counts[intent] = intent_counts.get(intent, 0) + 1
        
        return max(intent_counts.items(), key=lambda x: x[1])[0] if intent_counts else None
    
    def get_user_learning_stats(self, user_id: str) -> Dict:
        """Get learning statistics for specific user"""
        user_corrections = [c for c in self.corrections if c['user_id'] == user_id]
        
        return {
            'user_id': user_id,
            'total_corrections': len(user_corrections),
            'learned_patterns': len([p for p in self.learned_patterns.values()]),
            'recent_corrections': user_corrections[-5:] if user_corrections else []
        }

# Global instance
_learning_system = None

def get_learning_system() -> SelfLearningSystem:
    """Get or create global learning system instance"""
    global _learning_system
    if _learning_system is None:
        _learning_system = SelfLearningSystem()
    return _learning_system

# Test
if __name__ == "__main__":
    learning = SelfLearningSystem()
    
    # Test adding correction
    learning.add_correction("Buy ETH", "buy", "sell", "test_user")
    
    # Test checking pattern
    result = learning.check_learned_pattern("Buy ETH")
    print(f"Learned pattern result: {result}")
    
    # Test stats
    stats = learning.get_learning_stats()
    print(f"Learning stats: {stats}")
