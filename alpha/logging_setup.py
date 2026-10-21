"""Logging setup: rotating on-disk log plus console output."""
from __future__ import annotations

import logging
import logging.handlers
import os
import sys

from . import config

_CONFIGURED = False


def setup_logging(level: int = logging.INFO, console: bool = True) -> logging.Logger:
    """Create the ``alpha`` logger exactly once."""
    global _CONFIGURED
    logger = logging.getLogger("alpha")
    if _CONFIGURED:
        return logger

    logger.setLevel(level)
    logger.propagate = False
    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)-7s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    try:
        os.makedirs(config.LOG_DIR, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            os.path.join(config.LOG_DIR, "alpha.log"),
            maxBytes=1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setFormatter(fmt)
        logger.addHandler(file_handler)
    except Exception:
        pass

    if console:
        stream = logging.StreamHandler(sys.stdout)
        stream.setFormatter(fmt)
        logger.addHandler(stream)

    _CONFIGURED = True
    return logger


def get_logger(name: str = "alpha") -> logging.Logger:
    """Return a child logger of the package logger."""
    if not _CONFIGURED:
        setup_logging()
    return logging.getLogger(f"alpha.{name}" if name != "alpha" else "alpha")
