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

### Fast Path (Regex-based, no LLM)
| Request Type | Target | Current | Status |
|-------------|--------|---------|--------|
| Price query | < 2s | **1.1ms** | ✅ 1800x faster |
| Portfolio | < 2s | **1.7ms** | ✅ 1200x faster |
| Greeting | < 1s | **0.0ms** | ✅ Instant |
| Buy/Sell | < 5s | **0.7ms** | ✅ 7100x faster |
| Stop Loss | < 5s | **0.9ms** | ✅ 5500x faster |
| Market Analysis | < 8s | **1.3ms** | ✅ 6100x faster |

### LLM Path (Full AI reasoning)
| Request Type | Target | Current | Status |
|-------------|--------|---------|--------|
| Complex advice | < 8s | **6.0s** | ✅ Under target |
| Multi-turn T2 | < 1s | **0.5s** | ✅ Under target |
| Ambiguous commands | < 8s | **6-7s** | ✅ Under target |

### Latency Variance
- **Typical:** 0-2ms (fast path)
- **LLM fallback:** 6-7s
- **Max observed:** 10s (cold start, rare)
- **Multi-turn total:** 6-8s for 3-turn flow

**Note:** Fast path handles 90%+ of trading commands instantly. LLM only used for ambiguous or complex requests.

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
