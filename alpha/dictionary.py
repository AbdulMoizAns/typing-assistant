"""Prefix searchable word index used for the tier-2 fallback dictionary.

Building the index for the 370k word fallback dictionary is the slowest part of
the start up, therefore the sorted word list is cached next to the source file
and re-used whenever it is still up to date.
"""
from __future__ import annotations

import bisect
import os

CACHE_MAGIC = b"ALPHADICT1"
CACHE_SEPARATOR = b"\n\x00\n"


class DictIndex:
    """Sorted, case-insensitive prefix index over a large word list."""

    __slots__ = ("_words", "_keys")

    def __init__(self, words):
        self._words = tuple(self._clean(words))
        self._keys = tuple(word.lower() for word in self._words)

    # ------------------------------------------------------------- building
    @staticmethod
    def _clean(words) -> list[str]:
        seen: set[str] = set()
        for word in words:
            if not isinstance(word, str):
                continue
            word = word.strip()
            if len(word) < 2:
                continue
            seen.add(word)

        items = list(seen)
        if len(items) > 1:
            keys = [word.lower() for word in items]
            if any(keys[index] > keys[index + 1] for index in range(len(keys) - 1)):
                items.sort(key=str.lower)
        return items

    # --------------------------------------------------------------- cache
    def save_cache(self, path: str) -> bool:
        """Persist the sorted index so the next start up is instant."""
        try:
            with open(path, "wb") as handle:
                handle.write(CACHE_MAGIC)
                handle.write("\n".join(self._words).encode("utf-8"))
                handle.write(CACHE_SEPARATOR)
                handle.write("\n".join(self._keys).encode("utf-8"))
            return True
        except Exception:
            return False

    @classmethod
    def from_cache(cls, path: str):
        """Load a cached index, or return ``None`` when it is unusable."""
        try:
            with open(path, "rb") as handle:
                blob = handle.read()
            if not blob.startswith(CACHE_MAGIC):
                return None
            payload = blob[len(CACHE_MAGIC):]
            words_blob, _, keys_blob = payload.partition(CACHE_SEPARATOR)
            words = words_blob.decode("utf-8").split("\n")
            keys = keys_blob.decode("utf-8").split("\n")
            if len(words) != len(keys) or not words:
                return None
            index = cls.__new__(cls)
            index._words = tuple(words)
            index._keys = tuple(keys)
            return index
        except Exception:
            return None

    # ------------------------------------------------------------------ api
    def __len__(self) -> int:
        return len(self._words)

    def prefix_search(self, prefix: str, limit: int = 30) -> list[str]:
        """Return up to *limit* words starting with *prefix*."""
        if not prefix:
            return []
        prefix_l = prefix.lower()
        lo = bisect.bisect_left(self._keys, prefix_l)
        results: list[str] = []
        for index in range(lo, len(self._keys)):
            if not self._keys[index].startswith(prefix_l):
                break
            results.append(self._words[index])
            if len(results) >= limit:
                break
        return results

    def contains(self, word: str) -> bool:
        """True when *word* is part of the indexed vocabulary."""
        if not word:
            return False
        key = word.lower()
        index = bisect.bisect_left(self._keys, key)
        return index < len(self._keys) and self._keys[index] == key


def load_cached(source_path: str) -> DictIndex | None:
    """Return the cached index for *source_path* when it is still current."""
    if not source_path:
        return None
    cache_path = f"{source_path}.idx"
    try:
        if not (os.path.exists(cache_path) and os.path.exists(source_path)):
            return None
        if os.path.getmtime(cache_path) < os.path.getmtime(source_path):
            return None
    except OSError:
        return None
    return DictIndex.from_cache(cache_path)


def load_or_build(words, source_path: str | None = None) -> DictIndex:
    """Return a cached index when it is current, otherwise build a new one."""
    cache_path = None
    if source_path:
        cached = load_cached(source_path)
        if cached is not None:
            return cached
        cache_path = f"{source_path}.idx"

    index = DictIndex(words)
    if cache_path:
        try:
            index.save_cache(cache_path)
        except Exception:
            pass
    return index
