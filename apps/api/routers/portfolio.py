from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List

router = APIRouter()

class Asset(BaseModel):
    symbol: str
    name: str
    balance: float
    price_usd: float
    value_usd: float
    allocation: float
    change_24h: float

class PortfolioSummary(BaseModel):
    total_value_usd: float
    total_change_24h: float
    total_change_percentage: float
    assets: List[Asset]

@router.get("/")
async def get_portfolio():
    return {
        "total_value_usd": 124592.45,
        "total_change_24h": 6234.12,
        "total_change_percentage": 5.2,
        "assets": [
            {
                "symbol": "BTC",
                "name": "Bitcoin",
                "balance": 1.5,
                "price_usd": 67500.00,
                "value_usd": 101250.00,
                "allocation": 81.3,
                "change_24h": 3.2
            },
            {
                "symbol": "ETH",
                "name": "Ethereum",
                "balance": 10.0,
                "price_usd": 2250.00,
                "value_usd": 22500.00,
                "allocation": 18.1,
                "change_24h": 1.8
            },
            {
                "symbol": "USDC",
                "name": "USD Coin",
                "balance": 842.45,
                "price_usd": 1.00,
                "value_usd": 842.45,
                "allocation": 0.6,
                "change_24h": 0.0
            }
        ]
    }

@router.get("/assets")
async def get_assets():
    return {
        "assets": [
            {"symbol": "BTC", "name": "Bitcoin", "price": 67500.00, "change_24h": 3.2},
            {"symbol": "ETH", "name": "Ethereum", "price": 2250.00, "change_24h": 1.8},
            {"symbol": "SOL", "name": "Solana", "price": 145.00, "change_24h": 8.4},
            {"symbol": "BNB", "name": "Binance Coin", "price": 590.00, "change_24h": -0.5}
        ]
    }

@router.post("/rebalance")
async def rebalance_portfolio():
    return {
        "message": "Portfolio rebalanced successfully",
        "new_allocation": {
            "BTC": 70,
            "ETH": 25,
            "USDC": 5
        },
        "tx_hash": "0x..."
    }