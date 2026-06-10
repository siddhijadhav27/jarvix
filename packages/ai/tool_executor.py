"""
Tool Executor for Jarvix - Step 2
Executes tools based on universal intent classification.
"""

import json
import re
import os
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from .openrouter_client import call_openrouter
from .llm_client import call_llm


@dataclass
class ToolResult:
    """Result of a tool execution"""
    success: bool
    data: Any
    error: Optional[str] = None
    tool_name: str = ""


class ToolRegistry:
    """Registry of available tools"""
    
    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._schemas: Dict[str, Dict] = {}
    
    def register(self, name: str, func: Callable, schema: Dict):
        """Register a tool with its schema"""
        self._tools[name] = func
        self._schemas[name] = schema
    
    def get(self, name: str) -> Optional[Callable]:
        return self._tools.get(name)
    
    def get_schema(self, name: str) -> Optional[Dict]:
        return self._schemas.get(name)
    
    def list_tools(self) -> List[str]:
        return list(self._tools.keys())
    
    def get_all_schemas(self) -> List[Dict]:
        """Get all tool schemas for LLM function calling"""
        schemas = []
        for name, schema in self._schemas.items():
            schemas.append({
                "name": name,
                "description": schema.get("description", ""),
                "parameters": schema.get("parameters", {})
            })
        return schemas


# Global registry
_registry = None

def get_registry() -> ToolRegistry:
    """Get or create global tool registry"""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
        _register_default_tools()
    return _registry


def _register_default_tools():
    """Register all default tools"""
    registry = get_registry()
    
    # Web Search Tool
    registry.register(
        "web_search",
        _web_search_impl,
        {
            "description": "Search the web for information",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    }
                },
                "required": ["query"]
            }
        }
    )
    
    # Weather Tool
    registry.register(
        "weather",
        _weather_impl,
        {
            "description": "Get weather information for a location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City or location name"
                    }
                },
                "required": ["location"]
            }
        }
    )
    
    # Calculator Tool
    registry.register(
        "calculator",
        _calculator_impl,
        {
            "description": "Perform mathematical calculations",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Mathematical expression to evaluate"
                    }
                },
                "required": ["expression"]
            }
        }
    )
    
    # Crypto Price Tool
    registry.register(
        "crypto_price",
        _crypto_price_impl,
        {
            "description": "Get current cryptocurrency prices",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Crypto symbol (BTC, ETH, SOL, etc.)"
                    }
                },
                "required": ["symbol"]
            }
        }
    )
    
    # Send Notification Tool
    registry.register(
        "send_notification",
        _send_notification_impl,
        {
            "description": "Send a notification to the user",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Notification message"
                    },
                    "urgency": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                        "description": "Urgency level"
                    }
                },
                "required": ["message"]
            }
        }
    )
    
    # Set Reminder Tool
    registry.register(
        "set_reminder",
        _set_reminder_impl,
        {
            "description": "Set a reminder for the user",
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "What to remind about"
                    },
                    "time": {
                        "type": "string",
                        "description": "When to remind (e.g., 'in 30 minutes', 'tomorrow 9am')"
                    }
                },
                "required": ["task", "time"]
            }
        }
    )
    
    # File Reader Tool
    registry.register(
        "file_reader",
        _file_reader_impl,
        {
            "description": "Read contents of a file",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path to read"
                    }
                },
                "required": ["path"]
            }
        }
    )
    
    # Time/Date Tool
    registry.register(
        "get_time",
        _get_time_impl,
        {
            "description": "Get current time and date",
            "parameters": {
                "type": "object",
                "properties": {
                    "timezone": {
                        "type": "string",
                        "description": "Timezone (optional, defaults to local)"
                    }
                },
                "required": []
            }
        }
    )


# ============ Tool Implementations ============

def _web_search_impl(query: str) -> ToolResult:
    """Search the web (placeholder - would integrate with search API)"""
    # For now, return a mock result
    # In production, this would call Google Search, Bing, or DuckDuckGo API
    return ToolResult(
        success=True,
        data={
            "query": query,
            "results": [
                {"title": f"Search results for '{query}'", "snippet": "Web search would return real results here."}
            ],
            "note": "Web search requires API key configuration"
        },
        tool_name="web_search"
    )


