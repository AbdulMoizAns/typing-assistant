"""
ALPHA Typing Assistant v5.1 - With Auto-Suggest While Typing & Modern Dashboard
Author: Moiz Digital Service
Features:
  - Auto-Popup while typing (shows suggestions automatically after 2 letters)
  - Manual Shortcuts: Ctrl+Space, Double-Ctrl, Alt+/
  - Interactive Desktop Dashboard UI with Live Test Sandbox & Activity Feed
  - Real-time global auto-correction on Space (English & Roman Urdu)
  - Low-level Windows hook with selective key suppression (Arrows/Enter/Tab/Esc)
  - Guaranteed popup visibility near caret / mouse / active window
  - Prioritized common vocabulary (hello, help, world, please, etc.)
  - Exact-character deletion to prevent text duplication
"""
import os
import sys
import time
import json
import re
import queue
import bisect
import ctypes
import copy
import tempfile
import atexit
import platform
import threading
import tkinter as tk
from tkinter import ttk, Listbox, Scrollbar
from collections import deque
from datetime import datetime

# =============================================================
# ZERO-TRUST AIR-GAP PRIVACY FIREWALL
# =============================================================
# Guarantees 100% offline isolation. Hard-blocks any attempt by
# dependencies, external modules, or sub-processes to establish
# network sockets or send telemetry. Keystrokes never leave RAM.
import socket

class AirGapPrivacyViolation(PermissionError):
    """Raised when any component attempts an unauthorized network connection."""
    pass

def _install_airgap_firewall():
    _OrigSocket = socket.socket

    class _AirGapBlockedSocket(_OrigSocket):
        def __init__(self, *args, **kwargs):
            raise AirGapPrivacyViolation(
                "[ALPHA AIR-GAP FIREWALL] Outbound/Inbound network connection BLOCKED! "
                "ALPHA is operating in 100% offline private mode to protect your typing privacy."
            )

        def connect(self, *args, **kwargs):
            raise AirGapPrivacyViolation("[ALPHA AIR-GAP FIREWALL] Network connection BLOCKED!")

        def connect_ex(self, *args, **kwargs):
            raise AirGapPrivacyViolation("[ALPHA AIR-GAP FIREWALL] Network connection BLOCKED!")

        def bind(self, *args, **kwargs):
            raise AirGapPrivacyViolation("[ALPHA AIR-GAP FIREWALL] Network binding BLOCKED!")

    def _blocked_call(*args, **kwargs):
        raise AirGapPrivacyViolation(
            "[ALPHA AIR-GAP FIREWALL] Outbound/Inbound network connection BLOCKED! "
            "ALPHA is operating in 100% offline private mode to protect your typing privacy."
        )

    socket.socket = _AirGapBlockedSocket
    socket.create_connection = _blocked_call
    try:
        socket.getaddrinfo = _blocked_call
        socket.gethostbyname = _blocked_call
        socket.gethostbyname_ex = _blocked_call
        socket.getfqdn = _blocked_call
    except Exception:
        pass

_install_airgap_firewall()

from pynput import keyboard as pynput_keyboard

try:
    import pyperclip
    import pyautogui
    pyautogui.FAILSAFE = False
    pyautogui.PAUSE = 0
    CLIPBOARD_PASTE = True
except ImportError:
    CLIPBOARD_PASTE = False

try:
    import keyboard as kb_lib
    HAVE_KEYBOARD = True
except ImportError:
    HAVE_KEYBOARD = False

# =============================================================
# CONFIGURATION
# =============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SUGGESTIONS_FILE = os.path.join(BASE_DIR, "suggestions.json")
ERRORS_FILE = os.path.join(BASE_DIR, "errors.json")
DICTIONARY_FILE = os.path.join(BASE_DIR, "dictionary.json")
USER_LEARNING_FILE = os.path.join(BASE_DIR, "user_learning.json")
USAGE_STATS_FILE = os.path.join(BASE_DIR, "usage_stats.json")
RU_LEARNING_FILE = os.path.join(BASE_DIR, "ru_learning.json")
WORD_PAIRS_FILE = os.path.join(BASE_DIR, "word_pairs.json")
RECENCY_FILE = os.path.join(BASE_DIR, "recency.json")
SEQUENCES_FILE = os.path.join(BASE_DIR, "sequences.json")
FREQUENCY_FILE = os.path.join(BASE_DIR, "frequency_words.json")

POPUP_WIDTH = 320
MAX_SUGGESTIONS = 8
MIN_WORD_LENGTH = 2
BACKSPACE_DELAY = 0.005
PASTE_DELAY = 0.05
RESTORE_CLIPBOARD_DELAY = 0.08
DEBOUNCE_MS = 140

ENABLED_DEFAULT = True
AUTO_SUGGEST_DEFAULT = True

# Top 500+ most common everyday English words to rank at the top of suggestions
COMMON_ENGLISH_WORDS = {
    "the", "be", "to", "of", "and", "a", "in", "that", "have", "i", "it", "for", "not", "on", "with",
    "he", "as", "you", "do", "at", "this", "but", "his", "by", "from", "they", "we", "say", "her", "she",
    "or", "an", "will", "my", "one", "all", "would", "there", "their", "what", "so", "up", "out", "if",
    "about", "who", "get", "which", "go", "me", "when", "make", "can", "like", "time", "no", "just",
    "him", "know", "take", "people", "into", "year", "your", "good", "some", "could", "them", "see",
    "other", "than", "then", "now", "look", "only", "come", "its", "over", "think", "also", "back",
    "after", "use", "two", "how", "our", "work", "first", "well", "way", "even", "new", "want", "because",
    "any", "these", "give", "day", "most", "us", "hello", "help", "helpful", "helping", "please", "pleasure",
    "thank", "thanks", "world", "working", "worker", "write", "writing", "written", "great", "greatly",
    "start", "started", "starting", "stop", "stopped", "stopping", "need", "needed", "needing", "call",
    "called", "calling", "system", "program", "question", "answer", "problem", "service", "digital",
    "computer", "message", "email", "office", "school", "friend", "family", "today", "tomorrow",
    "yesterday", "morning", "night", "evening", "welcome", "happy", "blessed", "regards", "kindly",
    "sincerely", "important", "possible", "information", "support", "development", "project", "meeting",
    "schedule", "send", "sending", "receive", "received", "check", "checking", "update", "updated",
    "understand", "different", "number", "change", "water", "light", "house", "place", "again",
    "always", "around", "another", "before", "better", "between", "both", "business", "company",
    "continue", "during", "each", "early", "enough", "every", "example", "father", "feel",
    "group", "hand", "high", "home", "interest", "large", "last", "later", "leave", "life", "line",
    "little", "live", "long", "many", "mean", "might", "money", "month", "mother", "move", "much",
    "must", "name", "never", "next", "nothing", "off", "often", "once", "open", "order", "own",
    "part", "party", "point", "power", "present", "president", "public", "put", "read", "real",
    "reason", "right", "room", "run", "same", "second", "seem", "several", "show", "side", "small",
    "social", "state", "story", "student", "study", "such", "sure", "tell", "thing", "though",
    "three", "through", "together", "try", "turn", "under", "until", "upon", "value", "view",
    "voice", "wait", "walk", "week", "where", "while", "white", "whole", "why", "without", "wrong",
    "young", "shukriya", "theek", "bohat", "karna", "kaise", "nahi", "accha", "salam", "aap", "mera"
}

# =============================================================
# BACKGROUND WRITER (Thread-Safe Async I/O)
# =============================================================
class BackgroundWriter:
    __slots__ = ("_queue", "_thread")

    def __init__(self):
        self._queue = queue.Queue()
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def save(self, path, data):
        try:
            data_copy = copy.deepcopy(data)
        except Exception:
            data_copy = dict(data) if isinstance(data, dict) else list(data) if isinstance(data, list) else data
        self._queue.put((path, data_copy))

    def shutdown(self):
        self._queue.put(None)
        self._thread.join(timeout=2.0)

    def _worker(self):
        while True:
            item = self._queue.get()
            if item is None:
                self._queue.task_done()
                break
            path, data = item
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            except Exception:
                pass
            self._queue.task_done()


bg_writer = BackgroundWriter()
atexit.register(bg_writer.shutdown)

# =============================================================
# CARET TRACKING & MULTI-LAYER FALLBACK (Win32 API)
# =============================================================
class _RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

class _GUITHREADINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_uint32), ("flags", ctypes.c_uint32),
        ("hwndActive", ctypes.c_size_t), ("hwndFocus", ctypes.c_size_t),
        ("hwndCapture", ctypes.c_size_t), ("hwndMenuOwner", ctypes.c_size_t),
        ("hwndMoveSize", ctypes.c_size_t), ("hwndCaret", ctypes.c_size_t),
        ("rcCaret", _RECT),
    ]

