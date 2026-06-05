from fastapi import APIRouter, Depends, Request
from auth import verify_api_key
from rate_limit import limiter

router = APIRouter(tags=["News"])

@router.get("/news",
    summary="Get latest crypto news")
@limiter.limit("30/minute")
async def get_news(
    request: Request,
    user=Depends(verify_api_key)
):
    # MOCK DATA:Replace with real news API (CryptoPanic, NewsAPI, etc.)
    return {
        "articles": [
            {
                "title": "Bitcoin hits new all-time high",
                "source": "CoinDesk",
                "url": "https://coindesk.com",
                "published_at": "2025-06-05T10:00:00Z"
            },
            {
                "title": "Ethereum upgrade scheduled for Q3",
                "source": "CoinTelegraph",
                "url": "https://cointelegraph.com",
                "published_at": "2025-06-05T08:00:00Z"
            }
        ]
    }