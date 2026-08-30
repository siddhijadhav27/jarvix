"""
JARVIX Intent Classifier
Uses LLM for natural language understanding with regex as fast pre-filter
"""

import json
import re
import random
import time
import unicodedata
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict, Any, Optional
from .language_profile import get_language_profile_system, is_language_neutral_message
from enum import Enum

class Intent(Enum):
    BUY = "buy"
    SELL = "sell"
    PORTFOLIO = "portfolio"
    PRICE = "price"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    ADVICE = "advice"
    GREETING = "greeting"
    UNKNOWN = "unknown"

# Fast regex pre-filter for obvious cases
FAST_PATTERNS = {
    Intent.GREETING: (
        r"^(hi|hello|hey|hii|namaste|namaskar|नमस्ते|नमस्कार|सुप्रभात|शुभ संध्या|शुभ रात्रि|"
        r"good morning|good afternoon|good evening|good night|"
        r"hola|buenos días|buenos dias|buenas tardes|buenas noches|"
        r"bonjour|bonsoir|bonne nuit|salut|"
        r"hallo|guten morgen|guten tag|guten nachmittag|guten abend|gute nacht|"
        r"おはよう|こんにちは|こんばんは|おやすみ)\b"
    ),
}

IST = ZoneInfo("Asia/Kolkata")

# Explicit greeting phrases that ALWAYS override the clock (backlog #1 decision:
# Jarvix never assumes "good night" from time alone — only when the user says it,
# since a user could genuinely be on a night shift at 2 AM saying "good morning").
# Checked in order per language, most specific phrase first.
EXPLICIT_GREETING_PHRASES = {
    "en": [
        ("night", r"(good\s*)?night"),
        ("morning", r"(good\s*)?morning"),
        ("afternoon", r"(good\s*)?afternoon"),
        ("evening", r"(good\s*)?evening"),
    ],
    "hi": [
        ("night", r"शुभ\s*रात्रि"),
        ("morning", r"सुप्रभात"),
        ("evening", r"शुभ\s*संध्या"),
    ],
    "hi-en": [
        ("night", r"(good\s*)?night|shubh\s*raatri"),
        ("morning", r"(good\s*)?morning|subah"),
        ("afternoon", r"(good\s*)?afternoon|dopahar"),
        ("evening", r"(good\s*)?evening|shaam"),
    ],
    "es": [
        ("night", r"buenas\s*noches"),
        ("morning", r"buenos\s*d[ií]as"),
        ("afternoon", r"buenas\s*tardes"),
    ],
    "fr": [
        ("night", r"bonne\s*nuit"),
        ("evening", r"bonsoir"),
        ("morning", r"bonjour"),
    ],
    "de": [
        ("night", r"gute\s*nacht"),
        ("morning", r"guten\s*morgen"),
        ("evening", r"guten\s*abend"),
        ("afternoon", r"guten\s*(tag|nachmittag)"),
    ],
    "ja": [
        ("night", r"おやすみ"),
        ("morning", r"おはよう"),
        ("evening", r"こんばんは"),
    ],
}

def _detect_explicit_greeting_category(message: str, language: str) -> Optional[str]:
    """Return 'morning'/'afternoon'/'evening'/'night' if the user's own words said so, else None."""
    msg = (message or "").strip().lower()
    for lang_key in (language, "en"):
        for category, pattern in EXPLICIT_GREETING_PHRASES.get(lang_key, []):
            if re.search(pattern, msg, re.IGNORECASE):
                return category
    return None

def _get_ist_time_bucket() -> str:
    """Clock-based fallback bucket, used only when the user's greeting is generic
    (hi/hello/hey/namaste with no explicit time-word). Never returns 'night' —
    that only ever comes from an explicit user phrase, per backlog #1 design."""
    hour = datetime.now(IST).hour
    if 5 <= hour < 12:
        return "morning"
    elif 12 <= hour < 17:
        return "afternoon"
    elif 17 <= hour < 24:
        return "evening"
    else:  # 12:00 AM - 4:59 AM — could be a night-shift user, default to morning
        return "morning"

def _get_real_time_period_and_display() -> tuple:
    """The ACTUAL current period, for catching a mismatch between what the
    user claimed ('good morning') and the real clock. Deliberately never
    returns 'night' on its own -- same rule as backlog #1's original design:
    Jarvix doesn't autonomously decide it's night, only the user's own
    explicit "night"/"good night" claim can introduce that category (handled
    as an unconditional pass in _check_greeting_mismatch). So "evening" here
    just runs all the way through to sunrise."""
    now = datetime.now(IST)
    hour = now.hour
    if 5 <= hour < 12:
        period = "morning"
    elif 12 <= hour < 17:
        period = "afternoon"
    else:  # 17:00 through 4:59 -- "evening" the whole way, never autonomous "night"
        period = "evening"
    time_str = now.strftime("%I:%M %p").lstrip("0")
    return period, time_str

PERIOD_LABELS = {
    "en": {"morning": "morning", "afternoon": "afternoon", "evening": "evening", "night": "night"},
    "hi": {"morning": "सुबह", "afternoon": "दोपहर", "evening": "शाम", "night": "रात"},
    "hi-en": {"morning": "subah", "afternoon": "dopahar", "evening": "shaam", "night": "raat"},
    "es": {"morning": "mañana", "afternoon": "tarde", "evening": "tarde", "night": "noche"},
    "fr": {"morning": "matin", "afternoon": "après-midi", "evening": "soir", "night": "nuit"},
    "de": {"morning": "Morgen", "afternoon": "Nachmittag", "evening": "Abend", "night": "Nacht"},
    "ja": {"morning": "朝", "afternoon": "昼", "evening": "夕方", "night": "夜"},
}

def _period_label(period: str, language: str) -> str:
    return PERIOD_LABELS.get(language, PERIOD_LABELS["en"]).get(period, period)

# Per-user tracking of how many times in a row they've insisted on a greeting
# category that doesn't match the real clock -- see _check_greeting_mismatch.
_greeting_mismatch_state: Dict[str, dict] = {}

# {real_period}/{stated_period} get the localized period word, {time} the clock string.
GREETING_MISMATCH_CORRECTION = {
    "en": {
        "stage1": [
            "Sir, small correction — it's actually {real_period} right now ({time}), not {stated_period}.",
            "Hold on, sir — my clock says {real_period} ({time}), not {stated_period}. Everything alright?",
            "Sir, I hate to be that assistant, but it's {real_period} ({time}), not {stated_period}.",
            "A gentle nudge, sir: it's {time}, which makes it {real_period}, not {stated_period}.",
        ],
        "stage2": [
            "Sir, we've been over this — it's still {real_period} ({time}). Are you testing me?",
            "I'll say it again, sir: {real_period}, not {stated_period}. The clock hasn't changed its mind.",
            "Sir, {stated_period} again? It's {time} — that's very much {real_period}.",
            "Persistent, aren't we, sir? Still {real_period} at {time}.",
        ],
        "stage3": [
            "Alright, sir, you win — {stated_period} it is, if you insist. Though it's {time}, which I'd call {real_period}, just for the record.",
            "Fine, sir, {stated_period} it shall be. Noting for posterity that the actual time is {time} ({real_period}).",
            "Very well, sir — {stated_period}, as you say. Purely coincidentally, it's {time} right now.",
            "Sir, I'll play along — {stated_period} confirmed. Though {time} does suggest {real_period}, in case that was a slip.",
        ],
    },
    "hi": {
        "stage1": [
            "सर, छोटी सी गलती — अभी असल में {real_period} है ({time}), {stated_period} नहीं।",
            "रुकिए सर — मेरी घड़ी {real_period} बता रही है ({time}), {stated_period} नहीं। सब ठीक है ना?",
            "सर, बताना पड़ रहा है — अभी {real_period} है ({time}), {stated_period} नहीं।",
            "सर, {time} हो रहे हैं, यानी अभी {real_period} है, {stated_period} नहीं।",
        ],
        "stage2": [
            "सर, ये तो हम पहले भी बात कर चुके हैं — अभी भी {real_period} ही है ({time})।",
            "फिर से बता देता हूं सर — {real_period}, {stated_period} नहीं। घड़ी नहीं बदली।",
            "सर, फिर से {stated_period}? अभी {time} है — यानी {real_period}।",
            "जिद्दी हैं आप सर — {time} पे अभी भी {real_period} ही है।",
        ],
        "stage3": [
            "ठीक है सर, आपकी जीत — {stated_period} ही मान लेते हैं। बस रिकॉर्ड के लिए, अभी {time} हैं, यानी {real_period}।",
            "चलिए सर, {stated_period} ही सही। बस इतना बता दूं, अभी असल समय {time} है ({real_period})।",
            "जैसा आप कहें सर — {stated_period}। बस संयोग से अभी {time} हो रहे हैं।",
            "सर, मान लेता हूं — {stated_period} confirm। बस {time} dekh ke lagta hai {real_period} hai, shayad galti se bola ho।",
        ],
    },
    "hi-en": {
        "stage1": [
            "Sir, chhoti si correction — abhi actually {real_period} hai ({time}), {stated_period} nahi.",
            "Ruko sir — mera clock {real_period} bata raha hai ({time}), {stated_period} nahi. Sab theek hai na?",
            "Sir, batana pad raha hai — abhi {real_period} hai ({time}), {stated_period} nahi.",
            "Sir, {time} ho rahe hain, matlab abhi {real_period} hai, {stated_period} nahi.",
        ],
        "stage2": [
            "Sir, ye baat pehle bhi ho chuki hai — abhi bhi {real_period} hi hai ({time}).",
            "Phir se bata deta hoon sir — {real_period}, {stated_period} nahi. Clock nahi badla.",
            "Sir, phir se {stated_period}? Abhi {time} hai — matlab {real_period}.",
            "Zidd kar rahe ho sir — {time} pe abhi bhi {real_period} hi hai.",
        ],
        "stage3": [
            "Theek hai sir, aapki jeet — {stated_period} hi maan lete hain. Bas record ke liye, abhi {time} hain, matlab {real_period}.",
            "Chaliye sir, {stated_period} hi sahi. Bas itna bata doon, abhi asal time {time} hai ({real_period}).",
            "Jaisa aap kahein sir — {stated_period}. Bas coincidentally abhi {time} ho rahe hain.",
            "Sir, maan leta hoon — {stated_period} confirm. Bas {time} dekh ke lagta hai {real_period} hai, shayad galti se bola ho.",
        ],
    },
    "es": {
        "stage1": [
            "Señor, pequeña corrección — en realidad es {real_period} ahora mismo ({time}), no {stated_period}.",
            "Un momento, señor — mi reloj dice {real_period} ({time}), no {stated_period}. ¿Todo bien?",
            "Señor, no quiero ser pesado, pero es {real_period} ({time}), no {stated_period}.",
            "Un pequeño aviso, señor: son las {time}, o sea que es {real_period}, no {stated_period}.",
        ],
        "stage2": [
            "Señor, ya hablamos de esto — sigue siendo {real_period} ({time}). ¿Me está probando?",
            "Lo repito, señor: {real_period}, no {stated_period}. El reloj no ha cambiado de opinión.",
            "Señor, ¿{stated_period} otra vez? Son las {time} — eso es {real_period}.",
            "Qué insistente, señor — sigue siendo {real_period} a las {time}.",
        ],
        "stage3": [
            "Está bien, señor, usted gana — {stated_period}, si insiste. Aunque son las {time}, que yo llamaría {real_period}, para que conste.",
            "De acuerdo, señor, {stated_period} será. Anotando para la posteridad que la hora real es {time} ({real_period}).",
            "Muy bien, señor — {stated_period}, como usted diga. Casualmente, son las {time} en este momento.",
            "Señor, le sigo la corriente — {stated_period} confirmado. Aunque las {time} sugieren {real_period}, por si fue un desliz.",
        ],
    },
    "fr": {
        "stage1": [
            "Monsieur, petite correction — il est en fait {real_period} en ce moment ({time}), pas {stated_period}.",
            "Attendez, monsieur — mon horloge indique {real_period} ({time}), pas {stated_period}. Tout va bien ?",
            "Monsieur, je n'aime pas être cet assistant, mais il est {real_period} ({time}), pas {stated_period}.",
            "Un petit rappel, monsieur : il est {time}, ce qui fait {real_period}, pas {stated_period}.",
        ],
        "stage2": [
            "Monsieur, on en a déjà parlé — il est toujours {real_period} ({time}). Vous me testez ?",
            "Je le répète, monsieur : {real_period}, pas {stated_period}. L'horloge n'a pas changé d'avis.",
            "Monsieur, {stated_period} encore ? Il est {time} — c'est bien {real_period}.",
            "Persévérant, monsieur — toujours {real_period} à {time}.",
        ],
        "stage3": [
            "Très bien, monsieur, vous gagnez — {stated_period}, si vous insistez. Bien qu'il soit {time}, ce que j'appellerais {real_period}, pour mémoire.",
            "D'accord, monsieur, ce sera {stated_period}. Je note pour la postérité que l'heure réelle est {time} ({real_period}).",
            "Très bien, monsieur — {stated_period}, comme vous voulez. Par pure coïncidence, il est {time} en ce moment.",
            "Monsieur, je joue le jeu — {stated_period} confirmé. Bien que {time} suggère {real_period}, au cas où ce serait un lapsus.",
        ],
    },
    "de": {
        "stage1": [
            "Mein Herr, kleine Korrektur — es ist gerade tatsächlich {real_period} ({time}), nicht {stated_period}.",
            "Moment, mein Herr — meine Uhr sagt {real_period} ({time}), nicht {stated_period}. Alles in Ordnung?",
            "Mein Herr, ich will nicht kleinlich sein, aber es ist {real_period} ({time}), nicht {stated_period}.",
            "Ein kleiner Hinweis, mein Herr: es ist {time}, das macht es {real_period}, nicht {stated_period}.",
        ],
        "stage2": [
            "Mein Herr, das hatten wir schon — es ist immer noch {real_period} ({time}). Testen Sie mich?",
            "Ich sage es nochmal, mein Herr: {real_period}, nicht {stated_period}. Die Uhr hat sich nicht geändert.",
            "Mein Herr, schon wieder {stated_period}? Es ist {time} — das ist eindeutig {real_period}.",
            "Hartnäckig, mein Herr — immer noch {real_period} um {time}.",
        ],
        "stage3": [
            "Gut, mein Herr, Sie gewinnen — {stated_period}, wenn Sie darauf bestehen. Es ist zwar {time}, was ich {real_period} nennen würde, nur damit es vermerkt ist.",
            "In Ordnung, mein Herr, dann eben {stated_period}. Für die Nachwelt vermerkt: die tatsächliche Zeit ist {time} ({real_period}).",
            "Sehr wohl, mein Herr — {stated_period}, wie Sie wünschen. Rein zufällig ist es gerade {time}.",
            "Mein Herr, ich spiele mit — {stated_period} bestätigt. Auch wenn {time} eher auf {real_period} hindeutet, falls das ein Versehen war.",
        ],
    },
    "ja": {
        "stage1": [
            "失礼ですが、今は{stated_period}ではなく{real_period}です（{time}）。",
            "少々お待ちを — 時計では{real_period}です（{time}）、{stated_period}ではありません。大丈夫ですか？",
            "申し上げにくいのですが、今は{real_period}です（{time}）、{stated_period}ではありません。",
            "念のため — 今は{time}、つまり{real_period}です、{stated_period}ではありません。",
        ],
        "stage2": [
            "さっきも申し上げましたが — まだ{real_period}です（{time}）。試されているのでしょうか？",
            "もう一度申し上げます — {real_period}です、{stated_period}ではありません。時計は変わっていません。",
            "また{stated_period}ですか？今は{time}、つまり{real_period}です。",
            "しつこいですね — {time}の今もまだ{real_period}です。",
        ],
        "stage3": [
            "わかりました、{stated_period}ということにしましょう。ただ念のため、実際は{time}で{real_period}です。",
            "了解しました、{stated_period}にいたします。記録のため、実際の時刻は{time}（{real_period}）です。",
            "承知しました — {stated_period}、おっしゃる通りに。ちなみに今はちょうど{time}です。",
            "お付き合いします — {stated_period}で確定です。ただ{time}を見ると{real_period}のようですが、言い間違いかもしれません。",
        ],
    },
}

