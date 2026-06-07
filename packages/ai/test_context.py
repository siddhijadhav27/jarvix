# test_context.py
"""5 real tests for Jarvix Context Awareness + Memory"""

import sys
import os
import time
import asyncio

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from context import JarvixContext
from profile import UserProfile
from memory import ConversationMemory
from storage import get_storage


# ─── TEST 1: Pronoun Resolution ───────────────────────
async def test_01_pronoun_resolution():
    """
    User asks about ETH, then refers to it as "it".
    Jarvix should know "it" means ETH.
    """
    print("\n🧪 TEST 1: Pronoun Resolution")
    print("-" * 50)
    
    ctx = JarvixContext("test_user_1", "session_1")
    
    # Turn 1: User mentions ETH
    ctx.add_to_memory("user", "What's the price of ETH?", {"asset": "ETH"})
    ctx.add_to_memory("assistant", "ETH is $2,240")
    
    # Turn 2: User says "it" — should resolve to ETH
    message = "Should I buy it?"
    resolved = ctx.memory.resolve_references(message)
    
    print(f"   User: '{message}'")
    print(f"   Resolved: '{resolved}'")
    
    # Verify
    assert "ETH" in resolved, f"Expected ETH in resolved message, got: {resolved}"
    
    await ctx.close()
    print("   ✅ PASS — 'it' correctly resolved to ETH")
    return True


# ─── TEST 2: Learning from Trades ─────────────────────
async def test_02_learning_from_trades():
    """
    After 3 trades of 0.5 ETH, Jarvix should suggest 0.5 ETH
    when user says "Buy some ETH".
    """
    print("\n🧪 TEST 2: Learning from Trades")
    print("-" * 50)
    
    ctx = JarvixContext("test_user_2", "session_2")
    
    # Simulate 3 trades of 0.5 ETH
    ctx.learn_from_trade("ETH", 0.5, 1000)
    ctx.learn_from_trade("ETH", 0.5, 1100)
    ctx.learn_from_trade("ETH", 0.5, 1050)
    
    # Check learned amount
    suggested = ctx.profile.suggest_amount("ETH")
    print(f"   3 trades of 0.5 ETH")
    print(f"   Suggested amount: {suggested} ETH")
    
    # Verify
    assert suggested is not None, "Should have learned ETH amount"
    assert abs(suggested - 0.5) < 0.1, f"Expected ~0.5 ETH, got {suggested}"
    
    await ctx.close()
    print("   ✅ PASS — Learned amount is ~0.5 ETH")
    return True


# ─── TEST 3: Persistence Across Sessions ──────────────
async def test_03_persistence_across_sessions():
    """
    Session 2 should remember Session 1's trades.
    """
    print("\n🧪 TEST 3: Persistence Across Sessions")
    print("-" * 50)
    
    # Session 1: User trades
    ctx1 = JarvixContext("test_user_3", "session_3a")
    ctx1.learn_from_trade("BTC", 0.1, 5000)
    ctx1.learn_from_trade("BTC", 0.1, 5200)
    await ctx1.close()
    
    # Session 2: New session, same user
    ctx2 = JarvixContext("test_user_3", "session_3b")
    
    # Check if profile persisted
    btc_count = ctx2.profile.trade_counts.get("BTC", 0)
    btc_amount = ctx2.profile.suggest_amount("BTC")
    
    print(f"   Session 1: 2 BTC trades")
    print(f"   Session 2: BTC count = {btc_count}, usual = {btc_amount}")
    
    # Verify
    assert btc_count == 2, f"Expected 2 BTC trades, got {btc_count}"
    assert btc_amount is not None, "Should remember BTC amount"
    
    await ctx2.close()
    print("   ✅ PASS — Profile persisted across sessions")
    return True


# ─── TEST 4: Risk-Aware Advice ────────────────────────
async def test_04_risk_aware_advice():
    """
    Conservative user gets cautious advice.
    Aggressive user gets bold advice.
    """
    print("\n🧪 TEST 4: Risk-Aware Advice")
    print("-" * 50)
    
    # Conservative user: small trades, many assets
    conservative = JarvixContext("conservative_user", "session_4a")
    conservative.learn_from_trade("ETH", 0.1, 200)
    conservative.learn_from_trade("BTC", 0.01, 300)
    conservative.learn_from_trade("SOL", 1.0, 100)
    conservative.learn_from_trade("ADA", 100, 50)
    
    print(f"   Conservative user risk: {conservative.profile.risk_tolerance}")
    
    # Aggressive user: large trades, concentrated
    aggressive = JarvixContext("aggressive_user", "session_4b")
    aggressive.learn_from_trade("ETH", 5.0, 10000)
    aggressive.learn_from_trade("ETH", 10.0, 22000)
    aggressive.learn_from_trade("ETH", 8.0, 18000)
    
    print(f"   Aggressive user risk: {aggressive.profile.risk_tolerance}")
    
    # Verify
    assert conservative.profile.risk_tolerance == "conservative", \
        f"Expected conservative, got {conservative.profile.risk_tolerance}"
    assert aggressive.profile.risk_tolerance == "aggressive", \
        f"Expected aggressive, got {aggressive.profile.risk_tolerance}"
    
    await conservative.close()
    await aggressive.close()
    print("   ✅ PASS — Risk tolerance correctly inferred")
    return True


# ─── TEST 5: Market Context in Response ───────────────
async def test_05_market_context_in_prompt():
    """
    Prompt should include market data (price, change, sentiment).
    """
    print("\n🧪 TEST 5: Market Context in Prompt")
    print("-" * 50)
    
    ctx = JarvixContext("test_user_5", "session_5")
    
    # Build prompt for ETH
    prompt = await ctx.build_prompt(
        "Should I buy ETH?",
        "advice",
        {"asset": "ETH"}
    )
    
    print(f"   Prompt length: {len(prompt)} chars")
    
    # Check market context included
    has_price = "Price:" in prompt
    has_change = "24h Change:" in prompt or "Change:" in prompt
    has_sentiment = "Sentiment:" in prompt
    
    print(f"   Has price: {has_price}")
    print(f"   Has change: {has_change}")
    print(f"   Has sentiment: {has_sentiment}")
    
    # Verify
    assert has_price, "Prompt should include price"
    assert has_change, "Prompt should include 24h change"
    assert has_sentiment, "Prompt should include sentiment"
    
    await ctx.close()
    print("   ✅ PASS — Market context included in prompt")
    return True


# ─── RUN ALL TESTS ────────────────────────────────────
async def run_all_tests():
    print("🚀 JARVIX CONTEXT TESTS — Day 4")
    print("=" * 60)
    
    tests = [
        test_01_pronoun_resolution,
        test_02_learning_from_trades,
        test_03_persistence_across_sessions,
        test_04_risk_aware_advice,
        test_05_market_context_in_prompt,
    ]
    
    results = []
    for test in tests:
        try:
            result = await test()
            results.append((test.__name__, True, None))
        except Exception as e:
            results.append((test.__name__, False, str(e)))
            print(f"   ❌ FAIL — {e}")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result, _ in results if result)
    total = len(results)
    
    for name, result, error in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} — {name}")
        if error:
            print(f"       Error: {error}")
    
    print(f"\n📈 Results: {passed}/{total} passed ({passed/total*100:.0f}%)")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        return True
    else:
        print(f"\n⚠️ {total - passed} tests failed")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
