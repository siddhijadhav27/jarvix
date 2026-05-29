# test_ghost_mode.py
"""5 tests for Ghost Mode Onboarding"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ghost_portfolio import GhostPortfolio


def test_01_activation():
    """
    User signs up and gets $100K demo balance.
    """
    print("\n🧪 TEST 1: Ghost Mode Activation")
    print("-" * 50)
    
    portfolio = GhostPortfolio("user_activate")
    result = portfolio.activate()
    
    print(f"   Balance: ${result['balance']:,.2f}")
    print(f"   Days: {result['days_remaining']}")
    print(f"   Active: {portfolio.is_active}")
    
    # Verify
    assert result['balance'] == 100000.00, "Should start with $100K"
    assert result['days_remaining'] == 30, "Should be 30 days"
    assert portfolio.is_active, "Should be active"
    
    print("   ✅ PASS — $100K demo activated")
    return True


def test_02_buy_trade():
    """
    User buys 1 ETH at $2,000.
    Balance should decrease, holdings increase.
    """
    print("\n🧪 TEST 2: Buy Trade Execution")
    print("-" * 50)
    
    portfolio = GhostPortfolio("user_buy")
    portfolio.activate()
    
    result = portfolio.execute_trade("ETH", 1.0, 2000, "buy")
    
    print(f"   Buy 1 ETH @ $2,000")
    print(f"   Success: {result.get('success')}")
    print(f"   Balance: ${result.get('balance', 0):,.2f}")
    print(f"   Holdings: {result.get('holdings', {})}")
    
    # Verify
    assert result['success'], "Trade should succeed"
    assert result['balance'] == 98000.00, "Balance should be $98K"
    assert result['holdings'].get('ETH') == 1.0, "Should have 1 ETH"
    
    print("   ✅ PASS — Buy trade executed")
    return True


def test_03_portfolio_value():
    """
    Portfolio value updates with market prices.
    """
    print("\n🧪 TEST 3: Portfolio Value Calculation")
    print("-" * 50)
    
    portfolio = GhostPortfolio("user_value")
    portfolio.activate()
    portfolio.execute_trade("ETH", 1.0, 2000, "buy")
    
    # ETH price goes up to $2,200
    value = portfolio.get_portfolio_value({"ETH": 2200})
    
    print(f"   ETH price: $2,200 (bought at $2,000)")
    print(f"   Holdings value: ${value['holdings_value']:,.2f}")
    print(f"   Total value: ${value['total_value']:,.2f}")
    print(f"   P&L: ${value['pnl']:,.2f} ({value['pnl_percent']:+.2f}%)")
    
    # Verify
    assert value['holdings_value'] == 2200.00, "ETH should be worth $2,200"
    assert value['pnl'] == 200.00, "P&L should be $200"
    assert value['pnl_percent'] == 0.20, "Return should be 0.20%"
    
    print("   ✅ PASS — Portfolio value correct")
    return True


def test_04_sell_trade():
    """
    User sells 0.5 ETH at $2,200.
    Balance should increase, holdings decrease.
    """
    print("\n🧪 TEST 4: Sell Trade Execution")
    print("-" * 50)
    
    portfolio = GhostPortfolio("user_sell")
    portfolio.activate()
    portfolio.execute_trade("ETH", 1.0, 2000, "buy")
    
    result = portfolio.execute_trade("ETH", 0.5, 2200, "sell")
    
    print(f"   Sell 0.5 ETH @ $2,200")
    print(f"   Success: {result.get('success')}")
    print(f"   Balance: ${result.get('balance', 0):,.2f}")
    print(f"   Holdings: {result.get('holdings', {})}")
    
    # Verify
    assert result['success'], "Sell should succeed"
    assert result['balance'] == 99100.00, "Balance should be $99,100"
    assert result['holdings'].get('ETH') == 0.5, "Should have 0.5 ETH left"
    
    print("   ✅ PASS — Sell trade executed")
    return True


def test_05_insufficient_balance():
    """
    User tries to buy more than balance allows.
    Should return error.
    """
    print("\n🧪 TEST 5: Insufficient Balance Protection")
    print("-" * 50)
    
    portfolio = GhostPortfolio("user_poor")
    portfolio.activate()
    
    # Try to buy 10 BTC at $50K = $500K (only have $100K)
    result = portfolio.execute_trade("BTC", 10, 50000, "buy")
    
    print(f"   Try buy 10 BTC @ $50,000 = $500K")
    print(f"   Success: {result.get('success')}")
    print(f"   Error: {result.get('error')}")
    
    # Verify
    assert not result.get('success'), "Should fail"
    assert "Insufficient" in result.get('error', ''), "Should say insufficient balance"
    assert portfolio.balance_usd == 100000.00, "Balance should be unchanged"
    
    print("   ✅ PASS — Insufficient balance blocked")
    return True


# ─── RUN ALL TESTS ────────────────────────────────────
def run_all_tests():
    print("🚀 GHOST MODE ONBOARDING TESTS")
    print("=" * 60)
    
    tests = [
        test_01_activation,
        test_02_buy_trade,
        test_03_portfolio_value,
        test_04_sell_trade,
        test_05_insufficient_balance,
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
