"""
Global Typing Assistant PRO — v3.2 (Language Detection + Roman Urdu Support)
Author: Moiz Digital Service
=====================================================================
New in v3.2:
  - Language Detection (English vs Roman Urdu vs Mixed)
  - Roman Urdu specific suggestions and corrections
  - Smart suggestions based on detected language
"""

import tkinter as tk
from tkinter import Listbox
import pyautogui
import pyperclip
import threading
import time
import json
import os
import re
import queue
import bisect
import ctypes
import difflib
from pynput import keyboard as pynput_keyboard
from collections import deque
from collections import Counter

# ══════════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════════
BASE_DIR           = os.path.dirname(os.path.abspath(__file__))
SUGGESTIONS_FILE   = os.path.join(BASE_DIR, "suggestions.json")
ERRORS_FILE        = os.path.join(BASE_DIR, "errors.json")
DICTIONARY_FILE    = os.path.join(BASE_DIR, "dictionary.json")
USER_LEARNING_FILE = os.path.join(BASE_DIR, "user_learning.json")
USAGE_STATS_FILE   = os.path.join(BASE_DIR, "usage_stats.json")

POPUP_WIDTH        = 320
POPUP_HEIGHT       = 220
MAX_SUGGESTIONS    = 10
MIN_WORD_LENGTH    = 2
DEBOUNCE_TIME      = 0.3
FOCUS_RETURN_DELAY = 0.15   
POLL_INTERVAL_MS   = 60
LEARN_MIN_LEN      = 4
LEARN_ALPHA_RATIO  = 0.7

