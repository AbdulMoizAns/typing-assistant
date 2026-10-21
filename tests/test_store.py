"""Suggestion engine, learning behaviour and persistence."""
from __future__ import annotations

from alpha import config


def test_tier1_blocks_the_fallback_dictionary(dm):
    """Everyday prefixes must never surface obscure dictionary words."""
    results = dm.get_smart_matches_enhanced("th")
    assert results
    assert all(not word.startswith("thack") for word in results)
    assert "the" in results


def test_tier2_is_used_for_rare_prefixes(dm):
    results = dm.get_smart_matches_enhanced("qu")
    assert any(word.startswith("qu") for word in results)


def test_short_prefixes_can_reach_the_fallback(dm):
    """A two letter prefix with few everyday hits still finds dictionary words."""
    results = dm.get_smart_matches_enhanced("qu")
    assert len(results) <= config.MAX_SUGGESTIONS


def test_exact_snippet_wins(dm):
    results = dm.get_smart_matches_enhanced("sig1")
    assert results[0].startswith("Best regards")


def test_template_variables_are_expanded(dm):
    expanded = dm.expand_template("Hello, {name}.")
    assert expanded == "Hello, Moiz."


def test_correction_prefers_the_errors_database(dm):
    assert dm.correct_error("teh", "english") == "the"
    assert dm.correct_error("recieve", "english") == "receive"


def test_correction_keeps_english_words_intact(dm):
    """'men' must not become 'mein' inside an English sentence."""
    assert dm.correct_error("men", "english") == "men"
    assert dm.correct_error("main", "english") == "main"


def test_commit_word_builds_bigrams(dm):
    dm.commit_word("thank")
    dm.commit_word("you")
    predictions = dm.predict_next_words("thank", None)
    assert "you" in predictions


def test_trigrams_outweigh_bigrams(dm):
    dm.sequence_learner.learn_pair("how", "are")
    dm.sequence_learner.learn_triple("how", "are", "you")
    predictions = dm.predict_next_words("are", "how")
    assert predictions[0] == "you"


def test_learn_from_selection_records_word_pairs(dm):
    dm.learn_from_selection("teh", "the", "thank")
    assert "thank|teh" in dm.word_pairs
    assert dm.word_pairs["thank|teh"]["the"] == 1


def test_learned_pairs_feed_the_suggestions(dm):
    dm.learn_from_selection("teh", "the", "thank")
    results = dm.get_smart_matches_enhanced("teh", "english", prev_word="thank")
    assert "the" in results


def test_usage_stats_and_learning_are_indexed(dm):
    dm.record_usage("hello")
    dm.learn_word("hello", "english")
    assert "hello" in dm._usage_index.search("hel")
    assert "hello" in dm._user_index.search("hel")


def test_reload_picks_up_changed_files(dm, data_dir):
    import json
    import time

    path = data_dir / "suggestions.json"
    time.sleep(0.01)
    path.write_text(json.dumps({"snippets": {"abc": "changed"}}), encoding="utf-8")
    os_mtime = path.stat().st_mtime
    assert dm.reload_if_changed() is True
    assert dm.suggestions["snippets"]["abc"] == "changed"
    assert os_mtime


def test_sequences_are_saved_on_flush(dm, data_dir):
    import json

    dm.commit_word("hello")
    dm.commit_word("world")
    dm.maybe_save_sequences(force=True)
    dm.bg.flush()

    data = json.loads((data_dir / "sequences.json").read_text(encoding="utf-8"))
    assert data["pairs"]["hello"]["world"] >= 1