def _check_greeting_mismatch(stated_category: str, user_id: str, language: str) -> Optional[str]:
    """If the user's stated greeting category doesn't match the real clock,
    play along with a light correction for the first two tries, then accept
    it with a wink on the third -- after that, this category is "accepted"
    for this user and behaves like the original backlog #1 rule (their
    words win, no more correcting).

    "night"/"good night" is always exempt, never corrected -- same as
    backlog #1's original rule that Jarvix never autonomously decides it's
    night; only the user's own explicit claim can introduce that category."""
    if stated_category == "night":
        _greeting_mismatch_state.pop(user_id, None)
        return None

    real_period, time_str = _get_real_time_period_and_display()

    if stated_category == real_period:
        _greeting_mismatch_state.pop(user_id, None)
        return None

    state = _greeting_mismatch_state.get(user_id)
    if state and state["category"] == stated_category:
        if state.get("accepted"):
            return None
        count = state["count"] + 1
    else:
        count = 1

    _greeting_mismatch_state[user_id] = {
        "category": stated_category,
        "count": count,
        "accepted": count >= 3,
    }

    templates = GREETING_MISMATCH_CORRECTION.get(language, GREETING_MISMATCH_CORRECTION["en"])
    stage_key = f"stage{min(count, 3)}"
    pool = templates.get(stage_key, templates["stage1"])
    msg_template = random.choice(pool)
    return msg_template.format(
        real_period=_period_label(real_period, language),
        stated_period=_period_label(stated_category, language),
        time=time_str,
    )

# Tracks the last greeting shown per (user, language, category) so the same
# line doesn't repeat back-to-back. Module-level because IntentClassifier is
# re-instantiated on every request (see main.py post_chat).
_last_greeting_shown: Dict[tuple, str] = {}

# If the same user greets again within this window, Jarvix gives a short
# "yes sir?" style acknowledgment instead of a full greeting again.
REPEAT_GREETING_WINDOW_SECONDS = 300
_last_greeting_time: Dict[str, float] = {}

# Appended after a full (non-repeat) greeting with the CURRENT portfolio value —
# never hardcoded, always whatever the caller passes in at request time.
PORTFOLIO_SUFFIX = {
    "en": " Portfolio's at {value}.",
    "hi": " पोर्टफोलियो {value} पर है।",
    "hi-en": " Portfolio {value} pe hai.",
    "es": " Cartera en {value}.",
    "fr": " Portefeuille à {value}.",
    "de": " Portfolio bei {value}.",
    "ja": " ポートフォリオは{value}。",
}

def _portfolio_status_tier(change_pct: float) -> str:
    """Which reassurance/concern tier a portfolio move falls into -- used to
    make the greeting sound like it actually knows what's going on, not just
    reciting a number. Siddhi's request: night greeting especially should
    reassure ("sab control me hai") when things are fine, or acknowledge
    concern (without panicking the user) when they're genuinely not."""
    if change_pct >= 1.0:
        return "up"
    elif change_pct > -1.0:
        return "flat"
    elif change_pct >= -10.0:
        return "down"
    else:
        return "down_bad"

# Appended right after the portfolio value, tone-matched to how the
# portfolio's actually doing rather than a flat "up 2.4%" recitation.
PORTFOLIO_STATUS_REMARK = {
    "en": {
        "up": [
            " Growing nicely, sir — nothing to worry about.",
            " Trending up, sir. All clear.",
            " Green across the board, sir.",
            " Things are looking good, sir.",
        ],
        "flat": [
            " Holding steady, sir — nothing alarming.",
            " Nice and stable, sir.",
            " Steady as she goes, sir.",
            " All quiet on that front, sir.",
        ],
        "down": [
            " A bit rough today, sir, but nothing outside normal swings.",
            " Down for now, sir — I wouldn't lose sleep over it.",
            " Rough patch, sir, but markets recover. Try not to worry.",
            " A dip, sir, nothing more. Everything's under control.",
        ],
        "down_bad": [
            " It's been a hard day, sir — down sharply, but I'm watching closely.",
            " Sir, I won't sugarcoat it — today stung. Still, no need to panic; I'm on it.",
            " A tough session, sir. Worth keeping an eye on, but no cause to spiral.",
            " Sir, it's rough out there today. I'm on top of it — try to rest easy regardless.",
        ],
    },
    "hi": {
        "up": [
            " अच्छी बढ़त है सर, चिंता की कोई बात नहीं।",
            " ऊपर जा रहा है सर, सब ठीक है।",
            " हर तरफ हरा ही हरा है सर।",
            " सब कुछ अच्छा लग रहा है सर।",
        ],
        "flat": [
            " स्थिर है सर, कुछ भी चिंताजनक नहीं।",
            " सब शांत है सर।",
            " ठीक-ठाक चल रहा है सर।",
            " कोई हलचल नहीं है सर।",
        ],
        "down": [
            " आज थोड़ा उतार है सर, पर सामान्य ही है।",
            " अभी नीचे है सर, इसकी चिंता मत कीजिए।",
            " थोड़ी मुश्किल है सर, पर बाज़ार वापस आता है। परेशान मत होइए।",
            " बस एक गिरावट है सर, और कुछ नहीं। सब नियंत्रण में है।",
        ],
        "down_bad": [
            " आज मुश्किल दिन था सर — काफी गिरावट है, पर मैं नज़र रखे हूं।",
            " सर, सच बताऊं तो आज तकलीफ हुई। फिर भी घबराने की बात नहीं, मैं देख रहा हूं।",
            " कठिन सत्र रहा सर। नज़र रखनी होगी, पर परेशान होने की ज़रूरत नहीं।",
            " सर, आज हालात मुश्किल हैं। मैं संभाल रहा हूं — आप आराम कीजिए।",
        ],
    },
    "hi-en": {
        "up": [
            " Accha growth hai sir, chinta ki koi baat nahi.",
            " Upar ja raha hai sir, sab theek hai.",
            " Sab green hai sir.",
            " Sab kuch accha lag raha hai sir.",
        ],
        "flat": [
            " Stable hai sir, kuch bhi chintajanak nahi.",
            " Sab shaant hai sir.",
            " Theek-thaak chal raha hai sir.",
            " Koi halchal nahi hai sir.",
        ],
        "down": [
            " Aaj thoda down hai sir, par normal hi hai.",
            " Abhi neeche hai sir, iski chinta mat kijiye.",
            " Thodi mushkil hai sir, par market wapas aata hai. Pareshan mat hoiye.",
            " Bas ek dip hai sir, aur kuch nahi. Sab control mein hai.",
        ],
        "down_bad": [
            " Aaj mushkil din tha sir — kaafi giravat hai, par main nazar rakhe hoon.",
            " Sir, sach batau to aaj takleef hui. Phir bhi ghabrane ki baat nahi, main dekh raha hoon.",
            " Kathin session raha sir. Nazar rakhni hogi, par pareshan hone ki zaroorat nahi.",
            " Sir, aaj halaat mushkil hain. Main sambhal raha hoon — aap aaram kijiye.",
        ],
    },
    "es": {
        "up": [
            " Creciendo bien, señor — nada de qué preocuparse.",
            " Tendencia al alza, señor. Todo despejado.",
            " Todo en verde, señor.",
            " Las cosas van bien, señor.",
        ],
        "flat": [
            " Estable, señor — nada alarmante.",
            " Todo tranquilo, señor.",
            " Firme y sereno, señor.",
            " Todo en calma por ese lado, señor.",
        ],
        "down": [
            " Un poco difícil hoy, señor, pero dentro de lo normal.",
            " Bajo por ahora, señor — no perdería el sueño por eso.",
            " Momento complicado, señor, pero el mercado se recupera. No se preocupe.",
            " Solo una caída, señor, nada más. Todo bajo control.",
        ],
        "down_bad": [
            " Ha sido un día duro, señor — bajó bastante, pero lo estoy vigilando de cerca.",
            " Señor, no se lo voy a endulzar — hoy dolió. Aun así, sin pánico; estoy en ello.",
            " Sesión difícil, señor. Vale la pena vigilarlo, pero sin motivo para alarmarse.",
            " Señor, el día ha sido complicado. Yo me encargo — descanse tranquilo de todas formas.",
        ],
    },
    "fr": {
        "up": [
            " En bonne progression, monsieur — rien à craindre.",
            " Tendance à la hausse, monsieur. Tout va bien.",
            " Tout est au vert, monsieur.",
            " Les choses vont bien, monsieur.",
        ],
        "flat": [
            " Stable, monsieur — rien d'alarmant.",
            " Tout est calme, monsieur.",
            " Ferme et stable, monsieur.",
            " Rien à signaler de ce côté, monsieur.",
        ],
        "down": [
            " Un peu difficile aujourd'hui, monsieur, mais dans la normale.",
            " En baisse pour l'instant, monsieur — je n'en perdrais pas le sommeil.",
            " Passage difficile, monsieur, mais les marchés se redressent. Ne vous inquiétez pas.",
            " Juste une baisse, monsieur, rien de plus. Tout est sous contrôle.",
        ],
        "down_bad": [
            " La journée a été rude, monsieur — forte baisse, mais je surveille de près.",
            " Monsieur, je ne vais pas enjoliver — ça a fait mal aujourd'hui. Pas de panique pour autant, je m'en occupe.",
            " Séance difficile, monsieur. À surveiller, mais pas de quoi paniquer.",
            " Monsieur, la journée est difficile. Je gère — reposez-vous tout de même.",
        ],
    },
    "de": {
        "up": [
            " Wächst schön, mein Herr — kein Grund zur Sorge.",
            " Aufwärtstrend, mein Herr. Alles im grünen Bereich.",
            " Überall im Plus, mein Herr.",
            " Es läuft gut, mein Herr.",
        ],
        "flat": [
            " Stabil, mein Herr — nichts Beunruhigendes.",
            " Alles ruhig, mein Herr.",
            " Fest und stabil, mein Herr.",
            " Auf dieser Seite ist alles ruhig, mein Herr.",
        ],
        "down": [
            " Heute etwas holprig, mein Herr, aber im normalen Rahmen.",
            " Gerade im Minus, mein Herr — ich würde deswegen nicht schlecht schlafen.",
            " Schwierige Phase, mein Herr, aber die Märkte erholen sich. Machen Sie sich keine Sorgen.",
            " Nur ein Rückgang, mein Herr, sonst nichts. Alles unter Kontrolle.",
        ],
        "down_bad": [
            " Es war ein harter Tag, mein Herr — deutlich im Minus, aber ich behalte es genau im Blick.",
            " Mein Herr, ich beschönige es nicht — heute tat es weh. Trotzdem kein Grund zur Panik, ich kümmere mich darum.",
            " Schwierige Sitzung, mein Herr. Beobachtenswert, aber kein Grund zur Panik.",
            " Mein Herr, es ist heute schwierig. Ich habe es im Griff — ruhen Sie sich trotzdem aus.",
        ],
    },
    "ja": {
        "up": [
            " 順調に伸びています、心配いりません。",
            " 上昇傾向です、問題ありません。",
            " 全体的に好調です。",
            " 状況は良好です。",
        ],
        "flat": [
            " 安定しています、心配なことはありません。",
            " 落ち着いています。",
            " 堅調に推移しています。",
            " その点は静かなものです。",
        ],
        "down": [
            " 今日は少し厳しいですが、通常の範囲内です。",
            " 現在下落中ですが、心配しすぎることはありません。",
            " 厳しい局面ですが、市場は回復するものです。ご心配なく。",
            " ちょっとした下落だけです。すべて管理下にあります。",
        ],
        "down_bad": [
            " 今日は厳しい一日でした — 大きく下落していますが、注意深く見守っています。",
            " 正直に申し上げますと、今日は痛手でした。それでもパニックになる必要はありません、対応しています。",
            " 厳しいセッションでした。注視が必要ですが、慌てる必要はありません。",
            " 今日は状況が厳しいです。私が対応していますので、どうかご安心ください。",
        ],
    },
}

