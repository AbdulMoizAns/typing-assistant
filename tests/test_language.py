"""Language detection and correction behaviour."""
from __future__ import annotations

from alpha.language import (
    LanguageDetector,
    apply_case_pattern,
    roman_urdu_correction,
)


def test_detects_plain_english():
    detector = LanguageDetector()
    assert detector.detect("this is a simple english sentence") == "english"


def test_detects_roman_urdu():
    detector = LanguageDetector()
    assert detector.detect("aap kaise ho") == "roman_urdu"
    assert detector.detect("mera naam moiz hai") == "roman_urdu"


def test_detects_urdu_script():
    detector = LanguageDetector()
    assert detector.detect("میرا نام") == "urdu_script"


def test_empty_text_is_english():
    detector = LanguageDetector()
    assert detector.detect("") == "english"
    assert detector.detect("   ") == "english"


def test_roman_urdu_typos_are_corrected_in_english_mode():
    """Typos that are not English words must always be fixed."""
    assert roman_urdu_correction("nhe", "english") == "nahi"
    assert roman_urdu_correction("mei", "english") == "mein"
    assert roman_urdu_correction("shukria", "english") == "Shukriya"
    assert roman_urdu_correction("thik", "english") == "Theek"
    assert roman_urdu_correction("krna", "english") == "karna"


def test_english_words_are_never_roman_urdu_rewritten():
    """``men``, ``main``, ``ap`` and ``ye`` are real English words."""
    def known_english(word):
        return word in {"men", "main", "ap", "ye", "mai", "wo"}

    for word in ("men", "main", "ap", "ye", "mai", "wo"):
        assert roman_urdu_correction(word, "english", known_english) == word


def test_roman_only_corrections_apply_in_roman_urdu_mode():
    def known_english(word):
        return word in {"men", "main", "ap", "ye", "mai", "wo"}

    assert roman_urdu_correction("men", "roman_urdu", known_english) == "mein"
    assert roman_urdu_correction("ye", "roman_urdu", known_english) == "yeh"


def test_case_pattern_is_preserved():
    assert apply_case_pattern("TEH", "the") == "THE"
    assert apply_case_pattern("Teh", "the") == "The"
    assert apply_case_pattern("teh", "the") == "the"


def test_ends_with_h_is_not_a_language_signal():
    """The old heuristic classified words such as 'high' as Roman Urdu."""
    detector = LanguageDetector()
    assert detector.detect("the graph is high") == "english"
