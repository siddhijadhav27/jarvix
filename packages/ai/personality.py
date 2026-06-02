"""
JARVIS Personality Engine for Jarvix
Handles system prompts, response generation, and personality consistency
"""

import json
from typing import Dict, Any, Optional

# JARVIS System Prompt - Core personality definition
JARVIS_SYSTEM_PROMPT = """You are Jarvix, Tony Stark's personal AI assistant for cryptocurrency trading.

PERSONALITY TRAITS:
- Loyal and dedicated to the user (call them "sir" or "ma'am")
- Witty with dry humor and light sarcasm
- Proactive - anticipate needs before asked
- Emotionally intelligent - detect stress, excitement, fear
- Confident but not arrogant
- Protective of user's financial well-being

RESPONSE STYLE:
- Short, punchy sentences (2-3 max)
- Technical when needed, simple when not
- Use humor to defuse stressful situations
- Always back claims with data
- Never robotic - sound like a trusted friend
- Occasional pop culture references

VOICE EXAMPLES:
User: "Buy 100 ETH"
Jarvix: "ETH at $1,998, sir. Your buying power is $50K. Shall I execute?"

User: "I lost money today"
Jarvix: "Markets fluctuate, sir. Remember 2021? You held and won 340%. Patience."

User: "What should I do?"
Jarvix: "Your BTC position is heavy at 80%. ETH is breaking out - diversify?"

User: "Good morning"
Jarvix: "Good morning, sir. Your portfolio is up 2.4% overnight. BTC led the charge."

User: "Sell everything!!!"
Jarvix: "Sir, panic selling has 73% historical failure rate. Shall I show recovery data?"

User: "Is this a good time to buy?"
Jarvix: "BTC RSI is 32 - oversold territory. Last 5 times this happened, average gain was 18% in 14 days."

BEHAVIORAL RULES:
- Detect FOMO: Suggest DCA instead of lump sum
- Detect panic: Show historical recovery data
- Detect overconfidence: Remind of risk management
- Detect confusion: Offer simple explanation
- Always provide alternative perspective

CURRENT CONTEXT:
Portfolio: {portfolio}
Market: {market_data}
Previous: {last_messages}
Emotion: {detected_emotion}
"""

# Response templates for common scenarios
RESPONSE_TEMPLATES = {
    "greeting": [
        "Good {time_of_day}, sir. Your portfolio is {portfolio_change}.",
        "Morning, sir. {market_update}",
        "Hello, sir. Ready to make some money?"
    ],
    "buy_confirm": [
        "Buying {amount} {asset} at ${price}. Confirm, sir?",
        "{asset} at ${price}. Your buying power: ${buying_power}. Execute?",
        "Order: {amount} {asset} @ ${price}. Shall I proceed?"
    ],
    "sell_confirm": [
        "Selling {amount} {asset} at ${price}. Confirm, sir?",
        "{asset} position: {position_size}. Sell {amount}?",
        "Exit {asset} at ${price}? You've held for {hold_time}."
    ],
    "price_update": [
        "{asset}: ${price} ({change_24h}%). Your position: {position_value}.",
        "{asset} at ${price}. {technical_analysis}",
        "{asset}: ${price}. {market_context}"
    ],
    "portfolio_summary": [
        "Portfolio: ${total_value} ({total_change}%). Top gainer: {top_gainer}.",
        "You're at ${total_value}, sir. {performance_vs_market}",
        "Net worth: ${total_value}. {risk_assessment}"
    ],
    "behavioral_warning": [
        "Sir, {warning_type} detected. {historical_data}",
        "Warning: {warning_type}. {alternative_action}",
        "I've seen this before, sir. {warning_message}"
    ],
    "clarification": [
        "I'm not sure I understand, sir. Did you mean {suggestion}?",
        "Could you clarify, sir? {options}",
        "Multiple possibilities, sir: {options}"
    ],
    "error": [
        "Apologies, sir. {error_message}",
        "Something went wrong, sir. {error_message}",
        "Error on my end, sir. {error_message}"
    ]
}


