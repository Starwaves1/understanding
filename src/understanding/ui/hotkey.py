"""Modifier-tap hotkey: press a modifier chord (default ⌃⌥) and release it
without pressing any other key. Chords used with a key (⌃⌥K) don't fire.

The tap logic is a pure state machine (ModifierTap) so it's testable; the
NSEvent monitors just feed it.
"""

from __future__ import annotations

import time
from collections.abc import Callable

from AppKit import (
    NSEvent,
    NSEventMaskFlagsChanged,
    NSEventMaskKeyDown,
    NSEventModifierFlagCommand,
    NSEventModifierFlagControl,
    NSEventModifierFlagOption,
    NSEventModifierFlagShift,
    NSEventTypeKeyDown,
)

FLAGS = {
    "control": NSEventModifierFlagControl,
    "option": NSEventModifierFlagOption,
    "command": NSEventModifierFlagCommand,
    "shift": NSEventModifierFlagShift,
}
ESCAPE_KEYCODE = 53


class ModifierTap:
    def __init__(self, target: set[str], max_seconds: float, now: Callable[[], float] = time.monotonic) -> None:
        unknown = target - FLAGS.keys()
        if unknown:
            raise ValueError(f"unknown modifiers {unknown}; use {sorted(FLAGS)}")
        self.target = frozenset(target)
        self.max_seconds = max_seconds
        self.now = now
        self.armed_at: float | None = None

    def modifiers(self, held: set[str]) -> bool:
        """Feed the currently-held modifiers. Returns True when the tap completes."""
        if held == self.target:
            if self.armed_at is None:
                self.armed_at = self.now()
            return False
        if held and held < self.target and self.armed_at is not None:
            return False  # releasing the chord one key at a time
        if not held and self.armed_at is not None:
            fired = self.now() - self.armed_at <= self.max_seconds
            self.armed_at = None
            return fired
        self.armed_at = None
        return False

    def key(self) -> None:
        self.armed_at = None


class Hotkey:
    def __init__(
        self,
        modifiers: list[str],
        max_seconds: float,
        on_tap: Callable[[], None],
        on_escape: Callable[[], None],
    ) -> None:
        self.tap = ModifierTap(set(modifiers), max_seconds)
        self.on_tap = on_tap
        self.on_escape = on_escape
        mask = NSEventMaskFlagsChanged | NSEventMaskKeyDown
        # Global: events going to other apps (needs Accessibility permission).
        self._global = NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(mask, self._handle)
        # Local: events going to our own windows (the prompt panel).
        self._local = NSEvent.addLocalMonitorForEventsMatchingMask_handler_(mask, self._handle_local)

    def _handle_local(self, event):
        self._handle(event)
        return event

    def _handle(self, event) -> None:
        if event.type() == NSEventTypeKeyDown:
            self.tap.key()
            if event.keyCode() == ESCAPE_KEYCODE:
                self.on_escape()
            return
        flags = event.modifierFlags()
        held = {name for name, bit in FLAGS.items() if flags & bit}
        if self.tap.modifiers(held):
            self.on_tap()
