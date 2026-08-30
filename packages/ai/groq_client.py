"""
Groq LLM Client for Jarvix
Replaces github_models_client.py — GitHub Models was fully retired July 30, 2026.
Groq's API is OpenAI-compatible. Model list was pulled live from
/openai/v1/models (2026-08-30) since docs/training data go stale fast here --
openai/gpt-oss-20b was picked as a fast, general-purpose instruct model for
per-message intent classification.
"""

import httpx
import os
from typing import Optional

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "openai/gpt-oss-20b"
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")


def _load_token() -> str:
    token = GROQ_API_KEY
    if not token:
        try:
            with open(os.path.join(os.path.dirname(__file__), "../../.env")) as f:
                for line in f:
                    if line.startswith("GROQ_API_KEY="):
                        token = line.strip().split("=", 1)[1]
                        break
        except Exception:
            pass
    return token


async def call_llm(prompt: str, timeout: float = 30.0) -> str:
    """
    Call LLM via Groq API. Same interface as github_models_client.call_llm
    so it's a drop-in replacement for intent.py's _classify_with_llm.
    """
    token = _load_token()

    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }

        payload = {
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": "You are a crypto trading assistant. Return ONLY valid JSON."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
            "max_tokens": 500,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(GROQ_URL, headers=headers, json=payload, timeout=timeout)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

    except httpx.ConnectError:
        return "Error: Cannot connect to Groq API."
    except httpx.TimeoutException:
        return "Error: LLM request timed out."
    except httpx.HTTPStatusError as e:
        return f"Error: Groq API returned {e.response.status_code}: {e.response.text[:200]}"
    except Exception as e:
        return f"Error: {str(e)}"


# Test
async def test_groq():
    """Test Groq connection"""
    result = await call_llm("Say 'Groq is ready' if you can hear me.")
    return result
