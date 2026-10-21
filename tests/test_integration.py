"""End to end flow: key events -> buffer -> correction -> injected text."""
from __future__ import annotations

import time

import pytest

pynput_keyboard = pytest.importorskip("pynput.keyboard")


class FakeInjector:
    """Records what would have been typed into the foreground app."""

    def __init__(self):
        self.typed: list[str] = []
        self.deleted = 0
        self.mode = "unicode"

    def backspace(self, count=1):
        self.deleted += count

    def type_text(self, text):
        self.typed.append(text)
        return True


def _char(letter):
    return pynput_keyboard.KeyCode(char=letter)


def _wait_for_insertion(assistant, timeout=2.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not assistant._inserting:
            return True
        time.sleep(0.01)
    return False


@pytest.fixture()
def live(assistant):
    """An assistant whose text injection is captured instead of performed."""
    from alpha.engine import GlobalAssistant

    injector = FakeInjector()
    assistant.injector = injector
    # restore the real insertion path (the shared fixture stubs it out)
    assistant._start_insertion = GlobalAssistant._start_insertion.__get__(assistant)
    return assistant, injector


def test_typing_a_typo_replaces_it_in_place(live):
    assistant, injector = live
    for letter in "teh":
        assistant._on_key_press(_char(letter))
    assistant._on_key_press(pynput_keyboard.Key.space)

    assert _wait_for_insertion(assistant)
    assert injector.typed == ["the "]
    assert injector.deleted == 3
    assert "".join(assistant.typing_buffer) == "the "


def test_context_is_preserved_around_a_correction(live):
    assistant, injector = live
    for letter in "thank you teh":
        assistant._on_key_press(_char(letter))
    assistant._on_key_press(pynput_keyboard.Key.space)

    assert _wait_for_insertion(assistant)
    assert injector.typed == ["the "]
    assert "".join(assistant.typing_buffer) == "thank you the "


def test_plain_english_word_is_not_rewritten(live):
    assistant, injector = live
    for letter in "men":
        assistant._on_key_press(_char(letter))
    assistant._on_key_press(pynput_keyboard.Key.space)

    assert _wait_for_insertion(assistant)
    assert injector.typed == []
    assert "".join(assistant.typing_buffer) == "men "


def test_roman_urdu_typo_is_corrected(live):
    assistant, injector = live
    for letter in "shukria":
        assistant._on_key_press(_char(letter))
    assistant._on_key_press(pynput_keyboard.Key.space)

    assert _wait_for_insertion(assistant)
    assert injector.typed == ["Shukriya "]


def test_backspace_updates_the_buffer(live):
    assistant, _ = live
    for letter in "helx":
        assistant._on_key_press(_char(letter))
    assistant._on_key_press(pynput_keyboard.Key.backspace)
    assert assistant._get_current_word() == "hel"


def test_enter_clears_the_buffer(live):
    assistant, _ = live
    for letter in "hello":
        assistant._on_key_press(_char(letter))
    assistant._on_key_press(pynput_keyboard.Key.enter)
    assert "".join(assistant.typing_buffer) == ""


def test_words_are_committed_to_the_ngram_model(live):
    assistant, _ = live
    for letter in "thank":
        assistant._on_key_press(_char(letter))
    assistant._on_key_press(pynput_keyboard.Key.space)
    for letter in "you":
        assistant._on_key_press(_char(letter))
    assistant._on_key_press(pynput_keyboard.Key.space)

    assert "thank" in assistant.dm.word_history
    assert "you" in assistant.dm.word_history
    assert "you" in assistant.dm.predict_next_words("thank", None)
