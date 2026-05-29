"""
JARVIX Command Executor
Handles multi-turn conversations with state management
"""

from typing import Dict, Any
from conversation import (
    ConversationContext, ConversationState,
    get_context, update_context
)
from intent import IntentClassifier

class CommandExecutor:
    """Execute trading commands with conversation state"""

    def __init__(self):
        self.classifier = IntentClassifier()

    async def execute(self, message: str, user_id: str = "default") -> Dict[str, Any]:
        """Process message with conversation context"""

        context = get_context(user_id)

        # Handle pending states FIRST (critical for multi-turn)
        if context.state == ConversationState.AWAITING_AMOUNT:
            return await self._handle_amount_response(message, context, user_id)

        if context.state == ConversationState.AWAITING_ASSET:
            return await self._handle_asset_response(message, context, user_id)

        if context.state == ConversationState.AWAITING_CONFIRMATION:
            return await self._handle_confirmation(message, context, user_id)

        if context.state == ConversationState.AWAITING_PRICE:
            return await self._handle_price_response(message, context, user_id)

        # Fresh command — classify with LLM
        classified = await self.classifier.classify(message)

        # Update context with this interaction
        context.last_message = message
        update_context(user_id, context)

        return await self._route_intent(classified, user_id, context)

    async def _route_intent(self, classified: Dict, user_id: str, context: ConversationContext) -> Dict[str, Any]:
        """Route to appropriate handler based on intent"""

        intent = classified.get("intent", "unknown")
        needs_clarification = classified.get("needs_clarification", False)

        if needs_clarification:
            # Store pending intent for multi-turn
            context.state = self._get_clarification_state(classified)
            context.pending_intent = intent
            context.pending_entities = {
                "asset": classified.get("asset"),
                "amount": classified.get("amount"),
                "amount_type": classified.get("amount_type"),
                "price": classified.get("price")
            }
            update_context(user_id, context)

            return {
                "status": "awaiting_clarification",
                "intent": intent,
                "message": classified.get("clarification_question", "Can you clarify?"),
                "missing": self._get_missing_fields(classified)
            }

        # Full command — execute immediately
        if intent == "buy":
            return await self._execute_buy(classified, user_id, context)
        elif intent == "sell":
            return await self._execute_sell(classified, user_id, context)
        elif intent == "portfolio":
            return await self._get_portfolio(user_id)
        elif intent == "price":
            return await self._get_price(classified.get("asset"))
        elif intent == "stop_loss":
            return await self._set_stop_loss(classified, user_id, context)
        elif intent == "advice":
            return await self._get_advice(context.last_message or "")
        elif intent == "greeting":
            return {"message": "Hello! I'm Jarvix, your AI trading assistant. How can I help?"}
        else:
            return {"message": "I'm not sure what you mean. Try: 'Buy 100 ETH' or 'What's my portfolio?'"}

    def _get_clarification_state(self, classified: Dict) -> ConversationState:
        """Determine what we're waiting for"""
        if classified.get("amount") is None and classified.get("asset"):
            return ConversationState.AWAITING_AMOUNT
        if classified.get("asset") is None:
            return ConversationState.AWAITING_ASSET
        if classified.get("price") is None and classified.get("intent") in ["stop_loss", "take_profit"]:
            return ConversationState.AWAITING_PRICE
        return ConversationState.AWAITING_CONFIRMATION

    def _get_missing_fields(self, classified: Dict) -> list:
        """List missing required fields"""
        missing = []
        if classified.get("asset") is None:
            missing.append("asset")
        if classified.get("amount") is None:
            missing.append("amount")
        if classified.get("price") is None and classified.get("intent") in ["stop_loss", "take_profit"]:
            missing.append("price")
        return missing

    # Multi-turn handlers
    async def _handle_amount_response(self, message: str, context: ConversationContext, user_id: str) -> Dict[str, Any]:
        """Handle response when awaiting amount"""
        try:
            amount = float(message.strip())
            context.pending_entities["amount"] = amount
            context.pending_entities["amount_type"] = "fixed"

            # Check if we have everything now
            if context.pending_entities.get("asset"):
                return await self._prompt_confirmation(context, user_id)
            else:
                context.state = ConversationState.AWAITING_ASSET
                update_context(user_id, context)
                return {"message": "Which asset? (e.g., BTC, ETH, SOL)"}

        except ValueError:
            return {"message": "Please enter a number (e.g., 100)"}

    async def _handle_asset_response(self, message: str, context: ConversationContext, user_id: str) -> Dict[str, Any]:
        """Handle response when awaiting asset"""
        asset = message.strip().upper()
        context.pending_entities["asset"] = asset

        # Check if we have everything now
        if context.pending_entities.get("amount"):
            return await self._prompt_confirmation(context, user_id)
        else:
            context.state = ConversationState.AWAITING_AMOUNT
            update_context(user_id, context)
            return {"message": f"How much {asset} would you like to {context.pending_intent}?"}

    async def _handle_price_response(self, message: str, context: ConversationContext, user_id: str) -> Dict[str, Any]:
        """Handle response when awaiting price"""
        try:
            price = float(message.strip().replace("$", "").replace("k", "000"))
            context.pending_entities["price"] = price
            return await self._prompt_confirmation(context, user_id)
        except ValueError:
            return {"message": "Please enter a price (e.g., 2500 or $2.5k)"}

    async def _handle_confirmation(self, message: str, context: ConversationContext, user_id: str) -> Dict[str, Any]:
        """Handle confirmation response"""

        msg_lower = message.lower().strip()

        confirmed = msg_lower in [
            "yes", "confirm", "ok", "okay",
            "do it", "go ahead", "sure", "yep",
            "yeah", "y", "proceed"
        ]

        cancelled = msg_lower in [
            "no", "cancel", "stop", "abort",
            "never mind", "nope", "don't",
            "dont", "nah", "quit"
        ]

        if confirmed:
            pending = context.pending_entities
            intent = context.pending_intent

            # Clear state
            context.state = ConversationState.IDLE
            context.pending_intent = None
            context.pending_entities = {}
            update_context(user_id, context)

            # Execute the trade
            return {
                "action": intent,
                "asset": pending.get("asset"),
                "amount": pending.get("amount"),
                "amount_type": pending.get("amount_type"),
                "price": pending.get("price"),
                "status": "executing",
                "message": f"✅ Executing: {intent.upper()} {pending.get('amount')} {pending.get('asset')}..."
            }

        elif cancelled:
            context.state = ConversationState.IDLE
            context.pending_intent = None
            context.pending_entities = {}
            update_context(user_id, context)
            return {"status": "cancelled", "message": "❌ Cancelled. Anything else?"}

        else:
            return {
                "status": "awaiting_confirmation",
                "message": "Please say 'yes' to confirm or 'no' to cancel."
            }

    async def _prompt_confirmation(self, context: ConversationContext, user_id: str) -> Dict[str, Any]:
        """Prompt user for confirmation"""
        context.state = ConversationState.AWAITING_CONFIRMATION
        update_context(user_id, context)

        pending = context.pending_entities
        intent = context.pending_intent

        msg = f"Confirm: {intent.upper()} {pending.get('amount')} {pending.get('asset')}"
        if pending.get("price"):
            msg += f" at ${pending.get('price')}"
        msg += "?"

        return {
            "status": "awaiting_confirmation",
            "intent": intent,
            "entities": pending,
            "message": msg
        }

    # Intent handlers
    async def _execute_buy(self, classified: Dict, user_id: str, context: ConversationContext) -> Dict[str, Any]:
        """Execute buy command"""
        asset = classified.get("asset")
        amount = classified.get("amount")

        if not asset or not amount:
            # Store state and ask for missing info
            context.state = ConversationState.AWAITING_AMOUNT if not amount else ConversationState.AWAITING_ASSET
            context.pending_intent = "buy"
            context.pending_entities = {"asset": asset, "amount": amount}
            update_context(user_id, context)

            if not asset:
                return {"message": "Which asset would you like to buy? (e.g., BTC, ETH)"}
            return {"message": f"How much {asset} would you like to buy?"}

        return await self._prompt_confirmation(context, user_id)

    async def _execute_sell(self, classified: Dict, user_id: str, context: ConversationContext) -> Dict[str, Any]:
        """Execute sell command"""
        asset = classified.get("asset")
        amount = classified.get("amount")

        if not asset or not amount:
            context.state = ConversationState.AWAITING_AMOUNT if not amount else ConversationState.AWAITING_ASSET
            context.pending_intent = "sell"
            context.pending_entities = {"asset": asset, "amount": amount}
            update_context(user_id, context)

            if not asset:
                return {"message": "Which asset would you like to sell?"}
            return {"message": f"How much {asset} would you like to sell?"}

        return await self._prompt_confirmation(context, user_id)

    async def _get_portfolio(self, user_id: str) -> Dict[str, Any]:
        """Get portfolio"""
        return {
            "action": "portfolio",
            "status": "fetching",
            "message": "Fetching your portfolio..."
        }

    async def _get_price(self, asset: str) -> Dict[str, Any]:
        """Get price"""
        if not asset:
            return {"message": "Which asset? (e.g., 'Price of BTC')"}
        return {
            "action": "price",
            "asset": asset,
            "message": f"Fetching {asset} price..."
        }

    async def _set_stop_loss(self, classified: Dict, user_id: str, context: ConversationContext) -> Dict[str, Any]:
        """Set stop-loss"""
        asset = classified.get("asset")
        price = classified.get("price")

        if not asset or not price:
            context.state = ConversationState.AWAITING_PRICE if not price else ConversationState.AWAITING_ASSET
            context.pending_intent = "stop_loss"
            context.pending_entities = {"asset": asset, "price": price}
            update_context(user_id, context)

            if not asset:
                return {"message": "Which asset?"}
            return {"message": f"What stop-loss price for {asset}?"}

        return await self._prompt_confirmation(context, user_id)

    async def _get_advice(self, message: str) -> Dict[str, Any]:
        """Get trading advice"""
        from simple_router import simple_chat
        from response_cleaner import clean_response

        response = await simple_chat(message)
        clean = clean_response(response)

        return {
            "action": "advice",
            "message": clean[:500]  # Limit length
        }
