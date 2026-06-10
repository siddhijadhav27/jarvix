# test_behavioral_guard.py
"""5 tests for Behavioral Finance Guard"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from behavioral_guard import BehavioralGuard


def test_01_panic_selling():
    """
    User sells 60% of ETH after -15% price drop.
    Guard should detect panic selling and warn.
    """
    print("\n🧪 TEST 1: Panic Selling Detection")
    print("-" * 50)
    
    guard = BehavioralGuard("user_panic")
    
    result = guard.check_trade(
        intent="sell",
        asset="ETH",
        amount=6.0,  # 60% of 10 ETH holding
        price=2000,
        portfolio={"ETH": {"amount": 10.0}},
        market_change=-0.15  # -15% drop
    )
    
    print(f"   Selling 60% of ETH after -15% drop")
    print(f"   Risk Score: {result['risk_score']}")
    print(f"   Patterns: {result['patterns']}")
    
    # Verify
    assert result['risk_score'] > 0, "Should detect panic selling"
    assert 'panic_selling' in result['patterns'], "Should flag panic selling"
    assert len(result['warnings']) > 0, "Should generate warning"
    assert result['requires_confirmation'], "Should require confirmation"
    
    print("   ✅ PASS — Panic selling detected")
    return True


def test_02_fomo_buying():
    """
    User buys SOL after +20% pump.
    Guard should detect FOMO and warn.
    """
    print("\n🧪 TEST 2: FOMO Buying Detection")
    print("-" * 50)
    
    guard = BehavioralGuard("user_fomo")
    
    result = guard.check_trade(
        intent="buy",
        asset="SOL",
        amount=100.0,
        price=150,
        market_change=0.20  # +20% pump
    )
    
    print(f"   Buying SOL after +20% pump")
    print(f"   Risk Score: {result['risk_score']}")
    print(f"   Patterns: {result['patterns']}")
    
    # Verify
    assert result['risk_score'] > 0, "Should detect FOMO"
    assert 'fomo_buying' in result['patterns'], "Should flag FOMO"
    assert len(result['warnings']) > 0, "Should generate warning"
    
    print("   ✅ PASS — FOMO detected")
    return True


def test_03_normal_trade():
    """
    User makes normal trade with no emotional patterns.
    Guard should not flag anything.
    """
    print("\n🧪 TEST 3: Normal Trade (No Pattern)")
    print("-" * 50)
    
    guard = BehavioralGuard("user_normal")
    # Establish usual amount
    guard.profile.learn_from_trade("ETH", 0.5, 1000)
    
    result = guard.check_trade(
        intent="buy",
        asset="ETH",
        amount=0.5,  # Normal size
        price=2000,
        market_change=0.02  # Small move
    )
    
    print(f"   Normal buy of 0.5 ETH at +2%")
    print(f"   Risk Score: {result['risk_score']}")
    print(f"   Patterns: {result['patterns']}")
    
    # Verify
    assert result['risk_score'] == 0, "Should not flag normal trade"
    assert len(result['patterns']) == 0, "Should have no patterns"
    assert len(result['warnings']) == 0, "Should have no warnings"
    assert result['allowed'], "Should allow trade without confirmation"
    
    print("   ✅ PASS — Normal trade not flagged")
    return True


def test_04_overconfidence():
    """
    User trades 10x their usual size.
    Guard should detect overconfidence.
    """
    print("\n🧪 TEST 4: Overconfidence Detection")
    print("-" * 50)
    
    guard = BehavioralGuard("user_overconf")
    # Establish usual amount as 0.1 BTC
    guard.profile.learn_from_trade("BTC", 0.1, 5000)
    
    result = guard.check_trade(
        intent="buy",
        asset="BTC",
        amount=1.0,  # 10x usual
        price=50000,
        market_change=0.05
    )
    
    print(f"   Buying 1.0 BTC (usual: 0.1)")
    print(f"   Risk Score: {result['risk_score']}")
    print(f"   Patterns: {result['patterns']}")
    
    # Verify
    assert result['risk_score'] > 0, "Should detect overconfidence"
    assert 'overconfidence' in result['patterns'], "Should flag overconfidence"
    assert len(result['warnings']) > 0, "Should generate warning"
    
    print("   ✅ PASS — Overconfidence detected")
    return True


def test_05_combined_patterns():
    """
    User shows multiple patterns at once.
    Guard should detect all and block if score > 70.
    """
    print("\n🧪 TEST 5: Combined Patterns")
    print("-" * 50)
    
    guard = BehavioralGuard("user_combo")
    # Establish usual amount
    guard.profile.learn_from_trade("ETH", 0.1, 200)
    
    # FOMO + Overconfidence: Buying 10x usual after +20% pump
    result = guard.check_trade(
        intent="buy",
        asset="ETH",
        amount=1.0,  # 10x usual
        price=2500,
        market_change=0.20  # +20% pump
    )
    
    print(f"   Buying 1.0 ETH (10x usual) after +20% pump")
    print(f"   Risk Score: {result['risk_score']}")
    print(f"   Patterns: {result['patterns']}")
    print(f"   Warnings: {len(result['warnings'])}")
    
    # Verify
    assert len(result['patterns']) >= 2, "Should detect multiple patterns"
    assert result['risk_score'] >= 50, "Should have high risk score"
    assert result['requires_confirmation'], "Should require confirmation"
    
    print("   ✅ PASS — Multiple patterns detected")
    return True


# ─── RUN ALL TESTS ────────────────────────────────────
def run_all_tests():
    print("🚀 BEHAVIORAL FINANCE GUARD TESTS")
    print("=" * 60)
    
    tests = [
        test_01_panic_selling,
        test_02_fomo_buying,
        test_03_normal_trade,
        test_04_overconfidence,
        test_05_combined_patterns,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
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
    success = run_all_tests()
    sys.exit(0 if success else 1)
