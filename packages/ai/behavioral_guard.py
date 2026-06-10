# behavioral_guard.py
"""Behavioral Finance Guard — detects emotional trading patterns"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from enum import Enum

from storage import get_storage
from profile import UserProfile


class EmotionalPattern(Enum):
    """Types of emotional trading patterns"""
    PANIC_SELLING = "panic_selling"
    FOMO_BUYING = "fomo_buying"
    REVENGE_TRADING = "revenge_trading"
    OVERCONFIDENCE = "overconfidence"
    NONE = "none"


class BehavioralGuard:
    """
    Detects and prevents emotional trading decisions.
    
    Patterns detected:
    - Panic Selling: Selling >50% after price drop
    - FOMO Buying: Buying after +15% pump
    - Revenge Trading: Trading after recent loss
    - Overconfidence: Position size 5x+ usual
    """
    
    # Detection thresholds
    PANIC_SELL_THRESHOLD = 0.5  # Sell >50% of holding
    PANIC_DROP_THRESHOLD = -0.10  # After -10% drop
    FOMO_PUMP_THRESHOLD = 0.15  # After +15% pump
    REVENGE_WINDOW_HOURS = 2  # Within 2 hours of loss
    OVERCONFIDENCE_MULTIPLIER = 5  # 5x usual size
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.storage = get_storage()
        self.profile = UserProfile(user_id)
    
    # ─── Pattern Detection ─────────────────────────────
    
    def check_trade(self, intent: str, asset: str, amount: float, 
                    price: float, portfolio: Optional[Dict] = None,
                    market_change: Optional[float] = None) -> Dict[str, Any]:
        """
        Check a trade for emotional patterns.
        Returns risk assessment with warnings.
        """
        warnings = []
        risk_score = 0
        patterns = []
        
        # Check panic selling
        if intent == "sell":
            panic = self._check_panic_selling(asset, amount, portfolio, market_change)
            if panic["detected"]:
                warnings.append(panic["message"])
                risk_score += panic["risk"]
                patterns.append(EmotionalPattern.PANIC_SELLING.value)
        
        # Check FOMO buying
        if intent == "buy":
            fomo = self._check_fomo_buying(asset, market_change)
            if fomo["detected"]:
                warnings.append(fomo["message"])
                risk_score += fomo["risk"]
                patterns.append(EmotionalPattern.FOMO_BUYING.value)
        
        # Check revenge trading
        revenge = self._check_revenge_trading()
        if revenge["detected"]:
            warnings.append(revenge["message"])
            risk_score += revenge["risk"]
            patterns.append(EmotionalPattern.REVENGE_TRADING.value)
        
        # Check overconfidence
        overconf = self._check_overconfidence(asset, amount)
        if overconf["detected"]:
            warnings.append(overconf["message"])
            risk_score += overconf["risk"]
            patterns.append(EmotionalPattern.OVERCONFIDENCE.value)
        
        return {
            "allowed": risk_score < 70,
            "risk_score": min(risk_score, 100),
            "patterns": patterns,
            "warnings": warnings,
            "requires_confirmation": risk_score >= 50,
            "timestamp": datetime.now().isoformat()
        }
    
    def _check_panic_selling(self, asset: str, amount: float,
                             portfolio: Optional[Dict],
                             market_change: Optional[float]) -> Dict:
        """Detect panic selling after price drop"""
        
        # Check if selling large portion
        if portfolio and asset in portfolio:
            holding = portfolio[asset].get("amount", 0)
            if holding > 0 and amount / holding > self.PANIC_SELL_THRESHOLD:
                # Check if price recently dropped
                if market_change and market_change < self.PANIC_DROP_THRESHOLD:
                    return {
                        "detected": True,
                        "risk": 55,  # Increased from 40 to trigger confirmation
                        "message": (
                            f"⚠️ PANIC SELLING DETECTED: You're selling "
                            f"{(amount/holding)*100:.0f}% of your {asset} "
                            f"after a {abs(market_change)*100:.0f}% drop. "
                            f"Consider waiting for recovery."
                        )
                    }
        
        return {"detected": False, "risk": 0, "message": ""}
    
    def _check_fomo_buying(self, asset: str, 
                           market_change: Optional[float]) -> Dict:
        """Detect FOMO buying after price pump"""
        
        if market_change and market_change > self.FOMO_PUMP_THRESHOLD:
            return {
                "detected": True,
                "risk": 35,
                "message": (
                    f"⚠️ FOMO DETECTED: {asset} is up {market_change*100:.0f}% "
                    f"recently. Buying after a pump often leads to losses. "
                    f"Consider waiting for a pullback."
                )
            }
        
        return {"detected": False, "risk": 0, "message": ""}
    
    def _check_revenge_trading(self) -> Dict:
        """Detect revenge trading after recent loss"""
        
        # Check recent trade history
        recent_loss = self._get_recent_loss()
        
        if recent_loss:
            return {
                "detected": True,
                "risk": 30,
                "message": (
                    f"⚠️ REVENGE TRADING DETECTED: You had a recent loss "
                    f"of ${abs(recent_loss):.2f}. Trading emotionally after "
                    f"losses often leads to bigger losses. Take a break."
                )
            }
        
        return {"detected": False, "risk": 0, "message": ""}
    
    def _check_overconfidence(self, asset: str, amount: float) -> Dict:
        """Detect unusually large position sizes"""
        
        usual = self.profile.suggest_amount(asset)
        
        if usual and amount > usual * self.OVERCONFIDENCE_MULTIPLIER:
            return {
                "detected": True,
                "risk": 25,
                "message": (
                    f"⚠️ OVERCONFIDENCE DETECTED: This trade ({amount}) is "
                    f"{amount/usual:.0f}x your usual size ({usual}). "
                    f"Consider reducing position size."
                )
            }
        
        return {"detected": False, "risk": 0, "message": ""}
    
    # ─── Helpers ───────────────────────────────────────
    
    def _get_recent_loss(self) -> Optional[float]:
        """Check for recent trading losses"""
        # This would query trade history from storage
        # For now, simplified check
        return None  # Placeholder
    
    def get_stats(self) -> Dict[str, Any]:
        """Get guard statistics"""
        return {
            "user_id": self.user_id,
            "patterns_tracked": [p.value for p in EmotionalPattern],
            "thresholds": {
                "panic_sell": self.PANIC_SELL_THRESHOLD,
                "panic_drop": self.PANIC_DROP_THRESHOLD,
                "fomo_pump": self.FOMO_PUMP_THRESHOLD,
                "revenge_window": self.REVENGE_WINDOW_HOURS,
                "overconfidence": self.OVERCONFIDENCE_MULTIPLIER
            }
        }


# Test
if __name__ == "__main__":
    print("🧪 Behavioral Guard Tests")
    print("=" * 60)
    
    # Test 1: Panic selling
    print("\n1. Panic Selling Detection")
    guard = BehavioralGuard("test_user")
    result = guard.check_trade(
        intent="sell",
        asset="ETH",
        amount=5.0,
        price=2000,
        portfolio={"ETH": {"amount": 10.0}},
        market_change=-0.15
    )
    print(f"   Risk Score: {result['risk_score']}")
    print(f"   Patterns: {result['patterns']}")
    for warning in result['warnings']:
        print(f"   Warning: {warning[:80]}")
    
    # Test 2: FOMO buying
    print("\n2. FOMO Buying Detection")
    guard2 = BehavioralGuard("test_user_2")
    result2 = guard2.check_trade(
        intent="buy",
        asset="SOL",
        amount=100.0,
        price=150,
        market_change=0.20
    )
    print(f"   Risk Score: {result2['risk_score']}")
    print(f"   Patterns: {result2['patterns']}")
    for warning in result2['warnings']:
        print(f"   Warning: {warning[:80]}")
    
    # Test 3: Normal trade (no pattern)
    print("\n3. Normal Trade (No Pattern)")
    guard3 = BehavioralGuard("test_user_3")
    # First establish usual amount
    guard3.profile.learn_from_trade("ETH", 0.5, 1000)
    
    result3 = guard3.check_trade(
        intent="buy",
        asset="ETH",
        amount=0.5,
        price=2000,
        market_change=0.02
    )
    print(f"   Risk Score: {result3['risk_score']}")
    print(f"   Patterns: {result3['patterns']}")
    print(f"   Warnings: {len(result3['warnings'])}")
    
    # Test 4: Overconfidence
    print("\n4. Overconfidence Detection")
    guard4 = BehavioralGuard("test_user_4")
    guard4.profile.learn_from_trade("BTC", 0.1, 5000)
    
    result4 = guard4.check_trade(
        intent="buy",
        asset="BTC",
        amount=1.0,  # 10x usual
        price=50000,
        market_change=0.05
    )
    print(f"   Risk Score: {result4['risk_score']}")
    print(f"   Patterns: {result4['patterns']}")
    for warning in result4['warnings']:
        print(f"   Warning: {warning[:80]}")
    
    print("\n✅ Behavioral Guard tests complete!")