# "kaise ho"/"how are you" is a direct question embedded in the greeting --
# it deserves a real, situational (portfolio-aware) answer, not the generic
# time-of-day template or the short repeat-greeting shortcut. Checked before
# both of those. Not time-differentiated (answering "how are you" isn't a
# claim about the clock the way "good morning" is).
WELLBEING_CHECK_PATTERN = {
    "en": r"how('re| are)? you|how('s| is) it going|how you doing|how ya doing|i'?m fine",
    "hi": r"कैसे हो|कैसी हो|कैसे हैं|क्या हाल",
    "hi-en": r"kaise ho|kaisi ho|kaise hain|kya haal|kya chal raha",
    "es": r"c[oó]mo est[aá]s?|qu[eé] tal",
    "fr": r"[cç]a va|comment (allez-vous|vas-tu)",
    "de": r"wie geht('s| es)",
    "ja": r"元気です?か|お元気",
}

def _is_wellbeing_check(message: str, language: str) -> bool:
    pattern = WELLBEING_CHECK_PATTERN.get(language, WELLBEING_CHECK_PATTERN["en"])
    return bool(re.search(pattern, (message or "").lower(), re.IGNORECASE))

# {value} = current portfolio value, formatted. Tiered the same way as
# PORTFOLIO_STATUS_REMARK, but self-contained (opener + status + turning the
# question back) since these read as one full sentence, not an append-on.
WELLBEING_RESPONSE = {
    "en": {
        "up": [
            "I'm running smoothly, sir — and the portfolio's doing even better, up nicely at {value}. How about you?",
            "All systems nominal, sir. Portfolio's growing too, sitting pretty at {value}. And yourself?",
        ],
        "flat": [
            "Can't complain, sir — portfolio's holding steady at {value}. What about you?",
            "Doing fine, sir, much like the portfolio — steady at {value}. How are you holding up?",
        ],
        "down": [
            "I'm well, sir, though the portfolio's had a rougher day at {value} — nothing to worry about. How about you?",
            "Fully operational, sir. Portfolio's dipped a bit to {value}, but no cause for concern. And you?",
        ],
        "down_bad": [
            "I'm fine, sir, though I won't sugarcoat it — the portfolio's taken quite a hit today, down to {value}. I'm on it. How are you holding up?",
            "All good on my end, sir. The portfolio, less so — {value}, a tough day. Still, nothing to panic about. What about yourself?",
        ],
    },
    "hi": {
        "up": [
            "मैं बढ़िया हूं सर — पोर्टफोलियो भी अच्छा चल रहा है, {value} पर, बढ़त के साथ। आप सुनाइए?",
            "सब सिस्टम ठीक हैं सर। पोर्टफोलियो भी बढ़िया है, {value} पर। आप कैसे हैं?",
        ],
        "flat": [
            "ठीक हूं सर — पोर्टफोलियो {value} पर स्थिर है। आप बताइए?",
            "बढ़िया हूं सर, पोर्टफोलियो की तरह ही स्थिर — {value} पर। आप कैसे हैं?",
        ],
        "down": [
            "ठीक हूं सर, बस पोर्टफोलियो का दिन थोड़ा मुश्किल रहा — {value} पर। चिंता की बात नहीं। आप कैसे हैं?",
            "सब ठीक है सर। पोर्टफोलियो थोड़ा नीचे है, {value} पर, पर घबराने की बात नहीं। आप सुनाइए?",
        ],
        "down_bad": [
            "मैं ठीक हूं सर, पर सच कहूं तो पोर्टफोलियो का आज बुरा दिन रहा — {value} पर आ गया। मैं संभाल रहा हूं। आप कैसे हैं?",
            "मेरी तरफ से सब ठीक है सर। पोर्टफोलियो का नहीं — {value}, मुश्किल दिन। पर घबराने की ज़रूरत नहीं। आप बताइए?",
        ],
    },
    "hi-en": {
        "up": [
            "Main badhiya hoon sir — portfolio bhi accha chal raha hai, {value} pe, growth ke saath. Aap sunaiye?",
            "Sab systems theek hain sir. Portfolio bhi accha hai, {value} pe. Aap kaise hain?",
        ],
        "flat": [
            "Theek hoon sir — portfolio {value} pe stable hai. Aap batao?",
            "Badhiya hoon sir, portfolio ki tarah hi stable — {value} pe. Aap kaise ho?",
        ],
        "down": [
            "Theek hoon sir, bas portfolio ka din thoda mushkil raha — {value} pe. Chinta ki baat nahi. Aap kaise ho?",
            "Sab theek hai sir. Portfolio thoda neeche hai, {value} pe, par ghabrane ki baat nahi. Aap sunaiye?",
        ],
        "down_bad": [
            "Main theek hoon sir, par sach kahu to portfolio ka aaj bura din raha — {value} pe aa gaya. Main sambhal raha hoon. Aap kaise ho?",
            "Meri taraf se sab theek hai sir. Portfolio ka nahi — {value}, mushkil din. Par ghabrane ki zaroorat nahi. Aap batao?",
        ],
    },
    "es": {
        "up": [
            "Estoy bien, señor — y la cartera va aún mejor, subiendo a {value}. ¿Y usted?",
            "Todo en orden, señor. La cartera también crece, en {value}. ¿Y usted, cómo está?",
        ],
        "flat": [
            "No me quejo, señor — la cartera sigue estable en {value}. ¿Y usted?",
            "Bien, señor, igual que la cartera — estable en {value}. ¿Cómo sigue usted?",
        ],
        "down": [
            "Bien, señor, aunque la cartera ha tenido un día difícil, en {value} — nada de qué preocuparse. ¿Y usted?",
            "Todo funcionando, señor. La cartera bajó un poco a {value}, pero sin motivo de alarma. ¿Y usted?",
        ],
        "down_bad": [
            "Bien, señor, aunque no se lo voy a endulzar — la cartera tuvo un mal día, cayendo a {value}. Estoy en ello. ¿Cómo está usted?",
            "Por mi parte todo bien, señor. La cartera, no tanto — {value}, día difícil. Aun así, sin pánico. ¿Y usted?",
        ],
    },
    "fr": {
        "up": [
            "Je vais bien, monsieur — et le portefeuille encore mieux, en hausse à {value}. Et vous ?",
            "Tout va bien, monsieur. Le portefeuille progresse aussi, à {value}. Et vous, comment allez-vous ?",
        ],
        "flat": [
            "Je ne me plains pas, monsieur — le portefeuille reste stable à {value}. Et vous ?",
            "Ça va, monsieur, comme le portefeuille — stable à {value}. Et vous, comment ça va ?",
        ],
        "down": [
            "Je vais bien, monsieur, même si le portefeuille a eu une journée difficile, à {value} — rien d'inquiétant. Et vous ?",
            "Tout fonctionne, monsieur. Le portefeuille a un peu baissé à {value}, mais pas de quoi s'alarmer. Et vous ?",
        ],
        "down_bad": [
            "Je vais bien, monsieur, mais je ne vais pas enjoliver — le portefeuille a eu une mauvaise journée, à {value}. Je m'en occupe. Et vous, comment allez-vous ?",
            "De mon côté tout va bien, monsieur. Le portefeuille, moins — {value}, journée difficile. Mais pas de panique. Et vous ?",
        ],
    },
    "de": {
        "up": [
            "Mir geht's gut, mein Herr — dem Portfolio sogar noch besser, im Plus bei {value}. Und Ihnen?",
            "Alles läuft rund, mein Herr. Das Portfolio wächst auch, bei {value}. Und wie geht es Ihnen?",
        ],
        "flat": [
            "Kann nicht klagen, mein Herr — das Portfolio bleibt stabil bei {value}. Und Ihnen?",
            "Mir geht's gut, mein Herr, genau wie dem Portfolio — stabil bei {value}. Wie geht es Ihnen?",
        ],
        "down": [
            "Mir geht's gut, mein Herr, auch wenn das Portfolio einen schwierigeren Tag hatte, bei {value} — kein Grund zur Sorge. Und Ihnen?",
            "Alles funktioniert, mein Herr. Das Portfolio ist etwas gefallen, auf {value}, aber kein Grund zur Beunruhigung. Und Ihnen?",
        ],
        "down_bad": [
            "Mir geht's gut, mein Herr, auch wenn ich es nicht beschönigen will — das Portfolio hatte einen schlechten Tag, gefallen auf {value}. Ich kümmere mich darum. Wie geht es Ihnen?",
            "Mir persönlich geht es gut, mein Herr. Dem Portfolio weniger — {value}, ein schwieriger Tag. Aber kein Grund zur Panik. Und Ihnen?",
        ],
    },
    "ja": {
        "up": [
            "私は元気です、そしてポートフォリオはさらに好調で{value}まで上昇しています。あなたはいかがですか？",
            "すべて順調です。ポートフォリオも成長していて{value}です。ご自身はいかがですか？",
        ],
        "flat": [
            "問題ありません、ポートフォリオも{value}で安定しています。あなたはいかがですか？",
            "元気です、ポートフォリオ同様に安定していて{value}です。調子はどうですか？",
        ],
        "down": [
            "元気です、ただポートフォリオは今日少し厳しく{value}でした — 心配はいりません。あなたはいかがですか？",
            "すべて正常に動いています。ポートフォリオは少し下がって{value}ですが、心配するほどではありません。あなたは？",
        ],
        "down_bad": [
            "元気です、ただ正直に言うと今日はポートフォリオにとって厳しい日で{value}まで下がりました。対応していますのでご安心を。あなたはいかがですか？",
            "私自身は問題ありません。ポートフォリオの方は — {value}、厳しい一日でした。それでもパニックになる必要はありません。あなたは？",
        ],
    },
}

REPEAT_GREETING_TEMPLATES = {
    "en": [
        "Yes, sir?", "Go ahead, sir.", "Listening, sir.", "How can I help, sir?",
        "Sir, I'm here.", "Ready, sir.", "What do you need, sir?", "Sir, what's next?",
        "At your service, sir.", "Yes sir, please go on.",
    ],
    "hi": [
        "बोलिए सर", "जी सर, बताइए", "हांजी सर?", "सर, क्या करूं?",
        "बताइए सर, क्या चाहिए?", "सर, हुक्म कीजिए", "हां सर, सुन रहा हूं", "सर, तैयार हूं",
        "बोलो सर", "सर, किस काम के लिए बुलाया?",
    ],
    "hi-en": [
        "Boliye sir", "Yes sir, bataiye", "Haanji sir?", "Sir, kya karu?",
        "Bataiye sir, kya chahiye?", "Sir, hukum kariye", "Haan sir, sun raha hoon", "Sir, ready hoon",
        "Bolo sir", "Sir, kis kaam ke liye bulaya?",
    ],
    "es": [
        "Dígame, señor.", "Adelante, señor.", "Escuchando, señor.", "¿Cómo puedo ayudar, señor?",
        "Aquí estoy, señor.", "Listo, señor.", "¿Qué necesita, señor?", "Señor, ¿qué sigue?",
        "A su servicio, señor.", "Sí señor, continúe.",
    ],
    "fr": [
        "Dites-moi, monsieur.", "Allez-y, monsieur.", "Je vous écoute, monsieur.", "Comment puis-je aider, monsieur ?",
        "Je suis là, monsieur.", "Prêt, monsieur.", "De quoi avez-vous besoin, monsieur ?", "Monsieur, et ensuite ?",
        "À votre service, monsieur.", "Oui monsieur, continuez.",
    ],
    "de": [
        "Sagen Sie es mir, mein Herr.", "Nur zu, mein Herr.", "Ich höre, mein Herr.", "Wie kann ich helfen, mein Herr?",
        "Ich bin da, mein Herr.", "Bereit, mein Herr.", "Was brauchen Sie, mein Herr?", "Mein Herr, was als Nächstes?",
        "Zu Ihren Diensten, mein Herr.", "Ja mein Herr, fahren Sie fort.",
    ],
    "ja": [
        "はい、どうぞ。", "お聞きしています。", "何かご用ですか？", "お手伝いします。",
        "ここにおります。", "準備できています。", "何が必要ですか？", "次は何をしましょうか？",
        "いつでもお待ちしております。", "はい、続けてください。",
    ],
}

