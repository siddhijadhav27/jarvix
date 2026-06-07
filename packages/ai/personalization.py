"""
Personalization System for Jarvix
Learns user preferences and customizes responses
"""

import json
import os
from typing import Dict, Optional, List, Any
from datetime import datetime, timedelta
from collections import Counter

# Personalization database path
PERSONALIZATION_DB_PATH = os.path.join(os.path.dirname(__file__), "../../data/personalization_db.json")

class PersonalizationSystem:
    """
    Personalization system that learns user preferences
    """
    
    def __init__(self):
        self.user_profiles = {}  # {user_id: UserProfile}
        self.load_database()
    
    def load_database(self):
        """Load personalization database"""
        if os.path.exists(PERSONALIZATION_DB_PATH):
            try:
                with open(PERSONALIZATION_DB_PATH, 'r') as f:
                    data = json.load(f)
                    self.user_profiles = data.get('user_profiles', {})
                print(f"[PERSONALIZATION] Loaded {len(self.user_profiles)} user profiles")
            except Exception as e:
                print(f"[PERSONALIZATION] Error loading database: {e}")
                self._init_empty_db()
        else:
            self._init_empty_db()
    
    def _init_empty_db(self):
        """Initialize empty database"""
        os.makedirs(os.path.dirname(PERSONALIZATION_DB_PATH), exist_ok=True)
        self.save_database()
    
    def save_database(self):
        """Save personalization database"""
        try:
            with open(PERSONALIZATION_DB_PATH, 'w') as f:
                json.dump({
                    'user_profiles': self.user_profiles,
                    'last_updated': datetime.now().isoformat()
                }, f, indent=2)
        except Exception as e:
            print(f"[PERSONALIZATION] Error saving database: {e}")
    
    def get_or_create_profile(self, user_id: str) -> Dict:
        """Get or create user profile"""
        if user_id not in self.user_profiles:
            self.user_profiles[user_id] = {
                'user_id': user_id,
                'created_at': datetime.now().isoformat(),
                'preferences': {
                    'risk_level': 'medium',  # low, medium, high
                    'preferred_assets': [],
                    'auto_confirm': False,
                    'notifications': True,
                    'response_style': 'witty',  # witty, formal, concise
                    'detail_level': 'standard',  # minimal, standard, detailed
                },
                'behavior': {
                    'total_commands': 0,
                    'intent_counts': {},
                    'asset_counts': {},
                    'time_distribution': {},  # Hour of day
                    'avg_trade_size': 0,
                    'last_active': None,
                },
                'portfolio_history': [],
                'favorite_commands': [],
                'suggestions_enabled': True
            }
            self.save_database()
        
        return self.user_profiles[user_id]
    
    def update_behavior(self, user_id: str, message: str, intent: str, asset: Optional[str] = None, amount: Optional[float] = None):
        """Update user behavior based on command"""
        profile = self.get_or_create_profile(user_id)
        behavior = profile['behavior']
        
        # Update counts
        behavior['total_commands'] += 1
        
        # Intent counts
        if intent not in behavior['intent_counts']:
            behavior['intent_counts'][intent] = 0
        behavior['intent_counts'][intent] += 1
        
        # Asset counts
        if asset:
            if asset not in behavior['asset_counts']:
                behavior['asset_counts'][asset] = 0
            behavior['asset_counts'][asset] += 1
        
        # Time distribution
        hour = datetime.now().hour
        if str(hour) not in behavior['time_distribution']:
            behavior['time_distribution'][str(hour)] = 0
        behavior['time_distribution'][str(hour)] += 1
        
        # Average trade size
        if amount and amount > 0:
            current_avg = behavior['avg_trade_size']
            total_commands = behavior['total_commands']
            behavior['avg_trade_size'] = ((current_avg * (total_commands - 1)) + amount) / total_commands
        
        # Last active
        behavior['last_active'] = datetime.now().isoformat()
        
        # Update favorite commands (top 5)
        self._update_favorite_commands(profile, message)
        
        # Auto-update preferences based on behavior
        self._auto_update_preferences(profile)
        
        self.save_database()
    
    def _update_favorite_commands(self, profile: Dict, message: str):
        """Update favorite commands list"""
        favorites = profile.get('favorite_commands', [])
        
        # Add or update command
        found = False
        for fav in favorites:
            if fav['message'] == message:
                fav['count'] += 1
                fav['last_used'] = datetime.now().isoformat()
                found = True
                break
        
        if not found:
            favorites.append({
                'message': message,
                'count': 1,
                'first_used': datetime.now().isoformat(),
                'last_used': datetime.now().isoformat()
            })
        
        # Sort by count and keep top 5
        favorites.sort(key=lambda x: x['count'], reverse=True)
        profile['favorite_commands'] = favorites[:5]
    
    def _auto_update_preferences(self, profile: Dict):
        """Auto-update preferences based on behavior"""
        behavior = profile['behavior']
        preferences = profile['preferences']
        
        # Update preferred assets (top 3 most used)
        asset_counts = behavior.get('asset_counts', {})
        if asset_counts:
            top_assets = sorted(asset_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            preferences['preferred_assets'] = [asset for asset, count in top_assets]
        
        # Update risk level based on trade sizes
        avg_size = behavior.get('avg_trade_size', 0)
        if avg_size > 1000:
            preferences['risk_level'] = 'high'
        elif avg_size > 100:
            preferences['risk_level'] = 'medium'
        else:
            preferences['risk_level'] = 'low'
        
        # Update response style based on command frequency
        total_commands = behavior.get('total_commands', 0)
        if total_commands > 50:
            preferences['response_style'] = 'concise'  # Experienced user
        elif total_commands > 20:
            preferences['response_style'] = 'witty'  # Regular user
        else:
            preferences['response_style'] = 'detailed'  # New user
    
    def get_personalized_response(self, user_id: str, intent: str, asset: Optional[str] = None) -> str:
        """Get personalized response based on user profile"""
        profile = self.get_or_create_profile(user_id)
        preferences = profile['preferences']
        behavior = profile['behavior']
        
        style = preferences.get('response_style', 'witty')
        detail = preferences.get('detail_level', 'standard')
        
        # Base response
        responses = {
            'buy': {
                'witty': f"Sir, shall I acquire {asset or 'the asset'} for you?",
                'formal': f"Requesting confirmation to purchase {asset or 'asset'}.",
                'concise': f"Buy {asset or 'asset'}? Confirm.",
                'detailed': f"I understand you wish to purchase {asset or 'the specified asset'}. Shall I proceed with the transaction?"
            },
            'sell': {
                'witty': f"Time to offload {asset or 'it'}, sir?",
                'formal': f"Requesting confirmation to sell {asset or 'asset'}.",
                'concise': f"Sell {asset or 'asset'}? Confirm.",
                'detailed': f"I understand you wish to sell {asset or 'the specified asset'}. Shall I proceed with the transaction?"
            },
            'price': {
                'witty': f"Checking the market for {asset or 'you'}, sir.",
                'formal': f"Retrieving current price for {asset or 'asset'}.",
                'concise': f"{asset or 'Asset'}: $1,998",
                'detailed': f"Allow me to check the current market price for {asset or 'the specified asset'}."
            },
            'portfolio': {
                'witty': "Admiring your holdings, sir?",
                'formal': "Retrieving portfolio information.",
                'concise': "Portfolio: $311,342",
                'detailed': "I shall retrieve your complete portfolio information."
            }
        }
        
        # Get response for intent and style
        intent_responses = responses.get(intent, responses['price'])
        response = intent_responses.get(style, intent_responses['witty'])
        
        # Add personalization details
        if detail == 'detailed' and behavior['total_commands'] > 10:
            # Add user-specific insight
            top_asset = self._get_top_asset(profile)
            if top_asset:
                response += f" I notice you frequently trade {top_asset}."
        
        return response
    
    def _get_top_asset(self, profile: Dict) -> Optional[str]:
        """Get user's most traded asset"""
        asset_counts = profile['behavior'].get('asset_counts', {})
        if asset_counts:
            return max(asset_counts.items(), key=lambda x: x[1])[0]
        return None
    
    def get_suggestions(self, user_id: str) -> List[Dict]:
        """Get personalized suggestions for user"""
        profile = self.get_or_create_profile(user_id)
        behavior = profile['behavior']
        suggestions = []
        
        # Suggest based on favorite commands
        favorites = profile.get('favorite_commands', [])
        if favorites:
            top_fav = favorites[0]
            suggestions.append({
                'type': 'favorite',
                'message': f"You often use: '{top_fav['message']}'",
                'command': top_fav['message']
            })
        
        # Suggest based on time patterns
        time_dist = behavior.get('time_distribution', {})
        if time_dist:
            current_hour = datetime.now().hour
            # Check if user is active at this time
            if str(current_hour) in time_dist:
                suggestions.append({
                    'type': 'time',
                    'message': f"You usually trade around {current_hour}:00"
                })
        
        # Suggest based on preferred assets
        preferred = profile['preferences'].get('preferred_assets', [])
        if preferred:
            suggestions.append({
                'type': 'asset',
                'message': f"Your favorite asset: {preferred[0]}"
            })
        
        # Suggest based on inactivity
        last_active = behavior.get('last_active')
        if last_active:
            last_time = datetime.fromisoformat(last_active)
            days_inactive = (datetime.now() - last_time).days
            if days_inactive > 7:
                suggestions.append({
                    'type': 're_engagement',
                    'message': f"Welcome back! It's been {days_inactive} days."
                })
        
        return suggestions[:3]  # Return top 3 suggestions
    
    def get_user_insights(self, user_id: str) -> Dict:
        """Get insights about user behavior"""
        profile = self.get_or_create_profile(user_id)
        behavior = profile['behavior']
        
        insights = {
            'user_id': user_id,
            'total_commands': behavior['total_commands'],
            'most_used_intent': self._get_most_used(behavior['intent_counts']),
            'most_traded_asset': self._get_most_used(behavior['asset_counts']),
            'avg_trade_size': round(behavior.get('avg_trade_size', 0), 2),
            'risk_level': profile['preferences']['risk_level'],
            'response_style': profile['preferences']['response_style'],
            'favorite_commands': [f['message'] for f in profile.get('favorite_commands', [])[:3]],
            'suggestions': self.get_suggestions(user_id)
        }
        
        return insights
    
    def _get_most_used(self, counts: Dict) -> Optional[str]:
        """Get most used item from counts"""
        if counts:
            return max(counts.items(), key=lambda x: x[1])[0]
        return None
    
    def update_preferences(self, user_id: str, preferences: Dict):
        """Manually update user preferences"""
        profile = self.get_or_create_profile(user_id)
        profile['preferences'].update(preferences)
        self.save_database()
        return profile['preferences']

# Global instance
_personalization_system = None

def get_personalization_system() -> PersonalizationSystem:
    """Get or create global personalization system instance"""
    global _personalization_system
    if _personalization_system is None:
        _personalization_system = PersonalizationSystem()
    return _personalization_system

# Test
if __name__ == "__main__":
    ps = PersonalizationSystem()
    
    # Test creating profile
    profile = ps.get_or_create_profile("test_user")
    print(f"Profile created: {profile['user_id']}")
    
    # Test updating behavior
    ps.update_behavior("test_user", "Buy ETH", "buy", "ETH", 100)
    ps.update_behavior("test_user", "Buy BTC", "buy", "BTC", 50)
    ps.update_behavior("test_user", "Sell ETH", "sell", "ETH", 25)
    
    # Test personalized response
    response = ps.get_personalized_response("test_user", "buy", "ETH")
    print(f"Personalized response: {response}")
    
    # Test insights
    insights = ps.get_user_insights("test_user")
    print(f"Insights: {insights}")
