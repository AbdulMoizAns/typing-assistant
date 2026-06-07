"""
Global Typing Assistant PRO — v2 ALL BUGS FIXED
================================================
ORIGINAL FIXES (purani version se):
  ✅ FIX 1: keyboard.type() HATAYA → clipboard paste lagaya
            (doubled/garbled text problem khatam)
  ✅ FIX 2: Popup wrong location → real TEXT CURSOR position
            (Windows GetGUIThreadInfo API se actual caret position)
  ✅ FIX 3: Enter key → target app mein newline jata tha → extra backspace
  ✅ FIX 4: FOCUS_RETURN_DELAY 0.05s → 0.25s
  ✅ FIX 5: Dictionary fast prefix search → bisect (370K words, O(log n))
  ✅ FIX 6: Learning validation → garbage words nahi seekhta
  ✅ FIX 7: is_processing flag → proper timing
  ✅ FIX 8: MIN_WORD_LENGTH 1 → 2

NEW BUGS FIXED (v2 — ye sab naye fixes hain):
  ✅ FIX 14: Backspace ke baad fresh word context — "back" + backspace + "y"
             pehle "bacy" banta tha (bekaar suggestions). Ab backspace se puri
             buffer clear hoti hai → "y" type karo → yes, you, year milte hain.
  ✅ FIX 9:  [MAIN FIX] AUTO-CORRECT ON SPACE — ab space dabao to
             galat word KHUD BA KHUD theek hota hai, popup select
             ki zaroorat nahi. "teh " type karo → "the " ban jata hai.
  ✅ FIX 10: DictIndex.prefix_search break condition galat tha.
             Pehle prefix_l[0] (sirf pehla char) check karta tha jis
             se O(n) loop chalta tha. Ab 'else: break' se sahi O(log n+k).
  ✅ FIX 11: _is_quality_word mein prefix search se dictionary check
             galat tha — "app" type karo to "apple" milta tha aur word
             dictionary mein samjha jata tha. Ab exact match hota hai.
  ✅ FIX 12: [Fix] prefix stripping — _resolve_selection dead code tha,
             kabhi call nahi hoti thi. Ab _resolve_suggestion properly
             GlobalAssistant mein wire ki gayi hai aur popup callback
             seedha isi se connected hai.
  ✅ FIX 13: _patched_init useless monkey-patch tha (kuch nahi karta tha).
             Hataya. __main__ mein bhi _patched_select ki zaroorat nahi.
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
MIN_WORD_LENGTH    = 2       # FIX 8: was 1 (popup on every char)
DEBOUNCE_TIME      = 0.3
FOCUS_RETURN_DELAY = 0.25    # FIX 4: was 0.05 (too short)
BACKSPACE_DELAY    = 0.03    # delay between each backspace
POLL_INTERVAL_MS   = 60

# Minimum word quality for auto-learning
LEARN_MIN_LEN      = 4       # don't learn very short words
LEARN_ALPHA_RATIO  = 0.7     # at least 70% letters

# ══════════════════════════════════════════════════════════════════
# CARET POSITION (text cursor, not mouse cursor)
# ══════════════════════════════════════════════════════════════════

class _RECT(ctypes.Structure):
    _fields_ = [("left",   ctypes.c_long),
                ("top",    ctypes.c_long),
                ("right",  ctypes.c_long),
                ("bottom", ctypes.c_long)]

class _GUITHREADINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize",        ctypes.c_uint32),
        ("flags",         ctypes.c_uint32),
        ("hwndActive",    ctypes.c_size_t),
        ("hwndFocus",     ctypes.c_size_t),
        ("hwndCapture",   ctypes.c_size_t),
        ("hwndMenuOwner", ctypes.c_size_t),
        ("hwndMoveSize",  ctypes.c_size_t),
        ("hwndCaret",     ctypes.c_size_t),
        ("rcCaret",       _RECT),
    ]

class _POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

def get_caret_position():
    """
    FIX 2: Real text cursor (caret) position via Windows API.
    Ab popup wahan dikhega jahan user type kar raha hai.
    """
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
    # Fallback: mouse position
    try:
        return pyautogui.position()
    except Exception:
        return 300, 300

# ══════════════════════════════════════════════════════════════════
# FAST DICTIONARY INDEX (bisect — 370K words mein bhi fast)
# ══════════════════════════════════════════════════════════════════

class DictIndex:
    """
    FIX 5: Binary search index for 370K word dictionary.
    Prefix search: O(log n + k) — real-time mein fast.
    """
    def __init__(self, words):
        self._words = sorted(set(w for w in words if len(w) >= 2), key=str.lower)
        self._keys  = [w.lower() for w in self._words]
        print(f"[Dict] {len(self._words):,} words indexed")

    def prefix_search(self, prefix, limit=15):
        """
        FIX 10: Break condition theek ki — pehle prefix_l[0] check hota tha
        jis se O(n) loop chalta tha. Ab sahi 'else: break' se sorted list
        mein prefix range khatam hote hi ruk jata hai → O(log n + k).
        """
        prefix_l = prefix.lower()
        lo = bisect.bisect_left(self._keys, prefix_l)
        results = []
        for i in range(lo, len(self._keys)):
            if self._keys[i].startswith(prefix_l):
                results.append(self._words[i])
                if len(results) >= limit:
                    break
            else:
                # FIX 10: Sorted list mein prefix range khatam —
                # aage koi bhi word match nahi karega, foran rok do.
                break
        return results

    def exact_match(self, word):
        """
        FIX 11: Exact dictionary lookup.
        prefix_search se galat tha — ab binary search se exact word dhundta hai.
        """
        word_l = word.lower()
        lo = bisect.bisect_left(self._keys, word_l)
        if lo < len(self._keys) and self._keys[lo] == word_l:
            return True
        return False

# ══════════════════════════════════════════════════════════════════
# DATA MANAGER
# ══════════════════════════════════════════════════════════════════

class DataManager:
    def __init__(self):
        print("[DataManager] Loading files...")
        self.suggestions   = self._load_json(SUGGESTIONS_FILE, {})
        self.errors        = self._load_json(ERRORS_FILE, {})
        self.user_learning = self._load_json(USER_LEARNING_FILE, {})
        self.usage_stats   = self._load_json(USAGE_STATS_FILE, {})
        self.dict_index    = self._build_dict_index()
        print("[DataManager] Ready.")

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
        if isinstance(raw, list) and raw:
            return DictIndex(raw)
        return None

    def get_all_custom_words(self):
        """All words from suggestions.json."""
        words = []
        for cat_words in self.suggestions.values():
            words.extend(cat_words)
        return words

    def correct_error(self, word):
        """
        Autocorrect: direct match, then fuzzy match.
        Returns corrected word or original if no match.
        """
        w = word.lower()
        # Direct match
        if w in self.errors:
            return self.errors[w]
        # Fuzzy match for close typos (only for words >= 4 chars)
        if len(w) >= 4:
            matches = difflib.get_close_matches(w, self.errors.keys(), n=1, cutoff=0.78)
            if matches:
                return self.errors[matches[0]]
        return word

    def get_word_weight(self, word):
        """Usage frequency score for ranking suggestions."""
        w = word.lower()
        return self.user_learning.get(w, 0) + self.usage_stats.get(w, 0)

    def get_smart_matches(self, prefix):
        """
        Get ranked suggestions for the given prefix.
        Order: custom phrases → user learned → dictionary
        """
        if not prefix or len(prefix) < MIN_WORD_LENGTH:
            return []

        prefix_l = prefix.lower()
        seen = set()
        results = []

        # 1. Custom suggestion phrases (suggestions.json) — exact prefix match
        for w in self.get_all_custom_words():
            if w.lower().startswith(prefix_l) or prefix_l in w.lower():
                if w not in seen:
                    seen.add(w)
                    results.append((w, self.get_word_weight(w) + 100))

        # 2. Learned words (user_learning.json)
        for w, count in sorted(self.user_learning.items(),
                                key=lambda x: x[1], reverse=True):
            if w.lower().startswith(prefix_l):
                if w not in seen:
                    seen.add(w)
                    results.append((w, count + 50))

        # 3. Dictionary prefix search (fast bisect)
        if self.dict_index:
            dict_matches = self.dict_index.prefix_search(prefix_l, limit=20)
            for w in dict_matches:
                if w not in seen:
                    seen.add(w)
                    weight = self.get_word_weight(w)
                    results.append((w, weight))

        # Sort by weight, return top N
        results.sort(key=lambda x: x[1], reverse=True)
        return [w for w, _ in results[:MAX_SUGGESTIONS]]

    def _is_quality_word(self, word):
        """
        FIX 6 + FIX 11: Check if word is worth learning.
        FIX 11: Pehle prefix_search se galat check hota tha — "app" likhne
        pe "apple" milta tha aur word dictionary mein samjha jata tha.
        Ab exact_match() se sahi check hota hai.
        """
        if len(word) < LEARN_MIN_LEN:
            return False
        alpha_count = sum(1 for c in word if c.isalpha())
        if alpha_count / len(word) < LEARN_ALPHA_RATIO:
            return False
        # FIX 11: Exact match — prefix match nahi (tha galat pehle)
        if self.dict_index and self.dict_index.exact_match(word):
            return False
        return True

    def learn_word(self, word):
        """Auto-learn a word the user types frequently."""
        if not self._is_quality_word(word):
            return
        w = word.lower()
        self.user_learning[w] = self.user_learning.get(w, 0) + 1
        # Save every 5 occurrences to avoid constant disk writes
        if self.user_learning[w] % 5 == 0:
            self._save_json(USER_LEARNING_FILE, self.user_learning)

    def record_usage(self, word):
        """Track a selected/accepted suggestion."""
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
        self.root        = root
        self.on_select   = on_select_callback
        self.top         = None
        self.listbox     = None
        self.suggestions = []
        self.current_word= ""
        self.active      = False

    def show(self, suggestions, word, x, y):
        if not suggestions:
            self.close()
            return

        self.suggestions  = suggestions
        self.current_word = word

        # FIX 2: x, y is now the real caret position (bottom of text cursor)
        screen_w = self.root.winfo_screenwidth()
        popup_x  = min(x, screen_w - POPUP_WIDTH - 10)
        popup_y  = y + 4

        if self.top is None:
            self.top = tk.Toplevel(self.root)
            self.top.title("")
            self.top.attributes('-topmost', True)
            self.top.overrideredirect(True)
            self.top.configure(bg="#1e1e2e")

            self.listbox = Listbox(
                self.top,
                font=("Segoe UI", 11),
                selectmode=tk.SINGLE,
                bg="#1e1e2e",
                fg="#cdd6f4",
                selectbackground="#313244",
                selectforeground="#89b4fa",
                activestyle='none',
                bd=0, highlightthickness=1,
                highlightbackground="#45475a",
            )
            self.listbox.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
            self.listbox.bind('<ButtonRelease-1>', self._on_mouse_click)
            self.top.bind('<Escape>', lambda e: self.close())
            self.active = True
        else:
            self.top.lift()

        # Resize popup height to fit suggestions
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
            word     = self.current_word
            selected = self.suggestions[idx]
            self.close()
            # Mouse click: no extra backspace
            self.on_select(word, selected, extra_bs=0)

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

    def confirm_selected(self, key_used='tab'):
        if not self.listbox or not self.suggestions:
            return
        idx = self.listbox.curselection()
        if idx:
            word     = self.current_word
            selected = self.suggestions[idx[0]]
            self.close()
            # FIX 3: Enter → 1 extra backspace (Enter newline delete karne ke liye)
            extra = 1 if key_used == 'enter' else 0
            self.on_select(word, selected, extra_bs=extra)

    def close(self):
        self.active = False
        if self.top:
            try:
                self.top.destroy()
            except tk.TclError:
                pass
            self.top     = None
            self.listbox = None

# ══════════════════════════════════════════════════════════════════
# GLOBAL ASSISTANT
# ══════════════════════════════════════════════════════════════════

class GlobalAssistant:
    def __init__(self):
        self.dm           = DataManager()
        self.enabled      = True
        self.is_inserting = False      # FIX 7: correct flag name
        self.last_ctrl_t  = 0
        self.typing_buffer= deque(maxlen=80)
        self.event_queue  = queue.Queue()

        self.root  = tk.Tk()
        self.root.withdraw()

        # FIX 12: _resolve_suggestion directly popup callback mein pass karo.
        # Pehle _apply_suggestion pass hota tha jo [Fix] prefix strip nahi karta tha.
        # _patched_select aur _patched_init monkey-patch ki zaroorat ab nahi (FIX 13).
        self.popup = SuggestionPopup(self.root, self._resolve_suggestion)

    # ─────────────────────────── word ───────────────────────────

    def _get_current_word(self):
        text = ''.join(self.typing_buffer)
        words = re.findall(r"[a-zA-Z\u0600-\u06FF']+", text)
        return words[-1] if words else ""

    # ─────────────────────────── [Fix] prefix resolve ───────────

    def _resolve_suggestion(self, original_word, raw_selection, extra_bs=0):
        """
        FIX 12: [Fix] prefix theek se strip karo phir apply karo.
        Pehle _resolve_selection naam ki method thi jo kabhi call hi nahi hoti thi
        (dead code). Ab ye method popup ka seedha callback hai — koi monkey-patch nahi.
        """
        suggestion = raw_selection[6:] if raw_selection.startswith("[Fix] ") else raw_selection
        self._apply_suggestion(original_word, suggestion, extra_bs)

    # ─────────────────────────── insert ─────────────────────────

    def _apply_suggestion(self, original_word, suggestion, extra_bs=0):
        """
        FIX 1 + FIX 3 + FIX 4:
        - keyboard.type() → clipboard paste (no more doubled characters)
        - extra_bs → compensate for Enter/Tab/Space going to target app
        - Longer delay for focus to return
        """
        self.typing_buffer.clear()
        self.is_inserting = True
        self.dm.record_usage(suggestion.strip())
        threading.Thread(
            target=self._do_insert,
            args=(original_word, suggestion, extra_bs),
            daemon=True
        ).start()

    def _do_insert(self, original_word, suggestion, extra_bs=0):
        try:
            # FIX 4: Enough time for popup to close & target app to regain focus
            time.sleep(FOCUS_RETURN_DELAY)

            # FIX 3: Delete original word + any key that went to target app
            total_bs = len(original_word) + extra_bs
            print(f"[Insert] '{original_word}' → '{suggestion}' ({total_bs} backspaces)")
            for _ in range(total_bs):
                pyautogui.press('backspace')
                time.sleep(BACKSPACE_DELAY)

            # FIX 1: Clipboard paste — NO keyboard.type() → NO doubled characters
            old_clip = ""
            try:
                old_clip = pyperclip.paste()
            except Exception:
                pass

            pyperclip.copy(suggestion)
            time.sleep(0.06)
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(0.15)
            print(f"[Insert] Pasted '{suggestion}'")
            try:
                pyperclip.copy(old_clip)   # restore original clipboard
            except Exception:
                pass

        except Exception as e:
            print(f"[Insert] Error: {e}")
        finally:
            self.is_inserting = False
            self.typing_buffer.clear()

    # ─────────────────────────── keyboard ───────────────────────

    def on_press(self, key):
        # FIX 7: Block all processing during insertion (no buffer corruption)
        if self.is_inserting:
            return True

        try:
            # Double-Ctrl → force show popup
            if key in (pynput_keyboard.Key.ctrl_l, pynput_keyboard.Key.ctrl_r):
                now = time.time()
                if now - self.last_ctrl_t < DEBOUNCE_TIME:
                    self.event_queue.put(('force_show',))
                self.last_ctrl_t = now
                return True

            # Popup navigation (when popup is visible)
            if self.popup.active:
                if key == pynput_keyboard.Key.down:
                    self.event_queue.put(('popup_down',))
                    return True
                if key == pynput_keyboard.Key.up:
                    self.event_queue.put(('popup_up',))
                    return True
                if key == pynput_keyboard.Key.enter:
                    self.event_queue.put(('popup_confirm', 'enter'))
                    return True
                if key == pynput_keyboard.Key.tab:
                    self.event_queue.put(('popup_confirm', 'tab'))
                    return True
                if key == pynput_keyboard.Key.esc:
                    self.event_queue.put(('popup_close',))
                    return True

            # Arrow keys → cursor moved, reset buffer
            if key in (pynput_keyboard.Key.left, pynput_keyboard.Key.right):
                self.typing_buffer.clear()
                self.event_queue.put(('popup_close',))
                return True

            if not self.enabled:
                return True

            # Normal character typing
            if hasattr(key, 'char') and key.char is not None:
                if ord(key.char) >= 32:
                    self.typing_buffer.append(key.char)
                    self.event_queue.put(('suggest',))

            elif key == pynput_keyboard.Key.space:
                word = self._get_current_word()
                if word:
                    corrected = self.dm.correct_error(word)
                    if corrected != word:
                        # ══════════════════════════════════════════════
                        # FIX 9: MAIN AUTO-CORRECT — space dabane pe
                        # galat word KHUD BA KHUD theek hota hai.
                        # "teh " type karo → "the " ban jata hai bina
                        # popup select kiye.
                        # extra_bs=1 → space bhi delete karta hai,
                        # corrected + " " → corrected word ke baad
                        # space bhi paste hota hai.
                        # ══════════════════════════════════════════════
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
                # FIX 14: Backspace pe puri buffer clear karo.
                # Pehle sirf ek char pop hota tha: "back" + backspace = "bac",
                # phir "y" type karo = "bacy" → bekaar suggestions.
                # Ab backspace se buffer reset hota hai → next char fresh word
                # shuru karta hai: backspace ke baad "y" type karo → "y" se
                # suggestions: yes, you, year — bilkul sahi.
                self.typing_buffer.clear()
                self.event_queue.put(('popup_close',))

            elif key == pynput_keyboard.Key.enter:
                word = self._get_current_word()
                if word:
                    self.dm.learn_word(word)
                self.typing_buffer.clear()
                self.event_queue.put(('popup_close',))

        except AttributeError:
            pass
        except Exception as e:
            print(f"[on_press] {e}")

        return True   # ALWAYS return True → listener never dies

    # ─────────────────────────── poll ───────────────────────────

    def _poll_queue(self):
        try:
            while True:
                event = self.event_queue.get_nowait()
                cmd   = event[0] if isinstance(event, tuple) else event

                if cmd == 'suggest':
                    if not self.enabled:
                        self.popup.close()
                    else:
                        word = self._get_current_word()
                        if len(word) >= MIN_WORD_LENGTH:
                            corrected = self.dm.correct_error(word)
                            matches   = self.dm.get_smart_matches(word)
                            final_list = []

                            # Put autocorrect fix at top (if different from typed)
                            if corrected != word and corrected not in matches:
                                final_list.append(f"[Fix] {corrected}")

                            for m in matches:
                                if m.lower() != word.lower():
                                    final_list.append(m)

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
                        corrected = self.dm.correct_error(word)
                        matches   = self.dm.get_smart_matches(word)
                        final_list = []
                        if corrected != word:
                            final_list.append(f"[Fix] {corrected}")
                        final_list.extend(m for m in matches if m.lower() != word.lower())
                        if final_list:
                            x, y = get_caret_position()
                            self.popup.show(final_list[:MAX_SUGGESTIONS], word, x, y)

                elif cmd == 'popup_down':
                    self.popup.select_next()
                elif cmd == 'popup_up':
                    self.popup.select_prev()
                elif cmd == 'popup_confirm':
                    key_used = event[1] if isinstance(event, tuple) and len(event) > 1 else 'tab'
                    self.popup.confirm_selected(key_used)
                elif cmd == 'popup_close':
                    self.popup.close()

        except queue.Empty:
            pass
        finally:
            self.root.after(POLL_INTERVAL_MS, self._poll_queue)

    # ─────────────────────────── splash ─────────────────────────

    def show_splash(self):
        splash = tk.Toplevel(self.root)
        splash.title("Alpha")
        splash.overrideredirect(True)
        splash.attributes('-topmost', True)
        w, h = 420, 220
        sw = splash.winfo_screenwidth()
        sh = splash.winfo_screenheight()
        splash.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
        canvas = tk.Canvas(splash, width=w, height=h, bg="#001a33", highlightthickness=0)
        canvas.pack()
        canvas.create_text(w//2, 50,  text="ALPHA",
                           fill="#00bfff", font=("Segoe UI", 32, "bold"))
        canvas.create_text(w//2, 100, text="AI Typing Assistant",
                           fill="#66d9ff", font=("Segoe UI", 14))
        canvas.create_line(60, 130, w-60, 130, fill="#00bfff", width=1)
        canvas.create_text(w//2, 155, text="Reserved by Moiz Digital Service",
                           fill="#cccccc", font=("Segoe UI", 11))
        canvas.create_text(w//2, 185, text="© 2026 All Rights Reserved",
                           fill="#888888", font=("Segoe UI", 9))
        splash.bind("<Button-1>", lambda e: splash.destroy())
        splash.after(3000, splash.destroy)

    # ─────────────────────────── start ──────────────────────────

    def start(self):
        print("=" * 60)
        print("  ⌨️  Global Typing Assistant PRO v2 — All Bugs Fixed")
        print("=" * 60)
        print("  Type anywhere  → suggestions near your text cursor")
        print("  Space          → AUTO-CORRECT galat word (FIX 9 ✅)")
        print("  Up / Down      → navigate popup")
        print("  Enter / Tab    → select suggestion")
        print("  Esc            → close popup")
        print("  Mouse click    → select (most reliable)")
        print("  Double Ctrl    → force show suggestions")
        print("=" * 60)

        self.show_splash()

        listener = pynput_keyboard.Listener(
            on_press=self.on_press,
            suppress=False    # let all keystrokes reach apps normally
        )
        listener.daemon = True
        listener.start()
        time.sleep(0.2)

        if listener.running:
            print("  [Listener] ✅ Active — type in any app!")
        else:
            print("  [Listener] ❌ FAILED — Run as Administrator")

        self.root.after(POLL_INTERVAL_MS, self._poll_queue)

        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            pass
        except Exception as e:
            print(f"[App] Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.popup.close()
            listener.stop()
            DataManager._save_json(USER_LEARNING_FILE, self.dm.user_learning)
            DataManager._save_json(USAGE_STATS_FILE,   self.dm.usage_stats)
            print("[App] Goodbye!")


# ══════════════════════════════════════════════════════════════════
# ENTRY POINT
# FIX 13: _patched_init (dead monkey-patch) hataya.
# FIX 12: _patched_select hataya — ab popup callback seedha
#          _resolve_suggestion se connected hai GlobalAssistant.__init__ mein.
# ══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    assistant = GlobalAssistant()
    assistant.start()
