"""
Ghost Mode Onboarding for Jarvix
Paper trading with $25,000 virtual cash
"""

import json
import redis
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

GHOST_STARTING_CASH = 25000.0
GHOST_MODE_DURATION_DAYS = 30


class GhostMode:
    """Manages paper trading for new users"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.key_prefix = f"jarvix:ghost:{user_id}"
    
    def _get_key(self, suffix: str) -> str:
        return f"{self.key_prefix}:{suffix}"
    
    def initialize(self) -> Dict[str, Any]:
        """Initialize ghost mode with $25,000 virtual cash"""
        ghost_portfolio = {
            "cash": GHOST_STARTING_CASH,
            "holdings": {},
            "started_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(days=GHOST_MODE_DURATION_DAYS)).isoformat(),
            "total_trades": 0,
            "profit_loss": 0.0,
            "status": "active"
        }
        
        redis_client.set(self._get_key("portfolio"), json.dumps(ghost_portfolio))
        return ghost_portfolio
    
    def get_portfolio(self) -> Optional[Dict[str, Any]]:
        """Get ghost mode portfolio"""
        data = redis_client.get(self._get_key("portfolio"))
        if data:
            return json.loads(data)
        return None
    
    def is_active(self) -> bool:
        """Check if ghost mode is still active"""
        portfolio = self.get_portfolio()
        if not portfolio:
            return False
        
        expires = datetime.fromisoformat(portfolio.get("expires_at", ""))
        return datetime.now() < expires and portfolio.get("status") == "active"
    
    def execute_trade(self, action: str, asset: str, amount: float, price: float) -> Dict[str, Any]:
        """Execute a paper trade"""
        portfolio = self.get_portfolio()
        if not portfolio:
            return {"error": "Ghost mode not initialized"}
        
        if not self.is_active():
            return {"error": "Ghost mode expired"}
        
        total_cost = amount * price
        
        if action == "buy":
            if portfolio["cash"] < total_cost:
                return {"error": f"Insufficient funds. Have ${portfolio['cash']:.2f}, need ${total_cost:.2f}"}
            
            portfolio["cash"] -= total_cost
            
            if asset not in portfolio["holdings"]:
                portfolio["holdings"][asset] = {"amount": 0, "avg_price": 0}
            
            # Update average price
            current = portfolio["holdings"][asset]
            total_amount = current["amount"] + amount
            current["avg_price"] = ((current["amount"] * current["avg_price"]) + (amount * price)) / total_amount
            current["amount"] = total_amount
            
        elif action == "sell":
            if asset not in portfolio["holdings"] or portfolio["holdings"][asset]["amount"] < amount:
                return {"error": f"Insufficient {asset} to sell"}
            
            portfolio["cash"] += total_cost
            portfolio["holdings"][asset]["amount"] -= amount
            
            # Calculate P&L
            avg_price = portfolio["holdings"][asset]["avg_price"]
            pnl = (price - avg_price) * amount
            portfolio["profit_loss"] += pnl
            
            if portfolio["holdings"][asset]["amount"] == 0:
                del portfolio["holdings"][asset]
        
        portfolio["total_trades"] += 1
        
        # Save trade history
        trade = {
            "action": action,
            "asset": asset,
            "amount": amount,
            "price": price,
            "total": total_cost,
            "timestamp": datetime.now().isoformat()
        }
        redis_client.lpush(self._get_key("trades"), json.dumps(trade))
        redis_client.ltrim(self._get_key("trades"), 0, 99)  # Keep last 100
        
        # Update portfolio
        redis_client.set(self._get_key("portfolio"), json.dumps(portfolio))
        
        return {
            "success": True,
            "trade": trade,
            "portfolio": portfolio
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get ghost mode summary"""
        portfolio = self.get_portfolio()
        if not portfolio:
            return {"error": "Ghost mode not initialized"}
        
        # Calculate current value (with demo prices)
        demo_prices = {
            "BTC": 73084, "ETH": 1998, "SOL": 150,
            "ADA": 0.40, "DOGE": 0.16, "XRP": 0.50
        }
        
        holdings_value = 0
        for asset, data in portfolio.get("holdings", {}).items():
            price = demo_prices.get(asset, 0)
            holdings_value += data["amount"] * price
        
        total_value = portfolio["cash"] + holdings_value
        
        return {
            "status": "active" if self.is_active() else "expired",
            "started_at": portfolio["started_at"],
            "expires_at": portfolio["expires_at"],
            "starting_cash": GHOST_STARTING_CASH,
            "current_cash": portfolio["cash"],
            "holdings_value": holdings_value,
            "total_value": total_value,
            "profit_loss": total_value - GHOST_STARTING_CASH,
            "profit_loss_percent": ((total_value - GHOST_STARTING_CASH) / GHOST_STARTING_CASH) * 100,
            "total_trades": portfolio["total_trades"],
            "holdings": portfolio["holdings"]
        }
    
    def get_trades(self, limit: int = 10) -> list:
        """Get recent trades"""
        trades = redis_client.lrange(self._get_key("trades"), 0, limit - 1)
        return [json.loads(t) for t in reversed(trades)]


def get_ghost_mode(user_id: str) -> GhostMode:
    """Get or create ghost mode for user"""
    ghost = GhostMode(user_id)
    if not ghost.get_portfolio():
        ghost.initialize()
    return ghost
