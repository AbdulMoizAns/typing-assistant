"""Settings persistence."""
from __future__ import annotations

import json

from alpha.settings import Settings


def test_defaults_are_used_when_no_file_exists(data_dir):
    settings = Settings(path=str(data_dir / "missing.json"))
    assert settings.get("auto_suggest") is True
    assert settings.get("next_word_prediction") is True
    assert settings.get("enabled") is True


def test_values_persist_to_disk(data_dir):
    path = str(data_dir / "settings.json")
    settings = Settings(path=path)
    settings.set("auto_suggest", False)
    assert settings.get("auto_suggest") is False

    reloaded = Settings(path=path)
    assert reloaded.get("auto_suggest") is False


def test_unknown_keys_are_ignored(data_dir):
    path = data_dir / "settings.json"
    path.write_text(json.dumps({"auto_suggest": False, "bogus": 1}), encoding="utf-8")
    settings = Settings(path=str(path))
    assert settings.get("auto_suggest") is False
    assert "bogus" not in settings.as_dict()
