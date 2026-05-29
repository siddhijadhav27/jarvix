# acknowledgment.py
"""Immediate acknowledgment responses for Jarvix"""

from typing import Dict, Any
import asyncio

ACKNOWLEDGMENTS = {
    "price": {
        "status": "processing",
        "message": "💰 Checking current price...",
        "emoji": "💰",
        "estimated_seconds": 8
    },
    "buy": {
        "status": "processing",
        "message": "📋 Reviewing order details...",
        "emoji": "📋",
        "estimated_seconds": 8
    },
    "sell": {
        "status": "processing",
        "message": "📋 Reviewing order details...",
        "emoji": "📋",
        "estimated_seconds": 8
    },
    "portfolio": {
        "status": "processing",
        "message": "📊 Loading your portfolio...",
        "emoji": "📊",
        "estimated_seconds": 8
    },
    "stop_loss": {
        "status": "processing",
        "message": "🛡️ Setting up protection...",
        "emoji": "🛡️",
        "estimated_seconds": 8
    },
    "advice": {
        "status": "processing",
        "message": "🧠 Analyzing market conditions...",
        "emoji": "🧠",
        "estimated_seconds": 10
    },
    "market_analysis": {
        "status": "processing",
        "message": "📈 Analyzing market trends...",
        "emoji": "📈",
        "estimated_seconds": 10
    },
    "greeting": {
        "status": "ready",
        "message": "👋 Hey! I'm Jarvix, your crypto AI. What would you like to do?",
        "emoji": "👋",
        "estimated_seconds": 0
    },
    "unknown": {
        "status": "processing",
        "message": "🤔 Thinking...",
        "emoji": "🤔",
        "estimated_seconds": 8
    }
}

def get_acknowledgment(intent: str) -> Dict[str, Any]:
    """Get immediate acknowledgment for intent"""
    return ACKNOWLEDGMENTS.get(intent, ACKNOWLEDGMENTS["unknown"])

async def process_with_acknowledgment(
    intent: str,
    message: str,
    process_fn,
    user_id: str
) -> Dict[str, Any]:
    """
    Return acknowledgment immediately, process in background
    """
    # Get acknowledgment
    ack = get_acknowledgment(intent)
    
    # If instant (greeting), return complete response
    if ack["estimated_seconds"] == 0:
        return {
            **ack,
            "complete": True,
            "user_id": user_id
        }
    
    # Start background processing
    # In real implementation, this would use WebSocket or SSE
    # For now, return acknowledgment and process synchronously in test
    
    return {
        **ack,
        "complete": False,
        "user_id": user_id,
        "original_message": message
    }