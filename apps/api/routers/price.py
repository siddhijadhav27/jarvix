from fastapi import APIRouter, Depends, Request, HTTPException
from auth import verify_api_key
from rate_limit import limiter

router = APIRouter(tags=["Price"])

# MOCK PRICES — replace with real API (Binance, CoinGecko, etc.)
MOCK_PRICES = {
    "BTC": 64000.0,
    "ETH": 3000.0,
    "BNB": 400.0,
    "SOL": 150.0,
    "MATIC": 0.85,
}

@router.get("/price/{asset}",
    summary="Get current price of an asset")
@limiter.limit("60/minute")
async def get_price(
    asset: str,
    request: Request,
    user=Depends(verify_api_key)
):
    asset = asset.upper()
    if asset not in MOCK_PRICES:
        raise HTTPException(
            status_code=404,
            detail=f"Asset '{asset}' not found",
        )
    return {
        "asset": asset,
        "price_usd": MOCK_PRICES[asset],
        "currency": "USD"
    }