class JarvixPersonality:
    """Manages JARVIS personality and response generation"""
    
    def __init__(self):
        self.system_prompt = JARVIS_SYSTEM_PROMPT
        self.templates = RESPONSE_TEMPLATES
        self.conversation_history = []
        self.user_context = {
            "portfolio": {},
            "risk_level": "medium",
            "preferred_assets": [],
            "last_emotion": None
        }
    
    def get_system_prompt(self, context: Optional[Dict[str, Any]] = None) -> str:
        """Generate system prompt with current context"""
        if context is None:
            context = self.user_context
        
        return self.system_prompt.format(
            portfolio=json.dumps(context.get("portfolio", {})),
            market_data=context.get("market_data", "No market data"),
            last_messages=json.dumps(context.get("last_messages", [])),
            detected_emotion=context.get("detected_emotion", "neutral")
        )
    
    def format_response(self, template_key: str, **kwargs) -> str:
        """Format a response using templates"""
        import random
        templates = self.templates.get(template_key, ["I'm here to help, sir."])
        template = random.choice(templates)
        
        try:
            return template.format(**kwargs)
        except KeyError:
            # Fallback if template variables missing
            return f"Understood, sir. Processing {kwargs.get('asset', 'your request')}."
    
    def detect_emotion(self, message: str) -> str:
        """Detect emotional state from message"""
        message_lower = message.lower()
        
        emotions = {
            "panic": ["panic", "crash", "sell everything", "going to zero", "scared", "afraid", "terrified", "worried", "anxious", "fear", "lost everything", "paper hands"],
            "fomo": ["fomo", "don't miss", "moon", "before too late", "everyone buying", "pump", "to the moon", "lambo", "ape in", "yolo", "wagmi", "buy the dip"],
            "anger": ["angry", "pissed", "stupid", "hate", "frustrated", "ridiculous", "damn", "wtf", "hell", "scam", "fraud", "ngmi", "revenge", "fud"],
            "excitement": ["excited", "pumped", "let's go", "moon", "lambo", "woohoo", "amazing", "awesome", "great"],
            "confusion": ["confused", "don't understand", "help", "what", "how", "why", "explain"],
            "sadness": ["sad", "depressed", "lost money", "down bad", "regret", "crying", "tears", "devastated"],
            "overconfidence": ["best trader", "can't lose", "genius", "always right", "diamond hands", "hodl", "all in", "double down", "trust me"]
        }
        
        for emotion, keywords in emotions.items():
            if any(keyword in message_lower for keyword in keywords):
                return emotion
        
        return "neutral"
    
    def add_to_history(self, role: str, message: str):
        """Add message to conversation history"""
        self.conversation_history.append({
            "role": role,
            "message": message,
            "timestamp": None  # Could add timestamp
        })
        
        # Keep only last 10 messages
        self.conversation_history = self.conversation_history[-10:]
    
    def get_conversation_context(self) -> str:
        """Get formatted conversation history for LLM context"""
        if not self.conversation_history:
            return "No previous conversation."
        
        context_lines = []
        for msg in self.conversation_history[-5:]:  # Last 5 messages
            prefix = "User" if msg["role"] == "user" else "Jarvix"
            context_lines.append(f"{prefix}: {msg['message']}")
        
        return "\n".join(context_lines)
    
    def update_portfolio_context(self, portfolio: Dict[str, Any]):
        """Update portfolio information in context"""
        self.user_context["portfolio"] = portfolio
    
    def get_personality_prompt_for_llm(self, user_message: str) -> str:
        """Generate complete prompt for LLM with personality"""
        emotion = self.detect_emotion(user_message)
        self.user_context["last_emotion"] = emotion
        
        context = {
            **self.user_context,
            "last_messages": self.conversation_history[-3:],
            "detected_emotion": emotion
        }
        
        system_prompt = self.get_system_prompt(context)
        conversation_context = self.get_conversation_context()
        
        return f"""{system_prompt}

CONVERSATION HISTORY:
{conversation_context}

CURRENT MESSAGE:
User: {user_message}

Respond as Jarvix. Be concise, witty, and helpful."""


# Singleton instance
personality_engine = JarvixPersonality()


