"""
ALPHA Typing Assistant v3.5 FINAL
Author: Moiz Digital Service
=====================================================================
✅ FIXED: Caret position follows typing cursor
✅ FIXED: Enter key does NOT submit forms when popup active
✅ FIXED: Thread-safe buffer
✅ FIXED: Language detection + Roman Urdu support
"""

import tkinter as tk
from tkinter import Listbox
import pyautogui
import threading
import time
import json
import os
import re
import queue
import bisect
import ctypes
import tempfile
import atexit
import platform
from datetime import datetime
from pynput import keyboard as pynput_keyboard
from collections import deque

try:
    import keyboard
    HAVE_KEYBOARD = True
except ImportError:
    HAVE_KEYBOARD = False

# =============================================================
# CONFIG
# =============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SUGGESTIONS_FILE   = os.path.join(BASE_DIR, "suggestions.json")
ERRORS_FILE        = os.path.join(BASE_DIR, "errors.json")
DICTIONARY_FILE    = os.path.join(BASE_DIR, "dictionary.json")
USER_LEARNING_FILE = os.path.join(BASE_DIR, "user_learning.json")
USAGE_STATS_FILE   = os.path.join(BASE_DIR, "usage_stats.json")

POPUP_WIDTH        = 320
MAX_SUGGESTIONS    = 8
MIN_WORD_LENGTH    = 2
DEBOUNCE_TIME      = 0.3
FOCUS_RETURN_DELAY = 0.12
POLL_INTERVAL_MS   = 50
BACKSPACE_DELAY    = 0.005

# =============================================================
# LANGUAGE DETECTOR
# =============================================================
class LanguageDetector:
    ENGLISH_COMMON = {
        'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i',
        'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at',
        'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her', 'she'
    }
    
    ROMAN_URDU_COMMON = {
        'hai', 'hain', 'tha', 'thi', 'ho', 'mein', 'tum', 'wo', 'woh', 'yeh',
        'hum', 'aap', 'kya', 'kyun', 'kaise', 'nahi', 'haan', 'acha'
    }
    
    COMMON_TYPOS = {'teh', 'becuase', 'recieve', 'seperate', 'definately', 'adn', 'acn', 'taht'}
    
    def __init__(self):
        self.urdu_chars = set('ابپتٹثجچحخدڈذرزژسشصضطظعغفقکگلمنہوےؤئى')
    
    def detect(self, text):
        if not text or len(text.strip()) < 2:
            return 'unknown'
        text = text.strip().lower()
        words = text.split()
        if not words:
            return 'unknown'
        last_word = words[-1]
        
        if any(ch in self.urdu_chars for ch in last_word):
            return 'urdu_script'
        if last_word in self.COMMON_TYPOS:
            return 'english'
        if last_word in self.ENGLISH_COMMON:
            return 'english'
        if last_word in self.ROMAN_URDU_COMMON:
            return 'roman_urdu'
        if re.search(r'(th|ng|ck|tion|ing|ment)$', last_word):
            return 'english'
        if last_word.endswith('h') and len(last_word) > 2:
            return 'roman_urdu'
        return 'english'

# =============================================================
# ROMAN URDU CORRECTIONS
# =============================================================
ROMAN_URDU_CORRECTIONS = {
    'mei': 'mein', 'mai': 'mein', 'men': 'mein', 'nhe': 'nahi',
    'nai': 'nahi', 'nhi': 'nahi', 'karta': 'karta', 'hu': 'hoon',
    'ap': 'aap', 'wo': 'woh', 'ye': 'yeh', 'krna': 'karna',
    'bhot': 'bohat', 'zyda': 'zyada', 'ghr': 'ghar', 'skool': 'school'
}

ROMAN_URDU_PREFIXES = {
    'm': ['mein', 'mujhe', 'mera'], 't': ['tum', 'tujhe', 'tera'],
    'w': ['woh', 'wahan'], 'k': ['kya', 'kaise', 'kahan'],
    'h': ['hai', 'hain', 'hoon'], 'a': ['aap', 'acha', 'aaj']
}

# =============================================================
# CARET POSITION - CRITICAL FIX
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

_last_caret_pos = (300, 300)

def update_caret_position():
    """Call this on every keystroke to track caret"""
    global _last_caret_pos
    try:
        info = _GUITHREADINFO()
        info.cbSize = ctypes.sizeof(_GUITHREADINFO)
        if ctypes.windll.user32.GetGUIThreadInfo(0, ctypes.byref(info)):
            if info.hwndCaret:
                pt = _POINT(info.rcCaret.left, info.rcCaret.bottom)
                ctypes.windll.user32.ClientToScreen(info.hwndCaret, ctypes.byref(pt))
                if pt.x > 0 and pt.y > 0:
                    _last_caret_pos = (pt.x + 10, pt.y + 25)
                    return True
    except:
        pass
    return False

