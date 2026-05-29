"""
Simplified router for testing - uses persistent bridge directly
"""

import aiohttp
import asyncio

async def simple_chat(message: str) -> str:
    """Simple chat via persistent bridge"""
    timeout = aiohttp.ClientTimeout(total=10, connect=2)
    
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(
            "http://localhost:8082/chat",
            json={"message": message}
        ) as response:
            if response.status == 200:
                result = await response.json()
                return result.get("response", "")
            return ""

if __name__ == "__main__":
    import asyncio
    result = asyncio.run(simple_chat("What is Bitcoin?"))
    print(f"Response: {result[:200]}")
