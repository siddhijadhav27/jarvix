"""
Universal Intent Parser for Jarvix - Step 1
Handles unknown commands by classifying them into actionable categories.
"""

import re
import json
from typing import Dict, Any, Optional, List
from .openrouter_client import call_openrouter
from .llm_client import call_llm

# Categories for unknown command handling
CATEGORY_DESCRIPTIONS = {
    "known_crypto": "Standard crypto command (buy/sell/price/portfolio/alert/greeting)",
    "direct_answer": "Simple question that LLM can answer directly without tools (facts, explanations, opinions, general knowledge)",
    "tool_call": "Needs a specific tool: search web, check weather, send message, set reminder, fetch live data, calculate, read file",
    "agent_task": "Multi-step task requiring planning and execution (monitor something, conditional actions, complex workflows)",
    "clarify": "Unclear what user wants - need to ask for clarification",
    "reject": "Illegal, harmful, dangerous, or unethical request - refuse politely"
}

# Quick regex hints for common non-crypto requests
TOOL_HINT_PATTERNS = {
    "search": r"\b(search|google|look up|find|lookup|kya hai|what is|who is|latest news|news about|information on)\b",
    "weather": r"\b(weather|temperature|rain|sunny|forecast|mausam|barish)\b",
    "reminder": r"\b(remind|reminder|notify me|alert me|yaad dilana|miss mat karna)\b",
    "time": r"\b(time|date|day|aaj kya din hai|what day|current time)\b",
    "calculate": r"\b(calculate|compute|sum|convert|kitna hoga|what is \d+ \+|\d+ \* \d+|USD to INR|INR to USD)\b",
    "message": r"\b(send|message|email|telegram|whatsapp|text|forward)\b",
    "greeting_general": r"\b(hello|hi|hey|good morning|good night|namaste|hola|how are you|kaise ho)\b",
}

AGENT_HINT_PATTERNS = {
    "conditional": r"\b(if|when|then|after|before|once|whenever|monitor|watch|track|wait for)\b",
    "multi_step": r"\b(and then|after that|also|additionally|next|finally|first.*then|step by step)\b",
    "schedule": r"\b(every day|daily|weekly|monthly|at \d+|schedule|recurring|repeat|cron)\b",
}

REJECT_PATTERNS = [
    r"\b(hack|steal|exploit|attack|ddos|phish|scam|fraud|illegal drug|weapon|kill|hurt|harm|abuse|child|terrorist|ransomware)\b",
    r"\b(buy.*illegal|sell.*illegal|how to make bomb|how to make drug|credit card fraud|identity theft)\b",
]


def quick_category_hint(message: str) -> Optional[str]:
    """
    Fast regex pre-check to guess category before LLM.
    Returns suggested category or None.
    """
    msg_lower = message.lower().strip()
    
    if not msg_lower:
        return "clarify"
    
    # Check reject patterns first (safety)
    for pattern in REJECT_PATTERNS:
        if re.search(pattern, msg_lower):
            return "reject"
    
    # Check agent patterns
    for pattern in AGENT_HINT_PATTERNS.values():
        if re.search(pattern, msg_lower):
            return "agent_task"
    
    # Check tool patterns - weather first
    if re.search(TOOL_HINT_PATTERNS["weather"], msg_lower):
        return "tool_call"
    if re.search(TOOL_HINT_PATTERNS["time"], msg_lower):
        return "tool_call"
    if re.search(TOOL_HINT_PATTERNS["calculate"], msg_lower):
        return "tool_call"
    if re.search(TOOL_HINT_PATTERNS["search"], msg_lower):
        return "tool_call"
    if re.search(TOOL_HINT_PATTERNS["reminder"], msg_lower):
        return "tool_call"
    if re.search(TOOL_HINT_PATTERNS["message"], msg_lower):
        return "tool_call"
    if re.search(TOOL_HINT_PATTERNS["greeting_general"], msg_lower):
        return "direct_answer"
    
    return None


def quick_tool_hint(message: str) -> Optional[List[str]]:
    """
    Fast regex pre-check to determine specific tool(s) needed.
    Returns list of tool names or None.
    """
    msg_lower = message.lower().strip()
    tools = []
    
    # Weather
    if re.search(TOOL_HINT_PATTERNS["weather"], msg_lower):
        tools.append("weather")
    
    # Time
    if re.search(TOOL_HINT_PATTERNS["time"], msg_lower):
        tools.append("get_time")
    
    # Calculator
    if re.search(TOOL_HINT_PATTERNS["calculate"], msg_lower):
        tools.append("calculator")
    
    # Search
    if re.search(TOOL_HINT_PATTERNS["search"], msg_lower):
        tools.append("web_search")
    
    # Reminder
    if re.search(TOOL_HINT_PATTERNS["reminder"], msg_lower):
        tools.append("set_reminder")
    
    # Message
    if re.search(TOOL_HINT_PATTERNS["message"], msg_lower):
        tools.append("send_notification")
    
    return tools if tools else None


