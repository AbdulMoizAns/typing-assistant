"""Thread safe UI dispatching."""
from __future__ import annotations

from alpha.ui_queue import UIDispatcher


class FakeRoot:
    """Minimal stand in for a tkinter root window."""

    def __init__(self):
        self.timers = {}
        self._counter = 0

    def after(self, delay, fn):
        self._counter += 1
        self.timers[self._counter] = fn
        return self._counter

    def after_cancel(self, timer):
        self.timers.pop(timer, None)


def test_posted_callables_run_on_drain():
    root = FakeRoot()
    dispatcher = UIDispatcher(root)
    calls = []
    dispatcher.post(calls.append, "value")
    dispatcher._drain()
    assert calls == ["value"]


def test_named_timers_are_registered_and_fire():
    root = FakeRoot()
    dispatcher = UIDispatcher(root)
    calls = []
    dispatcher.post_after("debounce", 50, calls.append, "later")
    dispatcher._drain()
    assert len(root.timers) == 1
    for fn in list(root.timers.values()):
        fn()
    assert calls == ["later"]


def test_cancel_removes_a_pending_timer():
    root = FakeRoot()
    dispatcher = UIDispatcher(root)
    calls = []
    dispatcher.post_after("debounce", 50, calls.append, "later")
    dispatcher._drain()
    dispatcher.cancel("debounce")
    dispatcher._drain()
    assert root.timers == {}
    assert calls == []


def test_a_new_timer_replaces_the_previous_one():
    root = FakeRoot()
    dispatcher = UIDispatcher(root)
    calls = []
    dispatcher.post_after("suggest", 50, calls.append, "first")
    dispatcher._drain()
    dispatcher.post_after("suggest", 50, calls.append, "second")
    dispatcher._drain()
    assert len(root.timers) == 1


def test_exceptions_in_callbacks_do_not_break_the_dispatcher():
    root = FakeRoot()
    dispatcher = UIDispatcher(root)
    calls = []

    def boom():
        raise RuntimeError("boom")

    dispatcher.post(boom)
    dispatcher.post(calls.append, "still works")
    dispatcher._drain()
    assert calls == ["still works"]
