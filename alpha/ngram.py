"""N-gram model backing next-word prediction.

The model keeps a bigram table (``word -> {next: count}``) and a trigram table
(``word_word -> {next: count}``).  Learning is incremental: committing a word
only touches the pair that was just completed, which keeps counters honest and
avoids rewriting the whole dataset on every keystroke.
"""
from __future__ import annotations

from . import config

TRIGRAM_WEIGHT = 3.0
BIGRAM_WEIGHT = 1.0


class SequenceLearner:
    """Bigram + trigram sequence model."""

    __slots__ = ("sequences", "trigrams", "dirty")

    def __init__(self):
        self.sequences: dict[str, dict[str, int]] = {}
        self.trigrams: dict[str, dict[str, int]] = {}
        self.dirty = False

    # ----------------------------------------------------------------- learn
    def learn_pair(self, previous: str, current: str) -> None:
        if not previous or not current:
            return
        prev_l, cur_l = previous.lower(), current.lower()
        bucket = self.sequences.setdefault(prev_l, {})
        bucket[cur_l] = bucket.get(cur_l, 0) + 1
        self.dirty = True

    def learn_triple(self, first: str, second: str, third: str) -> None:
        if not first or not second or not third:
            return
        key = f"{first.lower()}_{second.lower()}"
        bucket = self.trigrams.setdefault(key, {})
        third_l = third.lower()
        bucket[third_l] = bucket.get(third_l, 0) + 1
        self.dirty = True

    def learn(self, word_list) -> None:
        """Learn every adjacent pair in *word_list* (bulk import helper)."""
        if len(word_list) < 2:
            return
        for i in range(len(word_list) - 1):
            self.learn_pair(word_list[i], word_list[i + 1])
        for i in range(len(word_list) - 2):
            self.learn_triple(word_list[i], word_list[i + 1], word_list[i + 2])

    # --------------------------------------------------------------- predict
    def predict_next(self, current_word: str, prev_word: str | None = None, limit: int = 5) -> list[str]:
        """Return the most likely continuations for *current_word*."""
        if not current_word:
            return []
        cur = current_word.lower()
        scores: dict[str, float] = {}

        if prev_word:
            tkey = f"{prev_word.lower()}_{cur}"
            for word, count in self.trigrams.get(tkey, {}).items():
                scores[word] = scores.get(word, 0.0) + count * TRIGRAM_WEIGHT
        for word, count in self.sequences.get(cur, {}).items():
            scores[word] = scores.get(word, 0.0) + count * BIGRAM_WEIGHT

        ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
        return [word for word, _ in ranked[:limit]]

    # ----------------------------------------------------------- maintenance
    def prune(self) -> None:
        """Drop the weakest entries so the on-disk dataset stays bounded."""
        if len(self.sequences) > config.MAX_SEQUENCE_PAIRS:
            ordered = sorted(self.sequences.items(), key=lambda kv: -max(kv[1].values()))
            self.sequences = dict(ordered[: config.MAX_SEQUENCE_PAIRS])
        if len(self.trigrams) > config.MAX_SEQUENCE_PAIRS:
            ordered = sorted(self.trigrams.items(), key=lambda kv: -max(kv[1].values()))
            self.trigrams = dict(ordered[: config.MAX_SEQUENCE_PAIRS])

    def to_dict(self) -> dict:
        return {"pairs": self.sequences, "trigrams": self.trigrams}

    def load_dict(self, data: dict) -> None:
        pairs = data.get("pairs") or {}
        trigrams = data.get("trigrams") or {}
        if isinstance(pairs, dict):
            self.sequences = {k: dict(v) for k, v in pairs.items() if isinstance(v, dict)}
        if isinstance(trigrams, dict):
            self.trigrams = {k: dict(v) for k, v in trigrams.items() if isinstance(v, dict)}
        self.dirty = False