def _weather_impl(location: str) -> ToolResult:
    """Get weather (placeholder - would integrate with weather API)"""
    # Mock weather data
    mock_weather = {
        "mumbai": {"temp": 32, "condition": "Sunny", "humidity": 75},
        "delhi": {"temp": 38, "condition": "Hot", "humidity": 45},
        "london": {"temp": 15, "condition": "Cloudy", "humidity": 80},
        "new york": {"temp": 22, "condition": "Clear", "humidity": 60},
    }
    
    location_lower = location.lower()
    weather = mock_weather.get(location_lower, {"temp": 25, "condition": "Unknown", "humidity": 50})
    
    return ToolResult(
        success=True,
        data={
            "location": location,
            "temperature": weather["temp"],
            "condition": weather["condition"],
            "humidity": weather["humidity"],
            "unit": "celsius"
        },
        tool_name="weather"
    )


def _calculator_impl(expression: str) -> ToolResult:
    """Evaluate mathematical expression safely"""
    try:
        # Sanitize expression - only allow safe operations
        allowed_chars = set('0123456789+-*/().%^ ')
        if not all(c in allowed_chars for c in expression):
            return ToolResult(
                success=False,
                data=None,
                error="Invalid characters in expression",
                tool_name="calculator"
            )
        
        # Safe eval with limited operations
        result = eval(expression, {"__builtins__": {}}, {})
        
        return ToolResult(
            success=True,
            data={"expression": expression, "result": result},
            tool_name="calculator"
        )
    except Exception as e:
        return ToolResult(
            success=False,
            data=None,
            error=str(e),
            tool_name="calculator"
        )


def _crypto_price_impl(symbol: str) -> ToolResult:
    """Get crypto price (mock data for now)"""
    mock_prices = {
        "BTC": 95000, "ETH": 3500, "SOL": 148,
        "ADA": 0.45, "DOGE": 0.12, "XRP": 0.62,
        "DOT": 7.2, "LINK": 14.5, "AVAX": 35,
        "MATIC": 0.58, "BNB": 605
    }
    
    symbol_upper = symbol.upper()
    price = mock_prices.get(symbol_upper)
    
    if price:
        return ToolResult(
            success=True,
            data={"symbol": symbol_upper, "price_usd": price, "change_24h": "+2.4%"},
            tool_name="crypto_price"
        )
    else:
        return ToolResult(
            success=False,
            data=None,
            error=f"Price not available for {symbol}",
            tool_name="crypto_price"
        )


def _send_notification_impl(message: str, urgency: str = "medium") -> ToolResult:
    """Send notification (placeholder)"""
    return ToolResult(
        success=True,
        data={"message": message, "urgency": urgency, "sent": True},
        tool_name="send_notification"
    )


def _set_reminder_impl(task: str, time: str) -> ToolResult:
    """Set reminder (placeholder)"""
    return ToolResult(
        success=True,
        data={"task": task, "time": time, "set": True},
        tool_name="set_reminder"
    )


def _file_reader_impl(path: str) -> ToolResult:
    """Read file contents"""
    try:
        # Security: only allow reading from specific directories
        allowed_prefixes = [
            "/home/siddhi/jarvix-backend/",
            "/home/siddhi/.hermes/",
        ]
        
        resolved = os.path.abspath(path)
        if not any(resolved.startswith(prefix) for prefix in allowed_prefixes):
            return ToolResult(
                success=False,
                data=None,
                error="Access denied: file outside allowed directories",
                tool_name="file_reader"
            )
        
        with open(path, 'r') as f:
            content = f.read()
        
        return ToolResult(
            success=True,
            data={"path": path, "content": content[:2000]},  # Limit content size
            tool_name="file_reader"
        )
    except Exception as e:
        return ToolResult(
            success=False,
            data=None,
            error=str(e),
            tool_name="file_reader"
        )


def _get_time_impl(timezone: Optional[str] = None) -> ToolResult:
    """Get current time"""
    from datetime import datetime
    import pytz
    
    try:
        if timezone:
            tz = pytz.timezone(timezone)
            now = datetime.now(tz)
        else:
            now = datetime.now()
        
        return ToolResult(
            success=True,
            data={
                "datetime": now.isoformat(),
                "date": now.strftime("%Y-%m-%d"),
                "time": now.strftime("%H:%M:%S"),
                "timezone": timezone or "local"
            },
            tool_name="get_time"
        )
    except Exception as e:
        return ToolResult(
            success=False,
            data=None,
            error=str(e),
            tool_name="get_time"
        )


