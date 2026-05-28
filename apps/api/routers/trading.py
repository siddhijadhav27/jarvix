from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from enum import Enum

router = APIRouter()

class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"

class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"

class TradeRequest(BaseModel):
    symbol: str
    side: OrderSide
    type: OrderType
    amount: float
    price: Optional[float] = None

class TradeResponse(BaseModel):
    id: str
    symbol: str
    side: str
    type: str
    amount: float
    price: float
    status: str
    timestamp: str

@router.post("/execute")
async def execute_trade(request: TradeRequest):
    return {
        "id": "trade_001",
        "symbol": request.symbol,
        "side": request.side,
        "type": request.type,
        "amount": request.amount,
        "price": request.price or 67500.00,
        "status": "filled",
        "timestamp": "2024-01-01T00:00:00Z",
        "message": f"Successfully executed {request.side} order for {request.amount} {request.symbol}"
    }

@router.get("/history")
async def get_trade_history():
    return {
        "trades": [
            {
                "id": "trade_001",
                "symbol": "BTC",
                "side": "buy",
                "type": "market",
                "amount": 0.5,
                "price": 67000.00,
                "status": "filled",
                "timestamp": "2024-01-01T00:00:00Z"
            },
            {
                "id": "trade_002",
                "symbol": "ETH",
                "side": "sell",
                "type": "limit",
                "amount": 2.0,
                "price": 2300.00,
                "status": "filled",
                "timestamp": "2024-01-01T01:00:00Z"
            }
        ]
    }

@router.get("/orders")
async def get_active_orders():
    return {
        "orders": [
            {
                "id": "order_001",
                "symbol": "BTC",
                "side": "buy",
                "type": "limit",
                "amount": 1.0,
                "price": 65000.00,
                "status": "open",
                "created_at": "2024-01-01T00:00:00Z"
            }
        ]
    }

@router.post("/cancel/{order_id}")
async def cancel_order(order_id: str):
    return {
        "message": f"Order {order_id} cancelled successfully",
        "order_id": order_id,
        "status": "cancelled"
    }