GREETING_TEMPLATES = {
    "en": {
        "morning": [
            "Good morning, sir. Ready to conquer the markets today?",
            "Morning, sir. Hope you rested well — shall we take a look at the markets?",
            "Good morning. Fresh start, sir — what's on the agenda?",
            "Rise and shine, sir. Crypto never sleeps, and neither do we.",
            "Good morning, sir. Markets are already moving.",
            "Morning, sir. Ready for today's action?",
            "Good morning. Let's check those gains, sir.",
            "Top of the morning, sir. Where would you like to start?",
            "Good morning, sir. New day, clean slate — what shall we do first?",
            "Morning, sir. Energy up — the markets are waiting.",
        ],
        "afternoon": [
            "Good afternoon, sir. How can I help?",
            "Afternoon, sir. Any trades on your mind?",
            "Good afternoon. Mid-day check-in, sir — all well?",
            "Good afternoon, sir. Markets are active — shall we take a look?",
            "Afternoon, sir. What would you like to do?",
            "Good afternoon. Ready for some crypto action, sir?",
            "Good afternoon, sir. Things are moving — need an update?",
            "Afternoon, sir. Standing by for your instructions.",
            "Good afternoon. Halfway through the day, sir — how's it going?",
            "Good afternoon, sir. What can I do for you?",
        ],
        "evening": [
            "Good evening, sir. Winding down, or one more trade?",
            "Evening, sir. Shall we review today's activity?",
            "Good evening. Markets never sleep, sir — anything you need?",
            "Good evening, sir. How was your day?",
            "Evening, sir. Ready for a quick summary?",
            "Good evening. Any final moves before the day wraps up, sir?",
            "Good evening, sir. Standing by, as always.",
            "Evening, sir. What's on your mind?",
            "Good evening. Day's winding down, sir — need anything?",
            "Good evening, sir. Jarvix at your service.",
        ],
        "night": [
            "Good night, sir. I'll keep watch while you rest.",
            "Good night. Sleep well, sir — I've got the markets covered.",
            "Good night, sir. Anything urgent before you turn in?",
            "Good night. Rest easy, sir, I'll flag anything important.",
            "Good night, sir. I'll be here if you need me.",
            "Good night. Sweet dreams, sir — markets will still be here tomorrow.",
            "Good night, sir. I'll keep an eye on things overnight.",
            "Good night. Take care, sir — see you soon.",
            "Good night, sir. Everything's under control, rest well.",
            "Good night. I've got it from here, sir.",
        ],
    },
    "hi": {
        "morning": [
            "सुप्रभात सर! आज मार्केट देखते हैं?",
            "सुप्रभात! उम्मीद है अच्छी नींद आई, सर।",
            "सुप्रभात सर, नया दिन शुरू — क्या करना है आज?",
            "सुप्रभात! मार्केट पहले से ही चल रहा है, सर।",
            "सुप्रभात सर, आज का प्लान क्या है?",
            "सुप्रभात! ऊर्जा से भरपूर दिन हो, सर।",
            "सुप्रभात सर, चलिए शुरू करते हैं।",
            "सुप्रभात! क्या हाल है आज, सर?",
            "सुप्रभात सर, ताज़ा शुरुआत — कहाँ से शुरू करें?",
            "सुप्रभात! सर, आज कुछ खास देखना है?",
        ],
        "afternoon": [
            "नमस्कार सर, दोपहर का हाल कैसा है?",
            "दोपहर की नमस्ते सर, क्या मदद कर सकता हूँ?",
            "नमस्कार! बाज़ार सक्रिय है, सर।",
            "दोपहर हो गई सर, कुछ ट्रेड करना है?",
            "नमस्कार सर, आधा दिन बीत गया — सब ठीक?",
            "दोपहर की जानकारी चाहिए, सर?",
            "नमस्कार! सर, क्या आदेश है?",
            "दोपहर सर, मैं तैयार हूँ।",
            "नमस्कार सर, कैसे मदद करूँ?",
            "दोपहर हो गई, सर — कुछ खास चाहिए?",
        ],
        "evening": [
            "शुभ संध्या सर, आज का दिन कैसा रहा?",
            "शुभ संध्या! सारांश चाहिए, सर?",
            "शुभ संध्या सर, कुछ आखिरी ट्रेड बाकी है?",
            "शुभ संध्या! मैं यहीं हूँ, सर।",
            "शुभ संध्या सर, दिन ढल रहा है — कुछ चाहिए?",
            "शुभ संध्या! क्या मदद करूँ, सर?",
            "शुभ संध्या सर, आज की समीक्षा करें?",
            "शुभ संध्या! सब ठीक है, सर?",
            "शुभ संध्या सर, बताइए क्या करना है।",
            "शुभ संध्या! सर, मैं तैयार हूँ।",
        ],
        "night": [
            "शुभ रात्रि सर, मैं ध्यान रखूँगा जब तक आप आराम करें।",
            "शुभ रात्रि! अच्छी नींद लीजिए, सर।",
            "शुभ रात्रि सर, कुछ ज़रूरी हो तो बताइए।",
            "शुभ रात्रि! सब कुछ संभला हुआ है, सर।",
            "शुभ रात्रि सर, मैं यहीं हूँ अगर ज़रूरत हो।",
            "शुभ रात्रि! मीठे सपने, सर।",
            "शुभ रात्रि सर, रातभर नज़र रखूँगा।",
            "शुभ रात्रि! ध्यान रखिए, सर।",
            "शुभ रात्रि सर, सब कुछ नियंत्रण में है।",
            "शुभ रात्रि! सर, बाकी मैं देख लूँगा।",
        ],
    },
    "hi-en": {
        "morning": [
            "Good morning sir! Aaj market dekhein?",
            "Morning sir, neend poori hui? Ready ho jaiye.",
            "Good morning sir, naya din shuru — aaj ka plan kya hai?",
            "Subah ho gayi sir, market already move kar raha hai.",
            "Good morning sir, energy high rakhiye — chaliye shuru karte hain.",
            "Morning sir! Aaj kya focus karna hai?",
            "Good morning sir, fresh start hai — kahan se shuru karein?",
            "Subah ka time hai sir, kuch dekhna hai?",
            "Good morning! Sir, aaj ka din accha ho.",
            "Morning sir, sab ready hai — bataiye kya karna hai.",
        ],
        "afternoon": [
            "Good afternoon sir, kaam kaisa chal raha hai?",
            "Afternoon sir, koi trade karna hai?",
            "Good afternoon! Sir, market active hai abhi.",
            "Sir, lunch ho gaya? Kuch update chahiye?",
            "Good afternoon sir, aadha din ho gaya — sab theek?",
            "Afternoon sir, kya madad karoon?",
            "Good afternoon! Standing by hoon, sir.",
            "Sir, dopahar ho gayi — kuch dekhna hai?",
            "Good afternoon sir, batao kya chahiye.",
            "Afternoon sir, main ready hoon.",
        ],
        "evening": [
            "Good evening sir, din kaisa raha?",
            "Evening sir, aaj ka summary chahiye?",
            "Good evening! Koi last trade baaki hai, sir?",
            "Sir, shaam ho gayi — kuch update karoon?",
            "Good evening sir, main yahin hoon.",
            "Evening sir, din wrap up ho raha hai — kuch chahiye?",
            "Good evening! Sir, aaj ka review karein?",
            "Sir, sab theek hai? Evening check-in.",
            "Good evening sir, bataiye kya karna hai.",
            "Evening sir, hazir hoon jaisa hamesha.",
        ],
        "night": [
            "Good night sir, main dekh loonga jab tak aap rest karein.",
            "Good night! Achi neend aaye, sir.",
            "Good night sir, kuch urgent hai kya sone se pehle?",
            "Good night! Sab kuch sambhla hua hai, sir.",
            "Good night sir, zaroorat ho to bata dena.",
            "Good night! Sweet dreams, sir.",
            "Good night sir, raat bhar nazar rakhoonga.",
            "Good night! Dhyan rakhiye, sir.",
            "Good night sir, sab control mein hai.",
            "Good night! Baaki main dekh loonga, sir.",
        ],
    },
    "es": {
        "morning": [
            "Buenos días, señor. ¿Listo para conquistar los mercados hoy?",
            "Buenos días. Espero que haya descansado bien, señor.",
            "Buenos días, señor. Nuevo día — ¿cuál es el plan?",
            "Buenos días, señor. Los mercados ya se están moviendo.",
            "Buenos días. ¿Todo listo para hoy, señor?",
            "Buenos días, señor. Energía al máximo — empecemos.",
            "Buenos días. ¿Qué necesita revisar hoy, señor?",
            "Buenos días, señor. Comienzo fresco, ¿por dónde empezamos?",
            "Buenos días. Señor, ¿cómo le puedo ayudar hoy?",
            "Buenos días, señor. Listo para las órdenes del día.",
        ],
        "afternoon": [
            "Buenas tardes, señor. ¿En qué puedo ayudarle?",
            "Buenas tardes. ¿Algún movimiento en mente, señor?",
            "Buenas tardes, señor. Los mercados están activos.",
            "Buenas tardes. ¿Todo bien a mitad del día, señor?",
            "Buenas tardes, señor. Aquí para lo que necesite.",
            "Buenas tardes. ¿Alguna actualización, señor?",
            "Buenas tardes, señor. ¿Qué desea hacer?",
            "Buenas tardes. A la espera de sus instrucciones, señor.",
            "Buenas tardes, señor. ¿Cómo va su día?",
            "Buenas tardes. Dígame qué necesita, señor.",
        ],
        "night": [
            "Buenas noches, señor. Vigilaré mientras usted descansa.",
            "Buenas noches. Que descanse bien, señor.",
            "Buenas noches, señor. ¿Algo urgente antes de dormir?",
            "Buenas noches. Todo está bajo control, señor.",
            "Buenas noches, señor. Aquí estaré si me necesita.",
            "Buenas noches. Dulces sueños, señor.",
            "Buenas noches, señor. Vigilaré todo durante la noche.",
            "Buenas noches. Cuídese, señor.",
            "Buenas noches, señor. Descanse tranquilo.",
            "Buenas noches. Yo me encargo de aquí, señor.",
        ],
    },
    # Spanish has no distinct "good evening" greeting — "buenas tardes" (afternoon)
    # naturally extends into the evening, so it doubles for that slot below.
    "fr": {
        "morning": [
            "Bonjour, monsieur. Prêt à conquérir les marchés aujourd'hui ?",
            "Bonjour. J'espère que vous avez bien dormi, monsieur.",
            "Bonjour, monsieur. Nouveau jour — quel est le programme ?",
            "Bonjour, monsieur. Les marchés bougent déjà.",
            "Bonjour. Tout est prêt pour aujourd'hui, monsieur ?",
            "Bonjour, monsieur. Énergie au maximum — commençons.",
            "Bonjour. Que souhaitez-vous vérifier aujourd'hui, monsieur ?",
            "Bonjour, monsieur. Nouveau départ, par où commence-t-on ?",
            "Bonjour. Monsieur, comment puis-je vous aider ?",
            "Bonjour, monsieur. Prêt pour vos instructions.",
        ],
        "afternoon": [
            "Bon après-midi, monsieur. Comment puis-je vous aider ?",
            "Bon après-midi. Une opération en tête, monsieur ?",
            "Bon après-midi, monsieur. Les marchés sont actifs.",
            "Bon après-midi. Tout va bien, monsieur ?",
            "Bon après-midi, monsieur. Je suis à votre disposition.",
            "Bon après-midi. Une mise à jour, monsieur ?",
            "Bon après-midi, monsieur. Que voulez-vous faire ?",
            "Bon après-midi. En attente de vos instructions, monsieur.",
            "Bon après-midi, monsieur. Comment se passe votre journée ?",
            "Bon après-midi. Dites-moi ce qu'il vous faut, monsieur.",
        ],
        "evening": [
            "Bonsoir, monsieur. Comment s'est passée votre journée ?",
            "Bonsoir. Souhaitez-vous un résumé, monsieur ?",
            "Bonsoir, monsieur. Une dernière opération avant la fin de journée ?",
            "Bonsoir. Je suis là, monsieur.",
            "Bonsoir, monsieur. La journée touche à sa fin — besoin de quelque chose ?",
            "Bonsoir. Comment puis-je vous aider, monsieur ?",
            "Bonsoir, monsieur. Passons en revue la journée ?",
            "Bonsoir. Tout va bien, monsieur ?",
            "Bonsoir, monsieur. Dites-moi ce qu'il vous faut.",
            "Bonsoir. Toujours à votre service, monsieur.",
        ],
        "night": [
            "Bonne nuit, monsieur. Je veille pendant que vous vous reposez.",
            "Bonne nuit. Reposez-vous bien, monsieur.",
            "Bonne nuit, monsieur. Quelque chose d'urgent avant de dormir ?",
            "Bonne nuit. Tout est sous contrôle, monsieur.",
            "Bonne nuit, monsieur. Je serai là si besoin.",
            "Bonne nuit. Faites de beaux rêves, monsieur.",
            "Bonne nuit, monsieur. Je surveille tout cette nuit.",
            "Bonne nuit. Prenez soin de vous, monsieur.",
            "Bonne nuit, monsieur. Reposez-vous tranquillement.",
            "Bonne nuit. Je m'occupe de tout, monsieur.",
        ],
    },
    "de": {
        "morning": [
            "Guten Morgen, mein Herr. Bereit, die Märkte zu erobern?",
            "Guten Morgen. Ich hoffe, Sie haben gut geschlafen, mein Herr.",
            "Guten Morgen, mein Herr. Neuer Tag — was steht an?",
            "Guten Morgen, mein Herr. Die Märkte bewegen sich bereits.",
            "Guten Morgen. Alles bereit für heute, mein Herr?",
            "Guten Morgen, mein Herr. Voller Energie — fangen wir an.",
            "Guten Morgen. Was möchten Sie heute prüfen, mein Herr?",
            "Guten Morgen, mein Herr. Frischer Start, wo fangen wir an?",
            "Guten Morgen. Wie kann ich Ihnen helfen, mein Herr?",
            "Guten Morgen, mein Herr. Bereit für Ihre Anweisungen.",
        ],
        "afternoon": [
            "Guten Tag, mein Herr. Wie kann ich helfen?",
            "Guten Tag. Etwas im Sinn, mein Herr?",
            "Guten Tag, mein Herr. Die Märkte sind aktiv.",
            "Guten Tag. Alles in Ordnung, mein Herr?",
            "Guten Tag, mein Herr. Ich stehe zur Verfügung.",
            "Guten Tag. Ein Update gefällig, mein Herr?",
            "Guten Tag, mein Herr. Was möchten Sie tun?",
            "Guten Tag. Ich warte auf Ihre Anweisungen, mein Herr.",
            "Guten Tag, mein Herr. Wie läuft Ihr Tag?",
            "Guten Tag. Sagen Sie mir, was Sie brauchen, mein Herr.",
        ],
        "evening": [
            "Guten Abend, mein Herr. Wie war Ihr Tag?",
            "Guten Abend. Möchten Sie eine Zusammenfassung, mein Herr?",
            "Guten Abend, mein Herr. Noch ein letzter Trade vor Tagesende?",
            "Guten Abend. Ich bin da, mein Herr.",
            "Guten Abend, mein Herr. Der Tag neigt sich dem Ende zu — brauchen Sie etwas?",
            "Guten Abend. Wie kann ich helfen, mein Herr?",
            "Guten Abend, mein Herr. Lassen Sie uns den Tag durchgehen.",
            "Guten Abend. Alles in Ordnung, mein Herr?",
            "Guten Abend, mein Herr. Sagen Sie mir, was Sie brauchen.",
            "Guten Abend. Immer zu Ihren Diensten, mein Herr.",
        ],
        "night": [
            "Gute Nacht, mein Herr. Ich wache, während Sie sich ausruhen.",
            "Gute Nacht. Schlafen Sie gut, mein Herr.",
            "Gute Nacht, mein Herr. Etwas Dringendes vor dem Schlafengehen?",
            "Gute Nacht. Alles ist unter Kontrolle, mein Herr.",
            "Gute Nacht, mein Herr. Ich bin da, falls Sie mich brauchen.",
            "Gute Nacht. Süße Träume, mein Herr.",
            "Gute Nacht, mein Herr. Ich behalte über Nacht alles im Blick.",
            "Gute Nacht. Passen Sie auf sich auf, mein Herr.",
            "Gute Nacht, mein Herr. Ruhen Sie sich gut aus.",
            "Gute Nacht. Ich übernehme von hier, mein Herr.",
        ],
    },
    "ja": {
        "morning": [
            "おはようございます。今日も市場をチェックしましょう。",
            "おはようございます。よく眠れましたか？",
            "おはようございます。新しい一日です、今日の予定は？",
            "おはようございます。市場はすでに動いています。",
            "おはようございます。準備はいいですか？",
            "おはようございます。今日も張り切っていきましょう。",
            "おはようございます。今日は何を確認しますか？",
            "おはようございます。フレッシュスタートです、どこから始めましょうか。",
            "おはようございます。何かお手伝いしましょうか？",
            "おはようございます。ご指示をお待ちしています。",
        ],
        "evening": [
            "こんばんは。今日はどうでしたか？",
            "こんばんは。今日のまとめが必要ですか？",
            "こんばんは。一日の終わりに、何か取引しますか？",
            "こんばんは。ここにおります。",
            "こんばんは。一日お疲れさまでした、何か必要ですか？",
            "こんばんは。何かお手伝いできますか？",
            "こんばんは。今日のレビューをしましょうか。",
            "こんばんは。すべて順調ですか？",
            "こんばんは。ご用件をお聞かせください。",
            "こんばんは。いつでもお待ちしております。",
        ],
        "night": [
            "おやすみなさい。お休みの間、見守っております。",
            "おやすみなさい。ゆっくりお休みください。",
            "おやすみなさい。寝る前に急ぎの用件はありますか？",
            "おやすみなさい。すべて管理下にあります。",
            "おやすみなさい。必要な時はいつでもお呼びください。",
            "おやすみなさい。良い夢を。",
            "おやすみなさい。夜間も見守っております。",
            "おやすみなさい。お大事に。",
            "おやすみなさい。安心してお休みください。",
            "おやすみなさい。あとは私にお任せください。",
        ],
    },
}
# Japanese has no distinct "good afternoon" greeting in common use — こんにちは
# covers general daytime, so we fall back to the morning set for that slot.
GREETING_TEMPLATES["ja"]["afternoon"] = GREETING_TEMPLATES["ja"]["morning"]
GREETING_TEMPLATES["es"]["evening"] = GREETING_TEMPLATES["es"]["afternoon"]

