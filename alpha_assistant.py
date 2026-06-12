"""
ALPHA Typing Assistant v3.5 FINAL - PRODUCTION READY
Author: Moiz Digital Service
Architecture: Optimized Monolithic with Async I/O
"""

import tkinter as tk
from tkinter import Listbox
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

# Optional hotkey support
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

POPUP_WIDTH = 320
MAX_SUGGESTIONS = 8
MIN_WORD_LENGTH = 2
DEBOUNCE_TIME = 0.3
FOCUS_RETURN_DELAY = 0.12
POLL_INTERVAL_MS = 50
BACKSPACE_DELAY = 0.005

# =============================================================
# BACKGROUND WRITER (Async I/O)
# =============================================================
class BackgroundWriter:
    __slots__ = ('_queue', '_thread')

    def __init__(self):
        self._queue = queue.Queue()
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def save(self, path, data):
        self._queue.put((path, data))

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
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            except Exception:
                pass
            self._queue.task_done()

bg_writer = BackgroundWriter()

# =============================================================
# CARET TRACKING (Win32 API)
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
    except Exception:
        pass
    return False

def get_caret_position():
    return _last_caret_pos

# =============================================================
# SEQUENCE LEARNER
# =============================================================
class SequenceLearner:
    __slots__ = ('sequences', 'trigrams')

    def __init__(self):
        self.sequences = {}
        self.trigrams = {}

    def learn(self, word_list):
        if len(word_list) < 2: return
        for i in range(len(word_list) - 1):
            current = word_list[i].lower()
            next_word = word_list[i + 1].lower()
            if current not in self.sequences: self.sequences[current] = {}
            self.sequences[current][next_word] = self.sequences[current].get(next_word, 0) + 1
        
        for i in range(len(word_list) - 2):
            key = f"{word_list[i].lower()}_{word_list[i+1].lower()}"
            next_word = word_list[i + 2].lower()
            if key not in self.trigrams: self.trigrams[key] = {}
            self.trigrams[key][next_word] = self.trigrams[key].get(next_word, 0) + 1

    def predict_next(self, current_word, prev_word=None):
        current = current_word.lower()
        results = []
        if prev_word:
            trigram_key = f"{prev_word.lower()}_{current}"
            if trigram_key in self.trigrams:
                for word, count in self.trigrams[trigram_key].items():
                    results.append((word, count * 2))
        if current in self.sequences:
            for word, count in self.sequences[current].items():
                results.append((word, count))
        
        results.sort(key=lambda x: x[1], reverse=True)
        return [word for word, _ in results[:5]]

# =============================================================
# DATA MANAGER
# =============================================================
class DictIndex:
    __slots__ = ('_words', '_keys')

    def __init__(self, words):
        clean_words = sorted(set(w.strip() for w in words if len(w.strip()) >= 2), key=str.lower)
        self._words = tuple(clean_words)
        self._keys = tuple(w.lower() for w in self._words)

    def prefix_search(self, prefix, limit=15):
        prefix_l = prefix.lower()
        lo = bisect.bisect_left(self._keys, prefix_l)
        results = []
        for i in range(lo, len(self._keys)):
            if self._keys[i].startswith(prefix_l):
                results.append(self._words[i])
                if len(results) >= limit: break
            else:
                break
        return results

