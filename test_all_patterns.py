"""
Comprehensive Test Suite for ALL Command Patterns
Tests emotions, anger, normal, slang, variations
"""

import asyncio
import sys
sys.path.insert(0, '/home/siddhi/jarvix-backend/packages')

from ai.intent import detect_intent_hybrid
from ai.personality import personality_engine
from ai.ghost_mode import get_ghost_mode
from ai.proactive_alerts import get_alert_manager

# ========== BUY PATTERNS (100+ variations) ==========
BUY_PATTERNS = [
    # Basic
    "Buy 100 ETH", "buy ETH", "BUY btc", "Purchase 50 SOL",
    # Slang
    "Grab me some BTC", "Get me 1000 ADA", "Acquire DOGE",
    "I want to buy ETH", "Add BTC to portfolio", "Pick up some SOL",
    # Questions
    "Should I buy BTC?", "Is it good to buy ETH now?",
    "Can I buy 100 SOL?", "Would you recommend buying ADA?",
    # Urgency/FOMO
    "Buy now before it moons!", "Don't miss this ETH opportunity!",
    "Hurry buy BTC!", "Quick get SOL before pump!",
    # Anger/Frustration
    "Just buy the damn BTC!", "I don't care, buy ETH now!",
    "Why didn't you buy SOL earlier?!", "Fine, buy whatever!",
    # Uncertainty
    "Maybe buy some BTC?", "Thinking about buying ETH",
    "Possibly get SOL", "Considering ADA purchase",
    # Vague
    "Buy something", "I want to buy", "Let's buy",
    "Buying time", "Time to buy", "Buy buy buy!",
    # With reasoning
    "Buy BTC because it's dipping", "Get ETH before merge",
    "Purchase SOL for long term", "Buy ADA for staking",
    # Different amounts
    "Buy 0.5 BTC", "Buy 100.5 ETH", "Buy 1 SOL",
    "Buy 1000000 DOGE", "Buy 0.001 BTC",
    # No amount
    "Buy BTC", "Get ETH", "Purchase SOL", "Acquire ADA",
    # All caps
    "BUY 100 ETH", "BUY BTC NOW", "GET SOL",
    # Mixed case
    "BuY 100 EtH", "bUy BtC", "PURCHASE sol",
    # With symbols
    "Buy $100 of BTC", "Buy 100$ ETH", "Get 1000₹ SOL",
    # With spaces
    "Buy   100   ETH", "  Buy BTC  ", "  Get  SOL  ",
    # Misspellings
    "Bye 100 ETH", "Biy BTC", "Purcase SOL",
    "Bai ADA", "Grt DOGE", "Aquire XRP",
    # With punctuation
    "Buy 100 ETH!", "Buy BTC?", "Get SOL!!!",
    "Purchase ADA...", "Buy, buy, buy!",
    # Multiple assets
    "Buy BTC and ETH", "Get SOL and ADA",
    "Purchase BTC, ETH, SOL", "Buy all three",
    # Negative phrasing
    "Not selling, buying!", "Instead of selling, buy",
    "Don't sell, buy!", "Buy don't sell",
    # Conditional
    "If BTC dips, buy", "Buy ETH if it drops",
    "When SOL pumps, buy more", "Buy the dip",
    # Sarcastic
    "Oh great, let me buy more BTC", "Sure, I'll buy the top",
    "Yeah, buying ETH is such a good idea *sarcasm*",
    # Emoji
    "Buy BTC 🚀", "Get ETH 💎", "Purchase SOL 🌙",
    "Buy ADA ✅", "Get DOGE 🐕",
    # Foreign language mix
    "Buy 100 ETH bhai", "BTC kharido", "ETH lena hai",
    "SOL comprar", "ADA kaufen", "BTC 買う",
    # Very long
    "I want to buy 100 ETH because I think it's going to the moon and my friend said it's a good investment and I have some extra money",
    # Very short
    "B", "buy", "get", "add",
    # Numbers only
    "100 ETH", "0.5 BTC", "1000",
    # Asset only
    "ETH", "BTC", "SOL", "DOGE",
]

