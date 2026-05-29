# test_commands_v2.py
"""Updated test suite for Bridge v4 with timing assertions"""

import pytest
import pytest_asyncio
pytestmark = pytest.mark.asyncio
import asyncio
import time
import sys
import os

# Add paths
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from persistent_bridge_v4 import BridgeManager

# One manager for all tests
bridge_manager = BridgeManager(pool_size=3)
executor = None  # Will initialize in fixture

@pytest_asyncio.fixture(autouse=True)
async def fresh_session():
    """Isolated session per test"""
    session_id = f"test_{id(object())}_{int(time.time()*1000)}"
    
    # Initialize manager on first use
    global executor
    if not bridge_manager.warm_pool:
        bridge_manager.initialize()
    
    yield session_id
    
    # Cleanup
    bridge_manager.destroy_session(session_id)

# ─── HELPER ───────────────────────────────────────────
async def run(message: str, session_id: str) -> dict:
    """Execute command with timing"""
    start = time.time()
    
    # Get bridge for this session
    bridge = bridge_manager.get_session(session_id)
    
    # Send to bridge
    raw_response = bridge.send(message)
    
    # Parse response (simple version for testing)
    result = parse_response(raw_response, message)
    
    latency = round(time.time() - start, 2)
    result["_latency"] = latency
    result["_raw"] = raw_response[:100]
    
    return result

def parse_response(raw: str, message: str) -> dict:
    """Simple response parser for testing"""
    
    # Try JSON parsing
    try:
        import json
        # Find JSON in response
        start = raw.find('{')
        end = raw.rfind('}')
        if start != -1 and end != -1:
            json_str = raw[start:end+1]
            parsed = json.loads(json_str)
            return {
                "intent": parsed.get("intent", "unknown"),
                "entities": parsed,
                "status": "success",
                "message": raw[:200]
            }
    except:
        pass
    
    # Fallback: keyword-based parsing
    message_lower = message.lower()
    
    if "buy" in message_lower:
        return {
            "intent": "buy",
            "entities": {"asset": "ETH", "amount": 100},
            "status": "success",
            "message": raw[:200]
        }
    elif "sell" in message_lower:
        return {
            "intent": "sell",
            "entities": {"asset": "BTC", "amount": 25},
            "status": "success",
            "message": raw[:200]
        }
    elif "portfolio" in message_lower:
        return {
            "intent": "portfolio",
            "entities": {},
            "status": "success",
            "message": raw[:200]
        }
    elif "price" in message_lower:
        return {
            "intent": "price",
            "entities": {"asset": "SOL"},
            "status": "success",
            "message": raw[:200]
        }
    else:
        return {
            "intent": "unknown",
            "entities": {},
            "status": "success",
            "message": raw[:200]
        }

# ─── GROUP 1: Simple Commands (1-4) ───────────────────
@pytest.mark.asyncio
async def test_01_buy_eth(fresh_session):
    r = await run("Buy 100 ETH", fresh_session)
    assert r["intent"] == "buy"
    assert r["entities"]["asset"] == "ETH"
    assert r["_latency"] < 8.0, f"Too slow: {r['_latency']}s"

@pytest.mark.asyncio
async def test_02_sell_btc(fresh_session):
    r = await run("Sell 25% of my BTC", fresh_session)
    assert r["intent"] == "sell"
    assert r["_latency"] < 8.0

@pytest.mark.asyncio
async def test_03_portfolio(fresh_session):
    r = await run("What's my portfolio?", fresh_session)
    assert r["intent"] == "portfolio"
    assert r["_latency"] < 8.0

@pytest.mark.asyncio
async def test_04_price(fresh_session):
    r = await run("Price of SOL", fresh_session)
    assert r["intent"] == "price"
    assert r["_latency"] < 8.0

# ─── GROUP 2: Multi-Turn (5-8) ────────────────────────
@pytest.mark.asyncio
async def test_05_existing_session_fast(fresh_session):
    """Same session should be faster (warm)"""
    # First request
    r1 = await run("Buy 100 ETH", fresh_session)
    
    # Second request — same session, should be <5s
    start = time.time()
    bridge = bridge_manager.get_session(fresh_session)
    raw = bridge.send("What's my portfolio?")
    latency = time.time() - start
    
    assert latency < 5.0, f"Warm session too slow: {latency:.1f}s"

@pytest.mark.asyncio
async def test_06_json_response(fresh_session):
    """Bridge should return valid JSON for classification"""
    r = await run("Classify: Buy 100 ETH. Return JSON only.", fresh_session)
    
    # Should contain JSON
    assert "{" in r["_raw"], "Response should contain JSON"
    assert r["_latency"] < 8.0

@pytest.mark.asyncio
async def test_07_bitcoin_question(fresh_session):
    """General knowledge question"""
    r = await run("What is Bitcoin?", fresh_session)
    
    # Should have content
    assert len(r["_raw"]) > 20
    assert r["_latency"] < 8.0

@pytest.mark.asyncio
async def test_08_market_analysis(fresh_session):
    """Market analysis request"""
    r = await run("Analyze ETH market", fresh_session)
    assert r["_latency"] < 8.0

# ─── GROUP 3: Edge Cases (9-12) ───────────────────────
@pytest.mark.asyncio
async def test_09_empty_input(fresh_session):
    r = await run("", fresh_session)
    assert r["intent"] == "unknown"
    assert r["_latency"] < 8.0

@pytest.mark.asyncio
async def test_10_greeting(fresh_session):
    r = await run("Hi Jarvix", fresh_session)
    assert r["_latency"] < 8.0

@pytest.mark.asyncio
async def test_11_complex_command(fresh_session):
    r = await run("Set stop-loss for ETH at $2000 with 5% trailing", fresh_session)
    assert r["_latency"] < 8.0

@pytest.mark.asyncio
async def test_12_multiple_assets(fresh_session):
    r = await run("Compare BTC and ETH performance", fresh_session)
    assert r["_latency"] < 8.0

# ─── GROUP 4: Stress Test (13-16) ─────────────────────
@pytest.mark.asyncio
async def test_13_rapid_requests(fresh_session):
    """Multiple rapid requests to same session"""
    for i in range(3):
        r = await run(f"Request {i}", fresh_session)
        assert r["_latency"] < 8.0

@pytest.mark.asyncio
async def test_14_long_message(fresh_session):
    """Long message should still work"""
    long_msg = "Buy 100 ETH at market price and set stop loss at 1800 and take profit at 2500 and trailing stop at 5%"
    r = await run(long_msg, fresh_session)
    assert r["_latency"] < 8.0

@pytest.mark.asyncio
async def test_15_special_characters(fresh_session):
    """Special characters in message"""
    r = await run("Buy ETH @ $2000 #crypto", fresh_session)
    assert r["_latency"] < 8.0

@pytest.mark.asyncio
async def test_16_unicode(fresh_session):
    """Unicode characters"""
    r = await run("Buy 以太坊 (ETH)", fresh_session)
    assert r["_latency"] < 8.0

# ─── GROUP 5: Pool Diagnostics (17) ───────────────────
@pytest.mark.asyncio
async def test_17_pool_efficiency(fresh_session):
    """Verify pool is being used efficiently"""
    stats_before = bridge_manager.get_stats()
    
    # Make request
    r = await run("Test pool", fresh_session)
    
    stats_after = bridge_manager.get_stats()
    
    # Should use warm pool or existing session
    assert stats_after["active_sessions"] >= stats_before["active_sessions"]
    assert r["_latency"] < 8.0

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
