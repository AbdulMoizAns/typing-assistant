"""Dictionary index and n-gram model."""
from __future__ import annotations

from alpha.dictionary import DictIndex
from alpha.ngram import SequenceLearner


def test_prefix_search_is_case_insensitive():
    index = DictIndex(["Apple", "apply", "banana"])
    assert index.prefix_search("ap") == ["Apple", "apply"]
    assert index.prefix_search("AP") == ["Apple", "apply"]


def test_prefix_search_respects_the_limit():
    index = DictIndex([f"word{i}" for i in range(50)])
    assert len(index.prefix_search("word", limit=5)) == 5


def test_prefix_search_returns_empty_for_unknown_prefix():
    index = DictIndex(["alpha", "beta"])
    assert index.prefix_search("zz") == []


def test_contains():
    index = DictIndex(["alpha", "beta"])
    assert index.contains("Alpha")
    assert not index.contains("gamma")


def test_bigram_learning_increments_counts():
    learner = SequenceLearner()
    learner.learn_pair("hello", "world")
    learner.learn_pair("hello", "world")
    assert learner.sequences["hello"]["world"] == 2


def test_prediction_uses_the_learned_bigram():
    learner = SequenceLearner()
    learner.learn_pair("hello", "world")
    assert learner.predict_next("hello")[0] == "world"


def test_trigram_has_higher_weight():
    learner = SequenceLearner()
    learner.learn_pair("how", "are")
    learner.learn_pair("are", "you")
    learner.learn_triple("how", "are", "you")
    predictions = learner.predict_next("are", "how")
    assert predictions[0] == "you"


def test_prediction_limit_is_respected():
    learner = SequenceLearner()
    for index in range(20):
        learner.learn_pair("a", f"w{index}")
    assert len(learner.predict_next("a", limit=5)) == 5


def test_to_dict_round_trip():
    learner = SequenceLearner()
    learner.learn_pair("a", "b")
    data = learner.to_dict()
    restored = SequenceLearner()
    restored.load_dict(data)
    assert restored.sequences["a"]["b"] == 1
