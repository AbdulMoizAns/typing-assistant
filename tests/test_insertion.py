"""Text injection helpers."""
from __future__ import annotations

from alpha.insertion import TextInjector, _utf16_units


def test_utf16_units_handle_astral_characters():
    units = _utf16_units("a\U0001F600")
    assert len(units) == 3  # 'a' plus a surrogate pair


def test_injector_reports_its_mode():
    injector = TextInjector()
    assert injector.mode in ("unicode", "clipboard", "keyboard", "none")
    assert injector.available is True


def test_empty_text_is_a_no_op():
    injector = TextInjector()
    assert injector.type_text("") is True


def test_backspace_with_zero_count_is_a_no_op():
    injector = TextInjector()
    injector.backspace(0)
