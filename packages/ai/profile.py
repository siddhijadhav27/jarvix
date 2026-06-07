# profile.py
"""Learning user profile for Jarvix — persists to Redis"""

from typing import Dict, List, Optional
from datetime import datetime
import json

from storage import get_storage


class UserProfile:
    """
    User profile that LEARNS from behavior — not hardcoded settings.
    
    Key features:
    - usual_amounts: Weighted average of trade sizes per asset
    - risk_tolerance: Inferred from trade behavior (not set manually)
    - trade_counts: Tracks frequency per asset
    - Outlier guard: Prevents one large trade from skewing everything
    """
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.storage = get_storage()
        
        # LEARNED from actual trades
        self.usual_amounts: Dict[str, float] = {}
        # {"ETH": 0.5, "BTC": 0.01}
        
        # INFERRED from behavior
        self.risk_tolerance: str = "unknown"
        # Becomes: "conservative" | "moderate" | "aggressive"
        
        # OBSERVED from history
        self.trade_counts: Dict[str, int] = {}
        # {"ETH": 12, "BTC": 3}
        
        self.total_trades: int = 0
        self.total_volume_usd: float = 0.0
        self.first_trade_at: Optional[str] = None
        self.last_trade_at: Optional[str] = None
        
        # Load from Redis if exists
        self._load()
    
    # ─── Core Learning ─────────────────────────────────
    
    def learn_from_trade(self, asset: str, amount: float, usd_value: float):
        """
        Called after every confirmed trade.
        Updates learned amounts with outlier protection.
        """
        asset = asset.upper()
        
        # Update trade count
        self.trade_counts[asset] = self.trade_counts.get(asset, 0) + 1
        self.total_trades += 1
        self.total_volume_usd += usd_value
        
        # Update timestamps
        now = datetime.now().isoformat()
        if self.first_trade_at is None:
            self.first_trade_at = now
        self.last_trade_at = now
        
        # Update usual amount with outlier guard
        current = self.usual_amounts.get(asset)
        
        if current is None:
            # First trade for this asset
            self.usual_amounts[asset] = amount
        elif amount > current * 5:
            # OUTLIER: New amount is 5x+ usual
            # Learn very little from it (5% weight)
            self.usual_amounts[asset] = current * 0.95 + amount * 0.05
            print(f"[PROFILE] Outlier detected: {amount} {asset} (usual: {current:.4f})")
        else:
            # Normal trade: weighted average (70% old, 30% new)
            self.usual_amounts[asset] = current * 0.7 + amount * 0.3
        
        # Re-infer risk tolerance
        self._infer_risk_tolerance()
        
        # Persist to Redis
        self.save()
    
    def _infer_risk_tolerance(self):
        """
        Infer risk tolerance from trade behavior:
        - Conservative: Small amounts, few assets, low frequency
        - Moderate: Medium amounts, diversified
        - Aggressive: Large amounts, concentrated, high frequency
        """
        if self.total_trades < 3:
            self.risk_tolerance = "unknown"
            return
        
        # Calculate metrics
        avg_trade_size = self.total_volume_usd / self.total_trades if self.total_trades > 0 else 0
        asset_diversity = len(self.trade_counts)
        max_concentration = max(self.trade_counts.values()) / self.total_trades if self.total_trades > 0 else 0
        
        # Scoring (simplified)
        if avg_trade_size > 10000 and max_concentration > 0.6:
            self.risk_tolerance = "aggressive"
        elif avg_trade_size < 1000 and asset_diversity >= 3:
            self.risk_tolerance = "conservative"
        else:
            self.risk_tolerance = "moderate"
    
    # ─── Suggestions ───────────────────────────────────
    
    def suggest_amount(self, asset: str) -> Optional[float]:
        """Suggest trade amount based on learned behavior"""
        asset = asset.upper()
        return self.usual_amounts.get(asset)
    
    def get_favorite_assets(self, limit: int = 3) -> List[str]:
        """Get most traded assets"""
        sorted_assets = sorted(
            self.trade_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return [asset for asset, count in sorted_assets[:limit]]
    
    # ─── Persistence ───────────────────────────────────
    
    def to_dict(self) -> dict:
        """Serialize to dictionary"""
        return {
            "user_id": self.user_id,
            "usual_amounts": self.usual_amounts,
            "risk_tolerance": self.risk_tolerance,
            "trade_counts": self.trade_counts,
            "total_trades": self.total_trades,
            "total_volume_usd": self.total_volume_usd,
            "first_trade_at": self.first_trade_at,
            "last_trade_at": self.last_trade_at,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "UserProfile":
        """Deserialize from dictionary"""
        profile = cls(data["user_id"])
        profile.usual_amounts = data.get("usual_amounts", {})
        profile.risk_tolerance = data.get("risk_tolerance", "unknown")
        profile.trade_counts = data.get("trade_counts", {})
        profile.total_trades = data.get("total_trades", 0)
        profile.total_volume_usd = data.get("total_volume_usd", 0.0)
        profile.first_trade_at = data.get("first_trade_at")
        profile.last_trade_at = data.get("last_trade_at")
        return profile
    
    def save(self):
        """Save to Redis"""
        self.storage.save_profile(self.user_id, self.to_dict())
    
    def _load(self):
        """Load from Redis"""
        data = self.storage.load_profile(self.user_id)
        if data:
            self.usual_amounts = data.get("usual_amounts", {})
            self.risk_tolerance = data.get("risk_tolerance", "unknown")
            self.trade_counts = data.get("trade_counts", {})
            self.total_trades = data.get("total_trades", 0)
            self.total_volume_usd = data.get("total_volume_usd", 0.0)
            self.first_trade_at = data.get("first_trade_at")
            self.last_trade_at = data.get("last_trade_at")
    
    # ─── Stats ─────────────────────────────────────────
    
    def get_stats(self) -> dict:
        """Get profile statistics"""
        return {
            "user_id": self.user_id,
            "risk_tolerance": self.risk_tolerance,
            "total_trades": self.total_trades,
            "total_volume_usd": round(self.total_volume_usd, 2),
            "favorite_assets": self.get_favorite_assets(),
            "usual_amounts": {k: round(v, 4) for k, v in self.usual_amounts.items()},
            "trade_counts": self.trade_counts,
        }


# Test
if __name__ == "__main__":
    print("🧪 UserProfile Tests")
    print("=" * 60)
    
    # Test 1: Create profile
    print("\n1. Create profile for user_123")
    profile = UserProfile("user_123")
    print(f"   Initial: {profile.get_stats()}")
    
    # Test 2: Learn normal trades
    print("\n2. Learn 3 normal ETH trades (0.5 ETH each)")
    for i in range(3):
        profile.learn_from_trade("ETH", 0.5, 1000.0)
    print(f"   Usual ETH: {profile.usual_amounts.get('ETH')}")
    print(f"   Trades: {profile.trade_counts}")
    
    # Test 3: Outlier trade
    print("\n3. Outlier trade (10 ETH — 20x usual)")
    profile.learn_from_trade("ETH", 10.0, 20000.0)
    print(f"   Usual ETH after outlier: {profile.usual_amounts.get('ETH'):.4f}")
    print(f"   Risk: {profile.risk_tolerance}")
    
    # Test 4: Load from Redis
    print("\n4. Load profile from Redis")
    profile2 = UserProfile("user_123")
    print(f"   Loaded usual ETH: {profile2.usual_amounts.get('ETH')}")
    print(f"   Loaded trades: {profile2.trade_counts}")
    
    # Test 5: Persistence check
    print("\n5. Persistence check — data survives reload")
    assert profile2.usual_amounts.get("ETH") == profile.usual_amounts.get("ETH")
    assert profile2.trade_counts.get("ETH") == profile.trade_counts.get("ETH")
    print("   ✅ Data persisted correctly")
    
    # Test 6: Suggest amount
    print("\n6. Suggest amount for ETH")
    suggested = profile.suggest_amount("ETH")
    print(f"   Suggested: {suggested} ETH")
    
    print("\n✅ All profile tests passed!")
