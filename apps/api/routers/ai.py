from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from auth import verify_api_key
from rate_limit import limiter

router = APIRouter(tags=["AI Agent"])

class AgentRequest(BaseModel):
    prompt: str = Field(..., example="What is my portfolio performance this week?")

@router.post("/agent",
    summary="Run the Jarvix AI agent")
@limiter.limit("20/minute")
async def run_agent(
    request: Request,
    body: AgentRequest,
    user=Depends(verify_api_key)
):
    # MOCK LLM
    return {
        "user": user["user"],
        "prompt": body.prompt,
        "response": "This is a placeholder response. Connect Kimi API here.",
        "model": "kimi"
    }