"""
Personalized greeting messages for Jarvix
"""
import random
from datetime import datetime

# Greeting messages by time of day
GREETINGS = {
    "morning": [
        "Good morning! Ready to conquer the markets today?",
        "Rise and shine! Your portfolio is looking great!",
        "Morning! Bitcoin never sleeps, and neither do we!",
        "Namaste! Aapka din shubh ho! Market ready hai!",
        "Top of the morning! Let's check those crypto gains!",
        "Hey early bird! Markets are already moving!",
        "Good morning, trader! Ready for today's action?",
        "Morning vibes! Your assets are waiting for you!",
        "Rise and grind! Crypto waits for no one!",
        "Namaste Sandy! Aapka portfolio ready hai!",
    ],
    "afternoon": [
        "Good afternoon! How's your portfolio looking?",
        "Afternoon check-in! Any trades today?",
        "Hey there! Mid-day market update ready!",
        "Good afternoon! Bitcoin is pumping!",
        "Afternoon! Your portfolio is trending up!",
        "Hey! Time for some crypto action?",
        "Good afternoon, trader! Markets are hot!",
        "Afternoon vibes! Check your gains!",
        "Mid-day hello! Portfolio looking strong!",
        "Namaste! Dupher ka market update!",
    ],
    "evening": [
        "Good evening! Winding down with some crypto stats?",
        "Evening! Let's review today's trades!",
        "Hey! Evening market check ready!",
        "Good evening! Your daily summary is here!",
        "Evening! Any final trades for today?",
        "Hey there! Crypto never sleeps!",
        "Good evening, trader! Day's recap ready!",
        "Evening vibes! Portfolio summary waiting!",
        "Night owl mode! Markets still active!",
        "Namaste! Sham ka market update!",
    ],
    "late_night": [
        "Late night! Crypto markets are 24/7!",
        "Night owl! Bitcoin is still pumping!",
        "Hey! Midnight trading session?",
        "Late night check! Portfolio never sleeps!",
        "Night trader! Markets are alive!",
        "Hey there! 3 AM crypto vibes!",
        "Late night! Your assets are working!",
        "Night mode! Crypto doesn't rest!",
        "Midnight hello! Portfolio still active!",
        "Namaste! Raat ka market update!",
    ]
}

def get_greeting_message():
    """Get personalized greeting based on time of day"""
    hour = datetime.now().hour
    
    if 5 <= hour < 12:
        time_slot = "morning"
    elif 12 <= hour < 17:
        time_slot = "afternoon"
    elif 17 <= hour < 21:
        time_slot = "evening"
    else:
        time_slot = "late_night"
    
    return random.choice(GREETINGS[time_slot])

def get_personalization_system():
    """Return personalization system prompt"""
    return "You are Jarvix, a personalized crypto trading assistant."
