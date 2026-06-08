"""
Global Typing Assistant PRO — v3.3 (Ultimate Compatibility + Performance)
Author: Moiz Digital Service
=====================================================================
v3.3 Features:
  - Universal app compatibility (browser, VS Code, Word, Notepad, games)
  - Blazing fast suggestions (optimized lookups)
  - Minimal console output (only essential info)
  - Smart language detection (English + Roman Urdu)
  - Auto-learning user habits
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

# =============================================================
# CONFIGURATION
# =============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# File paths
SUGGESTIONS_FILE   = os.path.join(BASE_DIR, "suggestions.json")
ERRORS_FILE        = os.path.join(BASE_DIR, "errors.json")
DICTIONARY_FILE    = os.path.join(BASE_DIR, "dictionary.json")
USER_LEARNING_FILE = os.path.join(BASE_DIR, "user_learning.json")
USAGE_STATS_FILE   = os.path.join(BASE_DIR, "usage_stats.json")

# Performance settings
POPUP_WIDTH        = 320
MAX_SUGGESTIONS    = 8
MIN_WORD_LENGTH    = 2
DEBOUNCE_TIME      = 0.3
FOCUS_RETURN_DELAY = 0.12
POLL_INTERVAL_MS   = 50
BACKSPACE_DELAY    = 0.003

# =============================================================
# LANGUAGE DETECTION
# =============================================================
class LanguageDetector:
    """Fast language detection for English vs Roman Urdu"""
    
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
    
    ROMAN_URDU_COMMON = {
        'hai', 'hain', 'tha', 'thi', 'the', 'ho', 'hota', 'hoti', 'hoon',
        'mein', 'tum', 'wo', 'woh', 'yeh', 'ye', 'hum', 'aap', 'ap',
        'kya', 'kyun', 'kaise', 'kahan', 'kab', 'kitna', 'kitne', 'kitni',
        'nahi', 'haan', 'ji', 'sahi', 'galat', 'acha', 'bura', 'achha',
        'karna', 'jana', 'aana', 'dena', 'lena', 'bolna', 'dekhna',
        'raha', 'rahi', 'rahe', 'chahiye', 'sakta', 'sakti', 'sakte',
        'baat', 'log', 'dil', 'pyar', 'dost', 'yaar', 'bhai', 'mujhe',
        'lekin', 'magar', 'agar', 'toh', 'to', 'warna', 'mat', 'bahut',
        'bohat', 'zyada', 'kafi', 'thoda', 'thori', 'thore', 'kal', 'aaj',
        'daftar', 'ghar', 'school', 'college', 'khana', 'peena', 'sona'
    }
    
    def __init__(self):
        self.urdu_chars = set('ابپتٹثجچحخدڈذرزژسشصضطظعغفقکگلمنہوےؤئى')
    
    def detect(self, text):
        """Returns: 'english', 'roman_urdu', 'urdu_script'"""
        if not text or len(text.strip()) < 2:
            return 'unknown'
        
        text = text.strip().lower()
        words = text.split()
        if not words:
            return 'unknown'
        
        last_word = words[-1]
        
        # Urdu script detection
        if any(ch in self.urdu_chars for ch in last_word):
            return 'urdu_script'
        
        # Direct matches
        if last_word in self.ENGLISH_COMMON:
            return 'english'
        if last_word in self.ROMAN_URDU_COMMON:
            return 'roman_urdu'
        
        # Pattern-based detection
        if re.search(r'(th|ng|ck|tion|ing|ment)$', last_word):
            return 'english'
        if re.search(r'h$', last_word) or re.search(r'(bh|ch|dh|kh|ph|sh|th|zh)', last_word):
            return 'roman_urdu'
        
        return 'english'


# =============================================================
# ROMAN URDU CORRECTIONS
# =============================================================
ROMAN_URDU_CORRECTIONS = {
    'mei': 'mein', 'mai': 'mein', 'men': 'mein', 'min': 'mein',
    'nhe': 'nahi', 'nai': 'nahi', 'nhi': 'nahi', 'nihi': 'nahi',
    'karta': 'karta', 'kerti': 'karti', 'kerta': 'karta',
    'chahta': 'chahata', 'chata': 'chahata',
    'hu': 'hoon', 'hon': 'hoon', 'hun': 'hoon',
    'raha': 'raha', 'reha': 'raha',
    'sakta': 'sakta', 'sekta': 'sakta',
    'ap': 'aap', 'wo': 'woh', 'vo': 'woh', 'ye': 'yeh', 'ya': 'yeh',
    'krna': 'karna', 'jna': 'jana', 'ana': 'aana',
    'bhot': 'bohat', 'bohot': 'bohat', 'bhut': 'bohat',
    'zyda': 'zyada', 'ziada': 'zyada',
    'ghr': 'ghar', 'gr': 'ghar',
    'skool': 'school', 'scool': 'school',
    'clg': 'college', 'cllg': 'college',
    'daftr': 'daftar', 'khna': 'khana', 'pyna': 'peena',
    'prhna': 'parhna', 'smjna': 'samajhna'
}

ROMAN_URDU_PREFIXES = {
    'm': ['mein', 'mujhe', 'mera', 'magar'],
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


# =============================================================
# CARET POSITION (Universal Windows API)
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

_last_caret_pos = (300, 300)

def get_caret_position():
    """Get caret position - works in most Windows apps"""
    global _last_caret_pos
    try:
        info = _GUITHREADINFO()
        info.cbSize = ctypes.sizeof(_GUITHREADINFO)
        if ctypes.windll.user32.GetGUIThreadInfo(0, ctypes.byref(info)):
            if info.hwndCaret:
                pt = _POINT(info.rcCaret.left, info.rcCaret.bottom)
                ctypes.windll.user32.ClientToScreen(info.hwndCaret, ctypes.byref(pt))
                if pt.x > 0 and pt.y > 0:
                    _last_caret_pos = (pt.x + 10, pt.y + 20)
                    return _last_caret_pos
    except:
        pass
    return _last_caret_pos


class _POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


# =============================================================
# DATA MANAGER
# =============================================================
class DictIndex:
    __slots__ = ('_words', '_keys')
    def __init__(self, words):
        self._words = sorted(set(w for w in words if len(w) >= 2), key=str.lower)
        self._keys = [w.lower() for w in self._words]
    
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


class DataManager:
    __slots__ = ('suggestions', 'user_learning', 'usage_stats', 'dict_index', 
                 'errors', 'ru_learning', '_ru_corrections', '_ru_prefixes')
    
    def __init__(self):
        self.suggestions = self._load_json(SUGGESTIONS_FILE, {})
        self.user_learning = self._load_json(USER_LEARNING_FILE, {})
        self.usage_stats = self._load_json(USAGE_STATS_FILE, {})
        self.dict_index = self._build_dict_index()
        
        raw_errors = self._load_json(ERRORS_FILE, {})
        self.errors = {k.strip().lower(): v.strip() for k, v in raw_errors.items() if k.strip()}
        
        self.ru_learning = self._load_json(os.path.join(BASE_DIR, "ru_learning.json"), {})
        self._ru_corrections = ROMAN_URDU_CORRECTIONS
        self._ru_prefixes = ROMAN_URDU_PREFIXES
    
    @staticmethod
    def _load_json(path, default):
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except:
            pass
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
        w = word.lower()
        if lang == 'roman_urdu':
            if w in self._ru_corrections:
                return self._ru_corrections[w]
            if w in self.ru_learning and self.ru_learning[w] > 2:
                return w
            if w in self.user_learning and self.user_learning[w] > 3:
                return w
            return word
        else:
            if w in self.errors:
                return self.errors[w]
            return word
    
    def get_smart_matches(self, prefix, lang='english'):
        if not prefix or len(prefix) < MIN_WORD_LENGTH:
            return []
        
        prefix_l = prefix.lower()
        seen = set()
        results = []
        
        if lang == 'roman_urdu':
            # Fast prefix lookup
            first_char = prefix_l[0] if prefix_l else ''
            if first_char in self._ru_prefixes:
                for w in self._ru_prefixes[first_char]:
                    if w.startswith(prefix_l) and w not in seen:
                        seen.add(w)
                        results.append((w, 200))
            
            # Learned words
            for w, cnt in list(self.ru_learning.items())[:30]:
                if w.startswith(prefix_l) and w not in seen and cnt > 2:
                    seen.add(w)
                    results.append((w, cnt + 100))
            
            # Corrections
            for w in self._ru_corrections.keys():
                if w.startswith(prefix_l) and w not in seen:
                    seen.add(w)
                    results.append((w, 80))
        
        else:  # English
            # Custom words
            for w in self.get_all_custom_words():
                if w.lower().startswith(prefix_l) and w not in seen:
                    seen.add(w)
                    results.append((w, 150))
            
            # Learned words
            for w, cnt in list(self.user_learning.items())[:50]:
                if w.lower().startswith(prefix_l) and w not in seen and cnt > 2:
                    seen.add(w)
                    results.append((w, cnt + 50))
            
            # Dictionary
            if self.dict_index:
                for w in self.dict_index.prefix_search(prefix_l, limit=10):
                    if w not in seen:
                        seen.add(w)
                        results.append((w, self.user_learning.get(w.lower(), 0) + 
                                        self.usage_stats.get(w.lower(), 0)))
        
        results.sort(key=lambda x: x[1], reverse=True)
        return [w for w, _ in results[:MAX_SUGGESTIONS]]
    
    def learn_word(self, word, lang='english'):
        w = word.lower()
        if lang == 'roman_urdu':
            self.ru_learning[w] = self.ru_learning.get(w, 0) + 1
            if self.ru_learning[w] % 10 == 0:
                self._save_json(os.path.join(BASE_DIR, "ru_learning.json"), self.ru_learning)
        else:
            self.user_learning[w] = self.user_learning.get(w, 0) + 1
            if self.user_learning[w] % 10 == 0:
                self._save_json(USER_LEARNING_FILE, self.user_learning)
    
    def record_usage(self, word):
        w = word.lower()
        self.usage_stats[w] = self.usage_stats.get(w, 0) + 1
        if len(self.usage_stats) % 50 == 0:
            self._save_json(USAGE_STATS_FILE, self.usage_stats)
    
    @staticmethod
    def _save_json(path, data):
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except:
            pass


# =============================================================
# SUGGESTION POPUP
# =============================================================
class SuggestionPopup:
    __slots__ = ('root', 'on_select', 'top', 'listbox', 'suggestions', 'current_word', 'active')
    
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
        popup_y = y + 25
        
        if self.top is None:
            self.top = tk.Toplevel(self.root)
            self.top.title("Alpha")
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
        
        visible = min(len(suggestions), 7)
        h = visible * 28 + 8
        self.top.geometry(f"{POPUP_WIDTH}x{h}+{popup_x}+{popup_y}")
        self.listbox.delete(0, tk.END)
        for item in suggestions:
            self.listbox.insert(tk.END, f"  {item}")
        self.listbox.select_set(0)
        self.listbox.activate(0)
    
    def _on_mouse_click(self, event):
        idx = self.listbox.nearest(event.y)
        if 0 <= idx < len(self.suggestions):
            self.close()
            self.on_select(self.current_word, self.suggestions[idx])
    
    def select_next(self):
        if not self.listbox or not self.suggestions:
            return
        idx = self.listbox.curselection()
        if idx and idx[0] < len(self.suggestions) - 1:
            new = idx[0] + 1
            self.listbox.select_clear(idx[0])
            self.listbox.select_set(new)
            self.listbox.activate(new)
            self.listbox.see(new)
        elif not idx:
            self.listbox.select_set(0)
            self.listbox.activate(0)
    
    def select_prev(self):
        if not self.listbox or not self.suggestions:
            return
        idx = self.listbox.curselection()
        if idx and idx[0] > 0:
            new = idx[0] - 1
            self.listbox.select_clear(idx[0])
            self.listbox.select_set(new)
            self.listbox.activate(new)
            self.listbox.see(new)
    
    def confirm_selected(self):
        if not self.listbox or not self.suggestions:
            return
        idx = self.listbox.curselection()
        if idx:
            word = self.suggestions[idx[0]]
            self.close()
            self.on_select(self.current_word, word)
    
    def close(self):
        self.active = False
        if self.top:
            try:
                self.top.destroy()
            except:
                pass
            self.top = None
            self.listbox = None


# =============================================================
# GLOBAL ASSISTANT (Main Class)
# =============================================================
class GlobalAssistant:
    def __init__(self):
        self.dm = DataManager()
        self.lang_detector = LanguageDetector()
        self.keyboard = pynput_keyboard.Controller()
        self.enabled = True
        self.is_inserting = False
        self.last_ctrl_t = 0
        self.typing_buffer = deque(maxlen=60)
        self.event_queue = queue.Queue()
        self.listener = None
        self.root = tk.Tk()
        self.root.withdraw()
        self.popup = SuggestionPopup(self.root, self._on_suggestion_selected)
        self.current_lang = 'english'
    
    def _get_current_word(self):
        text = ''.join(self.typing_buffer)
        words = re.findall(r"[a-zA-Z\u0600-\u06FF']+", text)
        return words[-1] if words else ""
    
    def _detect_language(self):
        text = ''.join(self.typing_buffer)
        if len(text.strip()) < 3:
            return 'unknown'
        return self.lang_detector.detect(text)
    
    def _get_suggestions(self, word, lang):
        suggestions = []
        
        if lang == 'english':
            corrected = self.dm.correct_error(word, 'english')
            if corrected != word:
                suggestions.append(f"🔧 {corrected}")
            
            for m in self.dm.get_smart_matches(word, 'english'):
                if m.lower() != word.lower():
                    suggestions.append(m)
        
        elif lang == 'roman_urdu':
            corrected = self.dm.correct_error(word, 'roman_urdu')
            if corrected != word:
                suggestions.append(f"🇵🇰 {corrected}")
            
            for m in self.dm.get_smart_matches(word, 'roman_urdu'):
                if m.lower() != word.lower() and m not in suggestions:
                    suggestions.append(m)
        
        elif lang == 'urdu_script':
            suggestions.append(f"📜 {word}")
        
        return suggestions[:MAX_SUGGESTIONS]
    
    def _on_suggestion_selected(self, original_word, suggestion):
        for prefix in ["🔧 ", "🇵🇰 ", "📜 "]:
            if suggestion.startswith(prefix):
                suggestion = suggestion[len(prefix):]
                break
        
        self._insert_suggestion(original_word, suggestion)
    
    def _insert_suggestion(self, original_word, suggestion, extra_bs=0):
        self.typing_buffer.clear()
        self.is_inserting = True
        self.dm.record_usage(suggestion)
        threading.Thread(target=self._do_insert, args=(original_word, suggestion, extra_bs), daemon=True).start()
    
    def _do_insert(self, original_word, suggestion, extra_bs=0):
        try:
            time.sleep(FOCUS_RETURN_DELAY)
            
            for _ in range(len(original_word) + extra_bs):
                self.keyboard.press(pynput_keyboard.Key.backspace)
                self.keyboard.release(pynput_keyboard.Key.backspace)
                time.sleep(BACKSPACE_DELAY)
            
            self.keyboard.type(suggestion)
            
        except Exception as e:
            print(f"Insert error: {e}")
        finally:
            self.is_inserting = False
            self.typing_buffer.clear()
    
    def _win32_event_filter(self, msg, data):
        if self.popup and self.popup.active:
            if data.vkCode in (13, 9, 27, 38, 40):
                if msg == 256:
                    if data.vkCode == 13:
                        self.event_queue.put(('confirm',))
                    elif data.vkCode == 38:
                        self.event_queue.put(('up',))
                    elif data.vkCode == 40:
                        self.event_queue.put(('down',))
                    elif data.vkCode == 27:
                        self.event_queue.put(('close',))
                return False
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
                self.event_queue.put(('close',))
                return True
            
            if not self.enabled:
                return True
            
            if hasattr(key, 'char') and key.char and ord(key.char) >= 32:
                self.typing_buffer.append(key.char)
                self.event_queue.put(('suggest', self._get_current_word()))
            
            elif key == pynput_keyboard.Key.space:
                word = self._get_current_word()
                if word:
                    lang = self._detect_language()
                    corrected = self.dm.correct_error(word, lang)
                    
                    if corrected != word:
                        self.typing_buffer.clear()
                        self.event_queue.put(('close',))
                        self._insert_suggestion(word, corrected + " ", extra_bs=1)
                        return True
                    else:
                        self.dm.learn_word(word, lang)
                
                self.typing_buffer.clear()
                self.event_queue.put(('close',))
            
            elif key == pynput_keyboard.Key.backspace:
                if self.typing_buffer:
                    self.typing_buffer.pop()
                self.event_queue.put(('suggest', self._get_current_word()))
            
            elif key == pynput_keyboard.Key.enter:
                word = self._get_current_word()
                if word:
                    lang = self._detect_language()
                    self.dm.learn_word(word, lang)
                self.typing_buffer.clear()
                self.event_queue.put(('close',))
        
        except Exception:
            pass
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
                            self.current_lang = self._detect_language()
                            suggestions = self._get_suggestions(word, self.current_lang)
                            if suggestions:
                                x, y = get_caret_position()
                                self.popup.show(suggestions, word, x, y)
                            else:
                                self.popup.close()
                        else:
                            self.popup.close()
                
                elif cmd == 'force_show':
                    word = self._get_current_word()
                    if word and self.enabled:
                        self.current_lang = self._detect_language()
                        suggestions = self._get_suggestions(word, self.current_lang)
                        if suggestions:
                            x, y = get_caret_position()
                            self.popup.show(suggestions, word, x, y)
                
                elif cmd == 'up':
                    self.popup.select_prev()
                elif cmd == 'down':
                    self.popup.select_next()
                elif cmd == 'confirm':
                    self.popup.confirm_selected()
                elif cmd in ('close', 'popup_close'):
                    self.popup.close()
        
        except queue.Empty:
            pass
        finally:
            self.root.after(POLL_INTERVAL_MS, self._poll_queue)
    
    def show_splash(self):
        splash = tk.Toplevel(self.root)
        splash.title("Alpha")
        splash.overrideredirect(True)
        splash.attributes('-topmost', True)
        
        w, h = 500, 280
        sw, sh = splash.winfo_screenwidth(), splash.winfo_screenheight()
        splash.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
        
        canvas = tk.Canvas(splash, width=w, height=h, bg="#0d1117", highlightthickness=0)
        canvas.pack()
        
        canvas.create_text(w//2, 50, text="ALPHA", fill="#ffffff", font=("Segoe UI", 48, "bold"))
        canvas.create_text(w//2, 95, text="Intelligent Typing Assistant", fill="#58a6ff", font=("Segoe UI", 13))
        canvas.create_text(w//2, 135, text="English • Roman Urdu • Universal", fill="#00ff88", font=("Segoe UI", 11))
        canvas.create_line(100, 160, w-100, 160, fill="#30363d", width=1)
        canvas.create_text(w//2, 195, text="✓ Ready • Click anywhere to start", fill="#8b949e", font=("Segoe UI", 10))
        canvas.create_text(w//2, 235, text="Moiz Digital Service", fill="#6e7681", font=("Segoe UI", 9))
        
        splash.bind("<Button-1>", lambda e: splash.destroy())
        splash.after(3500, splash.destroy)
    
    def start(self):
        print("=" * 50)
        print("  ALPHA Typing Assistant v3.3")
        print("  English + Roman Urdu | Universal Compatibility")
        print("=" * 50)
        
        self.show_splash()
        
        self.listener = pynput_keyboard.Listener(
            on_press=self.on_press,
            win32_event_filter=self._win32_event_filter,
            suppress=False
        )
        self.listener.daemon = True
        self.listener.start()
        time.sleep(0.2)
        
        if self.listener.running:
            print("  ✓ Active")
        else:
            print("  ✗ Run as Administrator for full functionality")
        
        self.root.after(POLL_INTERVAL_MS, self._poll_queue)
        
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            pass
        finally:
            self.popup.close()
            if self.listener:
                self.listener.stop()
            DataManager._save_json(USER_LEARNING_FILE, self.dm.user_learning)
            DataManager._save_json(USAGE_STATS_FILE, self.dm.usage_stats)
            print("=" * 50)
            print("  Goodbye!")
            print("=" * 50)


if __name__ == "__main__":
    assistant = GlobalAssistant()
    assistant.start()
