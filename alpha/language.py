"""Language detection and correction for English, Roman Urdu and Urdu script.

Design note
-----------
Roman Urdu spellings frequently collide with real English words (``men``,
``main``, ``ap``, ``ye``).  Blindly applying a Roman Urdu correction map
therefore rewrites valid English sentences.  Corrections are consequently
split into two tables:

``RU_TYPO_CORRECTIONS``
    Sources that are *not* valid English words (``nhe``, ``thik``,
    ``shukria``).  These are safe to apply in any language mode.

``RU_ROMAN_ONLY_CORRECTIONS``
    Sources that are also common English words.  These are only applied when
    the text was actually detected as Roman Urdu.
"""
from __future__ import annotations

import re

WORD_RE = re.compile(r"[a-zA-Z\u0600-\u06ff']+")

URDU_CHARS = set("ابپتٹثجچحخدڈذرزژسشصضطظعغفقکگلمنہوےؤئى")

RU_TYPO_CORRECTIONS = {
    "mei": "mein",
    "nhe": "nahi",
    "nai": "nahi",
    "nhi": "nahi",
    "krna": "karna",
    "bhot": "bohat",
    "zyda": "zyada",
    "ghr": "ghar",
    "skool": "school",
    "shukria": "Shukriya",
    "thik": "Theek",
    "theek": "Theek",
    "achha": "Achha",
    "acha": "Achha",
    "kuch": "Kuch",
    "bahut": "Bahut",
    "sab": "Sab",
    "kaun": "Kaun",
    "kyon": "Kyun",
    "hai": "Hai",
    "kya": "Kya",
    "tum": "Tum",
    "hum": "Hum",
    "aap": "Aap",
    "woh": "Woh",
    "batao": "Batao",
    "jaldi": "Jaldi",
    "zaroor": "Zaroor",
    "chahiye": "Chahiye",
}

RU_ROMAN_ONLY_CORRECTIONS = {
    "men": "mein",
    "mai": "mein",
    "ap": "aap",
    "ye": "yeh",
    "main": "Main",
    "wo": "woh",
}

ALL_RU_CORRECTIONS = {**RU_TYPO_CORRECTIONS, **RU_ROMAN_ONLY_CORRECTIONS}


def apply_case_pattern(source: str, target: str) -> str:
    """Keep the capitalisation style of *source* for the replacement *target*."""
    if not target:
        return target
    if source.isupper() and len(source) > 1:
        return target.upper()
    if source and source[0].isupper():
        return target[0].upper() + target[1:]
    return target


