"""
LLM Client for Jarvix
Connects to Hermes Bridge (localhost:8082) for AI responses
"""

import httpx
import json
import re
from typing import Optional, Dict, Any

HERMES_BRIDGE_URL = "http://localhost:8082/chat"

async def call_llm(prompt: str, timeout: float = 30.0) -> str:
    """
    Call LLM via Hermes Bridge
    
    Args:
        prompt: The prompt to send to LLM
        timeout: Request timeout in seconds
        
    Returns:
        Cleaned LLM response text
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                HERMES_BRIDGE_URL,
                json={"message": prompt},
                timeout=timeout
            )
            response.raise_for_status()
            data = response.json()
            
            # Clean TUI artifacts from response
            raw_response = data.get("response", "")
            return clean_response(raw_response)
            
    except httpx.ConnectError:
        return "Error: Cannot connect to Hermes Bridge. Is it running on port 8082?"
    except httpx.TimeoutException:
        return "Error: LLM request timed out. Please try again."
    except Exception as e:
        return f"Error: {str(e)}"


def clean_response(response: str) -> str:
    """
    Remove TUI artifacts from Hermes Bridge response
    """
    lines = response.split('\n')
    cleaned_lines = []
    
    for line in lines:
        line = line.strip()
        
        # Skip empty lines
        if not line:
            continue
        
        # Skip TUI artifact lines (expanded list)
        if line.startswith('⚕'):
            continue
        if line.startswith('─'):
            continue
        if line.startswith('╭') or line.startswith('╰') or line.startswith('│'):
            continue
        if line.startswith('❯'):
            continue
        if '⏲' in line and len(line) < 50:
            continue
        if line.startswith('⏱'):
            continue
        if '⏱' in line and len(line) < 50:
            continue
        if line.startswith('●'):
            continue
        if line.startswith('msg='):
            continue
        if 'synthesizing...' in line or 'brainstorming...' in line or 'pondering...' in line:
            continue
        if 'deliberating...' in line or 'musing...' in line or 'contemplating...' in line:
            continue
        if 'reflecting...' in line or 'analyzing...' in line or 'formulating...' in line:
            continue
        if 'computing...' in line or 'Interrupted' in line:
            continue
        if 'interrupt' in line.lower() and 'queue' in line.lower():
            continue
        if line.startswith('[') and '█' in line:
            continue
        if 'K/' in line and 'K │' in line:
            continue
        if 'h ' in line and 'm │' in line:
            continue
        if 's │' in line:
            continue
        if line.startswith('(') and '...' in line:
            continue
        if line.startswith('٩') and '...' in line:
            continue
        if line.startswith('◉') and '...' in line:
            continue
        if line.startswith('ಠ_ಠ'):
            continue
        if line.startswith('ヽ'):
            continue
        if line.startswith('...'):
            continue
        if line in ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0']:
            continue
        if len(line) == 1 and line.isdigit():
            continue
        if 'overconfidence.' in line or 'panic.' in line or 'anger.' in line:
            continue
        if len(line) == 3 and line[0].isdigit() and line[2].isdigit() and line[1] == ' ':
            continue
        if line.startswith('Operation interrupted'):
            continue
        if 'more lines' in line:
            continue
        
        # Skip prompt leakage
        if line.startswith('You are Jarvix'):
            continue
        if line.startswith('PERSONALITY:'):
            continue
        if line.startswith('RESPONSE STYLE:'):
            continue
        if line.startswith('CURRENT SITUATION:'):
            continue
        if line.startswith('USER CONTEXT:'):
            continue
        if line.startswith('CURRENT MESSAGE:'):
            continue
        if line.startswith('User:'):
            continue
        if line.startswith('Intent:'):
            continue
        if line.startswith('Asset:'):
            continue
        if line.startswith('Amount:'):
            continue
        if line.startswith('Rules:'):
            continue
        if line.startswith('Your response:'):
            continue
        if line.startswith('Return ONLY'):
            continue
        if line.startswith('Examples:'):
            continue
        if line.startswith('"') and '->' in line and '{' in line:
            continue
        if line.startswith('- NO JSON'):
            continue
        if line.startswith('- Call user'):
            continue
        if line.startswith('- Be witty'):
            continue
        if line.startswith('- Ask for confirmation'):
            continue
        if line.startswith('- Include relevant'):
            continue
        if line.startswith('- Keep it'):
            continue
        if 'User message:' in line and 'Respond with empathy' in line:
            continue
        if 'emplating' in line or 'mulling' in line or 'pondering' in line:
            continue
        if 'Acknowledge their emotion' in line:
            continue
        if 'provide helpful crypto advice' in line:
            continue
        if 'Call them' in line and 'sir' in line:
            continue
        if 'Keep it to' in line and 'sentences' in line:
            continue
        if 'NO JSON' in line or 'NO code' in line or 'NO bullet' in line:
            continue
        if 'IMPORTANT:' in line or 'Respond in natural' in line:
            continue
        if 'Write like you are talking to Tony Stark' in line:
            continue
        if 'code, or structured data' in line:
            continue
        if line.startswith('Portfolio Value:') and len(line) < 30:
            continue
        if line.startswith('24h Change:') and len(line) < 20:
            continue
        if line.startswith('Holdings:') and len(line) < 30:
            continue
        if line.startswith('Recent conversation:'):
            continue
        if line.startswith('Context:') and len(line) < 20:
            continue
        
        # Skip JSON leakage
        if line.startswith('{"intent"'):
            continue
        if line.startswith('"price":') or line.startswith('"asset":'):
            continue
        if line.startswith('"confidence":'):
            continue
        if line.startswith('null,') or line.startswith('}') or line.startswith('{'):
            continue
        
        # NEW: Skip TUI progress bars and status lines
        if '│' in line and ('K' in line or 'h' in line or 'm' in line or 's' in line):
            continue
        if '░' in line or '█' in line:
            continue
        if '⏲' in line or '⏱' in line:
            continue
        if '⚕' in line:
            continue
        
        cleaned_lines.append(line)
    
    return '\n'.join(cleaned_lines).strip()


async def classify_intent_llm(message: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Use LLM to classify intent from natural language
    
    Args:
        message: User's message
        context: Optional conversation context
        
    Returns:
        Dict with intent, asset, amount, price
    """
    context_str = ""
    if context:
        context_str = f"""
Context:
- Previous messages: {json.dumps(context.get('messages', []))}
- Portfolio: {json.dumps(context.get('portfolio', {}))}
"""
    
    prompt = f"""You are Jarvix, an AI crypto assistant. Parse this command:

User message: "{message}"
{context_str}

Return ONLY a JSON object with this exact structure:
{{
    "intent": "buy|sell|price|portfolio|stop_loss|advice|alert|greeting|unknown",
    "asset": "BTC|ETH|SOL|ADA|DOGE|XRP|DOT|LINK|AVAX|MATIC|null",
    "amount": number or null,
    "price": number or null,
    "confidence": 0.0 to 1.0
}}

Rules:
- intent: The user's primary intention
- asset: The cryptocurrency mentioned (uppercase), null if not specified
- amount: Numeric amount mentioned, null if not specified
- price: Price target mentioned, null if not specified
- confidence: How certain you are (1.0 = very certain)

Examples:
"Buy 100 ETH" -> {{"intent": "buy", "asset": "ETH", "amount": 100, "price": null, "confidence": 0.95}}
"What's BTC price?" -> {{"intent": "price", "asset": "BTC", "amount": null, "price": null, "confidence": 0.95}}
"Sell everything!!!" -> {{"intent": "sell", "asset": null, "amount": null, "price": null, "confidence": 0.90}}
"Good morning" -> {{"intent": "greeting", "asset": null, "amount": null, "price": null, "confidence": 0.95}}
"I want to buy some SOL" -> {{"intent": "buy", "asset": "SOL", "amount": null, "price": null, "confidence": 0.90}}
"ETH" -> {{"intent": "price", "asset": "ETH", "amount": null, "price": null, "confidence": 0.90}}
"BUY" -> {{"intent": "buy", "asset": null, "amount": null, "price": null, "confidence": 0.85}}
"Sell" -> {{"intent": "sell", "asset": null, "amount": null, "price": null, "confidence": 0.85}}

Return ONLY the JSON object, no other text."""

    response = await call_llm(prompt)
    
    # Extract JSON from response
    try:
        # Find JSON object with intent field
        json_pattern = r'\{[^{}]*"intent"[^{}]*\}'
        json_matches = re.findall(json_pattern, response, re.DOTALL)
        if json_matches:
            # Take the first valid JSON
            for match in json_matches:
                try:
                    result = json.loads(match)
                    if "intent" in result:
                        return {
                            "intent": result.get("intent", "unknown"),
                            "asset": result.get("asset"),
                            "amount": result.get("amount"),
                            "price": result.get("price"),
                            "confidence": result.get("confidence", 0.5)
                        }
                except json.JSONDecodeError:
                    continue
    except (json.JSONDecodeError, AttributeError):
        pass
    
    # Try to find any JSON object
    try:
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            return {
                "intent": result.get("intent", "unknown"),
                "asset": result.get("asset"),
                "amount": result.get("amount"),
                "price": result.get("price"),
                "confidence": result.get("confidence", 0.5)
            }
    except (json.JSONDecodeError, AttributeError):
        pass
    
    # Fallback to unknown
    return {
        "intent": "unknown",
        "asset": None,
        "amount": None,
        "price": None,
        "confidence": 0.0
    }