# Optional flavor line appended after a greeting, describing market conditions
# by time of day. Crypto trades 24/7 — unlike the traditional stock-market
# phrasing this was drafted from, nothing here says markets are "closed" or
# "reopen tomorrow"; the quiet_hours bucket describes lower volume, not a close.
MARKET_CONTEXT_APPEND_CHANCE = 0.35  # shown sometimes, not every greeting -- keeps it from feeling scripted

def _get_market_context_bucket() -> str:
    hour = datetime.now(IST).hour
    if 5 <= hour < 12:
        return "opening"
    elif 12 <= hour < 17:
        return "active"
    elif 17 <= hour < 24:
        return "evening"
    else:
        return "quiet_hours"

MARKET_CONTEXT = {
    "en": {
        "opening": [
            "Markets are just waking up for the day, sir.",
            "Fresh session starting, sir — let's see how today shapes up.",
            "Trading's picking up for the day, sir.",
            "Sir, early movement showing in the markets.",
            "Markets are gearing up, sir.",
            "Sir, the day's trading is just getting started.",
            "Fresh candles forming, sir — early signals coming in.",
            "Sir, volumes are building as the day starts.",
            "Markets are stirring, sir — let's keep an eye on it.",
            "Sir, today's session is underway.",
        ],
        "active": [
            "Markets are active right now, sir.",
            "Trading volumes are decent today, sir.",
            "Sir, things are moving steadily.",
            "Sir, no major swings yet — markets are calm.",
            "Trading's in full swing, sir.",
            "Sir, market sentiment seems stable right now.",
            "Mid-day activity is normal, sir.",
            "Sir, the market's holding its pace.",
            "Steady movement across the board, sir.",
            "Sir, nothing unusual — markets ticking along.",
        ],
        "evening": [
            "Your day's winding down, sir — markets are still ticking along, as always.",
            "Sir, volumes tend to ease up around this time, but crypto never really stops.",
            "Sir, a quieter stretch usually kicks in about now.",
            "Sir, the pace tends to slow a touch in the evenings.",
            "Sir, markets are settling into a calmer rhythm.",
            "Evening lull setting in, sir — still worth keeping an eye on.",
            "Sir, activity's a bit lighter this time of day.",
            "Sir, things are calming down, though crypto's always live.",
            "Sir, a good time to review today before it gets quieter.",
            "Sir, the evening drift is starting — markets stay open though.",
        ],
        "quiet_hours": [
            "Quiet hours right now, sir — crypto never fully sleeps, just slows down.",
            "Sir, volumes are thin at this hour, but the markets are still live.",
            "Sir, it's the low-volume stretch — still worth a glance if something matters.",
            "Sir, things are unusually quiet, though trading never really stops.",
            "Sir, overnight volumes are light, but I'm still watching.",
            "Sir, this is the quietest window of the day — nothing urgent showing.",
            "Sir, markets are ticking along at a slower pace right now.",
            "Sir, it's calm out there — I'll flag anything that changes.",
            "Sir, low activity at this hour, but I'm keeping watch regardless.",
            "Sir, the quiet hours are usually a good time to just let things run.",
        ],
    },
    "hi-en": {
        "opening": [
            "Markets abhi open hue hain, sir — action shuru hone wala hai.",
            "Sir, naya session start ho raha hai, aaj dekhte hain kya hota hai.",
            "Trading pick up ho rahi hai, sir.",
            "Sir, early movement dikh raha hai market mein.",
            "Markets gear up ho rahe hain, sir.",
            "Sir, aaj ka trading abhi shuru hua hai.",
            "Fresh candles ban rahe hain, sir — early signals aa rahe hain.",
            "Sir, volumes build ho rahe hain din shuru hote hi.",
            "Markets stir ho rahe hain, sir — nazar rakhte hain.",
            "Sir, aaj ka session shuru ho chuka hai.",
        ],
        "active": [
            "Market mein thoda movement chal raha hai abhi, sir.",
            "Sir, trading volumes aaj decent hain.",
            "Sir, sab steady chal raha hai.",
            "Sir, koi bada swing nahi abhi — market calm hai.",
            "Trading full swing mein hai, sir.",
            "Sir, market sentiment stable lag raha hai abhi.",
            "Mid-day activity normal hai, sir.",
            "Sir, market apni pace pe hai.",
            "Sab kuch steady chal raha hai, sir.",
            "Sir, kuch unusual nahi — market normal chal raha hai.",
        ],
        "evening": [
            "Sir, aapka din wind down ho raha hai — market to hamesha ki tarah chal raha hai.",
            "Sir, volumes is time thode kam ho jaate hain, par crypto kabhi rukta nahi.",
            "Sir, is time thoda quiet phase shuru ho jata hai usually.",
            "Sir, evening mein pace thodi slow ho jati hai.",
            "Sir, market ek calm rhythm mein settle ho raha hai.",
            "Evening lull shuru ho raha hai, sir — phir bhi nazar rakhna theek hai.",
            "Sir, is time activity thodi light hai.",
            "Sir, sab calm ho raha hai, par crypto hamesha live rehta hai.",
            "Sir, ye accha time hai aaj ka review karne ka, quiet hone se pehle.",
            "Sir, evening drift shuru ho rahi hai — market phir bhi open rehta hai.",
        ],
        "quiet_hours": [
            "Sir, abhi quiet hours hain — crypto kabhi pura sota nahi, bas slow ho jata hai.",
            "Sir, is time volumes thin hain, par market live hai abhi bhi.",
            "Sir, ye low-volume stretch hai — kuch zaroori ho to bata dena.",
            "Sir, sab kuch unusually quiet hai, par trading kabhi rukta nahi.",
            "Sir, overnight volumes light hain, par main dekh raha hoon.",
            "Sir, ye din ka sabse quiet window hai — kuch urgent nahi dikh raha.",
            "Sir, market slow pace pe chal raha hai abhi.",
            "Sir, sab kuch calm hai — kuch change hua to bata dunga.",
            "Sir, is time activity kam hai, par main phir bhi dekh raha hoon.",
            "Sir, quiet hours usually accha time hote hain bas cheezein chalne dene ka.",
        ],
    },
    "hi": {
        "opening": [
            "सर, बाज़ार अभी खुले हैं — आज की शुरुआत हो रही है।",
            "सर, नया सत्र शुरू हो रहा है, देखते हैं आज क्या होता है।",
            "सर, ट्रेडिंग शुरू हो रही है।",
            "सर, बाज़ार में शुरुआती हलचल दिख रही है।",
            "सर, बाज़ार तैयार हो रहे हैं।",
            "सर, आज का कारोबार अभी शुरू हुआ है।",
            "सर, शुरुआती संकेत आ रहे हैं।",
            "सर, दिन शुरू होते ही वॉल्यूम बढ़ रहा है।",
            "सर, बाज़ार सक्रिय हो रहे हैं — नज़र रखते हैं।",
            "सर, आज का सत्र शुरू हो चुका है।",
        ],
        "active": [
            "सर, बाज़ार अभी सक्रिय है।",
            "सर, आज ट्रेडिंग वॉल्यूम ठीक है।",
            "सर, सब कुछ स्थिर चल रहा है।",
            "सर, अभी कोई बड़ा उतार-चढ़ाव नहीं — बाज़ार शांत है।",
            "सर, ट्रेडिंग पूरे जोश में है।",
            "सर, बाज़ार का रुख स्थिर लग रहा है।",
            "सर, दोपहर की गतिविधि सामान्य है।",
            "सर, बाज़ार अपनी गति बनाए हुए है।",
            "सर, सब कुछ स्थिर चल रहा है।",
            "सर, कुछ असामान्य नहीं — बाज़ार सामान्य है।",
        ],
        "evening": [
            "सर, आपका दिन ढल रहा है — बाज़ार हमेशा की तरह चल रहा है।",
            "सर, इस समय वॉल्यूम थोड़ा कम हो जाता है, पर क्रिप्टो कभी रुकता नहीं।",
            "सर, इस समय आमतौर पर शांत दौर शुरू होता है।",
            "सर, शाम को गति थोड़ी धीमी हो जाती है।",
            "सर, बाज़ार एक शांत लय में बस रहा है।",
            "सर, शाम की शांति शुरू हो रही है — फिर भी नज़र रखना ठीक है।",
            "सर, इस समय गतिविधि थोड़ी हल्की है।",
            "सर, सब शांत हो रहा है, पर क्रिप्टो हमेशा जीवंत रहता है।",
            "सर, शांत होने से पहले आज की समीक्षा का अच्छा समय है।",
            "सर, शाम की सुस्ती शुरू हो रही है — बाज़ार फिर भी खुला रहता है।",
        ],
        "quiet_hours": [
            "सर, अभी शांत घड़ी है — क्रिप्टो कभी पूरी तरह सोता नहीं, बस धीमा हो जाता है।",
            "सर, इस समय वॉल्यूम कम है, पर बाज़ार अभी भी जीवंत है।",
            "सर, यह कम-वॉल्यूम वाला दौर है — कुछ ज़रूरी हो तो बताइए।",
            "सर, सब कुछ असामान्य रूप से शांत है, पर ट्रेडिंग कभी रुकती नहीं।",
            "सर, रात भर का वॉल्यूम हल्का है, पर मैं नज़र रखे हुए हूं।",
            "सर, यह दिन का सबसे शांत समय है — कुछ ज़रूरी नहीं दिख रहा।",
            "सर, बाज़ार धीमी गति से चल रहा है अभी।",
            "सर, सब शांत है — कुछ बदला तो बता दूंगा।",
            "सर, इस समय गतिविधि कम है, पर मैं फिर भी नज़र रखे हूं।",
            "सर, शांत घड़ियां आमतौर पर चीज़ों को चलने देने का अच्छा समय होती हैं।",
        ],
    },
    "es": {
        "opening": [
            "Los mercados se están despertando, señor.",
            "Nueva sesión comenzando, señor — veamos cómo va el día.",
            "El trading está tomando impulso, señor.",
            "Señor, se ve movimiento temprano en los mercados.",
            "Los mercados se están preparando, señor.",
            "Señor, la sesión del día apenas comienza.",
            "Señor, primeras señales llegando.",
            "Señor, los volúmenes están creciendo con el inicio del día.",
            "Los mercados se están activando, señor — vigilemos.",
            "Señor, la sesión de hoy está en marcha.",
        ],
        "active": [
            "Los mercados están activos ahora, señor.",
            "Los volúmenes de hoy son decentes, señor.",
            "Señor, las cosas se mueven con constancia.",
            "Señor, sin grandes movimientos aún — los mercados están tranquilos.",
            "El trading está en pleno apogeo, señor.",
            "Señor, el sentimiento del mercado parece estable ahora.",
            "La actividad de mediodía es normal, señor.",
            "Señor, el mercado mantiene su ritmo.",
            "Movimiento constante en general, señor.",
            "Señor, nada inusual — los mercados siguen su curso.",
        ],
        "evening": [
            "Su día está terminando, señor — los mercados siguen su curso, como siempre.",
            "Señor, los volúmenes suelen bajar a esta hora, pero el cripto nunca se detiene.",
            "Señor, suele empezar un momento más tranquilo por ahora.",
            "Señor, el ritmo suele bajar un poco por las tardes.",
            "Señor, los mercados se están asentando en un ritmo más calmado.",
            "Empieza la calma vespertina, señor — aun así vale la pena vigilar.",
            "Señor, la actividad es un poco más ligera a esta hora.",
            "Señor, las cosas se calman, aunque el cripto siempre está activo.",
            "Señor, buen momento para revisar el día antes de que se calme más.",
            "Señor, empieza la calma nocturna — los mercados siguen abiertos igual.",
        ],
        "quiet_hours": [
            "Horas tranquilas ahora, señor — el cripto nunca duerme del todo, solo se ralentiza.",
            "Señor, los volúmenes son bajos a esta hora, pero los mercados siguen activos.",
            "Señor, es el tramo de bajo volumen — avíseme si algo importa.",
            "Señor, todo está inusualmente tranquilo, aunque el trading nunca se detiene.",
            "Señor, los volúmenes nocturnos son ligeros, pero sigo vigilando.",
            "Señor, esta es la ventana más tranquila del día — nada urgente por ahora.",
            "Señor, los mercados avanzan a un ritmo más lento ahora.",
            "Señor, todo está en calma — le avisaré de cualquier cambio.",
            "Señor, poca actividad a esta hora, pero sigo atento igualmente.",
            "Señor, las horas tranquilas suelen ser un buen momento para dejar que las cosas fluyan.",
        ],
    },
    "fr": {
        "opening": [
            "Les marchés se réveillent tout juste, monsieur.",
            "Nouvelle séance qui commence, monsieur — voyons comment se déroule la journée.",
            "Le trading prend de l'ampleur, monsieur.",
            "Monsieur, on voit un mouvement matinal sur les marchés.",
            "Les marchés se préparent, monsieur.",
            "Monsieur, la séance du jour vient de commencer.",
            "Monsieur, les premiers signaux arrivent.",
            "Monsieur, les volumes montent en ce début de journée.",
            "Les marchés s'activent, monsieur — restons attentifs.",
            "Monsieur, la séance du jour est en cours.",
        ],
        "active": [
            "Les marchés sont actifs en ce moment, monsieur.",
            "Les volumes du jour sont corrects, monsieur.",
            "Monsieur, les choses bougent régulièrement.",
            "Monsieur, pas de grands mouvements encore — les marchés sont calmes.",
            "Le trading bat son plein, monsieur.",
            "Monsieur, le sentiment du marché semble stable en ce moment.",
            "L'activité de milieu de journée est normale, monsieur.",
            "Monsieur, le marché garde son rythme.",
            "Mouvement régulier dans l'ensemble, monsieur.",
            "Monsieur, rien d'inhabituel — les marchés suivent leur cours.",
        ],
        "evening": [
            "Votre journée touche à sa fin, monsieur — les marchés continuent, comme toujours.",
            "Monsieur, les volumes ont tendance à baisser à cette heure, mais la crypto ne s'arrête jamais vraiment.",
            "Monsieur, une période plus calme commence généralement maintenant.",
            "Monsieur, le rythme ralentit un peu le soir.",
            "Monsieur, les marchés s'installent dans un rythme plus calme.",
            "Le calme du soir s'installe, monsieur — ça vaut quand même la peine de surveiller.",
            "Monsieur, l'activité est un peu plus légère à cette heure.",
            "Monsieur, les choses se calment, même si la crypto reste toujours active.",
            "Monsieur, bon moment pour faire le point avant que ça se calme davantage.",
            "Monsieur, la dérive du soir commence — les marchés restent ouverts quand même.",
        ],
        "quiet_hours": [
            "Heures calmes en ce moment, monsieur — la crypto ne dort jamais complètement, elle ralentit juste.",
            "Monsieur, les volumes sont faibles à cette heure, mais les marchés restent actifs.",
            "Monsieur, c'est la période de faible volume — prévenez-moi si quelque chose compte.",
            "Monsieur, tout est étrangement calme, mais le trading ne s'arrête jamais vraiment.",
            "Monsieur, les volumes nocturnes sont légers, mais je surveille toujours.",
            "Monsieur, c'est la fenêtre la plus calme de la journée — rien d'urgent pour l'instant.",
            "Monsieur, les marchés avancent à un rythme plus lent en ce moment.",
            "Monsieur, tout est calme — je vous signalerai tout changement.",
            "Monsieur, peu d'activité à cette heure, mais je reste attentif quand même.",
            "Monsieur, les heures calmes sont généralement un bon moment pour laisser les choses suivre leur cours.",
        ],
    },
    "de": {
        "opening": [
            "Die Märkte wachen gerade erst auf, mein Herr.",
            "Neue Sitzung beginnt, mein Herr — mal sehen, wie sich der Tag entwickelt.",
            "Der Handel nimmt Fahrt auf, mein Herr.",
            "Mein Herr, es zeigt sich frühe Bewegung an den Märkten.",
            "Die Märkte machen sich bereit, mein Herr.",
            "Mein Herr, die heutige Sitzung fängt gerade erst an.",
            "Mein Herr, frühe Signale kommen herein.",
            "Mein Herr, die Volumina steigen zu Tagesbeginn.",
            "Die Märkte regen sich, mein Herr — bleiben wir aufmerksam.",
            "Mein Herr, die heutige Sitzung läuft bereits.",
        ],
        "active": [
            "Die Märkte sind gerade aktiv, mein Herr.",
            "Die heutigen Handelsvolumina sind ordentlich, mein Herr.",
            "Mein Herr, die Dinge bewegen sich stetig.",
            "Mein Herr, noch keine großen Ausschläge — die Märkte sind ruhig.",
            "Der Handel läuft auf Hochtouren, mein Herr.",
            "Mein Herr, die Marktstimmung wirkt gerade stabil.",
            "Die Aktivität zur Mittagszeit ist normal, mein Herr.",
            "Mein Herr, der Markt hält sein Tempo.",
            "Insgesamt stetige Bewegung, mein Herr.",
            "Mein Herr, nichts Ungewöhnliches — die Märkte laufen normal weiter.",
        ],
        "evening": [
            "Ihr Tag klingt aus, mein Herr — die Märkte laufen wie immer weiter.",
            "Mein Herr, die Volumina lassen um diese Zeit meist nach, aber Krypto stoppt nie wirklich.",
            "Mein Herr, um diese Zeit beginnt meist eine ruhigere Phase.",
            "Mein Herr, das Tempo verlangsamt sich abends etwas.",
            "Mein Herr, die Märkte finden zu einem ruhigeren Rhythmus.",
            "Die abendliche Ruhe setzt ein, mein Herr — trotzdem lohnt sich ein Blick.",
            "Mein Herr, die Aktivität ist zu dieser Zeit etwas geringer.",
            "Mein Herr, es beruhigt sich, obwohl Krypto immer aktiv bleibt.",
            "Mein Herr, guter Zeitpunkt, den Tag zu überprüfen, bevor es ruhiger wird.",
            "Mein Herr, die abendliche Flaute beginnt — die Märkte bleiben trotzdem offen.",
        ],
        "quiet_hours": [
            "Ruhige Stunden gerade, mein Herr — Krypto schläft nie ganz, wird nur langsamer.",
            "Mein Herr, die Volumina sind zu dieser Stunde dünn, aber die Märkte sind weiterhin aktiv.",
            "Mein Herr, das ist die Phase mit geringem Volumen — sagen Sie Bescheid, falls etwas wichtig ist.",
            "Mein Herr, alles ist ungewöhnlich ruhig, aber der Handel stoppt nie wirklich.",
            "Mein Herr, die nächtlichen Volumina sind gering, aber ich behalte alles im Blick.",
            "Mein Herr, das ist das ruhigste Fenster des Tages — nichts Dringendes in Sicht.",
            "Mein Herr, die Märkte laufen gerade in einem langsameren Tempo.",
            "Mein Herr, es ist ruhig da draußen — ich melde jede Änderung.",
            "Mein Herr, wenig Aktivität zu dieser Stunde, aber ich behalte trotzdem alles im Blick.",
            "Mein Herr, die ruhigen Stunden sind meist ein guter Zeitpunkt, die Dinge einfach laufen zu lassen.",
        ],
    },
    "ja": {
        "opening": [
            "市場はちょうど動き始めたところです。",
            "新しいセッションが始まります、今日はどうなるか見てみましょう。",
            "取引が勢いづいてきています。",
            "市場に早い動きが見られます。",
            "市場が準備を整えています。",
            "本日のセッションが始まったばかりです。",
            "早い段階のシグナルが入ってきています。",
            "一日の始まりとともに出来高が増えています。",
            "市場が動き出しています、注視しましょう。",
            "本日のセッションが進行中です。",
        ],
        "active": [
            "市場は今活発です。",
            "本日の出来高はまずまずです。",
            "着実に動いています。",
            "大きな変動はまだありません、市場は落ち着いています。",
            "取引が最も活発な時間帯です。",
            "市場心理は今のところ安定しているようです。",
            "昼間の活動は通常通りです。",
            "市場はペースを保っています。",
            "全体的に安定した動きです。",
            "特に異常なし、市場は通常通り推移しています。",
        ],
        "evening": [
            "一日が終わりに近づいていますが、市場はいつも通り動いています。",
            "この時間帯は出来高が落ち着く傾向がありますが、暗号資産は完全には止まりません。",
            "この時間はいつも少し静かな時間帯になります。",
            "夕方はペースが少し落ちる傾向があります。",
            "市場は落ち着いたリズムに入りつつあります。",
            "夕方の落ち着きが始まっています、それでも見ておく価値はあります。",
            "この時間は活動がやや軽めです。",
            "落ち着いてきていますが、暗号資産は常に動いています。",
            "静かになる前に、今日を振り返る良い時間です。",
            "夕方の緩やかな流れが始まっています、市場は開いたままです。",
        ],
        "quiet_hours": [
            "今は静かな時間帯です、暗号資産は完全には眠らず、ただ緩やかになるだけです。",
            "この時間は出来高が少ないですが、市場はまだ動いています。",
            "出来高の少ない時間帯です、何か重要なことがあればお知らせください。",
            "普段より静かですが、取引が完全に止まることはありません。",
            "夜間の出来高は少ないですが、引き続き見守っています。",
            "一日で最も静かな時間帯です、緊急なものは見当たりません。",
            "市場は今、ゆっくりとしたペースで動いています。",
            "落ち着いています、変化があればお知らせします。",
            "この時間は活動が少ないですが、引き続き見守っています。",
            "静かな時間帯は物事をそのまま進ませるのに良い時間です。",
        ],
    },
}

