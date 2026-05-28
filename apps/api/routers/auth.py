from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

router = APIRouter()

class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str

@router.post("/login")
async def login(request: LoginRequest):
    return {
        "access_token": "jwt_token_here",
        "token_type": "bearer",
        "user": {
            "id": "1",
            "email": request.email,
            "name": "Siddhi Rajan Jadhav"
        }
    }

@router.post("/register")
async def register(request: RegisterRequest):
    return {
        "message": "User registered successfully",
        "user": {
            "id": "1",
            "email": request.email,
            "name": request.name
        }
    }

@router.post("/refresh")
async def refresh_token():
    return {
        "access_token": "new_jwt_token_here",
        "token_type": "bearer"
    }