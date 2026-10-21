"""Persisted user settings."""
from __future__ import annotations

import json
import os
import threading

from . import config
from .logging_setup import get_logger

log = get_logger("settings")


class Settings:
    """Small JSON backed settings store."""

    DEFAULTS = {
        "auto_suggest": config.AUTO_SUGGEST_DEFAULT,
        "next_word_prediction": config.NEXT_WORD_DEFAULT,
        "enabled": config.ENABLED_DEFAULT,
        "show_activity_feed": True,
    }

    def __init__(self, path: str | None = None):
        self.path = path or config.SETTINGS_FILE
        self._lock = threading.Lock()
        self._values = dict(self.DEFAULTS)
        self.load()

    def load(self) -> None:
        try:
            if os.path.exists(self.path):
                with open(self.path, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
                if isinstance(data, dict):
                    with self._lock:
                        self._values.update({k: v for k, v in data.items() if k in self.DEFAULTS})
        except Exception:
            log.warning("Could not read settings from %s", self.path)

    def save(self) -> None:
        with self._lock:
            snapshot = dict(self._values)
        try:
            tmp = f"{self.path}.tmp"
            with open(tmp, "w", encoding="utf-8") as handle:
                json.dump(snapshot, handle, indent=2, ensure_ascii=False)
            os.replace(tmp, self.path)
        except Exception:
            log.exception("Could not persist settings")

    def get(self, key: str, default=None):
        with self._lock:
            return self._values.get(key, self.DEFAULTS.get(key, default))

    def set(self, key: str, value) -> None:
        with self._lock:
            self._values[key] = value
        self.save()

    def as_dict(self) -> dict:
        with self._lock:
            return dict(self._values)
