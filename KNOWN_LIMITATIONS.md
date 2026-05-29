# Known Limitations

## Current LLM Status

| Model | Status | Notes |
|-------|--------|-------|
| **Kimi** | ✅ Active | Via Hermes Persistent Bridge (port 8082) |
| **Claude** | ⏳ Pending | Waiting for API key |
| **GPT-4** | ⏳ Pending | Waiting for API key |
| **Gemini** | ⏳ Pending | Waiting for API key |

## Fallback Behavior

When Kimi is unavailable, the router returns:
```json
{
    "status": "unavailable",
    "message": "AI service temporarily unavailable. Please try again in a moment.",
    "retry_after": 30
}
```

**No mock fallbacks are used.** This is intentional — fake responses in a trading platform are dangerous.

## Latency Targets

| Request Type | Target | Current |
|-------------|--------|---------|
| Simple query | < 1s | ~3s |
| Trade confirmation | < 2s | ~3s |
| Complex analysis | < 5s | ~3s |

**Note:** Latency will improve to < 2s when:
1. Response streaming is implemented (Phase 3)
2. Direct API access is available (bypassing Hermes CLI)

## When Additional Keys Are Available

Adding Claude/GPT-4/Gemini requires:
1. Set API keys in environment:
   ```bash
   export ANTHROPIC_API_KEY=sk-ant-...
   export OPENAI_API_KEY=sk-...
   export GEMINI_API_KEY=...
   ```
2. Router automatically detects and uses them
3. Fallback chain: Kimi → Claude → GPT-4 → Gemini

## Response Cleaning

All responses are cleaned to remove CLI artifacts:
- ANSI escape codes (colors)
- Progress bars
- Box-drawing characters
- UI metadata (session IDs, timestamps)

See `packages/ai/response_cleaner.py` for implementation.
