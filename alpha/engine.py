"""Global assistant engine: low level hook, corrections, predictions, insertion."""
from __future__ import annotations

import ctypes
import re
import sys
import threading
import time
from collections import deque

from . import config
from .insertion import TextInjector
from .logging_setup import get_logger
from .popup import SuggestionPopup
from .session import SessionTracker
from .settings import Settings
from .store import DataManager
from .win32 import get_caret_position, is_console_foreground, update_caret_position

log = get_logger("engine")

WORD_RE = re.compile(r"[a-zA-Z\u0600-\u06ff']+")

try:
    from pynput import keyboard as pynput_keyboard
    HAVE_PYNPUT = True
except Exception:  # pragma: no cover - pynput missing
    pynput_keyboard = None
    HAVE_PYNPUT = False


# =============================================================
# SELECTIVE GLOBAL HOOK
# =============================================================
if HAVE_PYNPUT and sys.platform == "win32":
    from pynput._util.win32 import SystemHook

    class SelectiveListener(pynput_keyboard.Listener):
        """Low level hook that can swallow individual key events."""

        def __init__(self, assistant, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.assistant = assistant
            self.NAV_VKS = {
                config.VK_UP: "up",
                config.VK_DOWN: "down",
                config.VK_RETURN: "return",
                config.VK_TAB: "tab",
                config.VK_ESCAPE: "escape",
            }

        def _handler(self, code, msg, lpdata):
            if code == SystemHook.HC_ACTION:
                data = ctypes.cast(lpdata, self._LPKBDLLHOOKSTRUCT).contents
                vk = data.vkCode
                is_press = msg in self._PRESS_MESSAGES

                # Global hotkeys (Ctrl+Alt+X / Ctrl+Alt+S) are consumed here so
                # that they never reach the focused application.
                if is_press and self.assistant.handle_raw_key(vk):
                    self.suppress_event()

                if self.assistant.popup.active and vk in self.NAV_VKS:
                    key_name = self.NAV_VKS[vk]
                    if self.assistant.should_suppress_nav(key_name):
                        if is_press:
                            self.assistant.dispatcher.post(self.assistant.popup.navigate, key_name)
                        self.suppress_event()
                    elif is_press:
                        # Consoles keep their Enter/Tab, only the popup is closed.
                        self.assistant.dispatcher.post(self.assistant.popup.close)
            super()._handler(code, msg, lpdata)
else:  # pragma: no cover - non Windows
    class SelectiveListener:
        def __init__(self, assistant, *args, **kwargs):
            self.assistant = assistant


class GlobalAssistant:
    """Owns the keyboard hook and coordinates engine, popup and dashboard."""

    def __init__(self, root, dispatcher, dm: DataManager | None = None, settings: Settings | None = None):
        self.root = root
        self.dispatcher = dispatcher
        self.settings = settings or Settings()
        self.dm = dm or DataManager()
        self.lang_detector = self.dm.lang_detector
        self.session = SessionTracker(on_record_callback=self._on_correction_recorded)

        self.keyboard = None
        if HAVE_PYNPUT:
            try:
                self.keyboard = pynput_keyboard.Controller()
            except Exception:
                log.warning("Could not create the keyboard controller")
        self.injector = TextInjector(self.keyboard)

        self.enabled = bool(self.settings.get("enabled", config.ENABLED_DEFAULT))
        self.auto_suggest = bool(self.settings.get("auto_suggest", config.AUTO_SUGGEST_DEFAULT))
        self.next_word_prediction = bool(self.settings.get("next_word_prediction", config.NEXT_WORD_DEFAULT))

        self.listener = None
        self.popup = SuggestionPopup(root, self._on_suggestion_selected)
        self.dashboard_ui = None

        self.current_lang = "english"
        self.last_word_corrected = None

        self._inserting = False
        self._insert_lock = threading.Lock()
        self._buffer_lock = threading.RLock()

        self.typing_buffer: deque = deque(maxlen=60)
        self.last_ctrl_t = 0.0
        self.last_was_ctrl = False
        self.ctrl_down = False
        self.alt_down = False
        self.shift_down = False

        self.running = False
        self._caret_thread = None

    # ------------------------------------------------------------- lifecycle
    def _on_correction_recorded(self, entry):
        """Forward a recorded correction to the dashboard (main thread)."""
        if self.dashboard_ui:
            self.dispatcher.post(self.dashboard_ui.add_log_entry, entry)

    def start(self):
        if self.running:
            return
        self.running = True
        self._caret_thread = threading.Thread(target=self._caret_poll, daemon=True)
        self._caret_thread.start()

        if HAVE_PYNPUT:
            self.listener = SelectiveListener(
                assistant=self,
                on_press=self._on_key_press,
                on_release=self._on_key_release,
            )
            self.listener.start()
        else:
            log.error("pynput is not installed - the global hook is disabled")

        self.root.after(5000, self._periodic)
        log.info("ALPHA engine started (insertion mode: %s)", self.injector.mode)

    def stop(self):
        self.running = False
        if self.listener:
            try:
                self.listener.stop()
            except Exception:
                pass
        self.popup.close()
        self.dm.flush()
        log.info("ALPHA engine stopped")

    def _periodic(self):
        try:
            self.dm.maybe_save_sequences()
            self.dm.reload_if_changed()
        except Exception:
            log.exception("Periodic maintenance failed")
        if self.running:
            self.root.after(5000, self._periodic)

    def _caret_poll(self):
        while self.running:
            update_caret_position()
            time.sleep(0.1)

    # ----------------------------------------------------------- hotkey glue
    def handle_raw_key(self, vk: int) -> bool:
        """Handle global hotkeys.  Returns True when the key was consumed."""
        if not self.ctrl_down or not self.alt_down:
            return False
        if vk == 0x58:  # X
            self.dispatcher.post(self.toggle_assistant)
            return True
        if vk == 0x53:  # S
            self.dispatcher.post(self.show_session_summary)
            return True
        return False

    def should_suppress_nav(self, key_name: str) -> bool:
        """Decide whether a navigation key may be swallowed."""
        if not self.popup.active:
            return False
        if key_name in ("return", "enter", "tab") and is_console_foreground():
            return False
        return True

    # ------------------------------------------------------------ key events
    def _on_key_press(self, key):
        if self._inserting:
            return True
        kb = self.kb

        if key in (kb.Key.ctrl_l, kb.Key.ctrl_r):
            self.ctrl_down = True
            now = time.time()
            if self.last_was_ctrl and (now - self.last_ctrl_t) < 0.45:
                self.last_was_ctrl = False
                self.dispatcher.post(self._trigger_suggestions)
            else:
                self.last_was_ctrl = True
            self.last_ctrl_t = now
            return True
        self.last_was_ctrl = False

        if key in (kb.Key.alt_l, kb.Key.alt_r):
            self.alt_down = True
            return True

        if key == kb.Key.shift_l or key == kb.Key.shift_r:
            self.shift_down = True
            return True

        if key == kb.Key.space:
            if self.ctrl_down:
                self.dispatcher.post(self._trigger_suggestions)
                return True
            with self._buffer_lock:
                self.typing_buffer.append(" ")
                self._handle_space()
            self.dispatcher.post(self.popup.close)
            if self.next_word_prediction and self.enabled:
                self.dispatcher.post_after(
                    "next_word", config.NEXT_WORD_DELAY_MS, self._trigger_next_word_prediction
                )
            return True

        if key == kb.Key.backspace:
            with self._buffer_lock:
                if self.typing_buffer:
                    self.typing_buffer.pop()
            if len(self._get_current_word()) < config.MIN_WORD_LENGTH:
                self.dispatcher.post(self.popup.close)
            return True

        if key in (kb.Key.enter, kb.Key.esc):
            with self._buffer_lock:
                self.typing_buffer.clear()
            self.dispatcher.post(self.popup.close)
            return True

        try:
            char = key.char
        except AttributeError:
            char = None

        if char:
            if self.popup.active and self.popup.is_next_word:
                self.dispatcher.post(self.popup.close)

            if char == "/" and self.alt_down:
                self.dispatcher.post(self._trigger_suggestions)
                return True

            with self._buffer_lock:
                self.typing_buffer.append(char)

            if self.auto_suggest and self.enabled:
                self.dispatcher.post_after(
                    "suggest", config.DEBOUNCE_MS, self._trigger_suggestions
                )
        return True

    def _on_key_release(self, key):
        kb = self.kb
        if key in (kb.Key.ctrl_l, kb.Key.ctrl_r):
            self.ctrl_down = False
        if key in (kb.Key.alt_l, kb.Key.alt_r):
            self.alt_down = False
        if key in (kb.Key.shift_l, kb.Key.shift_r):
            self.shift_down = False
        return True

    @property
    def kb(self):
        return pynput_keyboard

    # ------------------------------------------------------------- buffer ops
    def _buffer_text(self) -> str:
        with self._buffer_lock:
            return "".join(self.typing_buffer)

    def _get_current_word(self) -> str:
        """The word that is currently being typed (empty after a space)."""
        text = self._buffer_text()
        if not text or text[-1].isspace():
            return ""
        words = WORD_RE.findall(text)
        return words[-1] if words else ""

    def _last_word(self) -> str:
        """The most recent word, even when it was already terminated."""
        words = WORD_RE.findall(self._buffer_text())
        return words[-1] if words else ""

    def _current_word_from_buffer(self) -> str:
        return self._last_word()

    def _sync_buffer(self, original: str, replacement: str, append_space: bool) -> None:
        """Keep the mirror buffer in sync with what was written to the app."""
        with self._buffer_lock:
            text = "".join(self.typing_buffer)
            original_l = (original or "").lower()
            if original_l and text.lower().endswith(original_l + " "):
                text = text[: len(text) - len(original_l) - 1] + replacement + " "
            elif original_l and text.lower().endswith(original_l):
                text = text[: len(text) - len(original_l)] + replacement
            else:
                text = text + replacement + (" " if append_space else "")
            self.typing_buffer.clear()
            self.typing_buffer.extend(text)

    # ------------------------------------------------------------ space logic
    def _handle_space(self):
        if self._inserting or not self.enabled:
            return
        word = self._last_word()
        if not word:
            return
        if len(word) < config.MIN_WORD_LENGTH:
            self.dm.commit_word(word)
            return

        text = self._buffer_text()
        lang = self.lang_detector.detect(text)
        self.current_lang = lang

        corrected = self.dm.correct_error(word, lang)
        if corrected != word:
            prev_word = self._previous_word()
            self.dm.commit_word(corrected)
            self._start_insertion(
                corrected, original=word, mode="replace", append_space=True, prev_word=prev_word
            )
        else:
            self.dm.commit_word(word)
            self.dm.learn_word(word, lang)

    def _previous_word(self) -> str:
        words = WORD_RE.findall(self._buffer_text())
        if len(words) >= 2:
            return words[-2]
        return ""

    # ------------------------------------------------------------- insertion
    def _start_insertion(self, text, original="", mode="complete", append_space=False, prev_word=""):
        with self._insert_lock:
            if self._inserting:
                return
            self._inserting = True
        threading.Thread(
            target=self._do_insert,
            args=(text,),
            kwargs={
                "original": original,
                "mode": mode,
                "append_space": append_space,
                "prev_word": prev_word,
            },
            daemon=True,
        ).start()

    def _do_insert(self, suggestion, original="", mode="complete", append_space=False, prev_word=""):
        try:
            time.sleep(0.02)
            current_word = self._current_word_from_buffer()

            if mode == "complete":
                if current_word and suggestion.lower().startswith(current_word.lower()):
                    to_delete = len(current_word)
                else:
                    to_delete = 0
            else:
                to_delete = len(current_word or original)

            if to_delete > 0:
                self.injector.backspace(to_delete)

            payload = suggestion + (" " if append_space else "")
            if not self.injector.type_text(payload):
                log.error("Text injection failed for %r", suggestion)
                return

            self._sync_buffer(current_word or original, suggestion, append_space)
            self.dm.record_usage(suggestion)

            if original and original.lower() != suggestion.lower():
                self.dm.learn_from_selection(original, suggestion, prev_word)
                app = self.session.get_active_app()
                self.session.record_help(app, original, suggestion, self.current_lang)
        except Exception:
            log.exception("Insertion failed")
        finally:
            with self._insert_lock:
                self._inserting = False
            self.last_word_corrected = None

    def _do_insert_next_word(self, word: str):
        with self._insert_lock:
            if self._inserting:
                return
            self._inserting = True
        try:
            time.sleep(0.02)
            if not self.injector.type_text(f"{word} "):
                return
            with self._buffer_lock:
                self.typing_buffer.extend(list(f"{word} "))
            self.dm.record_usage(word)
            self.dm.commit_word(word)
            app = self.session.get_active_app()
            self.session.record_help(app, "[next-word]", word, self.current_lang)
        except Exception:
            log.exception("Next word insertion failed")
        finally:
            with self._insert_lock:
                self._inserting = False

        if self.next_word_prediction and self.enabled:
            self.dispatcher.post_after("next_word", 80, self._trigger_next_word_prediction)

    def _on_suggestion_selected(self, original_word, selected_word, is_next_word=False):
        if is_next_word:
            threading.Thread(
                target=self._do_insert_next_word, args=(selected_word,), daemon=True
            ).start()
        else:
            prev_word = self._previous_word()
            self._start_insertion(
                selected_word,
                original=original_word,
                mode="complete",
                append_space=False,
                prev_word=prev_word,
            )

    # ------------------------------------------------------------ suggestions
    def _trigger_suggestions(self):
        if self._inserting or not self.enabled:
            return
        word = self._get_current_word()
        if not word or len(word) < config.MIN_WORD_LENGTH:
            self.popup.close()
            return

        lang = self.lang_detector.detect(self._buffer_text())
        self.current_lang = lang
        suggestions = self.dm.get_smart_matches_with_prediction(word, lang)
        if not suggestions:
            self.popup.close()
            return

        completions = [item for item in suggestions if item.lower() != word.lower()]
        display = completions or suggestions

        caret_x, caret_y = get_caret_position()
        self.popup.show(display, word, caret_x, caret_y)
        self.dispatcher.post_after("auto_close", config.POPUP_AUTO_CLOSE_MS, self._auto_close_popup)
        if self.dashboard_ui:
            self.dashboard_ui.update_suggestion_chips(display)

    def _auto_close_popup(self):
        self.popup.close()

    def _trigger_next_word_prediction(self):
        if self._inserting or not self.enabled or not self.next_word_prediction:
            return
        text = self._buffer_text()
        words = WORD_RE.findall(text)
        if not words:
            return
        current_word = words[-1]
        prev_word = words[-2] if len(words) >= 2 else None

        lang = self.lang_detector.detect(text)
        self.current_lang = lang
        predictions = self.dm.predict_next_words(current_word, prev_word, lang)
        if not predictions:
            return

        caret_x, caret_y = get_caret_position()
        self.popup.show(predictions, current_word, caret_x, caret_y, is_next_word=True)
        if self.dashboard_ui:
            self.dashboard_ui.update_suggestion_chips(predictions, is_next=True)

    # ------------------------------------------------------------- commands
    def toggle_assistant(self):
        self.enabled = not self.enabled
        self.settings.set("enabled", self.enabled)
        if not self.enabled:
            self.popup.close()
        if self.dashboard_ui:
            self.dashboard_ui.update_status_ui()
        log.info("Assistant %s", "ACTIVE" if self.enabled else "PAUSED")

    def set_auto_suggest(self, value: bool):
        self.auto_suggest = bool(value)
        self.settings.set("auto_suggest", self.auto_suggest)

    def set_next_word_prediction(self, value: bool):
        self.next_word_prediction = bool(value)
        self.settings.set("next_word_prediction", self.next_word_prediction)

    def show_session_summary(self):
        log.info("\n%s\n%s\n%s", "=" * 55, self.session.get_summary(), "=" * 55)