# ============ Tool Execution Engine ============

async def execute_tool(tool_name: str, params: Dict[str, Any]) -> ToolResult:
    """Execute a tool by name with parameters"""
    registry = get_registry()
    tool_func = registry.get(tool_name)
    
    if not tool_func:
        return ToolResult(
            success=False,
            data=None,
            error=f"Tool '{tool_name}' not found",
            tool_name=tool_name
        )
    
    try:
        # Check if function is async
        import asyncio
        if asyncio.iscoroutinefunction(tool_func):
            result = await tool_func(**params)
        else:
            result = tool_func(**params)
        
        if isinstance(result, ToolResult):
            return result
        else:
            return ToolResult(success=True, data=result, tool_name=tool_name)
    except Exception as e:
        return ToolResult(
            success=False,
            data=None,
            error=str(e),
            tool_name=tool_name
        )


async def parse_and_execute_tools(
    message: str,
    suggested_tools: List[str],
    use_llm: bool = True
) -> Dict[str, Any]:
    """
    Parse message to extract tool parameters and execute tools.
    Uses execution override (Option C) to correct wrong tool suggestions.
    
    Returns:
        {
            "executed": List[ToolResult],
            "response": str,  # Natural language response
            "failed": List[str]
        }
    """
    registry = get_registry()
    executed = []
    failed = []
    
    # Option C: Execution override - check message content before executing
    corrected_tools = _correct_tools_from_message(message, suggested_tools)
    
    # Try to extract parameters from message for each suggested tool
    for tool_name in corrected_tools:
        tool_func = registry.get(tool_name)
        schema = registry.get_schema(tool_name)
        
        if not tool_func or not schema:
            failed.append(f"{tool_name}: not found")
            continue
        
        # Extract parameters from message using simple regex
        params = _extract_params_from_message(message, tool_name, schema)
        
        if params:
            result = await execute_tool(tool_name, params)
            executed.append(result)
            
            if not result.success:
                failed.append(f"{tool_name}: {result.error}")
        else:
            failed.append(f"{tool_name}: could not extract parameters")
    
    # Generate natural language response
    response = _generate_tool_response(executed, failed, message)
    
    return {
        "executed": executed,
        "response": response,
        "failed": failed
    }


def _correct_tools_from_message(message: str, suggested_tools: List[str]) -> List[str]:
    """
    Option C: Override wrong tool suggestions based on message content.
    If LLM suggested web_search but message is clearly about weather/time/math,
    correct to the right tool.
    """
    msg_lower = message.lower()
    
    # Check for weather keywords
    if re.search(r'\b(weather|temperature|rain|sunny|forecast|mausam|barish)\b', msg_lower):
        return ["weather"]
    
    # Check for time keywords
    if re.search(r'\b(time|date|day|aaj kya din hai|what day|current time)\b', msg_lower):
        return ["get_time"]
    
    # Check for calculator keywords
    if re.search(r'\b(calculate|compute|sum|convert|kitna hoga|what is \d+ \+|\d+ \* \d+)\b', msg_lower):
        return ["calculator"]
    
    # Check for crypto price keywords
    if re.search(r'\b(price of|what is the price|how much is)\s+(btc|eth|sol|ada|doge|xrp|dot|link|avax|matic|bnb)\b', msg_lower):
        return ["crypto_price"]
    
    # Check for reminder keywords
    if re.search(r'\b(remind|reminder|notify me|alert me|yaad dilana)\b', msg_lower):
        return ["set_reminder"]
    
    # Check for message/notification keywords
    if re.search(r'\b(send|message|email|telegram|whatsapp|text|forward)\b', msg_lower):
        return ["send_notification"]
    
    # If no override matched, use suggested tools but filter out web_search if other specific tools exist
    if len(suggested_tools) > 1 and "web_search" in suggested_tools:
        specific_tools = [t for t in suggested_tools if t != "web_search"]
        if specific_tools:
            return specific_tools
    
    return suggested_tools if suggested_tools else ["web_search"]


