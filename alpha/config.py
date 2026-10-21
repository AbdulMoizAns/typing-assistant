"""Central configuration for ALPHA Typing Assistant.

Every tunable, path and default lives here so that behaviour can be changed
without touching engine logic.
"""
from __future__ import annotations

import os

PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(PACKAGE_DIR)

# ---------------------------------------------------------------- data files
SUGGESTIONS_FILE = os.path.join(BASE_DIR, "suggestions.json")
ERRORS_FILE = os.path.join(BASE_DIR, "errors.json")
DICTIONARY_FILE = os.path.join(BASE_DIR, "dictionary.json")
FREQUENCY_FILE = os.path.join(BASE_DIR, "frequency_words.json")
SEQUENCES_FILE = os.path.join(BASE_DIR, "sequences.json")
USAGE_STATS_FILE = os.path.join(BASE_DIR, "usage_stats.json")
RECENCY_FILE = os.path.join(BASE_DIR, "recency.json")
USER_LEARNING_FILE = os.path.join(BASE_DIR, "user_learning.json")
RU_LEARNING_FILE = os.path.join(BASE_DIR, "ru_learning.json")
WORD_PAIRS_FILE = os.path.join(BASE_DIR, "word_pairs.json")
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")
LOG_DIR = os.path.join(BASE_DIR, "logs")

# ------------------------------------------------------------------- tunables
POPUP_WIDTH = 320
MAX_SUGGESTIONS = 8
MAX_VISIBLE_ROWS = 8
ROW_HEIGHT = 28
POPUP_HEADER_HEIGHT = 32
POPUP_MIN_GAP = 10
POPUP_CARET_GAP = 28
MIN_WORD_LENGTH = 2

PASTE_DELAY = 0.05
RESTORE_CLIPBOARD_DELAY = 0.08
BACKSPACE_DELAY = 0.005
DEBOUNCE_MS = 140
NEXT_WORD_DELAY_MS = 70
POPUP_AUTO_CLOSE_MS = 15000
UI_POLL_MS = 25
SEQUENCE_FLUSH_SECONDS = 10.0

# ------------------------------------------------------------------- defaults
ENABLED_DEFAULT = True
AUTO_SUGGEST_DEFAULT = True
NEXT_WORD_DEFAULT = True

# ------------------------------------------------------------- data ceilings
MAX_USER_LEARNING = 2000
MAX_USAGE_STATS = 4000
MAX_RECENCY = 500
MAX_WORD_PAIRS = 1000
MAX_SEQUENCE_PAIRS = 20000

# --------------------------------------------------------------- hotkey codes
VK_CONTROL = 0x11
VK_MENU = 0x12
VK_SHIFT = 0x10
VK_SPACE = 0x20
VK_BACK = 0x08
VK_TAB = 0x09
VK_RETURN = 0x0D
VK_ESCAPE = 0x1B
VK_LEFT = 0x25
VK_UP = 0x26
VK_RIGHT = 0x27
VK_DOWN = 0x28
