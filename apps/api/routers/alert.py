from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from auth import verify_api_key
from rate_limit import limiter
import time

router = APIRouter(tags=["Alerts"])

alerts_store: list[dict] = []

class AlertRequest(BaseModel):
    asset: str = Field(..., example="BTC")
    condition: str = Field(..., pattern="^(above|below)$", example="above")
    price_usd: float = Field(..., gt=0, example=70000.0)

@router.post("/alert",
    summary="Set a price alert")
@limiter.limit("20/minute")
async def set_alert(
    request: Request,
    alert: AlertRequest,
    user=Depends(verify_api_key)
):
    entry = {
        "alert_id": f"alert_{int(time.time())}",
        "user": user["user"],
        "asset": alert.asset.upper(),
        "condition": alert.condition,
        "price_usd": alert.price_usd,
        "status": "active"
    }
    alerts_store.append(entry)
    return entry