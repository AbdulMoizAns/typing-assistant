"""Shared pytest fixtures for the ALPHA test suite."""
from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alpha.settings import Settings  # noqa: E402
from alpha.store import DataManager  # noqa: E402

FREQUENCY_SAMPLE = {
    "version": "test",
    "total_english": 8,
    "total_roman_urdu": 3,
    "english": ["the", "be", "to", "of", "and", "that", "this", "there"],
    "roman_urdu": ["kaise", "nahi", "shukriya"],
}

DICTIONARY_SAMPLE = [
    "the", "then", "theory", "therapy", "there", "thermal", "thing",
    "quantum", "quarantine", "quick", "quiet",
    "kaise", "kailash", "nahi",
]


@pytest.fixture()
def data_dir(tmp_path):
    """A miniature data directory that mirrors the real layout."""
    (tmp_path / "frequency_words.json").write_text(
        json.dumps(FREQUENCY_SAMPLE), encoding="utf-8"
    )
    (tmp_path / "dictionary.json").write_text(
        json.dumps(DICTIONARY_SAMPLE), encoding="utf-8"
    )
    (tmp_path / "errors.json").write_text(
        json.dumps({"teh": "the", "recieve": "receive"}), encoding="utf-8"
    )
    (tmp_path / "suggestions.json").write_text(
        json.dumps({
            "snippets": {"sig1": "Best regards,\nAbdul Moiz"},
            "templates": ["Hello, {name}.", "Thank you for your {noun}."],
            "variables": {"name": "Moiz"},
        }),
        encoding="utf-8",
    )
    (tmp_path / "sequences.json").write_text(
        json.dumps({"pairs": {}, "trigrams": {}}), encoding="utf-8"
    )
    return tmp_path


@pytest.fixture()
def writer():
    """A background writer that is shut down at the end of the test."""
    from alpha.store import BackgroundWriter

    instance = BackgroundWriter()
    yield instance
    instance.shutdown()


@pytest.fixture()
def dm(data_dir, writer):
    """A DataManager bound to the miniature data directory."""
    manager = DataManager(bg=writer, base_dir=str(data_dir))
    yield manager
    manager.flush()


@pytest.fixture()
def settings(data_dir):
    return Settings(path=str(data_dir / "settings.json"))


class DispatcherStub:
    """Records everything that would be posted to the Tk main thread."""

    def __init__(self):
        self.posted = []
        self.timers = []
        self.cancelled = []

    def post(self, fn, *args, **kwargs):
        self.posted.append((fn, args, kwargs))

    def post_after(self, name, delay_ms, fn, *args, **kwargs):
        self.timers.append((name, delay_ms, fn, args, kwargs))

    def cancel(self, name):
        self.cancelled.append(name)


@pytest.fixture()
def assistant(dm, settings, dispatcher):
    """An engine instance with the text injection stubbed out."""
    from alpha.engine import GlobalAssistant

    engine = GlobalAssistant(root=None, dispatcher=dispatcher, dm=dm, settings=settings)
    engine.insertions = []
    engine._start_insertion = lambda *args, **kwargs: engine.insertions.append((args, kwargs))
    return engine


@pytest.fixture()
def dispatcher():
    return DispatcherStub()
