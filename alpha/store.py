"""Data layer: dictionaries, corrections, n-grams and user learning data.

All persistence happens through a coalescing background writer so that a burst
of keystrokes never turns into a burst of disk writes.
"""
from __future__ import annotations

import copy
import json
import os
import re
import threading
import time

from . import config
from .dictionary import DictIndex, load_cached, load_or_build
from .language import (
    ALL_RU_CORRECTIONS,
    RU_ROMAN_ONLY_CORRECTIONS,
    RU_TYPO_CORRECTIONS,
    LanguageDetector,
    apply_case_pattern,
    roman_urdu_correction,
)
from .logging_setup import get_logger
from .ngram import SequenceLearner

log = get_logger("store")

WORD_RE = re.compile(r"[a-zA-Z\u0600-\u06ff']+")


class BackgroundWriter:
    """Writes JSON files off the main thread, coalescing pending writes."""

    BATCH_WINDOW = 0.4

    def __init__(self):
        self._pending: dict[str, object] = {}
        self._pending_lock = threading.Lock()
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._immediate = threading.Event()
        self._busy = False
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def save(self, path: str, data) -> None:
        """Queue *data* for a write to *path* (replacing a pending write)."""
        try:
            snapshot = copy.deepcopy(data)
        except Exception:
            snapshot = data
        with self._pending_lock:
            self._pending[path] = snapshot
        self._wake.set()

    def flush(self, timeout: float = 2.0) -> bool:
        """Block until every queued write has reached the disk."""
        self._immediate.set()
        self._wake.set()
        deadline = time.time() + timeout
        while time.time() < deadline:
            with self._pending_lock:
                pending = bool(self._pending)
            if not pending and not self._busy:
                return True
            time.sleep(0.02)
        return False

    def shutdown(self) -> None:
        self.flush(timeout=1.0)
        self._stop.set()
        self._wake.set()
        self._thread.join(timeout=2.0)

    def _worker(self) -> None:
        while not self._stop.is_set():
            self._wake.wait(timeout=1.0)
            self._wake.clear()
            if self._immediate.is_set():
                self._immediate.clear()
            else:
                time.sleep(self.BATCH_WINDOW)

            with self._pending_lock:
                items = list(self._pending.items())
            if not items:
                continue

            self._busy = True
            try:
                for path, data in items:
                    self._write(path, data)
            finally:
                self._busy = False

            # Only drop the entries that were actually written; a newer write
            # for the same path must survive.
            with self._pending_lock:
                for path, data in items:
                    if self._pending.get(path) is data:
                        del self._pending[path]

    @staticmethod
    def _write(path: str, data) -> None:
        try:
            tmp = f"{path}.tmp"
            with open(tmp, "w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=2, ensure_ascii=False)
            os.replace(tmp, path)
        except Exception:
            log.exception("Failed to persist %s", path)


class PrefixIndex:
    """Maps the first two characters of a word to the words sharing them."""

    __slots__ = ("_buckets",)

    def __init__(self, words=()):
        self._buckets: dict[str, list[str]] = {}
        for word in words:
            self.add(word)

    def add(self, word: str) -> None:
        key = word[:2].lower()
        bucket = self._buckets.setdefault(key, [])
        if word not in bucket:
            bucket.append(word)

    def remove(self, word: str) -> None:
        key = word[:2].lower()
        bucket = self._buckets.get(key)
        if bucket and word in bucket:
            bucket.remove(word)

    def search(self, prefix: str) -> list[str]:
        """Return indexed words that start with *prefix*."""
        if not prefix:
            return []
        key = prefix[:2].lower()
        bucket = self._buckets.get(key)
        if not bucket:
            return []
        lowered = prefix.lower()
        return [word for word in bucket if word.lower().startswith(lowered)]


class DataManager:
    """Owns every dataset used by the assistant."""

    def __init__(self, bg: BackgroundWriter | None = None, base_dir: str | None = None):
        self.bg = bg
        self.base_dir = base_dir or config.BASE_DIR
        self.lang_detector = LanguageDetector()

        self.suggestions = self._load_json(self._path("suggestions.json"), {})
        self.user_learning = self._load_json(self._path("user_learning.json"), {})
        self.usage_stats = self._load_json(self._path("usage_stats.json"), {})
        self.ru_learning = self._load_json(self._path("ru_learning.json"), {})
        self.word_pairs = self._load_json(self._path("word_pairs.json"), {})
        self.recency_tracker = self._load_json(self._path("recency.json"), {})

        freq_raw = self._load_json(self._path("frequency_words.json"), {})
        self.freq_english_words = list(freq_raw.get("english", []))
        self.freq_roman_urdu_words = list(freq_raw.get("roman_urdu", []))
        self.freq_english_ranks = {w.lower(): i for i, w in enumerate(self.freq_english_words)}
        all_freq = self.freq_english_words + self.freq_roman_urdu_words
        self.freq_index = DictIndex(all_freq) if all_freq else None

        self.dict_index = self._build_dict_index()

        raw_errors = self._load_json(self._path("errors.json"), {})
        self.errors = {
            key.strip().lower(): value.strip()
            for key, value in raw_errors.items()
            if isinstance(key, str) and isinstance(value, str)
            and key.strip() and value.strip()
            and key.strip().lower() != value.strip().lower()
        }
        for typo, correct in {
            "teh": "the", "reciver": "receiver", "becuase": "because",
            "recieve": "receive", "seperate": "separate",
            "definately": "definitely", "adn": "and", "acn": "can",
            "taht": "that", "reciept": "receipt", "occured": "occurred",
            "untill": "until", "wich": "which", "freind": "friend",
        }.items():
            self.errors.setdefault(typo, correct)

        self.sequence_learner = SequenceLearner()
        self._load_sequences()
        self._load_common_sequences()

        self.word_history: list[str] = []
        self._user_index = PrefixIndex(self.user_learning.keys())
        self._usage_index = PrefixIndex(self.usage_stats.keys())
        self._pairs_index: dict[str, dict[str, int]] = {}
        self._rebuild_pairs_index()
        self._last_sequence_save = time.time()
        self._file_stamps = self._snapshot_stamps()

    # ------------------------------------------------------------------ paths
    def _path(self, name: str) -> str:
        return os.path.join(self.base_dir, name)

    @staticmethod
    def _load_json(path: str, default):
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as handle:
                    return json.load(handle)
        except Exception:
            log.warning("Could not read %s", path)
        return default

    def _snapshot_stamps(self) -> dict:
        stamps = {}
        for name in ("suggestions.json", "errors.json"):
            path = self._path(name)
            try:
                stamps[path] = os.path.getmtime(path)
            except OSError:
                stamps[path] = None
        return stamps

    def reload_if_changed(self) -> bool:
        """Re-read user editable files when they changed on disk."""
        changed = False
        stamps = self._snapshot_stamps()
        for path, stamp in stamps.items():
            if self._file_stamps.get(path) != stamp:
                changed = True
        if not changed:
            return False

        suggestions = self._load_json(self._path("suggestions.json"), None)
        if suggestions is not None:
            self.suggestions = suggestions
        errors = self._load_json(self._path("errors.json"), None)
        if errors is not None and isinstance(errors, dict):
            self.errors = {
                key.strip().lower(): value.strip()
                for key, value in errors.items()
                if isinstance(key, str) and isinstance(value, str)
                and key.strip() and value.strip()
            }
        self._file_stamps = stamps
        log.info("Reloaded suggestions.json / errors.json from disk")
        return True

    # ------------------------------------------------------------- dictionary
    def _build_dict_index(self):
        path = self._path("dictionary.json")
        cached = load_cached(path)
        if cached is not None:
            log.info("Loaded %d cached dictionary words", len(cached))
            return cached

        raw = self._load_json(path, [])
        if isinstance(raw, list) and raw:
            index = load_or_build(raw, path)
            log.info("Indexed %d fallback dictionary words", len(index))
            return index
        return None

    def is_known_english(self, word: str) -> bool:
        """True when *word* is a common English word."""
        if not word:
            return False
        key = word.lower()
        if key in self.freq_english_ranks:
            return True
        if key in self.errors:
            return False
        return bool(self.dict_index and self.dict_index.contains(key))

    # ------------------------------------------------------------ corrections
    def correct_error(self, word: str, lang: str = "english") -> str:
        """Return the corrected form of *word* for the detected language."""
        if not word or len(word) < 2:
            return word

        if lang == "roman_urdu":
            replacement = ALL_RU_CORRECTIONS.get(word.lower())
            if replacement:
                return apply_case_pattern(word, replacement)

        replacement = self.errors.get(word.lower())
        if replacement:
            return self._match_case(word, replacement)

        replacement = RU_TYPO_CORRECTIONS.get(word.lower())
        if replacement and not self.is_known_english(word):
            return apply_case_pattern(word, replacement)

        return word

    @staticmethod
    def _match_case(source: str, target: str) -> str:
        if source.isupper() and len(source) > 1:
            return target.upper()
        if source and source[0].isupper():
            return target[0].upper() + target[1:]
        return target

    # ------------------------------------------------------------ suggestions
    def get_custom_matches(self, prefix: str) -> list[tuple[str, int]]:
        """Custom snippets and templates that match *prefix*."""
        prefix_l = prefix.lower()
        results: list[tuple[str, int]] = []
        snippets = self.suggestions.get("snippets", {})
        if isinstance(snippets, dict):
            for key, value in snippets.items():
                if not isinstance(key, str) or not isinstance(value, str):
                    continue
                if key.lower() == prefix_l:
                    results.append((self.expand_template(value), 1500))
                elif key.lower().startswith(prefix_l):
                    results.append((self.expand_template(value), 950))
                elif value.lower().startswith(prefix_l):
                    results.append((value, 200))

        templates = self.suggestions.get("templates", [])
        if isinstance(templates, list):
            for template in templates:
                if isinstance(template, str) and template.lower().startswith(prefix_l):
                    results.append((self.expand_template(template), 100))
        return results

    def expand_template(self, template: str) -> str:
        """Replace ``{name}`` placeholders with values from suggestions.json."""
        if not template or "{" not in template:
            return template
        variables = self.suggestions.get("variables", {})
        if not isinstance(variables, dict):
            return template
        expanded = template
        for name, value in variables.items():
            if isinstance(name, str) and isinstance(value, str):
                expanded = expanded.replace("{" + name + "}", value)
        return expanded

    def get_smart_matches_enhanced(self, prefix: str, lang: str = "english", prev_word: str = "") -> list[str]:
        """Two tier suggestion lookup (frequency vocabulary, then dictionary)."""
        if not prefix or len(prefix) < config.MIN_WORD_LENGTH:
            return []
        prefix_l = prefix.lower()
        tier1_map: dict[str, int] = {}

        def add(word: str, score: int) -> None:
            if not word:
                return
            if word not in tier1_map or score > tier1_map[word]:
                tier1_map[word] = score

        # 1. exact typo match - highest priority
        if prefix_l in self.errors:
            score = 3500 if lang == "english" else 3000
            add(self._match_case(prefix, self.errors[prefix_l]), score)

        if prefix_l in RU_TYPO_CORRECTIONS or prefix_l in RU_ROMAN_ONLY_CORRECTIONS:
            score = 3500 if lang == "roman_urdu" else 1800
            add(roman_urdu_correction(prefix, lang, self.is_known_english), score)

        # 2. snippets and templates
        for custom_text, custom_score in self.get_custom_matches(prefix_l):
            add(custom_text, 1400 + custom_score if "\n" in custom_text or "{" in custom_text
                else 2700 + custom_score)

        # 3. contextual bigrams learned from the user
        if prev_word:
            bucket = self._pairs_index.get(prev_word.lower())
            if bucket:
                for word, count in sorted(bucket.items(), key=lambda kv: (-kv[1], kv[0]))[:3]:
                    add(word, 2200 + count * 10)

        # 4. words the user already used
        for word in self._user_index.search(prefix_l):
            add(word, 2100 + self.user_learning.get(word.lower(), 0) * 10)

        for word in self._usage_index.search(prefix_l):
            add(word, 2000 + self.usage_stats.get(word.lower(), 0) * 5)

        # 5. Roman Urdu vocabulary
        ru_weight = 2400 if lang == "roman_urdu" else 1700
        for word in self.freq_roman_urdu_words:
            if word.lower().startswith(prefix_l):
                add(word, ru_weight)

        # 6. high frequency English vocabulary, ranked by real world usage
        en_base = 2500 if lang == "english" else 1800
        if self.freq_index:
            for word in self.freq_index.prefix_search(prefix_l, limit=60):
                rank = self.freq_english_ranks.get(word.lower(), 10000)
                score = en_base - (rank // 8)
                if len(word) - len(prefix_l) <= 3:
                    score += 50
                add(word, score)

            if prefix_l in self.errors:
                corrected = self.errors[prefix_l].lower()
                if corrected != prefix_l and len(corrected) >= 2:
                    for word in self.freq_index.prefix_search(corrected, limit=20):
                        rank = self.freq_english_ranks.get(word.lower(), 10000)
                        add(word, en_base - 100 - (rank // 8))

        # 7. boost candidates the user actually uses
        for word in list(tier1_map.keys()):
            key = word.lower()
            bonus = 0
            if key in self.user_learning:
                bonus += min(150, self.user_learning[key] * 15)
            if key in self.usage_stats:
                bonus += min(100, self.usage_stats[key] * 8)
            if key in self.recency_tracker:
                bonus += min(50, int(self.recency_tracker[key] * 5))
            if bonus:
                tier1_map[word] += bonus

        tier1_sorted = sorted(tier1_map.items(), key=lambda kv: (-kv[1], kv[0]))
        tier1_candidates = [word for word, _ in tier1_sorted]

        # Tier 1 gate: only fall through to the 370k dictionary when the
        # everyday vocabulary cannot fill the popup.
        if len(tier1_candidates) >= 4:
            return tier1_candidates[: config.MAX_SUGGESTIONS]

        tier2_results: list[str] = []
        seen = {word.lower() for word in tier1_candidates}
        if self.dict_index:
            for word in self.dict_index.prefix_search(prefix_l, limit=40):
                key = word.lower()
                if key not in seen and key.isalpha() and len(key) >= 3:
                    seen.add(key)
                    tier2_results.append(word)
            tier2_results.sort(key=lambda word: (len(word), word.lower()))

        return (tier1_candidates + tier2_results)[: config.MAX_SUGGESTIONS]

    # -------------------------------------------------------------- learning
    def commit_word(self, word: str) -> None:
        """Record a committed word in the n-gram model (incremental)."""
        if not word:
            return
        key = word.lower()
        history = self.word_history
        if len(history) >= 2:
            self.sequence_learner.learn_triple(history[-2], history[-1], key)
        if history:
            self.sequence_learner.learn_pair(history[-1], key)
        history.append(key)
        if len(history) > 100:
            del history[:-100]

    def learn_from_text(self, text: str) -> None:
        """Learn every pair contained in *text* (bulk import helper)."""
        words = WORD_RE.findall(text.lower())
        if len(words) < 2:
            if words:
                self.commit_word(words[0])
            return
        self.word_history.extend(words[-2:])
        if len(self.word_history) > 100:
            del self.word_history[:-100]
        self.sequence_learner.learn(words)

    def learn_from_selection(self, original_word: str, selected_word: str, prev_word: str = "") -> None:
        """Remember that *selected_word* followed *original_word*."""
        if prev_word and original_word:
            key = f"{prev_word.lower()}|{original_word.lower()}"
            bucket = self.word_pairs.setdefault(key, {})
            bucket[selected_word] = bucket.get(selected_word, 0) + 1
            self._pairs_index.setdefault(prev_word.lower(), bucket)
            if len(self.word_pairs) > config.MAX_WORD_PAIRS:
                oldest = next(iter(self.word_pairs))
                del self.word_pairs[oldest]
                self._rebuild_pairs_index()
            self._save(self._path("word_pairs.json"), self.word_pairs)

        self.recency_tracker[selected_word] = time.time()
        if len(self.recency_tracker) > config.MAX_RECENCY:
            ordered = sorted(self.recency_tracker.items(), key=lambda kv: kv[1])
            self.recency_tracker = dict(ordered[-config.MAX_RECENCY:])
        self._save(self._path("recency.json"), self.recency_tracker)

    def learn_word(self, word: str, lang: str = "english") -> None:
        """Count a word the user typed."""
        if not word:
            return
        key = word.lower()
        if lang == "roman_urdu":
            self.ru_learning[key] = self.ru_learning.get(key, 0) + 1
            self._save(self._path("ru_learning.json"), self.ru_learning)
        else:
            self.user_learning[key] = self.user_learning.get(key, 0) + 1
            self._user_index.add(key)
            if len(self.user_learning) > config.MAX_USER_LEARNING:
                ordered = sorted(self.user_learning.items(), key=lambda kv: kv[1])
                self.user_learning = dict(ordered[-config.MAX_USER_LEARNING:])
                self._user_index = PrefixIndex(self.user_learning.keys())
            self._save(self._path("user_learning.json"), self.user_learning)

    def record_usage(self, word: str) -> None:
        """Count a word that was inserted."""
        if not word:
            return
        key = word.lower()
        self.usage_stats[key] = self.usage_stats.get(key, 0) + 1
        self._usage_index.add(key)
        if len(self.usage_stats) > config.MAX_USAGE_STATS:
            ordered = sorted(self.usage_stats.items(), key=lambda kv: kv[1])
            self.usage_stats = dict(ordered[-config.MAX_USAGE_STATS:])
            self._usage_index = PrefixIndex(self.usage_stats.keys())
        self._save(self._path("usage_stats.json"), self.usage_stats)

    # ------------------------------------------------------------ prediction
    def predict_next_words(self, current_word: str, prev_word: str | None = None,
                           lang: str = "english", limit: int = 5) -> list[str]:
        """Predict the words that follow *current_word*."""
        if not current_word:
            return []
        predictions = self.sequence_learner.predict_next(current_word, prev_word, limit=limit * 2)

        bucket = self._pairs_index.get(current_word.lower())
        if bucket:
            for word in sorted(bucket, key=lambda w: (-bucket[w], w))[:3]:
                if word not in predictions:
                    predictions.append(word)

        return predictions[:limit]

    def predict_next_word(self, current_word: str) -> list[str]:
        prev = self.word_history[-1] if self.word_history else None
        return self.sequence_learner.predict_next(current_word, prev)

    def get_smart_matches_with_prediction(self, prefix: str, lang: str = "english") -> list[str]:
        """Combined predictions and completions for the popup."""
        suggestions: list[str] = []
        for prediction in self.predict_next_word(prefix)[:3]:
            if prediction not in suggestions:
                suggestions.append(prediction)
        for match in self.get_smart_matches_enhanced(prefix, lang):
            if match not in suggestions:
                suggestions.append(match)
        return suggestions[: config.MAX_SUGGESTIONS]

    # ---------------------------------------------------------- persistence
    def _save(self, path: str, data) -> None:
        if self.bg:
            self.bg.save(path, data)

    def _load_sequences(self) -> None:
        data = self._load_json(self._path("sequences.json"), {})
        self.sequence_learner.load_dict(data if isinstance(data, dict) else {})

    def _load_common_sequences(self) -> None:
        """Seed the model with the built-in everyday bigrams and trigrams."""
        common = {
            "how": {"are": 120, "to": 90, "do": 80, "is": 70, "can": 60},
            "are": {"you": 120, "we": 80, "there": 70, "they": 60, "your": 50},
            "i": {"am": 120, "have": 100, "will": 90, "would": 85, "want": 80, "can": 75, "need": 70},
            "you": {"are": 110, "have": 90, "can": 80, "want": 70, "know": 60},
            "thank": {"you": 140, "god": 80},
            "thanks": {"for": 110, "to": 80, "you": 70},
            "please": {"let": 120, "find": 100, "help": 90, "send": 85, "contact": 80, "check": 75},
            "let": {"me": 130, "us": 110},
            "would": {"like": 130, "be": 100, "have": 80, "prefer": 70},
            "could": {"you": 120, "be": 80, "have": 70},
            "can": {"you": 120, "i": 100, "we": 90, "be": 70},
            "will": {"be": 110, "have": 90, "do": 80, "call": 70},
            "good": {"morning": 120, "afternoon": 100, "evening": 95, "night": 90, "job": 80, "luck": 75},
            "have": {"a": 120, "been": 100, "to": 90, "done": 70},
            "take": {"care": 130, "it": 90, "time": 80},
            "see": {"you": 130, "the": 80, "it": 70},
            "nice": {"to": 130},
            "looking": {"forward": 140},
            "what": {"is": 120, "are": 90, "do": 80, "about": 70},
            "where": {"is": 120, "are": 90, "can": 70},
            "when": {"is": 110, "will": 90, "can": 80, "you": 70},
            "who": {"is": 120, "are": 90, "can": 80},
            "this": {"is": 120, "will": 80, "was": 70},
            "that": {"is": 120, "was": 90, "would": 70},
            "there": {"is": 120, "are": 110, "was": 80},
            "here": {"is": 120, "are": 90},
            "well": {"done": 120, "said": 80},
            "very": {"good": 120, "much": 110, "well": 90, "happy": 80},
            "in": {"order": 110, "the": 100, "this": 80},
            "as": {"well": 120, "per": 110, "soon": 100},
            "aap": {"kaise": 140, "kahan": 110, "kya": 100, "ko": 90, "ka": 85, "batao": 80},
            "kaise": {"ho": 140, "hain": 130},
            "mein": {"theek": 140, "thik": 130, "bhi": 100, "apne": 90, "aaj": 80},
            "theek": {"hoon": 140, "hai": 130, "hoga": 90},
            "thik": {"hoon": 140, "hai": 130},
            "shukriya": {"bohat": 130, "bhai": 120, "aapka": 110, "dost": 90},
            "bohat": {"shukriya": 140, "achha": 120, "khoob": 110, "zyada": 100},
            "kya": {"hal": 140, "haal": 140, "hai": 130, "hua": 110, "baat": 100, "aap": 90},
            "hal": {"hai": 140, "hain": 130},
            "haal": {"hai": 140, "hain": 130},
            "apna": {"khayal": 140, "kaam": 110, "naam": 90},
            "allah": {"hafiz": 140, "ka": 100},
            "jumma": {"mubarak": 150},
            "eid": {"mubarak": 150},
            "koi": {"baat": 140, "masla": 120, "nahi": 110},
            "hum": {"sab": 130, "bhi": 100},
            "yeh": {"kaam": 120, "baat": 110, "kya": 100},
            "karna": {"hai": 130, "hoga": 110, "chahiye": 100},
            "zaroor": {"karna": 120, "aana": 110, "batana": 100},
            "assalam": {"o": 150},
            "o": {"alaikum": 150},
            "walaikum": {"assalam": 150},
        }
        for word, next_words in common.items():
            bucket = self.sequence_learner.sequences.setdefault(word, {})
            for next_word, count in next_words.items():
                bucket.setdefault(next_word, count)

        common_trigrams = {
            "how_are": {"you": 160, "things": 110, "they": 90, "we": 80},
            "thank_you": {"so": 160, "very": 150, "much": 140, "for": 130},
            "please_let": {"me": 160, "us": 130},
            "let_me": {"know": 160, "see": 120, "check": 110},
            "would_like": {"to": 160, "a": 110},
            "looking_forward": {"to": 160},
            "nice_to": {"meet": 160, "see": 130},
            "have_a": {"good": 160, "great": 150, "nice": 140, "wonderful": 120},
            "take_care": {"of": 160, "bye": 120},
            "see_you": {"soon": 160, "tomorrow": 140, "later": 130},
            "what_is": {"the": 160, "your": 150, "this": 140},
            "i_am": {"writing": 150, "pleased": 130, "fine": 120, "working": 110},
            "as_well": {"as": 160},
            "in_order": {"to": 160},
            "aap_kaise": {"ho": 170, "hain": 160},
            "mein_theek": {"hoon": 170},
            "mein_thik": {"hoon": 170},
            "kya_hal": {"hai": 170, "hain": 160},
            "kya_haal": {"hai": 170, "hain": 160},
            "apna_khayal": {"rakhna": 170, "rakhein": 160},
            "allah_hafiz": {"bhai": 160, "dost": 130},
            "jumma_mubarak": {"ho": 160, "aapko": 150},
            "eid_mubarak": {"ho": 160, "aapko": 150},
            "koi_baat": {"nahi": 170},
            "bohat_bohat": {"shukriya": 170, "mubarak": 160},
            "theek_hai": {"bhai": 160, "to": 130},
            "assalam_o": {"alaikum": 180},
        }
        for key, next_words in common_trigrams.items():
            bucket = self.sequence_learner.trigrams.setdefault(key, {})
            for next_word, count in next_words.items():
                bucket.setdefault(next_word, count)

    def _rebuild_pairs_index(self) -> None:
        self._pairs_index = {}
        for key, bucket in self.word_pairs.items():
            if not isinstance(bucket, dict):
                continue
            prev = key.split("|", 1)[0].lower()
            self._pairs_index.setdefault(prev, bucket)

    def maybe_save_sequences(self, force: bool = False) -> None:
        """Persist the n-gram model at most every few seconds."""
        if not self.sequence_learner.dirty:
            return
        now = time.time()
        if not force and (now - self._last_sequence_save) < config.SEQUENCE_FLUSH_SECONDS:
            return
        self.sequence_learner.dirty = False
        self._last_sequence_save = now
        self.sequence_learner.prune()
        self._save(self._path("sequences.json"), self.sequence_learner.to_dict())

    def flush(self) -> None:
        """Persist everything that is pending."""
        self.maybe_save_sequences(force=True)
        if self.bg:
            self.bg.flush()