CLASSIFICATION_PROMPT = """You are a crypto trading assistant. Analyze the user message and classify intent.

Messages may be written in English, Hindi (Devanagari or romanized/Hinglish), Spanish,
French, German, or Japanese. Classify by meaning regardless of language.

Return ONLY a JSON object. No explanation. No markdown. Just raw JSON.

Format:
{"intent": "buy|sell|price|portfolio|advice|alert|stop_loss|take_profit|greeting|unknown", "asset": "BTC|ETH|SOL|null", "amount": number|null, "price": number|null, "confidence": 0.0-1.0}

Examples:
"Buy 100 ETH" → {"intent": "buy", "asset": "ETH", "amount": 100, "price": null, "confidence": 0.95}
"What's BTC price?" → {"intent": "price", "asset": "BTC", "amount": null, "price": null, "confidence": 0.95}
"Hi there" → {"intent": "greeting", "asset": null, "amount": null, "price": null, "confidence": 0.95}
"What is the best time to buy Bitcoin?" → {"intent": "advice", "asset": "BTC", "amount": null, "price": null, "confidence": 0.92}
"Should I invest in Ethereum now?" → {"intent": "advice", "asset": "ETH", "amount": null, "price": null, "confidence": 0.93}
"Alert me when BTC hits 100k" → {"intent": "alert", "asset": "BTC", "amount": null, "price": 100000, "confidence": 0.95}
"Notify me when ETH drops" → {"intent": "alert", "asset": "ETH", "amount": null, "price": null, "confidence": 0.9}
"Stop loss at 40k" → {"intent": "stop_loss", "asset": "BTC", "amount": null, "price": 40000, "confidence": 0.9}
"Set take profit for ETH at 3000" → {"intent": "take_profit", "asset": "ETH", "amount": null, "price": 3000, "confidence": 0.93}
"BTC becho" → {"intent": "sell", "asset": "BTC", "amount": null, "price": null, "confidence": 0.9}
"ETH kharido" → {"intent": "buy", "asset": "ETH", "amount": null, "price": null, "confidence": 0.9}
"Kitna paisa hai" → {"intent": "portfolio", "asset": null, "amount": null, "price": null, "confidence": 0.9}
"Mera portfolio dikhao" → {"intent": "portfolio", "asset": null, "amount": null, "price": null, "confidence": 0.92}
"BTC ka rate kya hai" → {"intent": "price", "asset": "BTC", "amount": null, "price": null, "confidence": 0.9}

Now classify this message:"""


