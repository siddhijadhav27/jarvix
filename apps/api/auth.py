from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from jose import JWTError, jwt
from datetime import datetime, timedelta
import os

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/token", auto_error=False)

SECRET_KEY = os.getenv("JWT_SECRET", "change-me-in-production")
ALGORITHM = "HS256"

# MOCK API KEYS
VALID_API_KEYS = {
    "test-key-abc123": {"user": "demo", "scopes": ["read"]},
    "admin-key-xyz789": {"user": "admin", "scopes": ["read", "write"]},
}

def verify_api_key(api_key: str = Security(API_KEY_HEADER)):
    if api_key and api_key in VALID_API_KEYS:
        return VALID_API_KEYS[api_key]
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing API key",
        headers={"WWW-Authenticate": "ApiKey"},
    )

def create_jwt(data: dict, expires_minutes: int = 30):
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(minutes=expires_minutes)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_jwt(token: str = Security(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )