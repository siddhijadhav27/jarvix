"""
Runner adapted from test_all_patterns.py (which imports a module-level
detect_intent_hybrid that no longer exists -- it's a method on
IntentClassifier now). Same pattern lists (read straight from that file so
they never drift), correct current API.
"""
import asyncio
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, 'packages'))

# Pull just the *_PATTERNS list literals out of test_all_patterns.py (its own
# top-level import is stale) rather than duplicating ~200 lines of data here.
_patterns_source_lines = []
_in_patterns_section = False
with open(os.path.join(BASE_DIR, 'test_all_patterns.py')) as f:
    for line in f:
        if line.startswith('BUY_PATTERNS'):
            _in_patterns_section = True
        if line.startswith('async def test_all_patterns'):
            break
        if _in_patterns_section:
            _patterns_source_lines.append(line)
exec(''.join(_patterns_source_lines))

from ai.intent import IntentClassifier
from ai.personality import personality_engine

async def main():
    classifier = IntentClassifier()

    results = {
        "buy": {"total": 0, "correct": 0, "fails": []},
        "sell": {"total": 0, "correct": 0, "fails": []},
        "price": {"total": 0, "correct": 0, "fails": []},
        "portfolio": {"total": 0, "correct": 0, "fails": []},
        "greeting": {"total": 0, "correct": 0, "fails": []},
        "advice": {"total": 0, "correct": 0, "fails": []},
        "alert": {"total": 0, "correct": 0, "fails": []},
        "unknown": {"total": 0, "correct": 0, "fails": []},
    }

    all_patterns = [
        (BUY_PATTERNS, "buy"),
        (SELL_PATTERNS, "sell"),
        (PRICE_PATTERNS, "price"),
        (PORTFOLIO_PATTERNS, "portfolio"),
        (GREETING_PATTERNS, "greeting"),
        (ADVICE_PATTERNS, "advice"),
        (ALERT_PATTERNS, "alert"),
    ]

    for patterns, expected_intent in all_patterns:
        for pattern in patterns:
            try:
                result = await classifier.detect_intent_hybrid(pattern, user_id="pattern_check")
                detected = result.get("intent", "ERROR")
            except Exception as e:
                detected = f"EXCEPTION: {e}"

            # Groq's free tier has a strict requests-per-minute limit; a real
            # chat user won't fire 346 messages back to back, but this test
            # script does, so pace it to get an accurate read instead of a
            # wall of 429s.
            await asyncio.sleep(2.1)

            results[expected_intent]["total"] += 1
            if detected == expected_intent:
                results[expected_intent]["correct"] += 1
            else:
                results[expected_intent]["fails"].append((pattern, detected))

    for pattern in EMOTIONAL_PATTERNS:
        try:
            result = await classifier.detect_intent_hybrid(pattern, user_id="pattern_check")
            detected = result.get("intent", "ERROR")
        except Exception as e:
            detected = f"EXCEPTION: {e}"
        emotion = personality_engine.detect_emotion(pattern)
        results["unknown"]["total"] += 1
        if detected != "unknown" or emotion != "neutral":
            results["unknown"]["correct"] += 1
        else:
            results["unknown"]["fails"].append((pattern, detected))

    print("=" * 80)
    total_tests = total_correct = 0
    for intent, data in results.items():
        if data["total"] > 0:
            acc = (data["correct"] / data["total"]) * 100
            total_tests += data["total"]
            total_correct += data["correct"]
            print(f"{intent.upper()}: {data['correct']}/{data['total']} ({acc:.1f}%)")
            for p, d in data["fails"][:8]:
                print(f"    FAIL: '{p}' -> {d}")
            if len(data["fails"]) > 8:
                print(f"    ... and {len(data['fails']) - 8} more")

    overall = (total_correct / total_tests) * 100 if total_tests else 0
    print("=" * 80)
    print(f"OVERALL: {total_correct}/{total_tests} ({overall:.1f}%)")

if __name__ == "__main__":
    asyncio.run(main())