def get_caret_position():
    """Returns last known caret position (updated on every keystroke)"""
    return _last_caret_pos

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
        
        common_typos = {
            'teh': 'the', 'reciver': 'receiver', 'becuase': 'because',
            'recieve': 'receive', 'seperate': 'separate', 'definately': 'definitely',
            'adn': 'and', 'acn': 'can', 'taht': 'that'
        }
        for typo, correct in common_typos.items():
            if typo not in self.errors:
                self.errors[typo] = correct
        
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
        if not w or len(w) < 2:
            return word
        if lang == 'roman_urdu':
            if w in self._ru_corrections:
                return self._ru_corrections[w]
            if w in self.ru_learning and self.ru_learning[w] > 2:
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
            first_char = prefix_l[0] if prefix_l else ''
            if first_char in self._ru_prefixes:
                for w in self._ru_prefixes[first_char]:
                    if w.startswith(prefix_l) and w not in seen:
                        seen.add(w)
                        results.append((w, 200))
            for w, cnt in list(self.ru_learning.items())[:30]:
                if w.startswith(prefix_l) and w not in seen and cnt > 2:
                    seen.add(w)
                    results.append((w, cnt + 100))
            for w in self._ru_corrections.keys():
                if w.startswith(prefix_l) and w not in seen:
                    seen.add(w)
                    results.append((w, 80))
        else:
            for w in self.get_all_custom_words():
                if w.lower().startswith(prefix_l) and w not in seen:
                    seen.add(w)
                    results.append((w, 150))
            for w, cnt in list(self.user_learning.items())[:50]:
                if w.lower().startswith(prefix_l) and w not in seen and cnt > 2:
                    seen.add(w)
                    results.append((w, cnt + 50))
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
            self.root.after(10, lambda: self.on_select(self.current_word, word))
    
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
# SESSION TRACKER
# =============================================================
class SessionTracker:
    def __init__(self):
        self.session_file = None
        self.help_data = {
            'session_start': datetime.now().isoformat(),
            'computer_name': platform.node(),
            'os': platform.system(),
            'apps_helped': {},
            'total_corrections': 0,
            'words_corrected': [],
            'languages_used': set()
        }
        self._create_session_file()
    
    def _create_session_file(self):
        try:
            temp_dir = tempfile.gettempdir()
            self.session_file = os.path.join(temp_dir, f"alpha_session_{os.getpid()}.json")
            with open(self.session_file, 'w', encoding='utf-8') as f:
                json.dump(self.help_data, f, indent=2, ensure_ascii=False)
            atexit.register(self.cleanup)
        except:
            pass
    
    def record_help(self, app_name, original_word, corrected_word, language):
        if not app_name:
            app_name = "Unknown"
        if app_name not in self.help_data['apps_helped']:
            self.help_data['apps_helped'][app_name] = 0
        self.help_data['apps_helped'][app_name] += 1
        self.help_data['total_corrections'] += 1
        self.help_data['words_corrected'].append({
            'time': datetime.now().isoformat(),
            'app': app_name,
            'from': original_word,
            'to': corrected_word,
            'lang': language
        })
        if len(self.help_data['words_corrected']) > 50:
            self.help_data['words_corrected'] = self.help_data['words_corrected'][-50:]
        self.help_data['languages_used'].add(language)
        
        data_to_save = self.help_data.copy()
        data_to_save['languages_used'] = list(self.help_data['languages_used'])
        try:
            with open(self.session_file, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, indent=2, ensure_ascii=False)
        except:
            pass
    
    def get_active_app(self):
        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            buff = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
            window_title = buff.value
            if 'WhatsApp' in window_title: return 'WhatsApp'
            if 'Chrome' in window_title: return 'Google Chrome'
            if 'Notepad' in window_title: return 'Notepad'
            if 'Word' in window_title: return 'Microsoft Word'
            if 'VS Code' in window_title: return 'VS Code'
            return window_title[:30] if window_title else 'Unknown'
        except:
            return 'Unknown'
    
    def get_summary(self):
        s = f"Start: {self.help_data['session_start'][:19]} | PC: {self.help_data['computer_name']} | OS: {self.help_data['os']}"
        s += f"\nCorrections: {self.help_data['total_corrections']} | Languages: {', '.join(self.help_data['languages_used'])}"
        for app, count in self.help_data['apps_helped'].items():
            s += f"\n  {app}: {count}x"
        return s
    
    def cleanup(self):
        if self.session_file and os.path.exists(self.session_file):
            try:
                os.remove(self.session_file)
            except:
                pass