# ══════════════════════════════════════════════════════════════════
# LANGUAGE DETECTOR
# ══════════════════════════════════════════════════════════════════
class LanguageDetector:
    """Detects if user is typing English, Roman Urdu, or Mixed"""
    
    # Common English words (small set for quick detection)
    ENGLISH_COMMON = {
        'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i',
        'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at',
        'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her', 'she',
        'will', 'my', 'one', 'all', 'would', 'there', 'their', 'what', 'so',
        'up', 'out', 'if', 'about', 'who', 'get', 'which', 'go', 'me', 'when',
        'make', 'can', 'like', 'time', 'no', 'just', 'him', 'know', 'take',
        'people', 'into', 'year', 'your', 'good', 'some', 'could', 'them',
        'see', 'other', 'than', 'then', 'now', 'look', 'only', 'come', 'its',
        'over', 'think', 'also', 'back', 'after', 'use', 'two', 'how', 'our',
        'work', 'first', 'well', 'way', 'even', 'new', 'want', 'because',
        'any', 'these', 'give', 'day', 'most', 'us', 'is', 'was', 'are'
    }
    
    # Common Roman Urdu words (used in everyday typing)
    ROMAN_URDU_COMMON = {
        'hai', 'hain', 'tha', 'thi', 'the', 'ho', 'hota', 'hoti', 'hoon',
        'mein', 'tum', 'wo', 'woh', 'yeh', 'ye', 'hum', 'aap', 'ap',
        'kya', 'kyun', 'kaise', 'kahan', 'kab', 'kitna', 'kitne', 'kitni',
        'nahi', 'haan', 'ji', 'sahi', 'galat', 'acha', 'bura', 'achha',
        'karna', 'jana', 'aana', 'dena', 'lena', 'bolna', 'dekhna', 'karna',
        'raha', 'rahi', 'rahe', 'chahiye', 'sakta', 'sakti', 'sakte',
        'baat', 'log', 'dil', 'pyar', 'mohabbat', 'dost', 'yaar', 'bhai',
        'saab', 'sahab', 'janab', 'mujhe', 'tujhe', 'usne', 'maine', 'tune',
        'lekin', 'magar', 'agar', 'toh', 'to', 'warna', 'nahi', 'mat',
        'bahut', 'bohat', 'zyada', 'kafi', 'thoda', 'thori', 'thore',
        'kal', 'aaj', 'aj', 'parson', 'daftar', 'ghar', 'school', 'college',
        'khana', 'peena', 'sona', 'jagna', 'parhna', 'likhna', 'samajhna'
    }
    
    # Character patterns for Roman Urdu (frequent consonant clusters)
    ROMAN_URDU_PATTERNS = {
        'h$', 'h[aeiou]', '[aeiou]h', 'h[aeiou]h',  # 'h' patterns
        'aa', 'ee', 'oo', 'ii', 'uu',                 # double vowels
        'bh', 'ch', 'dh', 'gh', 'jh', 'kh', 'ph', 'rh', 'sh', 'th', 'zh'
    }
    
    # English character patterns
    ENGLISH_PATTERNS = {
        'th', 'ng', 'ck', 'tion', 'sion', 'ing', 'ment', 'ness',
        'tion$', 'able$', 'ible$', 'ful$', 'less$'
    }
    
    def __init__(self):
        self.urdu_chars = set('ابپتٹثجچحخدڈذرزژسشصضطظعغفقکگلمنہوےؤئى')
    
    def detect(self, text):
        """
        Detect language of the current typing context.
        Returns: 'english', 'roman_urdu', 'urdu_script', or 'unknown'
        """
        if not text or len(text.strip()) < 2:
            return 'unknown'
        
        text = text.strip().lower()
        words = text.split()
        
        if not words:
            return 'unknown'
        
        last_word = words[-1]
        
        # Check 1: Contains Urdu script characters -> Definitely Urdu
        if any(ch in self.urdu_chars for ch in last_word):
            return 'urdu_script'
        
        # Check 2: Direct word matches (fastest)
        if last_word in self.ENGLISH_COMMON:
            return 'english'
        
        if last_word in self.ROMAN_URDU_COMMON:
            return 'roman_urdu'
        
        # Check 3: Pattern-based detection for unknown words
        eng_score = 0
        ru_score = 0
        
        # English patterns
        if re.search(r'(th|ng|ck|tion|ing|ment)$', last_word):
            eng_score += 2
        if re.search(r'(able|ible|ful|less)$', last_word):
            eng_score += 2
        
        # Roman Urdu patterns
        if re.search(r'h$', last_word):
            ru_score += 1
        if re.search(r'[aeiou]h[aeiou]', last_word):
            ru_score += 2
        if re.search(r'(bh|ch|dh|kh|ph|sh|th|zh)', last_word):
            ru_score += 1
        
        # Vowel analysis
        vowel_count = sum(1 for ch in last_word if ch in 'aeiou')
        vowel_ratio = vowel_count / max(len(last_word), 1)
        
        # English tends to have more vowels relative to length
        if vowel_ratio > 0.35:
            eng_score += 1
        else:
            ru_score += 1
        
        # Length analysis
        if len(last_word) >= 6:
            # Long words are more likely English
            eng_score += 1
        
        # Final decision with threshold
        if eng_score >= ru_score + 1:
            return 'english'
        elif ru_score >= eng_score + 1:
            return 'roman_urdu'
        else:
            # Ambiguous - check against common word lists
            return self._resolve_ambiguous(last_word)
    
    def _resolve_ambiguous(self, word):
        """Resolve ambiguous cases by checking frequency"""
        # Common Roman Urdu words that might be ambiguous
        ru_words = {'ap', 'to', 'hai', 'ho', 'tu', 'hi', 'he', 'so', 'do', 'ko', 'se', 'pe'}
        eng_words = {'as', 'is', 'it', 'at', 'on', 'in', 'of', 'to', 'for', 'by', 'be'}
        
        if word in ru_words:
            return 'roman_urdu'
        if word in eng_words:
            return 'english'
        
        # Default to English for technical words
        if len(word) > 5 and word.isalpha():
            return 'english'
        
        return 'roman_urdu'
    
    def get_confidence(self, text):
        """Return confidence score for detection (0-1)"""
        words = text.lower().split()
        if not words:
            return 0.0
        
        last_word = words[-1]
        if last_word in self.ENGLISH_COMMON:
            return 0.95
        if last_word in self.ROMAN_URDU_COMMON:
            return 0.95
        
        return 0.7  # Default confidence for pattern-based detection


