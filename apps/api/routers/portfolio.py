from fastapi import APIRouter, Depends, Request
from auth import verify_api_key
from rate_limit import limiter

router = APIRouter(tags=["Portfolio"])

@router.get("/portfolio",
    summary="Get portfolio holdings",
    response_description="Current holdings and total value")
@limiter.limit("30/minute")
async def get_portfolio(
    request: Request,
    user=Depends(verify_api_key)
):
    # MOCK DATA: Replace with real blockchain/wallet data
    return {
        "user": user["user"],
        "holdings": [
            {"asset": "BTC", "amount": 0.5, "value_usd": 32000},
            {"asset": "ETH", "amount": 3.2, "value_usd": 9600},
        ],
        "total_usd": 41600
    }