class DataManager:
    __slots__ = ('suggestions', 'user_learning', 'usage_stats', 'dict_index',
                 'errors', 'ru_learning', '_ru_corrections', '_ru_prefixes',
                 'word_pairs', 'recency_tracker', 'sequence_learner', 'word_history')

    def __init__(self):
        self.suggestions = self._load_json(SUGGESTIONS_FILE, {})
        self.user_learning = self._load_json(USER_LEARNING_FILE, {})
        self.usage_stats = self._load_json(USAGE_STATS_FILE, {})
        self.dict_index = self._build_dict_index()
        
        raw_errors = self._load_json(ERRORS_FILE, {})
        self.errors = {k.strip().lower(): v.strip() for k, v in raw_errors.items() if k.strip()}
        
        common_typos = {'teh': 'the', 'reciver': 'receiver', 'becuase': 'because',
                        'recieve': 'receive', 'seperate': 'separate', 'definately': 'definitely',
                        'adn': 'and', 'acn': 'can', 'taht': 'that'}
        for typo, correct in common_typos.items():
            if typo not in self.errors: self.errors[typo] = correct

        self.ru_learning = self._load_json(RU_LEARNING_FILE, {})
        self._ru_corrections = ROMAN_URDU_CORRECTIONS
        self._ru_prefixes = ROMAN_URDU_PREFIXES
        self.word_pairs = self._load_json(WORD_PAIRS_FILE, {})
        self.recency_tracker = self._load_json(RECENCY_FILE, {})
        self.sequence_learner = SequenceLearner()
        self.word_history = deque(maxlen=10)
        self._load_sequences()

    @staticmethod
    def _load_json(path, default):
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return default

    def _build_dict_index(self):
        raw = self._load_json(DICTIONARY_FILE, [])
        return DictIndex(raw) if isinstance(raw, list) and raw else None

    def get_all_custom_words(self):
        words = []
        for cat_words in self.suggestions.values():
            words.extend([w.strip() for w in cat_words])
        return words

    def correct_error(self, word, lang='english'):
        w = word.lower()
        if not w or len(w) < 2: return word
        if lang == 'roman_urdu':
            if w in self._ru_corrections: return self._ru_corrections[w]
            if w in self.ru_learning and self.ru_learning[w] > 2: return w
        else:
            if w in self.errors: return self.errors[w]
        return word

    def get_smart_matches_enhanced(self, prefix, lang='english', prev_word=''):
        if not prefix or len(prefix) < MIN_WORD_LENGTH: return []
        prefix_l = prefix.lower()
        seen = set()
        results = []
        WEIGHTS = {
            'exact_match': 1000, 'context_match': 800, 'user_learning': 500,
            'recency': 400, 'usage_freq': 300, 'prefix_match': 200,
            'roman_urdu': 150, 'dictionary': 100, 'custom': 60
        }
        
        if prev_word:
            key = f"{prev_word}|{prefix_l}"
            if key in self.word_pairs:
                for word, score in sorted(self.word_pairs[key].items(), key=lambda x: x[1], reverse=True)[:3]:
                    if word not in seen:
                        seen.add(word)
                        results.append((word, WEIGHTS['context_match'] + score * 10))
        
        if prefix_l in self.errors:
            corrected = self.errors[prefix_l]
            if corrected not in seen:
                seen.add(corrected)
                results.append((corrected, WEIGHTS['exact_match']))
        
        for w, cnt in self.user_learning.items():
            if w.startswith(prefix_l) and w not in seen:
                recency = self.recency_tracker.get(w, 0)
                score = WEIGHTS['user_learning'] + (cnt * 10) + (recency * 2)
                results.append((w, score))
                seen.add(w)
                
        for w, cnt in self.usage_stats.items():
            if w.startswith(prefix_l) and w not in seen:
                score = WEIGHTS['usage_freq'] + (cnt * 5)
                results.append((w, score))
                seen.add(w)
                
        if self.dict_index:
            for w in self.dict_index.prefix_search(prefix_l, limit=15):
                if w not in seen:
                    score = WEIGHTS['dictionary']
                    if len(w) - len(prefix_l) <= 3: score += 50
                    results.append((w, score))
                    seen.add(w)
                    
        if lang == 'roman_urdu':
            for w in self._ru_corrections.keys():
                if w.startswith(prefix_l) and w not in seen:
                    results.append((w, WEIGHTS['roman_urdu']))
                    seen.add(w)
                    
        for w in self.get_all_custom_words():
            if w.lower().startswith(prefix_l) and w not in seen:
                results.append((w, WEIGHTS['custom']))
                seen.add(w)
                
        results.sort(key=lambda x: x[1], reverse=True)
        return [w for w, _ in results[:MAX_SUGGESTIONS]]

    def learn_from_selection(self, original_word, selected_word, prev_word=''):
        if prev_word:
            key = f"{prev_word}|{original_word.lower()}"
            if key not in self.word_pairs: self.word_pairs[key] = {}
            self.word_pairs[key][selected_word] = self.word_pairs[key].get(selected_word, 0) + 1
            if len(self.word_pairs) > 1000:
                oldest = next(iter(self.word_pairs))
                del self.word_pairs[oldest]
            bg_writer.save(WORD_PAIRS_FILE, self.word_pairs)
            
        self.recency_tracker[selected_word] = time.time()
        if len(self.recency_tracker) > 500:
            sorted_items = sorted(self.recency_tracker.items(), key=lambda x: x[1])
            self.recency_tracker = dict(sorted_items[-500:])
        bg_writer.save(RECENCY_FILE, self.recency_tracker)

    def learn_word(self, word, lang='english'):
        w = word.lower()
        if lang == 'roman_urdu':
            self.ru_learning[w] = self.ru_learning.get(w, 0) + 1
            if self.ru_learning[w] % 10 == 0: bg_writer.save(RU_LEARNING_FILE, self.ru_learning)
        else:
            self.user_learning[w] = self.user_learning.get(w, 0) + 1
            if self.user_learning[w] % 10 == 0: bg_writer.save(USER_LEARNING_FILE, self.user_learning)

    def record_usage(self, word):
        w = word.lower()
        self.usage_stats[w] = self.usage_stats.get(w, 0) + 1
        if len(self.usage_stats) % 50 == 0: bg_writer.save(USAGE_STATS_FILE, self.usage_stats)

    def _load_sequences(self):
        data = self._load_json(SEQUENCES_FILE, {})
        self.sequence_learner.sequences = data.get('pairs', {})
        self.sequence_learner.trigrams = data.get('trigrams', {})
        self._load_common_sequences()

    def _save_sequences(self):
        bg_writer.save(SEQUENCES_FILE, {'pairs': self.sequence_learner.sequences, 'trigrams': self.sequence_learner.trigrams})

    def _load_common_sequences(self):
        common = {
            'how': {'are': 100, 'to': 80, 'do': 70, 'is': 60},
            'are': {'you': 100, 'we': 60, 'they': 50, 'your': 40},
            'i': {'am': 100, 'have': 80, 'want': 70, 'need': 60, 'will': 50},
            'you': {'are': 90, 'have': 70, 'want': 60, 'can': 50},
            'thank': {'you': 100},
            'thanks': {'for': 90, 'you': 70},
            'please': {'help': 80, 'let': 70, 'send': 60},
            'can': {'you': 90, 'i': 80, 'we': 60},
            'will': {'be': 80, 'have': 70, 'do': 60},
            'would': {'like': 90, 'be': 80, 'have': 70},
            'assalam': {'o': 100},
            'o': {'alaikum': 100},
            'alaikum': {'assalam': 80},
            'shukriya': {'bohat': 90},
            'mein': {'thik': 80, 'ja': 70, 'karta': 60},
            'thik': {'hoon': 100},
            'karta': {'hoon': 90},
            'what': {'is': 80, 'are': 70, 'do': 60},
            'where': {'is': 80, 'are': 70, 'do': 50},
            'when': {'is': 80, 'do': 60, 'will': 50},
            'let': {'me': 90, 'us': 80},
            "let's": {'go': 90, 'see': 70},
            'going': {'to': 90, 'for': 60},
            'want': {'to': 90, 'a': 50, 'the': 40},
            'need': {'to': 90, 'a': 50, 'the': 40},
            'have': {'to': 70, 'a': 60, 'the': 50},
            'has': {'to': 70, 'been': 60, 'a': 50},
            'do': {'you': 80, 'we': 60, 'not': 50},
            'does': {'not': 80, 'the': 50},
            'did': {'you': 80, 'not': 60, 'we': 50},
            'should': {'be': 80, 'have': 70, 'we': 60},
            'could': {'be': 80, 'have': 70, 'you': 60},
            'would': {'like': 80, 'be': 70, 'you': 60},
            'this': {'is': 80, 'will': 50, 'has': 40},
            'that': {'is': 80, 'was': 70, 'will': 60},
            'there': {'is': 90, 'are': 80, 'was': 50},
            'here': {'is': 90, 'are': 70},
            'well': {'done': 80, 'said': 60},
            'very': {'good': 80, 'much': 70, 'well': 60},
            'all': {'the': 70, 'of': 60, 'is': 50},
            'some': {'of': 70, 'are': 60, 'people': 50},
            'more': {'than': 80, 'and': 50, 'of': 40},
            'also': {'have': 60, 'be': 50, 'has': 40},
            'just': {'want': 60, 'got': 50, 'like': 40},
            'still': {'have': 50, 'be': 40, 'going': 40},
            'already': {'have': 70, 'done': 60, 'been': 50},
            'never': {'have': 60, 'been': 50, 'thought': 40},
            'always': {'be': 70, 'have': 60, 'wanted': 50},
            'often': {'have': 50, 'go': 40, 'see': 30},
            'quite': {'a': 60, 'good': 50, 'well': 40},
        }
        for word, next_words in common.items():
            if word not in self.sequence_learner.sequences: self.sequence_learner.sequences[word] = {}
            for nw, count in next_words.items():
                if nw not in self.sequence_learner.sequences[word]:
                    self.sequence_learner.sequences[word][nw] = count

    def learn_from_text(self, text):
        words = re.findall(r"[a-zA-Z\u0600-\u06FF']+", text.lower())
        if len(words) >= 2:
            self.word_history.extend(words)
            self.sequence_learner.learn(list(self.word_history))
            if len(self.word_history) % 10 == 0: self._save_sequences()

    def predict_next_word(self, current_word):
        prev_word = self.word_history[-1] if len(self.word_history) >= 1 else None
        return self.sequence_learner.predict_next(current_word, prev_word)

    def get_smart_matches_with_prediction(self, prefix, lang='english'):
        suggestions = []
        prefix_l = prefix.lower()
        predictions = self.predict_next_word(prefix_l)
        for pred in predictions[:3]:
            if pred.startswith(prefix_l) or len(prefix_l) >= 2:
                suggestions.append(pred)
        regular = self.get_smart_matches_enhanced(prefix, lang)
        for m in regular:
            if m.lower() != prefix_l and m not in suggestions:
                suggestions.append(m)
        return suggestions[:MAX_SUGGESTIONS]