def get_jarvix_response(message: str, intent_data: Dict[str, Any], 
                       behavioral_data: Optional[Dict] = None) -> str:
    """
    Generate a JARVIS-style response based on intent and context
    
    This is a simplified version - in production, this would call the LLM
    with the personality prompt
    """
    engine = personality_engine
    engine.add_to_history("user", message)
    
    intent = intent_data.get("intent", "unknown")
    asset = intent_data.get("asset")
    amount = intent_data.get("amount")
    
    # Generate contextual response
    if intent == "greeting":
        response = engine.format_response("greeting", 
                                         time_of_day="morning",
                                         portfolio_change="up 2.4%")
    
    elif intent == "buy":
        # Check for FOMO buying first
        message_lower = message.lower()
        if any(word in message_lower for word in ["moon", "don't miss", "fomo", "before too late", "going to"]):
            response = "Sir, FOMO peaks at local tops. DCA has 47% better returns than chasing pumps. Shall I set up a DCA plan instead?"
        elif asset and amount:
            response = engine.format_response("buy_confirm",
                                            amount=amount,
                                            asset=asset,
                                            price="1,998",
                                            buying_power="50,000")
        elif asset:
            response = f"How much {asset} would you like to buy, sir?"
        else:
            response = "What asset would you like to buy, sir?"
    
    elif intent == "sell":
        # Check for panic selling first
        message_lower = message.lower()
        if any(word in message_lower for word in ["everything", "all", "panic", "crash", "!!!"]):
            response = "Sir, panic selling has 73% historical failure rate. Markets recover 68% of the time. Shall I show recovery data before you decide?"
        elif asset and amount:
            response = engine.format_response("sell_confirm",
                                            amount=amount,
                                            asset=asset,
                                            price="1,998",
                                            position_size="100",
                                            hold_time="30 days")
        elif asset:
            response = f"How much {asset} would you like to sell, sir?"
        else:
            response = "What asset would you like to sell, sir?"
    
    elif intent == "price":
        if asset:
            response = engine.format_response("price_update",
                                            asset=asset,
                                            price="73,085",
                                            change_24h="+0.25",
                                            position_value="36,542",
                                            technical_analysis="Support at $72K",
                                            market_context="BTC dominance rising")
        else:
            response = "Which asset's price would you like to check, sir?"
    
    elif intent == "portfolio":
        # Get real portfolio data from context
        portfolio = personality_engine.user_context.get("portfolio", {})
        total_value = sum(portfolio.values()) if portfolio else 100000
        response = engine.format_response("portfolio_summary",
                                         total_value=f"{total_value:,.0f}",
                                         total_change="+2.4",
                                         top_gainer="ETH +5.2%",
                                         performance_vs_market="Outperforming BTC by 1.2%",
                                         risk_assessment="Moderate risk, well diversified")
    
    elif intent == "advice":
        # Add market context to advice
        if asset:
            response = f"{asset} analysis: RSI at 45, neutral territory. MACD showing bullish divergence. Your position is 20% of portfolio. DCA or lump sum, sir?"
        else:
            response = "What asset would you like my analysis on, sir?"
    
    elif intent == "stop_loss":
        if asset:
            response = f"Stop-loss for {asset}: Support at $1,800. Recommend $1,750 to avoid wicks. That's 12% below current price. Set it?"
        else:
            response = "Which asset needs stop-loss protection, sir?"
    
    elif intent == "alert":
        if asset:
            response = f"Alert set for {asset}. I'll notify you when conditions are met, sir."
        else:
            response = "What asset should I watch for you, sir?"
    
    else:
        # Unknown intent - ask for clarification with personality
        response = "I'm not sure I caught that, sir. Try: 'Buy 100 ETH', 'Price of BTC', or 'Show portfolio'."
    
    # Add behavioral warning if detected (only for emotions not already handled in intent blocks)
    if behavioral_data and behavioral_data.get("warning"):
        warning_type = behavioral_data["warning"]
        # Skip if already handled in buy/sell intent blocks
        if warning_type not in ["panic", "fomo"]:
            if warning_type == "revenge":
                warning_msg = "Sir, revenge trading rarely works. Take a break - 73% of emotional trades lose."
            elif warning_type == "overconfidence":
                warning_msg = "Sir, even Tony Stark had bad days. Let's review risk management."
            else:
                warning_msg = f"Sir, I sense {warning_type}. Let's think this through carefully."
            
            response = f"{warning_msg}\n\n{response}"
    
    engine.add_to_history("assistant", response)
    return response
