import asyncio
import sys
sys.path.insert(0, '/home/siddhi/jarvix-backend/packages')

from ai.intent import detect_intent_hybrid

UNKNOWN_COMMANDS = [
    "What's the weather today?",
    "Tell me a joke",
    "Order pizza for me",
    "Who won the cricket match?",
    "Set an alarm for 6 AM",
    "What's the capital of France?",
    "Play some music",
    "What's your favorite color?",
    "How tall is Mount Everest?",
    "What time is it in Tokyo?",
]

async def test():
    print("=" * 60)
    print("UNKNOWN COMMANDS TESTING")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for i, cmd in enumerate(UNKNOWN_COMMANDS, 1):
        result = await detect_intent_hybrid(cmd)
        intent = result.get("intent", "ERROR")
        confidence = result.get("confidence", 0)
        
        status = "✅ PASS" if intent == "unknown" else "❌ FAIL"
        if intent == "unknown":
            passed += 1
        else:
            failed += 1
        
        print(f"{i:2d}. {status} | '{cmd}'")
        print(f"     Intent: {intent} (confidence: {confidence:.2f})")
        print()
    
    print("=" * 60)
    print(f"RESULT: {passed}/10 PASS | {failed}/10 FAIL")
    print(f"Accuracy: {passed*10}%")
    print("=" * 60)

asyncio.run(test())
