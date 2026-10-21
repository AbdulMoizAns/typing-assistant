"""Thread-safe marshalling of work onto the Tk main loop.

Tkinter is not thread safe: every widget call must happen on the thread that
created the root window.  The keyboard hook runs on a separate thread, so all
cross-thread UI work is funnelled through this dispatcher.
"""
from __future__ import annotations

import queue
import threading
from typing import Any, Callable

from .logging_setup import get_logger

log = get_logger("ui")


class UIDispatcher:
    """Queue based bridge from worker threads to the Tk main thread."""

    def __init__(self, root, poll_ms: int = 25):
        self.root = root
        self.poll_ms = poll_ms
        self._queue: "queue.Queue[tuple]" = queue.Queue()
        self._timers: dict[str, Any] = {}
        self._timer_lock = threading.Lock()
        self._running = False

    # ------------------------------------------------------------------ setup
    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self.root.after(self.poll_ms, self._drain)

    def stop(self) -> None:
        self._running = False

    # ------------------------------------------------------------------- post
    def post(self, fn: Callable, *args: Any, **kwargs: Any) -> None:
        """Run *fn* on the main thread as soon as possible."""
        self._queue.put(("run", fn, args, kwargs))

    def post_after(self, name: str, delay_ms: int, fn: Callable, *args: Any, **kwargs: Any) -> None:
        """Schedule *fn* on the main thread, replacing a timer called *name*."""
        self._queue.put(("timer", name, delay_ms, fn, args, kwargs))

    def cancel(self, name: str) -> None:
        """Cancel the pending timer called *name* (safe from any thread)."""
        self._queue.put(("cancel", name))

    # ----------------------------------------------------------------- drain
    def _drain(self) -> None:
        while True:
            try:
                item = self._queue.get_nowait()
            except queue.Empty:
                break
            try:
                self._handle(item)
            except Exception:
                log.exception("UI dispatch failed")
        if self._running:
            try:
                self.root.after(self.poll_ms, self._drain)
            except Exception:
                pass

    def _handle(self, item: tuple) -> None:
        kind = item[0]
        if kind == "run":
            _, fn, args, kwargs = item
            self._run(fn, args, kwargs)
        elif kind == "timer":
            _, name, delay, fn, args, kwargs = item
            self._cancel_timer(name)
            timer = self.root.after(delay, lambda: self._fire(name, fn, args, kwargs))
            with self._timer_lock:
                self._timers[name] = timer
        elif kind == "cancel":
            _, name = item
            self._cancel_timer(name)

    def _fire(self, name: str, fn: Callable, args: tuple, kwargs: dict) -> None:
        with self._timer_lock:
            self._timers.pop(name, None)
        self._run(fn, args, kwargs)

    def _cancel_timer(self, name: str) -> None:
        with self._timer_lock:
            timer = self._timers.pop(name, None)
        if timer is not None:
            try:
                self.root.after_cancel(timer)
            except Exception:
                pass

    @staticmethod
    def _run(fn: Callable, args: tuple, kwargs: dict) -> None:
        try:
            fn(*args, **kwargs)
        except Exception:
            log.exception("UI callback failed: %s", getattr(fn, "__name__", fn))