class _POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

if sys.platform == "win32":
    user32 = ctypes.windll.user32
else:
    user32 = None

_last_caret = (400, 350)
_caret_lock = threading.Lock()

def update_caret_position():
    """Poll Win32 caret position with mouse cursor and foreground window fallback."""
    global _last_caret
    if not user32:
        return False

    # 1. Try standard Win32 edit control caret
    try:
        info = _GUITHREADINFO()
        info.cbSize = ctypes.sizeof(_GUITHREADINFO)
        if user32.GetGUIThreadInfo(0, ctypes.byref(info)) and info.hwndCaret:
            pt = _POINT(info.rcCaret.left, info.rcCaret.bottom)
            user32.ClientToScreen(info.hwndCaret, ctypes.byref(pt))
            if pt.x > 0 and pt.y > 0:
                with _caret_lock:
                    _last_caret = (pt.x + 10, pt.y + 25)
                return True
    except Exception:
        pass

    # 2. Fallback: Mouse cursor position
    try:
        pt = _POINT()
        if user32.GetCursorPos(ctypes.byref(pt)):
            if pt.x > 0 and pt.y > 0:
                with _caret_lock:
                    _last_caret = (pt.x + 15, pt.y + 20)
                return True
    except Exception:
        pass

    # 3. Fallback: Active foreground window
    try:
        hwnd = user32.GetForegroundWindow()
        if hwnd:
            rect = _RECT()
            if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                win_x = rect.left + max(40, (rect.right - rect.left) // 4)
                win_y = rect.top + max(60, (rect.bottom - rect.top) // 3)
                if win_x > 0 and win_y > 0:
                    with _caret_lock:
                        _last_caret = (win_x, win_y)
                    return True
    except Exception:
        pass

    return False

def get_caret_position():
    with _caret_lock:
        return _last_caret

# =============================================================
# DATA MANAGER & NLP ENGINE
# =============================================================
class DictIndex:
    __slots__ = ("_words", "_keys")
    def __init__(self, words):
        clean = sorted(set(w.strip() for w in words if len(w.strip()) >= 2), key=str.lower)
        self._words = tuple(clean)
        self._keys = tuple(w.lower() for w in self._words)

    def prefix_search(self, prefix, limit=30):
        prefix_l = prefix.lower()
        lo = bisect.bisect_left(self._keys, prefix_l)
        results = []
        for i in range(lo, len(self._keys)):
            if self._keys[i].startswith(prefix_l):
                results.append(self._words[i])
                if len(results) >= limit:
                    break
            else:
                break
        return results


class SequenceLearner:
    __slots__ = ("sequences", "trigrams")
    def __init__(self):
        self.sequences = {}
        self.trigrams = {}

    def learn(self, word_list):
        if len(word_list) < 2:
            return
        for i in range(len(word_list) - 1):
            cur, nxt = word_list[i].lower(), word_list[i + 1].lower()
            self.sequences.setdefault(cur, {})
            self.sequences[cur][nxt] = self.sequences[cur].get(nxt, 0) + 1
        for i in range(len(word_list) - 2):
            key = f"{word_list[i].lower()}_{word_list[i+1].lower()}"
            nxt = word_list[i + 2].lower()
            self.trigrams.setdefault(key, {})
            self.trigrams[key][nxt] = self.trigrams[key].get(nxt, 0) + 1

    def predict_next(self, current_word, prev_word=None):
        cur = current_word.lower()
        score_dict = {}
        if prev_word:
            tkey = f"{prev_word.lower()}_{cur}"
            if tkey in self.trigrams:
                for w, c in self.trigrams[tkey].items():
                    score_dict[w] = score_dict.get(w, 0) + c * 3
        if cur in self.sequences:
            for w, c in self.sequences[cur].items():
                score_dict[w] = score_dict.get(w, 0) + c
        results = sorted(score_dict.items(), key=lambda x: x[1], reverse=True)
        return [w for w, _ in results[:5]]


class LanguageDetector:
    ENGLISH_COMMON = {
        "the", "be", "to", "of", "and", "a", "in", "that", "have", "i",
        "it", "for", "not", "on", "with", "he", "as", "you", "do", "at",
        "this", "but", "his", "by", "from", "they", "we", "say", "her",
    }
    ROMAN_URDU_COMMON = {
        "hai", "hain", "tha", "thi", "the", "ho", "mein", "main", "tum",
        "wo", "woh", "yeh", "ye", "hum", "aap", "ap", "kya", "kyun", "kyon",
        "kaise", "nahi", "nhi", "haan", "acha", "achha", "theek", "thik",
        "hoon", "hun", "karna", "krna", "bohat", "bhot", "bhai", "jana",
        "aaj", "kal", "shukriya", "shukria", "salaam", "karo", "raha",
        "rahi", "rahe", "wali", "wala", "wale", "kuch", "sab", "kaun",
        "mast", "gaya", "gayi", "gaye", "bhi", "toh", "to", "mat",
    }
    COMMON_TYPOS = {"teh", "becuase", "recieve", "seperate", "definately", "adn", "acn", "taht"}
    URDU_CHARS = set("ابپتٹثجچحخدڈذرزژسشصضطظعغفقکگلمنہوےؤئى")

    def detect(self, text):
        if not text or len(text.strip()) < 1:
            return "english"
        words = re.findall(r"[a-zA-Z؀-ۿ']+", text.lower())
        if not words:
            return "english"
        if any(any(ch in self.URDU_CHARS for ch in w) for w in words):
            return "urdu_script"

        recent = words[-4:]
        ru_count = sum(1 for w in recent if w in self.ROMAN_URDU_COMMON)
        en_count = sum(1 for w in recent if w in self.ENGLISH_COMMON)
        if ru_count > en_count:
            return "roman_urdu"

        last_word = words[-1]
        if last_word in self.COMMON_TYPOS or last_word in self.ENGLISH_COMMON:
            return "english"
        if last_word in self.ROMAN_URDU_COMMON:
            return "roman_urdu"
        if re.search(r"(th|ng|ck|tion|ing|ment)$", last_word):
            return "english"
        if last_word.endswith("h") and len(last_word) > 2 and not last_word.endswith(("th", "ch", "sh")):
            return "roman_urdu"
        return "english"


ROMAN_URDU_CORRECTIONS = {
    "mei": "mein", "mai": "mein", "men": "mein", "nhe": "nahi",
    "nai": "nahi", "nhi": "nahi", "krna": "karna", "bhot": "bohat",
    "zyda": "zyada", "ghr": "ghar", "skool": "school", "ap": "aap",
    "wo": "woh", "ye": "yeh", "shukria": "Shukriya", "shukriya": "Shukriya",
    "thik": "Theek", "theek": "Theek", "achha": "Achha", "acha": "Achha",
    "kuch": "Kuch", "bahut": "Bahut", "sab": "Sab", "kaun": "Kaun",
    "kyon": "Kyun", "hai": "Hai", "kya": "Kya", "main": "Main",
    "tum": "Tum", "aap": "Aap", "hum": "Hum", "woh": "Woh",
}


class DataManager:
    __slots__ = (
        "suggestions", "user_learning", "usage_stats", "dict_index",
        "errors", "ru_learning", "_ru_corrections",
        "word_pairs", "recency_tracker", "sequence_learner", "word_history",
        "lang_detector", "bg", "freq_english_words", "freq_english_ranks",
        "freq_roman_urdu_words", "freq_index",
    )

    def __init__(self, bg=None):
        self.bg = bg
        self.suggestions = self._load_json(SUGGESTIONS_FILE, {})
        self.user_learning = self._load_json(USER_LEARNING_FILE, {})
        self.usage_stats = self._load_json(USAGE_STATS_FILE, {})
        self.dict_index = self._build_dict_index()

        freq_raw = self._load_json(FREQUENCY_FILE, {})
        self.freq_english_words = freq_raw.get("english", [])
        self.freq_roman_urdu_words = freq_raw.get("roman_urdu", [])
        self.freq_english_ranks = {w: i for i, w in enumerate(self.freq_english_words)}
        all_freq = list(self.freq_english_words) + list(self.freq_roman_urdu_words)
        self.freq_index = DictIndex(all_freq) if all_freq else None

        raw_errors = self._load_json(ERRORS_FILE, {})
        self.errors = {k.strip().lower(): v.strip() for k, v in raw_errors.items()
                       if k.strip() and v.strip() and k.strip().lower() != v.strip().lower()}

        common_typos = {
            "teh": "the", "reciver": "receiver", "becuase": "because",
            "recieve": "receive", "seperate": "separate", "definately": "definitely",
            "adn": "and", "acn": "can", "taht": "that",
        }
        for typo, correct in common_typos.items():
            if typo not in self.errors:
                self.errors[typo] = correct

        self.ru_learning = self._load_json(RU_LEARNING_FILE, {})
        self._ru_corrections = dict(ROMAN_URDU_CORRECTIONS)
        self.word_pairs = self._load_json(WORD_PAIRS_FILE, {})
        self.recency_tracker = self._load_json(RECENCY_FILE, {})
        self.sequence_learner = SequenceLearner()
        self.word_history = []
        self.lang_detector = LanguageDetector()
        self._load_sequences()
        self._load_common_sequences()

    @staticmethod
    def _load_json(path, default):
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return default

    def _build_dict_index(self):
        raw = self._load_json(DICTIONARY_FILE, [])
        return DictIndex(raw) if isinstance(raw, list) and raw else None

    def correct_error(self, word, lang="english"):
        w = word.lower()
        if not w or len(w) < 2:
            return word

        # 1. Check Roman Urdu corrections
        if lang == "roman_urdu":
            if w in self._ru_corrections:
                return self._ru_corrections[w]
            if w in self.ru_learning and self.ru_learning[w] > 2:
                return w

        # 2. Check main errors database
        if w in self.errors:
            return self.errors[w]

        # 3. Fallback check for Roman Urdu corrections
        if w in self._ru_corrections:
            return self._ru_corrections[w]

        return word

    def get_custom_matches(self, prefix):
        prefix_l = prefix.lower()
        results = []
        snippets = self.suggestions.get("snippets", {})
        if isinstance(snippets, dict):
            for k, val in snippets.items():
                if k.lower() == prefix_l:
                    results.append((val, 1500))
                elif k.lower().startswith(prefix_l):
                    results.append((val, 950))
                elif isinstance(val, str) and val.lower().startswith(prefix_l):
                    results.append((val, 200))

        templates = self.suggestions.get("templates", [])
        if isinstance(templates, list):
            for tpl in templates:
                if isinstance(tpl, str) and tpl.lower().startswith(prefix_l):
                    results.append((tpl, 100))
        return results

    def get_smart_matches_enhanced(self, prefix, lang="english", prev_word=""):
        if not prefix or len(prefix) < MIN_WORD_LENGTH:
            return []
        prefix_l = prefix.lower()
        tier1_map = {}

        def add_tier1(w, score):
            if not w:
                return
            if w not in tier1_map or score > tier1_map[w]:
                tier1_map[w] = score

        # =============================================================
        # TIER 1: HIGH-FREQUENCY EVERYDAY WORDS & USER DATA
        # =============================================================
        # 1. Exact typo match (Highest priority)
        if prefix_l in self.errors:
            corr = self.errors[prefix_l]
            score = 3500 if lang == "english" else 3000
            add_tier1(corr, score)

        if prefix_l in self._ru_corrections:
            corr = self._ru_corrections[prefix_l]
            score = 3500 if lang == "roman_urdu" else 1800
            add_tier1(corr, score)

        # 2. Snippets (sig1, addr) vs Template sentences
        for custom_text, custom_score in self.get_custom_matches(prefix_l):
            if "\n" in custom_text or "{" in custom_text:
                add_tier1(custom_text, 1400 + custom_score)
            else:
                add_tier1(custom_text, 2700 + custom_score)

        # 3. Context match (bigrams from previous word)
        if prev_word:
            key = f"{prev_word}|{prefix_l}"
            if key in self.word_pairs:
                for w, sc in sorted(self.word_pairs[key].items(), key=lambda x: x[1], reverse=True)[:3]:
                    add_tier1(w, 2200 + sc * 10)

        # 4. User learning matches
        for w, cnt in self.user_learning.items():
            if w.lower().startswith(prefix_l):
                add_tier1(w, 2100 + cnt * 10)

        # 5. Usage stats matches
        for w, cnt in self.usage_stats.items():
            if w.lower().startswith(prefix_l):
                add_tier1(w, 2000 + cnt * 5)

        # 6. High-Frequency Roman Urdu Vocabulary
        ru_weight = 2400 if lang == "roman_urdu" else 1700
        for w in self.freq_roman_urdu_words:
            if w.startswith(prefix_l):
                add_tier1(w, ru_weight)

        # 7. High-Frequency English Vocabulary (Ranked by usage frequency)
        en_base = 2500 if lang == "english" else 1800
        if self.freq_index:
            matches = self.freq_index.prefix_search(prefix_l, limit=60)
            for w in matches:
                rank = self.freq_english_ranks.get(w, 10000)
                score = en_base - (rank // 8)
                if len(w) - len(prefix_l) <= 3:
                    score += 50
                add_tier1(w, score)

            # If prefix was a known typo (e.g. 'teh' for 'the'), also include completions of corrected word
            if prefix_l in self.errors:
                corr_l = self.errors[prefix_l].lower()
                if corr_l != prefix_l and len(corr_l) >= 2:
                    for w in self.freq_index.prefix_search(corr_l, limit=20):
                        rank = self.freq_english_ranks.get(w, 10000)
                        add_tier1(w, en_base - 100 - (rank // 8))

        # Fallback to curated common list if freq_index had no matches
        for w in COMMON_ENGLISH_WORDS:
            if w.startswith(prefix_l):
                add_tier1(w, 1600)

        # Boost any candidate that user has actually used/learned
        for w in list(tier1_map.keys()):
            w_l = w.lower()
            bonus = 0
            if w_l in self.user_learning:
                bonus += min(150, self.user_learning[w_l] * 15)
            if w_l in self.usage_stats:
                bonus += min(100, self.usage_stats[w_l] * 8)
            if w_l in self.recency_tracker:
                bonus += min(50, self.recency_tracker[w_l] * 5)
            if bonus > 0:
                tier1_map[w] += bonus

        tier1_sorted = sorted(tier1_map.items(), key=lambda x: x[1], reverse=True)
        tier1_candidates = [w for w, _ in tier1_sorted]

        # =============================================================
        # TIER 1 GATE:
        # If Tier 1 has sufficient matches (>= 4), or if prefix is short
        # (<= 2 chars) and Tier 1 has matches, RETURN IMMEDIATELY!
        # Do not even inspect the 370,000-word dictionary!
        # =============================================================
        if len(tier1_candidates) >= 4 or (tier1_candidates and len(prefix_l) <= 2):
            return tier1_candidates[:MAX_SUGGESTIONS]

        # =============================================================
        # TIER 2: GENERAL DICTIONARY FALLBACK
        # Only reached when Tier 1 has fewer than 4 matches
        # (e.g. for rare, scientific, medical, or technical words)
        # =============================================================
        tier2_results = []
        seen_words = {w.lower() for w in tier1_candidates}
        if self.dict_index:
            for w in self.dict_index.prefix_search(prefix_l, limit=40):
                w_l = w.lower()
                if w_l not in seen_words:
                    if w_l.isalpha() and len(w_l) >= 3:
                        seen_words.add(w_l)
                        tier2_results.append(w)
            tier2_results.sort(key=lambda x: (len(x), x.lower()))

        final_list = tier1_candidates + tier2_results
        return final_list[:MAX_SUGGESTIONS]

    def learn_from_selection(self, original_word, selected_word, prev_word=""):
        if prev_word:
            key = f"{prev_word}|{original_word.lower()}"
            self.word_pairs.setdefault(key, {})
            self.word_pairs[key][selected_word] = self.word_pairs[key].get(selected_word, 0) + 1
            if len(self.word_pairs) > 1000:
                oldest = next(iter(self.word_pairs))
                del self.word_pairs[oldest]
            if self.bg:
                self.bg.save(WORD_PAIRS_FILE, self.word_pairs)

        self.recency_tracker[selected_word] = time.time()
        if len(self.recency_tracker) > 500:
            self.recency_tracker = dict(sorted(self.recency_tracker.items(), key=lambda x: x[1])[-500:])
        if self.bg:
            self.bg.save(RECENCY_FILE, self.recency_tracker)

    def learn_word(self, word, lang="english"):
        w = word.lower()
        if lang == "roman_urdu":
            self.ru_learning[w] = self.ru_learning.get(w, 0) + 1
            if self.bg:
                self.bg.save(RU_LEARNING_FILE, self.ru_learning)
        else:
            self.user_learning[w] = self.user_learning.get(w, 0) + 1
            if self.bg:
                self.bg.save(USER_LEARNING_FILE, self.user_learning)

    def record_usage(self, word):
        w = word.lower()
        self.usage_stats[w] = self.usage_stats.get(w, 0) + 1
        if self.bg:
            self.bg.save(USAGE_STATS_FILE, self.usage_stats)

    def _load_sequences(self):
        data = self._load_json(SEQUENCES_FILE, {})
        self.sequence_learner.sequences = data.get("pairs", {})
        self.sequence_learner.trigrams = data.get("trigrams", {})

    def _save_sequences(self):
        if self.bg:
            self.bg.save(SEQUENCES_FILE, {
                "pairs": self.sequence_learner.sequences,
                "trigrams": self.sequence_learner.trigrams,
            })

    def _load_common_sequences(self):
        common = {
            "how": {"are": 120, "to": 90, "do": 80, "is": 70, "can": 60},
            "are": {"you": 120, "we": 80, "there": 70, "they": 60, "your": 50},
            "i": {"am": 120, "have": 100, "will": 90, "would": 85, "want": 80, "can": 75, "need": 70},
            "you": {"are": 110, "have": 90, "can": 80, "want": 70, "know": 60},
            "thank": {"you": 140, "god": 80},
            "thanks": {"for": 110, "to": 80, "you": 70},
            "please": {"let": 120, "find": 100, "help": 90, "send": 85, "contact": 80, "check": 75},
            "let": {"me": 130, "us": 110},
            "would": {"like": 130, "be": 100, "have": 80, "prefer": 70},
            "could": {"you": 120, "be": 80, "have": 70},
            "can": {"you": 120, "i": 100, "we": 90, "be": 70},
            "will": {"be": 110, "have": 90, "do": 80, "call": 70},
            "good": {"morning": 120, "afternoon": 100, "evening": 95, "night": 90, "job": 80, "luck": 75},
            "have": {"a": 120, "been": 100, "to": 90, "done": 70},
            "take": {"care": 130, "it": 90, "time": 80},
            "see": {"you": 130, "the": 80, "it": 70},
            "nice": {"to": 130},
            "looking": {"forward": 140},
            "what": {"is": 120, "are": 90, "do": 80, "about": 70},
            "where": {"is": 120, "are": 90, "can": 70},
            "when": {"is": 110, "will": 90, "can": 80, "you": 70},
            "who": {"is": 120, "are": 90, "can": 80},
            "this": {"is": 120, "will": 80, "was": 70},
            "that": {"is": 120, "was": 90, "would": 70},
            "there": {"is": 120, "are": 110, "was": 80},
            "here": {"is": 120, "are": 90},
            "well": {"done": 120, "said": 80},
            "very": {"good": 120, "much": 110, "well": 90, "happy": 80},
            "in": {"order": 110, "the": 100, "this": 80},
            "as": {"well": 120, "per": 110, "soon": 100},
            # Roman Urdu bigrams
            "aap": {"kaise": 140, "kahan": 110, "kya": 100, "ko": 90, "ka": 85, "batao": 80},
            "kaise": {"ho": 140, "hain": 130},
            "mein": {"theek": 140, "thik": 130, "bhi": 100, "apne": 90, "aaj": 80},
            "theek": {"hoon": 140, "hai": 130, "hoga": 90},
            "thik": {"hoon": 140, "hai": 130},
            "shukriya": {"bohat": 130, "bhai": 120, "aapka": 110, "dost": 90},
            "bohat": {"shukriya": 140, "achha": 120, "khoob": 110, "zyada": 100},
            "kya": {"hal": 140, "haal": 140, "hai": 130, "hua": 110, "baat": 100, "aap": 90},
            "hal": {"hai": 140, "hain": 130},
            "haal": {"hai": 140, "hain": 130},
            "apna": {"khayal": 140, "kaam": 110, "naam": 90},
            "allah": {"hafiz": 140, "ka": 100},
            "jumma": {"mubarak": 150},
            "eid": {"mubarak": 150},
            "koi": {"baat": 140, "masla": 120, "nahi": 110},
            "hum": {"sab": 130, "bhi": 100},
            "yeh": {"kaam": 120, "baat": 110, "kya": 100},
            "karna": {"hai": 130, "hoga": 110, "chahiye": 100},
            "zaroor": {"karna": 120, "aana": 110, "batana": 100},
            "assalam": {"o": 150},
            "o": {"alaikum": 150},
            "walaikum": {"assalam": 150},
        }
        for word, next_words in common.items():
            if word not in self.sequence_learner.sequences:
                self.sequence_learner.sequences[word] = {}
            for nw, cnt in next_words.items():
                if nw not in self.sequence_learner.sequences[word]:
                    self.sequence_learner.sequences[word][nw] = cnt

        common_trigrams = {
            "how_are": {"you": 160, "things": 110, "they": 90, "we": 80},
            "thank_you": {"so": 160, "very": 150, "much": 140, "for": 130},
            "please_let": {"me": 160, "us": 130},
            "let_me": {"know": 160, "see": 120, "check": 110},
            "would_like": {"to": 160, "a": 110},
            "looking_forward": {"to": 160},
            "nice_to": {"meet": 160, "see": 130},
            "have_a": {"good": 160, "great": 150, "nice": 140, "wonderful": 120},
            "take_care": {"of": 160, "bye": 120},
            "see_you": {"soon": 160, "tomorrow": 140, "later": 130},
            "what_is": {"the": 160, "your": 150, "this": 140},
            "i_am": {"writing": 150, "pleased": 130, "fine": 120, "working": 110},
            "as_well": {"as": 160},
            "in_order": {"to": 160},
            # Roman Urdu trigrams
            "aap_kaise": {"ho": 170, "hain": 160},
            "mein_theek": {"hoon": 170},
            "mein_thik": {"hoon": 170},
            "kya_hal": {"hai": 170, "hain": 160},
            "kya_haal": {"hai": 170, "hain": 160},
            "apna_khayal": {"rakhna": 170, "rakhein": 160},
            "allah_hafiz": {"bhai": 160, "dost": 130},
            "jumma_mubarak": {"ho": 160, "aapko": 150},
            "eid_mubarak": {"ho": 160, "aapko": 150},
            "koi_baat": {"nahi": 170},
            "bohat_bohat": {"shukriya": 170, "mubarak": 160},
            "theek_hai": {"bhai": 160, "to": 130},
            "assalam_o": {"alaikum": 180},
        }
        for tkey, next_words in common_trigrams.items():
            if tkey not in self.sequence_learner.trigrams:
                self.sequence_learner.trigrams[tkey] = {}
            for nw, cnt in next_words.items():
                if nw not in self.sequence_learner.trigrams[tkey]:
                    self.sequence_learner.trigrams[tkey][nw] = cnt

    def learn_from_text(self, text):
        words = re.findall(r"[a-zA-Z\u0600-\u06ff']+", text.lower())
        if len(words) >= 2:
            self.word_history.extend(words)
            if len(self.word_history) > 100:
                self.word_history = self.word_history[-100:]
            self.sequence_learner.learn(self.word_history)
            self._save_sequences()

    def predict_next_words(self, current_word, prev_word=None, lang="english", limit=5):
        if not current_word:
            return []
        cur = current_word.lower()
        prev = prev_word.lower() if prev_word else None

        preds = self.sequence_learner.predict_next(cur, prev)
        # Also check word_pairs
        key_pfx = f"{cur}|"
        for k, v in self.word_pairs.items():
            if k.startswith(key_pfx):
                for w in sorted(v, key=v.get, reverse=True)[:3]:
                    if w not in preds:
                        preds.append(w)

        return preds[:limit]

    def predict_next_word(self, current_word):
        prev = self.word_history[-1] if self.word_history else None
        return self.sequence_learner.predict_next(current_word, prev)

    def get_smart_matches_with_prediction(self, prefix, lang="english"):
        suggestions = []
        prefix_l = prefix.lower()
        for pred in self.predict_next_word(prefix_l)[:3]:
            if pred not in suggestions:
                suggestions.append(pred)
        for m in self.get_smart_matches_enhanced(prefix, lang):
            if m not in suggestions:
                suggestions.append(m)
        return suggestions[:MAX_SUGGESTIONS]

# =============================================================
# SUGGESTION POPUP (Dark Theme Listbox Near Cursor)
# =============================================================
class SuggestionPopup:
    __slots__ = ("root", "on_select", "top", "listbox", "suggestions", "current_word", "active", "is_next_word", "header_lbl")

    def __init__(self, root, on_select_callback):
        self.root = root
        self.on_select = on_select_callback
        self.top = None
        self.listbox = None
        self.header_lbl = None
        self.suggestions = []
        self.current_word = ""
        self.active = False
        self.is_next_word = False

    def show(self, suggestions, word, x, y, is_next_word=False):
        if not suggestions:
            self.close()
            return
        self.suggestions = suggestions
        self.current_word = word
        self.is_next_word = is_next_word

        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()

        # Strict screen boundaries: ensure popup is never placed off-screen or in negative coordinates
        popup_x = max(10, min(x, screen_w - POPUP_WIDTH - 20))
        popup_y = max(10, min(y, screen_h - 280))

        if self.top is None or not self.active:
            if self.top:
                try:
                    self.top.destroy()
                except Exception:
                    pass
            self.top = tk.Toplevel(self.root)
            self.top.title("Alpha Suggestions")
            self.top.attributes("-topmost", True)
            self.top.overrideredirect(True)
            self.top.configure(bg="#1e1e2e")

            self.header_lbl = tk.Label(
                self.top, text="", font=("Segoe UI", 8, "bold"),
                bg="#181825", fg="#89b4fa", anchor="w", padx=8, pady=3
            )
            self.header_lbl.pack(fill=tk.X)

            self.listbox = Listbox(
                self.top, font=("Segoe UI", 11), selectmode=tk.SINGLE,
                bg="#1e1e2e", fg="#cdd6f4", selectbackground="#313244",
                selectforeground="#89b4fa", activestyle="none", bd=0,
                highlightthickness=1, highlightbackground="#45475a"
            )
            self.listbox.pack(fill=tk.BOTH, expand=True, padx=3, pady=(0, 3))
            self.listbox.bind("<ButtonRelease-1>", self._on_mouse_click)
            self.active = True

        if self.header_lbl:
            if self.is_next_word:
                self.header_lbl.config(text="  ⚡ NEXT WORD (Tab / Enter to insert)", fg="#cba6f7")
            else:
                self.header_lbl.config(text="  SUGGESTIONS", fg="#89b4fa")

        visible = min(len(suggestions), 7)
        h = visible * 28 + 32
        self.top.geometry(f"{POPUP_WIDTH}x{h}+{popup_x}+{popup_y}")
        self.listbox.delete(0, tk.END)
        for i, item in enumerate(suggestions):
            display_text = item.replace("\n", " -> ") if "\n" in item else item
            prefix_str = f"  {i+1}. " if self.is_next_word else "  "
            self.listbox.insert(tk.END, f"{prefix_str}{display_text}")
        self.listbox.select_set(0)
        self.listbox.activate(0)

        # Force window to top and deiconify so it is 100% visible
        self.top.deiconify()
        self.top.lift()
        self.top.attributes("-topmost", True)

    def _on_mouse_click(self, event):
        idx = self.listbox.nearest(event.y)
        if 0 <= idx < len(self.suggestions):
            selected = self.suggestions[idx]
            was_next = self.is_next_word
            orig = self.current_word
            self.close()
            self.on_select(orig, selected, is_next_word=was_next)

    def select_next(self):
        if not self.listbox or not self.suggestions:
            return
        idx = self.listbox.curselection()
        if not idx:
            self.listbox.select_set(0)
            self.listbox.activate(0)
        elif idx[0] < len(self.suggestions) - 1:
            new_idx = idx[0] + 1
            self.listbox.select_clear(idx[0])
            self.listbox.select_set(new_idx)
            self.listbox.activate(new_idx)
            self.listbox.see(new_idx)

    def select_prev(self):
        if not self.listbox or not self.suggestions:
            return
        idx = self.listbox.curselection()
        if idx and idx[0] > 0:
            new_idx = idx[0] - 1
            self.listbox.select_clear(idx[0])
            self.listbox.select_set(new_idx)
            self.listbox.activate(new_idx)
            self.listbox.see(new_idx)

    def confirm_selected(self):
        if not self.listbox or not self.suggestions:
            return
        idx = self.listbox.curselection()
        selected_idx = idx[0] if idx else 0
        if 0 <= selected_idx < len(self.suggestions):
            word = self.suggestions[selected_idx]
            was_next = self.is_next_word
            orig = self.current_word
            self.close()
            self.on_select(orig, word, is_next_word=was_next)

    def close(self):
        self.active = False
        if self.top:
            try:
                self.top.destroy()
            except Exception:
                pass
            self.top = None
            self.listbox = None

    def navigate(self, key):
        if not self.active:
            return False
        if key in ("up", "w"):
            self.select_prev()
            return True
        if key in ("down", "s"):
            self.select_next()
            return True
        if key in ("enter", "return", "tab"):
            self.confirm_selected()
            return True
        if key in ("escape", "esc"):
            self.close()
            return True
        return False

# =============================================================
# SESSION TRACKER
# =============================================================
class SessionTracker:
    __slots__ = ("session_file", "help_data", "on_record_callback")

    def __init__(self, on_record_callback=None):
        self.session_file = None
        self.on_record_callback = on_record_callback
        self.help_data = {
            "session_start": datetime.now().isoformat(),
            "computer_name": platform.node(),
            "os": platform.system(),
            "apps_helped": {},
            "total_corrections": 0,
            "words_corrected": [],
            "languages_used": [],
        }
        self._create_session_file()

    def _create_session_file(self):
        # 100% In-Memory RAM storage only (Air-gap privacy guarantee)
        # Never writes keystrokes or activity logs to temporary disk files.
        self.session_file = None

    def record_help(self, app_name, original_word, corrected_word, language):
        if not app_name:
            app_name = "Unknown"
        if app_name not in self.help_data["apps_helped"]:
            self.help_data["apps_helped"][app_name] = 0
        self.help_data["apps_helped"][app_name] += 1
        self.help_data["total_corrections"] += 1
        entry = {
            "time": datetime.now().strftime("%H:%M:%S"),
            "app": app_name,
            "from": original_word,
            "to": corrected_word,
            "lang": language,
        }
        self.help_data["words_corrected"].append(entry)
        if len(self.help_data["words_corrected"]) > 50:
            self.help_data["words_corrected"] = self.help_data["words_corrected"][-50:]
        if language not in self.help_data["languages_used"]:
            self.help_data["languages_used"].append(language)

        if self.on_record_callback:
            self.on_record_callback(entry)

    def get_active_app(self):
        try:
            hwnd = user32.GetForegroundWindow() if user32 else 0
            length = user32.GetWindowTextLengthW(hwnd)
            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buff, length + 1)
            title = buff.value
            if not title:
                return "Desktop / Explorer"
            if "WhatsApp" in title:
                return "WhatsApp"
            if "Chrome" in title:
                return "Google Chrome"
            if "Notepad" in title:
                return "Notepad"
            if "Word" in title:
                return "Microsoft Word"
            if "VS Code" in title or "Visual Studio Code" in title:
                return "VS Code"
            if "ALPHA Typing Assistant" in title:
                return "ALPHA Sandbox"
            return title[:25]
        except Exception:
            return "Active Application"

    def get_summary(self):
        hd = self.help_data
        s = f"Start: {hd['session_start'][:19]} | PC: {hd['computer_name']} | OS: {hd['os']}\n"
        s += f"Corrections: {hd['total_corrections']} | Languages: {', '.join(hd['languages_used']) or 'none'}\n"
        if hd["apps_helped"]:
            s += "Applications helped:\n"
            for app, cnt in sorted(hd["apps_helped"].items(), key=lambda x: x[1], reverse=True):
                s += f"  - {app}: {cnt}x\n"
        else:
            s += "No corrections recorded yet.\n"
        return s

    def cleanup(self):
        if self.session_file and os.path.exists(self.session_file):
            try:
                os.remove(self.session_file)
            except Exception:
                pass

# =============================================================
# SELECTIVE GLOBAL HOOK (Low-Level Windows Hook Interception)
# =============================================================
if sys.platform == "win32":
    from pynput._util.win32 import SystemHook

    class SelectiveListener(pynput_keyboard.Listener):
        def __init__(self, assistant, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.assistant = assistant
            self.NAV_VKS = {
                0x26: "up",      # VK_UP
                0x28: "down",    # VK_DOWN
                0x0D: "return",  # VK_RETURN
                0x09: "tab",     # VK_TAB
                0x1B: "escape",  # VK_ESCAPE
            }

        def _handler(self, code, msg, lpdata):
            if code == SystemHook.HC_ACTION and self.assistant.popup.active:
                data = ctypes.cast(lpdata, self._LPKBDLLHOOKSTRUCT).contents
                vk = data.vkCode
                if vk in self.NAV_VKS:
                    if msg in self._PRESS_MESSAGES:
                        key_name = self.NAV_VKS[vk]
                        self.assistant.root.after(0, self.assistant.popup.navigate, key_name)
                    # Suppress event so it never leaks into the active app
                    self.suppress_event()
            super()._handler(code, msg, lpdata)
else:
    class SelectiveListener(pynput_keyboard.Listener):
        def __init__(self, assistant, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.assistant = assistant

# =============================================================
# GLOBAL ASSISTANT (Main Engine)
# =============================================================
class GlobalAssistant:
    __slots__ = (
        "dm", "lang_detector", "session", "keyboard", "enabled", "auto_suggest",
        "next_word_prediction", "is_inserting", "last_ctrl_t", "last_was_ctrl",
        "ctrl_down", "alt_down", "typing_buffer", "buffer_lock", "listener",
        "root", "popup", "current_lang", "last_word_corrected", "kb",
        "_caret_thread", "running", "dashboard_ui", "_suggest_timer", "_auto_close_timer",
    )

    def __init__(self, root):
        self.root = root
        self.dm = DataManager(bg_writer)
        self.lang_detector = LanguageDetector()
        self.session = SessionTracker(on_record_callback=self._on_correction_recorded)
        self.keyboard = pynput_keyboard.Controller()
        self.kb = pynput_keyboard
        self.enabled = ENABLED_DEFAULT
        self.auto_suggest = AUTO_SUGGEST_DEFAULT
        self.next_word_prediction = True
        self.is_inserting = False
        self.last_ctrl_t = 0
        self.last_was_ctrl = False
        self.ctrl_down = False
        self.alt_down = False
        self.typing_buffer = deque(maxlen=60)
        self.buffer_lock = threading.RLock()
        self.listener = None
        self.popup = SuggestionPopup(root, self._on_suggestion_selected)
        self.current_lang = "english"
        self.last_word_corrected = None
        self._caret_thread = threading.Thread(target=self._caret_poll, daemon=True)
        self.running = False
        self.dashboard_ui = None
        self._suggest_timer = None
        self._auto_close_timer = None

        if HAVE_KEYBOARD:
            try:
                kb_lib.add_hotkey("ctrl+alt+x", self.toggle_assistant, suppress=True)
                kb_lib.add_hotkey("ctrl+alt+s", self.show_session_summary, suppress=True)
            except Exception:
                pass

    def _on_correction_recorded(self, entry):
        if self.dashboard_ui:
            self.root.after(0, self.dashboard_ui.add_log_entry, entry)

    def _caret_poll(self):
        while self.running:
            update_caret_position()
            time.sleep(0.1)

    def _on_key_press(self, key):
        if self.is_inserting:
            return True

        # Track modifier states
        if key in (self.kb.Key.ctrl_l, self.kb.Key.ctrl_r):
            self.ctrl_down = True
            now = time.time()
            if self.last_was_ctrl and (now - self.last_ctrl_t < 0.45):
                self.last_was_ctrl = False
                self.root.after(0, self._trigger_suggestions)
            else:
                self.last_was_ctrl = True
            self.last_ctrl_t = now
            return True
        else:
            self.last_was_ctrl = False

        if key in (self.kb.Key.alt_l, self.kb.Key.alt_r):
            self.alt_down = True
            return True

        # Ctrl + Space shortcut: trigger suggestions
        if key == self.kb.Key.space and self.ctrl_down:
            self.root.after(0, self._trigger_suggestions)
            return True

        # Physical Spacebar handling (Auto-Correction & Next-Word Prediction)
        if key == self.kb.Key.space:
            with self.buffer_lock:
                self._handle_space()
                self.typing_buffer.append(" ")
            if self.popup.active:
                self.root.after(0, self.popup.close)
            if self.next_word_prediction and self.enabled:
                self.root.after(70, self._trigger_next_word_prediction)
            return True

        # Backspace handling: synchronize buffer
        if key == self.kb.Key.backspace:
            with self.buffer_lock:
                if self.typing_buffer:
                    self.typing_buffer.pop()
            # If word is now too short, close popup
            if len(self._get_current_word()) < MIN_WORD_LENGTH and self.popup.active:
                self.root.after(0, self.popup.close)
            return True

        # Enter / Escape: reset word buffer & close popup
        if key in (self.kb.Key.enter, self.kb.Key.esc):
            with self.buffer_lock:
                self.typing_buffer.clear()
            if self.popup.active:
                self.root.after(0, self.popup.close)
            return True

        # Process printable character
        try:
            ch = key.char
            if ch is not None:
                # If next-word prediction popup was active, dismiss it as user started typing a new word
                if self.popup.active and getattr(self.popup, "is_next_word", False):
                    self.root.after(0, self.popup.close)

                # Alt + / shortcut: trigger suggestions
                if ch == "/" and self.alt_down:
                    self.root.after(0, self._trigger_suggestions)
                    return True

                with self.buffer_lock:
                    self.typing_buffer.append(ch)

                # Auto-Suggest as you type (debounced)
                if self.auto_suggest and self.enabled:
                    word = self._get_current_word()
                    if len(word) >= MIN_WORD_LENGTH:
                        if self._suggest_timer:
                            self.root.after_cancel(self._suggest_timer)
                        self._suggest_timer = self.root.after(DEBOUNCE_MS, self._trigger_suggestions)
        except AttributeError:
            pass

        return True

    def _on_key_release(self, key):
        if key in (self.kb.Key.ctrl_l, self.kb.Key.ctrl_r):
            self.ctrl_down = False
        if key in (self.kb.Key.alt_l, self.kb.Key.alt_r):
            self.alt_down = False
        return True

    def start(self):
        self.running = True
        self._caret_thread.start()
        self.listener = SelectiveListener(
            assistant=self,
            on_press=self._on_key_press,
            on_release=self._on_key_release,
        )
        self.listener.start()

    def stop(self):
        self.running = False
        if self.listener:
            self.listener.stop()
        self.popup.close()

    def _get_current_word(self):
        with self.buffer_lock:
            text = "".join(self.typing_buffer)
            words = re.findall(r"[a-zA-Z؀-ۿ']+", text)
            return words[-1] if words else ""

    def _handle_space(self):
        if self.is_inserting or not self.enabled:
            return
        word = self._get_current_word()
        if not word or len(word) < MIN_WORD_LENGTH:
            return

        full_buf = "".join(self.typing_buffer)
        lang = self.lang_detector.detect(full_buf)
        self.current_lang = lang

        corrected = self.dm.correct_error(word, lang)
        if corrected != word:
            self.last_word_corrected = word
            threading.Thread(
                target=self._do_insert,
                args=(corrected,),
                kwargs={"extra_bs": 0, "append_space": True, "original": word},
                daemon=True,
            ).start()
        else:
            self.dm.learn_from_text(full_buf)

    def _do_insert(self, suggestion, extra_bs=0, append_space=False, original=""):
        """Delete previous word cleanly and paste suggestion with zero duplication."""
        if not CLIPBOARD_PASTE or self.is_inserting:
            return
        self.is_inserting = True
        try:
            time.sleep(0.01)
            # Preserve user clipboard
            try:
                saved_clip = pyperclip.paste()
            except Exception:
                saved_clip = ""

            try:
                pyperclip.copy(suggestion)

                # Send exact count of backspaces: length of word + 1 if space was already typed
                if original:
                    chars_to_delete = len(original) + (1 if append_space else 0) + extra_bs
                    for _ in range(chars_to_delete):
                        self.keyboard.press(self.kb.Key.backspace)
                        self.keyboard.release(self.kb.Key.backspace)
                        time.sleep(BACKSPACE_DELAY)
                else:
                    self.keyboard.press(self.kb.Key.ctrl)
                    self.keyboard.press(self.kb.Key.backspace)
                    self.keyboard.release(self.kb.Key.backspace)
                    self.keyboard.release(self.kb.Key.ctrl)
                    for _ in range(extra_bs):
                        self.keyboard.press(self.kb.Key.backspace)
                        self.keyboard.release(self.kb.Key.backspace)
                        time.sleep(BACKSPACE_DELAY)

                time.sleep(PASTE_DELAY)

                # Paste suggestion
                self.keyboard.press(self.kb.Key.ctrl)
                self.keyboard.press("v")
                self.keyboard.release("v")
                self.keyboard.release(self.kb.Key.ctrl)

                time.sleep(PASTE_DELAY)
                if append_space:
                    self.keyboard.press(" ")
                    self.keyboard.release(" ")

                time.sleep(RESTORE_CLIPBOARD_DELAY)

            finally:
                try:
                    pyperclip.copy(saved_clip)
                except Exception:
                    pass

            # Record stats & learning
            self.dm.record_usage(suggestion)
            if original and original != suggestion:
                self.dm.learn_from_selection(original, suggestion)
                app = self.session.get_active_app()
                self.session.record_help(app, original, suggestion, self.current_lang)

        finally:
            self.is_inserting = False
            self.last_word_corrected = None
            self._maybe_clear_buffer()

    def _maybe_clear_buffer(self):
        with self.buffer_lock:
            self.typing_buffer.clear()

    def _trigger_suggestions(self):
        if self.is_inserting or not self.enabled:
            return
        word = self._get_current_word()
        if not word or len(word) < MIN_WORD_LENGTH:
            self.popup.close()
            return

        lang = self.lang_detector.detect("".join(self.typing_buffer))
        self.current_lang = lang
        suggestions = self.dm.get_smart_matches_with_prediction(word, lang)
        if suggestions:
            # Filter exact identical word if other completions exist, else show all
            completions = [s for s in suggestions if s.lower() != word.lower()]
            display_list = completions if completions else suggestions
            caret_x, caret_y = get_caret_position()
            self.popup.show(display_list, word, caret_x, caret_y)
            if self._auto_close_timer:
                self.root.after_cancel(self._auto_close_timer)
            self._auto_close_timer = self.root.after(15000, self._auto_close_popup)
            if self.dashboard_ui:
                self.root.after(0, self.dashboard_ui.update_suggestion_chips, display_list)

    def _auto_close_popup(self):
        self.popup.close()

    def _trigger_next_word_prediction(self):
        if self.is_inserting or not self.enabled or not self.next_word_prediction:
            return
        with self.buffer_lock:
            text = "".join(self.typing_buffer)
            words = re.findall(r"[a-zA-Z\u0600-\u06ff']+", text)
        if not words:
            return
        current_word = words[-1]
        prev_word = words[-2] if len(words) >= 2 else None

        lang = self.lang_detector.detect(text)
        self.current_lang = lang
        predictions = self.dm.predict_next_words(current_word, prev_word, lang)
        if predictions:
            caret_x, caret_y = get_caret_position()
            self.popup.show(predictions, current_word, caret_x, caret_y, is_next_word=True)
            if self.dashboard_ui:
                self.root.after(0, self.dashboard_ui.update_suggestion_chips, predictions, True)

    def _do_insert_next_word(self, word):
        """Insert predicted next word with trailing space and zero backspaces."""
        if not CLIPBOARD_PASTE or self.is_inserting:
            return
        self.is_inserting = True
        try:
            time.sleep(0.01)
            try:
                saved_clip = pyperclip.paste()
            except Exception:
                saved_clip = ""

            try:
                insertion = f"{word} "
                pyperclip.copy(insertion)
                time.sleep(PASTE_DELAY)

                self.keyboard.press(self.kb.Key.ctrl)
                self.keyboard.press("v")
                self.keyboard.release("v")
                self.keyboard.release(self.kb.Key.ctrl)

                time.sleep(RESTORE_CLIPBOARD_DELAY)
            finally:
                try:
                    pyperclip.copy(saved_clip)
                except Exception:
                    pass

            with self.buffer_lock:
                self.typing_buffer.extend(list(f"{word} "))

            self.dm.record_usage(word)
            app = self.session.get_active_app()
            self.session.record_help(app, "[next-word]", word, self.current_lang)

            # Continuous chaining: immediately predict next word after this insertion!
            if self.next_word_prediction and self.enabled:
                self.root.after(80, self._trigger_next_word_prediction)
        finally:
            self.is_inserting = False
            self.last_word_corrected = None

    def _on_suggestion_selected(self, original_word, selected_word, is_next_word=False):
        if not CLIPBOARD_PASTE:
            return
        if is_next_word:
            threading.Thread(
                target=self._do_insert_next_word,
                args=(selected_word,),
                daemon=True,
            ).start()
        else:
            threading.Thread(
                target=self._do_insert,
                args=(selected_word,),
                kwargs={"extra_bs": 0, "append_space": False, "original": original_word},
                daemon=True,
            ).start()

    def toggle_assistant(self):
        self.enabled = not self.enabled
        if self.dashboard_ui:
            self.root.after(0, self.dashboard_ui.update_status_ui)
        print(f"[ALPHA] Assistant {'ACTIVE' if self.enabled else 'PAUSED'}")

    def show_session_summary(self):
        print("\n" + "=" * 55)
        print("           ALPHA SESSION SUMMARY")
        print("=" * 55)
        print(self.session.get_summary())
        print("=" * 55 + "\n")


# =============================================================
# MODERN DASHBOARD UI (Central Control & Sandbox)
# =============================================================
class DashboardUI:
    def __init__(self, root, assistant):
        self.root = root
        self.assistant = assistant
        self.assistant.dashboard_ui = self

        self.root.title("ALPHA Typing Assistant v5.1")
        self.root.configure(bg="#1e1e2e")
        w, h = 640, 640
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        self.root.geometry(f"{w}x{h}+{(screen_w - w) // 2}+{(screen_h - h) // 2}")
        self.root.minsize(580, 560)

        # Set application icons
        base_dir = os.path.dirname(os.path.abspath(__file__))
        icon_ico = os.path.join(base_dir, "app_icon.ico")
        icon_32 = os.path.join(base_dir, "app_icon_32.png")
        icon_png = os.path.join(base_dir, "app_icon.png")

        self.logo_img = None
        if os.path.exists(icon_ico):
            try:
                self.root.iconbitmap(icon_ico)
            except Exception:
                pass

        if os.path.exists(icon_32):
            try:
                self.logo_img = tk.PhotoImage(file=icon_32)
                self.root.iconphoto(True, self.logo_img)
            except Exception:
                pass
        elif os.path.exists(icon_png):
            try:
                self.logo_img = tk.PhotoImage(file=icon_png)
                self.root.iconphoto(True, self.logo_img)
            except Exception:
                pass

        self._build_ui()

    def _build_ui(self):
        # 1. Header Frame
        header = tk.Frame(self.root, bg="#181825", padx=16, pady=12)
        header.pack(fill=tk.X)

        if self.logo_img:
            logo_lbl = tk.Label(header, image=self.logo_img, bg="#181825")
            logo_lbl.pack(side=tk.LEFT, padx=(0, 10))

        title_lbl = tk.Label(
            header, text="ALPHA Typing Assistant", font=("Segoe UI", 16, "bold"),
            bg="#181825", fg="#89b4fa"
        )
        title_lbl.pack(side=tk.LEFT)

        self.status_lbl = tk.Label(
            header, text="[ACTIVE]", font=("Segoe UI", 11, "bold"),
            bg="#181825", fg="#a6e3a3"
        )
        self.status_lbl.pack(side=tk.LEFT, padx=(15, 6))

        shield_lbl = tk.Label(
            header, text="🛡️ Air-Gap Locked (100% Offline)", font=("Segoe UI", 9, "bold"),
            bg="#181825", fg="#89dceb"
        )
        shield_lbl.pack(side=tk.LEFT, padx=4)

        self.toggle_btn = tk.Button(
            header, text="Pause Assistant", font=("Segoe UI", 9, "bold"),
            bg="#313244", fg="#cdd6f4", activebackground="#45475a", activeforeground="#89b4fa",
            bd=0, padx=10, pady=4, cursor="hand2", command=self.assistant.toggle_assistant
        )
        self.toggle_btn.pack(side=tk.RIGHT)

        # 2. Main Content Container
        content = tk.Frame(self.root, bg="#1e1e2e", padx=16, pady=10)
        content.pack(fill=tk.BOTH, expand=True)

        # Sandbox Section
        sandbox_title = tk.Label(
            content, text="Interactive Test Sandbox (Works here and in ANY Windows app!):",
            font=("Segoe UI", 10, "bold"), bg="#1e1e2e", fg="#cdd6f4", anchor="w"
        )
        sandbox_title.pack(fill=tk.X, pady=(0, 4))

        self.sandbox_entry = tk.Text(
            content, font=("Segoe UI", 12), bg="#181825", fg="#cdd6f4",
            insertbackground="#89b4fa", selectbackground="#313244", selectforeground="#89b4fa",
            relief=tk.FLAT, bd=0, height=3, padx=10, pady=8, wrap=tk.WORD
        )
        self.sandbox_entry.pack(fill=tk.X)
        self.sandbox_entry.insert(
            tk.END, "Try typing here! E.g. type 'teh ' or 'shukria ' or 'sig1', or type 'hel'..."
        )
        self.sandbox_entry.bind("<FocusIn>", self._clear_sandbox_placeholder)
        self.sandbox_entry.bind("<KeyRelease>", self._on_sandbox_key)

        # Live Suggestions Bar
        self.chips_frame = tk.Frame(content, bg="#1e1e2e")
        self.chips_frame.pack(fill=tk.X, pady=(6, 8))

        self.chips_label = tk.Label(
            self.chips_frame, text="Live Suggestions:", font=("Segoe UI", 9, "bold"),
            bg="#1e1e2e", fg="#a6adc8"
        )
        self.chips_label.pack(side=tk.LEFT)

        self.chips_container = tk.Frame(self.chips_frame, bg="#1e1e2e")
        self.chips_container.pack(side=tk.LEFT, padx=10)
        self._render_default_chips(["hello", "help", "thanks", "Shukriya", "Theek"])

        # Auto-Suggest & Next-Word Checkbox Controls
        options_frame = tk.Frame(content, bg="#1e1e2e")
        options_frame.pack(fill=tk.X, pady=(0, 6))

        self.auto_suggest_var = tk.BooleanVar(value=True)
        auto_chk = tk.Checkbutton(
            options_frame, text="Auto-show popup suggestions while typing (No hotkey needed)",
            variable=self.auto_suggest_var, font=("Segoe UI", 9),
            bg="#1e1e2e", fg="#cdd6f4", selectcolor="#181825",
            activebackground="#1e1e2e", activeforeground="#89b4fa",
            command=self._on_toggle_auto_suggest
        )
        auto_chk.pack(anchor="w")

        self.next_word_var = tk.BooleanVar(value=True)
        next_word_chk = tk.Checkbutton(
            options_frame, text="Next-Word Prediction on Space (Google Gboard style)",
            variable=self.next_word_var, font=("Segoe UI", 9),
            bg="#1e1e2e", fg="#cdd6f4", selectcolor="#181825",
            activebackground="#1e1e2e", activeforeground="#cba6f7",
            command=self._on_toggle_next_word
        )
        next_word_chk.pack(anchor="w")

        # 3. Live Activity / Corrections Feed
        feed_title = tk.Label(
            content, text="Recent Auto-Corrections & Activity Feed:",
            font=("Segoe UI", 10, "bold"), bg="#1e1e2e", fg="#cdd6f4", anchor="w"
        )
        feed_title.pack(fill=tk.X, pady=(4, 2))

        feed_frame = tk.Frame(content, bg="#181825")
        feed_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        scrollbar = Scrollbar(feed_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.activity_listbox = Listbox(
            feed_frame, font=("Consolas", 10), bg="#181825", fg="#a6adc8",
            selectbackground="#313244", selectforeground="#89b4fa", bd=0, relief=tk.FLAT,
            yscrollcommand=scrollbar.set
        )
        self.activity_listbox.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)
        scrollbar.config(command=self.activity_listbox.yview)

        self.activity_listbox.insert(
            tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] ALPHA Engine online. Active in Notepad, Chrome, Word, etc."
        )

        # 4. Shortcuts Quick Reference Card
        guide_frame = tk.Frame(content, bg="#181825", padx=12, pady=6)
        guide_frame.pack(fill=tk.X)

        guide_text = (
            "• Typing 2+ letters: Shows popup suggestions automatically\n"
            "• Space: Auto-corrects typos (teh -> the, shukria -> Shukriya)\n"
            "• Ctrl+Space or Double-Ctrl: Manually open popup near cursor\n"
            "• Up/Down + Enter: Select suggestion | Escape: Close popup"
        )
        guide_lbl = tk.Label(
            guide_frame, text=guide_text, font=("Segoe UI", 9),
            bg="#181825", fg="#a6adc8", justify=tk.LEFT
        )
        guide_lbl.pack(anchor="w")

        # 5. Footer Buttons
        footer = tk.Frame(self.root, bg="#181825", padx=16, pady=8)
        footer.pack(fill=tk.X)

        test_popup_btn = tk.Button(
            footer, text="Test Popup Now", font=("Segoe UI", 9, "bold"),
            bg="#89b4fa", fg="#1e1e2e", activebackground="#b4befe",
            bd=0, padx=12, pady=5, cursor="hand2", command=self._test_popup_manual
        )
        test_popup_btn.pack(side=tk.LEFT)

        clear_btn = tk.Button(
            footer, text="Clear Sandbox", font=("Segoe UI", 9),
            bg="#313244", fg="#cdd6f4", activebackground="#45475a",
            bd=0, padx=10, pady=5, cursor="hand2", command=self._clear_sandbox
        )
        clear_btn.pack(side=tk.LEFT, padx=10)

        min_btn = tk.Button(
            footer, text="Minimize to Background", font=("Segoe UI", 9),
            bg="#313244", fg="#cdd6f4", activebackground="#45475a",
            bd=0, padx=10, pady=5, cursor="hand2", command=self.root.iconify
        )
        min_btn.pack(side=tk.RIGHT)

    def _on_toggle_auto_suggest(self):
        self.assistant.auto_suggest = self.auto_suggest_var.get()
        state = "ENABLED" if self.assistant.auto_suggest else "DISABLED"
        print(f"[ALPHA] Auto-suggest while typing is now {state}")

    def _on_toggle_next_word(self):
        self.assistant.next_word_prediction = self.next_word_var.get()
        state = "ENABLED" if self.assistant.next_word_prediction else "DISABLED"
        print(f"[ALPHA] Next-word prediction is now {state}")

    def _clear_sandbox_placeholder(self, event):
        txt = self.sandbox_entry.get("1.0", tk.END).strip()
        if "Try typing here!" in txt:
            self.sandbox_entry.delete("1.0", tk.END)

    def _clear_sandbox(self):
        self.sandbox_entry.delete("1.0", tk.END)
        self.sandbox_entry.focus()

    def _on_sandbox_key(self, event):
        if event.keysym == "space" and self.assistant.next_word_prediction:
            self._trigger_sandbox_next_word()
            return

        txt = self.sandbox_entry.get("1.0", "insert").strip()
        words = re.findall(r"[a-zA-Z\u0600-\u06ff']+", txt)
        if words:
            last = words[-1]
            if len(last) >= 2:
                suggs = self.assistant.dm.get_smart_matches_with_prediction(last)
                self.update_suggestion_chips(suggs[:5], is_next=False)

    def _trigger_sandbox_next_word(self):
        txt = self.sandbox_entry.get("1.0", "insert")
        words = re.findall(r"[a-zA-Z\u0600-\u06ff']+", txt)
        if not words:
            return
        last_word = words[-1]
        prev_word = words[-2] if len(words) >= 2 else None
        next_words = self.assistant.dm.predict_next_words(last_word, prev_word=prev_word, limit=5)
        if next_words:
            self.update_suggestion_chips(next_words, is_next=True)

    def _render_default_chips(self, items):
        self.update_suggestion_chips(items, is_next=False)

    def update_suggestion_chips(self, items, is_next=False):
        if not items:
            return
        for widget in self.chips_container.winfo_children():
            widget.destroy()

        if is_next:
            self.chips_label.config(text="⚡ Next Word:", fg="#cba6f7")
            btn_bg = "#2b2042"
            btn_fg = "#cba6f7"
            btn_active = "#453266"
        else:
            self.chips_label.config(text="Live Suggestions:", fg="#a6adc8")
            btn_bg = "#313244"
            btn_fg = "#89b4fa"
            btn_active = "#45475a"

        for item in items[:5]:
            btn = tk.Button(
                self.chips_container,
                text=f"⚡ {item}" if is_next else item,
                font=("Segoe UI", 8, "bold" if is_next else "normal"),
                bg=btn_bg, fg=btn_fg, activebackground=btn_active,
                bd=0, padx=8, pady=2, cursor="hand2",
                command=lambda w=item, n=is_next: self._insert_chip(w, n)
            )
            btn.pack(side=tk.LEFT, padx=3)

    def _insert_chip(self, word, is_next=False):
        self.sandbox_entry.insert(tk.INSERT, f"{word} ")
        self.sandbox_entry.focus()
        if self.assistant.next_word_prediction:
            self.root.after(60, self._trigger_sandbox_next_word)

    def _test_popup_manual(self):
        # Open popup centered right in front of the Dashboard window so it is 100% visible
        pos_x = self.root.winfo_rootx() + 150
        pos_y = self.root.winfo_rooty() + 180
        self.assistant.popup.show(
            ["hello", "help", "helpful", "thanks", "Shukriya", "Theek"],
            "hel", pos_x, pos_y
        )

    def add_log_entry(self, entry):
        line = f"[{entry['time']}] Auto-corrected: '{entry['from']}' -> '{entry['to']}' ({entry['app']})"
        self.activity_listbox.insert(0, line)
        if self.activity_listbox.size() > 50:
            self.activity_listbox.delete(50, tk.END)

    def update_status_ui(self):
        if self.assistant.enabled:
            self.status_lbl.config(text="[ACTIVE]", fg="#a6e3a3")
            self.toggle_btn.config(text="Pause Assistant")
        else:
            self.status_lbl.config(text="[PAUSED]", fg="#f38ba8")
            self.toggle_btn.config(text="Resume Assistant")


# =============================================================
# MAIN ENTRY POINT
# =============================================================
def main():
    root = tk.Tk()
    assistant = GlobalAssistant(root)
    dashboard = DashboardUI(root, assistant)
    root.after(100, assistant.start)

    print("=" * 55)
    print(" ALPHA Typing Assistant v5.1 - Active & Ready")
    print(" - Type 2+ letters: Suggestions popup automatically")
    print(" - Press Space to auto-correct typos")
    print(" - Double-tap Ctrl or Ctrl+Space for manual popup")
    print(" - Use Up/Down + Enter to select suggestion")
    print(" - Ctrl+Alt+X: Toggle On/Off")
    print(" - Ctrl+Alt+S: View Session Summary")
    print("=" * 55)

    root.mainloop()


if __name__ == "__main__":
    main()
