"""
JARVIX Response Cleaner
Strips CLI artifacts from Hermes/Kimi responses
"""

import re

# UI artifacts to filter out
UI_ARTIFACTS = [
    '...', '>>>', '%|', 'it/s', 
    'Processing', 'Thinking', '━━━',
    'kimi-for-coding', 'msg=interrupt',
    '/queue', '/bg', '/steer', 'Ctrl+C',
    'analyzing...', '⚕', '⏱', '⏲',
    '─────────────────', 'Session:',
    'Duration:', 'Messages:', 'Resume this session',
    'hermes --resume'
]

def clean_response(raw_output: str) -> str:
    """
    Clean Hermes CLI artifacts from API responses
    
    Args:
        raw_output: Raw response from Hermes/Kimi
        
    Returns:
        Clean text suitable for frontend display
    """
    if not raw_output:
        return ""
    
    # Step 1: Remove ANSI escape codes (colors, cursor movement)
    ansi_escape = re.compile(r'\x1B(?:[@-Z\-_]|\[[0-?]*[ -/]*[@-~])')
    cleaned = ansi_escape.sub('', raw_output)
    
    # Step 2: Remove progress bar characters
    cleaned = re.sub(r'[⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏▓░█▌▐]', '', cleaned)
    
    # Step 3: Remove box-drawing characters
    cleaned = re.sub(r'[╭╮╯╰│─┤├┬┴┼]', '', cleaned)
    
    # Step 4: Split into lines and filter
    lines = cleaned.split('\n')
    clean_lines = []
    
    for line in lines:
        stripped = line.strip()
        
        # Skip empty lines
        if not stripped:
            continue
            
        # Skip UI artifact lines
        if any(artifact in stripped for artifact in UI_ARTIFACTS):
            continue
            
        # Skip lines that are just numbers or timestamps
        if re.match(r'^\d+$', stripped):
            continue
            
        # Skip lines with just progress indicators
        if re.match(r'^[\s░█▓▒\d.%]+$', stripped):
            continue
            
        clean_lines.append(stripped)
    
    # Step 5: Join and clean up extra whitespace
    result = '\n'.join(clean_lines)
    
    # Step 6: Remove multiple consecutive newlines
    result = re.sub(r'\n{3,}', '\n\n', result)
    
    return result.strip()


