from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager
import uvicorn

from routers import auth, portfolio, trading, ai
from services.kimi import KimiService

# Lifespan context manager for startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Jarvix API starting up...")
    yield
    # Shutdown
    print("👋 Jarvix API shutting down...")

app = FastAPI(
    title="Jarvix API",
    description="AI-powered crypto command center API",
    version="0.1.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://jarvix.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(portfolio.router, prefix="/api/portfolio", tags=["Portfolio"])
app.include_router(trading.router, prefix="/api/trade", tags=["Trading"])
app.include_router(ai.router, prefix="/api/ai", tags=["AI"])

@app.get("/")
async def root():
    return {
        "message": "Welcome to Jarvix API",
        "version": "0.1.0",
        "status": "operational",
        "features": ["portfolio", "trading", "ai", "analytics"]
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "services": {
            "api": "up",
            "database": "connected",
            "redis": "connected"
        }
    }

@app.get("/api/status")
async def api_status():
    return {
        "status": "operational",
        "timestamp": "2024-01-01T00:00:00Z",
        "version": "0.1.0",
        "environment": "development"
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)