"""Session statistics kept in RAM only (no keystroke ever reaches the disk)."""
from __future__ import annotations

import ctypes
import os
import platform
from datetime import datetime

from .logging_setup import get_logger
from .win32 import IS_WINDOWS, get_foreground_window_title, user32

log = get_logger("session")

KNOWN_APPS = {
    "chrome.exe": "Google Chrome",
    "msedge.exe": "Microsoft Edge",
    "firefox.exe": "Firefox",
    "brave.exe": "Brave",
    "opera.exe": "Opera",
    "notepad.exe": "Notepad",
    "notepad++.exe": "Notepad++",
    "code.exe": "VS Code",
    "devenv.exe": "Visual Studio",
    "pycharm64.exe": "PyCharm",
    "word.exe": "Microsoft Word",
    "excel.exe": "Microsoft Excel",
    "outlook.exe": "Microsoft Outlook",
    "onenote.exe": "Microsoft OneNote",
    "whatsapp.exe": "WhatsApp",
    "telegram.exe": "Telegram",
    "discord.exe": "Discord",
    "slack.exe": "Slack",
    "cmd.exe": "Command Prompt",
    "powershell.exe": "PowerShell",
    "windowsterminal.exe": "Windows Terminal",
    "explorer.exe": "File Explorer",
    "python.exe": "Python Console",
    "pythonw.exe": "Python Console",
}

if IS_WINDOWS:
    kernel32 = ctypes.windll.kernel32
else:  # pragma: no cover
    kernel32 = None


def get_foreground_process_name() -> str:
    """Executable name of the foreground window (never the document title)."""
    if not user32 or not kernel32:
        return ""
    try:
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return ""
        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if not pid.value:
            return ""
        handle = kernel32.OpenProcess(0x1000, False, pid.value)
        if not handle:
            return ""
        try:
            buffer = ctypes.create_unicode_buffer(1024)
            size = ctypes.c_ulong(1024)
            if kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
                return os.path.basename(buffer.value)
        finally:
            kernel32.CloseHandle(handle)
    except Exception:
        return ""
    return ""


class SessionTracker:
    """Counts corrections per application for the current session."""

    def __init__(self, on_record_callback=None):
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

    def record_help(self, app_name: str, original_word: str, corrected_word: str, language: str) -> None:
        if not app_name:
            app_name = "Unknown"
        self.help_data["apps_helped"][app_name] = self.help_data["apps_helped"].get(app_name, 0) + 1
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
            del self.help_data["words_corrected"][:-50]
        if language not in self.help_data["languages_used"]:
            self.help_data["languages_used"].append(language)
        if self.on_record_callback:
            try:
                self.on_record_callback(entry)
            except Exception:
                log.exception("Session callback failed")

    def get_active_app(self) -> str:
        """Friendly name of the active application without leaking titles."""
        process = get_foreground_process_name().lower()
        if process in KNOWN_APPS:
            return KNOWN_APPS[process]
        if process:
            return process.replace(".exe", "").title()
        title = get_foreground_window_title()
        if "ALPHA Typing Assistant" in title:
            return "ALPHA Sandbox"
        return "Active Application"

    def get_summary(self) -> str:
        data = self.help_data
        lines = [
            f"Start: {data['session_start'][:19]} | PC: {data['computer_name']} | OS: {data['os']}",
            f"Corrections: {data['total_corrections']} | Languages: "
            f"{', '.join(data['languages_used']) or 'none'}",
        ]
        if data["apps_helped"]:
            lines.append("Applications helped:")
            for app, count in sorted(data["apps_helped"].items(), key=lambda kv: -kv[1]):
                lines.append(f"  - {app}: {count}x")
        else:
            lines.append("No corrections recorded yet.")
        return "\n".join(lines)
