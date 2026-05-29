# test_bridge_v4_fixed.py
"""Fixed test suite with fast path intent classification"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from persistent_bridge_v4 import BridgeManager
from fast_intent import classify_fast, classify_with_fallback

# Initialize once
manager = BridgeManager(pool_size=2)
manager.initialize()

# Timing targets
LATENCY_TARGETS = {
    "greeting": 1.0,
    "portfolio": 2.0,
    "price": 2.0,
    "buy_sell": 5.0,
    "stop_loss": 5.0,
    "advice": 8.0,
    "market_analysis": 8.0,
    "multi_turn_t2": 1.0,
}

def run_test(name, message, session_id, intent_type="general"):
    """Run a single test with fast path"""
    print(f"\n🧪 {name}")
    
    start = time.time()
    
    # Try fast path first
    result = classify_fast(message)
    
    if result:
        # Fast path — no LLM needed
        latency = time.time() - start
        target = LATENCY_TARGETS.get(intent_type, 5.0)
        status = "✅ PASS" if latency < target else "❌ FAIL"
        print(f"   {status} | Fast path: {latency*1000:.1f}ms | Intent: {result['intent']}")
        return {
            "name": name,
            "latency": latency,
            "intent": result["intent"],
            "fast_path": True,
            "pass": latency < target
        }
    else:
        # Slow path — use bridge
        bridge = manager.get_session(session_id)
        response = bridge.send(message)
        latency = time.time() - start
        
        target = LATENCY_TARGETS.get(intent_type, 8.0)
        status = "✅ PASS" if latency < target else "❌ FAIL"
        print(f"   {status} | LLM path: {latency:.1f}s | Response: {response[:50]}")
        return {
            "name": name,
            "latency": latency,
            "response": response,
            "fast_path": False,
            "pass": latency < target
        }

# Run all tests
results = []

print("🚀 BRIDGE V4 FIXED TESTS")
print("=" * 60)

# Group 1: Fast path tests (should be instant)
results.append(run_test("Test 1: Price of BTC", "Price of BTC", "test_1", "price"))
results.append(run_test("Test 2: Portfolio", "What's my portfolio?", "test_2", "portfolio"))
results.append(run_test("Test 3: Greeting", "Hi Jarvix", "test_3", "greeting"))

# Group 2: Buy/Sell (fast path)
results.append(run_test("Test 4: Buy ETH", "Buy 100 ETH", "test_4", "buy_sell"))
results.append(run_test("Test 5: Sell BTC", "Sell 25% of my BTC", "test_5", "buy_sell"))

# Group 3: Complex (LLM path)
results.append(run_test("Test 6: Stop Loss", "Set stop-loss for ETH at $2000", "test_6", "stop_loss"))
results.append(run_test("Test 7: Advice", "Should I buy SOL now?", "test_7", "advice"))

# Group 4: Market analysis (LLM with timeout)
results.append(run_test("Test 8: Market Analysis", "Analyze ETH market", "test_8", "market_analysis"))

# Summary
print("\n" + "=" * 60)
print("📊 TEST SUMMARY")
print("=" * 60)

passed = sum(1 for r in results if r["pass"])
total = len(results)

for r in results:
    status = "✅" if r["pass"] else "❌"
    path = "FAST" if r.get("fast_path") else "LLM"
    latency = f"{r['latency']*1000:.1f}ms" if r.get("fast_path") else f"{r['latency']:.1f}s"
    print(f"{status} {r['name']}: {latency} [{path}]")

print(f"\n📈 Results: {passed}/{total} passed ({passed/total*100:.0f}%)")

# Cleanup
for i in range(1, 9):
    manager.destroy_session(f"test_{i}")

if passed == total:
    print("\n🎉 ALL TESTS PASSED!")
else:
    print(f"\n⚠️ {total - passed} tests failed")
