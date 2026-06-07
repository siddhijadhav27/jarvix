"""
Direct Hermes AIAgent - No TUI, No Bridge
Uses Hermes internal AIAgent class directly
"""

import os
import sys
import asyncio
from typing import Optional

# Add hermes-agent to path
sys.path.insert(0, '/home/siddhi/.hermes/hermes-agent')

class HermesDirectLLM:
    """Direct LLM via Hermes AIAgent"""
    
    def __init__(self):
        self.agent = None
        self.initialized = False
    
    def initialize(self):
        """Initialize AIAgent with Kimi credentials"""
        if self.initialized:
            return
        
        try:
            from run_agent import AIAgent
            
            # Read API key from env
            api_key = os.environ.get('KIMI_API_KEY', '')
            if not api_key:
                # Try reading from .env file
                try:
                    with open('/home/siddhi/.hermes/.env', 'r') as f:
                        for line in f:
                            if line.startswith('KIMI_API_KEY='):
                                api_key = line.split('=', 1)[1].strip()
                                break
                except:
                    pass
            
            # Create agent with minimal config
            self.agent = AIAgent(
                model="kimi-for-coding",
                provider="kimi-coding",
                max_iterations=1,  # No tool calls
                quiet_mode=True,   # Suppress output
                skip_memory=True,  # Don't load history
                skip_context_files=True,
            )
            
            self.initialized = True
            
        except Exception as e:
            print(f"Failed to initialize AIAgent: {e}")
            raise
    
    def chat(self, message: str) -> str:
        """Send message and get response"""
        if not self.initialized:
            self.initialize()
        
        try:
            # Use simple chat interface
            response = self.agent.chat(message)
            return response
        except Exception as e:
            return f"Error: {str(e)}"


# Singleton instance
_llm = None

def get_llm() -> HermesDirectLLM:
    global _llm
    if _llm is None:
        _llm = HermesDirectLLM()
    return _llm


# Test
if __name__ == "__main__":
    llm = get_llm()
    print("Testing direct LLM...")
    result = llm.chat("Say 'Jarvix is ready, sir.' in exactly those words.")
    print(f"Response: {result}")