# Test function
def test_cleaner():
    """Test cleaner against various Hermes responses"""
    
    test_cases = [
        # Test 1: Simple response with session info
        {
            "input": "Query: What is Bitcoin?\nInitializing agent...\r\n────────────────────────────────────────\r\n\r\n╭─ ⚕ Hermes ───────────────────────────────────────────────────────────────────╮\r\n    Bitcoin is a decentralized digital currency.\r\n╰──────────────────────────────────────────────────────────────────────────────╯\r\n\nSession: 20260529_142015_a9d758\nDuration: 18s\nMessages: 2",
            "expected": "Query: What is Bitcoin?\nBitcoin is a decentralized digital currency."
        },
        
        # Test 2: Response with progress bars
        {
            "input": "⚕ kimi-for-coding │ 19.7K/262.1K │ [█░░░░░░░░░] 8% │ 2m │ ⏲ 4s\n───────────────────────────────────────────────────────────────────────────────\n─\n⚕ ❯ msg=interrupt · /queue · /bg · /steer · Ctrl+C cancel\n───────────────────────────────────────────────────────────────────────────────\n─\n\n٩(๑❛ᴗ❛๑)۶ analyzing...\n\n⚕ kimi-for-coding │ 19.7K/262.1K │ [█░░░░░░░░░] 8% │ 2m │ ⏱ 0s\n───────────────────────────────────────────────────────────────────────────────\n─\n\n╭─ ⚕ Hermes ───────────────────────────────────────────────────────────────────╮\n\n    Bitcoin is a decentralized digital currency.\n\n╰──────────────────────────────────────────────────────────────────────────────╯",
            "expected": "Bitcoin is a decentralized digital currency."
        },
        
        # Test 3: Response with ANSI colors
        {
            "input": "\x1b[32mQuery: What is Bitcoin?\x1b[0m\n\x1b[90mInitializing agent...\x1b[0m\n\nBitcoin is a decentralized digital currency.",
            "expected": "Query: What is Bitcoin?\nBitcoin is a decentralized digital currency."
        },
        
        # Test 4: Minimal response
        {
            "input": "pong",
            "expected": "pong"
        },
        
        # Test 5: Response with multiple paragraphs
        {
            "input": "Query: Explain Bitcoin\n\n⚕ kimi-for-coding │ analyzing...\n────────────────────────────────────────\n\n╭─ ⚕ Hermes ───────────────────────────────────────────────────────────────────╮\n\n    Bitcoin is a decentralized digital currency.\n    \n    It was created in 2009 by Satoshi Nakamoto.\n    \n    Key features:\n    - Limited supply: 21 million coins\n    - Decentralized: No central authority\n    - Transparent: All transactions public\n\n╰──────────────────────────────────────────────────────────────────────────────╯",
            "expected": "Query: Explain Bitcoin\nBitcoin is a decentralized digital currency.\nIt was created in 2009 by Satoshi Nakamoto.\nKey features:\n- Limited supply: 21 million coins\n- Decentralized: No central authority\n- Transparent: All transactions public"
        },
        
        # Test 6: Response with "Resume this session"
        {
            "input": "Bitcoin is a decentralized digital currency.\n\nResume this session with:\n  hermes --resume 20260529_142015_a9d758\n\nSession: 20260529_142015_a9d758",
            "expected": "Bitcoin is a decentralized digital currency."
        },
        
        # Test 7: Empty response
        {
            "input": "",
            "expected": ""
        },
        
        # Test 8: Only UI artifacts
        {
            "input": "⚕ kimi-for-coding │ analyzing...\n────────────────────────────────────────\n٩(๑❛ᴗ❛๑)۶ analyzing...",
            "expected": ""
        },
        
        # Test 9: Real-world complex response
        {
            "input": "Query: Should I buy ETH now?\nInitializing agent...\r\n────────────────────────────────────────\r\n\r\n╭─ ⚕ Hermes ───────────────────────────────────────────────────────────────────╮\r\n    Wait 2 hours. Whale selling detected. Price dropping 3%.\r\n    \r\n    Current ETH price: $2,241\r\n    Support level: $2,100\r\n    Whale movement: $50M moved to exchange\r\n╰──────────────────────────────────────────────────────────────────────────────╯\r\n\nSession: 20260529_142015_a9d758\nDuration: 12s",
            "expected": "Query: Should I buy ETH now?\nWait 2 hours. Whale selling detected. Price dropping 3%.\nCurrent ETH price: $2,241\nSupport level: $2,100\nWhale movement: $50M moved to exchange"
        },
        
        # Test 10: Response with emojis
        {
            "input": "Query: How are you?\n\n⚕ Hermes ───────────────────────────────────────────────────────────────────\n\n    I'm doing great! Ready to help with your crypto trades. 🚀\n    \n    What would you like to know?\n\n╰──────────────────────────────────────────────────────────────────────────────╯",
            "expected": "Query: How are you?\nI'm doing great! Ready to help with your crypto trades. 🚀\nWhat would you like to know?"
        }
    ]
    
    print("🧪 Testing Response Cleaner")
    print("=" * 50)
    
    passed = 0
    failed = 0
    
    for i, test in enumerate(test_cases, 1):
        result = clean_response(test["input"])
        
        if result == test["expected"]:
            print(f"✅ Test {i}: PASSED")
            passed += 1
        else:
            print(f"❌ Test {i}: FAILED")
            print(f"   Expected ({len(test['expected'])} chars): {test['expected'][:80]}...")
            print(f"   Got      ({len(result)} chars): {result[:80]}...")
            failed += 1
    
    print(f"\n📊 Results: {passed}/{passed+failed} passed")
    
    return failed == 0


if __name__ == "__main__":
    success = test_cleaner()
    exit(0 if success else 1)