# ========== SELL PATTERNS (100+ variations) ==========
SELL_PATTERNS = [
    # Basic
    "Sell 100 ETH", "sell BTC", "SELL sol", "Dump 50 ADA",
    # Slang
    "Get rid of DOGE", "Cash out BTC", "Liquidate ETH",
    "Unload SOL", "Offload ADA", "Exit DOGE position",
    # Questions
    "Should I sell BTC?", "Is it time to sell ETH?",
    "Can I sell 100 SOL?", "Would you recommend selling?",
    # Urgency/Panic
    "Sell everything now!", "Dump it all!",
    "Get out of BTC!", "Emergency sell ETH!",
    # Anger/Frustration
    "Just sell the damn BTC!", "I hate ETH, sell it!",
    "Why didn't you sell earlier?!", "Sell everything, I'm done!",
    # Fear
    "Sell before it crashes!", "Get out before dump!",
    "Sell now, market is crashing!", "Emergency exit!",
    # Vague
    "Sell something", "I want to sell", "Let's sell",
    "Selling time", "Time to sell", "Sell sell sell!",
    # With reasoning
    "Sell BTC to take profits", "Dump ETH before crash",
    "Cash out SOL at peak", "Liquidate ADA for cash",
    # Different amounts
    "Sell 0.5 BTC", "Sell 100.5 ETH", "Sell 1 SOL",
    "Sell half my BTC", "Sell 25% of ETH",
    # All
    "Sell everything", "Sell all", "Sell 100%",
    "Liquidate all holdings", "Cash out everything",
    # All caps
    "SELL 100 ETH", "SELL BTC NOW", "DUMP SOL",
    # Mixed case
    "SeLl 100 EtH", "sElL BtC", "DUMP sol",
    # With punctuation
    "Sell 100 ETH!", "Sell BTC?", "Dump SOL!!!",
    "Cash out ADA...", "Sell, sell, sell!",
    # Multiple assets
    "Sell BTC and ETH", "Dump SOL and ADA",
    "Sell everything except BTC", "Sell all altcoins",
    # Stop loss
    "Sell if BTC drops below 50k", "Stop loss at 40k",
    "Sell ETH at 1500", "Exit if SOL hits 100",
    # Sarcastic
    "Oh sure, sell at the bottom", "Great time to sell *sarcasm*",
    "Yeah, let's sell the winners",
    # Emoji
    "Sell BTC 📉", "Dump ETH 😰", "Cash out SOL 😱",
    "Sell ADA 💔", "Liquidate DOGE 🚨",
    # Foreign
    "Sell 100 ETH bhai", "BTC becho", "ETH dena hai",
    "SOL vender", "ADA verkaufen", "BTC 売る",
]

# ========== PRICE PATTERNS (50+ variations) ==========
PRICE_PATTERNS = [
    "Price of BTC", "BTC price", "How much is ETH?",
    "What is SOL worth?", "Current ADA price",
    "Show me BTC price", "Tell me ETH value",
    "BTC rate", "ETH cost", "SOL value",
    "How much does BTC cost?", "What's the price of ETH?",
    "BTC to USD", "ETH price in dollars",
    "Is BTC up or down?", "ETH performance today",
    "BTC chart", "ETH graph", "SOL trend",
    "📈 BTC", "📉 ETH", "💰 SOL price",
    "BTC kitna hai", "ETH ka rate", "SOL price kya hai",
]

# ========== PORTFOLIO PATTERNS (30+ variations) ==========
PORTFOLIO_PATTERNS = [
    "Show portfolio", "My holdings", "What do I own?",
    "Portfolio value", "Net worth", "Balance",
    "How much do I have?", "My assets", "Holdings",
    "Show me my portfolio", "Portfolio summary",
    "What am I holding?", "Current positions",
    "Portfolio performance", "P&L", "Profit and loss",
    "💼 portfolio", "📊 holdings", "💰 balance",
    "Mera portfolio", "Kitna paisa hai", "Holdings dikhao",
]

# ========== GREETING PATTERNS (30+ variations) ==========
GREETING_PATTERNS = [
    "Hello", "Hi", "Hey", "Good morning",
    "Good afternoon", "Good evening", "What's up",
    "How are you", "How's it going", "Yo",
    "Hii", "Hiii", "Heyy", "Hellooo",
    "👋", "🙋", "🖐️", "✋",
    "Namaste", "Hola", "Bonjour", "Ciao",
    "Jarvix", "You there?", "Wake up",
]

# ========== ADVICE PATTERNS (30+ variations) ==========
ADVICE_PATTERNS = [
    "Should I buy BTC?", "Is ETH a good investment?",
    "What do you think about SOL?", "Analyze ADA",
    "Give me advice", "What should I do?",
    "Recommend something", "What's your opinion?",
    "BTC analysis", "ETH forecast", "SOL prediction",
    "Market analysis", "Technical analysis",
    "Fundamental analysis", "Price prediction",
    "🤔 BTC", "🧐 ETH", "📊 analysis",
    "Kya karu?", "Kya lena chahiye?", "Kaise invest karu?",
]

# ========== ALERT PATTERNS (20+ variations) ==========
ALERT_PATTERNS = [
    "Alert me when BTC hits 100k", "Notify when ETH drops",
    "Set alert for SOL", "Tell me when ADA pumps",
    "Price alert", "Notification", "Watch BTC",
    "Monitor ETH", "Track SOL price", "Alert setup",
    "🚨 alert", "🔔 notify", "⏰ reminder",
    "BTC alert lagao", "ETH ka notification", "Price track karo",
]