# =============================================================
# LANGUAGE DETECTOR
# =============================================================
class LanguageDetector:
    __slots__ = ('urdu_chars',)
    ENGLISH_COMMON = {
        'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i',
        'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at',
        'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her', 'she'
    }
    ROMAN_URDU_COMMON = {'hai', 'hain', 'tha', 'thi', 'ho', 'mein', 'tum', 'wo', 'woh', 'yeh', 'hum', 'aap', 'kya', 'kyun', 'kaise', 'nahi', 'haan', 'acha'}
    COMMON_TYPOS = {'teh', 'becuase', 'recieve', 'seperate', 'definately', 'adn', 'acn', 'taht'}

    def __init__(self):
        self.urdu_chars = set('ابپتٹثجچحخدڈذرزژسشصضطظعغفقکگلمنہوےؤئى')

    def detect(self, text):
        if not text or len(text.strip()) < 1: return 'english'
        text = text.strip().lower()
        words = text.split()
        if not words: return 'english'
        
        last_word = words[-1]
        if any(ch in self.urdu_chars for ch in last_word): return 'urdu_script'
        if last_word in self.COMMON_TYPOS or last_word in self.ENGLISH_COMMON: return 'english'
        if last_word in self.ROMAN_URDU_COMMON: return 'roman_urdu'
        
        if re.search(r'(th|ng|ck|tion|ing|ment)$', last_word): return 'english'
        if last_word.endswith('h') and len(last_word) > 2: return 'roman_urdu'
        return 'english'

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
            self.listbox.insert(tk.END, f" {item}")
        self.listbox.select_set(0)
        self.listbox.activate(0)

    def _on_mouse_click(self, event):
        idx = self.listbox.nearest(event.y)
        if 0 <= idx < len(self.suggestions):
            self.close()
            self.on_select(self.current_word, self.suggestions[idx])

    def select_next(self):
        if not self.listbox or not self.suggestions: return
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
        if not self.listbox or not self.suggestions: return
        idx = self.listbox.curselection()
        if idx and idx[0] > 0:
            new = idx[0] - 1
            self.listbox.select_clear(idx[0])
            self.listbox.select_set(new)
            self.listbox.activate(new)
            self.listbox.see(new)

    def confirm_selected(self):
        if not self.listbox or not self.suggestions: return
        idx = self.listbox.curselection()
        if idx:
            word = self.suggestions[idx[0]]
            self.close()
            self.root.after(10, lambda: self.on_select(self.current_word, word))

    def close(self):
        self.active = False
        if self.top:
            try: self.top.destroy()
            except Exception: pass
            self.top = None
            self.listbox = None

