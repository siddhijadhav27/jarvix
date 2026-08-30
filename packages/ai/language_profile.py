"""
Language Profile System for Jarvix
Tracks which languages each user is comfortable in, so ambiguous/short
messages ("namaste", "hi", emojis) can fall back to a language the user
actually knows instead of defaulting to English every time.

Core rule (backlog #1 follow-up): the language detected FROM the current
message always wins when it's a confident signal. This profile is only
consulted when the current message gives no such signal.
"""

import json
import os
import random
from typing import Dict, List, Optional
from datetime import datetime

LANGUAGE_DB_PATH = os.path.join(os.path.dirname(__file__), "../../data/language_profile_db.json")

DECAY_GRACE_DAYS = 30  # confidence only starts decaying after this many idle days
DECAY_PER_WEEK = 1

# Language-neutral tokens carry no real signal about which language someone
# speaks -- counting them would just add noise to the profile, so they're
# skipped entirely rather than nudging any language's confidence.
LANGUAGE_NEUTRAL_TOKENS = {
    "ok", "okay", "k", "kk", "hmm", "hm", "mm", "lol", "lmao", "haha", "hehe",
    "yes", "no", "yeah", "nah", "ya", "yep", "nope", "cool", "nice", "wow",
    "👍", "👌", "👎", "😂", "😊", "🙏", "❤️", "🔥", "✅",
}


def is_language_neutral_message(message: str) -> bool:
    """True if every word in the message is a language-neutral filler --
    e.g. 'ok', 'lol', a single emoji -- with nothing that hints at a language."""
    words = (message or "").strip().lower().split()
    if not words:
        return True
    return all(w.strip("!?.,") in LANGUAGE_NEUTRAL_TOKENS for w in words)


class LanguageProfileSystem:
    """Per-user known-language tracker with weighted, decaying confidence."""

    def __init__(self):
        self.profiles: Dict[str, Dict[str, dict]] = {}
        self.last_response_language: Dict[str, str] = {}
        self.load_database()

    def load_database(self):
        if os.path.exists(LANGUAGE_DB_PATH):
            try:
                with open(LANGUAGE_DB_PATH, 'r') as f:
                    data = json.load(f)
                    self.profiles = data.get('profiles', {})
                    self.last_response_language = data.get('last_response_language', {})
                print(f"[LANG_PROFILE] Loaded profiles for {len(self.profiles)} users")
            except Exception as e:
                print(f"[LANG_PROFILE] Error loading database: {e}")
                self._init_empty_db()
        else:
            self._init_empty_db()

    def _init_empty_db(self):
        os.makedirs(os.path.dirname(LANGUAGE_DB_PATH), exist_ok=True)
        self.save_database()

    def save_database(self):
        try:
            with open(LANGUAGE_DB_PATH, 'w') as f:
                json.dump({
                    'profiles': self.profiles,
                    'last_response_language': self.last_response_language,
                    'last_updated': datetime.now().isoformat()
                }, f, indent=2)
        except Exception as e:
            print(f"[LANG_PROFILE] Error saving database: {e}")

    def update_language(self, user_id: str, language_code: str, message_length: int = 1):
        """Record that user_id wrote a message in language_code, with a
        confidence bump weighted by message length (short messages are
        noisy, so they move the score less) and a boost if this looks like
        a correction (user switched away from the language we last replied in)."""
        user_profiles = self.profiles.setdefault(user_id, {})

        # Weight: short messages are noisy signal, don't let them swing confidence much
        if message_length <= 2:
            weight = 0.3
        elif message_length <= 5:
            weight = 0.7
        else:
            weight = 1.0

        # Correction signal: user just switched away from the language Jarvix last
        # replied in — that's a stronger-than-usual signal, weight it up a bit
        last_reply_lang = self.last_response_language.get(user_id)
        is_correction = last_reply_lang is not None and last_reply_lang != language_code
        correction_bonus = 1.3 if is_correction else 1.0

        entry = user_profiles.get(language_code)
        if entry:
            base_increase = 15 if message_length > 2 else 10
            entry['confidence_score'] = min(entry['confidence_score'] + base_increase * weight * correction_bonus, 100)
            entry['message_count'] = entry.get('message_count', 0) + 1
            entry['last_used'] = datetime.now().isoformat()
        else:
            user_profiles[language_code] = {
                'confidence_score': min(20 * weight * correction_bonus, 100),
                'message_count': 1,
                'last_used': datetime.now().isoformat(),
            }

        self.save_database()

    def record_response_language(self, user_id: str, language_code: str):
        """Track what language Jarvix just replied in, so the next message
        can be checked for a language correction."""
        self.last_response_language[user_id] = language_code
        self.save_database()

    def apply_decay(self, user_id: str):
        """Confidence only decays after DECAY_GRACE_DAYS of no use for that
        language — a language you used last month is still "known", it just
        fades slowly if truly abandoned."""
        user_profiles = self.profiles.get(user_id)
        if not user_profiles:
            return

        changed = False
        for lang_code, entry in user_profiles.items():
            last_used = entry.get('last_used')
            if not last_used:
                continue
            idle_days = (datetime.now() - datetime.fromisoformat(last_used)).days
            if idle_days > DECAY_GRACE_DAYS:
                weeks_beyond_grace = (idle_days - DECAY_GRACE_DAYS) // 7
                if weeks_beyond_grace > 0:
                    decayed = max(entry['confidence_score'] - weeks_beyond_grace * DECAY_PER_WEEK, 0)
                    if decayed != entry['confidence_score']:
                        entry['confidence_score'] = decayed
                        changed = True

        if changed:
            self.save_database()

    def get_known_languages(self, user_id: str, min_confidence: float = 30) -> List[str]:
        """Languages this user has shown enough confidence in, highest first."""
        user_profiles = self.profiles.get(user_id, {})
        known = [
            (lang, entry['confidence_score'])
            for lang, entry in user_profiles.items()
            if entry['confidence_score'] >= min_confidence
        ]
        known.sort(key=lambda pair: pair[1], reverse=True)
        return [lang for lang, _ in known]

    def get_primary_language(self, user_id: str) -> Optional[str]:
        """The single language this user is most comfortable in, if any."""
        known = self.get_known_languages(user_id, min_confidence=30)
        return known[0] if known else None

    def get_weighted_language_choice(self, user_id: str, min_confidence: float = 30) -> Optional[str]:
        """Pick a known language weighted by confidence, instead of always the
        single top one -- so a user with two strong known languages sees both
        in play over time rather than Jarvix locking onto whichever is #1."""
        user_profiles = self.profiles.get(user_id, {})
        known = self.get_known_languages(user_id, min_confidence)
        if not known:
            return None
        weights = [user_profiles[lang]['confidence_score'] for lang in known]
        return random.choices(known, weights=weights, k=1)[0]

    def get_total_messages(self, user_id: str) -> int:
        """Total messages we've seen from this user across all languages."""
        user_profiles = self.profiles.get(user_id, {})
        return sum(entry.get('message_count', 0) for entry in user_profiles.values())


_language_profile_system = None


def get_language_profile_system() -> LanguageProfileSystem:
    """Get or create global language profile system instance"""
    global _language_profile_system
    if _language_profile_system is None:
        _language_profile_system = LanguageProfileSystem()
    return _language_profile_system
