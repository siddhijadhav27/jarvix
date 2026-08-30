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
GROQ_API_KEY_BACKUP = os.getenv("GROQ_API_KEY_BACKUP", "")


def _load_tokens() -> list:
    """Primary key first, then backup -- both read fresh from .env if the
    process env vars weren't set, since main.py loads this before any
    dotenv-style loader might run."""
    primary, backup = GROQ_API_KEY, GROQ_API_KEY_BACKUP
    if not primary or not backup:
        try:
            with open(os.path.join(os.path.dirname(__file__), "../../.env")) as f:
                for line in f:
                    if not primary and line.startswith("GROQ_API_KEY="):
                        primary = line.strip().split("=", 1)[1]
                    elif not backup and line.startswith("GROQ_API_KEY_BACKUP="):
                        backup = line.strip().split("=", 1)[1]
        except Exception:
            pass
    return [t for t in (primary, backup) if t]


async def call_llm(prompt: str, timeout: float = 30.0) -> str:
    """
    Call LLM via Groq API. Same interface as github_models_client.call_llm
    so it's a drop-in replacement for intent.py's _classify_with_llm.

    Tries the primary key first; if Groq returns 429 (rate limit or quota
    exhausted), retries once with the backup key before giving up -- so a
    used-up free-tier key doesn't stop classification mid-session.
    """
    tokens = _load_tokens()
    if not tokens:
        return "Error: No Groq API key configured."

    last_error = "Error: No Groq API key configured."

    for token in tokens:
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
                "max_tokens": 150,  # a classification response is ~30-50 tokens; capped tighter to stay well under the 8000 TPM free-tier limit
                "reasoning_effort": "low",  # gpt-oss is a reasoning model -- without this it can burn the whole max_tokens budget on hidden chain-of-thought and return empty content (finish_reason "length") instead of the JSON
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(GROQ_URL, headers=headers, json=payload, timeout=timeout)
                if response.status_code == 429 and token != tokens[-1]:
                    last_error = f"Error: Groq API returned 429: {response.text[:200]}"
                    continue  # try the next key
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]

        except httpx.ConnectError:
            last_error = "Error: Cannot connect to Groq API."
        except httpx.TimeoutException:
            last_error = "Error: LLM request timed out."
        except httpx.HTTPStatusError as e:
            last_error = f"Error: Groq API returned {e.response.status_code}: {e.response.text[:200]}"
        except Exception as e:
            last_error = f"Error: {str(e)}"

    return last_error


# Test
async def test_groq():
    """Test Groq connection"""
    result = await call_llm("Say 'Groq is ready' if you can hear me.")
    return result
