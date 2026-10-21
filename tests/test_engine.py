"""Engine behaviour: buffer bookkeeping, space handling and key routing."""
from __future__ import annotations

def _set_buffer(assistant, text):
    with assistant._buffer_lock:
        assistant.typing_buffer.clear()
        assistant.typing_buffer.extend(text)


def test_space_corrects_a_typo(assistant):
    _set_buffer(assistant, "teh ")
    assistant._handle_space()
    assert assistant.insertions
    args, kwargs = assistant.insertions[0]
    assert args[0] == "the"
    assert kwargs["original"] == "teh"
    assert kwargs["mode"] == "replace"
    assert kwargs["append_space"] is True


def test_space_without_typo_commits_the_word(assistant):
    _set_buffer(assistant, "hello ")
    assistant._handle_space()
    assert not assistant.insertions
    assert assistant.dm.word_history[-1] == "hello"


def test_english_words_are_not_rewritten(assistant):
    _set_buffer(assistant, "men ")
    assistant._handle_space()
    assert not assistant.insertions


def test_sync_buffer_keeps_the_surrounding_context(assistant):
    """The sentence context must survive a correction."""
    _set_buffer(assistant, "thank you teh ")
    assistant._sync_buffer("teh", "the", True)
    assert "".join(assistant.typing_buffer) == "thank you the "


def test_sync_buffer_replaces_a_single_word(assistant):
    _set_buffer(assistant, "thank you teh")
    assistant._sync_buffer("teh", "the", False)
    assert "".join(assistant.typing_buffer) == "thank you the"


def test_sync_buffer_appends_when_nothing_matches(assistant):
    _set_buffer(assistant, "hello ")
    assistant._sync_buffer("xyz", "world", False)
    assert "".join(assistant.typing_buffer) == "hello world"


def test_current_word_is_empty_after_a_space(assistant):
    _set_buffer(assistant, "the quick brown ")
    assert assistant._get_current_word() == ""
    assert assistant._last_word() == "brown"


def test_current_word_ignores_trailing_space(assistant):
    _set_buffer(assistant, "hello wor")
    assert assistant._get_current_word() == "wor"


def test_previous_word_is_reported(assistant):
    _set_buffer(assistant, "thank you teh")
    assert assistant._previous_word() == "you"


def test_console_keeps_its_enter_key(assistant, monkeypatch):
    monkeypatch.setattr("alpha.engine.is_console_foreground", lambda: True)
    assistant.popup.active = True
    assert assistant.should_suppress_nav("return") is False
    assert assistant.should_suppress_nav("up") is True


def test_normal_apps_allow_enter_to_be_swallowed(assistant, monkeypatch):
    monkeypatch.setattr("alpha.engine.is_console_foreground", lambda: False)
    assistant.popup.active = True
    assert assistant.should_suppress_nav("return") is True


def test_popup_closed_keys_are_never_swallowed(assistant, monkeypatch):
    monkeypatch.setattr("alpha.engine.is_console_foreground", lambda: False)
    assistant.popup.active = False
    assert assistant.should_suppress_nav("return") is False


def test_global_hotkey_requires_ctrl_and_alt(assistant):
    assert assistant.handle_raw_key(0x58) is False


def test_toggle_persists_the_state(assistant):
    previous = assistant.enabled
    assistant.toggle_assistant()
    assert assistant.enabled is not previous
    assert assistant.settings.get("enabled") is assistant.enabled
    assistant.toggle_assistant()


def test_suggestion_trigger_requires_a_minimum_word_length(assistant):
    _set_buffer(assistant, "a")
    assistant._trigger_suggestions()
    assert not assistant.popup.active


def test_next_word_prediction_uses_the_learned_model(assistant, monkeypatch):
    shown = []
    monkeypatch.setattr(assistant.popup, "show", lambda *a, **k: shown.append(a))
    assistant.dm.sequence_learner.learn_pair("hello", "world")
    _set_buffer(assistant, "hello ")
    assistant._trigger_next_word_prediction()
    assert shown
    assert "world" in shown[0][0]
