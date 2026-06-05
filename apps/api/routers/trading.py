from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from auth import verify_api_key
from rate_limit import limiter

router = APIRouter(tags=["Trading"])

class TradeRequest(BaseModel):
    asset: str = Field(..., example="BTC")
    action: str = Field(..., pattern="^(buy|sell)$", example="buy")
    amount: float = Field(..., gt=0, example=0.1)

class TradeResponse(BaseModel):
    trade_id: str
    status: str
    asset: str
    amount: float
    price_usd: float

@router.post("/trade",
    response_model=TradeResponse,
    summary="Execute a trade")
@limiter.limit("10/minute")
async def execute_trade(
    request: Request,
    trade: TradeRequest,
    user=Depends(verify_api_key)
):
    # MOCK DATA:Replace with real Binance/exchange execution
    return TradeResponse(
        trade_id="trade_abc123",
        status="executed",
        asset=trade.asset,
        amount=trade.amount,
        price_usd=64000.0
    )