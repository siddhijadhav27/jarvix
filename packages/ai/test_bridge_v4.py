"""Sync test suite for Bridge v4"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from persistent_bridge_v4 import BridgeManager

# Initialize once
manager = BridgeManager(pool_size=2)
manager.initialize()

def run_test(name, message, session_id, max_latency=8.0):
    """Run a single test"""
    print(f"\\n🧪 {name}")
    
    start = time.time()
    bridge = manager.get_session(session_id)
    response = bridge.send(message)
    latency = time.time() - start
    
    status = "✅ PASS" if latency < max_latency else "❌ FAIL"
    print(f"   {status} | Latency: {latency:.1f}s | Response: {response[:60]}")
    
    return {
        "name": name,
        "latency": latency,
        "response": response,
        "pass": latency < max_latency
    }

# Run all tests
results = []

# Group 1: Simple Commands
results.append(run_test("Test 1: Buy ETH", "Buy 100 ETH", "test_1", 8.0))
results.append(run_test("Test 2: Sell BTC", "Sell 25% of my BTC", "test_2", 8.0))
results.append(run_test("Test 3: Portfolio", "What's my portfolio?", "test_3", 8.0))
results.append(run_test("Test 4: Price", "Price of SOL", "test_4", 8.0))

# Group 2: Multi-turn (same session)
print("\\n🧪 Test 5: Multi-turn (same session)")
start = time.time()
bridge = manager.get_session("test_5")
r1 = bridge.send("Buy ETH")
latency1 = time.time() - start

start = time.time()
r2 = bridge.send("100")
latency2 = time.time() - start

print(f"   Turn 1: {latency1:.1f}s | {r1[:60]}")
print(f"   Turn 2: {latency2:.1f}s | {r2[:60]}")

results.append({
    "name": "Test 5: Multi-turn",
    "latency": latency1 + latency2,
    "pass": latency2 < 5.0  # Second turn should be fast
})

# Group 3: JSON
results.append(run_test("Test 6: JSON Classification", "Classify: Buy 100 ETH. Return JSON only.", "test_6", 8.0))

# Group 4: Edge cases
results.append(run_test("Test 7: Bitcoin question", "What is Bitcoin?", "test_7", 8.0))
results.append(run_test("Test 8: Market analysis", "Analyze ETH market", "test_8", 8.0))

# Summary
print("\\n" + "="*60)
print("📊 TEST SUMMARY")
print("="*60)

passed = sum(1 for r in results if r["pass"])
total = len(results)

for r in results:
    status = "✅" if r["pass"] else "❌"
    print(f"{status} {r['name']}: {r['latency']:.1f}s")

print(f"\\n📈 Results: {passed}/{total} passed ({passed/total*100:.0f}%)")

# Cleanup
for i in range(1, 9):
    manager.destroy_session(f"test_{i}")

if passed == total:
    print("\\n🎉 ALL TESTS PASSED!")
else:
    print(f"\\n⚠️ {total - passed} tests failed")