# ══════════════════════════════════════════════════════════════════
# ROMAN URDU CORRECTION MAPS
# ══════════════════════════════════════════════════════════════════
ROMAN_URDU_ERRORS = {
    # Common Roman Urdu typos
    'mei': 'mein', 'mai': 'mein', 'men': 'mein', 'min': 'mein',
    'nhe': 'nahi', 'nai': 'nahi', 'nhi': 'nahi', 'nihi': 'nahi',
    'karta': 'karta', 'kerti': 'karti', 'kerta': 'karta', 'kerta': 'karta',
    'chahta': 'chahata', 'chata': 'chahata', 'chata': 'chahata',
    'hu': 'hoon', 'hon': 'hoon', 'hun': 'hoon',
    'raha': 'raha', 'reha': 'raha', 'raha': 'raha',
    'sakta': 'sakta', 'sekta': 'sakta', 'sakta': 'sakta',
    'ap': 'aap', 'aap': 'aap',
    'wo': 'woh', 'woh': 'woh', 'vo': 'woh',
    'ye': 'yeh', 'yeh': 'yeh', 'ya': 'yeh',
    'iska': 'is ka', 'uska': 'us ka', 'mera': 'mera', 'tera': 'tera',
    'krna': 'karna', 'krna': 'karna', 'karna': 'karna',
    'jana': 'jana', 'jana': 'jana', 'jna': 'jana',
    'ana': 'aana', 'aana': 'aana', 'ana': 'aana',
    'dena': 'dena', 'lena': 'lena', 'bolna': 'bolna',
    'dekhna': 'dekhna', 'kaha': 'kahan', 'kahan': 'kahan',
    'kitna': 'kitna', 'kitni': 'kitni', 'kitne': 'kitne',
    'bhot': 'bohat', 'bohot': 'bohat', 'bhut': 'bohat',
    'zyda': 'zyada', 'ziada': 'zyada', 'zyada': 'zyada',
    'thoda': 'thoda', 'thori': 'thori', 'thore': 'thore',
    'kal': 'kal', 'aaj': 'aaj', 'aj': 'aaj',
    'ghr': 'ghar', 'ghar': 'ghar', 'gr': 'ghar',
    'skool': 'school', 'scool': 'school', 'school': 'school',
    'clg': 'college', 'college': 'college', 'cllg': 'college',
    'daftr': 'daftar', 'daftar': 'daftar',
    'khna': 'khana', 'khana': 'khana',
    'pyna': 'peena', 'peena': 'peena', 'pina': 'peena',
    'sona': 'sona', 'jagna': 'jagna',
    'prhna': 'parhna', 'parhna': 'parhna', 'prhna': 'parhna',
    'likhna': 'likhna', 'smjna': 'samajhna', 'samjhna': 'samajhna'
}

# Roman Urdu suggestions for common prefixes
ROMAN_URDU_SUGGESTIONS = {
    'm': ['mein', 'mujhe', 'mera', 'main', 'magar'],
    't': ['tum', 'tujhe', 'tera', 'toh', 'tha'],
    'w': ['woh', 'wahan', 'warna', 'wapis'],
    'k': ['kya', 'kaise', 'kahan', 'kab', 'kitna', 'karna'],
    'h': ['hai', 'hain', 'hoon', 'hota', 'hum', 'haan'],
    'a': ['aap', 'acha', 'aaj', 'aana', 'agar'],
    'b': ['bahut', 'baat', 'bhai', 'bolna', 'bura'],
    's': ['sahi', 'sakta', 'samajh', 'sona', 'school'],
    'p': ['pyar', 'parhna', 'peena', 'phir'],
    'd': ['dil', 'dost', 'dena', 'dekhna', 'daftar']
}


# ══════════════════════════════════════════════════════════════════
# CARET POSITION (Windows API)
# ══════════════════════════════════════════════════════════════════
class _RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

class _GUITHREADINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize",        ctypes.c_uint32), ("flags",         ctypes.c_uint32),
        ("hwndActive",    ctypes.c_size_t), ("hwndFocus",     ctypes.c_size_t),
        ("hwndCapture",   ctypes.c_size_t), ("hwndMenuOwner", ctypes.c_size_t),
        ("hwndMoveSize",  ctypes.c_size_t), ("hwndCaret",     ctypes.c_size_t),
        ("rcCaret",       _RECT),
    ]

class _POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

def get_caret_position():
    try:
        info = _GUITHREADINFO()
        info.cbSize = ctypes.sizeof(_GUITHREADINFO)
        if ctypes.windll.user32.GetGUIThreadInfo(0, ctypes.byref(info)):
            hwnd = info.hwndCaret
            if hwnd:
                pt = _POINT(info.rcCaret.left, info.rcCaret.bottom)
                ctypes.windll.user32.ClientToScreen(hwnd, ctypes.byref(pt))
                if pt.x > 0 and pt.y > 0:
                    return pt.x, pt.y
    except Exception:
        pass
    try:
        return pyautogui.position()
    except Exception:
        return 300, 300


