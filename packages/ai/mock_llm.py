"""
Mock LLM for Jarvix - Returns JARVIS-style responses
Use when real LLM is unavailable
"""

import random
from typing import Dict, Any

# JARVIS-style responses by intent
JARVIS_RESPONSES = {
    "buy": [
        "Sir, {amount} {asset} queued up — that would bring your stack to {new_total}. Shall I execute?",
        "Sir, {asset} at the ready. {amount} coins, worth roughly ${value}. Confirm?",
        "Sir, adding {amount} {asset} to your position. Your {asset} stack will be {new_total}. Execute?",
    ],
    "sell": [
        "Sir, selling {amount} {asset} would liquidate {percent}% of your position. Shall I execute?",
        "Sir, {amount} {asset} ready to offload. Worth roughly ${value}. Confirm?",
        "Sir, cashing out {amount} {asset}. Your portfolio will drop to ${new_portfolio}. Execute?",
    ],
    "price": [
        "Sir, {asset} is currently trading at ${price}. Your {holdings} {asset} is worth ${value} — not bad for a Tuesday.",
        "Sir, {asset} sits at ${price}. That's a {change}% move from your entry. Want me to set an alert?",
    ],
    "portfolio": [
        "Sir, your portfolio sits at ${total} — up {change}% today. You're holding {holdings}. Not a bad day's work.",
        "Sir, net worth check: ${total}. {holdings}. Steady as she goes.",
    ],
    "greeting": [
        "Good morning, sir. Portfolio's up {change}% — markets are kind today. What's the play?",
        "Sir, Jarvix online. Markets are {status}. Ready when you are.",
    ],
    "advice": [
        "Sir, {asset} analysis: {sentiment}. Your position is {position}. Want me to pull up the charts?",
        "Sir, my models suggest {asset} is {trend}. But you know what they say — past performance, future results.",
    ],
    "stop_loss": [
        "Sir, stop-loss set for {asset} at ${price}. Your position will be protected at {percent}% below current.",
        "Sir, safety net deployed: {asset} stop at ${price}. Smart move.",
    ],
    "alert": [
        "Sir, alert set for {asset} at ${price}. I'll ping you when it hits.",
        "Sir, watching {asset} like a hawk. Alert at ${price}.",
    ],
    "unknown": [
        "Sir, I didn't quite catch that. Could you rephrase? I'm best with buy, sell, price, or portfolio commands.",
        "Sir, my circuits are humming but I'm not sure what you're after. Try 'buy 100 ETH' or 'BTC price'?",
    ],
}

# Emotional responses
EMOTIONAL_RESPONSES = {
    "anger": [
        "Sir, I hear the frustration — but your portfolio is up {change}% today at ${total}. Markets are cyclical; the green days always return.",
        "Sir, take a breath. Your portfolio is at ${total}. Panic is the enemy of profit.",
    ],
    "panic": [
        "Sir, I feel the panic — but your portfolio is up {change}% at ${total} today. Selling everything on a green day? Take a breath and let's look at the charts first.",
        "Sir, deep breath. Markets recover 68% of the time. Your portfolio: ${total}. Hold steady.",
    ],
    "fomo": [
        "Sir, FOMO is real — but you already hold {holdings} {asset}. Patience, young padawan.",
        "Sir, the moon can wait. Your {asset} position is solid at {amount}. Don't chase.",
    ],
    "sadness": [
        "Sir, I see the red — but your portfolio is at ${total}. Dips are just discounts for the patient.",
        "Sir, every trader has rough days. Your portfolio: ${total}. Tomorrow's another session.",
    ],
    "overconfidence": [
        "Sir, diamond hands are admirable — but even Tony Stark checks his suit before flying. Want me to run a risk check?",
        "Sir, confidence is good, caution is better. Your portfolio: ${total}. Shall I review your exposure?",
    ],
    "excitement": [
        "Sir, I feel the energy! Your portfolio is up {change}% at ${total}. But remember — don't get high on your own supply.",
        "Sir, the market's moving! Your {asset} is performing. Want to take some profits?",
    ],
}

# Demo portfolio
DEMO_PORTFOLIO = {
    "BTC": {"amount": 0.5, "price": 73084},
    "ETH": {"amount": 100, "price": 1998},
    "SOL": {"amount": 500, "price": 150},
    "total": 100000,
    "change_24h": 2.4,
}


def generate_mock_response(intent_data: Dict[str, Any], emotion: str = "neutral", context: Dict[str, Any] = None) -> str:
    """Generate JARVIS-style mock response"""
    
    intent = intent_data.get("intent", "unknown")
    asset = intent_data.get("asset")
    amount = intent_data.get("amount")
    
    # Get portfolio data
    portfolio = context or DEMO_PORTFOLIO
    total = portfolio.get("total", 311342)
    change = portfolio.get("change_24h", 2.4)
    
    # Format holdings string
    holdings = []
    for a, data in portfolio.items():
        if a not in ["total", "change_24h"]:
            holdings.append(f"{data['amount']} {a}")
    holdings_str = ", ".join(holdings)
    
    # Select response template
    if emotion != "neutral" and emotion in EMOTIONAL_RESPONSES:
        templates = EMOTIONAL_RESPONSES[emotion]
    elif intent in JARVIS_RESPONSES:
        templates = JARVIS_RESPONSES[intent]
    else:
        templates = JARVIS_RESPONSES["unknown"]
    
    template = random.choice(templates)
    
    # Calculate values
    asset_price = portfolio.get(asset, {}).get("price", 0) if asset else 0
    asset_amount = portfolio.get(asset, {}).get("amount", 0) if asset else 0
    
    if amount and asset:
        new_total = asset_amount + amount
        value = amount * asset_price
        percent = round((amount / (asset_amount + amount)) * 100, 1) if asset_amount + amount > 0 else 0
    else:
        new_total = asset_amount
        value = asset_amount * asset_price
        percent = 0
    
    # Format response
    try:
        response = template.format(
            asset=asset or "crypto",
            amount=amount or "some",
            price=asset_price,
            total=total,
            change=change,
            holdings=holdings_str,
            new_total=new_total,
            value=value,
            percent=percent,
            new_portfolio=total - value if intent == "sell" else total,
            sentiment="bullish" if change > 0 else "bearish",
            trend="up" if change > 0 else "down",
            position=f"{asset_amount} coins" if asset else "diversified",
            status="green" if change > 0 else "red",
        )
    except KeyError:
        # Fallback if template formatting fails
        response = f"Sir, I understand. Your portfolio is at ${total}. How can I help?"
    
    return response


# Test
if __name__ == "__main__":
    # Test buy
    print("BUY:")
    print(generate_mock_response({"intent": "buy", "asset": "ETH", "amount": 100}))
    
    print("\nANGER:")
    print(generate_mock_response({"intent": "unknown"}, emotion="anger"))
    
    print("\nPANIC:")
    print(generate_mock_response({"intent": "sell"}, emotion="panic"))
