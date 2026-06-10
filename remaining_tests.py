"""
Remaining Jarvix Tests - 75 commands
EMOTIONAL: 30 | UNKNOWN: 10 | MULTI-LANGUAGE: 24 | EDGE CASES: 11
"""

EMOTIONAL_COMMANDS = [
    "I'm so angry at this market crash!",
    "This is so frustrating, why didn't you sell?",
    "I'm really excited about BTC pumping!",
    "I'm scared of losing all my money",
    "This is amazing, we're going to the moon!",
    "I'm disappointed with my portfolio",
    "So happy I bought ETH early!",
    "I'm worried about the dip",
    "This makes me furious!",
    "I'm thrilled about the gains!",
    "So sad I missed the pump",
    "I'm anxious about this trade",
    "This is hilarious, crypto never sleeps",
    "I'm shocked by this volatility",
    "So confused, what should I do?",
    "I'm grateful for the profits",
    "This is depressing, everything is red",
    "I'm optimistic about the market",
    "So stressed about my investments",
    "I'm proud of my trading skills",
    "This is embarrassing, I bought the top",
    "I'm jealous of your gains",
    "So relieved I sold in time",
    "I'm nervous about this buy",
    "This is disgusting market manipulation",
    "I'm in love with this coin",
    "So bored of this sideways market",
    "I'm surprised by this pump",
    "This is devastating, I lost everything",
    "I'm hopeful for recovery",
]

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

MULTI_LANGUAGE_COMMANDS = [
    "BTC kharido",  # Hindi
    "ETH becho",  # Hindi
    "SOL lena hai",  # Hindi
    "Bitcoin comprar",  # Spanish
    "Ethereum vender",  # Spanish
    "Solana precio",  # Spanish
    "BTC kaufen",  # German
    "ETH verkaufen",  # German
    "ADA preis",  # German
    "比特币 买",  # Chinese
    "以太坊 卖",  # Chinese
    "BTC 買う",  # Japanese
    "ETH 売る",  # Japanese
    "Acheter BTC",  # French
    "Vendre ETH",  # French
    "Prix SOL",  # French
    "Comprare BTC",  # Italian
    "Vendere ETH",  # Italian
    "Kup BTC",  # Polish
    "Sprzedaj ETH",  # Polish
    "Купить BTC",  # Russian
    "Продать ETH",  # Russian
    "BTC satın al",  # Turkish
    "ETH sat",  # Turkish
]

EDGE_CASE_COMMANDS = [
    "",  # Empty
    "B",  # Single char
    "buy",  # No asset/amount
    "12345",  # Numbers only
    "!!!@@@###",  # Symbols only
    "   ",  # Spaces only
    "ETH ETH ETH ETH ETH",  # Repeated
    "Buy -100 BTC",  # Negative
    "Sell 0 ETH",  # Zero
    "Buy 999999999 BTC",  # Huge amount
    "@#$%^&*()",  # Special chars
]

ALL_COMMANDS = {
    "EMOTIONAL": EMOTIONAL_COMMANDS,
    "UNKNOWN": UNKNOWN_COMMANDS,
    "MULTI_LANGUAGE": MULTI_LANGUAGE_COMMANDS,
    "EDGE_CASES": EDGE_CASE_COMMANDS,
}

if __name__ == "__main__":
    total = 0
    for category, commands in ALL_COMMANDS.items():
        print(f"{category}: {len(commands)} commands")
        total += len(commands)
    print(f"\nTotal: {total} commands")
