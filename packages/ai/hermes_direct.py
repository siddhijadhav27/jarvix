"""
Direct Hermes LLM Client - Bypass TUI
Uses Hermes AIAgent internally
"""

import os
import sys
import asyncio
from typing import Optional, Dict, Any

# Add hermes-agent to path
sys.path.insert(0, '/home/siddhi/.hermes/hermes-agent')

async def call_hermes_llm(prompt: str, timeout: float = 30.0) -> str:
    """
    Call LLM via Hermes AIAgent directly (no TUI)
    """
    try:
        # Import here to avoid startup overhead
        from run_agent import AIAgent
        
        # Create agent with Kimi credentials
        agent = AIAgent(
            model="kimi-for-coding",
            provider="kimi-coding",
            max_iterations=1,  # Single turn, no tools
            quiet_mode=True,   # No TUI output
            skip_memory=True,  # Don't load conversation history
        )
        
        # Simple chat interface
        response = agent.chat(prompt)
        return response
        
    except Exception as e:
        return f"Error: {str(e)}"


# Test
if __name__ == "__main__":
    result = asyncio.run(call_hermes_llm("Say 'Jarvix is ready, sir.'"))
    print(f"Response: {result}")