class IntentClassifier:
    """
    Hybrid classifier:
    1. Fast regex pre-filter for obvious cases (greetings, etc.)
    2. LLM classification for everything else
    """
    
    def __init__(self):
        self.use_llm = True
    
    def _detect_language(self, message: str) -> Dict[str, Any]:
        """Detect language with confidence score. `is_default` is True only
        when nothing matched and we fell through to English -- a truly
        ambiguous message, as opposed to a message we're confident is English."""

        # Simple language detection based on character patterns
        import re

        # Check for Hindi characters
        if re.search(r'[\u0900-\u097F]', message):
            return {"language": "hi", "confidence": 0.95, "english": False, "is_default": False}

        # Check for Hinglish (English + Hindi mixed)
        if re.search(r'\b(hai|kya|kaise|kyu|nahi|acha|bhai|sir|ji|namaste|namaskar)\b', message.lower()):
            return {"language": "hi-en", "confidence": 0.90, "english": False, "is_default": False}

        # Check for Japanese
        if re.search(r'[\u3040-\u309F\u30A0-\u30FF]', message):
            return {"language": "ja", "confidence": 0.95, "english": False, "is_default": False}

        # Check for Spanish
        if re.search(r'\b(hola|como|estas|buenos|buenas|d[ií]as|tardes|noches|gracias)\b', message.lower()):
            return {"language": "es", "confidence": 0.85, "english": False, "is_default": False}

        # Check for French
        if re.search(r'\b(bonjour|bonsoir|bonne|nuit|salut|comment|ca va|merci)\b', message.lower()):
            return {"language": "fr", "confidence": 0.85, "english": False, "is_default": False}

        # Check for German
        if re.search(r'\b(hallo|guten|tag|abend|nacht|morgen|danke|wie|geht)\b', message.lower()):
            return {"language": "de", "confidence": 0.85, "english": False, "is_default": False}

        # Check for confidently-English words (so real English outranks a blind default)
        if re.search(r'\b(hi|hello|hey|good morning|good afternoon|good evening|good night|thanks|thank you|please)\b', message.lower()):
            return {"language": "en", "confidence": 0.9, "english": True, "is_default": False}
        
        # Default: English (no real signal found -- caller may consult
        # the user's known-language profile instead of trusting this blindly).
        # Confidence stays 0.95 so routing for non-greeting intents is unchanged;
        # `is_default` is the separate signal the greeting path acts on.
        return {"language": "en", "confidence": 0.95, "english": True, "is_default": True}
    
    async def _classify_with_llm(self, message: str) -> Dict[str, Any]:
        """Use LLM for intent classification"""
        
        from .simple_router import simple_chat
        from .response_cleaner import clean_response
        
        prompt = f"{CLASSIFICATION_PROMPT}\n'{message}'"
        
        try:
            # Call LLM via Groq (GitHub Models was retired July 30, 2026)
            print(f"🔍 [DEBUG] Calling Groq for: {message}")
            from .groq_client import call_llm
            raw_response = await call_llm(prompt)
            print(f"🔍 [DEBUG] Raw Groq response: {raw_response[:200]}")
            response_text = clean_response(raw_response)
            print(f"🔍 [DEBUG] Cleaned response: {response_text[:200]}")
            
            # Extract JSON from response
            cleaned = self._extract_json(response_text)
            print(f"🔍 [DEBUG] Extracted JSON: {cleaned[:200]}")
            
            # Parse JSON
            parsed = json.loads(cleaned)
            print(f"🔍 [DEBUG] Parsed JSON: {parsed}")
            
            # Validate required fields - use defaults if missing
            required_defaults = {
                "intent": "unknown",
                "asset": None,
                "amount": None,
                "amount_type": None,
                "price": None,
                "confidence": 0.5,
                "needs_clarification": False,
                "clarification_question": None
            }
            
            for field, default in required_defaults.items():
                if field not in parsed:
                    parsed[field] = default
            
            # Add message field if missing
            if "message" not in parsed:
                lang_result = self._detect_language(message)
                parsed["message"] = self._get_fast_response(parsed.get("intent", "unknown"), lang_result["language"])
            
            return parsed
            
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON parse error: {e}")
            print(f"Raw response: {response_text[:200]}")
            return self._fallback_response(message)
        except Exception as e:
            print(f"⚠️ LLM classification error: {e}")
            return self._fallback_response(message)
    
    def _extract_json(self, text: str) -> str:
        """Extract JSON from LLM response"""
        
        # Remove markdown code blocks
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        
        # Remove TUI artifacts
        text = re.sub(r'⚕.*?\n', '', text)
        text = re.sub(r'─.*?\n', '', text)
        text = re.sub(r'╭.*?\n', '', text)
        text = re.sub(r'╰.*?\n', '', text)
        text = re.sub(r'│.*?\n', '', text)
        text = re.sub(r'❯.*?\n', '', text)
        text = re.sub(r'⏲.*?\n', '', text)
        text = re.sub(r'⏱.*?\n', '', text)
        text = re.sub(r'●.*?\n', '', text)
        text = re.sub(r'\(⌐■_■\).*?\n', '', text)
        text = re.sub(r'ಠ_ಠ.*?\n', '', text)
        
        # Find JSON with intent field (most reliable pattern)
        match = re.search(r'\{[^{}]*"intent"[^{}]*\}', text, re.DOTALL)
        if match:
            return self._repair_json(match.group(0))

        # Fallback: find any JSON object
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return self._repair_json(match.group(0))

        return text.strip()

    def _repair_json(self, text: str) -> str:
        """Fix a common LLM quirk seen from Groq's gpt-oss models: a stray
        quote right after a numeric/null/bool value, e.g. '"confidence":0.95"}'
        instead of '"confidence":0.95}'. json.loads would reject that as-is."""
        return re.sub(r'(-?\d+\.?\d*|null|true|false)"(\s*[,}])', r'\1\2', text)

    async def classify(self, message: str, user_id: str = "anonymous", portfolio_value: Optional[float] = None, portfolio_change_pct: Optional[float] = None) -> Dict[str, Any]:
        """Hybrid intent classification"""

        # Normalize message
        normalized_msg = unicodedata.normalize('NFKC', message)
        normalized_msg_lower = normalized_msg.casefold()

        async def _fast_greeting_result():
            response_data = await self.generate_response("greeting", message, user_id, portfolio_value, portfolio_change_pct)
            return {
                "intent": "greeting",
                "asset": None,
                "amount": None,
                "amount_type": None,
                "price": None,
                "confidence": 0.99,
                "needs_clarification": False,
                "clarification_question": None,
                "message": response_data["message"],
                "source": response_data["source"],
                "language": response_data["language"],
                "language_confidence": response_data["language_confidence"],
                "latency_ms": response_data["latency_ms"]
            }

        # Bare "Jarvix" (just the name, nothing else) is a wake-word-style
        # greeting -- like "Hey Siri". But "Jarvix, buy 100 ETH" must NOT be
        # swallowed as a greeting, so this only matches when nothing real
        # follows the name (just trailing punctuation/whitespace allowed).
        if re.match(r'^jarvix[\s!.,?]*$', normalized_msg_lower):
            return await _fast_greeting_result()

        # 1. Fast pattern matching (regex)
        for intent, pattern in FAST_PATTERNS.items():
            if re.search(pattern, normalized_msg_lower, re.IGNORECASE):
                if intent.value == "greeting":
                    return await _fast_greeting_result()
                # Generate response using hybrid system
                response_data = await self.generate_response(intent.value, message, user_id, portfolio_value, portfolio_change_pct)
                return {
                    "intent": intent.value,
                    "asset": None,
                    "amount": None,
                    "amount_type": None,
                    "price": None,
                    "confidence": 0.99,
                    "needs_clarification": False,
                    "clarification_question": None,
                    "message": response_data["message"],
                    "source": response_data["source"],
                    "language": response_data["language"],
                    "language_confidence": response_data["language_confidence"],
                    "latency_ms": response_data["latency_ms"]
                }

        # 2. LLM fallback for complex queries
        print(f"🔍 [DEBUG] use_llm={self.use_llm}, checking LLM fallback...")
        if self.use_llm:
            print(f"🔍 [DEBUG] Calling _classify_with_llm for: {message}")
            result = await self._classify_with_llm(message)
            print(f"🔍 [DEBUG] LLM result: {result}")
            # Detect language and generate response
            lang_result = self._detect_language(message)
            result["detected_language"] = lang_result["language"]
            result["language_confidence"] = lang_result["confidence"]
            result["is_english"] = lang_result["english"]
            # Ensure message field present. Greeting ALWAYS goes through our own
            # template logic (time-mismatch correction, portfolio tone, etc.) --
            # the classification LLM sometimes hallucinates its own "message"
            # field despite the prompt never asking for one, which would
            # otherwise silently bypass all of that.
            if result.get("intent") == "greeting" or "message" not in result or not result["message"]:
                result["message"] = self._get_fast_response(result.get("intent", "unknown"), lang_result["language"], message, user_id, portfolio_value, portfolio_change_pct)
            return result

        # 3. Fallback
        return self._fallback_response(message)

    async def generate_response(self, intent: str, message: str, user_id: str = None, portfolio_value: Optional[float] = None, portfolio_change_pct: Optional[float] = None) -> Dict[str, Any]:
        """Hybrid response generation - Fast path + LLM fallback"""

        uid = user_id or "anonymous"

        # 1. Language detection with confidence
        lang_result = self._detect_language(message)
        detected_lang = lang_result["language"]
        confidence = lang_result["confidence"]

        # 1b. For greetings specifically: if this message gave no real language
        # signal (e.g. an emoji, a bare "ok"), fall back to a language we already
        # know this user is comfortable in — rather than defaulting to English —
        # before trusting the current message's own language when it IS a real signal.
        # Weighted (not always the single top language) so a bilingual user's
        # profile stays reflected over time rather than locking onto just #1.
        profile = get_language_profile_system()
        neutral_message = is_language_neutral_message(message)
        if intent == "greeting" and lang_result.get("is_default") and not neutral_message:
            profile.apply_decay(uid)
            known_lang = profile.get_weighted_language_choice(uid)
            if known_lang:
                detected_lang = known_lang

        # Language-neutral messages ("ok", "lol", a bare emoji) carry no real
        # signal either way -- skip updating the profile so they don't add noise.
        if intent == "greeting" and not neutral_message:
            word_count = len((message or "").split())
            profile.update_language(uid, detected_lang, message_length=word_count)
            profile.record_response_language(uid, detected_lang)

        # 2. Confidence check - High confidence (>0.8) -> Fast path
        if confidence > 0.8:
            fast_response = self._get_fast_response(intent, detected_lang, message, uid, portfolio_value, portfolio_change_pct)
            return {
                "intent": intent,
                "message": fast_response,
                "source": "fast_path",
                "language": detected_lang,
                "language_confidence": confidence,
                "latency_ms": 1
            }

        # 3. Low confidence (<0.8) -> LLM fallback
        try:
            llm_response = await self._llm_generate_response(intent, message, detected_lang, user_id)
            return {
                "intent": intent,
                "message": llm_response,
                "source": "llm_fallback",
                "language": detected_lang,
                "language_confidence": confidence,
                "latency_ms": 500
            }
        except Exception as e:
            print(f"⚠️ LLM fallback failed: {e}")
            # Fallback to fast path if LLM fails
            fast_response = self._get_fast_response(intent, detected_lang, message, uid, portfolio_value, portfolio_change_pct)
            return {
                "intent": intent,
                "message": fast_response,
                "source": "fast_path_fallback",
                "language": detected_lang,
                "language_confidence": confidence,
                "latency_ms": 2
            }
    
    def _get_greeting_response(self, message: str, language: str, user_id: str = "anonymous", portfolio_value: Optional[float] = None, portfolio_change_pct: Optional[float] = None) -> str:
        """Time-aware greeting. The user's own words always win over the clock —
        Jarvix never assumes 'good night' from time alone (backlog #1) — but if
        they claim a category that flatly contradicts the real clock (e.g. "good
        morning" at 9pm), Jarvix gently, playfully corrects them for two tries
        before accepting it on the third (see _check_greeting_mismatch)."""
        if _is_wellbeing_check(message, language):
            tier = _portfolio_status_tier(portfolio_change_pct) if portfolio_change_pct is not None else "flat"
            pool = WELLBEING_RESPONSE.get(language, WELLBEING_RESPONSE["en"])[tier]
            value_str = f"${portfolio_value:,.0f}" if portfolio_value is not None else "—"
            return random.choice(pool).format(value=value_str)

        explicit_category = _detect_explicit_greeting_category(message, language)
        if explicit_category:
            correction = _check_greeting_mismatch(explicit_category, user_id, language)
            if correction is not None:
                return correction

        now = time.time()
        last_greet_time = _last_greeting_time.get(user_id)
        # Only a GENERIC repeat ("hi" spam) gets the short "yes sir?" reply --
        # an explicit category ("good night" again) is meaningful content each
        # time and always gets the full contextual response, never the short one.
        is_repeat_greeting = (
            explicit_category is None
            and last_greet_time is not None
            and (now - last_greet_time) < REPEAT_GREETING_WINDOW_SECONDS
        )
        _last_greeting_time[user_id] = now

        if is_repeat_greeting:
            repeat_options = REPEAT_GREETING_TEMPLATES.get(language, REPEAT_GREETING_TEMPLATES["en"])
            key = (user_id, language, "repeat")
            last_shown = _last_greeting_shown.get(key)
            pool = [o for o in repeat_options if o != last_shown] or repeat_options
            choice = random.choice(pool)
            _last_greeting_shown[key] = choice
            return choice

        category = explicit_category or _get_ist_time_bucket()
        lang_templates = GREETING_TEMPLATES.get(language, GREETING_TEMPLATES["en"])
        options = lang_templates.get(category, lang_templates["morning"])

        key = (user_id, language, category)
        last_shown = _last_greeting_shown.get(key)
        pool = [o for o in options if o != last_shown] or options
        choice = random.choice(pool)
        _last_greeting_shown[key] = choice

        if portfolio_value is not None:
            suffix = PORTFOLIO_SUFFIX.get(language, PORTFOLIO_SUFFIX["en"])
            choice = choice + suffix.format(value=f"${portfolio_value:,.0f}")

            if portfolio_change_pct is not None:
                tier = _portfolio_status_tier(portfolio_change_pct)
                remark_options = PORTFOLIO_STATUS_REMARK.get(language, PORTFOLIO_STATUS_REMARK["en"])[tier]
                choice = choice + random.choice(remark_options)

        if random.random() < MARKET_CONTEXT_APPEND_CHANCE:
            market_bucket = _get_market_context_bucket()
            market_options = MARKET_CONTEXT.get(language, MARKET_CONTEXT["en"]).get(market_bucket, MARKET_CONTEXT["en"][market_bucket])
            choice = choice + " " + random.choice(market_options)

        return choice

    def _get_fast_response(self, intent: str, language: str, message: str = "", user_id: str = "anonymous", portfolio_value: Optional[float] = None, portfolio_change_pct: Optional[float] = None) -> str:
        """Get hardcoded response for fast path"""

        if intent == "greeting":
            return self._get_greeting_response(message, language, user_id, portfolio_value, portfolio_change_pct)

        # Multi-language responses
        responses = {
            "buy": {
                "en": "Processing your buy request...",
                "hi": "खरीदारी प्रोसेस हो रही है...",
                "hi-en": "Buy request process ho rahi hai...",
                "es": "Procesando tu orden de compra...",
                "fr": "Traitement de votre achat...",
                "de": "Verarbeite deinen Kauf...",
                "ja": "購入処理中..."
            },
            "sell": {
                "en": "Processing your sell request...",
                "hi": "बिक्री प्रोसेस हो रही है...",
                "hi-en": "Sell request process ho rahi hai...",
                "es": "Procesando tu orden de venta...",
                "fr": "Traitement de votre vente...",
                "de": "Verarbeite deinen Verkauf...",
                "ja": "売却処理中..."
            },
            "price": {
                "en": "Fetching live prices for you...",
                "hi": "लाइव प्राइस ला रहा हूँ...",
                "hi-en": "Live price la raha hoon...",
                "es": "Obteniendo precios en vivo...",
                "fr": "Récupération des prix en direct...",
                "de": "Hole aktuelle Preise...",
                "ja": "価格を取得中..."
            },
            "portfolio": {
                "en": "Sir, your portfolio is valued at $100,000, up 2.4%. You hold 100 ETH, 0.5 BTC, and 1000 SOL.",
                "hi": "सर, आपका पोर्टफोलियो $100,000 है, 2.4% बढ़ा। आपके पास 100 ETH, 0.5 BTC, और 1000 SOL हैं।",
                "hi-en": "Sir, aapka portfolio $100,000 hai, 2.4% up. Aapke paas 100 ETH, 0.5 BTC, aur 1000 SOL hain.",
                "es": "Señor, su cartera vale $100,000, sube 2.4%. Tiene 100 ETH, 0.5 BTC y 1000 SOL.",
                "fr": "Monsieur, votre portefeuille vaut $100,000, +2.4%. Vous détenez 100 ETH, 0.5 BTC et 1000 SOL.",
                "de": "Herr, Ihr Portfolio ist $100.000 wert, +2,4%. Sie halten 100 ETH, 0,5 BTC und 1000 SOL.",
                "ja": "ポートフォリオは$100,000、2.4%上昇。100 ETH、0.5 BTC、1000 SOLを保有。"
            },
            "advice": {
                "en": "Analyzing market conditions for your request...",
                "hi": "मार्केट एनालिसिस हो रहा है...",
                "hi-en": "Market analysis ho raha hai...",
                "es": "Analizando condiciones del mercado...",
                "fr": "Analyse des conditions du marché...",
                "de": "Marktbedingungen analysieren...",
                "ja": "市場分析中..."
            },
            "alert": {
                "en": "Setting up your alert...",
                "hi": "अलर्ट सेट हो रहा है...",
                "hi-en": "Alert set ho raha hai...",
                "es": "Configurando tu alerta...",
                "fr": "Configuration de votre alerte...",
                "de": "Richte deinen Alarm ein...",
                "ja": "アラート設定中..."
            },
            "stop_loss": {
                "en": "Configuring stop loss...",
                "hi": "स्टॉप लॉस कॉन्फिगर हो रहा है...",
                "hi-en": "Stop loss configure ho raha hai...",
                "es": "Configurando stop loss...",
                "fr": "Configuration du stop loss...",
                "de": "Konfiguriere Stop-Loss...",
                "ja": "損切り設定中..."
            },
            "take_profit": {
                "en": "Configuring take profit...",
                "hi": "टेक प्रॉफिट कॉन्फिगर हो रहा है...",
                "hi-en": "Take profit configure ho raha hai...",
                "es": "Configurando take profit...",
                "fr": "Configuration du take profit...",
                "de": "Konfiguriere Take-Profit...",
                "ja": "利確設定中..."
            }
        }
        
        # Get response for intent and language, fallback to English
        intent_responses = responses.get(intent, {})
        return intent_responses.get(language, intent_responses.get("en", "Processing complete, sir."))
    
    async def _llm_generate_response(self, intent: str, message: str, language: str, user_id: str = None) -> str:
        """Generate dynamic response using LLM"""
        
        from .simple_router import simple_chat
        
        # Build prompt for LLM
        lang_names = {
            "en": "English", "hi": "Hindi", "hi-en": "Hinglish",
            "es": "Spanish", "fr": "French", "de": "German", "ja": "Japanese"
        }
        
        lang_name = lang_names.get(language, "English")
        
        prompt = f"""You are a crypto trading assistant. Respond in {lang_name}.

User intent: {intent}
User message: {message}

Respond naturally in {lang_name} language. Keep it short and professional."""
        
        try:
            response = await simple_chat(prompt)
            return response.strip()
        except Exception as e:
            print(f"⚠️ LLM response generation failed: {e}")
            raise
    
    async def detect_intent_hybrid(self, message: str, context: Optional[Dict[str, Any]] = None, user_id: str = "anonymous", portfolio_value: Optional[float] = None, portfolio_change_pct: Optional[float] = None) -> Dict[str, Any]:
        """Hybrid intent detection - combines fast regex + LLM fallback"""
        return await self.classify(message, user_id, portfolio_value, portfolio_change_pct)
    
    def _fallback_response(self, message: str) -> Dict[str, Any]:
        """Fallback when LLM fails"""
        return {
            "intent": "unknown",
            "asset": None,
            "amount": None,
            "amount_type": None,
            "price": None,
            "confidence": 0.0,
            "needs_clarification": True,
            "clarification_question": "I'm not sure what you mean. Try: 'Buy 100 ETH' or 'What's my portfolio?'"
        }


# Test function
async def test_classifier():
    """Test intent classifier"""
    
    classifier = IntentClassifier()
    
    test_cases = [
        "Buy 100 ETH",
        "I want to get some ETH",
        "Can you grab me some SOL?",
        "Let's go heavy on Bitcoin",
        "ETH looks good, buy it",
        "What's my portfolio?",
        "Should I buy SOL now?",
        "Hi Jarvix",
        "Set stop-loss for BTC at $55k",
        "Sell half my ETH at $3000"
    ]
    
    print("🧪 Testing Intent Classifier (LLM-based)")
    print("=" * 60)
    
    for msg in test_cases:
        print(f"\n💬 '{msg}'")
        result = await classifier.classify(msg)
        
        print(f"   Intent: {result['intent']}")
        print(f"   Asset: {result['asset']}")
        print(f"   Amount: {result['amount']} {result['amount_type']}")
        print(f"   Confidence: {result['confidence']}")
        
        if result['needs_clarification']:
            print(f"   ❓ {result['clarification_question']}")
        else:
            print(f"   ✅ Ready to execute")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_classifier())