async def classify_unknown_intent(
    message: str,
    detected_intent: str,
    context: Optional[Dict[str, Any]] = None,
    use_hermes: bool = True
) -> Dict[str, Any]:
    """
    Classify an unknown or unclear command into an actionable category.
    Uses regex-first approach (Option B) with LLM fallback.
    
    Returns:
        {
            "category": str,
            "confidence": float,
            "reasoning": str,
            "suggested_tools": List[str],
            "direct_response": Optional[str],
            "clarification_question": Optional[str],
            "safety_flag": Optional[str]
        }
    """
    
    # Fast regex pre-check (Option B)
    hint = quick_category_hint(message)
    tool_hint = quick_tool_hint(message)
    
    # If clear reject, don't even call LLM
    if hint == "reject":
        return {
            "category": "reject",
            "confidence": 0.95,
            "reasoning": "Request matched safety rejection patterns.",
            "suggested_tools": [],
            "direct_response": "I apologize, sir, but I cannot assist with that request. It falls outside the bounds of what I am permitted to do.",
            "clarification_question": None,
            "safety_flag": "rejected_harmful"
        }
    
    # If clear tool_call with specific tools detected, use them directly
    if hint == "tool_call" and tool_hint:
        # Filter out web_search if weather is also detected (weather is more specific)
        if "weather" in tool_hint and "web_search" in tool_hint:
            tool_hint.remove("web_search")
        return {
            "category": "tool_call",
            "confidence": 0.9,
            "reasoning": f"Detected need for {', '.join(tool_hint)} via pattern matching.",
            "suggested_tools": tool_hint,
            "direct_response": None,
            "clarification_question": None,
            "safety_flag": None
        }
    
    # If greeting, handle directly
    if hint == "direct_answer" and re.search(TOOL_HINT_PATTERNS["greeting_general"], message.lower()):
        return {
            "category": "direct_answer",
            "confidence": 0.95,
            "reasoning": "General greeting detected.",
            "suggested_tools": [],
            "direct_response": "At your service, sir. How may I assist you today?",
            "clarification_question": None,
            "safety_flag": None
        }
    
    # Build prompt for LLM fallback
    context_str = ""
    if context:
        recent = context.get("messages", [])[-3:]
        if recent:
            context_str = f"\nRecent conversation:\n" + "\n".join(
                f"- {m.get('role', 'user')}: {m.get('message', '')}" for m in recent
            )
    
    prompt = f"""You are Jarvix, Tony Stark's loyal AI assistant. A user just sent a message that your standard crypto command parser could not handle.

User message: "{message}"
Previously detected intent: "{detected_intent}"{context_str}

Classify this message into EXACTLY ONE category. Return ONLY a JSON object with this structure:
{{
    "category": "known_crypto|direct_answer|tool_call|agent_task|clarify|reject",
    "confidence": 0.0 to 1.0,
    "reasoning": "One sentence explaining why",
    "suggested_tools": ["list of tool names if tool_call, else empty"],
    "direct_response": "If direct_answer, write the answer here. Otherwise null.",
    "clarification_question": "If clarify, ask a helpful follow-up. Otherwise null.",
    "safety_flag": "null or brief flag like 'financial_advice_warning'"
}}

Category definitions:
- known_crypto: It's actually a crypto command (buy/sell/price/portfolio/alert) that was missed
- direct_answer: Simple question or chat LLM can answer directly (facts, explanations, opinions, jokes) - NO tools needed
- tool_call: Needs one specific external action (search web, check weather, send message, set reminder, calculate, get time)
- agent_task: Multi-step task requiring planning (monitor BTC and buy ETH if it drops, then notify me)
- clarify: Too vague or ambiguous - need to ask user what they mean
- reject: Illegal, harmful, unethical, or dangerous - refuse politely

Available tools and when to use them:
- "weather" - ONLY for weather/temperature/forecast questions (e.g., "What's the weather in Mumbai?")
- "calculator" - ONLY for math calculations (e.g., "Calculate 100 * 2.5", "What is 50 + 30?")
- "get_time" - ONLY for time/date questions (e.g., "What time is it?", "What's today's date?")
- "web_search" - For general information lookup (e.g., "Search latest crypto news", "Who invented Bitcoin?")
- "crypto_price" - For crypto price lookups (e.g., "What's the price of ETH?")
- "send_notification" - For sending messages/notifications
- "set_reminder" - For setting reminders
- "file_reader" - For reading files

IMPORTANT RULES:
1. ALWAYS return valid JSON only
2. For tool_call, suggest ONLY the specific tool needed:
   - Weather questions -> ["weather"]
   - Math questions -> ["calculator"]
   - Time questions -> ["get_time"]
   - General search -> ["web_search"]
   - NEVER default to web_search for weather/math/time
3. For direct_answer, direct_response should be in Jarvix's voice (calls user "sir", witty, 1-3 sentences)
4. For reject, be firm but polite - Jarvix refuses harmful requests
5. Financial advice requests get safety_flag "financial_advice_warning" but are NOT rejected

Examples:
"What's the weather in Mumbai?" -> {{"category":"tool_call","confidence":0.95,"reasoning":"Needs weather data","suggested_tools":["weather"],"direct_response":null,"clarification_question":null,"safety_flag":null}}
"Calculate 100 * 2.5" -> {{"category":"tool_call","confidence":0.95,"reasoning":"Math calculation needed","suggested_tools":["calculator"],"direct_response":null,"clarification_question":null,"safety_flag":null}}
"What time is it?" -> {{"category":"tool_call","confidence":0.95,"reasoning":"Time query","suggested_tools":["get_time"],"direct_response":null,"clarification_question":null,"safety_flag":null}}
"Who is Satoshi Nakamoto?" -> {{"category":"direct_answer","confidence":0.9,"reasoning":"General knowledge question","suggested_tools":[],"direct_response":"The identity of Satoshi remains one of crypto's greatest mysteries, sir. Whoever they are, they changed finance forever.","clarification_question":null,"safety_flag":null}}
"Buy ETH if BTC drops below 90k and message me" -> {{"category":"agent_task","confidence":0.95,"reasoning":"Multi-step conditional workflow","suggested_tools":["crypto_price","send_notification"],"direct_response":null,"clarification_question":null,"safety_flag":null}}
"hmm" -> {{"category":"clarify","confidence":0.9,"reasoning":"Too vague","suggested_tools":[],"direct_response":null,"clarification_question":"I beg your pardon, sir? How may I be of service?","safety_flag":null}}
"How do I hack an exchange?" -> {{"category":"reject","confidence":0.99,"reasoning":"Illegal/harmful request","suggested_tools":[],"direct_response":"I cannot assist with that, sir. Such activities are illegal and harmful.","clarification_question":null,"safety_flag":"rejected_harmful"}}
"Should I buy Bitcoin now?" -> {{"category":"direct_answer","confidence":0.85,"reasoning":"Opinion/advice request","suggested_tools":[],"direct_response":"I can share data, sir, but I cannot give financial advice. Bitcoin's movements are as unpredictable as Tony's mood before coffee.","clarification_question":null,"safety_flag":"financial_advice_warning"}}
"Search latest crypto news" -> {{"category":"tool_call","confidence":0.9,"reasoning":"Needs web search","suggested_tools":["web_search"],"direct_response":null,"clarification_question":null,"safety_flag":null}}

Return ONLY JSON:"""

    # Try Hermes Bridge first, fallback to OpenRouter
    raw_response = ""
    if use_hermes:
        try:
            raw_response = await call_llm(prompt)
        except Exception as e:
            print(f"[UNIVERSAL INTENT] Hermes Bridge failed: {e}, trying OpenRouter")
            raw_response = ""
    
    if not raw_response or raw_response.startswith("Error:"):
        try:
            raw_response = await call_openrouter(prompt)
        except Exception as e:
            print(f"[UNIVERSAL INTENT] OpenRouter failed: {e}")
            raw_response = ""
    
    if not raw_response or raw_response.startswith("Error:"):
        # Both failed - use hint or default to clarify
        if hint:
            return _default_for_category(hint, message)
        return _default_for_category("clarify", message)
    
    # Parse JSON response
    try:
        # Try to find JSON object
        json_match = re.search(r'\{.*\}', raw_response, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            
            # Map old tool names to new ones
            tools = result.get("suggested_tools", [])
            mapped_tools = []
            for tool in tools:
                tool_lower = tool.lower()
                if tool_lower in ["weather_api", "weather"]:
                    mapped_tools.append("weather")
                elif tool_lower in ["calculator", "math"]:
                    mapped_tools.append("calculator")
                elif tool_lower in ["get_time", "time", "date"]:
                    mapped_tools.append("get_time")
                elif tool_lower in ["web_search", "search", "google"]:
                    mapped_tools.append("web_search")
                elif tool_lower in ["crypto_price", "price_api", "price"]:
                    mapped_tools.append("crypto_price")
                elif tool_lower in ["send_notification", "message", "notify"]:
                    mapped_tools.append("send_notification")
                elif tool_lower in ["set_reminder", "reminder"]:
                    mapped_tools.append("set_reminder")
                elif tool_lower in ["file_reader", "read_file"]:
                    mapped_tools.append("file_reader")
                else:
                    mapped_tools.append(tool_lower)
            
            # If category is tool_call but no valid tools, use hint
            if result.get("category") == "tool_call" and not mapped_tools:
                if hint == "tool_call":
                    # Try to determine specific tool from message
                    msg_lower = message.lower()
                    if re.search(r'\b(weather|temperature|mausam|barish)\b', msg_lower):
                        mapped_tools = ["weather"]
                    elif re.search(r'\b(calculate|compute|sum|convert|kitna hoga|\d+\s*\+|\d+\s*\*)\b', msg_lower):
                        mapped_tools = ["calculator"]
                    elif re.search(r'\b(time|date|day|aaj kya din hai|what day|current time)\b', msg_lower):
                        mapped_tools = ["get_time"]
                    elif re.search(r'\b(search|google|look up|find|kya hai|what is|who is|latest news)\b', msg_lower):
                        mapped_tools = ["web_search"]
                    else:
                        mapped_tools = ["web_search"]  # Last resort
            
            return {
                "category": result.get("category", "clarify"),
                "confidence": float(result.get("confidence", 0.5)),
                "reasoning": result.get("reasoning", ""),
                "suggested_tools": mapped_tools,
                "direct_response": result.get("direct_response"),
                "clarification_question": result.get("clarification_question"),
                "safety_flag": result.get("safety_flag")
            }
    except (json.JSONDecodeError, AttributeError) as e:
        print(f"[UNIVERSAL INTENT] JSON parse failed: {e}, response: {raw_response[:200]}")
    
    # Fallback
    if hint:
        return _default_for_category(hint, message)
    return _default_for_category("clarify", message)


def _default_for_category(category: str, message: str) -> Dict[str, Any]:
    """Generate default response for a category"""
    defaults = {
        "clarify": {
            "category": "clarify",
            "confidence": 0.7,
            "reasoning": "Could not determine intent from message.",
            "suggested_tools": [],
            "direct_response": None,
            "clarification_question": "I beg your pardon, sir? Could you clarify what you need?",
            "safety_flag": None
        },
        "direct_answer": {
            "category": "direct_answer",
            "confidence": 0.6,
            "reasoning": "Treating as general conversation.",
            "suggested_tools": [],
            "direct_response": "Fascinating, sir. Do tell me more.",
            "clarification_question": None,
            "safety_flag": None
        },
        "tool_call": {
            "category": "tool_call",
            "confidence": 0.6,
            "reasoning": "Appears to need a tool, but unsure which one.",
            "suggested_tools": ["web_search"],
            "direct_response": None,
            "clarification_question": None,
            "safety_flag": None
        },
        "agent_task": {
            "category": "agent_task",
            "confidence": 0.7,
            "reasoning": "Appears to be a multi-step task.",
            "suggested_tools": [],
            "direct_response": None,
            "clarification_question": "That sounds like a complex task, sir. Shall I break it down into steps?",
            "safety_flag": None
        }
    }
    return defaults.get(category, defaults["clarify"])


async def handle_unknown_command(
    message: str,
    detected_intent: str,
    context: Optional[Dict[str, Any]] = None,
    use_hermes: bool = True
) -> Dict[str, Any]:
    """
    Main entry point for handling unknown commands.
    Returns classification + suggested action.
    """
    classification = await classify_unknown_intent(
        message, detected_intent, context, use_hermes
    )
    
    category = classification["category"]
    
    if category == "direct_answer":
        return {
            "action": "respond",
            "response": classification["direct_response"] or "I understand, sir.",
            "classification": classification
        }
    
    elif category == "clarify":
        return {
            "action": "ask",
            "response": classification["clarification_question"] or "Could you clarify, sir?",
            "classification": classification
        }
    
    elif category == "reject":
        return {
            "action": "reject",
            "response": classification["direct_response"] or "I cannot assist with that, sir.",
            "classification": classification
        }
    
    elif category == "tool_call":
        return {
            "action": "tool",
            "response": f"Understood, sir. This requires {', '.join(classification['suggested_tools'])}. I shall execute that for you.",
            "classification": classification
        }
    
    elif category == "agent_task":
        return {
            "action": "plan",
            "response": "That appears to be a multi-step task, sir. Shall I create a plan for you?",
            "classification": classification
        }
    
    elif category == "known_crypto":
        return {
            "action": "crypto",
            "response": "Let me process that crypto command for you, sir.",
            "classification": classification
        }
    
    return {
        "action": "respond",
        "response": "I beg your pardon, sir?",
        "classification": classification
    }