# ══════════════════════════════════════════════════════════════════
# DATA MANAGER & DICTIONARY
# ══════════════════════════════════════════════════════════════════
class DictIndex:
    def __init__(self, words):
        self._words = sorted(set(w for w in words if len(w) >= 2), key=str.lower)
        self._keys  = [w.lower() for w in self._words]

    def prefix_search(self, prefix, limit=15):
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

    def exact_match(self, word):
        word_l = word.lower()
        lo = bisect.bisect_left(self._keys, word_l)
        return lo < len(self._keys) and self._keys[lo] == word_l


class DataManager:
    def __init__(self):
        self.suggestions   = self._load_json(SUGGESTIONS_FILE, {})
        self.user_learning = self._load_json(USER_LEARNING_FILE, {})
        self.usage_stats   = self._load_json(USAGE_STATS_FILE, {})
        self.dict_index    = self._build_dict_index()
        
        raw_errors = self._load_json(ERRORS_FILE, {})
        self.errors = {k.strip().lower(): v.strip() for k, v in raw_errors.items() if k.strip()}
        
        # Roman Urdu learning store
        self.ru_learning = self._load_json(os.path.join(BASE_DIR, "ru_learning.json"), {})

    @staticmethod
    def _load_json(path, default):
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return default
        except Exception:
            return default

    def _build_dict_index(self):
        raw = self._load_json(DICTIONARY_FILE, [])
        return DictIndex(raw) if isinstance(raw, list) and raw else None

    def get_all_custom_words(self):
        words = []
        for cat_words in self.suggestions.values():
            words.extend(cat_words)
        return words

    def correct_error(self, word, lang='english'):
        """Correct error based on language"""
        w = word.lower()
        
        if lang == 'roman_urdu':
            # Check Roman Urdu error map first
            if w in ROMAN_URDU_ERRORS:
                return ROMAN_URDU_ERRORS[w]
            
            # Check learned Roman Urdu words
            if w in self.ru_learning and self.ru_learning[w] > 2:
                return w
            
            # Check user learning
            if w in self.user_learning and self.user_learning[w] > 2:
                return w
            
            # Fuzzy match for Roman Urdu
            if len(w) >= 3:
                matches = difflib.get_close_matches(w, ROMAN_URDU_ERRORS.keys(), n=1, cutoff=0.75)
                if matches:
                    return ROMAN_URDU_ERRORS[matches[0]]
            
            return word  # No correction
        
        else:  # English
            if w in self.errors:
                return self.errors[w]
            if len(w) >= 4:
                matches = difflib.get_close_matches(w, self.errors.keys(), n=1, cutoff=0.78)
                if matches:
                    return self.errors[matches[0]]
            return word

    def get_word_weight(self, word):
        w = word.lower()
        return self.user_learning.get(w, 0) + self.usage_stats.get(w, 0)
    
    def get_ru_word_weight(self, word):
        w = word.lower()
        return self.ru_learning.get(w, 0)

    def get_smart_matches(self, prefix, lang='english'):
        """Get smart matches based on language"""
        if not prefix or len(prefix) < MIN_WORD_LENGTH:
            return []
        
        prefix_l = prefix.lower()
        seen = set()
        results = []
        
        if lang == 'roman_urdu':
            # Roman Urdu specific suggestions
            # 1. Prefix-based suggestions from ROMAN_URDU_SUGGESTIONS
            first_char = prefix_l[0] if prefix_l else ''
            if first_char in ROMAN_URDU_SUGGESTIONS:
                for w in ROMAN_URDU_SUGGESTIONS[first_char]:
                    if w.startswith(prefix_l) and w not in seen:
                        seen.add(w)
                        results.append((w, 150))
            
            # 2. Learned Roman Urdu words
            for w, count in sorted(self.ru_learning.items(), key=lambda x: x[1], reverse=True):
                if w.startswith(prefix_l) and w not in seen and count > 2:
                    seen.add(w)
                    results.append((w, count + 100))
            
            # 3. User learning (might contain Roman Urdu)
            for w, count in sorted(self.user_learning.items(), key=lambda x: x[1], reverse=True):
                if w.startswith(prefix_l) and w not in seen and count > 3:
                    seen.add(w)
                    results.append((w, count + 50))
            
            # 4. Common Roman Urdu words from ROMAN_URDU_ERRORS
            for w in ROMAN_URDU_ERRORS.keys():
                if w.startswith(prefix_l) and w not in seen:
                    seen.add(w)
                    results.append((w, 80))
            
            # 5. Also add corrected versions as suggestions
            for wrong, correct in ROMAN_URDU_ERRORS.items():
                if correct.startswith(prefix_l) and correct not in seen:
                    seen.add(correct)
                    results.append((correct, 70))
        
        else:  # English
            # Existing English logic
            for w in self.get_all_custom_words():
                if w.lower().startswith(prefix_l) or prefix_l in w.lower():
                    if w not in seen:
                        seen.add(w)
                        results.append((w, self.get_word_weight(w) + 100))

            for w, count in sorted(self.user_learning.items(), key=lambda x: x[1], reverse=True):
                if w.lower().startswith(prefix_l) and w not in seen:
                    seen.add(w)
                    results.append((w, count + 50))

            if self.dict_index:
                for w in self.dict_index.prefix_search(prefix_l, limit=20):
                    if w not in seen:
                        seen.add(w)
                        results.append((w, self.get_word_weight(w)))
        
        results.sort(key=lambda x: x[1], reverse=True)
        return [w for w, _ in results[:MAX_SUGGESTIONS]]
    
    # @property
    # def ROMAN_URDU_COMMON_LIST(self):
    #     return list(ROMAN_URDU_ERRORS.keys()) + list(ROMAN_URDU_SUGGESTIONS.values())

    def learn_word(self, word, lang='english'):
        """Learn word based on language"""
        w = word.lower()
        
        if lang == 'roman_urdu':
            self.ru_learning[w] = self.ru_learning.get(w, 0) + 1
            if self.ru_learning[w] % 5 == 0:
                self._save_json(os.path.join(BASE_DIR, "ru_learning.json"), self.ru_learning)
        else:
            self.user_learning[w] = self.user_learning.get(w, 0) + 1
            if self.user_learning[w] % 5 == 0:
                self._save_json(USER_LEARNING_FILE, self.user_learning)

    def record_usage(self, word):
        w = word.lower()
        self.usage_stats[w] = self.usage_stats.get(w, 0) + 1
        self._save_json(USAGE_STATS_FILE, self.usage_stats)

    @staticmethod
    def _save_json(path, data):
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════
# SUGGESTION POPUP
# ══════════════════════════════════════════════════════════════════
class SuggestionPopup:
    def __init__(self, root, on_select_callback):
        self.root = root
        self.on_select = on_select_callback
        self.top = None
        self.listbox = None
        self.suggestions = []
        self.current_word = ""
        self.active = False

    def show(self, suggestions, word, x, y):
        if not suggestions:
            self.close()
            return
        self.suggestions = suggestions
        self.current_word = word
        screen_w = self.root.winfo_screenwidth()
        popup_x = min(x, screen_w - POPUP_WIDTH - 10)
        popup_y = y + 4

        if self.top is None:
            self.top = tk.Toplevel(self.root)
            self.top.title(" ")
            self.top.attributes('-topmost', True)
            self.top.overrideredirect(True)
            self.top.configure(bg="#1e1e2e")
            self.listbox = Listbox(self.top, font=("Segoe UI", 11), selectmode=tk.SINGLE,
                                   bg="#1e1e2e", fg="#cdd6f4", selectbackground="#313244",
                                   selectforeground="#89b4fa", activestyle='none',
                                   bd=0, highlightthickness=1, highlightbackground="#45475a")
            self.listbox.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
            self.listbox.bind('<ButtonRelease-1>', self._on_mouse_click)
            self.top.bind('<Escape>', lambda e: self.close())
            self.active = True
        else:
            self.top.lift()

        visible = min(len(suggestions), 8)
        h = visible * 28 + 8
        self.top.geometry(f"{POPUP_WIDTH}x{h}+{popup_x}+{popup_y}")
        self.listbox.delete(0, tk.END)
        for item in self.suggestions:
            display_item = f"  {item}"
            self.listbox.insert(tk.END, display_item)
        self.listbox.select_set(0)
        self.listbox.activate(0)

    def _on_mouse_click(self, event):
        idx = self.listbox.nearest(event.y)
        if 0 <= idx < len(self.suggestions):
            self.close()
            self.on_select(self.current_word, self.suggestions[idx], extra_bs=0)

    def select_next(self):
        if not self.listbox or not self.suggestions: return
        idx = self.listbox.curselection()
        if idx and idx[0] < len(self.suggestions) - 1:
            new = idx[0] + 1
            self.listbox.select_clear(idx[0]); self.listbox.select_set(new)
            self.listbox.activate(new); self.listbox.see(new)
        elif not idx:
            self.listbox.select_set(0); self.listbox.activate(0)

    def select_prev(self):
        if not self.listbox or not self.suggestions: return
        idx = self.listbox.curselection()
        if idx and idx[0] > 0:
            new = idx[0] - 1
            self.listbox.select_clear(idx[0]); self.listbox.select_set(new)
            self.listbox.activate(new); self.listbox.see(new)

    def confirm_selected(self, key_used='enter'):
        if not self.listbox or not self.suggestions: return
        idx = self.listbox.curselection()
        if idx:
            self.close()
            self.on_select(self.current_word, self.suggestions[idx[0]], extra_bs=0)

    def close(self):
        self.active = False
        if self.top:
            try: self.top.destroy()
            except tk.TclError: pass
            self.top = None; self.listbox = None