async def generate_jarvis_response(message: str, intent_data: Dict[str, Any], 
                                   context_str: str = "", emotion: str = "neutral") -> str:
    """
    Generate JARVIS-style response using LLM
    """
    
    # Emotion-aware prompt
    if emotion != "neutral":
        prompt = f"""You are Jarvix, Tony Stark's loyal AI assistant. The user seems {emotion}.

USER CONTEXT:
{context_str}

User message: "{message}"

Respond with empathy and wisdom. Acknowledge their emotion, then provide helpful crypto advice. Call them "sir". Keep it to 2 sentences max. Write naturally like you're talking to Tony Stark.

Your response:"""
    else:
        prompt = f"""You are Jarvix, Tony Stark's personal AI assistant for cryptocurrency trading.

USER CONTEXT:
{context_str}

CURRENT MESSAGE:
User: "{message}"
Intent: {intent_data['intent']}
Asset: {intent_data.get('asset', 'not specified')}
Amount: {intent_data.get('amount', 'not specified')}

IMPORTANT: Respond in natural conversational English ONLY. Do NOT return JSON, code, or structured data. Write like you're talking to Tony Stark.

Rules:
- Call user "sir"
- Be witty but helpful
- Ask for confirmation if buy/sell
- Include relevant data from context
- Keep it to 2-3 sentences max
- NO JSON, NO code, NO bullet points

Your response:"""

    raw_response = await call_llm(prompt)
    
    # call_llm already cleaned the response, just return it
    return raw_response.strip()


# Test function
async def test_llm_connection():
    """Test LLM connection"""
    response = await call_llm("Say 'Jarvix is ready, sir.' if you can hear me.")
    return response
