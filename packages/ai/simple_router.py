"""
Simplified router - uses persistent bridge and extracts clean responses
"""

import aiohttp
import asyncio
import re

def simple_chat(message: str) -> str:
    """Simple chat via persistent bridge with response extraction (sync)"""
    import requests
    
    try:
        response = requests.post(
            "http://localhost:8082/chat",
            json={"message": message},
            timeout=25
        )
        if response.status_code == 200:
            result = response.json()
            raw = result.get("response", "")
            
            # Extract JSON if present
            json_match = re.search(r'\{"intent"[^}]*\}', raw, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                # Remove newlines from inside JSON
                json_str = json_str.replace('\n', '').replace('\r', '')
                return json_str
            
            # Find longest non-UI line
            # Remove UI artifacts
            raw = re.sub(r"[^\x20-\x7E]", "", raw)
            lines = raw.split('\n')
            longest = ''
            for line in lines:
                stripped = line.strip()
                if len(stripped) > len(longest) and not any(x in stripped for x in [
                    'kimi-for-coding', 'msg=interrupt', '⚕', '⏱', '⏲',
                    '───', '❯', 'Available Tools', 'Available Skills'
                ]):
                    longest = stripped
            
            return longest if longest else raw
        return ""
    except Exception as e:
        print(f"[DEBUG] simple_chat error: {e}")
        return ""

if __name__ == "__main__":
    import asyncio
    result = asyncio.run(simple_chat("What is Bitcoin?"))
    print(f"Response: {result[:200]}")
