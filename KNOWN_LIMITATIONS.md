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

## Latency — Current Reality

### End-to-End Command Execution
| Step | Latency | Notes |
|------|---------|-------|
| Intent Classification | 1-2ms | Regex fast path |
| Acknowledgment | <100ms | Immediate user feedback |
| Cache Hit | <10ms | After first call |
| **Full LLM Execution** | **8-10s** | **Hermes Bridge → Kimi** |
| **End-to-End Total** | **~10s** | **Realistic baseline** |

### Root Cause
Current architecture routes through Hermes CLI as a bridge to Kimi API. Each request incurs Hermes initialization and session management overhead.

### Mitigations In Place
- **Response caching** (30s TTL for prices, 5min for analysis)
- **Immediate acknowledgment** (user sees response in <100ms)
- **Pre-warmed session pool** (eliminates cold start overhead)
- **Fast path intent** (regex for 90%+ of commands)

### Real Fix
Direct Kimi API key will reduce latency to 2-3s. Targeted for Phase 2 before live trading is enabled.

### Impact on Features
| Feature | Status | Notes |
|---------|--------|-------|
| Portfolio queries | ✅ Acceptable | Cached after first call |
| Price queries | ✅ Acceptable | Cached, 30s TTL |
| Trade execution | ✅ Acceptable | Confirmation flow buys time |
| **Voice commands** | **❌ BLOCKED** | **10s too slow for voice UX** |

**Voice cannot launch at 10 seconds.** Must be resolved before Phase 3 (Voice).

### Honest Timing Targets
```python
LATENCY_TARGETS = {
    "intent_classification":  0.005,  # 5ms — regex
    "cached_response":        0.01,   # 10ms — cache hit
    "full_llm_call":          12.0,   # 12s — real ceiling
    "acknowledged_response":  0.1,    # 100ms — immediate ack
}
```

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
