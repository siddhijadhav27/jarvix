from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from rate_limit import limiter
from routers import portfolio, trading, price, alert, news, ai, status, webhook

app = FastAPI(
    title="Jarvix API",
    version="1.0.0",
    description="REST API for Jarvix AI-powered crypto command center",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    openapi_url="/api/v1/openapi.json"
)

# Rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# API versioning prefix
PREFIX = "/api/v1"
app.include_router(portfolio.router, prefix=PREFIX)
app.include_router(trading.router, prefix=PREFIX)
app.include_router(price.router,     prefix=PREFIX)
app.include_router(alert.router,     prefix=PREFIX)
app.include_router(news.router,      prefix=PREFIX)
app.include_router(ai.router,     prefix=PREFIX)
app.include_router(status.router,    prefix=PREFIX)
app.include_router(webhook.router,   prefix=PREFIX)

# Error handling
@app.exception_handler(RequestValidationError)
async def validation_error_handler(req: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation failed",
            "detail": exc.errors(),
            "code": "VALIDATION_ERROR"
        }
    )

@app.exception_handler(Exception)
async def global_error_handler(req: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "code": "INTERNAL_ERROR"
        }
    )