# =============================================================
# SESSION TRACKER
# =============================================================
class SessionTracker:
    __slots__ = ('session_file', 'help_data')

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
        except Exception: pass

    def record_help(self, app_name, original_word, corrected_word, language):
        if not app_name: app_name = "Unknown"
        if app_name not in self.help_data['apps_helped']: self.help_data['apps_helped'][app_name] = 0
        self.help_data['apps_helped'][app_name] += 1
        self.help_data['total_corrections'] += 1
        self.help_data['words_corrected'].append({
            'time': datetime.now().isoformat(), 'app': app_name,
            'from': original_word, 'to': corrected_word, 'lang': language
        })
        if len(self.help_data['words_corrected']) > 50:
            self.help_data['words_corrected'] = self.help_data['words_corrected'][-50:]
        self.help_data['languages_used'].add(language)

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
        except Exception: return 'Unknown'

    def get_summary(self):
        s = f"Start: {self.help_data['session_start'][:19]} | PC: {self.help_data['computer_name']} | OS: {self.help_data['os']}\n"
        s += f"Corrections: {self.help_data['total_corrections']} | Languages: {', '.join(self.help_data['languages_used'])}\n"
        for app, count in self.help_data['apps_helped'].items():
            s += f"  {app}: {count}x\n"
        return s

    def cleanup(self):
        if self.session_file and os.path.exists(self.session_file):
            try: os.remove(self.session_file)
            except Exception: pass

