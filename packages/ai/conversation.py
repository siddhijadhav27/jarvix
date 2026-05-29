"""
JARVIX Conversation State Manager
Handles multi-turn dialogs and context persistence
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from enum import Enum
import time

class ConversationState(Enum):
    IDLE = "idle"
    AWAITING_AMOUNT = "awaiting_amount"
    AWAITING_ASSET = "awaiting_asset"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    AWAITING_PRICE = "awaiting_price"

@dataclass
class ConversationContext:
    state: ConversationState = ConversationState.IDLE
    pending_intent: Optional[str] = None
    pending_entities: Dict[str, Any] = field(default_factory=dict)
    last_message: Optional[str] = None
    last_response: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

# In-memory store (use Redis in production)
conversation_store: Dict[str, ConversationContext] = {}

def get_context(user_id: str) -> ConversationContext:
    """Get or create conversation context for user"""
    if user_id not in conversation_store:
        conversation_store[user_id] = ConversationContext()
    return conversation_store[user_id]

def update_context(user_id: str, context: ConversationContext):
    """Update conversation context"""
    context.updated_at = time.time()
    conversation_store[user_id] = context

def clear_context(user_id: str):
    """Clear conversation context"""
    if user_id in conversation_store:
        del conversation_store[user_id]

def is_context_stale(context: ConversationContext, max_age: int = 300) -> bool:
    """Check if context is stale (default 5 minutes)"""
    return (time.time() - context.updated_at) > max_age