class LanguageDetector:
    """Classifies a fragment of text as english / roman_urdu / urdu_script."""

    ENGLISH_MARKERS = frozenset({
        "the", "be", "to", "of", "and", "a", "in", "that", "have", "i", "it",
        "for", "not", "on", "with", "he", "as", "you", "do", "at", "this",
        "but", "his", "by", "from", "they", "we", "say", "her", "she", "or",
        "an", "will", "my", "one", "all", "would", "there", "their", "what",
        "so", "up", "out", "if", "about", "who", "get", "which", "go", "me",
        "when", "make", "can", "like", "time", "no", "just", "him", "know",
        "take", "people", "into", "year", "your", "good", "some", "could",
        "them", "see", "other", "than", "then", "now", "look", "only", "come",
        "its", "over", "think", "also", "back", "after", "use", "two", "how",
        "our", "work", "first", "well", "way", "even", "new", "want",
        "because", "any", "these", "give", "day", "most", "us", "hello",
        "help", "please", "thanks", "thank", "world", "please", "let",
        "really", "much", "very", "still", "back", "down", "off", "again",
    })

    ROMAN_URDU_MARKERS = frozenset({
        "hai", "hain", "hoon", "hun", "ho", "nahi", "nahin", "kya", "kyun",
        "kyon", "kaise", "kahan", "mera", "meri", "mere", "tumhara", "tumhari",
        "humara", "humari", "uska", "uski", "uske", "unka", "unki", "iske",
        "mera", "apna", "apni", "kuch", "sab", "kaun", "kya", "kaisay",
        "bohat", "bahut", "zyada", "thora", "jaldi", "foran", "abhi", "waqt",
        "raat", "subah", "dopahar", "sham", "sher", "dost", "dosti", "bhai",
        "behen", "didi", "yaar", "janab", "sahib", "madad", "masla", "masle",
        "koshish", "tayyar", "khush", "khushi", "shukriya", "shukr", "salaam",
        "assalam", "alaikum", "jumma", "eid", "mubarak", "khayal", "kaam",
        "baat", "wahee", "waqi", "haal", "hal", "chal", "chalo", "chalte",
        "raha", "rahi", "rahe", "wala", "wali", "wale", "gaya", "gayi",
        "gaye", "unga", "ungi", "enge", "karna", "karna", "hona", "hota",
        "hoti", "hone", "laga", "lagta", "lagti", "theek", "thik", "acha",
        "achha", "shukria", "bohat", "bhai", "sab", "kuch", "bhi", "toh",
        "to", "mat", "nahi", "bohat", "zaroor", "chahiye", "karna", "krna",
        "acha", "shukriya", "theek", "kaisay", "shukria", "kya", "hai",
    })

    STRONG_ROMAN_URDU = frozenset({
        "kaise", "nahi", "nhi", "kahan", "kyun", "kyon", "mera", "meri",
        "tumhara", "humara", "bohat", "bahut", "zyada", "shukriya",
        "zaroor", "chahiye", "jaldi", "theek", "thik", "acha", "achha",
        "salaam", "assalam", "alaikum", "jumma", "mubarak", "khayal",
        "dost", "bhai", "yaar", "madad", "khush", "kuch", "sab", "waqt",
        "abhi", "foran", "subah", "dopahar", "sham", "behen", "didi",
        "wali", "wala", "wale", "gaya", "gayi", "gaye", "raha", "rahi",
        "rahe", "kya", "hai", "hain", "hoon", "mein", "mera", "apna",
    })

    COMMON_TYPOS = frozenset({
        "teh", "becuase", "recieve", "seperate", "definately", "adn",
        "acn", "taht", "occured", "untill", "occassion", "accomodate",
    })

    def detect(self, text: str) -> str:
        """Return ``english``, ``roman_urdu`` or ``urdu_script``."""
        if not text or not text.strip():
            return "english"

        words = WORD_RE.findall(text.lower())
        if not words:
            return "english"

        if any(any(ch in URDU_CHARS for ch in word) for word in words):
            return "urdu_script"

        window = words[-6:]
        ru_score = sum(1 for word in window if word in self.ROMAN_URDU_MARKERS)
        en_score = sum(1 for word in window if word in self.ENGLISH_MARKERS)

        if ru_score > en_score:
            return "roman_urdu"

        last = words[-1]
        if last in self.STRONG_ROMAN_URDU and last not in self.ENGLISH_MARKERS:
            return "roman_urdu"

        if last in self.COMMON_TYPOS or last in self.ENGLISH_MARKERS:
            return "english"

        return "english"

    def is_urdu_script(self, text: str) -> bool:
        return self.detect(text) == "urdu_script"


def roman_urdu_correction(word: str, lang: str, is_known_english=None) -> str:
    """Return the Roman Urdu correction for *word* (or the word unchanged).

    *is_known_english* is a callable that reports whether a word is a common
    English word; it is used to protect English text from Roman Urdu rewrites.
    """
    if not word:
        return word
    key = word.lower()

    if lang == "roman_urdu":
        replacement = ALL_RU_CORRECTIONS.get(key)
        if replacement:
            return apply_case_pattern(word, replacement)
        return word

    replacement = RU_TYPO_CORRECTIONS.get(key)
    if replacement and is_known_english is not None and is_known_english(key):
        return word
    if replacement:
        return apply_case_pattern(word, replacement)
    return word