# ========== EMOTIONAL/ANGRY PATTERNS ==========
EMOTIONAL_PATTERNS = [
    "I hate this market!", "This is ridiculous!",
    "Why is BTC crashing?!", "I'm so angry right now!",
    "Stupid crypto!", "I lost everything!",
    "This is a scam!", "I want my money back!",
    "F*** this!", "Damn it!", "WTF!",
    "I'm crying right now", "So depressed",
    "Anxious about my holdings", "Stressed about ETH",
    "Scared to check portfolio", "Worried about crash",
    "Excited for pump!", "Happy with gains!",
    "To the moon! 🚀", "Lambo soon!",
    "HODL! 💎🙌", "Diamond hands!",
    "Paper hands", "Weak hands", "Shakeout",
    "FUD", "FOMO", "APE IN", "YOLO",
    "Buy the dip!", "Sell the rip!",
    "WAGMI", "NGMI", "Have fun staying poor",
    "This is fine 🔥", "Panic sell",
    "Revenge trading", "I'll show them",
    "Double down", "All in", "Mortgage the house",
    "Sell everything!", "Never selling!",
    "Trust me bro", "Source: trust me bro",
    "It's different this time", "New paradigm",
    "Institutional money coming", "Adoption is here",
    "Mainstream soon", "Early adoption",
]

# ========== TEST FUNCTION ==========
async def test_all_patterns():
    """Test all command patterns"""
    results = {
        "buy": {"total": 0, "correct": 0, "patterns": []},
        "sell": {"total": 0, "correct": 0, "patterns": []},
        "price": {"total": 0, "correct": 0, "patterns": []},
        "portfolio": {"total": 0, "correct": 0, "patterns": []},
        "greeting": {"total": 0, "correct": 0, "patterns": []},
        "advice": {"total": 0, "correct": 0, "patterns": []},
        "alert": {"total": 0, "correct": 0, "patterns": []},
        "unknown": {"total": 0, "correct": 0, "patterns": []},
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
    
    print("=" * 80)
    print("TESTING ALL COMMAND PATTERNS")
    print("=" * 80)
    
    for patterns, expected_intent in all_patterns:
        print(f"\n--- Testing {expected_intent.upper()} ({len(patterns)} patterns) ---")
        
        for pattern in patterns:
            result = await detect_intent_hybrid(pattern)
            detected = result["intent"]
            
            results[expected_intent]["total"] += 1
            
            if detected == expected_intent:
                results[expected_intent]["correct"] += 1
                status = "✅"
            else:
                status = "❌"
                results[expected_intent]["patterns"].append({
                    "pattern": pattern,
                    "expected": expected_intent,
                    "detected": detected
                })
            
            print(f"{status} '{pattern}' -> {detected}")
    
    # Test emotional patterns
    print(f"\n--- Testing EMOTIONAL/ANGRY ({len(EMOTIONAL_PATTERNS)} patterns) ---")
    for pattern in EMOTIONAL_PATTERNS:
        result = await detect_intent_hybrid(pattern)
        detected = result["intent"]
        emotion = personality_engine.detect_emotion(pattern)
        
        results["unknown"]["total"] += 1
        
        # Emotional patterns should either be detected or marked with emotion
        if detected != "unknown" or emotion != "neutral":
            results["unknown"]["correct"] += 1
            status = "✅"
        else:
            status = "❌"
            results["unknown"]["patterns"].append({
                "pattern": pattern,
                "detected": detected,
                "emotion": emotion
            })
        
        print(f"{status} '{pattern}' -> intent:{detected}, emotion:{emotion}")
    
    # Print summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    total_tests = 0
    total_correct = 0
    
    for intent, data in results.items():
        if data["total"] > 0:
            accuracy = (data["correct"] / data["total"]) * 100
            total_tests += data["total"]
            total_correct += data["correct"]
            
            print(f"\n{intent.upper()}:")
            print(f"  Correct: {data['correct']}/{data['total']} ({accuracy:.1f}%)")
            
            if data["patterns"]:
                print(f"  Failed patterns:")
                for fail in data["patterns"][:5]:  # Show first 5 failures
                    print(f"    - '{fail['pattern']}' -> {fail['detected']} (expected: {fail.get('expected', 'any')})")
    
    overall_accuracy = (total_correct / total_tests) * 100 if total_tests > 0 else 0
    print(f"\n{'=' * 80}")
    print(f"OVERALL: {total_correct}/{total_tests} ({overall_accuracy:.1f}%)")
    print(f"{'=' * 80}")
    
    return results

if __name__ == "__main__":
    asyncio.run(test_all_patterns())
