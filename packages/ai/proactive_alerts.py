"""
Proactive Alerts for Jarvix
Monitors market conditions and user behavior to send alerts
"""

import json
import redis
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# Demo prices for monitoring
DEMO_PRICES = {
    "BTC": 73084, "ETH": 1998, "SOL": 150,
    "ADA": 0.40, "DOGE": 0.16, "XRP": 0.50
}

class ProactiveAlertManager:
    """Manages proactive alerts for users"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.key_prefix = f"jarvix:alerts:{user_id}"
    
    def _get_key(self, suffix: str) -> str:
        return f"{self.key_prefix}:{suffix}"
    
    def create_alert(self, alert_type: str, message: str, priority: str = "medium", 
                    data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create a new alert"""
        alert = {
            "id": f"alert_{datetime.now().timestamp()}",
            "type": alert_type,
            "message": message,
            "priority": priority,  # low, medium, high, critical
            "data": data or {},
            "created_at": datetime.now().isoformat(),
            "read": False
        }
        
        # Store alert
        redis_client.lpush(self._get_key("list"), json.dumps(alert))
        redis_client.ltrim(self._get_key("list"), 0, 99)  # Keep last 100
        
        # Update unread count
        redis_client.incr(self._get_key("unread_count"))
        
        return alert
    
    def get_alerts(self, limit: int = 10, include_read: bool = False) -> List[Dict[str, Any]]:
        """Get recent alerts"""
        alerts = redis_client.lrange(self._get_key("list"), 0, limit - 1)
        result = []
        for alert_json in reversed(alerts):
            alert = json.loads(alert_json)
            if include_read or not alert.get("read", False):
                result.append(alert)
        return result
    
    def mark_read(self, alert_id: str) -> bool:
        """Mark alert as read"""
        alerts = redis_client.lrange(self._get_key("list"), 0, -1)
        for i, alert_json in enumerate(alerts):
            alert = json.loads(alert_json)
            if alert["id"] == alert_id:
                alert["read"] = True
                redis_client.lset(self._get_key("list"), i, json.dumps(alert))
                redis_client.decr(self._get_key("unread_count"))
                return True
        return False
    
    def get_unread_count(self) -> int:
        """Get unread alert count"""
        count = redis_client.get(self._get_key("unread_count"))
        return int(count) if count else 0
    
    def check_market_alerts(self) -> List[Dict[str, Any]]:
        """Check for market-related alerts"""
        alerts = []
        
        # Check for significant price movements (>5%)
        for asset, price in DEMO_PRICES.items():
            # Simulate random price change for demo
            import random
            change_pct = random.uniform(-8, 8)
            
            if abs(change_pct) > 5:
                direction = "up" if change_pct > 0 else "down"
                alerts.append(self.create_alert(
                    alert_type="market_movement",
                    message=f"{asset} is {direction} {abs(change_pct):.1f}%!",
                    priority="high" if abs(change_pct) > 10 else "medium",
                    data={"asset": asset, "change_pct": change_pct, "price": price}
                ))
        
        return alerts
    
    def check_behavioral_alerts(self, message: str, intent: str) -> Optional[Dict[str, Any]]:
        """Check for behavioral alerts based on user message"""
        message_lower = message.lower()
        
        # Panic selling alert
        if intent == "sell" and any(w in message_lower for w in ["crash", "dump", "panic", "everything"]):
            return self.create_alert(
                alert_type="behavioral_warning",
                message="Panic selling detected. Consider waiting 10 minutes before executing.",
                priority="high",
                data={"emotion": "panic", "action": "sell"}
            )
        
        # FOMO buying alert
        if intent == "buy" and any(w in message_lower for w in ["moon", "dont miss", "fomo", "urgent"]):
            return self.create_alert(
                alert_type="behavioral_warning",
                message="FOMO buying detected. Consider setting a limit order instead of market buy.",
                priority="medium",
                data={"emotion": "fomo", "action": "buy"}
            )
        
        return None
    
    def check_portfolio_alerts(self, portfolio: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for portfolio-related alerts"""
        alerts = []
        
        total_value = portfolio.get("total_value", 0)
        
        # Alert if portfolio drops >10%
        change_24h = portfolio.get("total_change_24h", 0)
        if change_24h < -10:
            alerts.append(self.create_alert(
                alert_type="portfolio_drop",
                message=f"Portfolio down {abs(change_24h):.1f}% today. Consider reviewing positions.",
                priority="critical",
                data={"change_24h": change_24h, "total_value": total_value}
            ))
        
        # Alert if portfolio up >20%
        elif change_24h > 20:
            alerts.append(self.create_alert(
                alert_type="portfolio_gain",
                message=f"Portfolio up {change_24h:.1f}% today! Consider taking some profits.",
                priority="medium",
                data={"change_24h": change_24h, "total_value": total_value}
            ))
        
        return alerts


def get_alert_manager(user_id: str) -> ProactiveAlertManager:
    """Get alert manager for user"""
    return ProactiveAlertManager(user_id)