# =============================================================
# ROMAN URDU DATA
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
# GLOBAL ASSISTANT (Main Engine)
# =============================================================
class GlobalAssistant:
    __slots__ = ('dm', 'lang_detector', 'session', 'keyboard', 'enabled', 
                 'is_inserting', 'last_ctrl_t', 'typing_buffer', 'buffer_lock', 
                 'event_queue', 'listener', 'root', 'popup', 'current_lang', 'suppress_next_space')

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
        self.suppress_next_space = False

        if HAVE_KEYBOARD:
            try:
                kb_lib.add_hotkey('ctrl+alt+x', self.toggle_assistant)
                kb_lib.add_hotkey('ctrl+alt+s', self.show_session_summary)
            except Exception: pass

    def toggle_assistant(self):
        self.enabled = not self.enabled
        print(f" Assistant {'ON' if self.enabled else 'OFF'}")

    def show_session_summary(self):
        print("\n" + "=" * 50)
        print(" ALPHA SESSION SUMMARY")
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
            if len(text.strip()) < 1: return 'english'
            detected = self.lang_detector.detect(text)
            return detected if detected != 'unknown' else 'english'

    def _get_suggestions(self, word, lang):
        suggestions = []
        with self.buffer_lock:
            text = ''.join(self.typing_buffer)
            words_list = re.findall(r"[a-zA-Z\u0600-\u06FF']+", text)
            prev_word = words_list[-2] if len(words_list) >= 2 else ''
            
            if lang == 'english':
                corrected = self.dm.correct_error(word, 'english')
                if corrected != word: suggestions.append(f"🔧 {corrected}")
                for m in self.dm.get_smart_matches_with_prediction(word, 'english'):
                    if m.lower() != word.lower(): suggestions.append(m)
            elif lang == 'roman_urdu':
                corrected = self.dm.correct_error(word, 'roman_urdu')
                if corrected != word: suggestions.append(f"🇵🇰 {corrected}")
                for m in self.dm.get_smart_matches_with_prediction(word, 'roman_urdu'):
                    if m.lower() != word.lower() and m not in suggestions: suggestions.append(m)
            elif lang == 'urdu_script':
                suggestions.append(f"📜 {word}")
                
            preds = self.dm.predict_next_word(word.lower())
            for p in preds:
                full = f"{word} {p}"
                if full not in suggestions: suggestions.append(f"→ {full}")
                
        return suggestions[:MAX_SUGGESTIONS]

    def _on_suggestion_selected(self, original_word, suggestion):
        for prefix in ["🔧 ", "🇵🇰 ", "📜 ", "→ "]:
            if suggestion.startswith(prefix):
                suggestion = suggestion[len(prefix):]
                break
                
        with self.buffer_lock:
            text = ''.join(self.typing_buffer)
            words_list = re.findall(r"[a-zA-Z\u0600-\u06FF']+", text)
            prev_word = words_list[-2] if len(words_list) >= 2 else ''
            
        self.dm.learn_from_selection(original_word, suggestion, prev_word)
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

    def _win32_event_filter(self, msg, data):
        if self.popup and self.popup.active:
            if data.vkCode in (13, 9, 27, 38, 40):
                if msg == 256:  # WM_KEYDOWN
                    if data.vkCode == 13: self.event_queue.put(('confirm',))
                    elif data.vkCode == 9: self.event_queue.put(('confirm',))
                    elif data.vkCode == 38: self.event_queue.put(('up',))
                    elif data.vkCode == 40: self.event_queue.put(('down',))
                    elif data.vkCode == 27: self.event_queue.put(('close',))
                    
                    if self.listener: self.listener.suppress_event()
                    return False
                    
        if (self.suppress_next_space or self.is_inserting) and msg == 256 and data.vkCode == 32:
            self.suppress_next_space = False
            if self.listener: self.listener.suppress_event()
            return False
            
        return True

    def on_press(self, key):
        if self.is_inserting: return True
        update_caret_position()
        
        try:
            if key in (pynput_keyboard.Key.ctrl_l, pynput_keyboard.Key.ctrl_r):
                now = time.time()
                if now - self.last_ctrl_t < DEBOUNCE_TIME:
                    self.event_queue.put(('force_show',))
                self.last_ctrl_t = now
                return True
                
            if key in (pynput_keyboard.Key.left, pynput_keyboard.Key.right):
                with self.buffer_lock: self.typing_buffer.clear()
                self.event_queue.put(('close',))
                return True
                
            if not self.enabled: return True
            
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
                        self.suppress_next_space = True
                        with self.buffer_lock: self.typing_buffer.clear()
                        self.event_queue.put(('close',))
                        self._insert_suggestion(word, corrected + " ", lang, extra_bs=0)
                        self.dm.learn_from_text(corrected + " ")
                        return True
                    else:
                        self.dm.learn_word(word, lang)
                        with self.buffer_lock:
                            text = ''.join(self.typing_buffer)
                            self.dm.learn_from_text(text)
                with self.buffer_lock:
                    self.typing_buffer.clear()
                self.event_queue.put(('close',))
                
            elif key == pynput_keyboard.Key.backspace:
                with self.buffer_lock:
                    if self.typing_buffer: self.typing_buffer.pop()
                    self.event_queue.put(('suggest', self._get_current_word()))
                    
            elif key == pynput_keyboard.Key.enter:
                word = self._get_current_word()
                if word:
                    lang = self._detect_language()
                    self.dm.learn_word(word, lang)
                    with self.buffer_lock:
                        text = ''.join(self.typing_buffer)
                        self.dm.learn_from_text(text)
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
                    if not self.enabled: self.popup.close()
                    else:
                        word = event[1] if len(event) > 1 else self._get_current_word()
                        if len(word) >= MIN_WORD_LENGTH:
                            self.current_lang = self._detect_language()
                            suggestions = self._get_suggestions(word, self.current_lang)
                            if suggestions:
                                x, y = get_caret_position()
                                self.popup.show(suggestions, word, x, y)
                            else: self.popup.close()
                        else: self.popup.close()
                elif cmd == 'force_show':
                    word = self._get_current_word()
                    if word and self.enabled:
                        self.current_lang = self._detect_language()
                        suggestions = self._get_suggestions(word, self.current_lang)
                        if suggestions:
                            x, y = get_caret_position()
                            self.popup.show(suggestions, word, x, y)
                elif cmd == 'up': self.popup.select_prev()
                elif cmd == 'down': self.popup.select_next()
                elif cmd == 'confirm': self.popup.confirm_selected()
                elif cmd in ('close', 'popup_close'): self.popup.close()
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
        
        def update_dots(count=0):
            try:
                if not splash.winfo_exists(): return
                dots = "." * (count % 4)
                canvas.itemconfig(status_id, text=f"✓ System Ready{dots}")
                splash.after(400, lambda: update_dots(count + 1))
            except Exception: pass

        splash.after(400, update_dots)
        splash.bind("<Button-1>", lambda e: splash.destroy())
        splash.after(3500, splash.destroy)

    def start(self):
        print("=" * 50)
        print(" ALPHA Typing Assistant v3.5 FINAL")
        print(" English + Roman Urdu | Universal Compatibility")
        print(" Hotkeys: Ctrl+Alt+X (Toggle), Ctrl+Alt+S (Summary)")
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
        
        if self.listener.running: print(" ✓ Active")
        else: print(" ✗ Run as Administrator for full functionality")
        
        self.root.after(POLL_INTERVAL_MS, self._poll_queue)
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            pass
        finally:
            self.popup.close()
            if self.listener: self.listener.stop()
            bg_writer.save(USER_LEARNING_FILE, self.dm.user_learning)
            bg_writer.save(USAGE_STATS_FILE, self.dm.usage_stats)
            bg_writer.shutdown()
            print("=" * 50)
            print(self.session.get_summary())
            print("=" * 50)
            print(" Goodbye!")
            print("=" * 50)

if __name__ == "__main__":
    assistant = GlobalAssistant()
    assistant.start()
