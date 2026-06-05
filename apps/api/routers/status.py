from fastapi import APIRouter, Request
from rate_limit import limiter

router = APIRouter(tags=["System"])

@router.get("/status",
    summary="System health check")
@limiter.limit("60/minute")
async def get_status(request: Request):
    # No auth required for health check
    return {
        "status": "ok",
        "version": "1.0.0",
        "services": {
            "api": "online",
            "database": "online",
            "ai": "online"
        }
    }