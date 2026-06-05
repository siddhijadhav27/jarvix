from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, HttpUrl
from auth import verify_api_key
from rate_limit import limiter
import httpx, time, hashlib, hmac

router = APIRouter(tags=["Webhooks"])

# In production, store in a database
webhook_registry: list[dict] = []

class WebhookRegister(BaseModel):
    url: HttpUrl
    events: list[str]
    secret: str

@router.post("/webhook",
    summary="Register a webhook endpoint")
@limiter.limit("10/minute")
async def register_webhook(
    request: Request,
    payload: WebhookRegister,
    user=Depends(verify_api_key)
):
    entry = {
        "id": f"wh_{int(time.time())}",
        "url": str(payload.url),
        "events": payload.events,
        "secret": payload.secret,
        "user": user["user"]
    }
    webhook_registry.append(entry)
    return {"webhook_id": entry["id"], "status": "registered"}

async def fire_webhooks(event: str, data: dict):
    """Call this from other routers when events happen."""
    for wh in webhook_registry:
        if event in wh["events"]:
            payload = {
                "event": event,
                "data": data,
                "timestamp": int(time.time())
            }
            sig = hmac.new(
                wh["secret"].encode(),
                str(payload).encode(),
                hashlib.sha256
            ).hexdigest()
            headers = {
                "X-Jarvix-Signature": f"sha256={sig}",
                "Content-Type": "application/json"
            }
            async with httpx.AsyncClient() as client:
                try:
                    await client.post(
                        wh["url"],
                        json=payload,
                        headers=headers,
                        timeout=5.0
                    )
                except Exception:
                    pass  # Log failed deliveries in production