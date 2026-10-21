"""ALPHA Typing Assistant - intelligent offline typing assistant for Windows."""

from __future__ import annotations

__version__ = "6.0.0"
__all__ = ["__version__", "main"]


def main(argv=None) -> int:
    """Entry point helper (see :mod:`alpha.main`)."""
    from .main import main as _main

    return _main(argv)
