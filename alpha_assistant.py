"""ALPHA Typing Assistant - launcher.

The application itself lives in the ``alpha`` package; this file only wires
the entry point so that ``python alpha_assistant.py`` keeps working.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from alpha.main import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
