"""Text injection into the foreground application.

Two strategies are supported:

``unicode``
    ``SendInput`` with ``KEYEVENTF_UNICODE``.  The text is delivered as raw
    characters, so the clipboard is never touched, nothing can be lost and
    private content is not exposed to other applications.

``clipboard``
    Legacy fallback that copies to the clipboard and pastes with Ctrl+V.  It is
    only used when the unicode path is unavailable (for example when the
    target application runs with a higher integrity level).
"""
from __future__ import annotations

import ctypes
import time
from ctypes import wintypes

from .logging_setup import get_logger

log = get_logger("insertion")

IS_WINDOWS = hasattr(ctypes, "windll")

ULONG_PTR = ctypes.POINTER(ctypes.c_ulong)

INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_EXTENDEDKEY = 0x0001

VK_BACK = 0x08
VK_TAB = 0x09
VK_RETURN = 0x0D
VK_SHIFT = 0x10


class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class _MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class _HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("mi", _MOUSEINPUT), ("ki", _KEYBDINPUT), ("hi", _HARDWAREINPUT)]


class _INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [("type", wintypes.DWORD), ("u", _INPUTUNION)]


def _send_inputs(inputs: list) -> int:
    """Send a batch of prepared INPUT structures."""
    if not IS_WINDOWS or not inputs:
        return 0
    array_type = _INPUT * len(inputs)
    array = array_type(*inputs)
    sent = ctypes.windll.user32.SendInput(len(inputs), array, ctypes.sizeof(_INPUT))
    return int(sent)


def _unicode_input(code_unit: int, key_up: bool) -> "_INPUT":
    flags = KEYEVENTF_UNICODE
    if key_up:
        flags |= KEYEVENTF_KEYUP
    item = _INPUT()
    item.type = INPUT_KEYBOARD
    item.ki = _KEYBDINPUT(0, code_unit, flags, 0, None)
    return item


def _vk_input(vk: int, key_up: bool) -> "_INPUT":
    flags = KEYEVENTF_EXTENDEDKEY if vk in (VK_BACK,) else 0
    if key_up:
        flags |= KEYEVENTF_KEYUP
    item = _INPUT()
    item.type = INPUT_KEYBOARD
    item.ki = _KEYBDINPUT(vk, 0, flags, 0, None)
    return item


def _utf16_units(text: str) -> list[int]:
    raw = text.encode("utf-16-le")
    return [raw[i] | (raw[i + 1] << 8) for i in range(0, len(raw), 2)]


def type_text_unicode(text: str) -> bool:
    """Type *text* directly as unicode characters (no clipboard involved)."""
    if not text:
        return True
    inputs: list = []
    for chunk in text:
        if chunk == "\n":
            inputs.append(_vk_input(VK_RETURN, False))
            inputs.append(_vk_input(VK_RETURN, True))
            continue
        if chunk == "\t":
            inputs.append(_vk_input(VK_TAB, False))
            inputs.append(_vk_input(VK_TAB, True))
            continue
        for unit in _utf16_units(chunk):
            inputs.append(_unicode_input(unit, False))
            inputs.append(_unicode_input(unit, True))
    sent = _send_inputs(inputs)
    if sent == 0:
        log.warning("SendInput returned 0 - unicode typing unavailable")
        return False
    return True


def press_backspace(count: int = 1) -> None:
    """Press backspace *count* times using the raw input API."""
    if count <= 0:
        return
    inputs: list = []
    for _ in range(count):
        inputs.append(_vk_input(VK_BACK, False))
        inputs.append(_vk_input(VK_BACK, True))
    _send_inputs(inputs)


class TextInjector:
    """Chooses the best available injection strategy and exposes a stable API."""

    def __init__(self, keyboard=None):
        self.keyboard = keyboard
        self._clipboard_ok = False
        try:
            import pyperclip  # noqa: F401

            self._clipboard_ok = True
        except Exception:
            self._clipboard_ok = False

        if not IS_WINDOWS:
            self.mode = "keyboard" if keyboard is not None else "none"
        else:
            # The unicode path works without any clipboard access at all.
            self.mode = "unicode"

    # ------------------------------------------------------------- properties
    @property
    def available(self) -> bool:
        return self.mode in ("unicode", "clipboard", "keyboard")

    @property
    def uses_clipboard(self) -> bool:
        return self.mode == "clipboard"

    # ------------------------------------------------------------------ api
    def type_text(self, text: str) -> bool:
        """Insert *text* at the caret of the focused application."""
        if not text:
            return True
        if self.mode == "unicode":
            if type_text_unicode(text):
                return True
            log.warning("Falling back to clipboard based insertion")
            self.mode = "clipboard"
        if self.mode == "clipboard" and self._clipboard_ok:
            return self._type_via_clipboard(text)
        if self.mode == "keyboard" and self.keyboard is not None:
            return self._type_via_keyboard(text)
        return False

    def backspace(self, count: int = 1) -> None:
        if count <= 0:
            return
        if IS_WINDOWS:
            press_backspace(count)
            return
        if self.keyboard is not None:
            for _ in range(count):
                self.keyboard.press("backspace")
                self.keyboard.release("backspace")

    # -------------------------------------------------------------- internals
    def _type_via_clipboard(self, text: str) -> bool:
        try:
            import pyperclip
        except Exception:
            return False
        saved = ""
        try:
            saved = pyperclip.paste()
        except Exception:
            saved = ""
        try:
            pyperclip.copy(text)
            time.sleep(0.02)
            if self.keyboard is None:
                return False
            self.keyboard.press("ctrl")
            self.keyboard.press("v")
            self.keyboard.release("v")
            self.keyboard.release("ctrl")
            time.sleep(0.02)
            return True
        except Exception:
            log.exception("Clipboard insertion failed")
            return False
        finally:
            try:
                pyperclip.copy(saved)
            except Exception:
                pass

    def _type_via_keyboard(self, text: str) -> bool:
        if self.keyboard is None:
            return False
        try:
            self.keyboard.type(text)
            return True
        except Exception:
            log.exception("Keyboard typing failed")
            return False
