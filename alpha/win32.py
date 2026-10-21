"""Thin Win32 helpers: caret tracking, foreground window info, console detection."""
from __future__ import annotations

import ctypes
import sys
import threading

IS_WINDOWS = sys.platform == "win32"

if IS_WINDOWS:
    user32 = ctypes.windll.user32
else:  # pragma: no cover - non Windows fallback
    user32 = None


class _RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


class _GUITHREADINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_uint32), ("flags", ctypes.c_uint32),
        ("hwndActive", ctypes.c_size_t), ("hwndFocus", ctypes.c_size_t),
        ("hwndCapture", ctypes.c_size_t), ("hwndMenuOwner", ctypes.c_size_t),
        ("hwndMoveOwner", ctypes.c_size_t), ("hwndCaret", ctypes.c_size_t),
        ("rcCaret", _RECT),
    ]


class _POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


CONSOLE_WINDOW_CLASSES = {
    "ConsoleWindowClass",
    "CASCADIA_HOSTING_WINDOW_CLASS",
    "WindowsTerminal",
    "PseudoConsoleWindow",
}

CONSOLE_TITLE_HINTS = ("cmd.exe", "powershell", "windows terminal", "command prompt")

_last_caret = (400, 350)
_caret_lock = threading.Lock()


def get_caret_position() -> tuple[int, int]:
    """Best effort caret position in screen coordinates."""
    with _caret_lock:
        return _last_caret


def update_caret_position() -> bool:
    """Poll the caret position with mouse and window fallbacks."""
    global _last_caret
    if not user32:
        return False

    try:
        info = _GUITHREADINFO()
        info.cbSize = ctypes.sizeof(_GUITHREADINFO)
        if user32.GetGUIThreadInfo(0, ctypes.byref(info)) and info.hwndCaret:
            point = _POINT(info.rcCaret.left, info.rcCaret.bottom)
            user32.ClientToScreen(info.hwndCaret, ctypes.byref(point))
            if point.x > 0 and point.y > 0:
                with _caret_lock:
                    _last_caret = (point.x + 10, point.y + 25)
                return True
    except Exception:
        pass

    try:
        point = _POINT()
        if user32.GetCursorPos(ctypes.byref(point)):
            if point.x > 0 and point.y > 0:
                with _caret_lock:
                    _last_caret = (point.x + 15, point.y + 20)
                return True
    except Exception:
        pass

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


def get_foreground_window_title() -> str:
    """Title of the foreground window (empty string when unavailable)."""
    if not user32:
        return ""
    try:
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return ""
        length = user32.GetWindowTextLengthW(hwnd)
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        return buffer.value or ""
    except Exception:
        return ""


def get_foreground_window_class() -> str:
    """Class name of the foreground window."""
    if not user32:
        return ""
    try:
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return ""
        buffer = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, buffer, 256)
        return buffer.value or ""
    except Exception:
        return ""


def is_console_foreground() -> bool:
    """True when a terminal / console currently has the focus.

    Consoles must keep their Enter and Tab keys, otherwise pressing Enter in
    a terminal would insert a suggestion instead of a new line.
    """
    if not user32:
        return False
    if get_foreground_window_class() in CONSOLE_WINDOW_CLASSES:
        return True
    title = get_foreground_window_title().strip().lower()
    return any(hint in title for hint in CONSOLE_TITLE_HINTS)


def is_self_foreground() -> bool:
    """True when the ALPHA dashboard itself is focused."""
    title = get_foreground_window_title()
    return "ALPHA Typing Assistant" in title