def _extract_params_from_message(message: str, tool_name: str, schema: Dict) -> Optional[Dict]:
    """Extract tool parameters from natural language message"""
    message_lower = message.lower()
    params = {}
    
    properties = schema.get("parameters", {}).get("properties", {})
    required = schema.get("parameters", {}).get("required", [])
    
    if tool_name == "weather":
        # Extract location
        location_patterns = [
            r'(?:weather|temperature|mausam)\s+(?:in|at|for)\s+([a-zA-Z\s]+)',
            r'([a-zA-Z\s]+)\s+(?:weather|temperature|mausam)',
        ]
        for pattern in location_patterns:
            match = re.search(pattern, message_lower)
            if match:
                params["location"] = match.group(1).strip().title()
                break
        if "location" not in params:
            params["location"] = "Mumbai"  # Default
    
    elif tool_name == "calculator":
        # Extract mathematical expression
        calc_patterns = [
            r'(?:calculate|compute|what is|kitna hoga)\s+(.+?)(?:\?|$)',
            r'(\d+\s*[+\-*/]\s*\d+)',
        ]
        for pattern in calc_patterns:
            match = re.search(pattern, message_lower)
            if match:
                params["expression"] = match.group(1).strip()
                break
    
    elif tool_name == "crypto_price":
        # Extract symbol
        symbol_match = re.search(r'\b(btc|eth|sol|ada|doge|xrp|dot|link|avax|matic|bnb)\b', message_lower)
        if symbol_match:
            params["symbol"] = symbol_match.group(1).upper()
    
    elif tool_name == "web_search":
        # Extract query
        search_patterns = [
            r'(?:search|google|look up|find)\s+(?:for\s+)?(.+?)(?:\?|$)',
            r'(?:what is|who is|latest|news about)\s+(.+?)(?:\?|$)',
        ]
        for pattern in search_patterns:
            match = re.search(pattern, message_lower)
            if match:
                params["query"] = match.group(1).strip()
                break
        if "query" not in params:
            params["query"] = message  # Use entire message as query
    
    elif tool_name == "get_time":
        # Optional timezone
        tz_match = re.search(r'(?:time|date)\s+(?:in|at)\s+([a-zA-Z/]+)', message_lower)
        if tz_match:
            params["timezone"] = tz_match.group(1)
    
    elif tool_name == "send_notification":
        params["message"] = message
        params["urgency"] = "medium"
    
    elif tool_name == "set_reminder":
        reminder_match = re.search(r'(?:remind me to|reminder for)\s+(.+?)(?:\s+(?:at|in|on)\s+(.+))?$', message_lower)
        if reminder_match:
            params["task"] = reminder_match.group(1).strip()
            params["time"] = reminder_match.group(2) if reminder_match.group(2) else "in 1 hour"
    
    # Check if all required params are present
    missing = [p for p in required if p not in params]
    if missing:
        return None
    
    return params if params else None


def _generate_tool_response(executed: List[ToolResult], failed: List[str], original_message: str) -> str:
    """Generate natural language response from tool results"""
    
    if not executed and failed:
        return f"I apologize, sir. I could not execute the requested action. {failed[0]}"
    
    responses = []
    
    for result in executed:
        if not result.success:
            continue
        
        data = result.data
        tool = result.tool_name
        
        if tool == "weather":
            responses.append(
                f"The weather in {data['location']} is {data['condition']} "
                f"with a temperature of {data['temperature']}°C."
            )
        
        elif tool == "calculator":
            responses.append(
                f"The result of {data['expression']} is {data['result']}."
            )
        
        elif tool == "crypto_price":
            responses.append(
                f"{data['symbol']} is currently trading at ${data['price_usd']:,}."
            )
        
        elif tool == "get_time":
            responses.append(
                f"The current time is {data['time']} on {data['date']}."
            )
        
        elif tool == "web_search":
            responses.append(
                f"I found information about '{data['query']}'. "
                f"{data['results'][0]['title']}: {data['results'][0]['snippet']}"
            )
        
        elif tool == "send_notification":
            responses.append("Notification sent successfully, sir.")
        
        elif tool == "set_reminder":
            responses.append(f"Reminder set for {data['time']}: {data['task']}")
    
    if responses:
        return " ".join(responses)
    
    return "I have processed your request, sir."


# Test
if __name__ == "__main__":
    import asyncio
    
    async def test():
        registry = get_registry()
        print("Available tools:", registry.list_tools())
        
        # Test weather
        result = await execute_tool("weather", {"location": "Mumbai"})
        print(f"\nWeather: {result}")
        
        # Test calculator
        result = await execute_tool("calculator", {"expression": "100 * 2.5"})
        print(f"Calculator: {result}")
    
    asyncio.run(test())