# =============================================================
# GLOBAL ASSISTANT (Main Class)
# =============================================================
class GlobalAssistant:
    def __init__(self):
        self.dm = DataManager()
        self.lang_detector = LanguageDetector()
        self.session = SessionTracker()
        self.keyboard = pynput_keyboard.Controller()
        self.enabled = True
        self.is_inserting = False
        self.last_ctrl_t = 0
        self.typing_buffer = deque(maxlen=60)
        self.buffer_lock = threading.Lock()
        self.event_queue = queue.Queue()
        self.listener = None
        self.root = tk.Tk()
        self.root.withdraw()
        self.popup = SuggestionPopup(self.root, self._on_suggestion_selected)
        self.current_lang = 'english'
        
        # Hotkeys
        if HAVE_KEYBOARD:
            try:
                keyboard.add_hotkey('ctrl+alt+x', self.toggle_assistant)
                keyboard.add_hotkey('ctrl+alt+s', self.show_session_summary)
            except:
                pass
    
    def toggle_assistant(self):
        self.enabled = not self.enabled
        print(f"  Assistant {'ON' if self.enabled else 'OFF'}")
    
    def show_session_summary(self):
        print("\n" + "=" * 50)
        print("  ALPHA SESSION SUMMARY")
        print("=" * 50)
        print(self.session.get_summary())
        print("=" * 50 + "\n")
    
    def _get_current_word(self):
        with self.buffer_lock:
            text = ''.join(self.typing_buffer)
        words = re.findall(r"[a-zA-Z\u0600-\u06FF']+", text)
        return words[-1] if words else ""
    
    def _detect_language(self):
        with self.buffer_lock:
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
        self._insert_suggestion(original_word, suggestion, self.current_lang)
    
    def _insert_suggestion(self, original_word, suggestion, lang, extra_bs=0):
        app = self.session.get_active_app()
        self.session.record_help(app, original_word, suggestion.strip(), lang)
        with self.buffer_lock:
            self.typing_buffer.clear()
        self.is_inserting = True
        self.dm.record_usage(suggestion)
        threading.Thread(target=self._do_insert, args=(original_word, suggestion, extra_bs), daemon=True).start()
    
    def _do_insert(self, original_word, suggestion, extra_bs=0):
        try:
            time.sleep(FOCUS_RETURN_DELAY)
            total_bs = len(original_word) + extra_bs
            for _ in range(total_bs):
                self.keyboard.press(pynput_keyboard.Key.backspace)
                self.keyboard.release(pynput_keyboard.Key.backspace)
                time.sleep(BACKSPACE_DELAY)
            self.keyboard.type(suggestion)
        except Exception as e:
            print(f"Insert error: {e}")
        finally:
            self.is_inserting = False
            with self.buffer_lock:
                self.typing_buffer.clear()
    
    # =============================================================
    # CRITICAL FIX: Enter key suppression - NO FORM SUBMISSION
    # =============================================================
    def _win32_event_filter(self, msg, data):
        """Suppress Enter/Tab when popup is active - prevents form submission"""
        if self.popup and self.popup.active:
            if data.vkCode in (13, 9, 27, 38, 40):
                if msg == 256:  # WM_KEYDOWN
                    if data.vkCode == 13:   # Enter
                        self.event_queue.put(('confirm',))
                    elif data.vkCode == 9:  # Tab
                        self.event_queue.put(('confirm',))
                    elif data.vkCode == 38: # Up
                        self.event_queue.put(('up',))
                    elif data.vkCode == 40: # Down
                        self.event_queue.put(('down',))
                    elif data.vkCode == 27: # Escape
                        self.event_queue.put(('close',))
                # CRITICAL: Return False to suppress key from reaching OS
                if self.listener:
                    self.listener.suppress_event()
                return False
        return True
    
    def on_press(self, key):
        if self.is_inserting:
            return True
        
        # Update caret position on EVERY keystroke (critical for web apps)
        update_caret_position()
        
        try:
            # Ctrl+Ctrl trigger
            if key in (pynput_keyboard.Key.ctrl_l, pynput_keyboard.Key.ctrl_r):
                now = time.time()
                if now - self.last_ctrl_t < DEBOUNCE_TIME:
                    self.event_queue.put(('force_show',))
                self.last_ctrl_t = now
                return True
            
            if key in (pynput_keyboard.Key.left, pynput_keyboard.Key.right):
                with self.buffer_lock:
                    self.typing_buffer.clear()
                self.event_queue.put(('close',))
                return True
            
            if not self.enabled:
                return True
            
            if hasattr(key, 'char') and key.char and ord(key.char) >= 32:
                with self.buffer_lock:
                    self.typing_buffer.append(key.char)
                self.event_queue.put(('suggest', self._get_current_word()))
            
            elif key == pynput_keyboard.Key.space:
                word = self._get_current_word()
                if word and len(word) >= MIN_WORD_LENGTH:
                    lang = self._detect_language()
                    corrected = self.dm.correct_error(word, lang)
                    if corrected != word:
                        with self.buffer_lock:
                            self.typing_buffer.clear()
                        self.event_queue.put(('close',))
                        self._insert_suggestion(word, corrected + " ", lang, extra_bs=0)
                        return True
                    else:
                        self.dm.learn_word(word, lang)
                with self.buffer_lock:
                    self.typing_buffer.clear()
                self.event_queue.put(('close',))
            
            elif key == pynput_keyboard.Key.backspace:
                with self.buffer_lock:
                    if self.typing_buffer:
                        self.typing_buffer.pop()
                self.event_queue.put(('suggest', self._get_current_word()))
            
            elif key == pynput_keyboard.Key.enter:
                word = self._get_current_word()
                if word:
                    lang = self._detect_language()
                    self.dm.learn_word(word, lang)
                with self.buffer_lock:
                    self.typing_buffer.clear()
                self.event_queue.put(('close',))
        
        except Exception as e:
            print(f"Key error: {e}")
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
        
        w, h = 520, 320
        sw, sh = splash.winfo_screenwidth(), splash.winfo_screenheight()
        splash.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
        
        canvas = tk.Canvas(splash, width=w, height=h, bg="#0a0e17", highlightthickness=0)
        canvas.pack()
        
        # Top accent bar
        canvas.create_rectangle(0, 0, w, 3, fill="#00ff88", outline="")
        
        # Background glow circles
        canvas.create_oval(50, 200, 200, 350, fill="", outline="#00ff88", width=1, dash=(4, 8))
        canvas.create_oval(320, -50, 470, 100, fill="", outline="#58a6ff", width=1, dash=(4, 8))
        
        # Logo area
        canvas.create_text(w//2, 55, text="ALPHA", fill="#ffffff", font=("Segoe UI", 44, "bold"))
        canvas.create_text(w//2, 90, text="Intelligent Typing Assistant", fill="#58a6ff", font=("Segoe UI", 12))
        
        # Divider
        canvas.create_line(80, 110, w-80, 110, fill="#1e2a45", width=1)
        
        # Feature badges
        features = [
            ("⚡", "Real-time Suggestions"),
            ("🌐", "English + Roman Urdu"),
            ("🛡️", "Universal Compatibility"),
        ]
        for i, (icon, text) in enumerate(features):
            y = 140 + i * 32
            canvas.create_oval(90, y-2, 108, y+16, fill="#0d1b2a", outline="#1e3a5f")
            canvas.create_text(99, y+7, text=icon, font=("Segoe UI", 10))
            canvas.create_text(180, y+7, text=text, fill="#8b949e", font=("Segoe UI", 10), anchor="w")
        
        # Bottom accent
        canvas.create_line(80, 245, w-80, 245, fill="#1e2a45", width=1)
        status_id = canvas.create_text(w//2, 270, text="✓ System Ready", fill="#00ff88", font=("Segoe UI", 10, "bold"))
        canvas.create_text(w//2, 295, text="Moiz Digital Service", fill="#4a5568", font=("Segoe UI", 8))
        
        # Animated dots
        def update_dots(count=0):
            try:
                dots = "." * (count % 4)
                canvas.itemconfig(status_id, text=f"✓ System Ready{dots}")
                splash.after(400, lambda: update_dots(count + 1))
            except:
                pass
        
        splash.after(400, update_dots)
        
        splash.bind("<Button-1>", lambda e: splash.destroy())
        splash.after(3500, splash.destroy)
    
    def start(self):
        print("=" * 50)
        print("  ALPHA Typing Assistant v3.5 FINAL")
        print("  English + Roman Urdu | Universal Compatibility")
        print("  Hotkeys: Ctrl+Alt+X (Toggle), Ctrl+Alt+S (Summary)")
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
            print(self.session.get_summary())
            print("=" * 50)
            print("  Goodbye!")
            print("=" * 50)

if __name__ == "__main__":
    assistant = GlobalAssistant()
    assistant.start()