# ══════════════════════════════════════════════════════════════════
# GLOBAL ASSISTANT
# ══════════════════════════════════════════════════════════════════
class GlobalAssistant:
    def __init__(self):
        self.dm = DataManager()
        self.lang_detector = LanguageDetector()
        self.keyboard_controller = pynput_keyboard.Controller()
        self.enabled = True
        self.is_inserting = False
        self.last_ctrl_t = 0
        self.typing_buffer = deque(maxlen=80)
        self.event_queue = queue.Queue()
        self.listener = None
        self.root = tk.Tk()
        self.root.withdraw()
        self.popup = SuggestionPopup(self.root, self._resolve_suggestion)
        self.current_language = 'unknown'
        self.lang_confidence = 0.0

    def _get_current_word(self):
        text = ''.join(self.typing_buffer)
        words = re.findall(r"[a-zA-Z\u0600-\u06FF']+", text)
        return words[-1] if words else ""

    def _detect_language(self):
        """Detect language from typing buffer"""
        text = ''.join(self.typing_buffer)
        if len(text.strip()) < 3:
            return 'unknown', 0.0
        
        lang = self.lang_detector.detect(text)
        confidence = self.lang_detector.get_confidence(text)
        return lang, confidence

    def _get_suggestions_by_language(self, word, lang):
        """Get suggestions based on detected language"""
        suggestions = []
        
        if lang == 'english':
            # English: Check error correction
            corrected = self.dm.correct_error(word, lang='english')
            if corrected != word:
                suggestions.append(f"[Fix] {corrected}")
            
            # Smart matches
            matches = self.dm.get_smart_matches(word, lang='english')
            for m in matches:
                if m.lower() != word.lower():
                    suggestions.append(m)
        
        elif lang == 'roman_urdu':
            # Roman Urdu: Special handling
            
            # 1. Check Roman Urdu error correction
            corrected = self.dm.correct_error(word, lang='roman_urdu')
            if corrected != word:
                suggestions.append(f"[RU] {corrected}")
            
            # 2. Get smart matches for Roman Urdu
            matches = self.dm.get_smart_matches(word, lang='roman_urdu')
            for m in matches:
                if m.lower() != word.lower() and m not in suggestions:
                    suggestions.append(m)
            
            # 3. If word is already common, mark it
            if word in ROMAN_URDU_ERRORS.values():
                if word not in suggestions:
                    suggestions.insert(0, f"✓ {word}")
        
        elif lang == 'urdu_script':
            # Urdu script (if you want to support full Urdu)
            suggestions.append(f"[Urdu] {word}")
        
        return suggestions[:MAX_SUGGESTIONS]

    def _resolve_suggestion(self, original_word, raw_selection, extra_bs=0):
        # Remove prefixes like "[Fix] ", "[RU] ", "✓ "
        suggestion = raw_selection
        if raw_selection.startswith("[Fix] "):
            suggestion = raw_selection[6:]
        elif raw_selection.startswith("[RU] "):
            suggestion = raw_selection[5:]
        elif raw_selection.startswith("✓ "):
            suggestion = raw_selection[2:]
        
        self._apply_suggestion(original_word, suggestion, extra_bs)

    def _apply_suggestion(self, original_word, suggestion, extra_bs=0):
        self.typing_buffer.clear()
        self.is_inserting = True
        self.dm.record_usage(suggestion.strip())
        threading.Thread(target=self._do_insert, args=(original_word, suggestion, extra_bs), daemon=True).start()

    def _do_insert(self, original_word, suggestion, extra_bs=0):
        old_pause = pyautogui.PAUSE
        try:
            time.sleep(FOCUS_RETURN_DELAY)
            pyautogui.PAUSE = 0
            total_bs = len(original_word) + extra_bs
            pyautogui.press('backspace', presses=total_bs)
            old_clip = ""
            try: old_clip = pyperclip.paste()
            except: pass
            pyperclip.copy(suggestion)
            pyautogui.hotkey('ctrl', 'v')
            try: pyperclip.copy(old_clip)
            except: pass
        except Exception as e:
            print(f"[Insert] Error: {e}")
        finally:
            pyautogui.PAUSE = old_pause
            self.is_inserting = False
            self.typing_buffer.clear()

    # 🛑 CORE OS BLOCKER + DIRECT NAVIGATION ROUTER 🛑
    def _win32_event_filter(self, msg, data):
        if self.popup and self.popup.active:
            if data.vkCode in (13, 9, 27, 38, 40):
                if msg == 256:
                    if data.vkCode == 13:   self.event_queue.put(('popup_confirm', 'enter'))
                    elif data.vkCode == 9:  self.event_queue.put(('popup_confirm', 'tab'))
                    elif data.vkCode == 38: self.event_queue.put(('popup_up',))
                    elif data.vkCode == 40: self.event_queue.put(('popup_down',))
                    elif data.vkCode == 27: self.event_queue.put(('popup_close',))
                return False  # Don't let pynput process suppressed keys
        return True

    def on_press(self, key):
        if self.is_inserting:
            return True
        try:
            if key in (pynput_keyboard.Key.ctrl_l, pynput_keyboard.Key.ctrl_r):
                now = time.time()
                if now - self.last_ctrl_t < DEBOUNCE_TIME:
                    self.event_queue.put(('force_show',))
                self.last_ctrl_t = now
                return True

            if key in (pynput_keyboard.Key.left, pynput_keyboard.Key.right):
                self.typing_buffer.clear()
                self.event_queue.put(('popup_close',))
                return True

            if not self.enabled: return True

            if hasattr(key, 'char') and key.char is not None and ord(key.char) >= 32:
                self.typing_buffer.append(key.char)
                self.event_queue.put(('suggest', self._get_current_word()))

            elif key == pynput_keyboard.Key.space:
                word = self._get_current_word()
                if word:
                    # Detect language for this word
                    lang, _ = self._detect_language()
                    corrected = self.dm.correct_error(word, lang=lang)
                    
                    if corrected != word:
                        self.typing_buffer.clear()
                        self.event_queue.put(('popup_close',))
                        # Add space after correction if needed
                        space_suffix = " " if not corrected.endswith(" ") else ""
                        self._apply_suggestion(word, corrected + space_suffix, extra_bs=1)
                        return True
                    else:
                        # Learn the word with language context
                        self.dm.learn_word(word, lang=lang)
                self.typing_buffer.clear()
                self.event_queue.put(('popup_close',))

            elif key == pynput_keyboard.Key.backspace:
                if self.typing_buffer: self.typing_buffer.pop()
                self.event_queue.put(('suggest', self._get_current_word()))

            elif key == pynput_keyboard.Key.enter:
                word = self._get_current_word()
                if word:
                    lang, _ = self._detect_language()
                    self.dm.learn_word(word, lang=lang)
                self.typing_buffer.clear()
                self.event_queue.put(('popup_close',))

        except AttributeError: pass
        except Exception as e: print(f"[on_press] {e}")
        return True

    def _poll_queue(self):
        try:
            while True:
                event = self.event_queue.get_nowait()
                cmd = event[0] if isinstance(event, tuple) else event
                
                if cmd == 'suggest':
                    if not self.enabled:
                        self.popup.close()
                    else:
                        word = event[1] if len(event) > 1 else self._get_current_word()
                        
                        if len(word) >= MIN_WORD_LENGTH:
                            # Detect language for suggestions
                            self.current_language, self.lang_confidence = self._detect_language()
                            
                            # Get language-specific suggestions
                            final_list = self._get_suggestions_by_language(word, self.current_language)
                            
                            if final_list:
                                x, y = get_caret_position()
                                self.popup.show(final_list[:MAX_SUGGESTIONS], word, x, y)
                            else:
                                self.popup.close()
                        else:
                            self.popup.close()
                            
                elif cmd == 'force_show':
                    word = self._get_current_word()
                    if word and self.enabled:
                        self.current_language, _ = self._detect_language()
                        final_list = self._get_suggestions_by_language(word, self.current_language)
                        if final_list:
                            x, y = get_caret_position()
                            self.popup.show(final_list[:MAX_SUGGESTIONS], word, x, y)
                            
                elif cmd == 'popup_down': self.popup.select_next()
                elif cmd == 'popup_up': self.popup.select_prev()
                elif cmd == 'popup_confirm': self.popup.confirm_selected()
                elif cmd == 'popup_close': self.popup.close()
                
        except queue.Empty: pass
        finally:
            self.root.after(POLL_INTERVAL_MS, self._poll_queue)

    def show_splash(self):
        splash = tk.Toplevel(self.root)
        splash.title("Alpha")
        splash.overrideredirect(True)
        splash.attributes('-topmost', True)
        
        w, h = 500, 300
        sw, sh = splash.winfo_screenwidth(), splash.winfo_screenheight()
        splash.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
        
        canvas = tk.Canvas(splash, width=w, height=h, bg="#0d1117", highlightthickness=0)
        canvas.pack()
        
        # Main title
        canvas.create_text(w//2, 60, text="ALPHA", fill="#ffffff", 
                          font=("Segoe UI", 52, "bold"))
        canvas.create_text(w//2, 100, text="INTELLIGENT TYPING ASSISTANT", 
                          fill="#58a6ff", font=("Segoe UI", 12, "bold"))
        
        # Tagline
        canvas.create_text(w//2, 140, text="State of the Art Language Detection", 
                          fill="#00ff88", font=("Segoe UI", 11))
        
        # Feature highlights
        features = "✨ English • 🔤 Roman Urdu • 📜 Urdu Script"
        canvas.create_text(w//2, 180, text=features, fill="#8b949e", font=("Segoe UI", 10))
        
        canvas.create_line(100, 200, w-100, 200, fill="#30363d", width=1)
        
        # Status
        canvas.create_text(w//2, 225, text="✓ System Ready", 
                          fill="#49f1a6", font=("Segoe UI", 10, "bold"))
        canvas.create_text(w//2, 250, text="Moiz Digital Service", 
                          fill="#6e7681", font=("Segoe UI", 9))
        
        # Animated dot
        def animate_dot():
            for i in range(3):
                splash.after(i * 500, lambda: canvas.itemconfig(7, text="✓ System Ready" + "." * (i + 1)))
        animate_dot()
        
        splash.bind("<Button-1>", lambda e: splash.destroy())
        splash.after(4000, splash.destroy)

    def start(self):
        print("=" * 60)
        print("  ⌨️  Global Typing Assistant PRO v3.2 — Language Detection + Roman Urdu!")
        print("=" * 60)
        print("  Features:")
        print("  - English & Roman Urdu detection (automatic)")
        print("  - Context-aware suggestions")
        print("  - Language-specific corrections")
        print("=" * 60)
        
        self.show_splash()
        
        self.listener = pynput_keyboard.Listener(
            on_press=self.on_press, 
            win32_event_filter=self._win32_event_filter,
            suppress=False
        )
        self.listener.daemon = True
        self.listener.start()
        time.sleep(0.2)
        
        print(f"  [Listener] {'✅ Active' if self.listener.running else '❌ FAILED — Run as Admin'}")
        print("  [Language Detection] ✅ Ready")
        print("=" * 60)
        
        self.root.after(POLL_INTERVAL_MS, self._poll_queue)
        try:
            self.root.mainloop()
        except KeyboardInterrupt: pass
        except Exception as e:
            print(f"[App] Error: {e}")
            import traceback; traceback.print_exc()
        finally:
            self.popup.close()
            self.listener.stop()
            DataManager._save_json(USER_LEARNING_FILE, self.dm.user_learning)
            DataManager._save_json(USAGE_STATS_FILE, self.dm.usage_stats)
            print("[App] Goodbye!")

if __name__ == "__main__":
    assistant = GlobalAssistant()
    assistant.start()