"""
Single source of truth for portfolio data
"""

from dataclasses import dataclass
from typing import Dict

@dataclass
class Holdings:
    btc: float = 0.5
    eth: float = 100.0
    sol: float = 500.0

@dataclass
class Prices:
    btc: float = 73085.0
    eth: float = 1997.95
    sol: float = 152.40

class PortfolioService:
    _instance = None
    holdings: Holdings
    prices: Prices
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.holdings = Holdings()
            cls._instance.prices = Prices()
        return cls._instance
    
    def get_portfolio_value(self) -> Dict:
        btc_value = self.holdings.btc * self.prices.btc
        eth_value = self.holdings.eth * self.prices.eth
        sol_value = self.holdings.sol * self.prices.sol
        total = btc_value + eth_value + sol_value
        
        return {
            "total_value": round(total, 2),
            "holdings": {
                "btc": {"amount": self.holdings.btc, "value": round(btc_value, 2)},
                "eth": {"amount": self.holdings.eth, "value": round(eth_value, 2)},
                "sol": {"amount": self.holdings.sol, "value": round(sol_value, 2)},
            },
            "prices": {
                "btc": self.prices.btc,
                "eth": self.prices.eth,
                "sol": self.prices.sol,
            }
        }
    
    def update_prices(self, prices: Dict):
        self.prices.btc = prices.get("btc", self.prices.btc)
        self.prices.eth = prices.get("eth", self.prices.eth)
        self.prices.sol = prices.get("sol", self.prices.sol)

# Global instance
portfolio = PortfolioService()
