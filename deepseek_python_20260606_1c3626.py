"""
Global Typing Assistant PRO — v2.1 (Cleaned & Optimized)
Author: Abdul Moiz Ansari
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
FOCUS_RETURN_DELAY = 0.05
POLL_INTERVAL_MS   = 60
LEARN_MIN_LEN      = 4
LEARN_ALPHA_RATIO  = 0.7

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
# FAST DICTIONARY INDEX (bisect)
# ══════════════════════════════════════════════════════════════════
class DictIndex:
    def __init__(self, words):
        self._words = sorted(set(w for w in words if len(w) >= 2), key=str.lower)
        self._keys  = [w.lower() for w in self._words]
        print(f"[Dict] {len(self._words):,} words indexed")

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

# ══════════════════════════════════════════════════════════════════
# DATA MANAGER
# ══════════════════════════════════════════════════════════════════
class DataManager:
    def __init__(self):
        print("[DataManager] Loading files...")
        self.suggestions   = self._load_json(SUGGESTIONS_FILE, {})
        self.user_learning = self._load_json(USER_LEARNING_FILE, {})
        self.usage_stats   = self._load_json(USAGE_STATS_FILE, {})
        self.dict_index    = self._build_dict_index()
        
        # 🔥 SANITIZE ERRORS ON LOAD (prevents trailing space bugs)
        raw_errors = self._load_json(ERRORS_FILE, {})
        self.errors = {k.strip().lower(): v.strip() for k, v in raw_errors.items() if k.strip()}
        
        print(f"[DataManager] Ready. {len(self.errors):,} error mappings loaded.")

    @staticmethod
    def _load_json(path, default):
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return default
        except Exception as e:
            print(f"[DataManager] Load error {path}: {e}")
            return default

    def _build_dict_index(self):
        raw = self._load_json(DICTIONARY_FILE, [])
        return DictIndex(raw) if isinstance(raw, list) and raw else None

    def get_all_custom_words(self):
        words = []
        for cat_words in self.suggestions.values():
            words.extend(cat_words)
        return words

    def correct_error(self, word):
        w = word.lower()
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

    def get_smart_matches(self, prefix):
        if not prefix or len(prefix) < MIN_WORD_LENGTH:
            return []
        prefix_l = prefix.lower()
        seen = set()
        results = []

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

    def _is_quality_word(self, word):
        if len(word) < LEARN_MIN_LEN:
            return False
        alpha_count = sum(1 for c in word if c.isalpha())
        if alpha_count / len(word) < LEARN_ALPHA_RATIO:
            return False
        if self.dict_index and self.dict_index.exact_match(word):
            return False
        return True

    def learn_word(self, word):
        if not self._is_quality_word(word):
            return
        w = word.lower()
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
        except Exception as e:
            print(f"[DataManager] Save error: {e}")

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
            self.listbox.insert(tk.END, f"  {item}")
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

    def confirm_selected(self, key_used='tab'):
        if not self.listbox or not self.suggestions: return
        idx = self.listbox.curselection()
        if idx:
            self.close()
            extra = 1 if key_used == 'enter' else 0
            self.on_select(self.current_word, self.suggestions[idx[0]], extra_bs=extra)

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
        self.enabled = True
        self.is_inserting = False
        self.last_ctrl_t = 0
        self.typing_buffer = deque(maxlen=80)
        self.event_queue = queue.Queue()
        self.root = tk.Tk()
        self.root.withdraw()
        self.popup = SuggestionPopup(self.root, self._resolve_suggestion)

    def _get_current_word(self):
        text = ''.join(self.typing_buffer)
        words = re.findall(r"[a-zA-Z\u0600-\u06FF']+", text)
        return words[-1] if words else ""

    def _resolve_suggestion(self, original_word, raw_selection, extra_bs=0):
        suggestion = raw_selection[6:] if raw_selection.startswith("[Fix] ") else raw_selection
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
            old_clip = ""
            try: old_clip = pyperclip.paste()
            except: pass
            pyperclip.copy(suggestion)
            total_bs = len(original_word) + extra_bs
            pyautogui.write('\b' * total_bs, interval=0.0)
            pyautogui.hotkey('ctrl', 'v')
            try: pyperclip.copy(old_clip)
            except: pass
        except Exception as e:
            print(f"[Insert] Error: {e}")
        finally:
            pyautogui.PAUSE = old_pause
            self.is_inserting = False
            self.typing_buffer.clear()

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

            if self.popup.active:
                if key == pynput_keyboard.Key.down: self.event_queue.put(('popup_down',)); return True
                if key == pynput_keyboard.Key.up: self.event_queue.put(('popup_up',)); return True
                if key == pynput_keyboard.Key.enter: self.event_queue.put(('popup_confirm', 'enter')); return True
                if key == pynput_keyboard.Key.tab: self.event_queue.put(('popup_confirm', 'tab')); return True
                if key == pynput_keyboard.Key.esc: self.event_queue.put(('popup_close',)); return True

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
                    corrected = self.dm.correct_error(word)
                    if corrected != word:
                        print(f"[AutoCorrect] '{word}' → '{corrected}'")
                        self.typing_buffer.clear()
                        self.event_queue.put(('popup_close',))
                        self._apply_suggestion(word, corrected + " ", extra_bs=1)
                        return True
                    else:
                        self.dm.learn_word(word)
                self.typing_buffer.clear()
                self.event_queue.put(('popup_close',))

            elif key == pynput_keyboard.Key.backspace:
                if self.typing_buffer: self.typing_buffer.pop()
                self.event_queue.put(('suggest', self._get_current_word()))

            elif key == pynput_keyboard.Key.enter:
                word = self._get_current_word()
                if word: self.dm.learn_word(word)
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
                    if not self.enabled: self.popup.close()
                    else:
                        word = event[1] if len(event) > 1 else self._get_current_word()
                        if len(word) >= MIN_WORD_LENGTH:
                            corrected = self.dm.correct_error(word)
                            matches = self.dm.get_smart_matches(word)
                            final_list = []
                            if corrected != word and corrected not in matches:
                                final_list.append(f"[Fix] {corrected}")
                            for m in matches:
                                if m.lower() != word.lower(): final_list.append(m)
                            if final_list:
                                x, y = get_caret_position()
                                self.popup.show(final_list[:MAX_SUGGESTIONS], word, x, y)
                            else: self.popup.close()
                        else: self.popup.close()
                elif cmd == 'force_show':
                    word = self._get_current_word()
                    if word and self.enabled:
                        corrected = self.dm.correct_error(word)
                        matches = self.dm.get_smart_matches(word)
                        final_list = []
                        if corrected != word: final_list.append(f"[Fix] {corrected}")
                        final_list.extend(m for m in matches if m.lower() != word.lower())
                        if final_list:
                            x, y = get_caret_position()
                            self.popup.show(final_list[:MAX_SUGGESTIONS], word, x, y)
                elif cmd == 'popup_down': self.popup.select_next()
                elif cmd == 'popup_up': self.popup.select_prev()
                elif cmd == 'popup_confirm':
                    key_used = event[1] if isinstance(event, tuple) and len(event) > 1 else 'tab'
                    self.popup.confirm_selected(key_used)
                elif cmd == 'popup_close': self.popup.close()
        except queue.Empty: pass
        finally:
            self.root.after(POLL_INTERVAL_MS, self._poll_queue)

    def show_splash(self):
        splash = tk.Toplevel(self.root)
        splash.title("Alpha")
        splash.overrideredirect(True)
        splash.attributes('-topmost', True)
        w, h = 420, 220
        sw, sh = splash.winfo_screenwidth(), splash.winfo_screenheight()
        splash.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
        canvas = tk.Canvas(splash, width=w, height=h, bg="#001a33", highlightthickness=0)
        canvas.pack()
        canvas.create_text(w//2, 50, text="ALPHA", fill="#00bfff", font=("Segoe UI", 32, "bold"))
        canvas.create_text(w//2, 100, text="AI Typing Assistant", fill="#66d9ff", font=("Segoe UI", 14))
        canvas.create_line(60, 130, w-60, 130, fill="#00bfff", width=1)
        canvas.create_text(w//2, 155, text="Reserved by Moiz Digital Service", fill="#cccccc", font=("Segoe UI", 11))
        canvas.create_text(w//2, 185, text="© 2026 All Rights Reserved", fill="#888888", font=("Segoe UI", 9))
        splash.bind("<Button-1>", lambda e: splash.destroy())
        splash.after(3000, splash.destroy())

    def start(self):
        print("=" * 60)
        print("  ⌨️  Global Typing Assistant PRO v2.1 — Sanitized & Optimized")
        print("=" * 60)
        self.show_splash()
        listener = pynput_keyboard.Listener(on_press=self.on_press, suppress=False)
        listener.daemon = True
        listener.start()
        time.sleep(0.2)
        print(f"  [Listener] {'✅ Active' if listener.running else '❌ FAILED — Run as Admin'}")
        self.root.after(POLL_INTERVAL_MS, self._poll_queue)
        try:
            self.root.mainloop()
        except KeyboardInterrupt: pass
        except Exception as e:
            print(f"[App] Error: {e}")
            import traceback; traceback.print_exc()
        finally:
            self.popup.close()
            listener.stop()
            DataManager._save_json(USER_LEARNING_FILE, self.dm.user_learning)
            DataManager._save_json(USAGE_STATS_FILE, self.dm.usage_stats)
            print("[App] Goodbye!")

if __name__ == "__main__":
    assistant = GlobalAssistant()
    assistant.start()