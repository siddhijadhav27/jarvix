# ghost_portfolio.py
"""Ghost Mode Portfolio — 30-day demo with real market data"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from storage import get_storage


class GhostPortfolio:
    """
    Demo portfolio for Ghost Mode onboarding.
    
    Features:
    - $100K starting balance
    - Real market prices for trades
    - 30-day countdown
    - Performance tracking
    - Trade history
    """
    
    STARTING_BALANCE = 100000.00  # $100K demo
    GHOST_DURATION_DAYS = 30
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.storage = get_storage()
        
        # Portfolio state
        self.balance_usd: float = self.STARTING_BALANCE
        self.holdings: Dict[str, float] = {}  # Asset -> Amount
        self.trade_history: List[Dict[str, Any]] = []
        
        # Timer state
        self.created_at: Optional[datetime] = None
        self.expires_at: Optional[datetime] = None
        self.is_active: bool = False
        
        # Load from Redis if exists
        self._load()
    
    # ─── Activation ────────────────────────────────────
    
    def activate(self) -> Dict[str, Any]:
        """Activate ghost mode for 30 days"""
        self.created_at = datetime.now()
        self.expires_at = self.created_at + timedelta(days=self.GHOST_DURATION_DAYS)
        self.is_active = True
        self.balance_usd = self.STARTING_BALANCE
        self.holdings = {}
        self.trade_history = []
        
        self._save()
        
        return {
            "status": "activated",
            "balance": self.balance_usd,
            "expires_at": self.expires_at.isoformat(),
            "days_remaining": self.GHOST_DURATION_DAYS
        }
    
    def deactivate(self):
        """Deactivate ghost mode"""
        self.is_active = False
        self._save()
    
    # ─── Trading ───────────────────────────────────────
    
    def execute_trade(self, asset: str, amount: float,
                      price: float, side: str) -> Dict[str, Any]:
        """
        Execute a demo trade with real market price.
        
        Args:
            asset: Asset symbol (ETH, BTC, etc.)
            amount: Amount to trade
            price: Current market price
            side: "buy" or "sell"
        
        Returns:
            Trade result with updated balance
        """
        if not self.is_active:
            return {"error": "Ghost mode not active"}
        
        if self.is_expired():
            return {"error": "Ghost mode expired"}
        
        asset = asset.upper()
        cost = amount * price
        
        if side == "buy":
            # Check balance
            if cost > self.balance_usd:
                return {
                    "error": "Insufficient demo balance",
                    "balance": self.balance_usd,
                    "required": cost
                }
            
            # Execute buy
            self.balance_usd -= cost
            self.holdings[asset] = self.holdings.get(asset, 0) + amount
            
        elif side == "sell":
            # Check holdings
            current_holding = self.holdings.get(asset, 0)
            if current_holding < amount:
                return {
                    "error": "Insufficient holdings",
                    "holding": current_holding,
                    "requested": amount
                }
            
            # Execute sell
            self.balance_usd += cost
            self.holdings[asset] -= amount
            
            # Remove if zero
            if self.holdings[asset] <= 0:
                del self.holdings[asset]
        
        else:
            return {"error": f"Invalid side: {side}"}
        
        # Record trade
        trade = {
            "asset": asset,
            "amount": amount,
            "price": price,
            "side": side,
            "cost": cost,
            "balance_after": self.balance_usd,
            "timestamp": datetime.now().isoformat()
        }
        self.trade_history.append(trade)
        
        # Save
        self._save()
        
        return {
            "success": True,
            "trade": trade,
            "balance": self.balance_usd,
            "holdings": self.holdings.copy()
        }
    
    # ─── Portfolio Value ───────────────────────────────
    
    def get_portfolio_value(self, current_prices: Dict[str, float]) -> Dict[str, Any]:
        """
        Calculate total portfolio value with current prices.
        
        Args:
            current_prices: Dict of asset -> current price
        
        Returns:
            Portfolio value breakdown
        """
        holdings_value = 0.0
        holdings_detail = {}
        
        for asset, amount in self.holdings.items():
            price = current_prices.get(asset, 0)
            value = amount * price
            holdings_value += value
            
            holdings_detail[asset] = {
                "amount": amount,
                "price": price,
                "value": value
            }
        
        total_value = self.balance_usd + holdings_value
        
        # Calculate P&L
        starting_value = self.STARTING_BALANCE
        pnl = total_value - starting_value
        pnl_percent = (pnl / starting_value) * 100 if starting_value > 0 else 0
        
        return {
            "balance_usd": self.balance_usd,
            "holdings_value": holdings_value,
            "total_value": total_value,
            "pnl": pnl,
            "pnl_percent": pnl_percent,
            "holdings": holdings_detail
        }
    
    # ─── Timer ─────────────────────────────────────────
    
    def get_time_remaining(self) -> Dict[str, Any]:
        """Get time remaining in ghost mode"""
        if not self.is_active or not self.expires_at:
            return {"active": False, "days_remaining": 0}
        
        now = datetime.now()
        if now >= self.expires_at:
            return {"active": False, "days_remaining": 0, "expired": True}
        
        remaining = self.expires_at - now
        days = remaining.days
        hours = remaining.seconds // 3600
        
        return {
            "active": True,
            "days_remaining": days,
            "hours_remaining": hours,
            "expires_at": self.expires_at.isoformat()
        }
    
    def is_expired(self) -> bool:
        """Check if ghost mode has expired"""
        if not self.is_active or not self.expires_at:
            return True
        return datetime.now() >= self.expires_at
    
    def get_day_number(self) -> int:
        """Get current day number (1-30)"""
        if not self.created_at:
            return 0
        
        elapsed = datetime.now() - self.created_at
        return min(elapsed.days + 1, self.GHOST_DURATION_DAYS)
    
    # ─── Reminders ─────────────────────────────────────
    
    def should_remind(self) -> Optional[str]:
        """Check if reminder should be shown"""
        if not self.is_active or self.is_expired():
            return None
        
        day = self.get_day_number()
        
        reminders = {
            7: "🎉 Week 1 complete! You're doing great. Ready to trade for real?",
            14: "📊 Halfway point! Check your performance summary.",
            21: "⏰ 1 week left in demo mode. Don't miss out!",
            25: "🚀 5 days left! Upgrade now to keep your progress.",
            29: "⚡ Final day tomorrow! Last chance to upgrade.",
            30: "🔔 Demo expired. Upgrade to continue trading."
        }
        
        return reminders.get(day)
    
    # ─── Persistence ───────────────────────────────────
    
    def to_dict(self) -> dict:
        """Serialize to dictionary"""
        return {
            "user_id": self.user_id,
            "balance_usd": self.balance_usd,
            "holdings": self.holdings,
            "trade_history": self.trade_history,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_active": self.is_active
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "GhostPortfolio":
        """Deserialize from dictionary"""
        portfolio = cls(data["user_id"])
        portfolio.balance_usd = data.get("balance_usd", cls.STARTING_BALANCE)
        portfolio.holdings = data.get("holdings", {})
        portfolio.trade_history = data.get("trade_history", [])
        
        if data.get("created_at"):
            portfolio.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("expires_at"):
            portfolio.expires_at = datetime.fromisoformat(data["expires_at"])
        
        portfolio.is_active = data.get("is_active", False)
        return portfolio
    
    def save(self):
        """Save to Redis"""
        self._save()
    
    def _save(self):
        """Internal save"""
        key = f"ghost_portfolio:{self.user_id}"
        self.storage.cache_set(key, self.to_dict(), ttl_seconds=86400 * 35)  # 35 days
    
    def _load(self):
        """Load from Redis"""
        key = f"ghost_portfolio:{self.user_id}"
        data = self.storage.cache_get(key)
        if data:
            loaded = GhostPortfolio.from_dict(data)
            self.balance_usd = loaded.balance_usd
            self.holdings = loaded.holdings
            self.trade_history = loaded.trade_history
            self.created_at = loaded.created_at
            self.expires_at = loaded.expires_at
            self.is_active = loaded.is_active
    
    # ─── Stats ─────────────────────────────────────────
    
    def get_stats(self) -> Dict[str, Any]:
        """Get ghost portfolio statistics"""
        timer = self.get_time_remaining()
        
        return {
            "user_id": self.user_id,
            "is_active": self.is_active,
            "balance": self.balance_usd,
            "holdings_count": len(self.holdings),
            "total_trades": len(self.trade_history),
            "days_remaining": timer.get("days_remaining", 0),
            "day_number": self.get_day_number()
        }


# Test
if __name__ == "__main__":
    print("🧪 Ghost Portfolio Tests")
    print("=" * 60)
    
    # Test 1: Activation
    print("\n1. Activate Ghost Mode")
    portfolio = GhostPortfolio("test_user_ghost")
    result = portfolio.activate()
    print(f"   Status: {result['status']}")
    print(f"   Balance: ${result['balance']:,.2f}")
    print(f"   Days: {result['days_remaining']}")
    
    # Test 2: Buy trade
    print("\n2. Buy 1 ETH at $2,000")
    result = portfolio.execute_trade("ETH", 1.0, 2000, "buy")
    print(f"   Success: {result.get('success')}")
    print(f"   Balance: ${result.get('balance', 0):,.2f}")
    print(f"   Holdings: {result.get('holdings', {})}")
    
    # Test 3: Portfolio value
    print("\n3. Portfolio Value (ETH at $2,200)")
    value = portfolio.get_portfolio_value({"ETH": 2200})
    print(f"   Balance: ${value['balance_usd']:,.2f}")
    print(f"   Holdings Value: ${value['holdings_value']:,.2f}")
    print(f"   Total: ${value['total_value']:,.2f}")
    print(f"   P&L: ${value['pnl']:,.2f} ({value['pnl_percent']:+.2f}%)")
    
    # Test 4: Sell trade
    print("\n4. Sell 0.5 ETH at $2,200")
    result = portfolio.execute_trade("ETH", 0.5, 2200, "sell")
    print(f"   Success: {result.get('success')}")
    print(f"   Balance: ${result.get('balance', 0):,.2f}")
    print(f"   Holdings: {result.get('holdings', {})}")
    
    # Test 5: Timer
    print("\n5. Time Remaining")
    timer = portfolio.get_time_remaining()
    print(f"   Active: {timer['active']}")
    print(f"   Days: {timer['days_remaining']}")
    print(f"   Hours: {timer['hours_remaining']}")
    
    # Test 6: Insufficient balance
    print("\n6. Insufficient Balance Test")
    result = portfolio.execute_trade("BTC", 100, 50000, "buy")
    print(f"   Error: {result.get('error')}")
    
    print("\n✅ Ghost Portfolio tests complete!")
